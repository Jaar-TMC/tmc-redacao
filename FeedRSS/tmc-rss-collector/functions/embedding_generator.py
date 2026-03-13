"""
Timer Trigger para geracao de embeddings de artigos.
Executa a cada 5 minutos para processar artigos sem embeddings.
"""

import azure.functions as func
import logging
from datetime import datetime

from services.database import get_db
from services.async_db import run_db
from services.embedding_service import (
    get_embedding_service,
    is_embedding_configured
)

logger = logging.getLogger(__name__)

# Configuration
MAX_ARTICLES_PER_RUN = 50


async def embedding_generator_handler(timer: func.TimerRequest) -> None:
    """
    Handler principal do timer trigger para geracao de embeddings.
    Executa a cada 5 minutos para processar artigos sem embeddings.

    Flow:
    1. Check if embedding service is configured
    2. Get articles without embeddings from database
    3. Generate embeddings in batch via OpenAI API
    4. Save embeddings to database
    5. Log results
    """
    start_time = datetime.utcnow()
    execution_id = start_time.strftime('%Y%m%d_%H%M%S')

    logger.info(f"[{execution_id}] Embedding Generator started")

    # Check configuration
    if not is_embedding_configured():
        logger.warning(f"[{execution_id}] Embedding service not configured (missing OPENAI_API_KEY)")
        return

    db = get_db()

    # Verify database connection
    if not await run_db(db.test_connection):
        logger.error(f"[{execution_id}] Database connection failed")
        return

    try:
        # Get articles without embeddings
        articles = await run_db(db.get_articles_without_embedding, limit=MAX_ARTICLES_PER_RUN)

        if not articles:
            logger.info(f"[{execution_id}] No articles pending embedding generation")
            return

        logger.info(f"[{execution_id}] Found {len(articles)} articles to process")

        # Initialize embedding service
        embedding_service = get_embedding_service()

        # Prepare texts for embedding
        texts = []
        article_ids = []
        for article in articles:
            title = article.get('title', '')
            content = article.get('content') or article.get('preview', '')

            # Combine title and content for better semantic representation
            text = f"{title}\n\n{content}" if content else title
            # Truncate to max length (8000 chars for text-embedding-3-small)
            text = text[:8000].strip()

            if text:
                texts.append(text)
                article_ids.append(article['id'])
            else:
                logger.warning(f"[{execution_id}] Skipping article {article['id']} - empty text")

        if not texts:
            logger.info(f"[{execution_id}] No valid texts to embed")
            return

        # Generate embeddings in batch
        logger.info(f"[{execution_id}] Generating embeddings for {len(texts)} articles")
        embeddings = await embedding_service.generate_embeddings_batch(texts)

        # Save embeddings to database in batch (single connection + transaction)
        saved_count = 0
        try:
            saved_count = await run_db(
                db.save_article_embeddings_batch,
                article_ids=article_ids,
                embeddings=embeddings,
                model_version='text-embedding-3-small'
            )
        except Exception as e:
            logger.error(f"[{execution_id}] Batch embedding save failed, falling back to individual: {e}")
            # Fallback to individual saves
            for article_id, embedding in zip(article_ids, embeddings):
                try:
                    success = await run_db(
                        db.save_article_embedding,
                        article_id=article_id,
                        embedding=embedding,
                        model_version='text-embedding-3-small'
                    )
                    if success:
                        await run_db(db.mark_article_has_embedding, article_id)
                        saved_count += 1
                except Exception as inner_e:
                    logger.error(f"[{execution_id}] Error saving embedding for article {article_id}: {inner_e}")
                    continue

        # Log results
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"[{execution_id}] Embedding Generator finished: "
            f"{len(articles)} found, {len(texts)} processed, {saved_count} saved, "
            f"{duration:.2f}s"
        )

    except Exception as e:
        logger.error(f"[{execution_id}] Embedding Generator error: {e}")
        raise
