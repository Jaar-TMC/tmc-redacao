"""Theme repository -- semantic theme management and article-theme relations."""

import json
import logging
from typing import List, Optional, Tuple
from uuid import UUID

from models import Article
from .base import BaseRepository, _execute

# Type alias for embedding vectors
EmbeddingVector = List[float]

logger = logging.getLogger(__name__)


class ThemeRepository(BaseRepository):
    """Repository for semantic theme CRUD and article-theme relations."""

    def create_theme(
        self,
        name: str,
        slug: str,
        centroid: Optional[EmbeddingVector] = None,
        article_count: int = 0,
        classification: Optional[dict] = None
    ) -> Optional[dict]:
        """Cria um novo tema semantico.

        Args:
            name: Nome do tema (ex: "Eleicoes 2026")
            slug: Slug URL-friendly (ex: "eleicoes-2026")
            centroid: Vetor centroide do tema (media dos embeddings)
            article_count: Contagem inicial de artigos
            classification: Metadados de classificacao

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
        """Retorna um tema pelo ID.

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
        """Retorna um tema pelo slug.

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
        """Retorna todos os temas com determinado status.

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
        """Atualiza um tema existente.

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
                _execute(cursor, query, tuple(params))
                conn.commit()

            return self.get_theme(theme_id)
        except Exception as e:
            logger.error(f"Error updating theme {theme_id}: {e}")
            return None

    def _row_to_theme(self, row) -> dict:
        """Converte uma row do cursor para dict de tema."""
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
        """Adiciona um artigo a um tema.

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
        """Retorna artigos de um tema com paginacao.

        Args:
            theme_id: ID do tema
            limit: Numero de artigos por pagina
            offset: Offset para paginacao

        Returns:
            Tuple (lista de artigos, total de artigos no tema)
        """
        query = """
            SELECT a.id, a.source_id, a.title, a.content, a.preview, a.url,
                   a.image_url, a.author, a.category, a.tags, a.published_at,
                   a.collected_at, a.hash,
                   s.name as source_name, s.url as source_url, s.favicon_url,
                   r.similarity_score, r.is_seed,
                   COUNT(*) OVER() as total_count
            FROM article_themes r
            JOIN collected_articles a ON r.article_id = a.id
            JOIN sources s ON a.source_id = s.id
            WHERE r.theme_id = %s
            ORDER BY r.similarity_score DESC, a.published_at DESC
            OFFSET %s ROWS FETCH NEXT %s ROWS ONLY
        """

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (str(theme_id), offset, limit))
                rows = cursor.fetchall()

                total = rows[0][-1] if rows else 0

                articles = []
                for row in rows:
                    article = self._row_to_article(row[:16])
                    article.similarity_score = row[16]
                    article.is_seed = bool(row[17])
                    articles.append(article)

                return articles, total
        except Exception as e:
            logger.error(f"Error getting articles for theme {theme_id}: {e}")
            return [], 0

    def get_article_themes(self, article_id: UUID) -> List[dict]:
        """Retorna os temas aos quais um artigo pertence.

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
        """Retorna artigos que ainda nao pertencem a nenhum tema.

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
        """Retorna artigos que possuem embedding mas ainda nao pertencem a nenhum tema.

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

    def add_article_to_theme_with_match_type(
        self,
        article_id: UUID,
        theme_id: UUID,
        similarity_score: float,
        match_type: str,
        is_seed: bool = False
    ) -> bool:
        """Adiciona um artigo a um tema com tipo de match.

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

    def update_theme_event_data(
        self,
        theme_id: UUID,
        canonical_event_key: Optional[str] = None,
        primary_entities: Optional[dict] = None,
        seed_article_id: Optional[UUID] = None
    ) -> bool:
        """Atualiza dados de evento de um tema.

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
                _execute(cursor, query, tuple(params))
                affected = cursor.rowcount
                conn.commit()
                return affected > 0
        except Exception as e:
            logger.error(f"Error updating theme event data: {e}")
            return False

    def _row_to_article(self, row) -> Article:
        """Converte uma row do cursor para Article (subset for theme queries)."""
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
        )
