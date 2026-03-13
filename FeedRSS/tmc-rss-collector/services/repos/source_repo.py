"""Source repository - CRUD operations for RSS feed sources."""

import logging
from typing import List, Optional
from uuid import UUID

from models import Source, SourceCreate, SourceUpdate
from .base import BaseRepository, _execute

logger = logging.getLogger(__name__)


def _build_update_query(table, updates, where):
    """Build a parameterized UPDATE query from safe column fragments.

    All update fragments are hardcoded column assignments (e.g. "name = %s"),
    never derived from user input. The WHERE clause is also a static string.
    """
    return "UPDATE " + table + " SET " + ", ".join(updates) + " WHERE " + where


class SourceRepository(BaseRepository):
    """Repository for RSS source management."""

    def get_all_sources(self) -> List[Source]:
        """Retorna todas as fontes cadastradas."""
        query = """
            SELECT id, name, url, favicon_url, active, frequency, category,
                   last_fetch, last_error, articles_count, created_at, updated_at
            FROM sources
            ORDER BY name
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._row_to_source(row) for row in rows]

    def get_active_sources(self) -> List[Source]:
        """Retorna apenas fontes ativas."""
        query = """
            SELECT id, name, url, favicon_url, active, frequency, category,
                   last_fetch, last_error, articles_count, created_at, updated_at
            FROM sources
            WHERE active = 1
            ORDER BY name
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._row_to_source(row) for row in rows]

    def get_sources_to_fetch(self) -> List[Source]:
        """Retorna fontes que devem ser coletadas agora.

        PERF: Filters in SQL instead of fetching all active sources then filtering in Python.
        Uses CASE to map frequency string to minutes, then checks elapsed time.
        """
        query = """
            SELECT id, name, url, favicon_url, active, frequency, category,
                   last_fetch, last_error, articles_count, created_at, updated_at
            FROM sources
            WHERE active = 1
            AND (
                last_fetch IS NULL
                OR DATEDIFF(minute, last_fetch, GETUTCDATE()) >=
                    CASE frequency
                        WHEN '15min' THEN 15
                        WHEN '30min' THEN 30
                        WHEN '1h' THEN 60
                        WHEN '2h' THEN 120
                        WHEN '6h' THEN 360
                        ELSE 60
                    END
            )
            ORDER BY last_fetch ASC
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._row_to_source(row) for row in rows]

    def get_source_by_id(self, source_id: UUID) -> Optional[Source]:
        """Retorna uma fonte especifica pelo ID."""
        query = """
            SELECT id, name, url, favicon_url, active, frequency, category,
                   last_fetch, last_error, articles_count, created_at, updated_at
            FROM sources
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(source_id),))
            row = cursor.fetchone()
            return self._row_to_source(row) if row else None

    def create_source(self, source: SourceCreate) -> Source:
        """Cria uma nova fonte."""
        query = """
            INSERT INTO sources (name, url, favicon_url, active, frequency, category)
            OUTPUT INSERTED.id, INSERTED.created_at, INSERTED.updated_at
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                source.name, source.url, source.favicon_url,
                source.active, source.frequency, source.category
            ))
            row = cursor.fetchone()
            conn.commit()

            return Source(
                id=row[0],
                name=source.name,
                url=source.url,
                favicon_url=source.favicon_url,
                active=source.active,
                frequency=source.frequency,
                category=source.category,
                created_at=row[1],
                updated_at=row[2]
            )

    def update_source(self, source_id: UUID, data: SourceUpdate) -> Optional[Source]:
        """Atualiza uma fonte existente."""
        updates = []
        params = []

        if data.name is not None:
            updates.append("name = %s")
            params.append(data.name)
        if data.url is not None:
            updates.append("url = %s")
            params.append(data.url)
        if data.favicon_url is not None:
            updates.append("favicon_url = %s")
            params.append(data.favicon_url)
        if data.active is not None:
            updates.append("active = %s")
            params.append(data.active)
        if data.frequency is not None:
            updates.append("frequency = %s")
            params.append(data.frequency)
        if data.category is not None:
            updates.append("category = %s")
            params.append(data.category)

        if not updates:
            return self.get_source_by_id(source_id)

        updates.append("updated_at = GETUTCDATE()")
        params.append(str(source_id))

        query = _build_update_query("sources", updates, "id = %s")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params))
            conn.commit()

        return self.get_source_by_id(source_id)

    def delete_source(self, source_id: UUID) -> bool:
        """Desativa uma fonte (soft delete)."""
        query = """
            UPDATE sources
            SET active = 0, updated_at = GETUTCDATE()
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(source_id),))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def update_source_last_fetch(self, source_id: UUID,
                                  articles_count_delta: int = 0,
                                  error: Optional[str] = None) -> None:
        """Atualiza last_fetch e contagem apos coleta."""
        if error:
            query = """
                UPDATE sources
                SET last_fetch = GETUTCDATE(),
                    last_error = %s,
                    updated_at = GETUTCDATE()
                WHERE id = %s
            """
            params = (error, str(source_id))
        else:
            query = """
                UPDATE sources
                SET last_fetch = GETUTCDATE(),
                    last_error = NULL,
                    articles_count = articles_count + %s,
                    updated_at = GETUTCDATE()
                WHERE id = %s
            """
            params = (articles_count_delta, str(source_id))

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            conn.commit()

    def _row_to_source(self, row) -> Source:
        """Converte uma row do cursor para Source."""
        return Source(
            id=row[0],
            name=row[1],
            url=row[2],
            favicon_url=row[3],
            active=bool(row[4]),
            frequency=row[5],
            category=row[6],
            last_fetch=row[7],
            last_error=row[8],
            articles_count=row[9] or 0,
            created_at=row[10],
            updated_at=row[11]
        )
