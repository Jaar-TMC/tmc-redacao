"""
Keep-alive handler to prevent Azure Functions cold starts.
Runs every 4 minutes -- performs a minimal DB health check to keep
both the Functions instance and the DB connection pool warm.
"""

import azure.functions as func
import logging
import time

from services.database import get_db
from services.async_db import run_db

logger = logging.getLogger(__name__)


async def keepalive_handler(timer: func.TimerRequest) -> None:
    """Lightweight ping to keep Functions instance warm."""
    start = time.time()

    try:
        # Warm the DB connection pool with a trivial SELECT 1 query
        db = get_db()
        await run_db(db.test_connection)
        elapsed = (time.time() - start) * 1000
        logger.info(f"[keepalive] OK -- DB pool warm ({elapsed:.0f}ms)")
    except Exception as e:
        logger.warning(f"[keepalive] DB check failed (non-critical): {e}")
