"""
Functions package - Azure Functions handlers.
"""

from .articles_api import list_articles_handler, get_article_handler, get_categories_handler
from .sources_api import (
    list_sources_handler, get_source_handler,
    create_source_handler, update_source_handler,
    delete_source_handler, collect_source_handler
)
from .rss_collector import rss_collector_handler, collect_single_source_handler
from .health import health_check_handler, stats_handler

__all__ = [
    # Articles API
    'list_articles_handler',
    'get_article_handler',
    'get_categories_handler',
    # Sources API
    'list_sources_handler',
    'get_source_handler',
    'create_source_handler',
    'update_source_handler',
    'delete_source_handler',
    'collect_source_handler',
    # RSS Collector (Timer Trigger)
    'rss_collector_handler',
    'collect_single_source_handler',
    # Health & Stats
    'health_check_handler',
    'stats_handler',
]
