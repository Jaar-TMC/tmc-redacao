"""
API REST para artigos coletados.
"""

import asyncio
import azure.functions as func
import hashlib
import json
import logging
import time
from math import ceil
from uuid import UUID

from services.database import get_db, encode_cursor, decode_cursor
from services.async_db import run_db
from models import ArticleListResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory facet cache keyed by filter combination (5-min TTL)
# Categories and tags only change when new articles are collected (every 15 min).
# Caching avoids expensive CROSS APPLY OPENJSON() on every /api/articles request.
# ---------------------------------------------------------------------------
_facet_cache = {}  # key: filter_hash -> {"categories": [...], "tags": [...], "timestamp": float}
FACET_CACHE_TTL = 300  # seconds
MAX_FACET_CACHE_ENTRIES = 20

# ---------------------------------------------------------------------------
# In-memory caches for /api/tags and /api/trending-tags (5-min TTL).
# These endpoints scan up to 24K articles with OPENJSON when the pre-aggregated
# tag_aggregations table is empty/stale. The handler-level cache ensures that
# even the first warm hit only reaches the DB once per TTL window.
# Key: (limit, period_hours) for trending; (search, limit, category, source, period) for tags.
# ---------------------------------------------------------------------------
_trending_tags_cache: dict = {}   # key -> {"data": [...], "ts": float}
_all_tags_cache: dict = {}        # key -> {"data": [...], "ts": float}
TAGS_CACHE_TTL = 300  # 5 minutes — matches RSS collection cadence (15 min)


def _facet_cache_key(category, source, period, search, tag, classification, max_hours):
    raw = f"{category}|{source}|{period}|{search}|{tag}|{classification}|{max_hours}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# In-memory urgency counts cache (30-sec TTL)
# Urgency counts (1h/3h/8h/total) change slowly; caching avoids a second
# full-table scan on every /api/articles request.
# ---------------------------------------------------------------------------
_urgency_cache = {
    "counts": None,
    "timestamp": 0,
    "key": None,  # filter hash to invalidate on filter change
}
URGENCY_CACHE_TTL = 30  # seconds


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

        # Per PAG-01/D-01: Parse opaque base64 cursor for keyset pagination
        cursor_str = req.params.get('cursor')
        cursor_direction = req.params.get('cursor_direction', 'next')
        cursor_data = None
        if cursor_str:
            try:
                cursor_published_at, cursor_id = decode_cursor(cursor_str)
                cursor_data = {"published_at": cursor_published_at, "id": cursor_id}
            except (ValueError, Exception) as e:
                logger.warning(f"[list_articles] Invalid cursor ignored, falling back to page=1: {e}")
                cursor_data = None

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

        # DB-05: Check urgency cache before querying
        # Build a cache key from filters that affect urgency counts (exclude page/limit)
        urgency_filter_key = _facet_cache_key(category, source, None, search, tag, classification, max_hours)
        now = time.time()
        urgency_cache_hit = (
            _urgency_cache["counts"] is not None
            and _urgency_cache["key"] == urgency_filter_key
            and (now - _urgency_cache["timestamp"]) < URGENCY_CACHE_TTL
        )

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
            order_by=order_by,
            skip_urgency_query=urgency_cache_hit,
            cursor=cursor_data,
            cursor_direction=cursor_direction
        )

        # DB-05: Use cached urgency counts on cache hit; update cache on miss
        if urgency_cache_hit:
            urgency_counts = _urgency_cache["counts"]
            logger.info(f"[list_articles] Urgency cache HIT (age={now - _urgency_cache['timestamp']:.0f}s)")
        else:
            _urgency_cache["counts"] = urgency_counts
            _urgency_cache["timestamp"] = now
            _urgency_cache["key"] = urgency_filter_key

        # Calcular total de paginas
        pages = ceil(total / limit) if total > 0 else 1

        # Per PAG-01/D-02/D-03: Build cursor response fields for keyset pagination
        next_cursor = None
        prev_cursor = None

        use_cursor_mode = order_by != 'score'
        if use_cursor_mode and articles:
            # nextCursor from last article -- only if this page is full (more pages exist)
            if len(articles) == limit:
                last_art = articles[-1]
                if last_art.published_at and last_art.id:
                    next_cursor = encode_cursor(last_art.published_at, last_art.id)

            # prevCursor from first article -- only if not on first page
            if cursor_data is not None or page > 1:
                first_art = articles[0]
                if first_art.published_at and first_art.id:
                    prev_cursor = encode_cursor(first_art.published_at, first_art.id)

        # Compute facets for filter dropdowns (avoids separate API calls)
        # Skip facet computation when client signals it doesn't need updated facets
        # (e.g., pagination-only requests where filters haven't changed)
        #
        # PERF: When search is active, facet queries also run the expensive
        # LIKE/FREETEXT filter — this doubles+ the total query cost.  Instead,
        # return cached unfiltered facets (or skip) so search stays fast.
        facets = None
        # DB-09: Keyed facet cache — find any cached entry for the current filters
        fkey = _facet_cache_key(category, source, period, search, tag, classification, max_hours)

        if skip_facets:
            logger.info("[list_articles] Skipping facet computation (skip_facets=true)")
        elif max_hours == '0':
            # PERF: "todas as matérias" (no time filter) scans 24K+ rows for facets.
            # Return cached facets instead of recomputing to avoid 504 timeouts.
            any_cached = next(iter(_facet_cache.values()), None) if _facet_cache else None
            if any_cached:
                facets = {
                    "categories": any_cached["categories"],
                    "tags": any_cached["tags"]
                }
                logger.info("[list_articles] max_hours=0 — returning cached facets to avoid timeout")
            else:
                logger.info("[list_articles] max_hours=0 — no cached facets, skipping to avoid timeout")
        elif search:
            # Return any cached facets when available; skip computation during search
            any_cached = next(iter(_facet_cache.values()), None) if _facet_cache else None
            if any_cached:
                facets = {
                    "categories": any_cached["categories"],
                    "tags": any_cached["tags"]
                }
                logger.info("[list_articles] Search active — returning cached unfiltered facets")
            else:
                logger.info("[list_articles] Search active — no cached facets, skipping")
        else:
            try:
                cached_entry = _facet_cache.get(fkey)
                cache_hit = (
                    cached_entry is not None
                    and (now - cached_entry["timestamp"]) < FACET_CACHE_TTL
                )

                if cache_hit:
                    cat_list = cached_entry["categories"]
                    tag_items = cached_entry["tags"]
                    logger.info(f"[list_articles] Facet cache HIT key={fkey} (age={now - cached_entry['timestamp']:.0f}s)")
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
                    if classification:
                        cat_kwargs['classification'] = classification

                    # Tag counts (contextual: exclude tag from own filters)
                    tag_kwargs = {'limit': 100}
                    if category:
                        tag_kwargs['category'] = category
                    if source:
                        tag_kwargs['source_id'] = source
                    if period:
                        tag_kwargs['period'] = period
                    if classification:
                        tag_kwargs['classification'] = classification

                    has_tag_filters = any(v for k, v in tag_kwargs.items() if k != 'limit')

                    # DB-07: Parallelize category + tag facet queries
                    cat_coro = run_db(db.get_categories_filtered, **cat_kwargs)
                    if has_tag_filters:
                        tag_coro = run_db(db.get_all_tags_filtered, **tag_kwargs)
                    else:
                        tag_coro = run_db(db.get_all_tags_fast, limit=100)

                    cat_list, tag_list = await asyncio.gather(cat_coro, tag_coro)
                    cat_list.sort(key=lambda x: x['count'], reverse=True)

                    tag_items = [{"id": i + 1, "tag": t['tag'], "theme": t['theme'], "count": t['count']} for i, t in enumerate(tag_list)]

                    facet_ms = (time.time() - t_facet) * 1000
                    logger.info(f"[list_articles] Facet cache MISS key={fkey} — computed in {facet_ms:.0f}ms")

                    # DB-09: Store in keyed cache; evict oldest if over limit
                    _facet_cache[fkey] = {
                        "categories": cat_list,
                        "tags": tag_items,
                        "timestamp": now
                    }
                    if len(_facet_cache) > MAX_FACET_CACHE_ENTRIES:
                        oldest_key = min(_facet_cache, key=lambda k: _facet_cache[k]["timestamp"])
                        del _facet_cache[oldest_key]

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
            "facets": facets,
            "nextCursor": next_cursor,
            "prevCursor": prev_cursor,
        }

        resp = func.HttpResponse(
            json.dumps(response, default=str),
            status_code=200,
            mimetype="application/json"
        )
        # Cache articles list for 60 seconds (data changes every 15 min via RSS collector)
        # Cache-Control set centrally in function_app.py via add_cache_headers()
        return resp

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
        # Detect query timeout to return a clearer message
        err_str = str(e).lower()
        is_timeout = 'timeout' in err_str or 'timed out' in err_str
        if is_timeout:
            return func.HttpResponse(
                json.dumps({"error": "A busca demorou demais. Tente um termo mais específico ou remova filtros."}),
                status_code=504,
                mimetype="application/json"
            )
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

        resp = func.HttpResponse(
            json.dumps(article.to_frontend_format(), default=str),
            status_code=200,
            mimetype="application/json"
        )
        # Cache single article for 2 minutes (content is static after collection)
        # Cache-Control set centrally in function_app.py via add_cache_headers()
        return resp

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

        resp = func.HttpResponse(
            json.dumps({"categories": categories}),
            status_code=200,
            mimetype="application/json"
        )
        # Cache categories for 5 minutes (only change when new articles are collected)
        # Cache-Control set centrally in function_app.py via add_cache_headers()
        return resp

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

        effective_hours = period_hours or 72
        cache_key = f"{limit}:{effective_hours}"
        now = time.monotonic()

        # Check in-memory cache first (5-min TTL) — avoids the DB entirely on warm hits.
        # The live OPENJSON fallback takes 24-28s on 24K articles; this cache cuts that to <1ms.
        cached = _trending_tags_cache.get(cache_key)
        if cached and (now - cached["ts"]) < TAGS_CACHE_TTL:
            logger.debug(f"[trending-tags] cache hit key={cache_key}")
            return func.HttpResponse(
                json.dumps({"items": cached["data"], "total": len(cached["data"])}),
                status_code=200,
                mimetype="application/json"
            )

        # Get trending tags from database
        db = get_db()
        tags = await run_db(db.get_trending_tags_fast, limit=limit, period_hours=effective_hours)

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

        # Store in handler-level cache
        _trending_tags_cache[cache_key] = {"data": items, "ts": now}
        # Evict oldest entry if cache grows beyond 20 keys (different limit/period combos)
        if len(_trending_tags_cache) > 20:
            oldest = min(_trending_tags_cache, key=lambda k: _trending_tags_cache[k]["ts"])
            del _trending_tags_cache[oldest]

        resp = func.HttpResponse(
            json.dumps({"items": items, "total": len(items)}),
            status_code=200,
            mimetype="application/json"
        )
        # Cache trending tags for 5 minutes (recalculated periodically)
        # Cache-Control set centrally in function_app.py via add_cache_headers()
        return resp

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

        # Cache key covers all filter dimensions. Filtered calls (category/source/period)
        # are still cached — they're expensive too (OPENJSON with JOIN).
        cache_key = f"{search}:{limit}:{category}:{source}:{period}"
        now = time.monotonic()

        cached = _all_tags_cache.get(cache_key)
        if cached and (now - cached["ts"]) < TAGS_CACHE_TTL:
            logger.debug(f"[tags] cache hit key={cache_key}")
            return func.HttpResponse(
                json.dumps({"items": cached["data"], "total": len(cached["data"])}),
                status_code=200,
                mimetype="application/json"
            )

        db = get_db()

        if has_filters:
            tags = await run_db(
                db.get_all_tags_filtered,
                category=category, source_id=source, period=period, limit=limit
            )
        else:
            tags = await run_db(db.get_all_tags_fast, search=search, limit=limit)

        # Format response
        items = []
        for i, tag_data in enumerate(tags):
            items.append({
                "id": i + 1,
                "theme": tag_data['theme'],
                "tag": tag_data['tag'],
                "count": tag_data['count']
            })

        # Store in handler-level cache
        _all_tags_cache[cache_key] = {"data": items, "ts": now}
        # Evict oldest entry if cache grows large (many distinct filter combos)
        if len(_all_tags_cache) > 50:
            oldest = min(_all_tags_cache, key=lambda k: _all_tags_cache[k]["ts"])
            del _all_tags_cache[oldest]

        resp = func.HttpResponse(
            json.dumps({"items": items, "total": len(items)}),
            status_code=200,
            mimetype="application/json"
        )
        # Cache tags for 5 minutes (only change when new articles are collected)
        # Cache-Control set centrally in function_app.py via add_cache_headers()
        return resp

    except Exception as e:
        logger.error(f"Error getting all tags: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )
