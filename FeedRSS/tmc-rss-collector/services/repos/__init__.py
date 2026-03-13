"""Domain repository classes for database operations.

Each repository encapsulates database operations for a specific domain,
providing a cleaner separation of concerns from the monolithic DatabaseService.
The DatabaseService facade delegates to these repos while maintaining
backward compatibility via the original methods.
"""

from .base import BaseRepository
from .source_repo import SourceRepository
from .embedding_repo import EmbeddingRepository
from .scoring_repo import ScoringRepository
from .auth_repo import AuthRepository
from .user_repo import UserRepository
from .audit_repo import AuditRepository
from .event_repo import EventRepository
from .theme_repo import ThemeRepository
from .article_repo import ArticleRepository

__all__ = [
    'BaseRepository',
    'SourceRepository',
    'EmbeddingRepository',
    'ScoringRepository',
    'AuthRepository',
    'UserRepository',
    'AuditRepository',
    'EventRepository',
    'ThemeRepository',
    'ArticleRepository',
]
