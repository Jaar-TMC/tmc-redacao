"""
Servico de parsing de feeds RSS e Atom.
Usa feedparser para parse e httpx para fetch assincrono.
"""

import feedparser
import httpx
import logging
import re
import unicodedata
import html
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import time
from email.utils import parsedate_to_datetime
import hashlib

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models import ArticleCreate

logger = logging.getLogger(__name__)


class RSSParser:
    """Parser de feeds RSS e Atom."""

    def __init__(self, timeout: int = 30):
        """
        Inicializa o parser.

        Args:
            timeout: Timeout em segundos para requisicoes HTTP
        """
        self.timeout = timeout
        self.user_agent = "TMC-RSS-Collector/1.0 (+https://tmc.com.br)"

    async def parse_feed(self, url: str, source_id: UUID,
                        source_category: Optional[str] = None,
                        max_articles: int = 100) -> List[ArticleCreate]:
        """
        Faz fetch e parse de um feed RSS/Atom.

        Args:
            url: URL do feed RSS
            source_id: ID da fonte no banco
            source_category: Categoria padrao da fonte
            max_articles: Maximo de artigos a retornar

        Returns:
            Lista de ArticleCreate
        """
        logger.info(f"Fetching feed: {url}")
        start_time = time.time()

        try:
            # Fetch do feed
            content = await self._fetch_feed(url)

            if not content:
                logger.warning(f"Empty response from {url}")
                return []

            # Parse do feed
            feed = feedparser.parse(content)

            # Verificar se houve erro de parse
            if feed.bozo and not feed.entries:
                logger.error(f"Feed parsing error for {url}: {feed.bozo_exception}")
                return []

            # Processar entries
            articles = []
            for entry in feed.entries[:max_articles]:
                try:
                    article = self._parse_entry(entry, source_id, source_category)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Error parsing entry from {url}: {e}")
                    continue

            duration = time.time() - start_time
            logger.info(f"Parsed {len(articles)} articles from {url} in {duration:.2f}s")

            return articles

        except Exception as e:
            logger.error(f"Error fetching/parsing feed {url}: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def _fetch_feed(self, url: str) -> Optional[bytes]:
        """
        Faz fetch do conteudo do feed via HTTP.

        Args:
            url: URL do feed

        Returns:
            Conteudo do feed como bytes ou None se falhar
            (feedparser handles encoding detection better with raw bytes)
        """
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    follow_redirects=True
                )

                response.raise_for_status()
                # Return raw bytes - feedparser handles encoding detection
                # better than httpx, using XML declaration and content sniffing
                return response.content

        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {url}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} fetching {url}")
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise

    def _parse_entry(self, entry, source_id: UUID,
                     source_category: Optional[str]) -> Optional[ArticleCreate]:
        """
        Converte uma entry do feedparser para ArticleCreate.

        Args:
            entry: Entry do feedparser
            source_id: ID da fonte
            source_category: Categoria padrao

        Returns:
            ArticleCreate ou None se entry invalida
        """
        # Titulo e obrigatorio
        title = self._clean_text(getattr(entry, 'title', ''))
        if not title:
            return None

        # URL e obrigatoria
        url = getattr(entry, 'link', '')
        if not url:
            return None

        # Conteudo (tentar varias fontes)
        content = self._extract_content(entry)

        # Preview (truncar content)
        preview = self._generate_preview(content or title, max_length=500)

        # Data de publicacao
        published_at = self._parse_date(entry)

        # Autor
        author = self._extract_author(entry)

        # Categoria (da entry ou default da fonte)
        category = self._extract_category(entry) or source_category

        # Tags
        tags = self._extract_tags(entry)

        # Imagem
        image_url = self._extract_image(entry)

        # Gerar hash para deduplicacao (baseado em URL + titulo)
        article_hash = self._generate_hash(url, title)

        return ArticleCreate(
            source_id=source_id,
            title=title,
            content=content,
            preview=preview,
            url=url,
            image_url=image_url,
            author=author,
            category=category,
            tags=tags,
            published_at=published_at,
            collected_at=datetime.utcnow(),
            hash=article_hash
        )

    def _generate_hash(self, url: str, title: str) -> str:
        """
        Gera hash unico para o artigo baseado em URL e titulo.

        Args:
            url: URL do artigo
            title: Titulo do artigo

        Returns:
            Hash SHA256 de 64 caracteres
        """
        content = f"{url}|{title}".lower().strip()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _extract_content(self, entry) -> Optional[str]:
        """Extrai conteudo da entry (tenta varias fontes)."""
        # Tentar content (pode ter multiplos)
        if hasattr(entry, 'content') and entry.content:
            for content in entry.content:
                if hasattr(content, 'value') and content.value:
                    return self._clean_html(content.value)

        # Tentar summary
        if hasattr(entry, 'summary') and entry.summary:
            return self._clean_html(entry.summary)

        # Tentar description
        if hasattr(entry, 'description') and entry.description:
            return self._clean_html(entry.description)

        return None

    def _extract_author(self, entry) -> Optional[str]:
        """Extrai autor da entry."""
        # Tentar author
        if hasattr(entry, 'author') and entry.author:
            return self._clean_text(entry.author)

        # Tentar author_detail
        if hasattr(entry, 'author_detail'):
            if hasattr(entry.author_detail, 'name'):
                return self._clean_text(entry.author_detail.name)

        # Tentar dc:creator (Dublin Core)
        if hasattr(entry, 'dc_creator'):
            return self._clean_text(entry.dc_creator)

        return None

    def _extract_category(self, entry) -> Optional[str]:
        """Extrai categoria da entry."""
        # Tentar tags (categoria primaria)
        if hasattr(entry, 'tags') and entry.tags:
            for tag in entry.tags:
                if hasattr(tag, 'term') and tag.term:
                    # Pegar primeira tag como categoria
                    return self._clean_text(tag.term)

        # Tentar category diretamente
        if hasattr(entry, 'category') and entry.category:
            return self._clean_text(entry.category)

        return None

    def _extract_tags(self, entry) -> List[str]:
        """Extrai lista de tags da entry."""
        tags = []

        if hasattr(entry, 'tags') and entry.tags:
            for tag in entry.tags:
                if hasattr(tag, 'term') and tag.term:
                    cleaned = self._clean_text(tag.term)
                    if cleaned and cleaned not in tags:
                        tags.append(cleaned)

        return tags[:10]  # Limitar a 10 tags

    def _extract_image(self, entry) -> Optional[str]:
        """Extrai URL da imagem da entry."""
        # Tentar media:content
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if media.get('medium') == 'image' or media.get('type', '').startswith('image'):
                    url = media.get('url')
                    if url:
                        return url

        # Tentar media:thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            for thumb in entry.media_thumbnail:
                url = thumb.get('url')
                if url:
                    return url

        # Tentar enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get('type', '').startswith('image'):
                    url = enc.get('href') or enc.get('url')
                    if url:
                        return url

        # Tentar image (atom)
        if hasattr(entry, 'image') and entry.image:
            if hasattr(entry.image, 'href'):
                return entry.image.href

        # Tentar extrair de content/summary
        content = self._extract_content(entry)
        if content:
            match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _parse_date(self, entry) -> Optional[datetime]:
        """Converte data do entry para datetime."""
        # Tentar published_parsed
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except Exception:
                pass

        # Tentar updated_parsed
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except Exception:
                pass

        # Tentar published string
        if hasattr(entry, 'published') and entry.published:
            try:
                return parsedate_to_datetime(entry.published)
            except Exception:
                pass

        # Tentar updated string
        if hasattr(entry, 'updated') and entry.updated:
            try:
                return parsedate_to_datetime(entry.updated)
            except Exception:
                pass

        # Fallback para agora
        return datetime.utcnow()

    def _clean_text(self, text: str) -> str:
        """Limpa texto removendo espacos extras e normalizando unicode."""
        if not text:
            return ""

        # Normalize unicode (NFC form - composed characters)
        text = unicodedata.normalize('NFC', text)

        # Remove null bytes and other control characters (except newlines/tabs)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # Clean whitespace
        return ' '.join(text.split()).strip()

    def _clean_html(self, html_content: str) -> str:
        """Remove tags HTML e limpa texto."""
        if not html_content:
            return ""

        # Decode HTML entities first (handles &aacute; &#225; etc.)
        text = html.unescape(html_content)

        # Remove tags HTML
        text = re.sub(r'<[^>]+>', ' ', text)

        # Additional common entity replacements (in case html.unescape missed any)
        text = text.replace('&nbsp;', ' ')

        # Normalize unicode and clean
        return self._clean_text(text)

    def _generate_preview(self, text: str, max_length: int = 500) -> str:
        """Gera preview truncando texto."""
        if not text:
            return ""

        text = self._clean_text(text)

        if len(text) <= max_length:
            return text

        # Truncar em palavra
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')

        if last_space > max_length * 0.7:
            truncated = truncated[:last_space]

        return truncated + '...'
