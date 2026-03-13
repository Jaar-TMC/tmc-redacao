"""Event repository - event signature extraction and matching."""

import json
import logging
from typing import List, Optional
from uuid import UUID

from .base import BaseRepository

logger = logging.getLogger(__name__)


class EventRepository(BaseRepository):
    """Repository for event signature storage and retrieval."""

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
        """Salva ou atualiza a assinatura de evento de um artigo.

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
        """Retorna a assinatura de evento de um artigo.

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
        """Busca assinaturas com chave canonica exata ou similar.

        Args:
            canonical_key: Chave canonica para buscar
            limit: Numero maximo de resultados

        Returns:
            Lista de assinaturas ordenadas por relevancia
        """
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
        """Busca temas com chave canonica de evento.

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
        """Retorna artigos que ainda nao possuem assinatura de evento extraida.

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
        """Atualiza o tema associado a uma assinatura de evento.

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
        """Retorna todas as assinaturas de evento de um tema.

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
