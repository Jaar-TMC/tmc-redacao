"""
Timer Trigger para calculo de scores editoriais de artigos.
Executa a cada 10 minutos para classificar artigos em A/B/C.
"""

import azure.functions as func
import logging
from datetime import datetime
from collections import Counter

from services.database import get_db
from services.scoring_service import get_scoring_service

logger = logging.getLogger(__name__)

# Configuration
# Aumentado de 20 para 50 para processar backlog mais rápido (~300 artigos/hora)
MAX_ARTICLES_PER_RUN = 50


async def scoring_calculator_handler(timer: func.TimerRequest) -> None:
    """
    Handler principal do timer trigger para calculo de scores.
    Executa a cada 10 minutos para processar artigos sem scores.

    Scoring System (4 Signals):
    - inesperado (Unexpected): Is this news surprising?
    - impacto (Impact): Does it affect the reader's life?
    - busca_agora (Search Now): Will readers search for this?
    - conversa (Conversation): Will readers discuss this?

    Classification:
    - A: total_score >= 75 (High priority)
    - B: total_score 40-74 (Medium priority)
    - C: total_score < 40 (Low priority)

    Flow:
    1. Get articles without scores from database
    2. Analyze each article using Claude AI (with heuristic fallback)
    3. Calculate scores and classification
    4. Save to database
    5. Log classification distribution
    """
    start_time = datetime.utcnow()
    execution_id = start_time.strftime('%Y%m%d_%H%M%S')

    logger.info(f"[{execution_id}] Scoring Calculator started")

    db = get_db()

    # Verify database connection
    if not db.test_connection():
        logger.error(f"[{execution_id}] Database connection failed")
        return

    try:
        # Initialize scoring service
        scoring_service = get_scoring_service()

        # Process pending articles
        processed = await scoring_service.process_pending_articles(
            limit=MAX_ARTICLES_PER_RUN,
            use_heuristic_fallback=True
        )

        if processed == 0:
            logger.info(f"[{execution_id}] No articles pending scoring")
            return

        # Update theme scores for themes with recently scored articles
        themes_updated = await _update_affected_theme_scores(db)
        logger.info(f"[{execution_id}] Updated scores for {themes_updated} themes")

        # Get classification distribution for logging
        distribution = await _get_recent_classification_distribution(db, hours=1)

        # Log results
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"[{execution_id}] Scoring Calculator finished: "
            f"{processed} articles scored, {themes_updated} themes updated, "
            f"distribution (last 1h): A={distribution.get('A', 0)}, "
            f"B={distribution.get('B', 0)}, C={distribution.get('C', 0)}, "
            f"{duration:.2f}s"
        )

    except Exception as e:
        logger.error(f"[{execution_id}] Scoring Calculator error: {e}")
        raise


async def _update_affected_theme_scores(db) -> int:
    """
    Update scores for themes that have recently scored articles.
    Uses batch SQL UPDATE for efficiency.

    Returns:
        Number of themes updated
    """
    update_query = """
        UPDATE t
        SET
            t.avg_score = scores.avg_score,
            t.max_score = scores.max_score,
            t.min_score = scores.min_score,
            t.classification = CASE
                WHEN scores.avg_score >= 75 THEN 'A'
                WHEN scores.avg_score >= 40 THEN 'B'
                ELSE 'C'
            END,
            t.last_updated_at = GETUTCDATE()
        FROM themes t
        INNER JOIN (
            SELECT
                at.theme_id,
                AVG(CAST(s.total_score AS FLOAT)) as avg_score,
                MAX(s.total_score) as max_score,
                MIN(s.total_score) as min_score
            FROM article_themes at
            INNER JOIN article_scores s ON at.article_id = s.article_id
            GROUP BY at.theme_id
        ) scores ON t.id = scores.theme_id
        WHERE t.status = 'active'
    """

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(update_query)
            updated = cursor.rowcount
            conn.commit()
            return updated
    except Exception as e:
        logger.warning(f"Error updating theme scores: {e}")
        return 0


async def _get_recent_classification_distribution(db, hours: int = 1) -> dict:
    """
    Get classification distribution for recently scored articles.

    Args:
        db: DatabaseService instance
        hours: Number of hours to look back

    Returns:
        Dict with counts per classification {'A': N, 'B': N, 'C': N}
    """
    query = """
        SELECT classification, COUNT(*) as count
        FROM article_scores
        WHERE scored_at >= DATEADD(hour, -%s, GETUTCDATE())
        GROUP BY classification
    """

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (hours,))
            rows = cursor.fetchall()

            return {row[0]: row[1] for row in rows if row[0]}
    except Exception as e:
        logger.warning(f"Error getting classification distribution: {e}")
        return {}
