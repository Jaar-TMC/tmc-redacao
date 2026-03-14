"""
AI Status API - Admin kill switch for AI operations.
GET /api/ai-status - Get current AI status (any authenticated user)
POST /api/ai-status - Pause/resume AI (admin only)
"""
import json
import logging
import azure.functions as func

logger = logging.getLogger(__name__)


async def get_ai_status_handler(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/ai-status - Returns current AI operational status."""
    try:
        from services.ai_status_service import get_ai_status_service
        service = get_ai_status_service()
        status = service.get_ai_status()

        return func.HttpResponse(
            json.dumps(status, default=str),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Erro ao consultar status da IA"}),
            status_code=500,
            mimetype="application/json"
        )


async def set_ai_status_handler(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/ai-status - Pause or resume AI operations (admin only)."""
    try:
        # Check admin role (req.user injected by @require_auth decorator)
        user = getattr(req, "user", None)
        if not user or user.get("role") != "admin":
            return func.HttpResponse(
                json.dumps({"error": "Acesso restrito a administradores"}),
                status_code=403,
                mimetype="application/json"
            )

        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "JSON inválido"}),
                status_code=400,
                mimetype="application/json"
            )

        paused = body.get("paused")
        if paused is None or not isinstance(paused, bool):
            return func.HttpResponse(
                json.dumps({"error": "Campo 'paused' (boolean) é obrigatório"}),
                status_code=400,
                mimetype="application/json"
            )

        user_email = user.get("email", "unknown")

        from services.ai_status_service import get_ai_status_service
        service = get_ai_status_service()
        success = service.set_ai_paused(paused, user_email)

        if success:
            action = "pausadas" if paused else "retomadas"
            logger.info(f"AI operations {action} by {user_email}")

            # Return updated status
            status = service.get_ai_status()
            return func.HttpResponse(
                json.dumps({
                    "message": f"Operações de IA {action} com sucesso",
                    **status
                }, default=str),
                status_code=200,
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "Falha ao atualizar status da IA"}),
                status_code=500,
                mimetype="application/json"
            )
    except Exception as e:
        logger.error(f"Error setting AI status: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Erro interno ao atualizar status da IA"}),
            status_code=500,
            mimetype="application/json"
        )
