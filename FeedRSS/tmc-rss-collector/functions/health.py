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

    Verifica status do servico, banco de dados, e circuit breakers.
    Returns: healthy | degraded | unhealthy
    """
    try:
        db = get_db()
        db_status = "connected" if db.test_connection() else "disconnected"
    except Exception:
        db_status = "disconnected"

    # Phase 4.5: Check LLM and Exa circuit breaker status
    llm_status = "unknown"
    exa_status = "unknown"
    try:
        from services.llm_service import _llm_service
        if _llm_service is not None:
            if _llm_service._llm_circuit_open:
                llm_status = "circuit_open"
            else:
                llm_status = "ok"
        else:
            llm_status = "not_initialized"
    except Exception:
        llm_status = "error"

    try:
        from services.fact_check_service import _fact_check_service
        if _fact_check_service is not None:
            if _fact_check_service._exa_circuit_open:
                exa_status = "circuit_open"
            else:
                exa_status = "ok"
        else:
            exa_status = "not_initialized"
    except Exception:
        exa_status = "error"

    # Determine overall status
    if db_status == "disconnected":
        overall_status = "unhealthy"
        status_code = 503
    elif llm_status == "circuit_open" or exa_status == "circuit_open":
        overall_status = "degraded"
        status_code = 200
    else:
        overall_status = "healthy"
        status_code = 200

    # Feature flag status for operational visibility
    feature_flags = {}
    try:
        from services.config import get_config
        cfg = get_config()
        feature_flags = {
            "production_safety_mode": cfg.production_safety_mode,
            "fact_check_enabled": cfg.fact_check_enabled,
            "enrichment_enabled": cfg.fact_check_enrichment_enabled,
            "verification_enabled": cfg.fact_check_verification_enabled,
            "decontamination_enabled": cfg.decontamination_enabled,
        }
    except Exception:
        feature_flags = {"error": "Failed to load config"}

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "llm_service": llm_status,
        "exa_enrichment": exa_status,
        "feature_flags": feature_flags,
        "version": "7.0.0",
        "service": "tmc-rss-collector"
    }

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
