"""
Serviço de enriquecimento de artigos.
Extrai imagens via Open Graph e gera URLs de favicon.
"""

import httpx
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# Module-level shared HTTP client for image enrichment (connection pooling)
_shared_http_client: Optional[httpx.AsyncClient] = None


def _get_enrichment_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client for enrichment requests."""
    global _shared_http_client
    if _shared_http_client is None:
        _shared_http_client = httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={
                'User-Agent': 'TMC-RSS-Collector/1.0 (+https://tmc.com.br)',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8'
            }
        )
    return _shared_http_client


async def extract_image_url(article_url: str, timeout: int = 10) -> Optional[str]:
    """
    Extrai URL da imagem principal do artigo via Open Graph tags.

    Busca em ordem:
    1. og:image (Open Graph)
    2. twitter:image (Twitter Cards)
    3. Primeira imagem grande no conteúdo

    Args:
        article_url: URL do artigo
        timeout: Timeout em segundos (default 10)

    Returns:
        URL da imagem ou None se não encontrar
    """
    try:
        client = _get_enrichment_client()
        response = await client.get(article_url)

        if response.status_code != 200:
            logger.warning(f"Failed to fetch {article_url}: status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Tentar og:image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']
            if _is_valid_image_url(image_url):
                return image_url

        # 2. Tentar twitter:image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            image_url = twitter_image['content']
            if _is_valid_image_url(image_url):
                return image_url

        # 3. Tentar twitter:image:src (variante)
        twitter_image_src = soup.find('meta', attrs={'name': 'twitter:image:src'})
        if twitter_image_src and twitter_image_src.get('content'):
            image_url = twitter_image_src['content']
            if _is_valid_image_url(image_url):
                return image_url

        # 4. Tentar primeira imagem grande no article/main
        article = soup.find(['article', 'main', 'div[class*="content"]'])
        if article:
            img = article.find('img', src=True)
            if img:
                src = img.get('src') or img.get('data-src')
                if src and _is_valid_image_url(src):
                    return _make_absolute_url(src, article_url)

        logger.debug(f"No image found for {article_url}")
        return None

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching {article_url}")
        return None
    except httpx.RequestError as e:
        logger.warning(f"Request error for {article_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error extracting image from {article_url}: {e}")
        return None


def _is_valid_image_url(url: str) -> bool:
    """
    Verifica se a URL parece ser uma imagem válida.
    Exclui placeholders, ícones pequenos, etc.
    """
    if not url:
        return False

    url_lower = url.lower()

    # Excluir placeholders comuns
    invalid_patterns = [
        'placeholder',
        'default',
        'avatar',
        'icon',
        'logo',
        '1x1',
        'spacer',
        'blank',
        'pixel'
    ]

    for pattern in invalid_patterns:
        if pattern in url_lower:
            return False

    # Verificar extensão de imagem válida
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
    has_valid_ext = any(ext in url_lower for ext in valid_extensions)

    # Aceitar URLs sem extensão (podem ser dinâmicas)
    # mas que parecem ser de CDN de imagens
    image_cdns = ['img', 'image', 'media', 'cdn', 'static', 'assets']
    is_image_cdn = any(cdn in url_lower for cdn in image_cdns)

    return has_valid_ext or is_image_cdn


def _make_absolute_url(url: str, base_url: str) -> str:
    """
    Converte URL relativa em absoluta.
    """
    if url.startswith('http'):
        return url

    parsed_base = urlparse(base_url)

    if url.startswith('//'):
        return f"{parsed_base.scheme}:{url}"

    if url.startswith('/'):
        return f"{parsed_base.scheme}://{parsed_base.netloc}{url}"

    # URL relativa
    base_path = '/'.join(base_url.split('/')[:-1])
    return f"{base_path}/{url}"


def get_favicon_url(site_url: str, size: int = 32) -> str:
    """
    Retorna URL do favicon usando Google Favicons API.

    Args:
        site_url: URL do site (pode ser qualquer página)
        size: Tamanho do ícone em pixels (16, 32, 64, 128)

    Returns:
        URL do favicon via Google Favicons API
    """
    try:
        parsed = urlparse(site_url)
        domain = parsed.netloc or parsed.path.split('/')[0]

        # Remover www. para consistência
        if domain.startswith('www.'):
            domain = domain[4:]

        return f"https://www.google.com/s2/favicons?domain={domain}&sz={size}"

    except Exception:
        # Fallback para domínio genérico
        return f"https://www.google.com/s2/favicons?domain=example.com&sz={size}"


def get_source_base_url(feed_url: str) -> str:
    """
    Extrai a URL base do site a partir da URL do feed.

    Exemplo:
        https://g1.globo.com/rss/g1/politica/ -> https://g1.globo.com
    """
    parsed = urlparse(feed_url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def enrich_article_image(article_url: str,
                               existing_image: Optional[str] = None,
                               timeout: int = 10) -> Optional[str]:
    """
    Enriquece um artigo com imagem se necessário.

    Se já existe uma imagem válida, retorna ela.
    Caso contrário, tenta extrair via Open Graph.

    Args:
        article_url: URL do artigo
        existing_image: URL de imagem existente (do feed RSS)
        timeout: Timeout em segundos

    Returns:
        URL da imagem (existente ou extraída) ou None
    """
    # Se já tem imagem válida, usar ela
    if existing_image and _is_valid_image_url(existing_image):
        return existing_image

    # Tentar extrair via Open Graph
    return await extract_image_url(article_url, timeout)
