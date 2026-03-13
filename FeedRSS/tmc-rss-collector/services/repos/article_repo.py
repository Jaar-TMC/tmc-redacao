"""Article repository -- collected articles, user articles, tags, categories, and collection logs."""

import json
import logging
import pymssql
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from models import (
    Article, ArticleCreate,
    CollectionLog, CollectionLogCreate,
    UserArticle, UserArticleCreate, UserArticleUpdate,
)
from .base import BaseRepository, _execute

logger = logging.getLogger(__name__)


class ArticleRepository(BaseRepository):
    """Repository for article CRUD, user articles, tags, categories, and collection logs."""

    # ========================================
    # ARTICLE FILTERS (shared)
    # ========================================

    def _build_article_filters(self,
                               category=None,
                               source_id=None,
                               period=None,
                               search=None,
                               tag=None,
                               classification=None):
        """Build shared WHERE clause and params for article queries.

        Returns:
            Tuple (where_clause, params, needs_scores_join)
        """
        conditions = []
        params = []
        needs_scores_join = False

        if classification and classification in ('A', 'B', 'C'):
            conditions.append("a.classification = %s")
            params.append(classification)

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
            search_escaped = search.replace('[', '[[]').replace('%', '[%]').replace('_', '[_]')
            search_with_spaces = search_escaped.replace('-', ' ')
            search_param = "%" + search_escaped + "%"

            if search_with_spaces != search_escaped:
                search_param_spaces = "%" + search_with_spaces + "%"
                conditions.append("""(
                    a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.preview COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.preview COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                )""")
                params.extend([search_param, search_param_spaces, search_param, search_param_spaces, search_param])
            else:
                conditions.append("""(
                    a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.preview COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    OR a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                )""")
                params.extend([search_param, search_param, search_param])

        if tag:
            conditions.append("""
                a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
            """)
            tag_param = '%"' + tag + '"%'
            params.append(tag_param)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, params, needs_scores_join

    # ========================================
    # ROW MAPPERS
    # ========================================

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
            tags=row[9],
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

    def _row_to_user_article(self, row) -> UserArticle:
        """Converte uma row do cursor para UserArticle.

        SELECT column order:
          0: id, 1: title, 2: linha_fina, 3: content, 4: preview,
          5: status, 6: category, 7: tags, 8: source_article_ids,
          9: generation_config, 10: author_name, 11: created_at,
          12: updated_at, 13: published_at, 14: deleted_at,
          15: titulo_curto, 16: resumo
        """
        return UserArticle(
            id=row[0],
            title=row[1],
            linha_fina=row[2],
            content=row[3],
            preview=row[4],
            status=row[5],
            category=row[6],
            tags=row[7],
            source_article_ids=row[8],
            generation_config=row[9],
            author_name=row[10],
            created_at=row[11],
            updated_at=row[12],
            published_at=row[13],
            deleted_at=row[14],
            titulo_curto=row[15] if len(row) > 15 else None,
            resumo=row[16] if len(row) > 16 else [],
        )

    # ========================================
    # COLLECTED ARTICLES
    # ========================================

    def get_articles(self, page=1, limit=20,
                     category=None, source_id=None,
                     period=None, search=None,
                     tag=None, classification=None):
        """Lista artigos com filtros e paginacao."""
        limit = min(limit, 100)
        offset = (page - 1) * limit

        where_clause, params, _needs = self._build_article_filters(
            category=category, source_id=source_id, period=period,
            search=search, tag=tag, classification=classification
        )

        query = (
            "SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,"
            " a.image_url, a.author, a.category, a.tags, a.published_at,"
            " a.collected_at, a.hash,"
            " s.name as source_name, s.url as source_url, s.favicon_url,"
            " COUNT(*) OVER() as total_count"
            " FROM collected_articles a"
            " JOIN sources s ON a.source_id = s.id"
            " " + where_clause +
            " ORDER BY a.published_at DESC"
            " OFFSET %s ROWS FETCH NEXT %s ROWS ONLY"
        )

        logger.info("[get_articles] search=%s, where_clause=%s", search, where_clause)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params) + (offset, limit))
            rows = cursor.fetchall()
            total = rows[0][-1] if rows else 0
            logger.info("[get_articles] total=%s, rows=%s", total, len(rows))
            articles = [self._row_to_article(row[:-1]) for row in rows]

        return articles, total

    def get_articles_with_urgency(self, page=1, limit=20,
                                   category=None, source_id=None,
                                   period=None, search=None,
                                   tag=None, classification=None,
                                   order_by=None):
        """Combined query: articles + count + urgency counts in a single DB connection."""
        limit = min(limit, 100)
        offset = (page - 1) * limit

        where_clause, params, _needs = self._build_article_filters(
            category=category, source_id=source_id, period=period,
            search=search, tag=tag, classification=classification
        )

        urgency_where, urgency_params, _urgency_needs = self._build_article_filters(
            category=category, source_id=source_id, period=None,
            search=search, tag=tag, classification=classification
        )

        logger.info("[get_articles_with_urgency] search=%s, order_by=%s", search, order_by)

        if order_by == 'score':
            order_clause = "ORDER BY ISNULL(a.total_score, -1) DESC, a.published_at DESC"
        else:
            order_clause = "ORDER BY a.published_at DESC"

        fallback_order_clause = "ORDER BY a.published_at DESC"

        select_cols = (
            "SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,"
            " a.image_url, a.author, a.category, a.tags, a.published_at,"
            " a.collected_at, a.hash,"
            " s.name as source_name, s.url as source_url, s.favicon_url,"
            " a.total_score, a.classification,"
            " sc.score_inesperado, sc.score_impacto, sc.score_busca_agora, sc.score_conversa,"
            " COUNT(*) OVER() as total_count"
            " FROM collected_articles a"
            " JOIN sources s ON a.source_id = s.id"
            " LEFT JOIN article_scores sc ON sc.article_id = a.id"
            " " + where_clause
        )

        query = select_cols + " " + order_clause + " OFFSET %s ROWS FETCH NEXT %s ROWS ONLY"

        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                _execute(cursor, query, tuple(params) + (offset, limit))
                rows = cursor.fetchall()
            except Exception as e:
                logger.error("[get_articles_with_urgency] Query failed (order_by=%s): %s", order_by, e)
                if order_by == 'score':
                    logger.warning("[get_articles_with_urgency] Falling back to date ordering")
                    try:
                        fallback_query = select_cols + " " + fallback_order_clause + " OFFSET %s ROWS FETCH NEXT %s ROWS ONLY"
                        _execute(cursor, fallback_query, tuple(params) + (offset, limit))
                        rows = cursor.fetchall()
                    except Exception as fallback_err:
                        logger.error("[get_articles_with_urgency] Fallback also failed: %s", fallback_err)
                        raise e
                else:
                    raise

            total = rows[0][-1] if rows else 0
            articles = [self._row_to_article(row[:-1]) for row in rows]

            urgency_query = (
                "SELECT"
                " SUM(CASE WHEN a.published_at >= DATEADD(hour, -1, GETUTCDATE()) THEN 1 ELSE 0 END),"
                " SUM(CASE WHEN a.published_at >= DATEADD(hour, -3, GETUTCDATE()) THEN 1 ELSE 0 END),"
                " SUM(CASE WHEN a.published_at >= DATEADD(hour, -8, GETUTCDATE()) THEN 1 ELSE 0 END),"
                " COUNT(*)"
                " FROM collected_articles a"
                " JOIN sources s ON a.source_id = s.id"
                " " + urgency_where
            )
            _execute(cursor, urgency_query, tuple(urgency_params))
            urow = cursor.fetchone()

            urgency_counts = {
                "now": urow[0] or 0,
                "recent": urow[1] or 0,
                "today": urow[2] or 0,
                "all": urow[3] or 0
            } if urow else {"now": 0, "recent": 0, "today": 0, "all": 0}

            logger.info("[get_articles_with_urgency] total=%s, rows=%s, urgency=%s",
                        total, len(rows), urgency_counts)

        return articles, total, urgency_counts

    def get_urgency_counts(self, category=None, source_id=None,
                           search=None, tag=None):
        """Returns article counts per urgency cluster."""
        urgency_where, urgency_params, urgency_needs_scores = self._build_article_filters(
            category=category, source_id=source_id, period=None,
            search=search, tag=tag
        )

        scores_join = " LEFT JOIN article_scores sc ON sc.article_id = a.id" if urgency_needs_scores else ""

        query = (
            "SELECT"
            " SUM(CASE WHEN a.published_at >= DATEADD(hour, -1, GETUTCDATE()) THEN 1 ELSE 0 END) as now_count,"
            " SUM(CASE WHEN a.published_at >= DATEADD(hour, -3, GETUTCDATE()) THEN 1 ELSE 0 END) as recent_count,"
            " SUM(CASE WHEN a.published_at >= DATEADD(hour, -8, GETUTCDATE()) THEN 1 ELSE 0 END) as today_count,"
            " COUNT(*) as all_count"
            " FROM collected_articles a"
            " JOIN sources s ON a.source_id = s.id"
            + scores_join + " " + urgency_where
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, urgency_params)
            row = cursor.fetchone()

            if row:
                return {
                    "now": row[0] or 0,
                    "recent": row[1] or 0,
                    "today": row[2] or 0,
                    "all": row[3] or 0
                }
            return {"now": 0, "recent": 0, "today": 0, "all": 0}

    def get_article_by_id(self, article_id):
        """Retorna um artigo especifico pelo ID."""
        query = """
            SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,
                   a.image_url, a.author, a.category, a.tags, a.published_at,
                   a.collected_at, a.hash,
                   s.name as source_name, s.url as source_url, s.favicon_url,
                   a.total_score, a.classification,
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

    def check_existing_hashes(self, hashes):
        """Verifica quais hashes ja existem no banco."""
        if not hashes:
            return set()

        existing = set()
        BATCH_SIZE = 1000

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for i in range(0, len(hashes), BATCH_SIZE):
                batch = hashes[i:i + BATCH_SIZE]
                placeholders = ','.join(['%s'] * len(batch))
                query = "SELECT hash FROM collected_articles WHERE hash IN (" + placeholders + ")"
                _execute(cursor, query, tuple(batch))
                existing.update(row[0] for row in cursor.fetchall())

        return existing

    def get_recent_titles(self, hours=24):
        """Retorna titulos de artigos recentes para deduplicacao por similaridade."""
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

    def insert_articles(self, articles):
        """Insere multiplos artigos (batch insert)."""
        result = self.insert_articles_returning(articles)
        return result[0]

    def insert_articles_returning(self, articles):
        """Insere multiplos artigos e retorna dados dos inseridos."""
        if not articles:
            return 0, []

        query = """
            INSERT INTO collected_articles
            (source_id, title, content, preview, url, image_url, author,
             category, tags, published_at, collected_at, hash)
            OUTPUT INSERTED.id, INSERTED.title, INSERTED.content, INSERTED.category
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        prepared = []
        for article in articles:
            tags_json = json.dumps(article.tags) if article.tags else '[]'
            prepared.append((
                str(article.source_id),
                article.title, article.content, article.preview,
                article.url, article.image_url, article.author,
                article.category, tags_json,
                article.published_at, article.collected_at, article.hash
            ))

        inserted = 0
        inserted_articles = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for i, params in enumerate(prepared):
                try:
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    if row:
                        inserted_articles.append({
                            'id': row[0],
                            'title': row[1],
                            'content': row[2] or '',
                            'category': row[3] or ''
                        })
                    inserted += 1
                except pymssql.IntegrityError:
                    logger.debug("Skipping duplicate article: %s", articles[i].url)
                    continue
                except Exception as e:
                    logger.error("Error inserting article %s: %s", articles[i].url, e)
                    continue
            conn.commit()

        return inserted, inserted_articles

    def delete_old_articles(self, hours=24):
        """Delete articles older than specified hours."""
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
            logger.info("Deleted %s articles older than %s hours", deleted, hours)
        return deleted

    def delete_duplicate_articles_by_title(self, similarity_threshold=0.85):
        """Delete duplicate articles keeping only the oldest one per similar title group."""
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
            DELETE TOP (500) FROM collected_articles
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
            logger.info("Deleted %s duplicate articles with same title", deleted)
        return deleted

    # ========================================
    # COLLECTION LOGS
    # ========================================

    def log_collection(self, source_id, status, articles_found,
                       articles_new, articles_duplicate,
                       duration_ms, error=None):
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
                duration_ms, status, articles_found,
                articles_new, articles_duplicate, error, duration_ms
            ))
            conn.commit()

    # ========================================
    # TAGS
    # ========================================

    def get_trending_tags(self, limit=20, period_hours=None):
        """Get trending tags with distinct article counts."""
        period_filter = ""
        params = []
        if period_hours:
            period_filter = "WHERE a.published_at >= DATEADD(hour, -%s, GETUTCDATE())"
            params.append(period_hours)

        query = (
            "WITH ArticleTags AS ("
            " SELECT a.id as article_id, LOWER(LTRIM(RTRIM(t.value))) as tag"
            " FROM collected_articles a CROSS APPLY OPENJSON(a.tags) t"
            " " + period_filter +
            "), TagCounts AS ("
            " SELECT tag, COUNT(DISTINCT article_id) as article_count"
            " FROM ArticleTags"
            " WHERE tag IS NOT NULL AND LEN(tag) > 2"
            " AND tag NOT IN ('g1', 'globo', 'folha', 'uol', 'estadao', 'cnn', 'bbc',"
            " 'r7', 'terra', 'ig', 'globoesporte', 'tecmundo', 'infomoney',"
            " 'noticias', 'noticia', 'news',"
            " 'cnn esportes', 'cnn brasil', 'cnn brasil money', 'cnn money',"
            " 'agencia cnn', 'agência cnn', 'cnn pop', '#cnnpop', 'cnnpop',"
            " 'cnn viagem', 'cnn soft', 'cnn series',"
            " 'folha de s.paulo', 'folha de sao paulo', 'o globo',"
            " 'valor economico', 'valor economico', 'poder360',"
            " 'metropoles', 'metropoles', 'carta capital', 'cartacapital')"
            " AND tag NOT LIKE '%%.com' AND tag NOT LIKE '%%.com.br'"
            " AND tag NOT LIKE '%%.br' AND tag NOT LIKE '%%.net' AND tag NOT LIKE '%%.org'"
            " AND tag NOT LIKE 'cnn %%' AND tag NOT LIKE '#cnn%%'"
            " GROUP BY tag"
            ") SELECT TOP %s tag, article_count FROM TagCounts ORDER BY article_count DESC"
        )
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params))
            rows = cursor.fetchall()
            return [{"tag": row[0], "count": row[1]} for row in rows]

    def get_all_tags(self, search=None, limit=100):
        """Get unique tags with article counts, ordered by popularity."""
        search_filter = ""
        params = []
        if search:
            search_filter = "AND tag LIKE %s"
            search_escaped = search.replace('[', '[[]').replace('%', '[%]').replace('_', '[_]')
            params.append("%" + search_escaped + "%")

        query = (
            "WITH ArticleTags AS ("
            " SELECT a.id as article_id, LOWER(LTRIM(RTRIM(t.value))) as tag"
            " FROM collected_articles a CROSS APPLY OPENJSON(a.tags) t"
            "), TagCounts AS ("
            " SELECT tag, COUNT(DISTINCT article_id) as article_count"
            " FROM ArticleTags"
            " WHERE tag IS NOT NULL AND LEN(tag) > 2"
            " AND tag NOT IN ('g1', 'globo', 'folha', 'uol', 'estadao', 'cnn', 'bbc',"
            " 'r7', 'terra', 'ig', 'globoesporte', 'tecmundo', 'infomoney',"
            " 'noticias', 'noticia', 'news',"
            " 'cnn esportes', 'cnn brasil', 'cnn brasil money', 'cnn money',"
            " 'agencia cnn', 'agência cnn', 'cnn pop', '#cnnpop', 'cnnpop',"
            " 'cnn viagem', 'cnn soft', 'cnn series',"
            " 'folha de s.paulo', 'folha de sao paulo', 'o globo',"
            " 'valor economico', 'valor economico', 'poder360',"
            " 'metropoles', 'metropoles', 'carta capital', 'cartacapital')"
            " AND tag NOT LIKE '%%.com' AND tag NOT LIKE '%%.com.br'"
            " AND tag NOT LIKE '%%.br' AND tag NOT LIKE '%%.net' AND tag NOT LIKE '%%.org'"
            " AND tag NOT LIKE 'cnn %%' AND tag NOT LIKE '#cnn%%'"
            " " + search_filter +
            " GROUP BY tag"
            ") SELECT TOP %s tag, article_count FROM TagCounts ORDER BY article_count DESC, tag ASC"
        )
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params))
            rows = cursor.fetchall()

            result = []
            for row in rows:
                tag_val = row[0]
                theme = ' '.join(word.capitalize() for word in tag_val.replace('-', ' ').split())
                result.append({"tag": tag_val, "theme": theme, "count": row[1]})
            return result

    def get_categories_filtered(self, search=None, tag=None,
                               source_id=None, period=None,
                               classification=None):
        """Get categories with article counts, filtered by active filters."""
        where_clause, params, needs_scores_join = self._build_article_filters(
            search=search, tag=tag, source_id=source_id, period=period,
            classification=classification
        )

        scores_join = ""
        if needs_scores_join:
            scores_join = "LEFT JOIN article_scores sc ON a.id = sc.article_id"

        extra_where = "AND" if where_clause else "WHERE"

        query = (
            "SELECT a.category, COUNT(*) as count"
            " FROM collected_articles a"
            " JOIN sources s ON a.source_id = s.id"
            " " + scores_join +
            " " + where_clause +
            " " + extra_where + " a.category IS NOT NULL"
            " GROUP BY a.category ORDER BY count DESC"
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params))
            return [{"name": row[0], "count": row[1]} for row in cursor.fetchall()]

    def get_all_tags_filtered(self, search=None, category=None,
                              source_id=None, period=None,
                              classification=None, limit=100):
        """Get tags with article counts, filtered by active filters."""
        conditions = []
        params = []

        if classification and classification in ('A', 'B', 'C'):
            conditions.append("a.classification = %s")
            params.append(classification)
        if category:
            conditions.append("a.category = %s")
            params.append(category)
        if source_id:
            conditions.append("s.name = %s")
            params.append(source_id)
        if search:
            search_escaped = search.replace('[', '[[]').replace('%', '[%]').replace('_', '[_]')
            search_param = "%" + search_escaped + "%"
            conditions.append("""(
                a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                OR a.preview COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
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

        query = (
            "WITH ArticleTags AS ("
            " SELECT a.id as article_id, LOWER(LTRIM(RTRIM(t.value))) as tag"
            " FROM collected_articles a"
            " JOIN sources s ON a.source_id = s.id"
            " CROSS APPLY OPENJSON(a.tags) t"
            " WHERE 1=1 " + where_extra +
            "), TagCounts AS ("
            " SELECT tag, COUNT(DISTINCT article_id) as article_count"
            " FROM ArticleTags"
            " WHERE tag IS NOT NULL AND LEN(tag) > 2"
            " AND tag NOT IN ('g1', 'globo', 'folha', 'uol', 'estadao', 'cnn', 'bbc',"
            " 'r7', 'terra', 'ig', 'globoesporte', 'tecmundo', 'infomoney',"
            " 'noticias', 'noticia', 'news',"
            " 'cnn esportes', 'cnn brasil', 'cnn brasil money', 'cnn money',"
            " 'agencia cnn', 'agência cnn', 'cnn pop', '#cnnpop', 'cnnpop',"
            " 'cnn viagem', 'cnn soft', 'cnn series',"
            " 'folha de s.paulo', 'folha de sao paulo', 'o globo',"
            " 'valor economico', 'valor economico', 'poder360',"
            " 'metropoles', 'metropoles', 'carta capital', 'cartacapital')"
            " AND tag NOT LIKE '%%.com' AND tag NOT LIKE '%%.com.br'"
            " AND tag NOT LIKE '%%.br' AND tag NOT LIKE '%%.net' AND tag NOT LIKE '%%.org'"
            " AND tag NOT LIKE 'cnn %%' AND tag NOT LIKE '#cnn%%'"
            " GROUP BY tag"
            ") SELECT TOP %s tag, article_count FROM TagCounts ORDER BY article_count DESC, tag ASC"
        )
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params))
            rows = cursor.fetchall()

            result = []
            for row in rows:
                tag_val = row[0]
                theme = ' '.join(word.capitalize() for word in tag_val.replace('-', ' ').split())
                result.append({"tag": tag_val, "theme": theme, "count": row[1]})
            return result

    def get_collection_stats(self):
        """Retorna estatisticas de coleta."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM collected_articles) as total_articles,
                    (SELECT COUNT(*) FROM collected_articles
                     WHERE collected_at >= DATEADD(day, -1, GETUTCDATE())) as articles_today,
                    (SELECT COUNT(*) FROM sources WHERE active = 1) as active_sources,
                    (SELECT MAX(finished_at) FROM collection_logs
                     WHERE status = 'success') as last_collection
            """)
            stats_row = cursor.fetchone()

            total_articles = stats_row[0]
            articles_today = stats_row[1]
            active_sources = stats_row[2]
            last_collection = stats_row[3]

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
    # USER ARTICLES
    # ========================================

    def get_user_articles(self, user_id=None, page=1, limit=20,
                          status=None, category=None,
                          search=None, date_range=None):
        """Lista artigos do usuario com filtros e paginacao."""
        limit = min(limit, 100)
        offset = (page - 1) * limit

        conditions = ["deleted_at IS NULL"]
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
            search_escaped = search.replace('[', '[[]').replace('%', '[%]').replace('_', '[_]')
            search_param = "%" + search_escaped + "%"
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

        query = (
            "SELECT id, title, linha_fina, content, preview, status, category,"
            " tags, source_article_ids, generation_config, author_name,"
            " created_at, updated_at, published_at, deleted_at,"
            " titulo_curto, resumo,"
            " COUNT(*) OVER() as total_count"
            " FROM user_articles"
            " " + where_clause +
            " ORDER BY updated_at DESC"
            " OFFSET %s ROWS FETCH NEXT %s ROWS ONLY"
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params) + (offset, limit))
            rows = cursor.fetchall()
            total = rows[0][-1] if rows else 0
            articles = [self._row_to_user_article(row[:-1]) for row in rows]

        return articles, total

    def get_user_article_by_id(self, article_id, user_id=None):
        """Retorna um artigo de usuario especifico pelo ID."""
        conditions = ["id = %s", "deleted_at IS NULL"]
        params = [str(article_id)]

        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)

        query = (
            "SELECT id, title, linha_fina, content, preview, status, category,"
            " tags, source_article_ids, generation_config, author_name,"
            " created_at, updated_at, published_at, deleted_at,"
            " titulo_curto, resumo"
            " FROM user_articles"
            " WHERE " + " AND ".join(conditions)
        )
        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params))
            row = cursor.fetchone()
            return self._row_to_user_article(row) if row else None

    def create_user_article(self, article, user_id=None):
        """Cria um novo artigo de usuario."""
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
                article.title, article.linha_fina, article.titulo_curto,
                resumo_json, article.content, preview,
                article.status, article.category, tags_json,
                source_ids_json, config_json, article.author_name, user_id
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

    def update_user_article(self, article_id, data, user_id=None):
        """Atualiza um artigo de usuario existente."""
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
            where_conditions = where_conditions + " AND user_id = %s"
            params.append(user_id)

        query = "UPDATE user_articles SET " + ", ".join(updates) + " WHERE " + where_conditions

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params))
            affected = cursor.rowcount
            conn.commit()

            if affected == 0:
                return None

        return self.get_user_article_by_id(article_id, user_id=user_id)

    def delete_user_article(self, article_id, user_id=None):
        """Soft delete de um artigo de usuario."""
        params = [str(article_id)]
        where = "id = %s AND deleted_at IS NULL"
        if user_id:
            where = where + " AND user_id = %s"
            params.append(user_id)

        query = "UPDATE user_articles SET deleted_at = GETUTCDATE(), updated_at = GETUTCDATE() WHERE " + where

        with self.get_connection() as conn:
            cursor = conn.cursor()
            _execute(cursor, query, tuple(params))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0
