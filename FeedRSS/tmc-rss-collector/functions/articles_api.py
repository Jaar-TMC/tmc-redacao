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
        classification: str - Filtrar por classificacao de score (A, B, ou C)
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
        classification = req.params.get('classification')  # A, B, or C
        order_by = req.params.get('order_by')  # 'score' or 'newest' (default)

        # Parse max_hours for urgency filter (1-24)
        max_hours = req.params.get('max_hours')
        if max_hours:
            try:
                hours = int(max_hours)
                if 1 <= hours <= 24:
                    period = str(hours)  # Reuse period field internally
            except ValueError:
                pass

        # Debug logging
        logger.info(f"[list_articles] Received params: page={page}, limit={limit}, category={category}, source={source}, search='{search}', tag={tag}, max_hours={max_hours}, classification={classification}")

        # Validar page
        if page < 1:
            page = 1

        # Fetch articles + urgency counts in single DB connection
        db = get_db()
        articles, total, urgency_counts = db.get_articles_with_urgency(
            page=page,
            limit=limit,
            category=category,
            source_id=source,
            period=period,
            search=search,
            tag=tag,
            classification=classification,
            order_by=order_by
        )

        # Calcular total de paginas
        pages = ceil(total / limit) if total > 0 else 1

        # Converter para formato frontend
        response = {
            "items": [article.to_frontend_format() for article in articles],
            "total": total,
            "page": page,
            "pages": pages,
            "urgency_counts": urgency_counts
        }

        return func.HttpResponse(
            json.dumps(response, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:
        logger.error(f"ValueError in list_articles: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "Parâmetro inválido"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error listing articles: {e}", exc_info=True)
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
    Accepts optional filter params to return contextual counts.

    Query Parameters:
        search: str - Active search filter
        tag: str - Active tag filter
        source: str - Active source filter
        max_hours: str - Active urgency filter
    """
    try:
        db = get_db()

        # Check if contextual filters are provided
        search = req.params.get('search')
        tag = req.params.get('tag')
        source = req.params.get('source')
        max_hours = req.params.get('max_hours')

        period = None
        if max_hours:
            try:
                hours = int(max_hours)
                if 1 <= hours <= 24:
                    period = str(hours)
            except ValueError:
                pass

        has_filters = any([search, tag, source, period])

        if has_filters:
            categories = db.get_categories_filtered(
                search=search, tag=tag, source_id=source, period=period
            )
        else:
            stats = db.get_collection_stats()
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
        logger.error(f"Error getting categories: {e}", exc_info=True)
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
        logger.error(f"ValueError in get_trending_tags: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "Parâmetro inválido"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error getting trending tags: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


async def get_all_tags_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/tags

    Returns ALL unique tags with article counts, ordered by popularity.
    Use for tag filter dropdown. Accepts optional filter params for contextual counts.

    Query Parameters:
        search: str - Optional search term to filter tags
        category: str - Active category filter
        source: str - Active source filter
        max_hours: str - Active urgency filter
    """
    try:
        search = req.params.get('search')
        limit = min(int(req.params.get('limit', '100')), 200)

        # Contextual filter params
        category = req.params.get('category')
        source = req.params.get('source')
        max_hours = req.params.get('max_hours')

        period = None
        if max_hours:
            try:
                hours = int(max_hours)
                if 1 <= hours <= 24:
                    period = str(hours)
            except ValueError:
                pass

        has_filters = any([category, source, period])

        db = get_db()

        if has_filters:
            tags = db.get_all_tags_filtered(
                category=category, source_id=source, period=period, limit=limit
            )
        else:
            tags = db.get_all_tags(search=search, limit=limit)

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
