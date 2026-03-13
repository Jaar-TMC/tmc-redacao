"""Scoring repository - operations for article editorial scores."""

import json
import logging
from typing import List, Optional
from uuid import UUID

from .base import BaseRepository

logger = logging.getLogger(__name__)


class ScoringRepository(BaseRepository):
    """Repository for article score storage and retrieval."""

    def save_article_score(
        self,
        article_id: UUID,
        signals: dict,
        scores: dict,
        classification: str,
        scored_by: str = 'system'
    ) -> bool:
        """Salva ou atualiza o score de um artigo.

        Args:
            article_id: ID do artigo
            signals: Dict com sinais extraidos
            scores: Dict com scores calculados
            classification: Classificacao final (A, B, C)
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

                # Sync denormalized score columns in collected_articles
                total_score = scores.get('total_score') if isinstance(scores, dict) else None
                try:
                    cursor.execute(
                        """UPDATE collected_articles
                           SET total_score = %s, classification = %s
                           WHERE id = %s""",
                        (total_score, classification, str(article_id))
                    )
                except Exception as e:
                    logger.warning(f"Failed to sync denormalized score for {article_id}: {e}")

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving score for article {article_id}: {e}")
            return False

    def get_article_score(self, article_id: UUID) -> Optional[dict]:
        """Retorna o score de um artigo.

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
        """Retorna artigos que ainda nao possuem score.

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
        """Marca que um artigo possui score (atualiza has_score flag).

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
        """Retorna todos os scores de artigos de um tema para calculo de agregados.

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
