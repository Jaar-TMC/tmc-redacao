"""
Authentication decorators for Azure Functions HTTP handlers.
Stack with @with_cors: @with_cors @require_auth async def handler(req): ...
"""
import asyncio
import json
import logging
import os
from functools import wraps
from typing import Optional

import azure.functions as func

from services.auth_service import decode_token

logger = logging.getLogger(__name__)

_PRODUCTION_SAFETY_MODE = os.environ.get("PRODUCTION_SAFETY_MODE", "true").lower() == "true"


async def get_current_user(req: func.HttpRequest) -> Optional[dict]:
    """Extract and validate JWT from Authorization header.
    Returns user dict {id, email, role, name} or None.

    This is async because it checks the token blacklist via a synchronous
    DB call that is offloaded to a thread pool to avoid blocking the event loop.
    """
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    payload = decode_token(token)
    if not payload:
        return None

    if payload.get("type") != "access":
        return None

    # Check token blacklist
    jti = payload.get("jti")
    if jti:
        try:
            from services.database import get_db
            db = get_db()
            if await asyncio.to_thread(db.is_token_blacklisted, jti):
                return None
        except Exception as e:
            logger.warning(f"Could not check token blacklist: {e}")
            # Always fail-closed: deny access when blacklist cannot be checked
            return None

    return {
        "id": payload["sub"],
        "email": payload.get("email", ""),
        "role": payload.get("role", "user"),
        "name": payload.get("name", ""),
        "jti": jti,
    }


def require_auth(handler):
    """Decorator: requires valid JWT. Injects req.user."""
    @wraps(handler)
    async def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        # Skip auth check for OPTIONS (CORS preflight)
        if req.method == "OPTIONS":
            return await handler(req)

        user = await get_current_user(req)
        if not user:
            return func.HttpResponse(
                json.dumps({"error": "Authentication required"}),
                status_code=401,
                mimetype="application/json",
            )
        req.user = user
        return await handler(req)
    return wrapper


def require_admin(handler):
    """Decorator: requires valid JWT with role='admin'."""
    @wraps(handler)
    async def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        if req.method == "OPTIONS":
            return await handler(req)

        user = await get_current_user(req)
        if not user:
            return func.HttpResponse(
                json.dumps({"error": "Authentication required"}),
                status_code=401,
                mimetype="application/json",
            )
        if user["role"] != "admin":
            return func.HttpResponse(
                json.dumps({"error": "Admin access required"}),
                status_code=403,
                mimetype="application/json",
            )
        req.user = user
        return await handler(req)
    return wrapper
