"""
Edit API - Azure Functions endpoint for AI article editing.

Endpoint:
- POST /api/edit-article - Edit an existing article based on user instructions
"""

import logging
import json
from typing import Optional, List
import azure.functions as func
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Request/Response Models
class CurrentArticle(BaseModel):
    """Current article state to edit."""
    title: Optional[str] = Field(default="", description="Current title")
    titulo: Optional[str] = Field(default="", description="Current title (PT)")
    linha_fina: Optional[str] = Field(default="", description="Current subtitle")
    linhaFina: Optional[str] = Field(default="", description="Current subtitle (camelCase)")
    titulo_curto: Optional[str] = Field(default="", description="Current short title")
    content: Optional[str] = Field(default="", description="Current content")
    conteudo: Optional[str] = Field(default="", description="Current content (PT)")
    tags: List[str] = Field(default=[], description="Current tags")


class EditArticleRequest(BaseModel):
    """Request model for article editing."""
    current_article: dict = Field(..., description="Current article data (title, linha_fina, content, tags)")
    instruction: str = Field(..., min_length=3, description="User's edit instruction")
    edit_scope: str = Field(default="full", description="Scope: full|title|linha_fina|content|tags")
    categoria: Optional[str] = Field(default="geral", description="Editorial category")
    tom: Optional[str] = Field(default="conversacional", description="Writing tone")


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


async def edit_article_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Edit an existing article using AI.

    POST /api/edit-article
    Body: {
        current_article: {title, linha_fina, content, tags},
        instruction: "Melhore o SEO do título",
        edit_scope: "full"|"title"|"linha_fina"|"content"|"tags",
        categoria: "geral",
        tom: "conversacional"
    }
    Returns: {
        titulo: string,
        linha_fina: string,
        conteudo: string,
        tags: string[],
        changes_summary: string
    }
    """
    logger.info("Edit article request received")

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = EditArticleRequest(**body)
        except Exception as e:
            return create_error_response(f"Validation error: {str(e)}", 400)

        # Validate current_article has at least some content
        current = request_data.current_article
        has_content = any([
            current.get('title') or current.get('titulo'),
            current.get('linha_fina') or current.get('linhaFina'),
            current.get('content') or current.get('conteudo')
        ])

        if not has_content:
            return create_error_response(
                "current_article must have at least title, linha_fina, or content",
                400
            )

        # Validate edit_scope
        valid_scopes = ['full', 'title', 'linha_fina', 'content', 'tags']
        if request_data.edit_scope not in valid_scopes:
            return create_error_response(
                f"edit_scope must be one of: {', '.join(valid_scopes)}",
                400
            )

        # Import LLM service (lazy import to avoid startup issues)
        from services.llm_service import get_llm_service

        try:
            llm = get_llm_service()
        except ValueError as e:
            logger.error(f"LLM service not configured: {e}")
            return create_error_response(
                "AI service not configured. Please set AZURE_AI_API_KEY or ANTHROPIC_API_KEY.",
                503
            )

        # Edit article
        result = await llm.edit_article(
            current_article=request_data.current_article,
            instruction=request_data.instruction,
            edit_scope=request_data.edit_scope,
            categoria=request_data.categoria,
            tom=request_data.tom
        )

        # Ensure titulo_curto is present in response
        if "titulo_curto" not in result:
            result["titulo_curto"] = result.get("titulo_curto", "")

        logger.info(f"Article edited successfully: {result.get('changes_summary', 'No summary')}")
        return create_success_response(result)

    except RuntimeError as e:
        logger.error(f"AI service error: {e}")
        return create_error_response(f"AI service error: {str(e)}", 503)
    except ValueError as e:
        logger.error(f"Invalid response from AI: {e}")
        return create_error_response(f"Invalid AI response: {str(e)}", 500)
    except Exception as e:
        logger.exception(f"Unexpected error in edit_article: {e}")
        return create_error_response("Internal server error", 500)


def edit_article_sync(req: func.HttpRequest) -> func.HttpResponse:
    """Sync wrapper for edit_article_handler."""
    import asyncio
    return asyncio.run(edit_article_handler(req))
