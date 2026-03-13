"""
Timer Trigger para manutencao periodica do clustering de temas.
Executa diariamente as 3AM para:
1. Merge temas muito similares (> 0.90)
2. Desativa temas orfaos (0 artigos)
3. Recalcula scores de todos os temas
4. Gera relatorio de qualidade
"""

import azure.functions as func
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from uuid import UUID

import numpy as np

from services.database import get_db, DatabaseService
from services.async_db import run_db
from services.clustering_service import (
    get_clustering_service,
    is_clustering_enabled,
    cosine_similarity,
    ClusteringService
)

logger = logging.getLogger(__name__)

# Configuration
MERGE_SIMILARITY_THRESHOLD = 0.90  # Temas com similaridade > 90% serao merged
MIN_ARTICLES_FOR_ACTIVE = 1  # Minimo de artigos para manter tema ativo


class MaintenanceReport:
    """Classe para armazenar e formatar o relatorio de manutencao."""

    def __init__(self):
        self.started_at = datetime.utcnow()
        self.finished_at = None
        self.themes_merged = []
        self.themes_deactivated = []
        self.themes_scores_updated = 0
        self.total_active_themes = 0
        self.total_inactive_themes = 0
        self.themes_created_24h = 0
        self.quality_metrics = {}
        self.errors = []

    def finish(self):
        """Marca o fim da execucao."""
        self.finished_at = datetime.utcnow()

    def duration_seconds(self) -> float:
        """Retorna duracao em segundos."""
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return (datetime.utcnow() - self.started_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Converte relatorio para dict."""
        return {
            'started_at': self.started_at.isoformat(),
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'duration_seconds': self.duration_seconds(),
            'themes_merged': self.themes_merged,
            'themes_merged_count': len(self.themes_merged),
            'themes_deactivated': self.themes_deactivated,
            'themes_deactivated_count': len(self.themes_deactivated),
            'themes_scores_updated': self.themes_scores_updated,
            'total_active_themes': self.total_active_themes,
            'total_inactive_themes': self.total_inactive_themes,
            'themes_created_24h': self.themes_created_24h,
            'quality_metrics': self.quality_metrics,
            'errors': self.errors
        }

    def to_log_string(self) -> str:
        """Gera string formatada para logging."""
        return (
            f"Maintenance Report: "
            f"merged={len(self.themes_merged)}, "
            f"deactivated={len(self.themes_deactivated)}, "
            f"scores_updated={self.themes_scores_updated}, "
            f"active={self.total_active_themes}, "
            f"inactive={self.total_inactive_themes}, "
            f"new_24h={self.themes_created_24h}, "
            f"duration={self.duration_seconds():.2f}s"
        )


async def merge_similar_themes(
    db: DatabaseService,
    clustering_service: ClusteringService,
    report: MaintenanceReport
) -> int:
    """
    Encontra e merge temas com alta similaridade (> 0.90).

    O tema menor (menos artigos) e merged no maior.
    Artigos do tema menor sao movidos para o maior.

    Args:
        db: DatabaseService instance
        clustering_service: ClusteringService instance
        report: MaintenanceReport para registrar resultados

    Returns:
        Numero de temas merged
    """
    logger.info("Starting merge_similar_themes...")

    # Carregar todos os temas ativos com centroids
    themes = await run_db(db.get_all_themes, status='active')
    themes_with_centroid = [t for t in themes if t.get('centroid') is not None]

    if len(themes_with_centroid) < 2:
        logger.info("Less than 2 themes with centroids, skipping merge check")
        return 0

    logger.info(f"Checking {len(themes_with_centroid)} themes for merge opportunities")

    # Calcular matriz de similaridade
    merge_candidates = []
    checked_pairs = set()

    for i, theme_a in enumerate(themes_with_centroid):
        for j, theme_b in enumerate(themes_with_centroid):
            if i >= j:
                continue

            pair_key = tuple(sorted([str(theme_a['id']), str(theme_b['id'])]))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            try:
                similarity = cosine_similarity(theme_a['centroid'], theme_b['centroid'])

                if similarity >= MERGE_SIMILARITY_THRESHOLD:
                    merge_candidates.append({
                        'theme_a': theme_a,
                        'theme_b': theme_b,
                        'similarity': similarity
                    })
            except Exception as e:
                logger.warning(f"Error calculating similarity between themes: {e}")
                continue

    if not merge_candidates:
        logger.info("No merge candidates found")
        return 0

    logger.info(f"Found {len(merge_candidates)} merge candidates")

    # Ordenar por similaridade (maior primeiro)
    merge_candidates.sort(key=lambda x: x['similarity'], reverse=True)

    # Executar merges
    merged_ids = set()
    merged_count = 0

    for candidate in merge_candidates:
        theme_a = candidate['theme_a']
        theme_b = candidate['theme_b']
        similarity = candidate['similarity']

        # Pular se algum dos temas ja foi merged
        if str(theme_a['id']) in merged_ids or str(theme_b['id']) in merged_ids:
            continue

        # Determinar qual tema e o target (maior) e qual e o source (menor)
        count_a = theme_a.get('article_count', 0)
        count_b = theme_b.get('article_count', 0)

        if count_a >= count_b:
            target_theme = theme_a
            source_theme = theme_b
        else:
            target_theme = theme_b
            source_theme = theme_a

        try:
            # Mover artigos do source para o target
            success = await _merge_theme_into(db, source_theme, target_theme, similarity)

            if success:
                merged_ids.add(str(source_theme['id']))
                merged_count += 1

                report.themes_merged.append({
                    'source_id': str(source_theme['id']),
                    'source_name': source_theme['name'],
                    'target_id': str(target_theme['id']),
                    'target_name': target_theme['name'],
                    'similarity': round(similarity, 4),
                    'articles_moved': source_theme.get('article_count', 0)
                })

                logger.info(
                    f"Merged theme '{source_theme['name']}' into '{target_theme['name']}' "
                    f"(similarity={similarity:.4f})"
                )
        except Exception as e:
            logger.error(f"Error merging themes: {e}")
            report.errors.append(f"Merge error: {str(e)}")

    return merged_count


def _merge_theme_into_sync(
    db: DatabaseService,
    source_theme: Dict,
    target_theme: Dict,
    similarity: float
) -> bool:
    """Sync helper: move articles from source to target theme and deactivate source."""
    source_id = source_theme['id']
    target_id = target_theme['id']

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()

            move_query = """
                UPDATE article_themes
                SET theme_id = %s,
                    similarity_score = CASE
                        WHEN similarity_score > %s THEN similarity_score * %s
                        ELSE similarity_score
                    END,
                    updated_at = GETUTCDATE()
                WHERE theme_id = %s
                AND article_id NOT IN (
                    SELECT article_id FROM article_themes WHERE theme_id = %s
                )
            """
            cursor.execute(move_query, (
                str(target_id),
                similarity,
                similarity,
                str(source_id),
                str(target_id)
            ))
            moved_count = cursor.rowcount

            delete_dups_query = """
                DELETE FROM article_themes
                WHERE theme_id = %s
            """
            cursor.execute(delete_dups_query, (str(source_id),))

            update_target_query = """
                UPDATE themes
                SET article_count = (
                    SELECT COUNT(*) FROM article_themes WHERE theme_id = %s
                ),
                last_updated_at = GETUTCDATE()
                WHERE id = %s
            """
            cursor.execute(update_target_query, (str(target_id), str(target_id)))

            deactivate_query = """
                UPDATE themes
                SET status = 'merged',
                    article_count = 0,
                    last_updated_at = GETUTCDATE()
                WHERE id = %s
            """
            cursor.execute(deactivate_query, (str(source_id),))

            conn.commit()

            logger.info(f"Moved {moved_count} articles from theme {source_id} to {target_id}")
            return True

    except Exception as e:
        logger.error(f"Error in _merge_theme_into: {e}")
        raise


async def _merge_theme_into(
    db: DatabaseService,
    source_theme: Dict,
    target_theme: Dict,
    similarity: float
) -> bool:
    """Move all articles from source_theme to target_theme and deactivate source."""
    return await run_db(_merge_theme_into_sync, db, source_theme, target_theme, similarity)


def _cleanup_orphan_themes_sync(db: DatabaseService) -> Tuple[int, List[Dict]]:
    """Sync helper: find and deactivate orphan themes. Returns (count, deactivated_list)."""
    query_orphans = """
        SELECT t.id, t.name, t.article_count
        FROM themes t
        WHERE t.status = 'active'
        AND (
            t.article_count = 0
            OR NOT EXISTS (
                SELECT 1 FROM article_themes at WHERE at.theme_id = t.id
            )
        )
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query_orphans)
        orphans = cursor.fetchall()

        if not orphans:
            return 0, []

        orphan_ids = []
        deactivated = []
        for orphan in orphans:
            theme_id = orphan[0]
            theme_name = orphan[1]
            orphan_ids.append(str(theme_id))
            deactivated.append({
                'id': str(theme_id),
                'name': theme_name,
                'reason': 'orphan'
            })
            logger.info(f"Deactivated orphan theme: {theme_name} (ID: {theme_id})")

        if orphan_ids:
            placeholders = ','.join(['%s'] * len(orphan_ids))
            batch_deactivate = f"""
                UPDATE themes
                SET status = 'inactive',
                    article_count = 0,
                    last_updated_at = GETUTCDATE()
                WHERE id IN ({placeholders})
            """
            cursor.execute(batch_deactivate, tuple(orphan_ids))

        conn.commit()
        return len(orphan_ids), deactivated


async def cleanup_orphan_themes(
    db: DatabaseService,
    report: MaintenanceReport
) -> int:
    """Find and deactivate orphan themes (no articles)."""
    logger.info("Starting cleanup_orphan_themes...")
    try:
        count, deactivated = await run_db(_cleanup_orphan_themes_sync, db)
        report.themes_deactivated.extend(deactivated)
        if count == 0:
            logger.info("No orphan themes found")
        else:
            logger.info(f"Found {count} orphan themes to deactivate")
        return count
    except Exception as e:
        logger.error(f"Error in cleanup_orphan_themes: {e}")
        report.errors.append(f"Cleanup error: {str(e)}")
        return 0


async def recalculate_all_scores(
    db: DatabaseService,
    clustering_service: ClusteringService,
    report: MaintenanceReport
) -> int:
    """
    Recalcula scores agregados de todos os temas ativos.

    Args:
        db: DatabaseService instance
        clustering_service: ClusteringService instance
        report: MaintenanceReport para registrar resultados

    Returns:
        Numero de temas atualizados
    """
    logger.info("Starting recalculate_all_scores...")

    try:
        scores_updated = await run_db(clustering_service.recalculate_all_theme_scores)
        report.themes_scores_updated = len(scores_updated)

        logger.info(f"Recalculated scores for {len(scores_updated)} themes")
        return len(scores_updated)

    except Exception as e:
        logger.error(f"Error in recalculate_all_scores: {e}")
        report.errors.append(f"Score recalculation error: {str(e)}")
        return 0


def _generate_quality_metrics_sync(db: DatabaseService) -> Dict[str, Any]:
    """Sync helper: generate clustering quality metrics from DB."""
    with db.get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM themes WHERE status = 'active'")
        total_active = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM themes WHERE status != 'active'")
        total_inactive = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM themes
            WHERE first_seen_at >= DATEADD(hour, -24, GETUTCDATE())
        """)
        created_24h = cursor.fetchone()[0]

        cursor.execute("""
            SELECT
                AVG(CAST(article_count AS FLOAT)) as avg_articles,
                MIN(article_count) as min_articles,
                MAX(article_count) as max_articles,
                STDEV(CAST(article_count AS FLOAT)) as std_articles
            FROM themes
            WHERE status = 'active' AND article_count > 0
        """)
        row = cursor.fetchone()

        cursor.execute("""
            SELECT
                AVG(avg_score) as avg_theme_score,
                MIN(avg_score) as min_theme_score,
                MAX(avg_score) as max_theme_score
            FROM themes
            WHERE status = 'active' AND avg_score IS NOT NULL
        """)
        score_row = cursor.fetchone()

        cursor.execute("""
            SELECT
                CASE
                    WHEN avg_score >= 75 THEN 'A'
                    WHEN avg_score >= 35 THEN 'B'
                    ELSE 'C'
                END as classification,
                COUNT(*) as count
            FROM themes
            WHERE status = 'active' AND avg_score IS NOT NULL
            GROUP BY
                CASE
                    WHEN avg_score >= 75 THEN 'A'
                    WHEN avg_score >= 35 THEN 'B'
                    ELSE 'C'
                END
        """)
        classification_counts = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("""
            SELECT COUNT(*)
            FROM collected_articles a
            JOIN article_embeddings e ON a.id = e.article_id
            LEFT JOIN article_themes at ON a.id = at.article_id
            WHERE at.article_id IS NULL
        """)
        pending_clustering = cursor.fetchone()[0]

        return {
            'total_active': total_active,
            'total_inactive': total_inactive,
            'created_24h': created_24h,
            'articles_distribution': {
                'avg': round(row[0], 2) if row[0] else 0,
                'min': row[1] or 0,
                'max': row[2] or 0,
                'std': round(row[3], 2) if row[3] else 0
            },
            'score_distribution': {
                'avg': round(score_row[0], 2) if score_row[0] else 0,
                'min': round(score_row[1], 2) if score_row[1] else 0,
                'max': round(score_row[2], 2) if score_row[2] else 0
            },
            'classification_counts': classification_counts,
            'pending_clustering': pending_clustering,
        }


async def generate_quality_metrics(
    db: DatabaseService,
    report: MaintenanceReport
) -> Dict[str, Any]:
    """Generate clustering quality metrics."""
    logger.info("Generating quality metrics...")
    try:
        metrics = await run_db(_generate_quality_metrics_sync, db)
        report.total_active_themes = metrics['total_active']
        report.total_inactive_themes = metrics['total_inactive']
        report.themes_created_24h = metrics['created_24h']
        report.quality_metrics = metrics
        return metrics
    except Exception as e:
        logger.error(f"Error generating quality metrics: {e}")
        report.errors.append(f"Metrics error: {str(e)}")
        return {}


async def run_maintenance(db: DatabaseService = None) -> MaintenanceReport:
    """
    Executa todas as tarefas de manutencao do clustering.

    Args:
        db: Optional DatabaseService (usa singleton se nao fornecido)

    Returns:
        MaintenanceReport com resultados
    """
    report = MaintenanceReport()

    if db is None:
        db = get_db()

    # Verificar conexao
    if not await run_db(db.test_connection):
        report.errors.append("Database connection failed")
        report.finish()
        return report

    # Inicializar clustering service
    clustering_service = get_clustering_service(db_service=db)

    try:
        # 1. Merge temas similares
        await merge_similar_themes(db, clustering_service, report)

        # 2. Cleanup temas orfaos
        await cleanup_orphan_themes(db, report)

        # 3. Recalcular scores
        await recalculate_all_scores(db, clustering_service, report)

        # 4. Gerar metricas de qualidade
        await generate_quality_metrics(db, report)

    except Exception as e:
        logger.error(f"Error during maintenance: {e}")
        report.errors.append(f"General error: {str(e)}")

    report.finish()
    return report


async def clustering_maintenance_handler(timer: func.TimerRequest) -> None:
    """
    Handler principal do timer trigger para manutencao do clustering.
    Executa diariamente as 3AM.

    Tarefas:
    1. Merge temas muito similares (> 0.90)
    2. Desativa temas orfaos (0 artigos)
    3. Recalcula scores de todos os temas
    4. Gera relatorio de qualidade
    """
    execution_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    logger.info(f"[{execution_id}] Clustering Maintenance started")

    # Verificar se clustering esta habilitado
    if not is_clustering_enabled():
        logger.info(f"[{execution_id}] Clustering is disabled via CLUSTERING_ENABLED env var")
        return

    db = get_db()

    # Verificar conexao
    if not await run_db(db.test_connection):
        logger.error(f"[{execution_id}] Database connection failed")
        return

    try:
        # Executar manutencao
        report = await run_maintenance(db)

        # Log resultado
        logger.info(f"[{execution_id}] {report.to_log_string()}")

        if report.errors:
            logger.warning(f"[{execution_id}] Maintenance completed with errors: {report.errors}")
        else:
            logger.info(f"[{execution_id}] Maintenance completed successfully")

    except Exception as e:
        logger.error(f"[{execution_id}] Clustering Maintenance error: {e}")
        raise


async def clustering_maintenance_manual_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handler HTTP para execucao manual da manutencao do clustering.

    POST /api/clustering/maintenance

    Query params:
        dry_run: bool - Se true, apenas simula sem fazer alteracoes (default: false)

    Returns:
        JSON com relatorio de manutencao
    """
    execution_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    logger.info(f"[{execution_id}] Manual Clustering Maintenance triggered")

    # Verificar se clustering esta habilitado
    if not is_clustering_enabled():
        return func.HttpResponse(
            json.dumps({
                'error': 'Clustering is disabled',
                'message': 'Set CLUSTERING_ENABLED=true to enable clustering'
            }),
            status_code=400,
            mimetype='application/json'
        )

    # Verificar dry_run parameter
    dry_run = req.params.get('dry_run', 'false').lower() == 'true'

    if dry_run:
        # Modo dry_run: apenas retorna metricas sem fazer alteracoes
        logger.info(f"[{execution_id}] Running in dry-run mode")
        db = get_db()

        if not await run_db(db.test_connection):
            return func.HttpResponse(
                json.dumps({'error': 'Database connection failed'}),
                status_code=500,
                mimetype='application/json'
            )

        report = MaintenanceReport()
        await generate_quality_metrics(db, report)
        report.finish()

        return func.HttpResponse(
            json.dumps({
                'mode': 'dry_run',
                'metrics': report.quality_metrics,
                'message': 'Dry run completed - no changes made'
            }),
            status_code=200,
            mimetype='application/json'
        )

    try:
        # Executar manutencao completa
        report = await run_maintenance()

        logger.info(f"[{execution_id}] {report.to_log_string()}")

        return func.HttpResponse(
            json.dumps({
                'success': len(report.errors) == 0,
                'report': report.to_dict()
            }),
            status_code=200 if not report.errors else 207,  # 207 = Multi-Status (partial success)
            mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"[{execution_id}] Manual maintenance error: {e}")
        return func.HttpResponse(
            json.dumps({
                'error': 'Erro interno ao executar manutenção',
                'message': 'Maintenance failed'
            }),
            status_code=500,
            mimetype='application/json'
        )
