"""
Research API - Web search endpoint for "Criar por Prompt" feature.

Endpoints:
- POST /api/research - Search web sources via Exa AI for a given topic prompt
"""

import asyncio
import logging
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

import azure.functions as func
from pydantic import BaseModel, Field, field_validator
import httpx

logger = logging.getLogger(__name__)

# Exa API configuration (same env vars as fact_check_service)
EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
EXA_ENDPOINT = os.environ.get("EXA_API_ENDPOINT", "https://api.exa.ai/search")
EXA_TIMEOUT = int(os.environ.get("EXA_TIMEOUT_SECONDS", "15"))

# Gov/official source domains for is_gov_source flag
GOV_DOMAINS = [".gov.br", "agenciabrasil.", "camara.leg.br", "senado.leg.br", "tse.jus.br"]

# URL patterns that indicate non-article pages (reused from fact_check_service)
_BAD_URL_PATTERNS = [
    "/topicos/", "/folha-topicos/", "/assuntos/", "/tag/",
    "/tags/", "/categoria/", "/categorias/", "/editoria/",
    "/index.php", "/index.html",
    "/c/mundo/", "/c/brasil/",
    "blogspot.com",
    "/docs/", "/developers/", "/api/",
    "/acompanhamento-", "/orcamento-cidadao",
    "/transparencia.",
]

# Category search angle hints (Portuguese)
_CATEGORY_ANGLES = {
    "politica": ["governo", "congresso", "legislação"],
    "economia": ["mercado", "PIB", "inflação"],
    "esportes": ["campeonato", "seleção", "competição"],
    "entretenimento": ["cultura", "celebridade", "show"],
    "geral": [],
}


# ============================================================================
# Request / Response Models
# ============================================================================

class ResearchRequest(BaseModel):
    prompt: str = Field(..., min_length=30, max_length=500)
    categoria: Optional[str] = None
    date_range_days: int = Field(default=7, ge=1, le=60)
    max_results: int = Field(default=10, ge=5, le=15)
    language: str = "pt"

    @field_validator("categoria")
    @classmethod
    def validate_categoria(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid = {"politica", "economia", "esportes", "entretenimento", "geral"}
            if v.lower() not in valid:
                raise ValueError(f"categoria must be one of: {', '.join(sorted(valid))}")
            return v.lower()
        return v


class ResearchSource(BaseModel):
    id: str
    title: str
    url: str
    domain: str
    published_date: Optional[str] = None
    snippet: str
    full_text: str
    char_count: int
    word_count: int
    relevance_score: float
    is_gov_source: bool


class ResearchResponse(BaseModel):
    sources: list
    search_queries: list
    total_chars: int
    search_duration_ms: int


# ============================================================================
# Helpers
# ============================================================================

def create_error_response(message: str, status_code: int = 400) -> func.HttpResponse:
    """Create a standardized error response."""
    return func.HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json",
    )


def create_success_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    """Create a standardized success response."""
    return func.HttpResponse(
        json.dumps(data, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json",
    )


def _is_quality_url(url: str, text: str) -> bool:
    """Filter out non-article URLs (topic pages, portals, indexes)."""
    url_lower = url.lower()
    for pattern in _BAD_URL_PATTERNS:
        if pattern in url_lower:
            return False
    if not text or len(text.strip()) < 150:
        return False
    return True


def _is_gov_source(url: str) -> bool:
    """Check if URL belongs to a government/official source."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in GOV_DOMAINS)


def _build_search_queries(prompt: str, categoria: Optional[str], language: str) -> list[str]:
    """Build 3-5 diverse search queries from the user's prompt."""
    queries = []

    # Query 1: prompt verbatim
    queries.append(prompt)

    # Query 2: prompt + current year
    current_year = datetime.utcnow().year
    queries.append(f"{prompt} {current_year}")

    # Query 3: category angle if provided
    if categoria and categoria in _CATEGORY_ANGLES:
        angles = _CATEGORY_ANGLES[categoria]
        if angles:
            queries.append(f"{prompt} {angles[0]}")

    # Query 4: Portuguese language hint for non-pt queries
    if language == "pt" and not any(
        word in prompt.lower() for word in ["brasil", "brasileiro", "brasileira"]
    ):
        queries.append(f"{prompt} Brasil")

    # Deduplicate while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        q_lower = q.strip().lower()
        if q_lower not in seen:
            seen.add(q_lower)
            unique_queries.append(q.strip())

    return unique_queries[:5]


def _get_date_range_start(days: int) -> str:
    """Get ISO date string for search range start."""
    start = datetime.utcnow() - timedelta(days=days)
    return start.strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def _search_exa(
    client: httpx.AsyncClient,
    query: str,
    num_results: int = 5,
    max_text: int = 4000,
    date_range_days: int = 7,
) -> list:
    """
    Execute a single Exa search.

    Returns list of {title, url, text, publishedDate} dicts.
    """
    headers = {
        "Content-Type": "application/json",
        "x-api-key": EXA_API_KEY,
    }

    payload = {
        "query": query,
        "type": "neural",
        "useAutoprompt": True,
        "numResults": num_results,
        "category": "news",
        "startPublishedDate": _get_date_range_start(date_range_days),
        "contents": {
            "text": {"maxCharacters": max_text},
            "highlights": {"numSentences": 3},
        },
    }

    response = await client.post(
        EXA_ENDPOINT,
        headers=headers,
        json=payload,
    )

    if response.status_code != 200:
        logger.warning(f"Exa API returned {response.status_code}: {response.text[:200]}")
        return []

    data = response.json()
    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "text": item.get("text", ""),
            "publishedDate": item.get("publishedDate", ""),
            "score": item.get("score", 0.0),
        })

    logger.info(f"Exa search '{query[:50]}...' returned {len(results)} results")

    # Cost logging
    try:
        from services.request_context import current_user_id, current_action_type, current_correlation_id
        from services.config import get_config
        from services.cost_queries import insert_api_usage_log
        insert_api_usage_log({
            'correlation_id': current_correlation_id.get(),
            'user_id': current_user_id.get(),
            'action_type': current_action_type.get(),
            'provider': 'exa',
            'operation': 'research_search',
            'request_count': 1,
            'input_units': num_results,
            'cost_usd': get_config().exa_cost_per_search,
            'status': 'success',
        })
    except Exception:
        pass

    return results


# ============================================================================
# Handler
# ============================================================================

async def research_topic_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Search web sources via Exa AI for a given topic prompt.

    POST /api/research
    Body: ResearchRequest JSON
    Returns: ResearchResponse JSON
    """
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Research request received")
    from services.request_context import current_user_id, current_action_type, current_correlation_id
    current_user_id.set(getattr(req, 'user', {}).get('id') if hasattr(req, 'user') else None)
    current_action_type.set('research')
    current_correlation_id.set(correlation_id)
    start_time = time.time()

    try:
        # Parse request body
        try:
            body = req.get_json()
        except ValueError:
            return create_error_response("Invalid JSON body", 400)

        # Validate request
        try:
            request_data = ResearchRequest(**body)
        except Exception as e:
            logger.warning(f"[{correlation_id}] Research request validation error: {e}")
            return create_error_response(
                "Erro de validacao: prompt deve ter entre 30 e 500 caracteres", 400
            )

        # Check Exa API key availability
        if not EXA_API_KEY:
            logger.error(f"[{correlation_id}] EXA_API_KEY not configured")
            return create_error_response(
                "Servico de pesquisa indisponivel (EXA_API_KEY nao configurado)", 503
            )

        # Build search queries
        queries = _build_search_queries(
            request_data.prompt,
            request_data.categoria,
            request_data.language,
        )
        logger.info(
            f"[{correlation_id}] Built {len(queries)} queries for prompt: "
            f"'{request_data.prompt[:60]}...'"
        )

        # Execute Exa searches in parallel for lower latency
        all_raw_results = []
        async with httpx.AsyncClient(timeout=float(EXA_TIMEOUT)) as client:
            async def _run_query(query):
                try:
                    return await _search_exa(
                        client,
                        query=query,
                        num_results=request_data.max_results,
                        max_text=4000,
                        date_range_days=request_data.date_range_days,
                    )
                except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                    logger.warning(
                        f"[{correlation_id}] Exa search failed for query "
                        f"'{query[:50]}': {e}"
                    )
                    return []
                except Exception as e:
                    logger.error(
                        f"[{correlation_id}] Unexpected Exa error for query "
                        f"'{query[:50]}': {e}"
                    )
                    return []

            results = await asyncio.gather(*[_run_query(q) for q in queries])
            for result_list in results:
                all_raw_results.extend(result_list)

        if not all_raw_results:
            logger.info(f"[{correlation_id}] No results from Exa searches")
            duration_ms = int((time.time() - start_time) * 1000)
            return create_success_response({
                "sources": [],
                "search_queries": queries,
                "total_chars": 0,
                "search_duration_ms": duration_ms,
            })

        # Deduplicate by URL (keep highest relevance score)
        url_best: dict[str, dict] = {}
        for item in all_raw_results:
            url = item.get("url", "")
            if not url:
                continue
            score = item.get("score", 0.0)
            if url not in url_best or score > url_best[url].get("score", 0.0):
                url_best[url] = item

        # Filter quality URLs
        filtered = []
        filtered_count = 0
        for url, item in url_best.items():
            text = item.get("text", "")
            if _is_quality_url(url, text):
                filtered.append(item)
            else:
                filtered_count += 1

        logger.info(
            f"[{correlation_id}] Dedup: {len(url_best)} unique URLs, "
            f"{filtered_count} filtered, {len(filtered)} kept"
        )

        # Build source objects
        sources = []
        for item in filtered:
            url = item.get("url", "")
            text = item.get("text", "")
            title = item.get("title", "")
            published = item.get("publishedDate", "")
            score = item.get("score", 0.0)

            # Extract domain
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
            except Exception:
                domain = ""

            # Truncate text to 4000 chars
            full_text = text[:4000] if text else ""
            snippet = text[:300] if text else ""
            char_count = len(full_text)
            word_count = len(full_text.split()) if full_text else 0

            # Normalize score to 0-1 range
            relevance_score = min(1.0, max(0.0, score)) if score else 0.0

            # Parse published date to ISO format
            pub_date = None
            if published:
                try:
                    # Exa returns ISO-like dates
                    pub_date = published[:10]  # YYYY-MM-DD
                except Exception:
                    pub_date = None

            sources.append({
                "id": str(uuid.uuid4()),
                "title": title,
                "url": url,
                "domain": domain,
                "published_date": pub_date,
                "snippet": snippet,
                "full_text": full_text,
                "char_count": char_count,
                "word_count": word_count,
                "relevance_score": round(relevance_score, 4),
                "is_gov_source": _is_gov_source(url),
            })

        # Sort: published_date desc (most recent first), then relevance_score desc
        def _sort_key(s: dict):
            date_str = s.get("published_date") or "0000-00-00"
            return (date_str, s.get("relevance_score", 0.0))

        sources.sort(key=_sort_key, reverse=True)

        # Trim to max_results
        sources = sources[: request_data.max_results]

        # Calculate totals
        total_chars = sum(s["char_count"] for s in sources)
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{correlation_id}] Research complete: {len(sources)} sources, "
            f"{total_chars} total chars, {duration_ms}ms"
        )

        return create_success_response({
            "sources": sources,
            "search_queries": queries,
            "total_chars": total_chars,
            "search_duration_ms": duration_ms,
        })

    except Exception as e:
        logger.exception(f"[{correlation_id}] Research handler error: {e}")
        return create_error_response("Erro interno no servico de pesquisa", 500)
