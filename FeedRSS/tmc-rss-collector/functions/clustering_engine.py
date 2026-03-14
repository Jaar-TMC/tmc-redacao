"""
Timer Trigger para clustering semantico de artigos em temas.
Executa a cada 30 minutos para agrupar artigos com embeddings em temas.
"""

import azure.functions as func
import logging
from datetime import datetime

from services.database import get_db
from services.async_db import run_db
from services.clustering_service import (
    get_clustering_service,
    is_clustering_enabled
)

logger = logging.getLogger(__name__)

# Configuration
MAX_ARTICLES_PER_RUN = 100


async def clustering_engine_handler(timer: func.TimerRequest) -> None:
    """
    Handler principal do timer trigger para clustering de artigos.
    Executa a cada 30 minutos para agrupar artigos em temas semanticos.

    Algorithm:
    1. Get articles with embeddings but no theme assignment
    2. For each article:
       a. Find best matching theme (cosine similarity >= 0.75)
       b. If match found: add to existing theme
       c. If no match: create new theme with article as seed
    3. Update theme centroids (exponential moving average)
    4. Recalculate theme aggregate scores
    5. Check for theme merging opportunities (similarity >= 0.90)

    Flow:
    1. Check if clustering is enabled
    2. Load active themes into cache
    3. Process pending articles
    4. Log new and updated themes
    """
    start_time = datetime.utcnow()
    execution_id = start_time.strftime('%Y%m%d_%H%M%S')

    logger.info(f"[{execution_id}] Clustering Engine started")

    from services.ai_status_service import is_ai_paused
    if is_ai_paused():
        logger.info(f"[{execution_id}] AI paused by admin, skipping clustering")
        return

    # Check if clustering is enabled
    if not is_clustering_enabled():
        logger.info(f"[{execution_id}] Clustering is disabled via CLUSTERING_ENABLED env var")
        return

    db = get_db()

    # Verify database connection
    if not await run_db(db.test_connection):
        logger.error(f"[{execution_id}] Database connection failed")
        return

    try:
        # Initialize clustering service with database
        clustering_service = get_clustering_service(db_service=db)

        # Get count of pending articles before processing
        pending_articles = await run_db(db.get_articles_pending_clustering, limit=MAX_ARTICLES_PER_RUN)
        pending_count = len(pending_articles) if pending_articles else 0

        if pending_count == 0:
            logger.info(f"[{execution_id}] No articles pending clustering")
            return

        logger.info(f"[{execution_id}] Found {pending_count} articles to cluster")

        # Process pending articles
        processed = await clustering_service.process_pending_articles(limit=MAX_ARTICLES_PER_RUN)

        # Get theme statistics
        theme_stats = await _get_theme_statistics(db)

        # Log results
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"[{execution_id}] Clustering Engine finished: "
            f"{processed} articles processed, "
            f"themes: total={theme_stats.get('total', 0)}, "
            f"new={theme_stats.get('new_today', 0)}, "
            f"updated={theme_stats.get('updated_today', 0)}, "
            f"{duration:.2f}s"
        )

    except Exception as e:
        logger.error(f"[{execution_id}] Clustering Engine error: {e}")
        raise


def _get_theme_statistics_sync(db) -> dict:
    """Sync helper: get theme statistics using a single aggregation query."""
    combined_query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN first_seen_at >= DATEADD(day, -1, GETUTCDATE()) THEN 1 ELSE 0 END) as new_today,
            SUM(CASE WHEN last_updated_at >= DATEADD(day, -1, GETUTCDATE())
                      AND last_updated_at > first_seen_at THEN 1 ELSE 0 END) as updated_today
        FROM themes
        WHERE status = 'active'
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(combined_query)
            row = cursor.fetchone()
            return {
                'total': row[0] or 0,
                'new_today': row[1] or 0,
                'updated_today': row[2] or 0
            }
    except Exception as e:
        logger.warning(f"Error getting theme statistics: {e}")
        return {'total': 0, 'new_today': 0, 'updated_today': 0}


async def _get_theme_statistics(db) -> dict:
    """Get statistics about themes for logging."""
    return await run_db(_get_theme_statistics_sync, db)
