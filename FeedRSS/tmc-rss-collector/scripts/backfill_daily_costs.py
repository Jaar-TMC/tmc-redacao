"""
One-time script to backfill daily_cost_summary and daily_cost_detail
from historical llm_usage_log data.

Run after migrations 017 + 018.
Usage: python scripts/backfill_daily_costs.py
"""

import os
import sys
import logging

# Add parent directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env vars from local.settings.json (same as run_migrations.py)
import json
_settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local.settings.json")
if os.path.exists(_settings_path):
    with open(_settings_path) as _f:
        for _k, _v in json.load(_f).get("Values", {}).items():
            os.environ.setdefault(_k, str(_v))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# task_type -> action_type mapping for historical data
TASK_TYPE_MAP = {
    'article_generation': 'generate_article',
    'article_edit': 'edit_article',
    'topic_extraction': 'extract_topics',
    'tag_generation': 'generate_tags',
    'story_fusion': 'merge_topics',
    'classification': 'system_rss',
    'scoring': 'system_scoring',
    'theme_naming': 'system_clustering',
    'claim_extraction': 'generate_article',
    'source_comparison': 'generate_article',
    'cove_qa': 'generate_article',
    'cove_verdict': 'generate_article',
    'enrichment_extraction': 'generate_article',
    'scan_claim_extraction': 'fact_check_scan',
    'scan_claim_verdict': 'fact_check_scan',
    'deep_verify_claims': 'deep_verify',
    'event_extraction': 'system_rss',
    'event_verification': 'system_clustering',
}


def backfill():
    """Backfill action_type in llm_usage_log and aggregate into summary tables."""
    from services.database import get_db
    db = get_db()

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Step 1: Backfill action_type in llm_usage_log
        logger.info("Step 1: Backfilling action_type in llm_usage_log...")
        total_updated = 0
        for task_type, action_type in TASK_TYPE_MAP.items():
            cursor.execute("""
                UPDATE llm_usage_log
                SET action_type = %s
                WHERE task_type = %s AND action_type IS NULL
            """, (action_type, task_type))
            count = cursor.rowcount
            if count > 0:
                logger.info(f"  {task_type} -> {action_type}: {count} rows")
                total_updated += count

        conn.commit()
        logger.info(f"Step 1 complete: {total_updated} rows updated")

        # Step 2: Get date range
        cursor.execute("SELECT MIN(CONVERT(DATE, created_at)), MAX(CONVERT(DATE, created_at)) FROM llm_usage_log")
        row = cursor.fetchone()
        if not row or not row[0]:
            logger.warning("No data in llm_usage_log, nothing to backfill")
            return

        min_date, max_date = row[0], row[1]
        logger.info(f"Step 2: Aggregating data from {min_date} to {max_date}")

        # Step 3: Aggregate each day
        import asyncio
        from services.cost_queries import aggregate_daily_costs
        from datetime import timedelta

        async def _aggregate_all_days(start, end):
            current = start
            days_ok = 0
            while current <= end:
                result = await aggregate_daily_costs(current)
                if result.get('status') == 'ok':
                    days_ok += 1
                else:
                    logger.warning(f"  Failed to aggregate {current}: {result.get('error')}")
                current += timedelta(days=1)
            return days_ok

        days_processed = asyncio.run(_aggregate_all_days(min_date, max_date))

        logger.info(f"Step 3 complete: {days_processed} days aggregated")

        # Step 4: Summary
        cursor.execute("SELECT COUNT(*) FROM daily_cost_summary")
        summary_rows = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM daily_cost_detail")
        detail_rows = cursor.fetchone()[0]

        logger.info(f"Backfill complete: {summary_rows} summary rows, {detail_rows} detail rows")


if __name__ == '__main__':
    backfill()
