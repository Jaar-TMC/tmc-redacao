"""
TMC RSS Collector - Entry Point
Azure Functions v2 com Python

Este arquivo registra todas as functions (triggers e routes) da aplicação.
"""

import azure.functions as func
import json
import logging
import asyncio
from functools import wraps
from utils.auth import require_auth, require_admin, require_ai_active

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar app
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# ========================================
# CORS Configuration
# ========================================

import os

# Phase 4.2: CORS from env var (comma-separated), with localhost fallback for dev only
_cors_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
if _cors_env:
    ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    # Only allow localhost in development
    _production_mode = os.environ.get("PRODUCTION_SAFETY_MODE", "true").lower() == "true"
    if _production_mode:
        ALLOWED_ORIGINS = []  # No CORS in production without explicit config
    else:
        ALLOWED_ORIGINS = [
            "http://localhost:5173",
            "http://localhost:3000",
        ]


def add_cors_headers(response: func.HttpResponse, origin: str = None) -> func.HttpResponse:
    """Add CORS headers to response."""
    allowed_origin = origin if origin in ALLOWED_ORIGINS else ""

    # Create new response with CORS headers
    headers = dict(response.headers) if response.headers else {}
    headers["Access-Control-Allow-Origin"] = allowed_origin
    headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    headers["Access-Control-Allow-Credentials"] = "true"

    return func.HttpResponse(
        response.get_body(),
        status_code=response.status_code,
        headers=headers,
        mimetype=response.mimetype
    )


def with_cors(handler):
    """Decorator to add CORS headers to HTTP handlers."""
    @wraps(handler)
    async def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        origin = req.headers.get("Origin", "")

        # Handle preflight OPTIONS request
        if req.method == "OPTIONS":
            allowed_origin = origin if origin in ALLOWED_ORIGINS else ""
            return func.HttpResponse(
                "",
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": allowed_origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                    "Access-Control-Allow-Credentials": "true",
                }
            )

        # Call original handler and add CORS headers
        try:
            response = await handler(req)
        except Exception as e:
            logger.exception(f"Unhandled error in {handler.__name__}: {e}")
            error_body = json.dumps({"error": "Internal server error"})
            response = func.HttpResponse(error_body, status_code=500, mimetype="application/json")

        try:
            return add_cors_headers(response, origin)
        except Exception as cors_err:
            # Safety net: if CORS header addition crashes, return response without CORS
            logger.error(f"add_cors_headers failed: {cors_err}")
            return response

    return wrapper


def check_rate_limit(endpoint_name: str):
    """Returns a (429 HttpResponse, None) if rate limited, or (None, retry_after) if allowed."""
    from services.rate_limiter import RateLimiter
    retry_after = RateLimiter.get().check(endpoint_name)
    if retry_after is not None:
        return func.HttpResponse(
            json.dumps({"error": "Rate limit exceeded", "retry_after_seconds": round(retry_after, 1)}),
            status_code=429,
            headers={"Retry-After": str(int(retry_after) + 1)},
            mimetype="application/json",
        )
    return None


# ========================================
# TIMER TRIGGER - RSS COLLECTOR
# ========================================

@app.timer_trigger(
    schedule="0 */15 * * * *",  # A cada 15 minutos
    arg_name="timer",
    run_on_startup=False
)
async def rss_collector(timer: func.TimerRequest) -> None:
    """
    Timer trigger que coleta feeds RSS a cada 15 minutos.

    Fluxo:
    1. Busca fontes ativas que devem ser coletadas
    2. Processa em paralelo (máx 10 simultâneas)
    3. Para cada fonte: fetch → parse → deduplica → enriquece → insere
    4. Atualiza last_fetch e registra logs
    """
    from functions.rss_collector import rss_collector_handler
    await rss_collector_handler(timer)


# ========================================
# TIMER TRIGGER - EMBEDDING GENERATOR
# ========================================

@app.timer_trigger(
    schedule="0 */5 * * * *",  # A cada 5 minutos
    arg_name="timer",
    run_on_startup=False
)
async def embedding_generator(timer: func.TimerRequest) -> None:
    """
    Timer trigger que gera embeddings para artigos a cada 5 minutos.

    Processa até 50 artigos por execução.
    """
    from functions.embedding_generator import embedding_generator_handler
    await embedding_generator_handler(timer)


# ========================================
# TIMER TRIGGER - SCORING CALCULATOR
# ========================================

@app.timer_trigger(
    schedule="0 */10 * * * *",  # A cada 10 minutos
    arg_name="timer",
    run_on_startup=False
)
async def scoring_calculator(timer: func.TimerRequest) -> None:
    """
    Timer trigger que calcula scores editoriais a cada 10 minutos.

    Classifica artigos em A/B/C usando 4 sinais editoriais.
    Processa até 20 artigos por execução.
    """
    from functions.scoring_calculator import scoring_calculator_handler
    await scoring_calculator_handler(timer)


# ========================================
# TIMER TRIGGER - CLUSTERING ENGINE
# ========================================

@app.timer_trigger(
    schedule="0 */30 * * * *",  # A cada 30 minutos
    arg_name="timer",
    run_on_startup=False
)
async def clustering_engine(timer: func.TimerRequest) -> None:
    """
    Timer trigger que agrupa artigos em temas semanticos a cada 30 minutos.

    Usa embeddings para clustering por similaridade de conteudo.
    """
    from functions.clustering_engine import clustering_engine_handler
    await clustering_engine_handler(timer)


# ========================================
# TIMER TRIGGER - CLUSTERING MAINTENANCE
# ========================================

@app.timer_trigger(
    schedule="0 0 3 * * *",  # Diariamente as 3AM UTC
    arg_name="timer",
    run_on_startup=False
)
async def clustering_maintenance(timer: func.TimerRequest) -> None:
    """
    Timer trigger para manutencao diaria do clustering.
    Executa diariamente as 3AM UTC.

    Tarefas:
    1. Merge temas muito similares (> 0.90)
    2. Desativa temas orfaos (0 artigos)
    3. Recalcula scores de todos os temas
    4. Gera relatorio de qualidade
    """
    from functions.clustering_maintenance import clustering_maintenance_handler
    await clustering_maintenance_handler(timer)


# ========================================
# TIMER TRIGGER - DAILY COST AGGREGATION
# ========================================

@app.timer_trigger(
    schedule="0 30 0 * * *",  # Daily at 00:30 UTC
    arg_name="timer",
    run_on_startup=False
)
async def daily_cost_aggregation(timer: func.TimerRequest) -> None:
    """
    Timer trigger para agregacao diaria de custos.
    Executa diariamente as 00:30 UTC (30min buffer para logs tardios).
    Agrega llm_usage_log e api_usage_log em daily_cost_summary e daily_cost_detail.
    """
    from datetime import datetime, timedelta
    from services.cost_queries import aggregate_daily_costs
    yesterday = (datetime.utcnow() - timedelta(days=1)).date()
    logger.info(f"Daily cost aggregation started for {yesterday}")
    result = await aggregate_daily_costs(yesterday)
    logger.info(f"Daily cost aggregation result: {result}")


# ========================================
# TIMER TRIGGER - DATA RETENTION CLEANUP
# ========================================

@app.timer_trigger(
    schedule="0 0 3 1 * *",  # 1st of each month at 03:00 UTC
    arg_name="timer",
    run_on_startup=False
)
async def cost_data_cleanup(timer: func.TimerRequest) -> None:
    """
    Timer trigger para limpeza mensal de dados brutos de custo.
    Deleta registros de llm_usage_log e api_usage_log com mais de 90 dias,
    apos confirmar que estao agregados em daily_cost_summary/daily_cost_detail.
    """
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(days=90)).date()
    logger.info(f"Cost data cleanup started, cutoff: {cutoff}")

    try:
        from services.database import get_db
        db = get_db()
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Delete old raw LLM usage logs (aggregated data preserved in summary tables)
            # Only delete data for dates confirmed aggregated
            cursor.execute("""
                DELETE FROM llm_usage_log
                WHERE created_at < %s
                  AND CONVERT(DATE, created_at) IN (SELECT DISTINCT date FROM daily_cost_summary)
            """, (str(cutoff),))
            llm_deleted = cursor.rowcount

            # Delete old raw API usage logs
            cursor.execute("""
                DELETE FROM api_usage_log
                WHERE created_at < %s
                  AND CONVERT(DATE, created_at) IN (SELECT DISTINCT date FROM daily_cost_summary)
            """, (str(cutoff),))
            api_deleted = cursor.rowcount

            conn.commit()
            logger.info(f"Cost data cleanup complete: {llm_deleted} LLM + {api_deleted} API records deleted (older than {cutoff})")
    except Exception as e:
        logger.error(f"Cost data cleanup failed: {e}")


# ========================================
# HTTP TRIGGERS - HEALTH & STATS
# ========================================

@app.route(route="health", methods=["GET", "OPTIONS"])
@with_cors
async def health(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/health - Health check do serviço."""
    from functions.health import health_check_handler
    return await health_check_handler(req)


@app.route(route="stats", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def stats(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/stats - Estatísticas de coleta (admin only)."""
    from functions.health import stats_handler
    return await stats_handler(req)


# ========================================
# HTTP TRIGGERS - ARTICLES API
# ========================================

@app.route(route="articles", methods=["GET", "OPTIONS"])
@with_cors
@require_auth
async def list_articles(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/articles - Lista artigos coletados.

    Query params:
        page: int - Página (default: 1)
        limit: int - Itens por página (default: 20, max: 100)
        category: str - Filtrar por categoria
        source: str - Filtrar por source_id
        period: str - 'today', 'week', 'month'
        search: str - Busca em título/conteúdo
        tag: str - Filtrar por tag exata
        max_hours: int - Filtrar por urgência (1-24 horas)

    Response includes urgency_counts: {now, recent, today, all}
    """
    from functions.articles_api import list_articles_handler
    return await list_articles_handler(req)


@app.route(route="articles/{id}", methods=["GET", "OPTIONS"])
@with_cors
@require_auth
async def get_article(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/articles/{id} - Retorna um artigo específico."""
    from functions.articles_api import get_article_handler
    return await get_article_handler(req)


@app.route(route="categories", methods=["GET", "OPTIONS"])
@with_cors
@require_auth
async def get_categories(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/categories - Lista categorias com contagem."""
    from functions.articles_api import get_categories_handler
    return await get_categories_handler(req)


@app.route(route="trending-tags", methods=["GET", "OPTIONS"])
@with_cors
@require_auth
async def get_trending_tags(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/trending-tags - Retorna tags em alta com contagem de artigos.

    Query params:
        limit: int - Máximo de tags (default: 20, max: 50)
        period: int - Filtrar artigos das últimas N horas (opcional)

    Returns:
        {
            "items": [{"id": 1, "theme": "Tag Name", "tag": "tag-name", "count": 15, "trend": "stable"}, ...],
            "total": 20
        }
    """
    from functions.articles_api import get_trending_tags_handler
    return await get_trending_tags_handler(req)


@app.route(route="tags", methods=["GET", "OPTIONS"])
@with_cors
@require_auth
async def get_all_tags(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/tags - Retorna TODAS as tags com contagem de artigos.

    Query params:
        search: str - Filtrar tags por nome (opcional)

    Returns:
        {
            "items": [{"id": 1, "theme": "Tag Name", "tag": "tag-name", "count": 15}, ...],
            "total": 150
        }
    """
    from functions.articles_api import get_all_tags_handler
    return await get_all_tags_handler(req)


# ========================================
# HTTP TRIGGERS - SOURCES API
# ========================================

@app.route(route="sources", methods=["GET", "POST", "OPTIONS"])
@with_cors
async def sources_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    /api/sources - Gerencia fontes RSS.

    GET: Lista todas as fontes RSS.
    POST: Cria uma nova fonte RSS (admin only).
    """
    from utils.auth import get_current_user
    user = await get_current_user(req)
    if not user:
        return func.HttpResponse(
            json.dumps({"error": "Authentication required"}),
            status_code=401,
            mimetype="application/json"
        )
    req.user = user
    if req.method == "POST":
        if user["role"] != "admin":
            return func.HttpResponse(
                json.dumps({"error": "Admin access required"}),
                status_code=403,
                mimetype="application/json"
            )
    if req.method == "GET":
        from functions.sources_api import list_sources_handler
        return await list_sources_handler(req)
    elif req.method == "POST":
        from functions.sources_api import create_source_handler
        return await create_source_handler(req)
    return func.HttpResponse(
        json.dumps({"error": "Method not allowed"}),
        status_code=405,
        mimetype="application/json"
    )


@app.route(route="sources/{id}", methods=["GET", "PUT", "DELETE", "OPTIONS"])
@with_cors
async def source_by_id_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    /api/sources/{id} - Gerencia uma fonte específica.

    GET: Retorna uma fonte específica.
    PUT: Atualiza uma fonte existente (admin only).
    DELETE: Desativa uma fonte (admin only, soft delete).
    """
    from utils.auth import get_current_user
    user = await get_current_user(req)
    if not user:
        return func.HttpResponse(
            json.dumps({"error": "Authentication required"}),
            status_code=401,
            mimetype="application/json"
        )
    req.user = user
    if req.method in ("PUT", "DELETE"):
        if user["role"] != "admin":
            return func.HttpResponse(
                json.dumps({"error": "Admin access required"}),
                status_code=403,
                mimetype="application/json"
            )
    if req.method == "GET":
        from functions.sources_api import get_source_handler
        return await get_source_handler(req)
    elif req.method == "PUT":
        from functions.sources_api import update_source_handler
        return await update_source_handler(req)
    elif req.method == "DELETE":
        from functions.sources_api import delete_source_handler
        return await delete_source_handler(req)
    return func.HttpResponse(
        json.dumps({"error": "Method not allowed"}),
        status_code=405,
        mimetype="application/json"
    )


@app.route(route="sources/{id}/collect", methods=["POST", "OPTIONS"])
@with_cors
@require_admin
async def collect_source(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/sources/{id}/collect - Dispara coleta manual (admin only)."""
    from functions.sources_api import collect_source_handler
    return await collect_source_handler(req)


# ========================================
# HTTP TRIGGERS - AI GENERATION API
# ========================================

@app.route(route="metrics", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def metrics(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/metrics - In-process pipeline metrics (admin only)."""
    import json as _json
    from services.metrics import Metrics
    return func.HttpResponse(
        _json.dumps(Metrics.get().snapshot()),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="ai-status", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
@with_cors
@require_auth
async def ai_status_get(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/ai-status - Current AI operational status."""
    from functions.ai_status_api import get_ai_status_handler
    return await get_ai_status_handler(req)


@app.route(route="ai-status", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@with_cors
@require_auth
async def ai_status_set(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/ai-status - Pause or resume AI operations (admin only)."""
    from functions.ai_status_api import set_ai_status_handler
    return await set_ai_status_handler(req)


@app.route(route="generate", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
@require_ai_active
async def generate_article(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/generate - Gera matéria usando IA.

    Body:
        {
            "texto_base": "Texto fonte para reescrita...",
            "persona": "imparcial|especialista|colunista|influencer",
            "tom": "formal|informal|tecnico|persuasivo|neutro",
            "tipo_materia": "destaque|coluna|servico|analise|reportagem",
            "orientacao_lide": "Orientação para o lide (opcional)",
            "citacoes": ["Citação 1", "Citação 2"],
            "contexto": "Contexto adicional (opcional)",
            "creditos": "Créditos da fonte (opcional)",
            "tags": ["tag1", "tag2"]
        }

    Returns:
        {
            "titulo": "Título gerado",
            "linha_fina": "Linha fina gerada",
            "conteudo": "Corpo da matéria (mín 2000 chars)",
            "tags_sugeridas": ["tag1", "tag2", "tag3"]
        }
    """
    rate_limit_response = check_rate_limit("generate")
    if rate_limit_response:
        return rate_limit_response
    from functions.generation_api import generate_article_handler
    return await generate_article_handler(req)


@app.route(route="extract-topics", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
@require_ai_active
async def extract_topics(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/extract-topics - Extrai tópicos do texto usando IA.

    Body:
        {"texto": "Texto para análise..."}

    Returns:
        {"topics": [{"type": "fato", "content": "..."}, ...]}
    """
    rate_limit_response = check_rate_limit("extract-topics")
    if rate_limit_response:
        return rate_limit_response
    from functions.generation_api import extract_topics_handler
    return await extract_topics_handler(req)


@app.route(route="generate-tags", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
@require_ai_active
async def generate_tags(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/generate-tags - Gera tags para conteúdo usando IA.

    Body:
        {"texto": "Conteúdo para análise...", "max_tags": 10}

    Returns:
        {"tags": ["tag1", "tag2", "tag3", ...]}
    """
    rate_limit_response = check_rate_limit("generate-tags")
    if rate_limit_response:
        return rate_limit_response
    from functions.generation_api import generate_tags_handler
    return await generate_tags_handler(req)


@app.route(route="merge-topics", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
@require_ai_active
async def merge_topics(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/merge-topics - Agrupa tópicos de múltiplas matérias usando IA.

    Transforma a visualização de "artigo por artigo" para "história unificada",
    agrupando conteúdo por elemento da história (fato, contexto, reação, etc.)
    em vez de por fonte.

    Body:
        {
            "articles": [
                {
                    "id": "art-1",
                    "title": "Título da matéria",
                    "content": "Conteúdo completo...",
                    "source": "Nome da Fonte"
                },
                ...  (máximo 3 artigos)
            ]
        }

    Returns:
        {
            "groups": [
                {
                    "id": "group-1",
                    "type": "fato|contexto|reacao|dado",
                    "label": "FATO PRINCIPAL",
                    "versions": [
                        {"id": "v1", "articleId": "art-1", "content": "...", "source": "Folha", "isRecommended": true}
                    ],
                    "aiSuggestion": {"recommendedId": "v1", "reason": "Versão mais completa"}
                }
            ],
            "exclusives": [
                {"id": "exc-1", "content": "...", "source": "G1", "type": "dado"}
            ],
            "quotes": [
                {"id": "q1", "text": "...", "speaker": "Nome", "source": "Estadão"}
            ],
            "summary": {"mainTopic": "...", "totalElements": 5}
        }
    """
    rate_limit_response = check_rate_limit("merge-topics")
    if rate_limit_response:
        return rate_limit_response
    from functions.generation_api import merge_topics_handler
    return await merge_topics_handler(req)


@app.route(route="edit-article", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
@require_ai_active
async def edit_article(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/edit-article - Edita uma matéria existente usando IA.

    Permite edições incrementais do artigo via chat com a IA.
    Suporta histórico de versões no frontend (undo/redo).

    Body:
        {
            "current_article": {
                "title": "Título atual",
                "linha_fina": "Linha fina atual",
                "content": "Conteúdo atual...",
                "tags": ["tag1", "tag2"]
            },
            "instruction": "Melhore o SEO do título",
            "edit_scope": "full|title|linha_fina|content|tags",
            "categoria": "geral",
            "tom": "conversacional"
        }

    Returns:
        {
            "titulo": "Título editado",
            "linha_fina": "Linha fina editada",
            "conteudo": "Conteúdo editado...",
            "tags": ["tag1", "tag2", "nova-tag"],
            "changes_summary": "Descrição das alterações feitas"
        }
    """
    rate_limit_response = check_rate_limit("edit-article")
    if rate_limit_response:
        return rate_limit_response
    from functions.edit_api import edit_article_handler
    return await edit_article_handler(req)


# ========================================
# HTTP TRIGGERS - FACT-CHECK SCAN
# ========================================

@app.route(route="fact-check-scan", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
@require_ai_active
async def fact_check_scan(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/fact-check-scan - On-demand article safety verification."""
    rate_limit_response = check_rate_limit("fact-check-scan")
    if rate_limit_response:
        return rate_limit_response
    from functions.fact_check_scan_api import fact_check_scan_handler
    return await fact_check_scan_handler(req)


@app.route(route="fact-check-deep-verify", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
@require_ai_active
async def fact_check_deep_verify(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/fact-check-deep-verify - Deep verify unverifiable claims."""
    rate_limit_response = check_rate_limit("fact-check-scan")
    if rate_limit_response:
        return rate_limit_response
    from functions.fact_check_scan_api import deep_verify_handler
    return await deep_verify_handler(req)


# ========================================
# HTTP TRIGGERS - RESEARCH (Criar por Prompt)
# ========================================

@app.route(route="research", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
@require_ai_active
async def research(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/research - Pesquisa fontes web via Exa AI para um dado prompt.

    Body:
        {
            "prompt": "Descrição do assunto (30-500 chars)",
            "categoria": "politica|economia|esportes|entretenimento|geral",
            "date_range_days": 7,
            "max_results": 10,
            "language": "pt"
        }

    Returns:
        {
            "sources": [...],
            "search_queries": [...],
            "total_chars": 12345,
            "search_duration_ms": 3200
        }
    """
    rate_limit_response = check_rate_limit("research")
    if rate_limit_response:
        return rate_limit_response
    from functions.research_api import research_topic_handler
    return await research_topic_handler(req)


# ========================================
# HTTP TRIGGERS - TRANSCRIPTION DIAGNOSTIC (temporary)
# ========================================

@app.route(route="transcribe-diag", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def transcribe_diag(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/transcribe-diag - Diagnostic for transcription deps."""
    import sys
    checks = {"python": sys.version}
    try:
        import youtube_transcript_api
        checks["youtube_transcript_api"] = "OK"
        checks["yta_dir"] = [m for m in dir(youtube_transcript_api.YouTubeTranscriptApi) if not m.startswith("_")]
    except Exception as e:
        checks["youtube_transcript_api"] = f"FAIL: {e}"
    try:
        from services.youtube_service import YouTubeService
        checks["youtube_service"] = "OK"
        vid = YouTubeService.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        checks["extract_video_id"] = vid
    except Exception as e:
        checks["youtube_service"] = f"FAIL: {e}"
    try:
        from functions.transcription_api import transcribe_handler
        checks["transcription_api"] = "OK"
    except Exception as e:
        checks["transcription_api"] = f"FAIL: {e}"
    # Test actual YouTube calls with user's video
    test_vid = req.params.get("vid", "dQw4w9WgXcQ")
    checks["test_video_id"] = test_vid
    import asyncio
    try:
        meta = await YouTubeService.get_video_metadata(test_vid)
        checks["metadata_fetch"] = f"OK: {meta.get('title','?')[:80]}"
    except Exception as e:
        checks["metadata_fetch"] = f"FAIL: {type(e).__name__}: {e}"
    try:
        caps = await YouTubeService.get_captions(test_vid, target_duration=60.0)
        checks["caption_fetch"] = f"OK: {len(caps['segments'])} segments, lang={caps['language']}, type={caps['caption_type']}"
    except Exception as e:
        import traceback
        logger.error(f"transcribe-diag caption_fetch failed: {traceback.format_exc()}")
        checks["caption_fetch"] = "FAIL"

    # Direct InnerTube test
    try:
        result = await YouTubeService._fetch_captions_innertube(test_vid, ["pt", "pt-BR", "en", "es"])
        if result is not None:
            raw_segs, lang, ctype = result
            checks["innertube_test"] = f"OK: {len(raw_segs)} raw segments, lang={lang}, type={ctype}"
            if raw_segs:
                checks["innertube_sample"] = raw_segs[0].get("text", "")[:100]
        else:
            checks["innertube_test"] = "RETURNED_NONE"
    except Exception as e:
        import traceback
        logger.error(f"transcribe-diag innertube_test failed: {traceback.format_exc()}")
        checks["innertube_test"] = "FAIL"

    # Test alternative timedtext domains
    try:
        import httpx as _httpx
        alt_domains = [
            "https://video.google.com/timedtext",
            "https://www.youtube.com/api/timedtext",
        ]
        for domain_url in alt_domains:
            domain_label = domain_url.split("//")[1].split("/")[0]
            for lang in ["pt", "en"]:
                for kind in ["asr", ""]:
                    params = {"v": test_vid, "lang": lang, "fmt": "json3"}
                    if kind:
                        params["kind"] = kind
                    async with _httpx.AsyncClient(timeout=10.0, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
                        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                    }) as hc:
                        r = await hc.get(domain_url, params=params)
                    key = f"timedtext_{domain_label}_{lang}_{kind or 'manual'}"
                    if r.status_code == 200:
                        try:
                            data = r.json()
                            evts = data.get("events", [])
                            checks[key] = f"OK: {len(evts)} events, {len(r.content)} bytes"
                            break  # found captions for this domain+lang
                        except Exception:
                            checks[key] = f"OK_status_but_not_json: {len(r.content)} bytes"
                    else:
                        checks[key] = f"HTTP_{r.status_code}"
                else:
                    continue
                break  # found captions for this domain
    except Exception as e:
        checks["timedtext_alt_error"] = f"{type(e).__name__}: {e}"

    # Raw InnerTube API call diagnostic
    try:
        import httpx
        from services.youtube_service import _INNERTUBE_CLIENTS
        for client_cfg in _INNERTUBE_CLIENTS:
            cname = client_cfg["name"]
            player_url = f"https://youtubei.googleapis.com/youtubei/v1/player?key={client_cfg['api_key']}&prettyPrint=false"
            player_body = {"context": client_cfg["context"], "videoId": test_vid}
            headers = {"Content-Type": "application/json", "User-Agent": client_cfg["user_agent"]}
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.post(player_url, json=player_body, headers=headers)
            checks[f"innertube_raw_{cname}_status"] = resp.status_code
            if resp.status_code == 200:
                pd = resp.json()
                ps = pd.get("playabilityStatus", {})
                checks[f"innertube_raw_{cname}_playability"] = ps.get("status", "?")
                caps = pd.get("captions", {})
                renderer = caps.get("playerCaptionsTracklistRenderer", {})
                tracks = renderer.get("captionTracks", [])
                checks[f"innertube_raw_{cname}_tracks"] = [
                    {"lang": t.get("languageCode"), "kind": t.get("kind", "manual")}
                    for t in tracks
                ]
                if not caps:
                    checks[f"innertube_raw_{cname}_captions_key"] = "MISSING"
                    checks[f"innertube_raw_{cname}_top_keys"] = list(pd.keys())[:15]
            else:
                checks[f"innertube_raw_{cname}_body"] = resp.text[:300]
    except Exception as e:
        checks["innertube_raw_error"] = f"{type(e).__name__}: {e}"

    # Test full handler with mock request
    try:
        from functions.transcription_api import transcribe_handler
        mock_body = json.dumps({"url": f"https://www.youtube.com/watch?v={test_vid}"}).encode("utf-8")
        mock_req = func.HttpRequest(
            method="POST",
            url="/api/transcribe",
            headers={"Content-Type": "application/json"},
            body=mock_body,
        )
        handler_response = await transcribe_handler(mock_req)
        checks["handler_test"] = f"OK: status={handler_response.status_code}"
        if handler_response.status_code != 200:
            checks["handler_body"] = handler_response.get_body().decode("utf-8")[:1000]
    except Exception as e:
        import traceback
        logger.error(f"transcribe-diag handler_test failed: {traceback.format_exc()}")
        checks["handler_test"] = "FAIL"

    return func.HttpResponse(json.dumps(checks, indent=2, ensure_ascii=False), mimetype="application/json")


# ========================================
# HTTP TRIGGERS - TRANSCRIPTION API
# ========================================

@app.route(route="transcribe", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
async def transcribe_video(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/transcribe - Fetch YouTube captions for a video URL.

    Body:
        {
            "url": "https://www.youtube.com/watch?v=VIDEO_ID",
            "languages": ["pt", "en"],  // optional
            "segment_duration": 45.0     // optional, seconds per merged segment
        }

    Returns:
        {
            "video": { videoId, url, title, channel, thumbnail },
            "transcription": [ { id, startTime, endTime, text, topic } ],
            "metadata": { language, total_segments, total_duration_seconds, caption_type }
        }
    """
    rate_limit_response = check_rate_limit("transcribe")
    if rate_limit_response:
        return rate_limit_response
    from functions.transcription_api import transcribe_handler
    return await transcribe_handler(req)


# ========================================
# HTTP TRIGGERS - USER ARTICLES API
# ========================================

@app.route(route="user-articles", methods=["GET", "POST", "OPTIONS"])
@with_cors
@require_auth
async def user_articles_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    /api/user-articles - Gerencia matérias do usuário.

    GET: Lista matérias do usuário.
    POST: Cria uma nova matéria.
    """
    if req.method == "GET":
        from functions.user_articles_api import list_user_articles_handler
        return await list_user_articles_handler(req)
    elif req.method == "POST":
        from functions.user_articles_api import create_user_article_handler
        return await create_user_article_handler(req)
    return func.HttpResponse(
        json.dumps({"error": "Method not allowed"}),
        status_code=405,
        mimetype="application/json"
    )


@app.route(route="user-articles/{id}", methods=["GET", "PUT", "DELETE", "OPTIONS"])
@with_cors
@require_auth
async def user_article_by_id_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    /api/user-articles/{id} - Gerencia uma matéria específica.

    GET: Retorna uma matéria específica.
    PUT: Atualiza uma matéria existente.
    DELETE: Remove uma matéria (soft delete).
    """
    if req.method == "GET":
        from functions.user_articles_api import get_user_article_handler
        return await get_user_article_handler(req)
    elif req.method == "PUT":
        from functions.user_articles_api import update_user_article_handler
        return await update_user_article_handler(req)
    elif req.method == "DELETE":
        from functions.user_articles_api import delete_user_article_handler
        return await delete_user_article_handler(req)
    return func.HttpResponse(
        json.dumps({"error": "Method not allowed"}),
        status_code=405,
        mimetype="application/json"
    )


# ========================================
# HTTP TRIGGERS - SEMANTIC THEMES API
# ========================================

@app.route(route="semantic-themes", methods=["GET", "OPTIONS"])
@with_cors
@require_auth
async def list_themes(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/semantic-themes - Lista temas semanticos com classificacao A/B/C.

    Query params:
        classification: str - Filtrar por classificacao ('A', 'B', 'C')
        status: str - Status do tema ('active', 'inactive') default: 'active'
        limit: int - Maximo de temas (default: 50, max: 100)
        page: int - Pagina (default: 1)
        sort: str - Ordenacao ('score', 'articles', 'recent') default: 'score'

    Returns:
        {
            "items": [...],
            "stats": {"totalA": N, "totalB": N, "totalC": N},
            "total": N,
            "page": N,
            "pages": N
        }
    """
    from functions.themes_api import list_themes_handler
    return await list_themes_handler(req)


@app.route(route="semantic-themes/{id}", methods=["GET", "OPTIONS"])
@with_cors
@require_auth
async def get_theme(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/semantic-themes/{id} - Retorna detalhes de um tema com artigos.

    Query params:
        articles_limit: int - Maximo de artigos (default: 10, max: 50)
        articles_page: int - Pagina de artigos (default: 1)
    """
    from functions.themes_api import get_theme_handler
    return await get_theme_handler(req)


# ========================================
# HTTP TRIGGERS - CLUSTERING STATS API
# ========================================

@app.route(route="clustering-stats", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def clustering_stats(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/clustering-stats - Retorna metricas de qualidade do clustering (admin only).

    Returns:
        {
            "totalThemes": N,
            "totalArticlesClustered": N,
            "avgArticlesPerTheme": N.N,
            "themesWithMultipleArticles": N,
            "silhouetteScore": N.NNNN,
            "coverageRatio": N.NNNN,
            "singletonThemes": N,
            "largestThemeSize": N,
            "evaluatedAt": "2024-01-15T14:45:00Z",
            "qualityLevel": "good|excellent|fair|poor",
            "recommendations": [...]
        }
    """
    from functions.themes_api import get_clustering_stats_handler
    return await get_clustering_stats_handler(req)


# ========================================
# HTTP TRIGGERS - CLUSTERING MAINTENANCE API
# ========================================

@app.route(route="clustering/maintenance", methods=["POST", "OPTIONS"])
@with_cors
@require_admin
async def clustering_maintenance_manual(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/clustering/maintenance - Executa manutencao do clustering manualmente.

    Executa as mesmas tarefas do timer diario:
    1. Merge temas muito similares (> 0.90)
    2. Desativa temas orfaos (0 artigos)
    3. Recalcula scores de todos os temas
    4. Gera relatorio de qualidade

    Query params:
        dry_run: bool - Se true, apenas retorna metricas sem fazer alteracoes (default: false)

    Returns:
        {
            "success": bool,
            "report": {
                "themes_merged": [...],
                "themes_deactivated": [...],
                "themes_scores_updated": N,
                "quality_metrics": {...},
                "duration_seconds": N,
                ...
            }
        }
    """
    from functions.clustering_maintenance import clustering_maintenance_manual_handler
    return await clustering_maintenance_manual_handler(req)


# ========================================
# HTTP TRIGGERS - AUTH API
# ========================================

@app.route(route="auth/login", methods=["POST", "OPTIONS"])
@with_cors
async def auth_login(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/auth/login - Authenticate user."""
    from functions.auth_api import login_handler
    return await login_handler(req)


@app.route(route="auth/refresh", methods=["POST", "OPTIONS"])
@with_cors
async def auth_refresh(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/auth/refresh - Refresh access token."""
    from functions.auth_api import refresh_handler
    return await refresh_handler(req)


@app.route(route="auth/me", methods=["GET", "PATCH", "OPTIONS"])
@with_cors
async def auth_me(req: func.HttpRequest) -> func.HttpResponse:
    """GET/PATCH /api/auth/me - Get or update current user."""
    from utils.auth import get_current_user
    if req.method != "OPTIONS":
        user = await get_current_user(req)
        if not user:
            return func.HttpResponse(
                json.dumps({"error": "Authentication required"}),
                status_code=401,
                mimetype="application/json"
            )
        req.user = user
    if req.method == "GET":
        from functions.auth_api import me_handler
        return await me_handler(req)
    elif req.method == "PATCH":
        from functions.auth_api import update_me_handler
        return await update_me_handler(req)


@app.route(route="auth/logout", methods=["POST", "OPTIONS"])
@with_cors
async def auth_logout(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/auth/logout - Logout and invalidate token."""
    from utils.auth import get_current_user
    if req.method != "OPTIONS":
        user = await get_current_user(req)
        if not user:
            return func.HttpResponse(
                json.dumps({"error": "Authentication required"}),
                status_code=401,
                mimetype="application/json"
            )
        req.user = user
    from functions.auth_api import logout_handler
    return await logout_handler(req)


@app.route(route="auth/users", methods=["GET", "POST", "OPTIONS"])
@with_cors
async def auth_users(req: func.HttpRequest) -> func.HttpResponse:
    """/api/auth/users - Admin user management."""
    from utils.auth import get_current_user
    if req.method != "OPTIONS":
        user = await get_current_user(req)
        if not user:
            return func.HttpResponse(
                json.dumps({"error": "Authentication required"}),
                status_code=401,
                mimetype="application/json"
            )
        if user["role"] != "admin":
            return func.HttpResponse(
                json.dumps({"error": "Admin access required"}),
                status_code=403,
                mimetype="application/json"
            )
        req.user = user
    if req.method == "GET":
        from functions.auth_api import list_users_handler
        return await list_users_handler(req)
    elif req.method == "POST":
        from functions.auth_api import create_user_handler
        return await create_user_handler(req)


@app.route(route="auth/users/{id}", methods=["PUT", "DELETE", "OPTIONS"])
@with_cors
async def auth_user_by_id(req: func.HttpRequest) -> func.HttpResponse:
    """/api/auth/users/{id} - Admin manage specific user."""
    from utils.auth import get_current_user
    if req.method != "OPTIONS":
        user = await get_current_user(req)
        if not user:
            return func.HttpResponse(
                json.dumps({"error": "Authentication required"}),
                status_code=401,
                mimetype="application/json"
            )
        if user["role"] != "admin":
            return func.HttpResponse(
                json.dumps({"error": "Admin access required"}),
                status_code=403,
                mimetype="application/json"
            )
        req.user = user
    if req.method == "PUT":
        from functions.auth_api import update_user_handler
        return await update_user_handler(req)
    elif req.method == "DELETE":
        from functions.auth_api import delete_user_handler
        return await delete_user_handler(req)


@app.route(route="auth/users/{id}/reset-password", methods=["POST", "OPTIONS"])
@with_cors
async def auth_reset_password(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/auth/users/{id}/reset-password - Admin reset user password."""
    from utils.auth import get_current_user
    if req.method != "OPTIONS":
        user = await get_current_user(req)
        if not user:
            return func.HttpResponse(
                json.dumps({"error": "Authentication required"}),
                status_code=401,
                mimetype="application/json"
            )
        if user["role"] != "admin":
            return func.HttpResponse(
                json.dumps({"error": "Admin access required"}),
                status_code=403,
                mimetype="application/json"
            )
        req.user = user
    from functions.auth_api import reset_password_handler
    return await reset_password_handler(req)


# ========================================
# HTTP TRIGGERS - COSTS API
# ========================================

@app.route(route="costs/overview", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def costs_overview(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/costs/overview - Cost overview for dashboard cards (admin only)."""
    from functions.costs_api import costs_overview_handler
    return await costs_overview_handler(req)


@app.route(route="costs/trends", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def costs_trends(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/costs/trends - Cost time series for trends chart (admin only)."""
    from functions.costs_api import costs_trends_handler
    return await costs_trends_handler(req)


@app.route(route="costs/breakdown", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def costs_breakdown(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/costs/breakdown - Cost breakdown by action type (admin only)."""
    from functions.costs_api import costs_breakdown_handler
    return await costs_breakdown_handler(req)


@app.route(route="costs/by-user", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def costs_by_user(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/costs/by-user - Cost breakdown by user (admin only)."""
    from functions.costs_api import costs_by_user_handler
    return await costs_by_user_handler(req)


@app.route(route="costs/by-source", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def costs_by_source(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/costs/by-source - Cost breakdown by RSS source (admin only)."""
    from functions.costs_api import costs_by_source_handler
    return await costs_by_source_handler(req)


@app.route(route="costs/source-estimate", methods=["GET", "OPTIONS"])
@with_cors
@require_admin
async def costs_source_estimate(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/costs/source-estimate - Per-source cost averages for what-if calc (admin only)."""
    from functions.costs_api import costs_source_estimate_handler
    return await costs_source_estimate_handler(req)


# ========================================
# STARTUP
# ========================================

logger.info("TMC RSS Collector initialized")
logger.info("Endpoints disponíveis:")
logger.info("  - Timer: rss_collector (cada 15 min)")
logger.info("  - Timer: embedding_generator (cada 5 min)")
logger.info("  - Timer: scoring_calculator (cada 10 min)")
logger.info("  - Timer: clustering_engine (cada 30 min)")
logger.info("  - Timer: clustering_maintenance (diario 3AM UTC)")
logger.info("  - Timer: daily_cost_aggregation (diario 00:30 UTC)")
logger.info("  - Timer: cost_data_cleanup (mensal 1o dia 3AM UTC)")
logger.info("  - GET  /api/health")
logger.info("  - GET  /api/stats")
logger.info("  - GET  /api/articles")
logger.info("  - GET  /api/articles/{id}")
logger.info("  - GET  /api/categories")
logger.info("  - GET  /api/trending-tags")
logger.info("  - GET  /api/sources")
logger.info("  - GET  /api/sources/{id}")
logger.info("  - POST /api/sources")
logger.info("  - PUT  /api/sources/{id}")
logger.info("  - DELETE /api/sources/{id}")
logger.info("  - POST /api/sources/{id}/collect")
logger.info("  - POST /api/generate")
logger.info("  - POST /api/extract-topics")
logger.info("  - POST /api/generate-tags")
logger.info("  - POST /api/merge-topics")
logger.info("  - POST /api/edit-article")
logger.info("  - POST /api/transcribe")
logger.info("  - GET  /api/user-articles")
logger.info("  - GET  /api/user-articles/{id}")
logger.info("  - POST /api/user-articles")
logger.info("  - PUT  /api/user-articles/{id}")
logger.info("  - DELETE /api/user-articles/{id}")
logger.info("  - GET  /api/semantic-themes")
logger.info("  - GET  /api/semantic-themes/{id}")
logger.info("  - GET  /api/clustering-stats")
logger.info("  - POST /api/clustering/maintenance")
logger.info("  - GET  /api/metrics")
logger.info("  - POST /api/auth/login")
logger.info("  - POST /api/auth/refresh")
logger.info("  - GET  /api/auth/me")
logger.info("  - PATCH /api/auth/me")
logger.info("  - POST /api/auth/logout")
logger.info("  - GET  /api/auth/users")
logger.info("  - POST /api/auth/users")
logger.info("  - PUT  /api/auth/users/{id}")
logger.info("  - DELETE /api/auth/users/{id}")
logger.info("  - POST /api/auth/users/{id}/reset-password")
logger.info("  - GET  /api/costs/overview")
logger.info("  - GET  /api/costs/trends")
logger.info("  - GET  /api/costs/breakdown")
logger.info("  - GET  /api/costs/by-user")
logger.info("  - GET  /api/costs/by-source")
logger.info("  - GET  /api/costs/source-estimate")
