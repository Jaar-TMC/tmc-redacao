"""
Timer Trigger para coleta automatica de feeds RSS.
Executa a cada 15 minutos.
"""

import azure.functions as func
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
import os

from services.database import get_db
from services.rss_parser import RSSParser
from services.deduplication import deduplicate_with_db
from services.enrichment import enrich_article_image
from services.ai_enrichment import enrich_articles_with_ai, is_ai_enrichment_enabled
from services.scoring_service import get_scoring_service
from models import Source

logger = logging.getLogger(__name__)

# Configuracoes
MAX_CONCURRENT = int(os.environ.get('RSS_MAX_CONCURRENT', '10'))
FETCH_TIMEOUT = int(os.environ.get('RSS_FETCH_TIMEOUT', '30'))
MAX_ARTICLES = int(os.environ.get('RSS_MAX_ARTICLES_PER_FEED', '100'))
MIN_CONTENT_CHARS = int(os.environ.get('RSS_MIN_CONTENT_CHARS', '300'))


async def rss_collector_handler(timer: func.TimerRequest) -> None:
    """
    Handler principal do timer trigger.
    Executa a cada 15 minutos para coletar feeds RSS.
    """
    start_time = datetime.utcnow()
    execution_id = start_time.strftime('%Y%m%d_%H%M%S')

    logger.info(f"[{execution_id}] RSS Collector started")

    db = get_db()

    # Verificar conexao com banco
    if not db.test_connection():
        logger.error(f"[{execution_id}] Database connection failed")
        return

    # Extended to 72h to prevent articles vanishing mid-workflow
    try:
        deleted_old = db.delete_old_articles(hours=72)
        if deleted_old > 0:
            logger.info(f"[{execution_id}] Cleanup: deleted {deleted_old} articles older than 72h")

        deleted_dupes = db.delete_duplicate_articles_by_title()
        if deleted_dupes > 0:
            logger.info(f"[{execution_id}] Cleanup: deleted {deleted_dupes} duplicate articles")
    except Exception as e:
        logger.warning(f"[{execution_id}] Cleanup failed: {e}")

    # Buscar fontes que devem ser coletadas
    try:
        sources = db.get_sources_to_fetch()
        logger.info(f"[{execution_id}] Found {len(sources)} sources to fetch")
    except Exception as e:
        logger.error(f"[{execution_id}] Error fetching sources: {e}")
        return

    if not sources:
        logger.info(f"[{execution_id}] No sources to fetch at this time")
        return

    # Processar fontes em paralelo
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    parser = RSSParser(timeout=FETCH_TIMEOUT)

    async def process_with_semaphore(source: Source) -> Dict[str, Any]:
        async with semaphore:
            return await process_single_source(source, db, parser, execution_id)

    tasks = [process_with_semaphore(s) for s in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Close the shared HTTP client after all feeds are processed
    try:
        await parser.close()
    except Exception:
        pass

    # Agregar resultados
    total_new = 0
    total_found = 0
    total_errors = 0
    total_scored = 0
    total_short_filtered = 0

    for result in results:
        if isinstance(result, Exception):
            total_errors += 1
        elif isinstance(result, dict):
            total_new += result.get('new', 0)
            total_found += result.get('found', 0)
            total_scored += result.get('scored', 0)
            total_short_filtered += result.get('short_filtered', 0)

    # Log final
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(
        f"[{execution_id}] RSS Collector finished: "
        f"{len(sources)} sources, {total_found} found, {total_new} new, "
        f"{total_scored} scored, {total_short_filtered} short filtered, "
        f"{total_errors} errors, {duration:.2f}s"
    )


async def process_single_source(source: Source, db, parser: RSSParser,
                                execution_id: str) -> Dict[str, Any]:
    """
    Processa uma unica fonte RSS.

    Fluxo:
    1. Fetch e parse do feed
    2. Deduplicar artigos
    3. Enriquecer artigos sem imagem
    4. Enriquecer com AI (categoria semantica e tags SEO)
    5. Inserir no banco
    6. Atualizar fonte e logar
    """
    start_time = datetime.utcnow()
    source_name = source.name

    logger.info(f"[{execution_id}] Processing: {source_name}")

    try:
        # 1. Parse do feed
        articles = await parser.parse_feed(
            url=source.url,
            source_id=source.id,
            source_category=source.category,
            max_articles=MAX_ARTICLES
        )

        articles_found = len(articles)
        logger.debug(f"[{execution_id}] {source_name}: Found {articles_found} articles")

        if not articles:
            # Feed vazio ou sem novidades
            db.update_source_last_fetch(source.id, 0)
            db.log_collection(
                source_id=source.id,
                status='success',
                articles_found=0,
                articles_new=0,
                articles_duplicate=0,
                duration_ms=_get_duration_ms(start_time)
            )
            return {'found': 0, 'new': 0, 'duplicate': 0}

        # 2. Deduplicar
        unique_articles = await deduplicate_with_db(articles, db)
        articles_duplicate = articles_found - len(unique_articles)

        logger.debug(f"[{execution_id}] {source_name}: {len(unique_articles)} unique, {articles_duplicate} duplicates")

        # 2b. Filter out short articles (< MIN_CONTENT_CHARS) to avoid wasting
        # AI tokens on classification, scoring, embedding for unusable articles
        before_filter = len(unique_articles)
        unique_articles = [
            a for a in unique_articles
            if a.content and len(a.content) >= MIN_CONTENT_CHARS
        ]
        articles_short = before_filter - len(unique_articles)
        if articles_short > 0:
            logger.info(
                f"[{execution_id}] {source_name}: Filtered {articles_short} articles "
                f"with content < {MIN_CONTENT_CHARS} chars"
            )

        if not unique_articles:
            db.update_source_last_fetch(source.id, 0)
            db.log_collection(
                source_id=source.id,
                status='success',
                articles_found=articles_found,
                articles_new=0,
                articles_duplicate=articles_duplicate,
                duration_ms=_get_duration_ms(start_time)
            )
            return {'found': articles_found, 'new': 0, 'duplicate': articles_duplicate, 'short_filtered': articles_short}

        # 3. Enriquecer artigos sem imagem (limitar a 5, processar em paralelo)
        articles_to_enrich = [a for a in unique_articles if not a.image_url][:5]
        if articles_to_enrich:
            async def _enrich_one(article):
                try:
                    article.image_url = await enrich_article_image(article.url, timeout=10)
                except Exception as e:
                    logger.debug(f"[{execution_id}] Failed to enrich image for {article.url}: {e}")
            await asyncio.gather(*[_enrich_one(a) for a in articles_to_enrich])

        # 4. Enriquecer artigos com AI (categoria semantica e tags SEO)
        try:
            if is_ai_enrichment_enabled():
                logger.info(f"[{execution_id}] {source_name}: Starting AI enrichment for {len(unique_articles)} articles")
                unique_articles = await enrich_articles_with_ai(unique_articles)
                logger.info(f"[{execution_id}] {source_name}: AI enrichment completed")
        except Exception as e:
            logger.warning(f"[{execution_id}] {source_name}: AI enrichment failed, using RSS data: {e}")
            # Graceful degradation - continue with RSS metadata

        # 5. Inserir no banco (retornando IDs para scoring inline)
        articles_new, inserted_articles = db.insert_articles_returning(unique_articles)

        logger.info(f"[{execution_id}] {source_name}: Inserted {articles_new} new articles")

        # 5b. Scoring inline - GUARANTEED: every article gets a score
        articles_scored = 0
        if inserted_articles:
            scoring_service = get_scoring_service()
            scores = await scoring_service.score_articles_batch(
                inserted_articles,
                use_heuristic_fallback=True,
                batch_delay=0.3
            )
            if scores:
                try:
                    articles_scored = await scoring_service._save_scores(scores)
                    logger.info(f"[{execution_id}] {source_name}: Scored {articles_scored}/{articles_new} articles inline")
                except Exception as e:
                    logger.error(f"[{execution_id}] {source_name}: Failed to save scores to DB: {e}")
            if articles_scored < len(inserted_articles):
                logger.warning(
                    f"[{execution_id}] {source_name}: Only {articles_scored}/{len(inserted_articles)} "
                    f"scores saved — scoring_calculator will backfill"
                )

        # 6. Atualizar fonte
        db.update_source_last_fetch(source.id, articles_new)

        # 7. Logar coleta
        duration_ms = _get_duration_ms(start_time)
        db.log_collection(
            source_id=source.id,
            status='success',
            articles_found=articles_found,
            articles_new=articles_new,
            articles_duplicate=articles_duplicate,
            duration_ms=duration_ms
        )

        return {
            'found': articles_found,
            'new': articles_new,
            'duplicate': articles_duplicate,
            'scored': articles_scored,
            'short_filtered': articles_short
        }

    except Exception as e:
        logger.error(f"[{execution_id}] Error processing {source_name}: {e}")

        # Atualizar fonte com erro
        db.update_source_last_fetch(source.id, 0, error=str(e))

        # Logar erro
        db.log_collection(
            source_id=source.id,
            status='error',
            articles_found=0,
            articles_new=0,
            articles_duplicate=0,
            duration_ms=_get_duration_ms(start_time),
            error=str(e)
        )

        raise


def _get_duration_ms(start_time: datetime) -> int:
    """Calcula duracao em milissegundos."""
    return int((datetime.utcnow() - start_time).total_seconds() * 1000)


# ========================================
# TRIGGER MANUAL (para testes)
# ========================================

async def collect_single_source_handler(source_id: str) -> Dict[str, Any]:
    """
    Handler para coleta manual de uma fonte especifica.
    Usado pelo endpoint POST /api/sources/{id}/collect
    """
    db = get_db()
    parser = RSSParser(timeout=FETCH_TIMEOUT)

    source = db.get_source_by_id(source_id)
    if not source:
        raise ValueError(f"Source not found: {source_id}")

    execution_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    try:
        result = await process_single_source(source, db, parser, execution_id)
    finally:
        try:
            await parser.close()
        except Exception:
            pass

    return {
        'source_id': str(source.id),
        'source_name': source.name,
        'articles_found': result.get('found', 0),
        'articles_new': result.get('new', 0),
        'articles_duplicate': result.get('duplicate', 0),
        'articles_short_filtered': result.get('short_filtered', 0)
    }
