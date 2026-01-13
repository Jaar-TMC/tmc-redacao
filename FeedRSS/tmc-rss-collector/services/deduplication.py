"""
Serviço de deduplicação de artigos.
Usa hash MD5 baseado em título + URL para identificar duplicatas.
"""

import hashlib
import logging
from typing import List, Set
from models import ArticleCreate

logger = logging.getLogger(__name__)


def generate_hash(title: str, url: str) -> str:
    """
    Gera hash MD5 único para identificar um artigo.

    A deduplicação é baseada em:
    - Título normalizado (lowercase, sem espaços extras)
    - URL do artigo

    Args:
        title: Título do artigo
        url: URL do artigo

    Returns:
        Hash MD5 hexadecimal (32 caracteres)
    """
    # Normalizar título
    normalized_title = normalize_text(title)

    # Normalizar URL (remover trailing slash, lowercase)
    normalized_url = url.lower().rstrip('/')

    # Combinar e gerar hash
    content = f"{normalized_title}|{normalized_url}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def normalize_text(text: str) -> str:
    """
    Normaliza texto para comparação.

    - Converte para lowercase
    - Remove espaços extras
    - Remove caracteres especiais comuns em títulos

    Args:
        text: Texto para normalizar

    Returns:
        Texto normalizado
    """
    if not text:
        return ""

    # Lowercase
    text = text.lower()

    # Remover espaços extras (múltiplos espaços, tabs, newlines)
    text = ' '.join(text.split())

    # Strip
    text = text.strip()

    return text


def deduplicate_articles(articles: List[ArticleCreate],
                        existing_hashes: Set[str]) -> List[ArticleCreate]:
    """
    Remove artigos duplicados de uma lista.

    Compara contra:
    1. Hashes já existentes no banco (existing_hashes)
    2. Duplicatas dentro da própria lista (artigos do mesmo feed)

    Args:
        articles: Lista de artigos para filtrar
        existing_hashes: Set de hashes que já existem no banco

    Returns:
        Lista de artigos únicos (não duplicados)
    """
    if not articles:
        return []

    unique_articles = []
    seen_hashes: Set[str] = set()

    for article in articles:
        # Gerar hash se não existir
        if not article.hash:
            article.hash = generate_hash(article.title, article.url)

        # Verificar se já existe no banco
        if article.hash in existing_hashes:
            logger.debug(f"Duplicate (in DB): {article.title[:50]}")
            continue

        # Verificar se já vimos nesta lista
        if article.hash in seen_hashes:
            logger.debug(f"Duplicate (in batch): {article.title[:50]}")
            continue

        # Artigo único
        seen_hashes.add(article.hash)
        unique_articles.append(article)

    duplicates_count = len(articles) - len(unique_articles)
    if duplicates_count > 0:
        logger.info(f"Filtered {duplicates_count} duplicate articles")

    return unique_articles


async def deduplicate_with_db(articles: List[ArticleCreate],
                              db_service) -> List[ArticleCreate]:
    """
    Remove artigos duplicados verificando contra o banco de dados.

    Fluxo:
    1. Gerar hash para todos os artigos
    2. Buscar hashes existentes no banco (query batch)
    3. Filtrar artigos com hash novo

    Args:
        articles: Lista de artigos para filtrar
        db_service: Instância do DatabaseService

    Returns:
        Lista de artigos que não existem no banco
    """
    if not articles:
        return []

    # 1. Gerar hashes para todos os artigos
    for article in articles:
        if not article.hash:
            article.hash = generate_hash(article.title, article.url)

    # 2. Extrair todos os hashes
    hashes = [article.hash for article in articles]

    # 3. Verificar quais já existem no banco
    existing_hashes = db_service.check_existing_hashes(hashes)
    logger.info(f"Found {len(existing_hashes)} existing hashes in DB")

    # 4. Filtrar artigos únicos
    return deduplicate_articles(articles, existing_hashes)


def is_similar_title(title1: str, title2: str, threshold: float = 0.9) -> bool:
    """
    Verifica se dois títulos são similares (fuzzy matching).

    Útil para detectar duplicatas com pequenas variações
    (ex: "Título da Notícia" vs "Título da Notícia - Portal X")

    Args:
        title1: Primeiro título
        title2: Segundo título
        threshold: Limiar de similaridade (0-1)

    Returns:
        True se os títulos são similares
    """
    # Normalizar
    t1 = normalize_text(title1)
    t2 = normalize_text(title2)

    # Se um contém o outro
    if t1 in t2 or t2 in t1:
        return True

    # Jaccard similarity baseado em palavras
    words1 = set(t1.split())
    words2 = set(t2.split())

    if not words1 or not words2:
        return False

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    similarity = intersection / union
    return similarity >= threshold


def get_article_fingerprint(article: ArticleCreate) -> str:
    """
    Gera fingerprint alternativo para o artigo.

    Útil quando o hash MD5 não é suficiente (ex: mesmo conteúdo, URLs diferentes).
    Baseado em título + primeiras palavras do conteúdo.

    Args:
        article: Artigo para gerar fingerprint

    Returns:
        Fingerprint string
    """
    title = normalize_text(article.title)

    # Extrair primeiras 50 palavras do conteúdo
    content_words = ""
    if article.content:
        words = article.content.split()[:50]
        content_words = ' '.join(words).lower()

    combined = f"{title}|{content_words}"
    return hashlib.md5(combined.encode('utf-8')).hexdigest()
