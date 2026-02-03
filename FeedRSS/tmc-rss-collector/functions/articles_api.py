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
        tag: str - Filtrar por tag exata
    """
    try:
        # Parse query params
        page = int(req.params.get('page', '1'))
        limit = min(int(req.params.get('limit', '20')), 100)
        category = req.params.get('category')
        source = req.params.get('source')
        period = req.params.get('period')
        search = req.params.get('search')
        tag = req.params.get('tag')

        # Debug logging
        logger.info(f"[list_articles] Received params: page={page}, limit={limit}, category={category}, source={source}, search='{search}', tag={tag}")

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
            search=search,
            tag=tag
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


async def get_trending_tags_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/trending-tags

    Returns trending tags with distinct article counts from ALL articles in the database.
    This is the source of truth for "Feed em Alta" / "Temas Quentes".

    Query Parameters:
        limit: int - Maximum tags to return (default: 20, max: 50)
        period: int - Optional filter for articles within last N hours
    """
    try:
        # Parse query params
        limit = min(int(req.params.get('limit', '20')), 50)
        period = req.params.get('period')

        # Convert period to hours if provided
        period_hours = None
        if period:
            period_hours = int(period)

        # Get trending tags from database
        db = get_db()
        tags = db.get_trending_tags(limit=limit, period_hours=period_hours)

        # Format response with proper display names
        items = []
        for i, tag_data in enumerate(tags):
            tag = tag_data['tag']
            # Capitalize first letter of each word (for display)
            display_name = ' '.join(
                word.capitalize() for word in tag.replace('-', ' ').split()
            )
            items.append({
                "id": i + 1,
                "theme": display_name,
                "tag": tag,  # Original lowercase tag for filtering
                "count": tag_data['count'],
                "trend": "stable"  # Could be calculated comparing to previous period
            })

        return func.HttpResponse(
            json.dumps({"items": items, "total": len(items)}),
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
        logger.error(f"Error getting trending tags: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def get_all_tags_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/tags

    Returns ALL unique tags with article counts, ordered by popularity.
    Use for tag filter dropdown.

    Query Parameters:
        search: str - Optional search term to filter tags
    """
    try:
        search = req.params.get('search')

        db = get_db()
        tags = db.get_all_tags(search=search)

        # Format response
        items = []
        for i, tag_data in enumerate(tags):
            items.append({
                "id": i + 1,
                "theme": tag_data['theme'],
                "tag": tag_data['tag'],
                "count": tag_data['count']
            })

        return func.HttpResponse(
            json.dumps({"items": items, "total": len(items)}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error getting all tags: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )
