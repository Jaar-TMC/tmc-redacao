"""
API REST para artigos coletados.
"""

import azure.functions as func
import json
import logging
from math import ceil
from uuid import UUID

from services.database import get_db
from models import ArticleListResponse

logger = logging.getLogger(__name__)


async def list_articles_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/articles

    Lista artigos com paginacao e filtros.

    Query Parameters:
        page: int - Pagina atual (default: 1)
        limit: int - Itens por pagina (default: 20, max: 100)
        category: str - Filtrar por categoria
        source: str - Filtrar por source_id
        period: str - 'today', 'week', 'month'
        search: str - Busca em titulo/conteudo
    """
    try:
        # Parse query params
        page = int(req.params.get('page', '1'))
        limit = min(int(req.params.get('limit', '20')), 100)
        category = req.params.get('category')
        source = req.params.get('source')
        period = req.params.get('period')
        search = req.params.get('search')

        # Validar page
        if page < 1:
            page = 1

        # Buscar artigos
        db = get_db()
        articles, total = db.get_articles(
            page=page,
            limit=limit,
            category=category,
            source_id=source,
            period=period,
            search=search
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
        logger.error(f"Error listing articles: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def get_article_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/articles/{id}

    Retorna um artigo especifico pelo ID.
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
        article = db.get_article_by_id(article_id)

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
        logger.error(f"Error getting article: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def get_categories_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/categories

    Retorna lista de categorias disponiveis com contagem de artigos.
    """
    try:
        db = get_db()
        stats = db.get_collection_stats()

        # Converter para formato de lista
        categories = [
            {"name": name, "count": count}
            for name, count in stats.get('by_category', {}).items()
        ]

        # Ordenar por contagem
        categories.sort(key=lambda x: x['count'], reverse=True)

        return func.HttpResponse(
            json.dumps({"categories": categories}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )
