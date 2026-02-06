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
from .llm_service import LLMService, get_llm_service
from .embedding_service import EmbeddingService, get_embedding_service, is_embedding_configured
from .clustering_service import (
    ClusteringService,
    get_clustering_service,
    is_clustering_enabled,
    cosine_similarity,
)
from .scoring_service import (
    ScoringService,
    get_scoring_service,
    calculate_classification,
    get_score_breakdown,
)
from .event_signature_service import (
    EventSignatureService,
    get_event_signature_service,
    is_event_extraction_enabled,
)
from .event_matching_service import (
    EventMatchingService,
    get_event_matching_service,
    is_event_matching_enabled,
)
from .llm_verification_service import (
    LLMVerificationService,
    get_llm_verification_service,
    is_verification_enabled,
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
    'LLMService',
    'get_llm_service',
    'EmbeddingService',
    'get_embedding_service',
    'is_embedding_configured',
    'ClusteringService',
    'get_clustering_service',
    'is_clustering_enabled',
    'cosine_similarity',
    'ScoringService',
    'get_scoring_service',
    'calculate_classification',
    'get_score_breakdown',
    # Event-Based Clustering
    'EventSignatureService',
    'get_event_signature_service',
    'is_event_extraction_enabled',
    'EventMatchingService',
    'get_event_matching_service',
    'is_event_matching_enabled',
    'LLMVerificationService',
    'get_llm_verification_service',
    'is_verification_enabled',
]
