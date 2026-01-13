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

    Verifica status do servico e conexao com banco de dados.
    """
    db = get_db()

    # Testar conexao com banco
    db_status = "connected" if db.test_connection() else "disconnected"

    response = {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "version": "1.0.0",
        "service": "tmc-rss-collector"
    }

    status_code = 200 if db_status == "connected" else 503

    return func.HttpResponse(
        json.dumps(response),
        status_code=status_code,
        mimetype="application/json"
    )


async def stats_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/stats

    Retorna estatisticas de coleta.
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
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
