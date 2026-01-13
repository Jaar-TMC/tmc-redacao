# Services package for TMC RSS Collector
"""
Services package - Servicos do coletor RSS.
"""

from .rss_parser import RSSParser
from .enrichment import (
    extract_image_url,
    get_favicon_url,
    get_source_base_url,
    enrich_article_image,
)
from .database import DatabaseService, get_db
from .deduplication import (
    generate_hash,
    normalize_text,
    deduplicate_articles,
    deduplicate_with_db,
    is_similar_title,
    get_article_fingerprint,
)

__all__ = [
    'RSSParser',
    'extract_image_url',
    'get_favicon_url',
    'get_source_base_url',
    'enrich_article_image',
    'DatabaseService',
    'get_db',
    'generate_hash',
    'normalize_text',
    'deduplicate_articles',
    'deduplicate_with_db',
    'is_similar_title',
    'get_article_fingerprint',
]
