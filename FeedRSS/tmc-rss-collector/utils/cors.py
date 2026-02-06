"""
CORS utilities for Azure Functions.
"""

import azure.functions as func
import json

# Allowed origins for CORS
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://purple-river-09235a310.azurestaticapps.net",
    "https://purple-river-09235a310.3.azurestaticapps.net",
]


def get_cors_headers(origin: str = None) -> dict:
    """Get CORS headers for response."""
    # Check if origin is allowed
    if origin and origin in ALLOWED_ORIGINS:
        allowed_origin = origin
    else:
        allowed_origin = ALLOWED_ORIGINS[0]  # Default to localhost

    return {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Allow-Credentials": "true",
    }


def create_response(
    body: dict,
    status_code: int = 200,
    origin: str = None
) -> func.HttpResponse:
    """Create HTTP response with CORS headers."""
    headers = get_cors_headers(origin)
    headers["Content-Type"] = "application/json"

    return func.HttpResponse(
        json.dumps(body, default=str, ensure_ascii=False),
        status_code=status_code,
        headers=headers
    )


def create_error_response(
    message: str,
    status_code: int = 400,
    origin: str = None
) -> func.HttpResponse:
    """Create error response with CORS headers."""
    return create_response({"error": message}, status_code, origin)


def create_options_response(origin: str = None) -> func.HttpResponse:
    """Create preflight OPTIONS response."""
    headers = get_cors_headers(origin)
    return func.HttpResponse(
        "",
        status_code=204,
        headers=headers
    )
