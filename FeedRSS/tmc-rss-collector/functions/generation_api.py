"""
Generation API - Azure Functions endpoints for AI article generation.

Endpoints:
- POST /api/generate - Generate article from source text
- POST /api/extract-topics - Extract topics from text
- POST /api/generate-tags - Generate tags for content
"""

import logging
import json
from typing import Optional
import azure.functions as func
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Request/Response Models
class GenerateRequest(BaseModel):
    """Request model for article generation."""
    texto_base: str = Field(..., min_length=100, description="Source text content")
    persona: str = Field(default="imparcial", description="Writer persona")
    tom: str = Field(default="formal", description="Writing tone")
    tipo_materia: str = Field(default="destaque", description="Article type")
    orientacao_lide: Optional[str] = Field(default=None, description="Lead guidance")
    citacoes: Optional[list] = Field(default=None, description="Quotes to include")
    contexto: Optional[str] = Field(default=None, description="Background context")
    creditos: Optional[str] = Field(default=None, description="Source credits")
    tags: Optional[list] = Field(default=None, description="Tags for SEO")


class ExtractTopicsRequest(BaseModel):
    """Request model for topic extraction."""
    texto: str = Field(..., min_length=50, description="Text to analyze")


class GenerateTagsRequest(BaseModel):
    """Request model for tag generation."""
    texto: str = Field(..., min_length=50, description="Content to analyze")
    max_tags: int = Field(default=10, ge=1, le=20, description="Maximum tags")


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


# Azure Function Handlers

async def generate_article_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate article using AI.

    POST /api/generate
    Body: GenerateRequest JSON
    Returns: {titulo, linha_fina, conteudo, tags_sugeridas}
    """
    logger.info("Generate article request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = GenerateRequest(**body)
        except Exception as e:
            return create_error_response(f"Validation error: {str(e)}", 400)

        # Import LLM service (lazy import to avoid startup issues)
        from services.llm_service import get_llm_service

        try:
            llm = get_llm_service()
        except ValueError as e:
            logger.error(f"LLM service not configured: {e}")
            return create_error_response(
                "AI service not configured. Please set ANTHROPIC_API_KEY.",
                503
            )

        # Generate article
        result = await llm.generate_article(
            texto_base=request_data.texto_base,
            persona=request_data.persona,
            tom=request_data.tom,
            tipo_materia=request_data.tipo_materia,
            orientacao_lide=request_data.orientacao_lide,
            citacoes=request_data.citacoes,
            contexto=request_data.contexto,
            creditos=request_data.creditos,
            tags=request_data.tags
        )

        logger.info("Article generated successfully")
        return create_success_response(result)

    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        return create_error_response(f"AI service error: {str(e)}", 503)
    except ValueError as e:
        logger.error(f"Invalid response from AI: {e}")
        return create_error_response(f"Invalid AI response: {str(e)}", 500)
    except Exception as e:
        logger.exception(f"Unexpected error in generate_article: {e}")
        return create_error_response("Internal server error", 500)


async def extract_topics_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Extract topics from text using AI.

    POST /api/extract-topics
    Body: {texto: string}
    Returns: {topics: [{type, content}, ...]}
    """
    logger.info("Extract topics request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = ExtractTopicsRequest(**body)
        except Exception as e:
            return create_error_response(f"Validation error: {str(e)}", 400)

        # Import LLM service
        from services.llm_service import get_llm_service

        try:
            llm = get_llm_service()
        except ValueError as e:
            return create_error_response(
                "AI service not configured. Please set ANTHROPIC_API_KEY.",
                503
            )

        # Extract topics
        topics = await llm.extract_topics(request_data.texto)

        return create_success_response({"topics": topics})

    except Exception as e:
        logger.exception(f"Error in extract_topics: {e}")
        return create_error_response("Internal server error", 500)


async def generate_tags_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate tags for content using AI.

    POST /api/generate-tags
    Body: {texto: string, max_tags?: number}
    Returns: {tags: [string, ...]}
    """
    logger.info("Generate tags request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = GenerateTagsRequest(**body)
        except Exception as e:
            return create_error_response(f"Validation error: {str(e)}", 400)

        # Import LLM service
        from services.llm_service import get_llm_service

        try:
            llm = get_llm_service()
        except ValueError as e:
            return create_error_response(
                "AI service not configured. Please set ANTHROPIC_API_KEY.",
                503
            )

        # Generate tags
        tags = await llm.generate_tags(request_data.texto, request_data.max_tags)

        return create_success_response({"tags": tags})

    except Exception as e:
        logger.exception(f"Error in generate_tags: {e}")
        return create_error_response("Internal server error", 500)


# Synchronous wrappers for Azure Functions (if needed)

def generate_article_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync wrapper for generate_article_handler."""
    import asyncio
    return asyncio.run(generate_article_handler(req))


def extract_topics_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync wrapper for extract_topics_handler."""
    import asyncio
    return asyncio.run(extract_topics_handler(req))


def generate_tags_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync wrapper for generate_tags_handler."""
    import asyncio
    return asyncio.run(generate_tags_handler(req))
