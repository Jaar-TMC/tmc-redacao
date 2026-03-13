"""Embedding repository - operations for article embeddings."""

import json
import logging
from typing import List, Optional
from uuid import UUID

from .base import BaseRepository

# Type alias for embedding vectors
EmbeddingVector = List[float]

logger = logging.getLogger(__name__)


class EmbeddingRepository(BaseRepository):
    """Repository for article embedding storage and retrieval."""

    def save_article_embedding(
        self,
        article_id: UUID,
        embedding: EmbeddingVector,
        model_version: str = 'text-embedding-3-small'
    ) -> bool:
        """Salva ou atualiza o embedding de um artigo.

        Args:
            article_id: ID do artigo
            embedding: Vetor de embedding (lista de floats)
            model_version: Versao do modelo usado para gerar o embedding

        Returns:
            True se salvo com sucesso, False caso contrario
        """
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

    def save_article_embeddings_batch(
        self,
        article_ids: List,
        embeddings: List,
        model_version: str = 'text-embedding-3-small'
    ) -> int:
        """Save multiple embeddings in a single connection and transaction.

        Uses MERGE to handle both inserts and updates. Also marks articles
        as having embeddings in the same transaction.

        Args:
            article_ids: List of article UUIDs
            embeddings: List of embedding vectors (parallel to article_ids)
            model_version: Model version string

        Returns:
            Number of embeddings saved successfully
        """
        if not article_ids or not embeddings:
            return 0

        merge_query = """
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

        mark_query = """
            UPDATE collected_articles
            SET has_embedding = 1
            WHERE id = %s AND (has_embedding = 0 OR has_embedding IS NULL)
        """

        # Pre-serialize all embeddings outside the connection
        prepared = []
        for article_id, embedding in zip(article_ids, embeddings):
            embedding_json = json.dumps(embedding)
            aid = str(article_id)
            prepared.append((aid, embedding_json, model_version))

        saved = 0
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                for aid, embedding_json, mv in prepared:
                    try:
                        cursor.execute(merge_query, (
                            aid, embedding_json, mv,
                            aid, embedding_json, mv
                        ))
                        cursor.execute(mark_query, (aid,))
                        saved += 1
                    except Exception as e:
                        logger.error(f"Error saving embedding for article {aid}: {e}")
                        continue

                conn.commit()

        except Exception as e:
            logger.error(f"Batch embedding save connection error: {e}")
            raise

        logger.info(f"Batch saved {saved}/{len(article_ids)} embeddings")
        return saved

    def get_article_embedding(self, article_id: UUID) -> Optional[dict]:
        """Retorna o embedding de um artigo.

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
        """Retorna artigos que ainda nao possuem embedding.

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
        """Marca que um artigo possui embedding (atualiza has_embedding flag).

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
