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
from utils.auth import require_auth, require_admin

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
    allowed_origin = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]

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
            allowed_origin = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
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
        response = await handler(req)
        return add_cors_headers(response, origin)

    return wrapper


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
async def stats(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/stats - Estatísticas de coleta."""
    from functions.health import stats_handler
    return await stats_handler(req)


# ========================================
# HTTP TRIGGERS - ARTICLES API
# ========================================

@app.route(route="articles", methods=["GET", "OPTIONS"])
@with_cors
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
async def get_article(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/articles/{id} - Retorna um artigo específico."""
    from functions.articles_api import get_article_handler
    return await get_article_handler(req)


@app.route(route="categories", methods=["GET", "OPTIONS"])
@with_cors
async def get_categories(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/categories - Lista categorias com contagem."""
    from functions.articles_api import get_categories_handler
    return await get_categories_handler(req)


@app.route(route="trending-tags", methods=["GET", "OPTIONS"])
@with_cors
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
    if req.method == "POST":
        from utils.auth import get_current_user
        user = get_current_user(req)
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
        from functions.sources_api import list_sources_handler
        return await list_sources_handler(req)
    elif req.method == "POST":
        from functions.sources_api import create_source_handler
        return await create_source_handler(req)


@app.route(route="sources/{id}", methods=["GET", "PUT", "DELETE", "OPTIONS"])
@with_cors
async def source_by_id_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    /api/sources/{id} - Gerencia uma fonte específica.

    GET: Retorna uma fonte específica.
    PUT: Atualiza uma fonte existente (admin only).
    DELETE: Desativa uma fonte (admin only, soft delete).
    """
    if req.method in ("PUT", "DELETE"):
        from utils.auth import get_current_user
        user = get_current_user(req)
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
        from functions.sources_api import get_source_handler
        return await get_source_handler(req)
    elif req.method == "PUT":
        from functions.sources_api import update_source_handler
        return await update_source_handler(req)
    elif req.method == "DELETE":
        from functions.sources_api import delete_source_handler
        return await delete_source_handler(req)


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
async def metrics(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/metrics - In-process pipeline metrics."""
    import json as _json
    from services.metrics import Metrics
    return func.HttpResponse(
        _json.dumps(Metrics.get().snapshot()),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="generate", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
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
    # Phase 4.8: Rate limiting
    from services.rate_limiter import RateLimiter
    retry_after = RateLimiter.get().check("generate")
    if retry_after is not None:
        import json as _json
        return func.HttpResponse(
            _json.dumps({"error": "Rate limit exceeded", "retry_after_seconds": round(retry_after, 1)}),
            status_code=429,
            headers={"Retry-After": str(int(retry_after) + 1)},
            mimetype="application/json",
        )
    from functions.generation_api import generate_article_handler
    return await generate_article_handler(req)


@app.route(route="extract-topics", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
async def extract_topics(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/extract-topics - Extrai tópicos do texto usando IA.

    Body:
        {"texto": "Texto para análise..."}

    Returns:
        {"topics": [{"type": "fato", "content": "..."}, ...]}
    """
    from functions.generation_api import extract_topics_handler
    return await extract_topics_handler(req)


@app.route(route="generate-tags", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
async def generate_tags(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/generate-tags - Gera tags para conteúdo usando IA.

    Body:
        {"texto": "Conteúdo para análise...", "max_tags": 10}

    Returns:
        {"tags": ["tag1", "tag2", "tag3", ...]}
    """
    from functions.generation_api import generate_tags_handler
    return await generate_tags_handler(req)


@app.route(route="merge-topics", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
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
    from functions.generation_api import merge_topics_handler
    return await merge_topics_handler(req)


@app.route(route="edit-article", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
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
    from functions.edit_api import edit_article_handler
    return await edit_article_handler(req)


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


# ========================================
# HTTP TRIGGERS - SEMANTIC THEMES API
# ========================================

@app.route(route="semantic-themes", methods=["GET", "OPTIONS"])
@with_cors
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
async def clustering_stats(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/clustering-stats - Retorna metricas de qualidade do clustering.

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
        user = get_current_user(req)
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
        user = get_current_user(req)
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
        user = get_current_user(req)
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
        user = get_current_user(req)
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
        user = get_current_user(req)
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
# STARTUP
# ========================================

logger.info("TMC RSS Collector initialized")
logger.info("Endpoints disponíveis:")
logger.info("  - Timer: rss_collector (cada 15 min)")
logger.info("  - Timer: embedding_generator (cada 5 min)")
logger.info("  - Timer: scoring_calculator (cada 10 min)")
logger.info("  - Timer: clustering_engine (cada 30 min)")
logger.info("  - Timer: clustering_maintenance (diario 3AM UTC)")
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
