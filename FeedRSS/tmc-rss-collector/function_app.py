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
logger.info("  - GET  /api/sources")
logger.info("  - GET  /api/sources/{id}")
logger.info("  - POST /api/sources")
logger.info("  - PUT  /api/sources/{id}")
logger.info("  - DELETE /api/sources/{id}")
logger.info("  - POST /api/sources/{id}/collect")
logger.info("  - POST /api/generate")
logger.info("  - POST /api/extract-topics")
logger.info("  - POST /api/generate-tags")
