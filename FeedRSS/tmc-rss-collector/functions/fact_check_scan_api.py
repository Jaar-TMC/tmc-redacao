"""
Fact-Check Scan API — on-demand article safety verification.

Endpoints:
- POST /api/fact-check-scan - Scan article text for factual accuracy
- POST /api/fact-check-deep-verify - Deep verify unverifiable claims from a scan
"""

import hashlib
import json
import logging
import os
import uuid
import time
from pydantic import BaseModel, Field

import azure.functions as func

logger = logging.getLogger(__name__)


class FactCheckScanRequest(BaseModel):
    """Request model for fact-check scanning."""
    article_text: str = Field(..., min_length=100, max_length=15000)
    article_title: str = Field(default="")
    source_urls: list = Field(default_factory=list)
    source_text: str = Field(default="")
    user_article_id: str = Field(default="")
    language: str = Field(default="pt")


def create_error_response(message: str, status_code: int = 400) -> func.HttpResponse:
    """Create a standardized error response."""
    return func.HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json"
    )


def create_success_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    """Create a standardized success response."""
    return func.HttpResponse(
        json.dumps(data, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json"
    )


async def fact_check_scan_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    On-demand article safety scan.

    POST /api/fact-check-scan
    Body: {
        article_text: "...",           (required, 100-15000 chars)
        article_title: "...",          (optional)
        source_urls: ["..."],          (optional)
        source_text: "...",            (optional)
        user_article_id: "...",        (optional)
        language: "pt"                 (optional, default "pt")
    }
    Returns: FactCheckScanResponse with ASI score and claim analysis
    """
    logger.info("Fact-check scan request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = FactCheckScanRequest(**body)
        except Exception as e:
            logger.warning(f"Validation error: {e}")
            return create_error_response(
                "Erro de validacao: article_text deve ter entre 100 e 15000 caracteres",
                400,
            )

        # Check feature flag
        if os.environ.get("FACT_CHECK_SCAN_ENABLED", "true").lower() != "true":
            return create_error_response(
                "Verificacao de seguranca temporariamente desabilitada", 503
            )

        # Compute text hash for caching
        article_text_hash = hashlib.sha256(
            request_data.article_text.encode("utf-8")
        ).hexdigest()

        # Check cache (skip cached results with 0 claims — likely failed extractions)
        from services.database import get_db
        cached = get_db().get_latest_scan(article_text_hash)
        if cached and cached.get("scan_result") and cached.get("total_claims", 0) > 0:
            logger.info(f"Cache hit for scan hash {article_text_hash[:16]}")
            # Return cached scan_result directly
            result = cached["scan_result"]
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    pass
            if isinstance(result, dict):
                result["cached"] = True
                return create_success_response(result)

        # Run scan
        correlation_id = str(uuid.uuid4())[:8]
        start_ms = time.time()

        from services.article_safety_service import get_article_safety_service

        try:
            service = get_article_safety_service()
        except Exception as e:
            logger.error(f"Article safety service not available: {e}")
            return create_error_response(
                "Servico de verificacao nao configurado", 503
            )

        scan_result = await service.scan(
            article_text=request_data.article_text,
            article_title=request_data.article_title,
            source_urls=request_data.source_urls,
            source_text=request_data.source_text,
            language=request_data.language,
            correlation_id=correlation_id,
        )

        duration_ms = int((time.time() - start_ms) * 1000)
        result_dict = scan_result.model_dump()

        # Fire-and-forget: insert scan record
        try:
            user_id = getattr(req, 'user', {}).get('id') if hasattr(req, 'user') else None
            get_db().insert_fact_check_scan({
                "scan_id": correlation_id,
                "user_id": user_id,
                "user_article_id": int(request_data.user_article_id) if request_data.user_article_id else None,
                "article_text_hash": article_text_hash,
                "article_char_count": len(request_data.article_text),
                "safety_index": scan_result.safety_index,
                "safety_label": scan_result.safety_label,
                "total_claims": scan_result.total_claims,
                "grounded_claims": scan_result.grounded_claims,
                "fabricated_claims": scan_result.fabricated_claims,
                "unverifiable_claims": scan_result.unverifiable_claims,
                "corroboration_score": scan_result.corroboration_score,
                "external_factcheck_matches": scan_result.fact_check_matches,
                "scan_result": result_dict,
                "scan_duration_ms": duration_ms,
            })
        except Exception as e:
            logger.warning(f"Failed to log scan (non-blocking): {e}")

        logger.info(
            f"Scan {correlation_id} complete: ASI={scan_result.safety_index} "
            f"({scan_result.safety_label}), {duration_ms}ms"
        )

        return create_success_response(result_dict)

    except Exception as e:
        logger.exception(f"Unexpected error in fact_check_scan: {e}")
        return create_error_response("Internal server error", 500)


async def deep_verify_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Deep verify unverifiable claims from a fact-check scan.

    POST /api/fact-check-deep-verify
    Body: {
        claims: [...],          (required - array of claim objects from scan result)
        article_title: "...",   (optional)
        language: "pt"          (optional)
    }
    Returns: { updated_claims, sources_searched, claims_resolved, deep_verify_duration_ms }
    """
    logger.info("Deep verify request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate claims array
        claims = body.get("claims")
        if not claims or not isinstance(claims, list):
            return create_error_response(
                "Erro de validacao: 'claims' deve ser uma lista nao vazia de afirmacoes",
                400,
            )
        if len(claims) > 50:
            claims = claims[:50]

        article_title = str(body.get("article_title", ""))[:500]
        language = str(body.get("language", "pt"))[:5]

        # Check feature flag
        if os.environ.get("FACT_CHECK_SCAN_ENABLED", "true").lower() != "true":
            return create_error_response(
                "Verificacao de seguranca temporariamente desabilitada", 503
            )

        correlation_id = str(uuid.uuid4())[:8]

        from services.article_safety_service import get_article_safety_service

        try:
            service = get_article_safety_service()
        except Exception as e:
            logger.error(f"Article safety service not available: {e}")
            return create_error_response(
                "Servico de verificacao nao configurado", 503
            )

        result = await service.deep_verify(
            claims=claims,
            article_title=article_title,
            language=language,
            correlation_id=correlation_id,
        )

        logger.info(
            f"Deep verify {correlation_id} complete: "
            f"{result['claims_resolved']} resolved, {result['deep_verify_duration_ms']}ms"
        )

        return create_success_response(result)

    except Exception as e:
        logger.exception(f"Unexpected error in deep_verify: {e}")
        return create_error_response("Internal server error", 500)
