"""
Shared HTTP response helpers for Azure Functions handlers.

Provides standardized JSON error and success responses used across
generation_api, fact_check_scan_api, and other handler modules.
"""

import json
import azure.functions as func


def create_error_response(message: str, status_code: int = 400, extra: dict = None) -> func.HttpResponse:
    """Create a standardized JSON error response."""
    body = {"error": message}
    if extra:
        body.update(extra)
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json"
    )


def create_success_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    """Create a standardized JSON success response."""
    return func.HttpResponse(
        json.dumps(data, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json"
    )
