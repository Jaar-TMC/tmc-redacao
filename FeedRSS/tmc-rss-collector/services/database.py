"""
Servico de acesso ao banco de dados Azure SQL Server.
Gerencia conexoes e operacoes CRUD para sources, articles e logs.
"""

import os
import pymssql
import logging
from typing import List, Optional, Set, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import json

from models import (
    Source, SourceCreate, SourceUpdate,
    Article, ArticleCreate,
    CollectionLog, CollectionLogCreate,
    UserArticle, UserArticleCreate, UserArticleUpdate
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

    def get_connection(self) -> pymssql.Connection:
        """Obtem uma conexao com o banco de dados."""
        return pymssql.connect(
            server=self.server,
            user=self.username,
            password=self.password,
            database=self.database,
            login_timeout=30,
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

    def get_articles(self, page: int = 1, limit: int = 20,
                     category: Optional[str] = None,
                     source_id: Optional[str] = None,
                     period: Optional[str] = None,
                     search: Optional[str] = None,
                     tag: Optional[str] = None) -> Tuple[List[Article], int]:
        """
        Lista artigos com filtros e paginacao.

        Args:
            page: Pagina atual (1-based)
            limit: Itens por pagina (max 100)
            category: Filtrar por categoria
            source_id: Filtrar por fonte (nome da fonte, não UUID)
            period: 'today', 'week', 'month'
            search: Busca em titulo/conteudo
            tag: Filtrar por tag exata (match no array JSON de tags)

        Returns:
            Tuple (lista de artigos, total de registros)
        """
        limit = min(limit, 100)
        offset = (page - 1) * limit

        # Construir WHERE clause
        conditions = []
        params = []

        if category:
            conditions.append("a.category = %s")
            params.append(category)

        if source_id:
            # Filter by source name (not UUID) - matches frontend filter behavior
            conditions.append("s.name = %s")
            params.append(source_id)

        if period:
            if period == 'today':
                conditions.append("a.published_at >= DATEADD(day, -1, GETUTCDATE())")
            elif period == 'week':
                conditions.append("a.published_at >= DATEADD(week, -1, GETUTCDATE())")
            elif period == 'month':
                conditions.append("a.published_at >= DATEADD(month, -1, GETUTCDATE())")

        if search:
            # Search in title, content, AND tags (tags is JSON array stored as string)
            # Use COLLATE to make search accent-insensitive (AI) and case-insensitive (CI)
            # Also search with dashes replaced by spaces to match "sao-paulo" with "São Paulo"
            search_with_spaces = search.replace('-', ' ')
            search_param = f"%{search}%"

            logger.info(f"[get_articles] Building search condition for: '{search}' -> param: '{search_param}'")

            if search_with_spaces != search:
                # If there were dashes, search for both formats
                search_param_spaces = f"%{search_with_spaces}%"
                conditions.append("""(
                    a.title LIKE %s
                    OR a.title LIKE %s
                    OR a.content LIKE %s
                    OR a.content LIKE %s
                    OR a.tags LIKE %s
                )""")
                params.extend([search_param, search_param_spaces, search_param, search_param_spaces, search_param])
            else:
                conditions.append("""(
                    a.title LIKE %s
                    OR a.content LIKE %s
                    OR a.tags LIKE %s
                )""")
                params.extend([search_param, search_param, search_param])

        if tag:
            # Filter articles that have this exact tag in their JSON tags array
            # Tags are stored as JSON: '["tag1", "tag2", "sao-paulo"]'
            # Use LIKE with quotes to match exact tag in array
            conditions.append("""
                a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
            """)
            # Match the tag in JSON format: "tag-name" (with quotes)
            tag_param = f'%"{tag}"%'
            params.append(tag_param)

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
            OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
        """

        # Query para total (needs JOIN for source name filter)
        count_query = f"""
            SELECT COUNT(*) FROM collected_articles a
            JOIN sources s ON a.source_id = s.id
            {where_clause}
        """

        # Debug logging
        logger.info(f"[get_articles] search={search}, where_clause={where_clause}")
        logger.info(f"[get_articles] params={params}, offset={offset}, limit={limit}")
        logger.info(f"[get_articles] count_query={count_query}")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Executar count
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            logger.info(f"[get_articles] total count={total}")

            # Executar query principal
            cursor.execute(query, params + [offset, limit])
            rows = cursor.fetchall()

            logger.info(f"[get_articles] rows fetched={len(rows)}")

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
        if not articles:
            return 0

        query = """
            INSERT INTO collected_articles
            (source_id, title, content, preview, url, image_url, author,
             category, tags, published_at, collected_at, hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                except pymssql.IntegrityError as e:
                    # Duplicata (hash ou url ja existe)
                    logger.debug(f"Skipping duplicate article: {article.url}")
                    continue
                except Exception as e:
                    logger.error(f"Error inserting article {article.url}: {e}")
                    continue

            conn.commit()

        return inserted

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

    def get_all_tags(self, search: Optional[str] = None) -> List[dict]:
        """
        Get ALL unique tags with article counts.

        Args:
            search: Optional search term to filter tags

        Returns:
            List of dicts: [{"tag": "tagname", "theme": "Tag Name", "count": N}, ...]
        """
        # Build search filter if specified
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
                    -- Exclude source names (media outlets)
                    AND tag NOT IN ('g1', 'globo', 'folha', 'uol', 'estadao', 'cnn', 'bbc',
                                    'r7', 'terra', 'ig', 'globoesporte', 'tecmundo', 'infomoney',
                                    'noticias', 'noticia', 'news')
                    -- Exclude domain-like tags
                    AND tag NOT LIKE '%%.com'
                    AND tag NOT LIKE '%%.com.br'
                    AND tag NOT LIKE '%%.br'
                    AND tag NOT LIKE '%%.net'
                    AND tag NOT LIKE '%%.org'
                    {search_filter}
                GROUP BY tag
            )
            SELECT tag, article_count
            FROM TagCounts
            ORDER BY article_count DESC, tag ASC
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params if params else None)
            rows = cursor.fetchall()

            # Format theme as Title Case
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

    # ========================================
    # USER ARTICLES
    # ========================================

    def get_user_articles(
        self,
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
                   created_at, updated_at, published_at, deleted_at
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

    def get_user_article_by_id(self, article_id: UUID) -> Optional[UserArticle]:
        """Retorna um artigo de usuario especifico pelo ID."""
        query = """
            SELECT id, title, linha_fina, content, preview, status, category,
                   tags, source_article_ids, generation_config, author_name,
                   created_at, updated_at, published_at, deleted_at
            FROM user_articles
            WHERE id = %s AND deleted_at IS NULL
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(article_id),))
            row = cursor.fetchone()
            return self._row_to_user_article(row) if row else None

    def create_user_article(self, article: UserArticleCreate) -> UserArticle:
        """
        Cria um novo artigo de usuario.

        Args:
            article: Dados do artigo a criar

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
            (title, linha_fina, content, preview, status, category,
             tags, source_article_ids, generation_config, author_name)
            OUTPUT INSERTED.id, INSERTED.created_at, INSERTED.updated_at
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        tags_json = json.dumps(article.tags) if article.tags else '[]'
        source_ids_json = json.dumps(article.source_article_ids) if article.source_article_ids else '[]'
        config_json = json.dumps(article.generation_config) if article.generation_config else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                article.title,
                article.linha_fina,
                article.content,
                preview,
                article.status,
                article.category,
                tags_json,
                source_ids_json,
                config_json,
                article.author_name
            ))
            row = cursor.fetchone()
            conn.commit()

            return UserArticle(
                id=row[0],
                title=article.title,
                linha_fina=article.linha_fina,
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
        self, article_id: UUID, data: UserArticleUpdate
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
            return self.get_user_article_by_id(article_id)

        updates.append("updated_at = GETUTCDATE()")
        params.append(str(article_id))

        query = f"""
            UPDATE user_articles
            SET {', '.join(updates)}
            WHERE id = %s AND deleted_at IS NULL
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            affected = cursor.rowcount
            conn.commit()

            if affected == 0:
                return None

        return self.get_user_article_by_id(article_id)

    def delete_user_article(self, article_id: UUID) -> bool:
        """
        Soft delete de um artigo de usuario.

        Args:
            article_id: ID do artigo

        Returns:
            True se deletado, False se nao encontrado
        """
        query = """
            UPDATE user_articles
            SET deleted_at = GETUTCDATE(), updated_at = GETUTCDATE()
            WHERE id = %s AND deleted_at IS NULL
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (str(article_id),))
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
            deleted_at=row[14]
        )


# Singleton para uso global
_db_service: Optional[DatabaseService] = None

def get_db() -> DatabaseService:
    """Retorna instancia singleton do DatabaseService."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
