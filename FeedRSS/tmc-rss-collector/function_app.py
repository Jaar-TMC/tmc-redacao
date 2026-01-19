"""
TMC RSS Collector - Entry Point
Azure Functions v2 com Python

Este arquivo registra todas as functions (triggers e routes) da aplicação.
"""

import azure.functions as func
import logging
import asyncio

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar app
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


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
# HTTP TRIGGERS - HEALTH & STATS
# ========================================

@app.route(route="health", methods=["GET"])
async def health(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/health - Health check do serviço."""
    from functions.health import health_check_handler
    return await health_check_handler(req)


@app.route(route="stats", methods=["GET"])
async def stats(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/stats - Estatísticas de coleta."""
    from functions.health import stats_handler
    return await stats_handler(req)


# ========================================
# HTTP TRIGGERS - ARTICLES API
# ========================================

@app.route(route="articles", methods=["GET"])
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
    """
    from functions.articles_api import list_articles_handler
    return await list_articles_handler(req)


@app.route(route="articles/{id}", methods=["GET"])
async def get_article(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/articles/{id} - Retorna um artigo específico."""
    from functions.articles_api import get_article_handler
    return await get_article_handler(req)


@app.route(route="categories", methods=["GET"])
async def get_categories(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/categories - Lista categorias com contagem."""
    from functions.articles_api import get_categories_handler
    return await get_categories_handler(req)


@app.route(route="trending-tags", methods=["GET"])
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


# ========================================
# HTTP TRIGGERS - SOURCES API
# ========================================

@app.route(route="sources", methods=["GET"])
async def list_sources(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sources - Lista todas as fontes RSS."""
    from functions.sources_api import list_sources_handler
    return await list_sources_handler(req)


@app.route(route="sources/{id}", methods=["GET"])
async def get_source(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/sources/{id} - Retorna uma fonte específica."""
    from functions.sources_api import get_source_handler
    return await get_source_handler(req)


@app.route(route="sources", methods=["POST"])
async def create_source(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/sources - Cria uma nova fonte RSS.

    Body:
        {
            "name": "G1 - Política",
            "url": "https://g1.globo.com/rss/g1/politica/",
            "category": "Política",
            "frequency": "30min",
            "active": true
        }
    """
    from functions.sources_api import create_source_handler
    return await create_source_handler(req)


@app.route(route="sources/{id}", methods=["PUT"])
async def update_source(req: func.HttpRequest) -> func.HttpResponse:
    """PUT /api/sources/{id} - Atualiza uma fonte existente."""
    from functions.sources_api import update_source_handler
    return await update_source_handler(req)


@app.route(route="sources/{id}", methods=["DELETE"])
async def delete_source(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/sources/{id} - Desativa uma fonte (soft delete)."""
    from functions.sources_api import delete_source_handler
    return await delete_source_handler(req)


@app.route(route="sources/{id}/collect", methods=["POST"])
async def collect_source(req: func.HttpRequest) -> func.HttpResponse:
    """POST /api/sources/{id}/collect - Dispara coleta manual."""
    from functions.sources_api import collect_source_handler
    return await collect_source_handler(req)


# ========================================
# HTTP TRIGGERS - AI GENERATION API
# ========================================

@app.route(route="generate", methods=["POST"])
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
    from functions.generation_api import generate_article_handler
    return await generate_article_handler(req)


@app.route(route="extract-topics", methods=["POST"])
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


@app.route(route="generate-tags", methods=["POST"])
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


@app.route(route="merge-topics", methods=["POST"])
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


@app.route(route="edit-article", methods=["POST"])
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

@app.route(route="user-articles", methods=["GET"])
async def list_user_articles(req: func.HttpRequest) -> func.HttpResponse:
    """
    GET /api/user-articles - Lista matérias do usuário.

    Query params:
        page: int - Página (default: 1)
        limit: int - Itens por página (default: 20, max: 100)
        status: str - 'draft' ou 'published'
        category: str - Filtrar por categoria
        search: str - Busca em título/conteúdo
        dateRange: str - '24h', '7d', '30d', '3m', 'year'
    """
    from functions.user_articles_api import list_user_articles_handler
    return await list_user_articles_handler(req)


@app.route(route="user-articles/{id}", methods=["GET"])
async def get_user_article(req: func.HttpRequest) -> func.HttpResponse:
    """GET /api/user-articles/{id} - Retorna uma matéria específica."""
    from functions.user_articles_api import get_user_article_handler
    return await get_user_article_handler(req)


@app.route(route="user-articles", methods=["POST"])
async def create_user_article(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST /api/user-articles - Cria uma nova matéria.

    Body:
        {
            "title": "Título da matéria",
            "linhaFina": "Subtítulo",
            "content": "Conteúdo...",
            "status": "draft" | "published",
            "category": "Categoria",
            "tags": ["tag1", "tag2"],
            "authorName": "Autor",
            "sourceArticleIds": ["id1", "id2"]
        }
    """
    from functions.user_articles_api import create_user_article_handler
    return await create_user_article_handler(req)


@app.route(route="user-articles/{id}", methods=["PUT"])
async def update_user_article(req: func.HttpRequest) -> func.HttpResponse:
    """PUT /api/user-articles/{id} - Atualiza uma matéria existente."""
    from functions.user_articles_api import update_user_article_handler
    return await update_user_article_handler(req)


@app.route(route="user-articles/{id}", methods=["DELETE"])
async def delete_user_article(req: func.HttpRequest) -> func.HttpResponse:
    """DELETE /api/user-articles/{id} - Remove uma matéria (soft delete)."""
    from functions.user_articles_api import delete_user_article_handler
    return await delete_user_article_handler(req)


# ========================================
# STARTUP
# ========================================

logger.info("TMC RSS Collector initialized")
logger.info("Endpoints disponíveis:")
logger.info("  - Timer: rss_collector (cada 15 min)")
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
