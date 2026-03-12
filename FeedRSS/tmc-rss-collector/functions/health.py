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

    # Full articles flow diagnostic: ?diag=full
    diag_result = None
    if req.params.get('diag') == 'full' and db_ok:
        import traceback
        steps = {}
        try:
            # Step 1: DB query
            articles, total, urgency = db.get_articles_with_urgency(page=1, limit=5)
            steps["1_query"] = f"OK: {total} total, {len(articles)} fetched"

            # Step 2: Model serialization
            serialized = [a.to_frontend_format(list_mode=True) for a in articles]
            steps["2_serialize"] = f"OK: {len(serialized)} serialized"

            # Step 3: Facet - categories
            cat_list = db.get_categories_filtered()
            steps["3_categories"] = f"OK: {len(cat_list)} categories"

            # Step 4: Facet - tags
            tag_list = db.get_all_tags(limit=100)
            steps["4_tags"] = f"OK: {len(tag_list)} tags"

            # Step 5: JSON encode full response
            full_response = {
                "items": serialized,
                "total": total,
                "page": 1,
                "pages": 1,
                "urgency_counts": urgency,
                "facets": {"categories": cat_list, "tags": tag_list}
            }
            encoded = json.dumps(full_response, default=str)
            steps["5_json"] = f"OK: {len(encoded)} bytes"

            diag_result = {"ok": True, "steps": steps}
        except Exception as e:
            tb = traceback.format_exc()
            diag_result = {"ok": False, "steps": steps, "error": str(e), "type": type(e).__name__, "trace": tb[-800:]}

    response = {
        "status": overall_status,
    }
    if diag_result is not None:
        response["diag"] = diag_result

    return func.HttpResponse(
        json.dumps(response, default=str),
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
