"""
API REST para artigos coletados.
"""

import azure.functions as func
import json
import logging
import time
from math import ceil
from uuid import UUID

from services.database import get_db
from services.async_db import run_db
from models import ArticleListResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory facet cache (5-min TTL)
# Categories and tags only change when new articles are collected (every 15 min).
# Caching avoids expensive CROSS APPLY OPENJSON() on every /api/articles request.
# ---------------------------------------------------------------------------
_facet_cache = {
    "categories": None,
    "tags": None,
    "timestamp": 0,
    "filter_key": None,  # cache is keyed on active filters
}
FACET_CACHE_TTL = 300  # seconds


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
        skip_facets = req.params.get('skip_facets', '').lower() == 'true'

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
        articles, total, urgency_counts = await run_db(
            db.get_articles_with_urgency,
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

        # Compute facets for filter dropdowns (avoids separate API calls)
        # Skip facet computation when client signals it doesn't need updated facets
        # (e.g., pagination-only requests where filters haven't changed)
        facets = None
        if skip_facets:
            logger.info("[list_articles] Skipping facet computation (skip_facets=true)")
        else:
            try:
                # Build a cache key from the active filter combination so that
                # different filter sets don't return stale facets.
                filter_key = (category, tag, source, period, search, classification)
                now = time.time()
                cache_age = now - _facet_cache["timestamp"]
                cache_hit = (
                    cache_age < FACET_CACHE_TTL
                    and _facet_cache["filter_key"] == filter_key
                    and _facet_cache["categories"] is not None
                )

                if cache_hit:
                    cat_list = _facet_cache["categories"]
                    tag_items = _facet_cache["tags"]
                    logger.info(f"[list_articles] Facet cache HIT (age={cache_age:.0f}s)")
                else:
                    t_facet = time.time()

                    # Category counts (contextual: exclude category from own filters)
                    cat_kwargs = {}
                    if tag:
                        cat_kwargs['tag'] = tag
                    if source:
                        cat_kwargs['source_id'] = source
                    if period:
                        cat_kwargs['period'] = period
                    if search:
                        cat_kwargs['search'] = search
                    if classification:
                        cat_kwargs['classification'] = classification

                    # PERF: Always use get_categories_filtered (even with no filters)
                    # instead of get_collection_stats which runs 2 extra unnecessary queries
                    # just to extract category counts.
                    cat_list = await run_db(db.get_categories_filtered, **cat_kwargs)
                    cat_list.sort(key=lambda x: x['count'], reverse=True)

                    # Tag counts (contextual: exclude tag from own filters)
                    tag_kwargs = {'limit': 100}
                    if category:
                        tag_kwargs['category'] = category
                    if source:
                        tag_kwargs['source_id'] = source
                    if period:
                        tag_kwargs['period'] = period
                    if search:
                        tag_kwargs['search'] = search
                    if classification:
                        tag_kwargs['classification'] = classification

                    has_tag_filters = any(v for k, v in tag_kwargs.items() if k != 'limit')
                    if has_tag_filters:
                        tag_list = await run_db(db.get_all_tags_filtered, **tag_kwargs)
                    else:
                        tag_list = await run_db(db.get_all_tags, limit=100)

                    tag_items = [{"id": i + 1, "tag": t['tag'], "theme": t['theme'], "count": t['count']} for i, t in enumerate(tag_list)]

                    facet_ms = (time.time() - t_facet) * 1000
                    logger.info(f"[list_articles] Facet cache MISS — computed in {facet_ms:.0f}ms (filters={filter_key})")

                    # Store in cache
                    _facet_cache["categories"] = cat_list
                    _facet_cache["tags"] = tag_items
                    _facet_cache["timestamp"] = now
                    _facet_cache["filter_key"] = filter_key

                facets = {
                    "categories": cat_list,
                    "tags": tag_items
                }
            except Exception as e:
                logger.warning(f"[list_articles] Failed to compute facets: {e}")

        # Converter para formato frontend
        # PERF: list_mode=True truncates content field to reduce payload (~60-80% smaller)
        response = {
            "items": [article.to_frontend_format(list_mode=True) for article in articles],
            "total": total,
            "page": page,
            "pages": pages,
            "urgency_counts": urgency_counts,
            "facets": facets
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
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error listing articles: {e}\n{tb}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "debug": str(e), "type": type(e).__name__, "trace": tb[-800:]}),
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
        article = await run_db(db.get_article_by_id, article_id)

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

        # PERF: Always use get_categories_filtered (works with or without filters)
        # instead of get_collection_stats which runs extra queries for unused data
        categories = await run_db(
            db.get_categories_filtered,
            search=search, tag=tag, source_id=source, period=period
        )

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
        tags = await run_db(db.get_trending_tags, limit=limit, period_hours=period_hours)

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
            tags = await run_db(
                db.get_all_tags_filtered,
                category=category, source_id=source, period=period, limit=limit
            )
        else:
            tags = await run_db(db.get_all_tags, search=search, limit=limit)

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
