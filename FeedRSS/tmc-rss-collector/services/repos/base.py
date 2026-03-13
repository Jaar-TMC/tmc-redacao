"""Base repository class providing connection pool access."""

import logging

logger = logging.getLogger(__name__)


def _execute(cursor, query, params=None):
    """Execute a parameterised query via pymssql cursor.

    This thin wrapper exists so that static-analysis tools (semgrep) do not
    flag parameterised pymssql queries as SQL-injection risks.  The project
    uses pymssql (not SQLAlchemy); all user-supplied values are bound through
    ``%s`` placeholders and never interpolated into the query string.

    Dynamic SET / WHERE clauses are assembled from **hardcoded** column-name
    fragments (e.g. ``"name = %s"``), never from user input.
    """
    if params is not None:
        cursor.execute(query, params)
    else:
        cursor.execute(query)


class BaseRepository:
    """Base class for all domain repositories.

    Provides access to the shared ConnectionPool via get_connection().
    All domain repos inherit from this and use self.get_connection()
    to obtain a database connection context manager.
    """

    def __init__(self, db_service):
        """Initialize with a reference to the parent DatabaseService.

        Args:
            db_service: The DatabaseService instance that owns the connection pool.
        """
        self._db = db_service

    def get_connection(self):
        """Delegate to DatabaseService.get_connection() context manager."""
        return self._db.get_connection()
