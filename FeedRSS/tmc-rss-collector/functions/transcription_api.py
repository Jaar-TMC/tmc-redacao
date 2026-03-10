"""
Transcription API - Azure Functions endpoint for YouTube caption transcription.

Endpoint:
- POST /api/transcribe - Fetch YouTube captions for a video URL
"""

import logging
import json
import re

import azure.functions as func
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)


# Prompt Injection Defense Patterns (shared with generation_api.py)
_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(?:all\s+)?(?:previous\s+|acima\s+)?instru[cç][oõ]es', re.IGNORECASE),
    re.compile(r'voc[eê]\s+(?:e|é)\s+agora\s+(?:um|uma)', re.IGNORECASE),
    re.compile(r'you\s+are\s+now\s+a', re.IGNORECASE),
    re.compile(r'<\s*/?system', re.IGNORECASE),
    re.compile(r'INSTRUC[AÃ]O\s*:', re.IGNORECASE),
    re.compile(r'Human\s*:', re.IGNORECASE),
    re.compile(r'Assistant\s*:', re.IGNORECASE),
    re.compile(r'\[INST\]', re.IGNORECASE),
    re.compile(r'<<SYS>>', re.IGNORECASE),
    re.compile(r'esquec[ea]\s+tudo', re.IGNORECASE),
    re.compile(r'sua\s+nova\s+tarefa', re.IGNORECASE),
    re.compile(r'responda\s+apenas\s+com', re.IGNORECASE),
    re.compile(r'nao\s+siga\s+as\s+regras', re.IGNORECASE),
    re.compile(r'<!--.*?-->', re.IGNORECASE | re.DOTALL),
    re.compile(r'nova\s+instru[cç][aã]o', re.IGNORECASE),
]


# Request Model
class TranscribeRequest(BaseModel):
    """Request model for YouTube transcription."""
    url: str = Field(..., min_length=10, max_length=500)
    languages: Optional[list[str]] = Field(None, max_length=5)
    segment_duration: float = Field(default=45.0, ge=15.0, le=120.0)


def _check_injection(text: str) -> bool:
    """Check if text contains prompt injection patterns. Returns True if injection detected."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def create_error_response(message: str, status_code: int = 400, details: str = None) -> func.HttpResponse:
    """Create a standardized error response."""
    body = {"error": message}
    if details:
        body["details"] = details
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False),
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


async def transcribe_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Fetch YouTube captions for a video URL.

    POST /api/transcribe
    Body: {
        url: "https://www.youtube.com/watch?v=VIDEO_ID",
        languages: ["pt", "en"],       // optional
        segment_duration: 45.0          // optional, seconds per merged segment
    }
    Returns: {
        video: { videoId, url, title, channel, thumbnail },
        transcription: [ { id, startTime, endTime, text, topic } ],
        metadata: { language, total_segments, total_duration_seconds, caption_type }
    }
    """
    logger.info("Transcribe request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = TranscribeRequest(**body)
        except Exception as e:
            logger.warning(f"Transcribe request validation error: {e}")
            return create_error_response("Erro de validação nos dados enviados.", 400)

        # Check for prompt injection in URL field
        if _check_injection(request_data.url):
            logger.warning(f"Injection pattern detected in transcribe URL")
            return create_error_response("Entrada inválida.", 400)

        # Import service (lazy to avoid startup issues)
        from services.youtube_service import (
            YouTubeService,
            VideoNotFoundError,
            CaptionsNotAvailableError,
            TranscriptionServiceError,
        )

        # Extract video ID
        video_id = YouTubeService.extract_video_id(request_data.url)
        if not video_id:
            logger.warning(f"Invalid YouTube URL: {request_data.url[:100]}")
            return create_error_response(
                "URL inválida. Forneça um link válido do YouTube.",
                400
            )

        logger.info(f"Processing transcription for video_id={video_id}")

        # Fetch metadata
        try:
            video_metadata = await YouTubeService.get_video_metadata(video_id)
        except VideoNotFoundError as e:
            logger.info(f"Video not found: {video_id}")
            return create_error_response(str(e), 404)

        logger.info(f"Video metadata fetched: {video_metadata.get('title', 'N/A')[:80]}")

        # Note: contentDetails.caption from YouTube Data API is unreliable
        # for auto-generated captions, so we always attempt the fetch.

        # Fetch captions
        try:
            captions_result = await YouTubeService.get_captions(
                video_id,
                languages=request_data.languages,
                target_duration=request_data.segment_duration,
            )
        except CaptionsNotAvailableError as e:
            logger.info(f"Captions not available for video {video_id}: {e}")
            return create_error_response(
                str(e),
                422,
                details="Este vídeo não possui legendas nos idiomas suportados."
            )
        except VideoNotFoundError as e:
            logger.info(f"Video unavailable during caption fetch: {video_id}")
            return create_error_response(str(e), 404)
        except TranscriptionServiceError as e:
            error_msg = str(e)
            logger.warning(f"Transcription service error for video {video_id}: {error_msg}")
            # YouTube blocking/rate-limiting → 503 (retryable)
            if "bloqueou" in error_msg or "limitou" in error_msg:
                return create_error_response(
                    error_msg, 503,
                    details="O YouTube está temporariamente limitando as requisições. "
                            "Tente novamente em alguns minutos."
                )
            return create_error_response(error_msg, 502)

        segments = captions_result["segments"]
        total_segments = len(segments)

        logger.info(
            f"Transcription complete for video_id={video_id}: "
            f"{total_segments} segments, "
            f"language={captions_result['language']}, "
            f"type={captions_result['caption_type']}"
        )

        # Build response
        response = {
            "video": video_metadata,
            "transcription": segments,
            "metadata": {
                "language": captions_result["language"],
                "total_segments": total_segments,
                "total_duration_seconds": captions_result["total_duration_seconds"],
                "caption_type": captions_result["caption_type"],
            },
        }

        return create_success_response(response)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.exception(f"Unexpected error in transcribe_handler: {e}")
        return create_error_response(
            "Erro interno ao processar transcrição.",
            500,
            details=f"{type(e).__name__}: {str(e)}\n{tb[-1500:]}"
        )
