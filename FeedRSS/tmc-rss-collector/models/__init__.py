"""
Models package - Pydantic models para o coletor RSS.
"""

from .source import Source, SourceCreate, SourceUpdate, SourceBase
from .article import Article, ArticleCreate, ArticleBase, ArticleListResponse
from .collection_log import CollectionLog, CollectionLogCreate
from .user_article import (
    UserArticle, UserArticleCreate, UserArticleUpdate,
    UserArticleBase, UserArticleListResponse
)
from .theme import (
    Theme, ThemeCreate, ThemeUpdate, ThemeBase,
    ThemeResponse, ThemeListResponse
)
from .article_score import (
    ArticleScore, ArticleScoreCreate, ArticleScoreUpdate, ArticleScoreBase,
    ArticleScoreResponse, ArticleScoreListResponse
)
from .article_embedding import (
    ArticleEmbedding, ArticleEmbeddingCreate, ArticleEmbeddingUpdate, ArticleEmbeddingBase,
    ArticleEmbeddingResponse, ArticleEmbeddingListResponse,
    BulkEmbeddingCreate, SemanticSearchRequest, SemanticSearchResult, SemanticSearchResponse
)
from .event_signature import (
    EventSignature, EventSignatureCreate, EventSignatureUpdate, EventSignatureBase,
    EventSignatureResponse, normalize_entity, entities_match, calculate_entity_similarity
)

__all__ = [
    # Source
    'Source',
    'SourceCreate',
    'SourceUpdate',
    'SourceBase',
    # Article
    'Article',
    'ArticleCreate',
    'ArticleBase',
    'ArticleListResponse',
    # Collection Log
    'CollectionLog',
    'CollectionLogCreate',
    # User Article
    'UserArticle',
    'UserArticleCreate',
    'UserArticleUpdate',
    'UserArticleBase',
    'UserArticleListResponse',
    # Theme (Semantic Clustering)
    'Theme',
    'ThemeCreate',
    'ThemeUpdate',
    'ThemeBase',
    'ThemeResponse',
    'ThemeListResponse',
    # Article Score (4 Signals)
    'ArticleScore',
    'ArticleScoreCreate',
    'ArticleScoreUpdate',
    'ArticleScoreBase',
    'ArticleScoreResponse',
    'ArticleScoreListResponse',
    # Article Embedding (Vectors)
    'ArticleEmbedding',
    'ArticleEmbeddingCreate',
    'ArticleEmbeddingUpdate',
    'ArticleEmbeddingBase',
    'ArticleEmbeddingResponse',
    'ArticleEmbeddingListResponse',
    'BulkEmbeddingCreate',
    'SemanticSearchRequest',
    'SemanticSearchResult',
    'SemanticSearchResponse',
    # Event Signature (Event-Based Clustering)
    'EventSignature',
    'EventSignatureCreate',
    'EventSignatureUpdate',
    'EventSignatureBase',
    'EventSignatureResponse',
    'normalize_entity',
    'entities_match',
    'calculate_entity_similarity',
]
