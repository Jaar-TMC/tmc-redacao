"""
Health check e estatisticas da API.
"""

import azure.functions as func
import json
import logging
from datetime import datetime

from services.database import get_db

logger = logging.getLogger(__name__)


async def health_check_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/health

    Public health check - returns only status without internal details.
    Returns: ok | degraded
    """
    try:
        db = get_db()
        db_ok = db.test_connection()
    except Exception:
        db_ok = False

    if not db_ok:
        overall_status = "degraded"
        status_code = 503
    else:
        overall_status = "ok"
        status_code = 200

    response = {
        "status": overall_status,
    }

    return func.HttpResponse(
        json.dumps(response),
        status_code=status_code,
        mimetype="application/json"
    )


async def stats_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/stats

    Retorna estatisticas de coleta. Requires admin auth.
    """
    try:
        db = get_db()
        stats = db.get_collection_stats()

        return func.HttpResponse(
            json.dumps(stats),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Erro interno ao buscar estatisticas"}),
            status_code=500,
            mimetype="application/json"
        )
