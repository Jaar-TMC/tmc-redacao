"""
API REST para artigos do usuario (materias criadas/rascunhos).
"""

import azure.functions as func
import json
import logging
from math import ceil
from uuid import UUID

from services.database import get_db
from models import UserArticleCreate, UserArticleUpdate, UserArticleListResponse

logger = logging.getLogger(__name__)


async def list_user_articles_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/user-articles

    Lista artigos do usuario com paginacao e filtros.

    Query Parameters:
        page: int - Pagina atual (default: 1)
        limit: int - Itens por pagina (default: 20, max: 100)
        status: str - 'draft' ou 'published'
        category: str - Filtrar por categoria
        search: str - Busca em titulo/conteudo
        dateRange: str - '24h', '7d', '30d', '3m', 'year'
    """
    try:
        # Parse query params
        page = int(req.params.get('page', '1'))
        limit = min(int(req.params.get('limit', '20')), 100)
        status = req.params.get('status')
        category = req.params.get('category')
        search = req.params.get('search')
        date_range = req.params.get('dateRange')

        # Validar page
        if page < 1:
            page = 1

        # Buscar artigos (scoped por user_id)
        db = get_db()
        articles, total = db.get_user_articles(
            user_id=req.user["id"],
            page=page,
            limit=limit,
            status=status,
            category=category,
            search=search,
            date_range=date_range
        )

        # Calcular total de paginas
        pages = ceil(total / limit) if total > 0 else 1

        # Converter para formato frontend
        response = {
            "items": [article.to_frontend_format() for article in articles],
            "total": total,
            "page": page,
            "pages": pages
        }

        return func.HttpResponse(
            json.dumps(response, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": f"Invalid parameter: {e}"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error listing user articles: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def get_user_article_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/user-articles/{id}

    Retorna um artigo de usuario especifico pelo ID.
    """
    try:
        article_id = req.route_params.get('id')

        if not article_id:
            return func.HttpResponse(
                json.dumps({"error": "Article ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        db = get_db()
        article = db.get_user_article_by_id(article_id, user_id=req.user["id"])

        if not article:
            return func.HttpResponse(
                json.dumps({"error": "Article not found"}),
                status_code=404,
                mimetype="application/json"
            )

        return func.HttpResponse(
            json.dumps(article.to_frontend_format(), default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting user article: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def create_user_article_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/user-articles

    Cria um novo artigo de usuario.

    Body:
        {
            "title": "Titulo da materia",
            "linhaFina": "Subtitulo (opcional)",
            "content": "Conteudo da materia...",
            "status": "draft" | "published",
            "category": "Esportes",
            "tags": ["tag1", "tag2"],
            "authorName": "Nome do Autor",
            "sourceArticleIds": ["id1", "id2"],
            "generationConfig": {...}
        }
    """
    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        # Validar campos obrigatorios
        if not body.get('title'):
            return func.HttpResponse(
                json.dumps({"error": "Title is required"}),
                status_code=400,
                mimetype="application/json"
            )

        if not body.get('content'):
            return func.HttpResponse(
                json.dumps({"error": "Content is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Criar modelo de entrada
        article_data = UserArticleCreate(
            title=body.get('title'),
            linha_fina=body.get('linhaFina'),
            content=body.get('content'),
            preview=body.get('preview'),
            status=body.get('status', 'draft'),
            category=body.get('category'),
            tags=body.get('tags', []),
            author_name=body.get('authorName'),
            source_article_ids=body.get('sourceArticleIds', []),
            generation_config=body.get('generationConfig')
        )

        # Criar no banco (com user_id do usuario autenticado)
        db = get_db()
        article = db.create_user_article(article_data, user_id=req.user["id"])

        logger.info(f"Created user article: {article.id} - {article.title[:50]}")

        return func.HttpResponse(
            json.dumps(article.to_frontend_format(), default=str),
            status_code=201,
            mimetype="application/json"
        )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": f"Validation error: {e}"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error creating user article: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def update_user_article_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    PUT /api/user-articles/{id}

    Atualiza um artigo de usuario existente (atualizacao parcial).

    Body (todos campos opcionais):
        {
            "title": "Novo titulo",
            "linhaFina": "Nova linha fina",
            "content": "Novo conteudo...",
            "status": "draft" | "published",
            "category": "Nova categoria",
            "tags": ["tag1", "tag2"],
            "authorName": "Novo autor"
        }
    """
    try:
        article_id = req.route_params.get('id')

        if not article_id:
            return func.HttpResponse(
                json.dumps({"error": "Article ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        # Criar modelo de atualizacao
        update_data = UserArticleUpdate(
            title=body.get('title'),
            linha_fina=body.get('linhaFina'),
            content=body.get('content'),
            preview=body.get('preview'),
            status=body.get('status'),
            category=body.get('category'),
            tags=body.get('tags'),
            author_name=body.get('authorName'),
            source_article_ids=body.get('sourceArticleIds'),
            generation_config=body.get('generationConfig')
        )

        # Atualizar no banco (scoped por user_id)
        db = get_db()
        article = db.update_user_article(article_id, update_data, user_id=req.user["id"])

        if not article:
            return func.HttpResponse(
                json.dumps({"error": "Article not found"}),
                status_code=404,
                mimetype="application/json"
            )

        logger.info(f"Updated user article: {article.id}")

        return func.HttpResponse(
            json.dumps(article.to_frontend_format(), default=str),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        return func.HttpResponse(
            json.dumps({"error": f"Validation error: {e}"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error updating user article: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def delete_user_article_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    DELETE /api/user-articles/{id}

    Soft delete de um artigo de usuario.
    """
    try:
        article_id = req.route_params.get('id')

        if not article_id:
            return func.HttpResponse(
                json.dumps({"error": "Article ID is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Deletar no banco (scoped por user_id)
        db = get_db()
        deleted = db.delete_user_article(article_id, user_id=req.user["id"])

        if not deleted:
            return func.HttpResponse(
                json.dumps({"error": "Article not found"}),
                status_code=404,
                mimetype="application/json"
            )

        logger.info(f"Deleted user article: {article_id}")

        return func.HttpResponse(
            json.dumps({"message": "Article deleted successfully"}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error deleting user article: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )
