"""
Timer Trigger para clustering semantico de artigos em temas.
Executa a cada 30 minutos para agrupar artigos com embeddings em temas.
"""

import azure.functions as func
import logging
from datetime import datetime

from services.database import get_db
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

    # Check if clustering is enabled
    if not is_clustering_enabled():
        logger.info(f"[{execution_id}] Clustering is disabled via CLUSTERING_ENABLED env var")
        return

    db = get_db()

    # Verify database connection
    if not db.test_connection():
        logger.error(f"[{execution_id}] Database connection failed")
        return

    try:
        # Initialize clustering service with database
        clustering_service = get_clustering_service(db_service=db)

        # Get count of pending articles before processing
        pending_articles = db.get_articles_pending_clustering(limit=MAX_ARTICLES_PER_RUN)
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


async def _get_theme_statistics(db) -> dict:
    """
    Get statistics about themes for logging.

    Args:
        db: DatabaseService instance

    Returns:
        Dict with theme statistics
    """
    query_total = """
        SELECT COUNT(*) FROM themes WHERE status = 'active'
    """

    query_new = """
        SELECT COUNT(*) FROM themes
        WHERE status = 'active'
        AND first_seen_at >= DATEADD(day, -1, GETUTCDATE())
    """

    query_updated = """
        SELECT COUNT(*) FROM themes
        WHERE status = 'active'
        AND last_updated_at >= DATEADD(day, -1, GETUTCDATE())
        AND last_updated_at > first_seen_at
    """

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(query_total)
            total = cursor.fetchone()[0]

            cursor.execute(query_new)
            new_today = cursor.fetchone()[0]

            cursor.execute(query_updated)
            updated_today = cursor.fetchone()[0]

            return {
                'total': total,
                'new_today': new_today,
                'updated_today': updated_today
            }
    except Exception as e:
        logger.warning(f"Error getting theme statistics: {e}")
        return {'total': 0, 'new_today': 0, 'updated_today': 0}
