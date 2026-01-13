"""
Servico de acesso ao banco de dados Azure SQL Server.
Gerencia conexoes e operacoes CRUD para sources, articles e logs.
"""

import os
import pyodbc
import logging
from typing import List, Optional, Set, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import json

from models import (
    Source, SourceCreate, SourceUpdate,
    Article, ArticleCreate,
    CollectionLog, CollectionLogCreate
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Servico de acesso ao banco de dados."""

    def __init__(self):
        """Inicializa o servico com configuracoes do ambiente."""
        self.server = os.environ.get('SQL_SERVER', 'bi4ia-tmc.database.windows.net')
        self.database = os.environ.get('SQL_DATABASE', 'tmc')
        self.username = os.environ.get('SQL_USERNAME', 'tmc_collector')
        self.password = os.environ.get('SQL_PASSWORD', '')

        self._connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server={self.server};"
            f"Database={self.database};"
            f"Uid={self.username};"
            f"Pwd={self.password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )

    def get_connection(self) -> pyodbc.Connection:
        """Obtem uma conexao com o banco de dados."""
        return pyodbc.connect(self._connection_string)

    def test_connection(self) -> bool:
        """Testa a conexao com o banco de dados."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    # ========================================
    # SOURCES
    # ========================================

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
        """
        Retorna fontes que devem ser coletadas agora.
        Filtra por active=1 e verifica frequencia vs last_fetch.
        """
        sources = self.get_active_sources()
        now = datetime.utcnow()
        return [s for s in sources if s.should_fetch(now)]

    def get_source_by_id(self, source_id: UUID) -> Optional[Source]:
        """Retorna uma fonte especifica pelo ID."""
        query = """
            SELECT id, name, url, favicon_url, active, frequency, category,
                   last_fetch, last_error, articles_count, created_at, updated_at
            FROM sources
            WHERE id = ?
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
            VALUES (?, ?, ?, ?, ?, ?)
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
        # Construir query dinamicamente com campos fornecidos
        updates = []
        params = []

        if data.name is not None:
            updates.append("name = ?")
            params.append(data.name)
        if data.url is not None:
            updates.append("url = ?")
            params.append(data.url)
        if data.favicon_url is not None:
            updates.append("favicon_url = ?")
            params.append(data.favicon_url)
        if data.active is not None:
            updates.append("active = ?")
            params.append(data.active)
        if data.frequency is not None:
            updates.append("frequency = ?")
            params.append(data.frequency)
        if data.category is not None:
            updates.append("category = ?")
            params.append(data.category)

        if not updates:
            return self.get_source_by_id(source_id)

        updates.append("updated_at = GETUTCDATE()")
        params.append(str(source_id))

        query = f"""
            UPDATE sources
            SET {', '.join(updates)}
            WHERE id = ?
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

        return self.get_source_by_id(source_id)

    def delete_source(self, source_id: UUID) -> bool:
        """Desativa uma fonte (soft delete)."""
        query = """
            UPDATE sources
            SET active = 0, updated_at = GETUTCDATE()
            WHERE id = ?
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
                    last_error = ?,
                    updated_at = GETUTCDATE()
                WHERE id = ?
            """
            params = (error, str(source_id))
        else:
            query = """
                UPDATE sources
                SET last_fetch = GETUTCDATE(),
                    last_error = NULL,
                    articles_count = articles_count + ?,
                    updated_at = GETUTCDATE()
                WHERE id = ?
            """
            params = (articles_count_delta, str(source_id))

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

    # ========================================
    # ARTICLES
    # ========================================

    def get_articles(self, page: int = 1, limit: int = 20,
                     category: Optional[str] = None,
                     source_id: Optional[str] = None,
                     period: Optional[str] = None,
                     search: Optional[str] = None) -> Tuple[List[Article], int]:
        """
        Lista artigos com filtros e paginacao.

        Args:
            page: Pagina atual (1-based)
            limit: Itens por pagina (max 100)
            category: Filtrar por categoria
            source_id: Filtrar por fonte
            period: 'today', 'week', 'month'
            search: Busca em titulo/conteudo

        Returns:
            Tuple (lista de artigos, total de registros)
        """
        limit = min(limit, 100)
        offset = (page - 1) * limit

        # Construir WHERE clause
        conditions = []
        params = []

        if category:
            conditions.append("a.category = ?")
            params.append(category)

        if source_id:
            conditions.append("a.source_id = ?")
            params.append(source_id)

        if period:
            if period == 'today':
                conditions.append("a.published_at >= DATEADD(day, -1, GETUTCDATE())")
            elif period == 'week':
                conditions.append("a.published_at >= DATEADD(week, -1, GETUTCDATE())")
            elif period == 'month':
                conditions.append("a.published_at >= DATEADD(month, -1, GETUTCDATE())")

        if search:
            conditions.append("(a.title LIKE ? OR a.content LIKE ?)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Query para dados
        query = f"""
            SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,
                   a.image_url, a.author, a.category, a.tags, a.published_at,
                   a.collected_at, a.hash,
                   s.name as source_name, s.url as source_url, s.favicon_url
            FROM collected_articles a
            JOIN sources s ON a.source_id = s.id
            {where_clause}
            ORDER BY a.published_at DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """

        # Query para total
        count_query = f"""
            SELECT COUNT(*) FROM collected_articles a {where_clause}
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Executar count
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Executar query principal
            cursor.execute(query, params + [offset, limit])
            rows = cursor.fetchall()

            articles = [self._row_to_article(row) for row in rows]

        return articles, total

    def get_article_by_id(self, article_id: UUID) -> Optional[Article]:
        """Retorna um artigo especifico pelo ID."""
        query = """
            SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,
                   a.image_url, a.author, a.category, a.tags, a.published_at,
                   a.collected_at, a.hash,
                   s.name as source_name, s.url as source_url, s.favicon_url
            FROM collected_articles a
            JOIN sources s ON a.source_id = s.id
            WHERE a.id = ?
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(article_id),))
            row = cursor.fetchone()
            return self._row_to_article(row) if row else None

    def check_existing_hashes(self, hashes: List[str]) -> Set[str]:
        """
        Verifica quais hashes ja existem no banco.

        Args:
            hashes: Lista de hashes MD5 para verificar

        Returns:
            Set de hashes que ja existem
        """
        if not hashes:
            return set()

        # Criar placeholders para IN clause
        placeholders = ','.join(['?' for _ in hashes])
        query = f"""
            SELECT hash FROM collected_articles
            WHERE hash IN ({placeholders})
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, hashes)
            rows = cursor.fetchall()
            return {row[0] for row in rows}

    def insert_articles(self, articles: List[ArticleCreate]) -> int:
        """
        Insere multiplos artigos (batch insert).

        Args:
            articles: Lista de artigos para inserir

        Returns:
            Numero de artigos inseridos com sucesso
        """
        if not articles:
            return 0

        query = """
            INSERT INTO collected_articles
            (source_id, title, content, preview, url, image_url, author,
             category, tags, published_at, collected_at, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        inserted = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()

            for article in articles:
                try:
                    tags_json = json.dumps(article.tags) if article.tags else '[]'
                    cursor.execute(query, (
                        str(article.source_id),
                        article.title,
                        article.content,
                        article.preview,
                        article.url,
                        article.image_url,
                        article.author,
                        article.category,
                        tags_json,
                        article.published_at,
                        article.collected_at,
                        article.hash
                    ))
                    inserted += 1
                except pyodbc.IntegrityError as e:
                    # Duplicata (hash ou url ja existe)
                    logger.debug(f"Skipping duplicate article: {article.url}")
                    continue
                except Exception as e:
                    logger.error(f"Error inserting article {article.url}: {e}")
                    continue

            conn.commit()

        return inserted

    # ========================================
    # COLLECTION LOGS
    # ========================================

    def log_collection(self, source_id: Optional[UUID],
                       status: str,
                       articles_found: int,
                       articles_new: int,
                       articles_duplicate: int,
                       duration_ms: int,
                       error: Optional[str] = None) -> None:
        """Registra um log de coleta."""
        query = """
            INSERT INTO collection_logs
            (source_id, started_at, finished_at, status, articles_found,
             articles_new, articles_duplicate, error_message, duration_ms)
            VALUES (?, DATEADD(ms, -?, GETUTCDATE()), GETUTCDATE(), ?, ?, ?, ?, ?, ?)
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                str(source_id) if source_id else None,
                duration_ms,
                status,
                articles_found,
                articles_new,
                articles_duplicate,
                error,
                duration_ms
            ))
            conn.commit()

    def get_collection_stats(self) -> dict:
        """Retorna estatisticas de coleta."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total de artigos
            cursor.execute("SELECT COUNT(*) FROM collected_articles")
            total_articles = cursor.fetchone()[0]

            # Artigos hoje
            cursor.execute("""
                SELECT COUNT(*) FROM collected_articles
                WHERE collected_at >= DATEADD(day, -1, GETUTCDATE())
            """)
            articles_today = cursor.fetchone()[0]

            # Fontes ativas
            cursor.execute("SELECT COUNT(*) FROM sources WHERE active = 1")
            active_sources = cursor.fetchone()[0]

            # Ultima coleta
            cursor.execute("""
                SELECT MAX(finished_at) FROM collection_logs
                WHERE status = 'success'
            """)
            last_collection = cursor.fetchone()[0]

            # Por categoria
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM collected_articles
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
            """)
            by_category = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_articles": total_articles,
            "articles_today": articles_today,
            "active_sources": active_sources,
            "last_collection": last_collection.isoformat() if last_collection else None,
            "by_category": by_category
        }

    # ========================================
    # HELPERS
    # ========================================

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

    def _row_to_article(self, row) -> Article:
        """Converte uma row do cursor para Article."""
        return Article(
            id=row[0],
            source_id=row[1],
            title=row[2],
            content=row[3],
            preview=row[4],
            url=row[5],
            image_url=row[6],
            author=row[7],
            category=row[8],
            tags=row[9],  # Sera parseado pelo validator
            published_at=row[10],
            collected_at=row[11],
            hash=row[12],
            source_name=row[13],
            source_url=row[14],
            favicon=row[15]
        )


# Singleton para uso global
_db_service: Optional[DatabaseService] = None

def get_db() -> DatabaseService:
    """Retorna instancia singleton do DatabaseService."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
