"""
Servico de acesso ao banco de dados Azure SQL Server.
Gerencia conexoes e operacoes CRUD para sources, articles e logs.
"""

import os
import pymssql
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models import (
    Source, SourceCreate, SourceUpdate,
    Article, ArticleCreate,
    CollectionLog, CollectionLogCreate,
    UserArticle, UserArticleCreate, UserArticleUpdate,
    User, UserCreate, UserUpdate, UserWithPassword
)

# Type alias for embedding vectors
EmbeddingVector = List[float]

logger = logging.getLogger(__name__)


class DatabaseService:
    """Servico de acesso ao banco de dados."""

    def __init__(self):
        """Inicializa o servico com configuracoes do ambiente."""
        self.server = os.environ.get('SQL_SERVER', '')
        self.database = os.environ.get('SQL_DATABASE', '')
        self.username = os.environ.get('SQL_USERNAME', '')
        self.password = os.environ.get('SQL_PASSWORD', '')
        # Phase 4.2: Fail explicitly if required DB config is missing
        if not self.server or not self.database:
            raise ValueError(
                "Database not configured. Set SQL_SERVER and SQL_DATABASE environment variables."
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((pymssql.OperationalError, pymssql.InterfaceError)),
        reraise=True
    )
    def get_connection(self) -> pymssql.Connection:
        """Obtem uma conexao com o banco de dados. Retries on transient errors."""
        query_timeout = int(os.environ.get('SQL_QUERY_TIMEOUT', '30'))
        return pymssql.connect(
            server=self.server,
            user=self.username,
            password=self.password,
            database=self.database,
            login_timeout=30,
            timeout=query_timeout,
            as_dict=False,
            charset='UTF-8'
        )

    def test_connection(self) -> bool:
        """Testa a conexao com o banco de dados."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
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
        # Construir query dinamicamente com campos fornecidos
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

        query = f"""
            UPDATE sources
            SET {', '.join(updates)}
            WHERE id = %s
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
            cursor.execute(query, params)
            conn.commit()

    # ========================================
    # ARTICLES
    # ========================================

    def _build_article_filters(self,
                               category: Optional[str] = None,
                               source_id: Optional[str] = None,
                               period: Optional[str] = None,
                               search: Optional[str] = None,
                               tag: Optional[str] = None,
                               classification: Optional[str] = None) -> Tuple[str, list, bool]:
        """
        Build shared WHERE clause and params for article queries.
        Reused by get_articles and get_urgency_counts to avoid duplication.

        Returns:
            Tuple (where_clause, params, needs_scores_join) - needs_scores_join
            indicates whether the query needs LEFT JOIN article_scores.
        """
        conditions = []
        params = []
        needs_scores_join = False

        if classification and classification in ('A', 'B', 'C'):
            conditions.append("sc.classification = %s")
            params.append(classification)
            needs_scores_join = True

        if category:
            conditions.append("a.category = %s")
            params.append(category)

        if source_id:
            conditions.append("s.name = %s")
            params.append(source_id)

        if period:
            if period == 'today':
                conditions.append("a.published_at >= DATEADD(day, -1, GETUTCDATE())")
            elif period == 'week':
                conditions.append("a.published_at >= DATEADD(week, -1, GETUTCDATE())")
            elif period == 'month':
                conditions.append("a.published_at >= DATEADD(month, -1, GETUTCDATE())")
            else:
                try:
                    hours = int(period)
                    if 1 <= hours <= 24:
                        conditions.append("a.published_at >= DATEADD(hour, -%s, GETUTCDATE())")
                        params.append(hours)
                except ValueError:
                    pass

        if search:
            search_with_spaces = search.replace('-', ' ')
            search_param = f"%{search}%"

            if search_with_spaces != search:
                search_param_spaces = f"%{search_with_spaces}%"
                conditions.append("""(
                    a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.content COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.content COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                )""")
                params.extend([search_param, search_param_spaces, search_param, search_param_spaces, search_param])
            else:
                conditions.append("""(
                    a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.content COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                )""")
                params.extend([search_param, search_param, search_param])

        if tag:
            conditions.append("""
                a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
            """)
            tag_param = f'%"{tag}"%'
            params.append(tag_param)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, params, needs_scores_join

    def get_articles(self, page: int = 1, limit: int = 20,
                     category: Optional[str] = None,
                     source_id: Optional[str] = None,
                     period: Optional[str] = None,
                     search: Optional[str] = None,
                     tag: Optional[str] = None,
                     classification: Optional[str] = None) -> Tuple[List[Article], int]:
        """
        Lista artigos com filtros e paginacao.
        Also returns urgency_counts in the same DB round-trip.

        Returns:
            Tuple (lista de artigos, total de registros)
        """
        limit = min(limit, 100)
        offset = (page - 1) * limit

        where_clause, params, needs_scores_join = self._build_article_filters(
            category=category, source_id=source_id, period=period,
            search=search, tag=tag, classification=classification
        )

        scores_join = "LEFT JOIN article_scores sc ON sc.article_id = a.id" if needs_scores_join else ""

        # Combined query: data + count in single round-trip
        query = f"""
            SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,
                   a.image_url, a.author, a.category, a.tags, a.published_at,
                   a.collected_at, a.hash,
                   s.name as source_name, s.url as source_url, s.favicon_url
            FROM collected_articles a
            JOIN sources s ON a.source_id = s.id
            {scores_join}
            {where_clause}
            ORDER BY a.published_at DESC
            OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
        """

        count_query = f"""
            SELECT COUNT(*) FROM collected_articles a
            JOIN sources s ON a.source_id = s.id
            {scores_join}
            {where_clause}
        """

        logger.info(f"[get_articles] search={search}, where_clause={where_clause}")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            cursor.execute(query, params + [offset, limit])
            rows = cursor.fetchall()

            logger.info(f"[get_articles] total={total}, rows={len(rows)}")

            articles = [self._row_to_article(row) for row in rows]

        return articles, total

    def get_articles_with_urgency(self, page: int = 1, limit: int = 20,
                                   category: Optional[str] = None,
                                   source_id: Optional[str] = None,
                                   period: Optional[str] = None,
                                   search: Optional[str] = None,
                                   tag: Optional[str] = None,
                                   classification: Optional[str] = None,
                                   order_by: Optional[str] = None) -> Tuple[List[Article], int, dict]:
        """
        Combined query: articles + count + urgency counts in a single DB connection.
        Avoids executing the expensive WHERE clause (especially LIKE on content) twice.

        Returns:
            Tuple (articles, total_count, urgency_counts_dict)
        """
        limit = min(limit, 100)
        offset = (page - 1) * limit

        where_clause, params, needs_scores_join = self._build_article_filters(
            category=category, source_id=source_id, period=period,
            search=search, tag=tag, classification=classification
        )

        # Build urgency WHERE: same content filters but restricted to last 24h
        urgency_where, urgency_params, urgency_needs_scores_join = self._build_article_filters(
            category=category, source_id=source_id, period=None,
            search=search, tag=tag, classification=classification
        )
        # Add 24h constraint for urgency
        if urgency_where:
            urgency_where += " AND a.published_at >= DATEADD(day, -1, GETUTCDATE())"
        else:
            urgency_where = "WHERE a.published_at >= DATEADD(day, -1, GETUTCDATE())"

        logger.info(f"[get_articles_with_urgency] search={search}, order_by={order_by}")

        scores_join = "LEFT JOIN article_scores sc ON sc.article_id = a.id" if needs_scores_join else ""
        urgency_scores_join = "LEFT JOIN article_scores sc ON sc.article_id = a.id" if urgency_needs_scores_join else ""

        # Dynamic ORDER BY - score sorts by total_score DESC with nulls last, then by date
        if order_by == 'score':
            order_clause = "ORDER BY COALESCE(sc.total_score, 0) DESC, a.published_at DESC"
        else:
            order_clause = "ORDER BY a.published_at DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Count total (reuses same connection)
            count_query = f"""
                SELECT COUNT(*) FROM collected_articles a
                JOIN sources s ON a.source_id = s.id
                {scores_join}
                {where_clause}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # 2. Get page of articles (always joins article_scores for score columns)
            query = f"""
                SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,
                       a.image_url, a.author, a.category, a.tags, a.published_at,
                       a.collected_at, a.hash,
                       s.name as source_name, s.url as source_url, s.favicon_url,
                       sc.total_score, sc.classification,
                       sc.score_inesperado, sc.score_impacto, sc.score_busca_agora, sc.score_conversa
                FROM collected_articles a
                JOIN sources s ON a.source_id = s.id
                LEFT JOIN article_scores sc ON sc.article_id = a.id
                {where_clause}
                {order_clause}
                OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
            """
            cursor.execute(query, params + [offset, limit])
            rows = cursor.fetchall()
            articles = [self._row_to_article(row) for row in rows]

            # 3. Urgency counts (single scan with CASE)
            urgency_query = f"""
                SELECT
                    SUM(CASE WHEN a.published_at >= DATEADD(hour, -1, GETUTCDATE()) THEN 1 ELSE 0 END),
                    SUM(CASE WHEN a.published_at >= DATEADD(hour, -3, GETUTCDATE()) THEN 1 ELSE 0 END),
                    SUM(CASE WHEN a.published_at >= DATEADD(hour, -8, GETUTCDATE()) THEN 1 ELSE 0 END),
                    COUNT(*)
                FROM collected_articles a
                JOIN sources s ON a.source_id = s.id
                {urgency_scores_join}
                {urgency_where}
            """
            cursor.execute(urgency_query, urgency_params)
            urow = cursor.fetchone()

            urgency_counts = {
                "now": urow[0] or 0,
                "recent": urow[1] or 0,
                "today": urow[2] or 0,
                "all": urow[3] or 0
            } if urow else {"now": 0, "recent": 0, "today": 0, "all": 0}

            logger.info(f"[get_articles_with_urgency] total={total}, rows={len(rows)}, urgency={urgency_counts}")

        return articles, total, urgency_counts

    def get_urgency_counts(self,
                           category: Optional[str] = None,
                           source_id: Optional[str] = None,
                           search: Optional[str] = None,
                           tag: Optional[str] = None) -> dict:
        """
        Returns article counts per urgency cluster using a single SQL query.
        Kept for backward compatibility. Prefer get_articles_with_urgency() for combined calls.
        """
        urgency_where, urgency_params, urgency_needs_scores = self._build_article_filters(
            category=category, source_id=source_id, period=None,
            search=search, tag=tag
        )
        if urgency_where:
            urgency_where += " AND a.published_at >= DATEADD(day, -1, GETUTCDATE())"
        else:
            urgency_where = "WHERE a.published_at >= DATEADD(day, -1, GETUTCDATE())"

        scores_join = "LEFT JOIN article_scores sc ON sc.article_id = a.id" if urgency_needs_scores else ""

        query = f"""
            SELECT
                SUM(CASE WHEN a.published_at >= DATEADD(hour, -1, GETUTCDATE()) THEN 1 ELSE 0 END) as now_count,
                SUM(CASE WHEN a.published_at >= DATEADD(hour, -3, GETUTCDATE()) THEN 1 ELSE 0 END) as recent_count,
                SUM(CASE WHEN a.published_at >= DATEADD(hour, -8, GETUTCDATE()) THEN 1 ELSE 0 END) as today_count,
                COUNT(*) as all_count
            FROM collected_articles a
            JOIN sources s ON a.source_id = s.id
            {scores_join}
            {urgency_where}
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, urgency_params)
            row = cursor.fetchone()

            if row:
                return {
                    "now": row[0] or 0,
                    "recent": row[1] or 0,
                    "today": row[2] or 0,
                    "all": row[3] or 0
                }
            return {"now": 0, "recent": 0, "today": 0, "all": 0}

    def get_article_by_id(self, article_id: UUID) -> Optional[Article]:
        """Retorna um artigo especifico pelo ID."""
        query = """
            SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,
                   a.image_url, a.author, a.category, a.tags, a.published_at,
                   a.collected_at, a.hash,
                   s.name as source_name, s.url as source_url, s.favicon_url,
                   sc.total_score, sc.classification,
                   sc.score_inesperado, sc.score_impacto, sc.score_busca_agora, sc.score_conversa
            FROM collected_articles a
            JOIN sources s ON a.source_id = s.id
            LEFT JOIN article_scores sc ON sc.article_id = a.id
            WHERE a.id = %s
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
        placeholders = ','.join(['%s' for _ in hashes])
        query = f"""
            SELECT hash FROM collected_articles
            WHERE hash IN ({placeholders})
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, hashes)
            rows = cursor.fetchall()
            return {row[0] for row in rows}

    def get_recent_titles(self, hours: int = 24) -> List[str]:
        """
        Retorna titulos de artigos recentes para deduplicacao por similaridade.

        Args:
            hours: Numero de horas para buscar artigos recentes (default: 24)

        Returns:
            Lista de titulos normalizados (lowercase, sem espacos extras)
        """
        query = """
            SELECT LOWER(LTRIM(RTRIM(title)))
            FROM collected_articles
            WHERE collected_at >= DATEADD(hour, -%s, GETUTCDATE())
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (hours,))
            rows = cursor.fetchall()
            return [row[0] for row in rows if row[0]]

    def insert_articles(self, articles: List[ArticleCreate]) -> int:
        """
        Insere multiplos artigos (batch insert).

        Args:
            articles: Lista de artigos para inserir

        Returns:
            Numero de artigos inseridos com sucesso
        """
        result = self.insert_articles_returning(articles)
        return result[0]

    def insert_articles_returning(self, articles: List[ArticleCreate]) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Insere multiplos artigos e retorna dados dos artigos inseridos.

        Args:
            articles: Lista de artigos para inserir

        Returns:
            Tuple (count, inserted_articles) onde inserted_articles contem
            dicts com id, title, content para uso no scoring inline.
        """
        if not articles:
            return 0, []

        query = """
            INSERT INTO collected_articles
            (source_id, title, content, preview, url, image_url, author,
             category, tags, published_at, collected_at, hash)
            OUTPUT INSERTED.id, INSERTED.title, INSERTED.content, INSERTED.category
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        inserted = 0
        inserted_articles = []
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
                    row = cursor.fetchone()
                    if row:
                        inserted_articles.append({
                            'id': row[0],
                            'title': row[1],
                            'content': row[2] or '',
                            'category': row[3] or ''
                        })
                    inserted += 1
                except pymssql.IntegrityError as e:
                    # Duplicata (hash ou url ja existe)
                    logger.debug(f"Skipping duplicate article: {article.url}")
                    continue
                except Exception as e:
                    logger.error(f"Error inserting article {article.url}: {e}")
                    continue

            conn.commit()

        return inserted, inserted_articles

    def delete_old_articles(self, hours: int = 24) -> int:
        """
        Delete articles older than specified hours.

        Args:
            hours: Number of hours after which articles are considered old (default: 24)

        Returns:
            Number of articles deleted
        """
        query = """
            DELETE FROM collected_articles
            WHERE collected_at < DATEADD(hour, -%s, GETUTCDATE())
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (hours,))
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            logger.info(f"Deleted {deleted} articles older than {hours} hours")

        return deleted

    def delete_duplicate_articles_by_title(self, similarity_threshold: float = 0.85) -> int:
        """
        Delete duplicate articles keeping only the oldest one per similar title group.

        Uses SQL to keep only one article per similar title (based on first 100 chars).
        This is a simplified approach - keeps the article with earliest collected_at.

        Returns:
            Number of articles deleted
        """
        # Delete articles with exact same title (keep oldest)
        query = """
            WITH Duplicates AS (
                SELECT id,
                       title,
                       ROW_NUMBER() OVER (
                           PARTITION BY LOWER(LTRIM(RTRIM(title)))
                           ORDER BY collected_at ASC
                       ) as rn
                FROM collected_articles
            )
            DELETE FROM collected_articles
            WHERE id IN (
                SELECT id FROM Duplicates WHERE rn > 1
            )
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            logger.info(f"Deleted {deleted} duplicate articles with same title")

        return deleted

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
            VALUES (%s, DATEADD(ms, -%s, GETUTCDATE()), GETUTCDATE(), %s, %s, %s, %s, %s, %s)
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

    def get_trending_tags(self, limit: int = 20, period_hours: Optional[int] = None) -> List[dict]:
        """
        Get trending tags with distinct article counts from ALL articles.

        Uses SQL to aggregate tags across all articles in the database,
        counting distinct articles per tag.

        Args:
            limit: Maximum number of tags to return (default: 20)
            period_hours: Optional filter for articles within last N hours

        Returns:
            List of dicts: [{"tag": "tagname", "count": N}, ...]
        """
        # Build period filter if specified
        period_filter = ""
        params = []
        if period_hours:
            period_filter = "WHERE collected_at >= DATEADD(hour, -%s, GETUTCDATE())"
            params.append(period_hours)

        # SQL Server approach: Parse JSON tags and count distinct articles
        # Note: tags are stored as JSON array like '["tag1", "tag2"]'
        # Filter out: source names, domains (.com, .br), and generic tags
        query = f"""
            WITH ArticleTags AS (
                SELECT
                    a.id as article_id,
                    LOWER(LTRIM(RTRIM(t.value))) as tag
                FROM collected_articles a
                CROSS APPLY OPENJSON(a.tags) t
                {period_filter}
            ),
            TagCounts AS (
                SELECT
                    tag,
                    COUNT(DISTINCT article_id) as article_count
                FROM ArticleTags
                WHERE tag IS NOT NULL
                    AND LEN(tag) > 2
                    -- Exclude source names (media outlets)
                    AND tag NOT IN ('g1', 'globo', 'folha', 'uol', 'estadao', 'cnn', 'bbc',
                                    'r7', 'terra', 'ig', 'globoesporte', 'tecmundo', 'infomoney',
                                    'noticias', 'noticia', 'news')
                    -- Exclude domain-like tags (.com, .br, .net, etc)
                    AND tag NOT LIKE '%%.com'
                    AND tag NOT LIKE '%%.com.br'
                    AND tag NOT LIKE '%%.br'
                    AND tag NOT LIKE '%%.net'
                    AND tag NOT LIKE '%%.org'
                GROUP BY tag
            )
            SELECT TOP %s tag, article_count
            FROM TagCounts
            ORDER BY article_count DESC
        """
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [{"tag": row[0], "count": row[1]} for row in rows]

    def get_all_tags(self, search: Optional[str] = None, limit: int = 100) -> List[dict]:
        """
        Get unique tags with article counts, ordered by popularity.

        Args:
            search: Optional search term to filter tags
            limit: Maximum number of tags to return (default: 100)

        Returns:
            List of dicts: [{"tag": "tagname", "theme": "Tag Name", "count": N}, ...]
        """
        search_filter = ""
        params = []
        if search:
            search_filter = "AND tag LIKE %s"
            params.append(f"%{search}%")

        query = f"""
            WITH ArticleTags AS (
                SELECT
                    a.id as article_id,
                    LOWER(LTRIM(RTRIM(t.value))) as tag
                FROM collected_articles a
                CROSS APPLY OPENJSON(a.tags) t
            ),
            TagCounts AS (
                SELECT
                    tag,
                    COUNT(DISTINCT article_id) as article_count
                FROM ArticleTags
                WHERE tag IS NOT NULL
                    AND LEN(tag) > 2
                    AND tag NOT IN ('g1', 'globo', 'folha', 'uol', 'estadao', 'cnn', 'bbc',
                                    'r7', 'terra', 'ig', 'globoesporte', 'tecmundo', 'infomoney',
                                    'noticias', 'noticia', 'news')
                    AND tag NOT LIKE '%%.com'
                    AND tag NOT LIKE '%%.com.br'
                    AND tag NOT LIKE '%%.br'
                    AND tag NOT LIKE '%%.net'
                    AND tag NOT LIKE '%%.org'
                    {search_filter}
                GROUP BY tag
            )
            SELECT TOP %s tag, article_count
            FROM TagCounts
            ORDER BY article_count DESC, tag ASC
        """
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = []
            for row in rows:
                tag = row[0]
                theme = ' '.join(word.capitalize() for word in tag.replace('-', ' ').split())
                result.append({
                    "tag": tag,
                    "theme": theme,
                    "count": row[1]
                })
            return result

    def get_categories_filtered(self,
                               search: Optional[str] = None,
                               tag: Optional[str] = None,
                               source_id: Optional[str] = None,
                               period: Optional[str] = None) -> List[dict]:
        """
        Get categories with article counts, filtered by active filters.
        Returns counts that reflect what the user would see with those filters.
        """
        where_clause, params, _ = self._build_article_filters(
            search=search, tag=tag, source_id=source_id, period=period
        )

        query = f"""
            SELECT a.category, COUNT(*) as count
            FROM collected_articles a
            JOIN sources s ON a.source_id = s.id
            {where_clause}
            {'AND' if where_clause else 'WHERE'} a.category IS NOT NULL
            GROUP BY a.category
            ORDER BY count DESC
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [{"name": row[0], "count": row[1]} for row in cursor.fetchall()]

    def get_all_tags_filtered(self,
                              search: Optional[str] = None,
                              category: Optional[str] = None,
                              source_id: Optional[str] = None,
                              period: Optional[str] = None,
                              limit: int = 100) -> List[dict]:
        """
        Get tags with article counts, filtered by active filters.
        Returns counts that reflect what the user would see with those filters.
        """
        conditions = []
        params = []

        # Build base filter conditions (reusing logic from _build_article_filters)
        if category:
            conditions.append("a.category = %s")
            params.append(category)
        if source_id:
            conditions.append("s.name = %s")
            params.append(source_id)
        if search:
            search_param = f"%{search}%"
            conditions.append("""(
                a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                OR a.content COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
            )""")
            params.extend([search_param, search_param])
        if period:
            try:
                hours = int(period)
                if 1 <= hours <= 24:
                    conditions.append("a.published_at >= DATEADD(hour, -%s, GETUTCDATE())")
                    params.append(hours)
            except ValueError:
                pass

        where_extra = ("AND " + " AND ".join(conditions)) if conditions else ""

        query = f"""
            WITH ArticleTags AS (
                SELECT
                    a.id as article_id,
                    LOWER(LTRIM(RTRIM(t.value))) as tag
                FROM collected_articles a
                JOIN sources s ON a.source_id = s.id
                CROSS APPLY OPENJSON(a.tags) t
                WHERE 1=1 {where_extra}
            ),
            TagCounts AS (
                SELECT
                    tag,
                    COUNT(DISTINCT article_id) as article_count
                FROM ArticleTags
                WHERE tag IS NOT NULL
                    AND LEN(tag) > 2
                    AND tag NOT IN ('g1', 'globo', 'folha', 'uol', 'estadao', 'cnn', 'bbc',
                                    'r7', 'terra', 'ig', 'globoesporte', 'tecmundo', 'infomoney',
                                    'noticias', 'noticia', 'news')
                    AND tag NOT LIKE '%%.com'
                    AND tag NOT LIKE '%%.com.br'
                    AND tag NOT LIKE '%%.br'
                    AND tag NOT LIKE '%%.net'
                    AND tag NOT LIKE '%%.org'
                GROUP BY tag
            )
            SELECT TOP %s tag, article_count
            FROM TagCounts
            ORDER BY article_count DESC, tag ASC
        """
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            result = []
            for row in rows:
                tag_val = row[0]
                theme = ' '.join(word.capitalize() for word in tag_val.replace('-', ' ').split())
                result.append({
                    "tag": tag_val,
                    "theme": theme,
                    "count": row[1]
                })
            return result

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
            favicon=row[15],
            score=row[16] if len(row) > 16 else None,
            score_classification=row[17] if len(row) > 17 else None,
            score_inesperado=row[18] if len(row) > 18 else None,
            score_impacto=row[19] if len(row) > 19 else None,
            score_busca_agora=row[20] if len(row) > 20 else None,
            score_conversa=row[21] if len(row) > 21 else None
        )

    # ========================================
    # USER ARTICLES
    # ========================================

    def get_user_articles(
        self,
        user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        date_range: Optional[str] = None
    ) -> Tuple[List[UserArticle], int]:
        """
        Lista artigos do usuario com filtros e paginacao.

        Args:
            user_id: Filter by owner (required for non-admin users)
            page: Pagina atual (1-based)
            limit: Itens por pagina (max 100)
            status: 'draft' ou 'published'
            category: Filtrar por categoria
            search: Busca em titulo/conteudo
            date_range: '24h', '7d', '30d', '3m', 'year'

        Returns:
            Tuple (lista de artigos, total de registros)
        """
        limit = min(limit, 100)
        offset = (page - 1) * limit

        # Construir WHERE clause
        conditions = ["deleted_at IS NULL"]  # Excluir soft-deleted
        params = []

        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)

        if status:
            conditions.append("status = %s")
            params.append(status)

        if category:
            conditions.append("category = %s")
            params.append(category)

        if search:
            conditions.append("(title LIKE %s OR content LIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        if date_range:
            if date_range == '24h':
                conditions.append("created_at >= DATEADD(hour, -24, GETUTCDATE())")
            elif date_range == '7d':
                conditions.append("created_at >= DATEADD(day, -7, GETUTCDATE())")
            elif date_range == '30d':
                conditions.append("created_at >= DATEADD(day, -30, GETUTCDATE())")
            elif date_range == '3m':
                conditions.append("created_at >= DATEADD(day, -90, GETUTCDATE())")
            elif date_range == 'year':
                conditions.append("YEAR(created_at) = YEAR(GETUTCDATE())")

        where_clause = "WHERE " + " AND ".join(conditions)

        # Query para dados
        query = f"""
            SELECT id, title, linha_fina, content, preview, status, category,
                   tags, source_article_ids, generation_config, author_name,
                   created_at, updated_at, published_at, deleted_at,
                   titulo_curto, resumo
            FROM user_articles
            {where_clause}
            ORDER BY updated_at DESC
            OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
        """

        # Query para total
        count_query = f"""
            SELECT COUNT(*) FROM user_articles {where_clause}
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Executar count
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Executar query principal
            cursor.execute(query, params + [offset, limit])
            rows = cursor.fetchall()

            articles = [self._row_to_user_article(row) for row in rows]

        return articles, total

    def get_user_article_by_id(self, article_id: UUID, user_id: Optional[str] = None) -> Optional[UserArticle]:
        """Retorna um artigo de usuario especifico pelo ID, optionally scoped by user_id."""
        conditions = ["id = %s", "deleted_at IS NULL"]
        params = [str(article_id)]

        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)

        query = f"""
            SELECT id, title, linha_fina, content, preview, status, category,
                   tags, source_article_ids, generation_config, author_name,
                   created_at, updated_at, published_at, deleted_at,
                   titulo_curto, resumo
            FROM user_articles
            WHERE {' AND '.join(conditions)}
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return self._row_to_user_article(row) if row else None

    def create_user_article(self, article: UserArticleCreate, user_id: Optional[str] = None) -> UserArticle:
        """
        Cria um novo artigo de usuario.

        Args:
            article: Dados do artigo a criar
            user_id: ID do usuario autenticado (owner)

        Returns:
            UserArticle criado com ID
        """
        # Gerar preview se nao fornecido
        preview = article.preview
        if not preview and article.content:
            import re
            text = re.sub(r'<[^>]+>', '', article.content)
            text = ' '.join(text.split())
            preview = text[:497] + '...' if len(text) > 500 else text

        query = """
            INSERT INTO user_articles
            (title, linha_fina, titulo_curto, resumo, content, preview, status, category,
             tags, source_article_ids, generation_config, author_name, user_id)
            OUTPUT INSERTED.id, INSERTED.created_at, INSERTED.updated_at
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        tags_json = json.dumps(article.tags) if article.tags else '[]'
        resumo_json = json.dumps(article.resumo) if article.resumo else '[]'
        source_ids_json = json.dumps(article.source_article_ids) if article.source_article_ids else '[]'
        config_json = json.dumps(article.generation_config) if article.generation_config else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                article.title,
                article.linha_fina,
                article.titulo_curto,
                resumo_json,
                article.content,
                preview,
                article.status,
                article.category,
                tags_json,
                source_ids_json,
                config_json,
                article.author_name,
                user_id
            ))
            row = cursor.fetchone()
            conn.commit()

            return UserArticle(
                id=row[0],
                title=article.title,
                linha_fina=article.linha_fina,
                titulo_curto=article.titulo_curto,
                resumo=article.resumo,
                content=article.content,
                preview=preview,
                status=article.status,
                category=article.category,
                tags=article.tags,
                source_article_ids=article.source_article_ids,
                generation_config=article.generation_config,
                author_name=article.author_name,
                created_at=row[1],
                updated_at=row[2]
            )

    def update_user_article(
        self, article_id: UUID, data: UserArticleUpdate, user_id: Optional[str] = None
    ) -> Optional[UserArticle]:
        """
        Atualiza um artigo de usuario existente.

        Args:
            article_id: ID do artigo
            data: Campos para atualizar (parcial)

        Returns:
            UserArticle atualizado ou None se nao encontrado
        """
        # Construir query dinamicamente com campos fornecidos
        updates = []
        params = []

        if data.title is not None:
            updates.append("title = %s")
            params.append(data.title)
        if data.linha_fina is not None:
            updates.append("linha_fina = %s")
            params.append(data.linha_fina)
        if data.titulo_curto is not None:
            updates.append("titulo_curto = %s")
            params.append(data.titulo_curto)
        if data.resumo is not None:
            updates.append("resumo = %s")
            params.append(json.dumps(data.resumo))
        if data.content is not None:
            updates.append("content = %s")
            params.append(data.content)
            # Atualizar preview automaticamente
            import re
            text = re.sub(r'<[^>]+>', '', data.content)
            text = ' '.join(text.split())
            preview = text[:497] + '...' if len(text) > 500 else text
            updates.append("preview = %s")
            params.append(preview)
        if data.preview is not None:
            updates.append("preview = %s")
            params.append(data.preview)
        if data.status is not None:
            updates.append("status = %s")
            params.append(data.status)
            # Se publicando, atualizar published_at
            if data.status == 'published':
                updates.append("published_at = GETUTCDATE()")
        if data.category is not None:
            updates.append("category = %s")
            params.append(data.category)
        if data.tags is not None:
            updates.append("tags = %s")
            params.append(json.dumps(data.tags))
        if data.author_name is not None:
            updates.append("author_name = %s")
            params.append(data.author_name)
        if data.source_article_ids is not None:
            updates.append("source_article_ids = %s")
            params.append(json.dumps(data.source_article_ids))
        if data.generation_config is not None:
            updates.append("generation_config = %s")
            params.append(json.dumps(data.generation_config))

        if not updates:
            return self.get_user_article_by_id(article_id, user_id=user_id)

        updates.append("updated_at = GETUTCDATE()")
        params.append(str(article_id))

        where_conditions = "id = %s AND deleted_at IS NULL"
        if user_id:
            where_conditions += " AND user_id = %s"
            params.append(user_id)

        query = f"""
            UPDATE user_articles
            SET {', '.join(updates)}
            WHERE {where_conditions}
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            affected = cursor.rowcount
            conn.commit()

            if affected == 0:
                return None

        return self.get_user_article_by_id(article_id, user_id=user_id)

    def delete_user_article(self, article_id: UUID, user_id: Optional[str] = None) -> bool:
        """
        Soft delete de um artigo de usuario.

        Args:
            article_id: ID do artigo
            user_id: Scope by owner (required for non-admin users)

        Returns:
            True se deletado, False se nao encontrado
        """
        params = [str(article_id)]
        where = "id = %s AND deleted_at IS NULL"
        if user_id:
            where += " AND user_id = %s"
            params.append(user_id)

        query = f"""
            UPDATE user_articles
            SET deleted_at = GETUTCDATE(), updated_at = GETUTCDATE()
            WHERE {where}
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def _row_to_user_article(self, row) -> UserArticle:
        """Converte uma row do cursor para UserArticle."""
        return UserArticle(
            id=row[0],
            title=row[1],
            linha_fina=row[2],
            content=row[3],
            preview=row[4],
            status=row[5],
            category=row[6],
            tags=row[7],  # Sera parseado pelo validator
            source_article_ids=row[8],  # Sera parseado pelo validator
            generation_config=row[9],  # Sera parseado pelo validator
            author_name=row[10],
            created_at=row[11],
            updated_at=row[12],
            published_at=row[13],
            deleted_at=row[14],
            titulo_curto=row[15] if len(row) > 15 else None,
            resumo=row[16] if len(row) > 16 else [],  # Sera parseado pelo validator
        )

    # ========================================
    # ARTICLE EMBEDDINGS
    # ========================================

    def save_article_embedding(
        self,
        article_id: UUID,
        embedding: EmbeddingVector,
        model_version: str = 'text-embedding-3-small'
    ) -> bool:
        """
        Salva ou atualiza o embedding de um artigo.

        Args:
            article_id: ID do artigo
            embedding: Vetor de embedding (lista de floats)
            model_version: Versao do modelo usado para gerar o embedding

        Returns:
            True se salvo com sucesso, False caso contrario
        """
        # Converter lista para JSON string (SQL Server VECTOR aceita JSON)
        embedding_json = json.dumps(embedding)

        query = """
            MERGE INTO article_embeddings AS target
            USING (SELECT %s AS article_id) AS source
            ON target.article_id = source.article_id
            WHEN MATCHED THEN
                UPDATE SET
                    embedding = %s,
                    model_version = %s,
                    updated_at = GETUTCDATE()
            WHEN NOT MATCHED THEN
                INSERT (article_id, embedding, model_version)
                VALUES (%s, %s, %s);
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    str(article_id),
                    embedding_json,
                    model_version,
                    str(article_id),
                    embedding_json,
                    model_version
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving embedding for article {article_id}: {e}")
            return False

    def get_article_embedding(self, article_id: UUID) -> Optional[dict]:
        """
        Retorna o embedding de um artigo.

        Args:
            article_id: ID do artigo

        Returns:
            Dict com embedding, model_version e timestamps, ou None se nao encontrado
        """
        query = """
            SELECT article_id, embedding, model_version, created_at, updated_at
            FROM article_embeddings
            WHERE article_id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(article_id),))
                row = cursor.fetchone()

                if not row:
                    return None

                # Parse embedding JSON back to list
                embedding = json.loads(row[1]) if row[1] else None

                return {
                    'article_id': row[0],
                    'embedding': embedding,
                    'model_version': row[2],
                    'created_at': row[3],
                    'updated_at': row[4]
                }
        except Exception as e:
            logger.error(f"Error getting embedding for article {article_id}: {e}")
            return None

    def get_articles_without_embedding(self, limit: int = 100) -> List[dict]:
        """
        Retorna artigos que ainda nao possuem embedding.

        Args:
            limit: Numero maximo de artigos a retornar

        Returns:
            Lista de dicts com id, title, content, preview dos artigos
        """
        query = """
            SELECT TOP %s
                a.id, a.title, a.content, a.preview
            FROM collected_articles a
            LEFT JOIN article_embeddings e ON a.id = e.article_id
            WHERE e.article_id IS NULL
            ORDER BY a.collected_at DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()

                return [
                    {
                        'id': row[0],
                        'title': row[1],
                        'content': row[2],
                        'preview': row[3]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting articles without embedding: {e}")
            return []

    def mark_article_has_embedding(self, article_id: UUID) -> bool:
        """
        Marca que um artigo possui embedding (atualiza has_embedding flag na tabela de artigos).

        Args:
            article_id: ID do artigo

        Returns:
            True se atualizado com sucesso
        """
        query = """
            UPDATE collected_articles
            SET has_embedding = 1, updated_at = GETUTCDATE()
            WHERE id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(article_id),))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking article {article_id} has embedding: {e}")
            return False

    # ========================================
    # SEMANTIC THEMES
    # ========================================

    def create_theme(
        self,
        name: str,
        slug: str,
        centroid: Optional[EmbeddingVector] = None,
        article_count: int = 0,
        classification: Optional[dict] = None
    ) -> Optional[dict]:
        """
        Cria um novo tema semantico.

        Args:
            name: Nome do tema (ex: "Eleicoes 2026")
            slug: Slug URL-friendly (ex: "eleicoes-2026")
            centroid: Vetor centroide do tema (media dos embeddings)
            article_count: Contagem inicial de artigos
            classification: Metadados de classificacao (categoria, subcategoria, etc)

        Returns:
            Dict com dados do tema criado, ou None se falhar
        """
        centroid_json = json.dumps(centroid) if centroid else None
        classification_json = json.dumps(classification) if classification else None

        query = """
            INSERT INTO themes
            (name, slug, centroid, article_count, classification)
            OUTPUT INSERTED.id, INSERTED.first_seen_at, INSERTED.last_updated_at, INSERTED.status
            VALUES (%s, %s, %s, %s, %s)
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    name,
                    slug,
                    centroid_json,
                    article_count,
                    classification_json
                ))
                row = cursor.fetchone()
                conn.commit()

                return {
                    'id': row[0],
                    'name': name,
                    'slug': slug,
                    'centroid': centroid,
                    'article_count': article_count,
                    'classification': classification,
                    'status': row[3],
                    'first_seen_at': row[1],
                    'last_updated_at': row[2]
                }
        except Exception as e:
            logger.error(f"Error creating theme '{name}': {e}")
            return None

    def get_theme(self, theme_id: UUID) -> Optional[dict]:
        """
        Retorna um tema pelo ID.

        Args:
            theme_id: ID do tema

        Returns:
            Dict com dados do tema ou None se nao encontrado
        """
        query = """
            SELECT id, name, slug, centroid, article_count, classification,
                   status, avg_score, min_score, max_score,
                   first_seen_at, last_updated_at, expires_at
            FROM themes
            WHERE id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(theme_id),))
                row = cursor.fetchone()

                if not row:
                    return None

                return self._row_to_theme(row)
        except Exception as e:
            logger.error(f"Error getting theme {theme_id}: {e}")
            return None

    def get_theme_by_slug(self, slug: str) -> Optional[dict]:
        """
        Retorna um tema pelo slug.

        Args:
            slug: Slug do tema

        Returns:
            Dict com dados do tema ou None se nao encontrado
        """
        query = """
            SELECT id, name, slug, centroid, article_count, classification,
                   status, avg_score, min_score, max_score,
                   first_seen_at, last_updated_at, expires_at
            FROM themes
            WHERE slug = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (slug,))
                row = cursor.fetchone()

                if not row:
                    return None

                return self._row_to_theme(row)
        except Exception as e:
            logger.error(f"Error getting theme by slug '{slug}': {e}")
            return None

    def get_all_themes(self, status: str = 'active') -> List[dict]:
        """
        Retorna todos os temas com determinado status.

        Args:
            status: Status do tema ('active', 'inactive', 'expired')

        Returns:
            Lista de dicts com dados dos temas
        """
        query = """
            SELECT id, name, slug, centroid, article_count, classification,
                   status, avg_score, min_score, max_score,
                   first_seen_at, last_updated_at, expires_at
            FROM themes
            WHERE status = %s
            ORDER BY article_count DESC, name ASC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (status,))
                rows = cursor.fetchall()

                return [self._row_to_theme(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting themes with status '{status}': {e}")
            return []

    def update_theme(self, theme_id: UUID, **kwargs) -> Optional[dict]:
        """
        Atualiza um tema existente.

        Args:
            theme_id: ID do tema
            **kwargs: Campos para atualizar (name, slug, centroid, article_count,
                      classification, status, avg_score, min_score, max_score, expires_at)

        Returns:
            Dict com tema atualizado ou None se nao encontrado
        """
        updates = []
        params = []

        if 'name' in kwargs:
            updates.append("name = %s")
            params.append(kwargs['name'])
        if 'slug' in kwargs:
            updates.append("slug = %s")
            params.append(kwargs['slug'])
        if 'centroid' in kwargs:
            updates.append("centroid = %s")
            params.append(json.dumps(kwargs['centroid']) if kwargs['centroid'] else None)
        if 'article_count' in kwargs:
            updates.append("article_count = %s")
            params.append(kwargs['article_count'])
        if 'classification' in kwargs:
            updates.append("classification = %s")
            params.append(json.dumps(kwargs['classification']) if kwargs['classification'] else None)
        if 'status' in kwargs:
            updates.append("status = %s")
            params.append(kwargs['status'])
        if 'avg_score' in kwargs:
            updates.append("avg_score = %s")
            params.append(kwargs['avg_score'])
        if 'min_score' in kwargs:
            updates.append("min_score = %s")
            params.append(kwargs['min_score'])
        if 'max_score' in kwargs:
            updates.append("max_score = %s")
            params.append(kwargs['max_score'])
        if 'expires_at' in kwargs:
            updates.append("expires_at = %s")
            params.append(kwargs['expires_at'])

        if not updates:
            return self.get_theme(theme_id)

        updates.append("last_updated_at = GETUTCDATE()")
        params.append(str(theme_id))

        query = f"""
            UPDATE themes
            SET {', '.join(updates)}
            WHERE id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()

            return self.get_theme(theme_id)
        except Exception as e:
            logger.error(f"Error updating theme {theme_id}: {e}")
            return None

    def _row_to_theme(self, row) -> dict:
        """Converte uma row do cursor para dict de tema."""
        # Handle empty strings and None for JSON fields
        centroid_raw = row[3]
        classification_raw = row[5]

        centroid = json.loads(centroid_raw) if centroid_raw and centroid_raw.strip() else None
        classification = json.loads(classification_raw) if classification_raw and classification_raw.strip() else None

        return {
            'id': row[0],
            'name': row[1],
            'slug': row[2],
            'centroid': centroid,
            'article_count': row[4],
            'classification': classification,
            'status': row[6],
            'avg_score': row[7],
            'min_score': row[8],
            'max_score': row[9],
            'first_seen_at': row[10],
            'last_updated_at': row[11],
            'expires_at': row[12]
        }

    # ========================================
    # ARTICLE-THEME RELATIONS
    # ========================================

    def add_article_to_theme(
        self,
        article_id: UUID,
        theme_id: UUID,
        similarity_score: float,
        is_seed: bool = False
    ) -> bool:
        """
        Adiciona um artigo a um tema.

        Args:
            article_id: ID do artigo
            theme_id: ID do tema
            similarity_score: Score de similaridade (0-1)
            is_seed: Se o artigo e um dos artigos semente do tema

        Returns:
            True se adicionado com sucesso
        """
        query = """
            MERGE INTO article_themes AS target
            USING (SELECT %s AS article_id, %s AS theme_id) AS source
            ON target.article_id = source.article_id AND target.theme_id = source.theme_id
            WHEN MATCHED THEN
                UPDATE SET
                    similarity_score = %s,
                    is_seed = %s
            WHEN NOT MATCHED THEN
                INSERT (article_id, theme_id, similarity_score, is_seed)
                VALUES (%s, %s, %s, %s);
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    str(article_id),
                    str(theme_id),
                    similarity_score,
                    is_seed,
                    str(article_id),
                    str(theme_id),
                    similarity_score,
                    is_seed
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding article {article_id} to theme {theme_id}: {e}")
            return False

    def get_articles_by_theme(
        self,
        theme_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Article], int]:
        """
        Retorna artigos de um tema com paginacao.

        Args:
            theme_id: ID do tema
            limit: Numero de artigos por pagina
            offset: Offset para paginacao

        Returns:
            Tuple (lista de artigos, total de artigos no tema)
        """
        # Query para dados com JOIN para obter detalhes do artigo
        query = """
            SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,
                   a.image_url, a.author, a.category, a.tags, a.published_at,
                   a.collected_at, a.hash,
                   s.name as source_name, s.url as source_url, s.favicon_url,
                   r.similarity_score, r.is_seed
            FROM article_themes r
            JOIN collected_articles a ON r.article_id = a.id
            JOIN sources s ON a.source_id = s.id
            WHERE r.theme_id = %s
            ORDER BY r.similarity_score DESC, a.published_at DESC
            OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
        """

        # Query para total
        count_query = """
            SELECT COUNT(*) FROM article_themes WHERE theme_id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Executar count
                cursor.execute(count_query, (str(theme_id),))
                total = cursor.fetchone()[0]

                # Executar query principal
                cursor.execute(query, (str(theme_id), offset, limit))
                rows = cursor.fetchall()

                articles = []
                for row in rows:
                    article = self._row_to_article(row[:16])
                    # Adicionar campos extras da relacao
                    article.similarity_score = row[16]
                    article.is_seed = bool(row[17])
                    articles.append(article)

                return articles, total
        except Exception as e:
            logger.error(f"Error getting articles for theme {theme_id}: {e}")
            return [], 0

    def get_article_themes(self, article_id: UUID) -> List[dict]:
        """
        Retorna os temas aos quais um artigo pertence.

        Args:
            article_id: ID do artigo

        Returns:
            Lista de dicts com theme_id, name, slug, similarity_score, is_seed
        """
        query = """
            SELECT t.id, t.name, t.slug, r.similarity_score, r.is_seed
            FROM article_themes r
            JOIN themes t ON r.theme_id = t.id
            WHERE r.article_id = %s
            ORDER BY r.similarity_score DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(article_id),))
                rows = cursor.fetchall()

                return [
                    {
                        'theme_id': row[0],
                        'name': row[1],
                        'slug': row[2],
                        'similarity_score': row[3],
                        'is_seed': bool(row[4])
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting themes for article {article_id}: {e}")
            return []

    def get_articles_without_theme(self, limit: int = 100) -> List[dict]:
        """
        Retorna artigos que ainda nao pertencem a nenhum tema.

        Args:
            limit: Numero maximo de artigos a retornar

        Returns:
            Lista de dicts com id, title, preview dos artigos
        """
        query = """
            SELECT TOP %s
                a.id, a.title, a.preview
            FROM collected_articles a
            LEFT JOIN article_themes r ON a.id = r.article_id
            WHERE r.article_id IS NULL
            ORDER BY a.collected_at DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()

                return [
                    {
                        'id': row[0],
                        'title': row[1],
                        'preview': row[2]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting articles without theme: {e}")
            return []

    def get_articles_pending_clustering(self, limit: int = 100) -> List[dict]:
        """
        Retorna artigos que possuem embedding mas ainda nao pertencem a nenhum tema.
        Estes sao os artigos prontos para clustering.

        Args:
            limit: Numero maximo de artigos a retornar

        Returns:
            Lista de dicts com id, title, preview e embedding dos artigos
        """
        query = """
            SELECT TOP %s
                a.id, a.title, a.preview, e.embedding
            FROM collected_articles a
            JOIN article_embeddings e ON a.id = e.article_id
            LEFT JOIN article_themes r ON a.id = r.article_id
            WHERE r.article_id IS NULL
            ORDER BY a.collected_at DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()

                return [
                    {
                        'id': row[0],
                        'title': row[1],
                        'preview': row[2],
                        'embedding': json.loads(row[3]) if row[3] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting articles pending clustering: {e}")
            return []

    # ========================================
    # ARTICLE SCORES
    # ========================================

    def save_article_score(
        self,
        article_id: UUID,
        signals: dict,
        scores: dict,
        classification: str,
        scored_by: str = 'system'
    ) -> bool:
        """
        Salva ou atualiza o score de um artigo.

        Args:
            article_id: ID do artigo
            signals: Dict com sinais extraidos (social_engagement, source_authority, etc)
            scores: Dict com scores calculados (relevance, freshness, credibility, etc)
            classification: Classificacao final (hot, trending, normal, low)
            scored_by: Quem calculou o score ('system', 'ai', 'manual')

        Returns:
            True se salvo com sucesso
        """
        signals_json = json.dumps(signals)
        scores_json = json.dumps(scores)

        query = """
            MERGE INTO article_scores AS target
            USING (SELECT %s AS article_id) AS source
            ON target.article_id = source.article_id
            WHEN MATCHED THEN
                UPDATE SET
                    signals = %s,
                    scores = %s,
                    classification = %s,
                    scored_by = %s,
                    scored_at = GETUTCDATE()
            WHEN NOT MATCHED THEN
                INSERT (article_id, signals, scores, classification, scored_by)
                VALUES (%s, %s, %s, %s, %s);
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    str(article_id),
                    signals_json,
                    scores_json,
                    classification,
                    scored_by,
                    str(article_id),
                    signals_json,
                    scores_json,
                    classification,
                    scored_by
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving score for article {article_id}: {e}")
            return False

    def get_article_score(self, article_id: UUID) -> Optional[dict]:
        """
        Retorna o score de um artigo.

        Args:
            article_id: ID do artigo

        Returns:
            Dict com signals, scores, classification e timestamps, ou None
        """
        query = """
            SELECT article_id, signals, scores, classification, scored_by, scored_at
            FROM article_scores
            WHERE article_id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(article_id),))
                row = cursor.fetchone()

                if not row:
                    return None

                return {
                    'article_id': row[0],
                    'signals': json.loads(row[1]) if row[1] else {},
                    'scores': json.loads(row[2]) if row[2] else {},
                    'classification': row[3],
                    'scored_by': row[4],
                    'scored_at': row[5]
                }
        except Exception as e:
            logger.error(f"Error getting score for article {article_id}: {e}")
            return None

    def get_articles_without_score(self, limit: int = 100) -> List[dict]:
        """
        Retorna artigos que ainda nao possuem score.

        Args:
            limit: Numero maximo de artigos a retornar

        Returns:
            Lista de dicts com id, title, preview dos artigos
        """
        query = """
            SELECT TOP %s
                a.id, a.title, a.preview, a.published_at,
                s.name as source_name
            FROM collected_articles a
            JOIN sources s ON a.source_id = s.id
            LEFT JOIN article_scores sc ON a.id = sc.article_id
            WHERE sc.article_id IS NULL
            ORDER BY a.collected_at DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()

                return [
                    {
                        'id': row[0],
                        'title': row[1],
                        'preview': row[2],
                        'published_at': row[3],
                        'source_name': row[4]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting articles without score: {e}")
            return []

    def mark_article_has_score(self, article_id: UUID) -> bool:
        """
        Marca que um artigo possui score (atualiza has_score flag na tabela de artigos).

        Args:
            article_id: ID do artigo

        Returns:
            True se atualizado com sucesso
        """
        query = """
            UPDATE collected_articles
            SET has_score = 1, updated_at = GETUTCDATE()
            WHERE id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(article_id),))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking article {article_id} has score: {e}")
            return False

    def get_theme_article_scores(self, theme_id: UUID) -> List[dict]:
        """
        Retorna todos os scores de artigos de um tema para calculo de agregados.

        Args:
            theme_id: ID do tema

        Returns:
            Lista de dicts com article_id, scores, classification
        """
        query = """
            SELECT sc.article_id, sc.scores, sc.classification
            FROM article_scores sc
            JOIN article_themes r ON sc.article_id = r.article_id
            WHERE r.theme_id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(theme_id),))
                rows = cursor.fetchall()

                return [
                    {
                        'article_id': row[0],
                        'scores': json.loads(row[1]) if row[1] else {},
                        'classification': row[2]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting article scores for theme {theme_id}: {e}")
            return []


    # ========================================
    # EVENT SIGNATURES
    # ========================================

    def save_event_signature(
        self,
        article_id: UUID,
        people: List[str],
        organizations: List[str],
        locations: List[str],
        event_action: str,
        unique_details: List[str],
        canonical_key: str,
        event_date: Optional[str] = None,
        confidence: float = 0.8,
        theme_id: Optional[UUID] = None
    ) -> Optional[dict]:
        """
        Salva ou atualiza a assinatura de evento de um artigo.

        Args:
            article_id: ID do artigo
            people: Lista de pessoas envolvidas
            organizations: Lista de organizacoes
            locations: Lista de locais
            event_action: Acao principal do evento
            unique_details: Detalhes unicos
            canonical_key: Chave canonica para matching
            event_date: Data do evento (YYYY-MM-DD)
            confidence: Confianca da extracao (0-1)
            theme_id: ID do tema associado

        Returns:
            Dict com dados da assinatura ou None se falhar
        """
        people_json = json.dumps(people) if people else '[]'
        organizations_json = json.dumps(organizations) if organizations else '[]'
        locations_json = json.dumps(locations) if locations else '[]'
        unique_details_json = json.dumps(unique_details) if unique_details else '[]'

        query = """
            MERGE INTO event_signatures AS target
            USING (SELECT %s AS article_id) AS source
            ON target.article_id = source.article_id
            WHEN MATCHED THEN
                UPDATE SET
                    people = %s,
                    organizations = %s,
                    locations = %s,
                    event_action = %s,
                    unique_details = %s,
                    canonical_key = %s,
                    event_date = %s,
                    confidence = %s,
                    theme_id = %s,
                    extracted_at = GETUTCDATE()
            WHEN NOT MATCHED THEN
                INSERT (article_id, people, organizations, locations, event_action,
                        unique_details, canonical_key, event_date, confidence, theme_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            OUTPUT INSERTED.id, INSERTED.extracted_at;
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    str(article_id),
                    people_json, organizations_json, locations_json,
                    event_action, unique_details_json, canonical_key,
                    event_date, confidence, str(theme_id) if theme_id else None,
                    str(article_id),
                    people_json, organizations_json, locations_json,
                    event_action, unique_details_json, canonical_key,
                    event_date, confidence, str(theme_id) if theme_id else None
                ))
                row = cursor.fetchone()
                conn.commit()

                return {
                    'id': row[0],
                    'article_id': article_id,
                    'people': people,
                    'organizations': organizations,
                    'locations': locations,
                    'event_action': event_action,
                    'unique_details': unique_details,
                    'canonical_key': canonical_key,
                    'event_date': event_date,
                    'confidence': confidence,
                    'theme_id': theme_id,
                    'extracted_at': row[1]
                }
        except Exception as e:
            logger.error(f"Error saving event signature for article {article_id}: {e}")
            return None

    def get_event_signature(self, article_id: UUID) -> Optional[dict]:
        """
        Retorna a assinatura de evento de um artigo.

        Args:
            article_id: ID do artigo

        Returns:
            Dict com dados da assinatura ou None se nao encontrado
        """
        query = """
            SELECT id, article_id, theme_id, people, organizations, locations,
                   event_action, unique_details, canonical_key, event_date,
                   confidence, extracted_at
            FROM event_signatures
            WHERE article_id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(article_id),))
                row = cursor.fetchone()

                if not row:
                    return None

                return self._row_to_event_signature(row)
        except Exception as e:
            logger.error(f"Error getting event signature for article {article_id}: {e}")
            return None

    def find_signatures_by_canonical_key(
        self,
        canonical_key: str,
        limit: int = 10
    ) -> List[dict]:
        """
        Busca assinaturas com chave canonica exata ou similar.

        Args:
            canonical_key: Chave canonica para buscar
            limit: Numero maximo de resultados

        Returns:
            Lista de assinaturas ordenadas por relevancia
        """
        # Busca exata primeiro
        query_exact = """
            SELECT TOP %s
                es.id, es.article_id, es.theme_id, es.people, es.organizations,
                es.locations, es.event_action, es.unique_details, es.canonical_key,
                es.event_date, es.confidence, es.extracted_at,
                t.id AS theme_id_from_theme, t.name AS theme_name
            FROM event_signatures es
            LEFT JOIN themes t ON es.theme_id = t.id
            WHERE es.canonical_key = %s
            ORDER BY es.confidence DESC, es.extracted_at DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query_exact, (limit, canonical_key))
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    sig = self._row_to_event_signature(row[:12])
                    sig['theme_name'] = row[13]
                    sig['match_type'] = 'exact'
                    results.append(sig)

                return results
        except Exception as e:
            logger.error(f"Error finding signatures by canonical key: {e}")
            return []

    def find_themes_by_canonical_key(self, canonical_key: str) -> List[dict]:
        """
        Busca temas com chave canonica de evento.

        Args:
            canonical_key: Chave canonica para buscar

        Returns:
            Lista de temas com match
        """
        query = """
            SELECT id, name, slug, centroid, article_count, canonical_event_key,
                   primary_entities, seed_article_id, status
            FROM themes
            WHERE canonical_event_key = %s
              AND status = 'active'
            ORDER BY article_count DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (canonical_key,))
                rows = cursor.fetchall()

                return [
                    {
                        'id': row[0],
                        'name': row[1],
                        'slug': row[2],
                        'centroid': json.loads(row[3]) if row[3] else None,
                        'article_count': row[4],
                        'canonical_event_key': row[5],
                        'primary_entities': json.loads(row[6]) if row[6] else None,
                        'seed_article_id': row[7],
                        'status': row[8],
                        'match_type': 'exact'
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error finding themes by canonical key: {e}")
            return []

    def get_articles_pending_signature(self, limit: int = 100) -> List[dict]:
        """
        Retorna artigos que ainda nao possuem assinatura de evento extraida.

        Args:
            limit: Numero maximo de artigos a retornar

        Returns:
            Lista de dicts com id, title, preview dos artigos
        """
        query = """
            SELECT TOP %s
                a.id, a.title, a.preview, a.content, a.collected_at
            FROM collected_articles a
            LEFT JOIN event_signatures es ON a.id = es.article_id
            WHERE es.article_id IS NULL
              AND a.collected_at >= DATEADD(day, -7, GETUTCDATE())
            ORDER BY a.collected_at DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()

                return [
                    {
                        'id': row[0],
                        'title': row[1],
                        'preview': row[2],
                        'content': row[3],
                        'collected_at': row[4]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting articles pending signature: {e}")
            return []

    def update_event_signature_theme(
        self,
        article_id: UUID,
        theme_id: UUID
    ) -> bool:
        """
        Atualiza o tema associado a uma assinatura de evento.

        Args:
            article_id: ID do artigo
            theme_id: ID do tema

        Returns:
            True se atualizado com sucesso
        """
        query = """
            UPDATE event_signatures
            SET theme_id = %s
            WHERE article_id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(theme_id), str(article_id)))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating event signature theme: {e}")
            return False

    def get_theme_signatures(self, theme_id: UUID) -> List[dict]:
        """
        Retorna todas as assinaturas de evento de um tema.

        Args:
            theme_id: ID do tema

        Returns:
            Lista de assinaturas do tema
        """
        query = """
            SELECT es.id, es.article_id, es.theme_id, es.people, es.organizations,
                   es.locations, es.event_action, es.unique_details, es.canonical_key,
                   es.event_date, es.confidence, es.extracted_at,
                   a.title
            FROM event_signatures es
            JOIN collected_articles a ON es.article_id = a.id
            WHERE es.theme_id = %s
            ORDER BY es.extracted_at DESC
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(theme_id),))
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    sig = self._row_to_event_signature(row[:12])
                    sig['article_title'] = row[12]
                    results.append(sig)

                return results
        except Exception as e:
            logger.error(f"Error getting theme signatures: {e}")
            return []

    def update_theme_event_data(
        self,
        theme_id: UUID,
        canonical_event_key: Optional[str] = None,
        primary_entities: Optional[dict] = None,
        seed_article_id: Optional[UUID] = None
    ) -> bool:
        """
        Atualiza dados de evento de um tema.

        Args:
            theme_id: ID do tema
            canonical_event_key: Chave canonica do evento
            primary_entities: Entidades principais do evento
            seed_article_id: ID do artigo semente

        Returns:
            True se atualizado com sucesso
        """
        updates = []
        params = []

        if canonical_event_key is not None:
            updates.append("canonical_event_key = %s")
            params.append(canonical_event_key)
        if primary_entities is not None:
            updates.append("primary_entities = %s")
            params.append(json.dumps(primary_entities))
        if seed_article_id is not None:
            updates.append("seed_article_id = %s")
            params.append(str(seed_article_id))

        if not updates:
            return True

        updates.append("last_updated_at = GETUTCDATE()")
        params.append(str(theme_id))

        query = f"""
            UPDATE themes
            SET {', '.join(updates)}
            WHERE id = %s
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating theme event data: {e}")
            return False

    def add_article_to_theme_with_match_type(
        self,
        article_id: UUID,
        theme_id: UUID,
        similarity_score: float,
        match_type: str,
        is_seed: bool = False
    ) -> bool:
        """
        Adiciona um artigo a um tema com tipo de match.

        Args:
            article_id: ID do artigo
            theme_id: ID do tema
            similarity_score: Score de similaridade (0-1)
            match_type: Tipo de match ('exact', 'entity', 'verified', 'embedding')
            is_seed: Se o artigo e semente do tema

        Returns:
            True se adicionado com sucesso
        """
        query = """
            MERGE INTO article_themes AS target
            USING (SELECT %s AS article_id, %s AS theme_id) AS source
            ON target.article_id = source.article_id AND target.theme_id = source.theme_id
            WHEN MATCHED THEN
                UPDATE SET
                    similarity_score = %s,
                    match_type = %s,
                    is_seed = %s
            WHEN NOT MATCHED THEN
                INSERT (article_id, theme_id, similarity_score, match_type, is_seed)
                VALUES (%s, %s, %s, %s, %s);
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    str(article_id), str(theme_id),
                    similarity_score, match_type, is_seed,
                    str(article_id), str(theme_id),
                    similarity_score, match_type, is_seed
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding article {article_id} to theme {theme_id}: {e}")
            return False

    def _row_to_event_signature(self, row) -> dict:
        """Converte uma row do cursor para dict de assinatura."""
        return {
            'id': row[0],
            'article_id': row[1],
            'theme_id': row[2],
            'people': json.loads(row[3]) if row[3] else [],
            'organizations': json.loads(row[4]) if row[4] else [],
            'locations': json.loads(row[5]) if row[5] else [],
            'event_action': row[6],
            'unique_details': json.loads(row[7]) if row[7] else [],
            'canonical_key': row[8],
            'event_date': row[9],
            'confidence': float(row[10]) if row[10] else 0.0,
            'extracted_at': row[11]
        }

    # ========================================
    # GENERATION AUDIT TRAIL
    # ========================================

    def insert_generation_audit(self, audit_data: dict) -> bool:
        """
        Insert a generation audit trail record.

        Non-blocking: errors are logged but never propagated.
        Long fields are truncated to prevent DB overflow.

        Args:
            audit_data: Dict with audit fields (see migration 004)

        Returns:
            True if inserted successfully, False otherwise
        """
        try:
            # Truncate long fields to prevent overflow
            def _trunc(val, max_len):
                if val and isinstance(val, str) and len(val) > max_len:
                    return val[:max_len]
                return val

            def _json_trunc(val, max_len):
                if val is None:
                    return None
                s = json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
                return _trunc(s, max_len)

            query = """
                INSERT INTO generation_audit_trail
                (article_id, theme_id, request_payload, system_prompt_hash,
                 user_prompt_text, enrichment_result, raw_llm_response,
                 verification_result, cove_applied, cove_reclassified,
                 safety_gate_decision, confidence_score, risk_level,
                 publish_blocked, block_reason, phase_timings, total_duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    audit_data.get('article_id'),
                    audit_data.get('theme_id'),
                    _json_trunc(audit_data.get('request_payload'), 5000),
                    _trunc(audit_data.get('system_prompt_hash'), 64),
                    _trunc(audit_data.get('user_prompt_text'), 5000),
                    _json_trunc(audit_data.get('enrichment_result'), 5000),
                    _trunc(audit_data.get('raw_llm_response'), 10000),
                    _json_trunc(audit_data.get('verification_result'), 10000),
                    1 if audit_data.get('cove_applied') else 0,
                    audit_data.get('cove_reclassified', 0),
                    _trunc(audit_data.get('safety_gate_decision'), 20),
                    audit_data.get('confidence_score'),
                    _trunc(audit_data.get('risk_level'), 20),
                    1 if audit_data.get('publish_blocked') else 0,
                    _trunc(audit_data.get('block_reason'), 500),
                    _json_trunc(audit_data.get('phase_timings'), 500),
                    audit_data.get('total_duration_ms'),
                ))
                conn.commit()

            logger.debug("Generation audit trail inserted successfully")
            return True

        except Exception as e:
            logger.warning(f"Failed to insert generation audit (non-blocking): {e}")
            return False

    def insert_llm_usage_log(self, log_data: dict) -> bool:
        """
        Insert an LLM usage log record for cost and performance tracking.

        Non-blocking: errors are logged but never propagated.

        Args:
            log_data: Dict with fields matching llm_usage_log table

        Returns:
            True if inserted successfully, False otherwise
        """
        try:
            def _trunc(val, max_len):
                if val and isinstance(val, str) and len(val) > max_len:
                    return val[:max_len]
                return val

            query = """
                INSERT INTO llm_usage_log
                (correlation_id, task_type, model, endpoint, provider,
                 input_tokens, output_tokens, input_cost_usd, output_cost_usd,
                 latency_ms, status, error_message, response_chars, stop_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    _trunc(log_data.get('correlation_id'), 64),
                    _trunc(log_data.get('task_type', 'unknown'), 50),
                    _trunc(log_data.get('model'), 100),
                    _trunc(log_data.get('endpoint'), 500),
                    _trunc(log_data.get('provider', 'anthropic'), 20),
                    log_data.get('input_tokens'),
                    log_data.get('output_tokens'),
                    log_data.get('input_cost_usd'),
                    log_data.get('output_cost_usd'),
                    log_data.get('latency_ms'),
                    _trunc(log_data.get('status', 'success'), 10),
                    _trunc(log_data.get('error_message'), 500),
                    log_data.get('response_chars'),
                    _trunc(log_data.get('stop_reason'), 20),
                ))
                conn.commit()

            return True

        except Exception as e:
            logger.warning(f"Failed to insert LLM usage log (non-blocking): {e}")
            return False

    # ========================================
    # USERS & AUTH
    # ========================================

    USER_COLUMNS = "id, name, email, role, avatar, is_new_user, is_active, last_login, failed_login_attempts, locked_until, created_at, updated_at"
    USER_WITH_PW_COLUMNS = "id, name, email, password_hash, role, avatar, is_new_user, is_active, last_login, failed_login_attempts, locked_until, created_at, updated_at"

    LOCKOUT_THRESHOLD = 5
    LOCKOUT_MINUTES = 15

    def _row_to_user(self, row) -> User:
        """Convert DB row to User model."""
        return User(
            id=row[0],
            name=row[1],
            email=row[2],
            role=row[3],
            avatar=row[4],
            is_new_user=bool(row[5]),
            is_active=bool(row[6]),
            last_login=row[7],
            failed_login_attempts=row[8] or 0,
            locked_until=row[9],
            created_at=row[10],
            updated_at=row[11],
        )

    def _row_to_user_with_password(self, row) -> UserWithPassword:
        """Convert DB row to UserWithPassword model (includes password_hash)."""
        return UserWithPassword(
            id=row[0],
            name=row[1],
            email=row[2],
            password_hash=row[3],
            role=row[4],
            avatar=row[5],
            is_new_user=bool(row[6]),
            is_active=bool(row[7]),
            last_login=row[8],
            failed_login_attempts=row[9] or 0,
            locked_until=row[10],
            created_at=row[11],
            updated_at=row[12],
        )

    def get_user_by_email(self, email: str) -> Optional[UserWithPassword]:
        """Get user by email (includes password_hash for login verification)."""
        query = f"""
            SELECT {self.USER_WITH_PW_COLUMNS}
            FROM users
            WHERE email = %s AND is_active = 1
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(email),))
            row = cursor.fetchone()
            return self._row_to_user_with_password(row) if row else None

    def get_user_by_id(self, user_id) -> Optional[User]:
        """Get user by ID (excludes password_hash)."""
        query = f"""
            SELECT {self.USER_COLUMNS}
            FROM users
            WHERE id = %s AND is_active = 1
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(user_id),))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None

    def get_users(self, page: int = 1, limit: int = 20, search: Optional[str] = None, role: Optional[str] = None) -> Tuple[List[User], int]:
        """List users with pagination and optional filters."""
        limit = min(limit, 100)
        offset = (page - 1) * limit

        conditions = ["is_active = 1"]
        params = []

        if search:
            conditions.append("(name LIKE %s OR email LIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])

        if role:
            conditions.append("role = %s")
            params.append(role)

        where_clause = "WHERE " + " AND ".join(conditions)

        count_query = f"SELECT COUNT(*) FROM users {where_clause}"

        query = f"""
            SELECT {self.USER_COLUMNS}
            FROM users
            {where_clause}
            ORDER BY name ASC
            OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            cursor.execute(query, params + [offset, limit])
            rows = cursor.fetchall()
            users = [self._row_to_user(row) for row in rows]

        return users, total

    def create_user(self, user_data: UserCreate, password_hash: str) -> User:
        """Create a new user. Password comes pre-hashed from auth_service."""
        query = f"""
            INSERT INTO users (name, email, password_hash, role)
            OUTPUT {', '.join('INSERTED.' + c.strip() for c in self.USER_COLUMNS.split(','))}
            VALUES (%s, %s, %s, %s)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                str(user_data.name),
                str(user_data.email),
                str(password_hash),
                str(user_data.role),
            ))
            row = cursor.fetchone()
            conn.commit()
            return self._row_to_user(row)

    def update_user(self, user_id, data: UserUpdate) -> Optional[User]:
        """Update user fields dynamically from non-None fields."""
        updates = []
        params = []

        if data.name is not None:
            updates.append("name = %s")
            params.append(data.name)
        if data.email is not None:
            updates.append("email = %s")
            params.append(data.email)
        if data.role is not None:
            updates.append("role = %s")
            params.append(data.role)
        if data.is_active is not None:
            updates.append("is_active = %s")
            params.append(1 if data.is_active else 0)

        if not updates:
            return self.get_user_by_id(user_id)

        updates.append("updated_at = GETUTCDATE()")
        params.append(str(user_id))

        query = f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = %s AND is_active = 1
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

        return self.get_user_by_id(user_id)

    def deactivate_user(self, user_id) -> bool:
        """Soft-deactivate a user."""
        query = """
            UPDATE users
            SET is_active = 0, updated_at = GETUTCDATE()
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(user_id),))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def reset_user_password(self, user_id, new_password_hash: str) -> bool:
        """Reset user password and mark as new user (force password change)."""
        query = """
            UPDATE users
            SET password_hash = %s, is_new_user = 1, updated_at = GETUTCDATE()
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(new_password_hash), str(user_id)))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def set_user_not_new(self, user_id) -> bool:
        """Clear is_new_user flag after user changes password."""
        query = """
            UPDATE users
            SET is_new_user = 0, updated_at = GETUTCDATE()
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(user_id),))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    # --- Login tracking ---

    def record_failed_login(self, user_id) -> None:
        """Increment failed login attempts; lock account after threshold."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE users SET failed_login_attempts = failed_login_attempts + 1, updated_at = GETUTCDATE() WHERE id = %s",
                (str(user_id),)
            )

            cursor.execute(
                "SELECT failed_login_attempts FROM users WHERE id = %s",
                (str(user_id),)
            )
            row = cursor.fetchone()
            if row and row[0] >= self.LOCKOUT_THRESHOLD:
                cursor.execute(
                    "UPDATE users SET locked_until = DATEADD(minute, %s, GETUTCDATE()) WHERE id = %s",
                    (self.LOCKOUT_MINUTES, str(user_id))
                )

            conn.commit()

    def record_successful_login(self, user_id) -> None:
        """Reset failed attempts, clear lock, update last_login."""
        query = """
            UPDATE users
            SET failed_login_attempts = 0, locked_until = NULL,
                last_login = GETUTCDATE(), updated_at = GETUTCDATE()
            WHERE id = %s
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(user_id),))
            conn.commit()

    # --- Token blacklist ---

    def blacklist_token(self, jti: str, user_id, expires_at) -> None:
        """Add a JWT token ID to the blacklist."""
        query = """
            INSERT INTO token_blacklist (token_jti, user_id, expires_at)
            VALUES (%s, %s, %s)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(jti), str(user_id), expires_at))
            conn.commit()

    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if a JWT token ID is blacklisted."""
        query = "SELECT 1 FROM token_blacklist WHERE token_jti = %s"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(jti),))
            return cursor.fetchone() is not None

    def cleanup_expired_blacklist(self) -> int:
        """Remove expired tokens from blacklist. Returns count deleted."""
        query = "DELETE FROM token_blacklist WHERE expires_at < GETUTCDATE()"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    # --- Auth audit log ---

    def log_auth_event(self, user_id, email: str, action: str,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None,
                       metadata: Optional[dict] = None) -> None:
        """Insert an auth audit log entry."""
        query = """
            INSERT INTO auth_audit_log
            (user_id, email, action, ip_address, user_agent, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                str(user_id) if user_id else None,
                str(email),
                str(action),
                str(ip_address) if ip_address else None,
                str(user_agent) if user_agent else None,
                metadata_json,
            ))
            conn.commit()


# Singleton para uso global (thread-safe)
import threading
_db_service: Optional[DatabaseService] = None
_db_service_lock = threading.Lock()

def get_db() -> DatabaseService:
    """Retorna instancia singleton do DatabaseService (thread-safe)."""
    global _db_service
    if _db_service is None:
        with _db_service_lock:
            if _db_service is None:
                _db_service = DatabaseService()
    return _db_service
