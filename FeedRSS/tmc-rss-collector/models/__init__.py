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
]
