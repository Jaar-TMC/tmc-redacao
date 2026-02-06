"""
Event Matching Service for Specific Event Clustering

Multi-stage matching algorithm to find themes that represent the SAME specific event:
1. Exact canonical key match (highest confidence)
2. Entity overlap matching (Jaccard similarity)
3. Embedding similarity (fallback)
4. LLM verification (for borderline cases)
"""

import os
import logging
from typing import Optional, Tuple, Dict, Any, List
from uuid import UUID
from datetime import datetime

import numpy as np

from models.event_signature import (
    EventSignature, EventSignatureCreate, normalize_entity,
    entities_match, calculate_entity_similarity
)
from services.clustering_service import cosine_similarity

logger = logging.getLogger(__name__)

# Configuration
EVENT_MATCHING_ENABLED = os.environ.get("EVENT_MATCHING_ENABLED", "true").lower() == "true"

# Thresholds
EXACT_MATCH_CONFIDENCE = 0.98
ENTITY_MATCH_HIGH_THRESHOLD = 0.70  # High confidence entity match
ENTITY_MATCH_LOW_THRESHOLD = 0.50   # Requires LLM verification
EMBEDDING_SIMILARITY_THRESHOLD = 0.55
EMBEDDING_SANITY_CHECK_THRESHOLD = 0.50


class EventMatchingService:
    """
    Service for matching articles to existing themes based on event signatures.

    Algorithm:
    1. STAGE 1: Exact canonical key match (confidence: 0.98)
       - Fast lookup using normalized key
       - If match found, high confidence same event

    2. STAGE 2: Entity overlap matching (confidence: 0.70-0.90)
       - Calculate Jaccard similarity of entities
       - If overlap >= 70%, likely same event
       - If overlap >= 50%, needs verification

    3. STAGE 3: Embedding similarity (confidence: 0.55-0.70)
       - Cosine similarity with theme centroid
       - Used as sanity check and fallback

    4. STAGE 4: LLM verification (for borderline cases)
       - Asks LLM if two articles describe the same event
       - Used when entity overlap is 50-70%
    """

    def __init__(self, db_service=None, llm_verification_service=None):
        """
        Initialize the event matching service.

        Args:
            db_service: DatabaseService for persistence
            llm_verification_service: LLMVerificationService for borderline cases
        """
        self.db = db_service
        self.llm_verifier = llm_verification_service

        # Cache for theme signatures (theme_id -> signature data)
        self._theme_signature_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_loaded = False

        logger.info(
            f"EventMatchingService initialized: enabled={EVENT_MATCHING_ENABLED}"
        )

    def _load_theme_cache(self) -> None:
        """Load active themes with event signatures into cache."""
        if self.db is None:
            logger.warning("No database service, cache not loaded")
            return

        try:
            # Get all active themes with event data
            themes = self.db.get_all_themes(status='active')

            self._theme_signature_cache = {}
            for theme in themes:
                if theme.get('canonical_event_key') or theme.get('centroid'):
                    self._theme_signature_cache[str(theme['id'])] = {
                        'id': theme['id'],
                        'name': theme['name'],
                        'canonical_event_key': theme.get('canonical_event_key'),
                        'primary_entities': theme.get('primary_entities') or {},
                        'centroid': theme.get('centroid'),
                        'article_count': theme.get('article_count', 0),
                        'seed_article_id': theme.get('seed_article_id')
                    }

            self._cache_loaded = True
            logger.info(f"Loaded {len(self._theme_signature_cache)} themes into event matching cache")

        except Exception as e:
            logger.error(f"Failed to load theme cache: {e}")
            self._theme_signature_cache = {}

    def invalidate_cache(self) -> None:
        """Invalidate the theme cache."""
        self._theme_signature_cache = {}
        self._cache_loaded = False
        logger.debug("Event matching cache invalidated")

    async def find_matching_theme(
        self,
        article: Dict[str, Any],
        signature: EventSignatureCreate,
        embedding: Optional[List[float]] = None
    ) -> Optional[Tuple[UUID, str, float]]:
        """
        Find a theme that matches the given event signature.

        Multi-stage matching:
        1. Exact canonical key match
        2. Entity overlap (Jaccard)
        3. Embedding similarity (if available)
        4. LLM verification (for borderline cases)

        Args:
            article: Article data dict with id, title, preview
            signature: EventSignatureCreate with extracted event data
            embedding: Optional article embedding vector

        Returns:
            Tuple of (theme_id, match_type, confidence) or None if no match
            match_type: "exact" | "entity" | "verified" | "embedding"
        """
        if not EVENT_MATCHING_ENABLED:
            return None

        if not self._cache_loaded:
            self._load_theme_cache()

        if not self._theme_signature_cache:
            logger.debug("No themes in cache")
            return None

        canonical_key = signature.canonical_key

        # STAGE 1: Exact canonical key match
        if canonical_key:
            for theme_id, theme_data in self._theme_signature_cache.items():
                if theme_data.get('canonical_event_key') == canonical_key:
                    logger.info(
                        f"Exact canonical key match: {canonical_key} -> theme {theme_id}"
                    )
                    return (UUID(theme_id), "exact", EXACT_MATCH_CONFIDENCE)

            # Also check database for exact match
            if self.db:
                db_matches = self.db.find_themes_by_canonical_key(canonical_key)
                if db_matches:
                    match = db_matches[0]
                    logger.info(f"Exact DB match: {canonical_key} -> theme {match['id']}")
                    return (match['id'], "exact", EXACT_MATCH_CONFIDENCE)

        # STAGE 2: Entity overlap matching
        entity_candidates = self._find_entity_candidates(signature)

        for candidate in entity_candidates:
            entity_score = self._calculate_entity_overlap(signature, candidate)

            # High confidence entity match (>= 70%)
            if entity_score >= ENTITY_MATCH_HIGH_THRESHOLD:
                # Sanity check with embedding if available
                if embedding and candidate.get('centroid'):
                    emb_sim = cosine_similarity(embedding, candidate['centroid'])
                    if emb_sim >= EMBEDDING_SANITY_CHECK_THRESHOLD:
                        logger.info(
                            f"High entity overlap ({entity_score:.2f}) with embedding check "
                            f"({emb_sim:.2f}) -> theme {candidate['id']}"
                        )
                        return (candidate['id'], "entity", entity_score)
                    else:
                        logger.debug(
                            f"Entity match rejected: embedding too low ({emb_sim:.2f})"
                        )
                else:
                    # No embedding, trust entity match
                    logger.info(
                        f"High entity overlap ({entity_score:.2f}) -> theme {candidate['id']}"
                    )
                    return (candidate['id'], "entity", entity_score)

            # Medium confidence (50-70%) - needs LLM verification
            elif entity_score >= ENTITY_MATCH_LOW_THRESHOLD:
                if embedding and candidate.get('centroid'):
                    emb_sim = cosine_similarity(embedding, candidate['centroid'])
                    if emb_sim >= EMBEDDING_SIMILARITY_THRESHOLD:
                        # STAGE 4: LLM verification for borderline cases
                        if self.llm_verifier and candidate.get('seed_article_id'):
                            is_same = await self._verify_same_event(
                                article, candidate
                            )
                            if is_same:
                                logger.info(
                                    f"LLM verified same event -> theme {candidate['id']}"
                                )
                                return (candidate['id'], "verified", 0.85)
                        else:
                            # No verifier, use combined score
                            combined = (entity_score + emb_sim) / 2
                            if combined >= 0.60:
                                logger.info(
                                    f"Combined match ({combined:.2f}) -> theme {candidate['id']}"
                                )
                                return (candidate['id'], "entity", combined)

        # STAGE 3: Pure embedding fallback (only if no entity match)
        if embedding:
            best_emb_match = self._find_best_embedding_match(embedding)
            if best_emb_match:
                theme_id, similarity = best_emb_match
                if similarity >= EMBEDDING_SIMILARITY_THRESHOLD:
                    logger.info(
                        f"Embedding fallback match ({similarity:.2f}) -> theme {theme_id}"
                    )
                    return (theme_id, "embedding", similarity)

        # No match found
        return None

    def _find_entity_candidates(
        self,
        signature: EventSignatureCreate
    ) -> List[Dict[str, Any]]:
        """
        Find theme candidates with overlapping entities.

        Args:
            signature: Event signature to match

        Returns:
            List of candidate themes with entity data
        """
        candidates = []
        sig_entities = self._get_normalized_entities(signature)

        if not sig_entities:
            return candidates

        for theme_id, theme_data in self._theme_signature_cache.items():
            primary_entities = theme_data.get('primary_entities') or {}

            # Get theme entities
            theme_entities = set()
            for entity_type in ['people', 'organizations', 'locations']:
                entities = primary_entities.get(entity_type, [])
                if entities:
                    theme_entities.update(normalize_entity(e) for e in entities)

            # Check for any overlap
            if sig_entities & theme_entities:
                candidates.append({
                    'id': UUID(theme_id),
                    'name': theme_data['name'],
                    'canonical_event_key': theme_data.get('canonical_event_key'),
                    'primary_entities': primary_entities,
                    'centroid': theme_data.get('centroid'),
                    'seed_article_id': theme_data.get('seed_article_id'),
                    'entity_set': theme_entities,
                    'event_action': primary_entities.get('event_action')
                })

        # Sort by entity overlap (descending)
        candidates.sort(
            key=lambda c: len(sig_entities & c['entity_set']),
            reverse=True
        )

        return candidates[:10]  # Top 10 candidates

    def _get_normalized_entities(
        self,
        signature: EventSignatureCreate
    ) -> set:
        """Get normalized entity set from signature."""
        entities = set()
        for person in (signature.people or []):
            entities.add(normalize_entity(person))
        for org in (signature.organizations or []):
            entities.add(normalize_entity(org))
        for loc in (signature.locations or []):
            entities.add(normalize_entity(loc))
        return entities

    def _calculate_entity_overlap(
        self,
        signature: EventSignatureCreate,
        candidate: Dict[str, Any]
    ) -> float:
        """
        Calculate entity overlap score using intelligent matching.

        Uses smart matching that considers:
        - Synonyms (EUA = Estados Unidos)
        - Partial matches (Trump = Donald Trump)
        - Similar actions (detido = preso)

        Args:
            signature: Event signature to match
            candidate: Candidate theme data

        Returns:
            Overlap score between 0 and 1
        """
        sig_entities = self._get_normalized_entities(signature)
        theme_entities = candidate.get('entity_set', set())

        if not sig_entities or not theme_entities:
            return 0.0

        # Use intelligent similarity calculation
        similarity = calculate_entity_similarity(sig_entities, theme_entities)

        # Bonus if action matches or is similar
        sig_action = normalize_entity(signature.event_action) if signature.event_action else ""
        theme_action = normalize_entity(candidate.get('event_action', ''))

        if sig_action and theme_action:
            if sig_action == theme_action:
                similarity = min(1.0, similarity + 0.15)
            elif entities_match(sig_action, theme_action):
                similarity = min(1.0, similarity + 0.10)

        return similarity

    async def _verify_same_event(
        self,
        article: Dict[str, Any],
        candidate: Dict[str, Any]
    ) -> bool:
        """
        Use LLM to verify if article describes the same event as the theme.

        Args:
            article: New article data
            candidate: Candidate theme data with seed article

        Returns:
            True if LLM confirms same event
        """
        if not self.llm_verifier:
            return False

        seed_article_id = candidate.get('seed_article_id')
        if not seed_article_id or not self.db:
            return False

        try:
            # Get seed article
            seed_article = self.db.get_article_by_id(seed_article_id)
            if not seed_article:
                return False

            # Call LLM verifier
            result = await self.llm_verifier.verify_same_event(
                article1={
                    'title': article.get('title', ''),
                    'preview': article.get('preview', '')
                },
                article2={
                    'title': seed_article.title,
                    'preview': seed_article.preview
                }
            )

            return result.get('is_same_event', False)

        except Exception as e:
            logger.error(f"Error in LLM verification: {e}")
            return False

    def _find_best_embedding_match(
        self,
        embedding: List[float]
    ) -> Optional[Tuple[UUID, float]]:
        """
        Find best theme match by embedding similarity.

        Args:
            embedding: Article embedding vector

        Returns:
            Tuple of (theme_id, similarity) or None
        """
        best_theme_id = None
        best_similarity = 0.0

        for theme_id, theme_data in self._theme_signature_cache.items():
            centroid = theme_data.get('centroid')
            if centroid is None:
                continue

            try:
                similarity = cosine_similarity(embedding, centroid)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_theme_id = UUID(theme_id)
            except Exception as e:
                logger.warning(f"Error calculating similarity for theme {theme_id}: {e}")
                continue

        if best_theme_id and best_similarity >= EMBEDDING_SIMILARITY_THRESHOLD:
            return (best_theme_id, best_similarity)

        return None

    def update_theme_signature_cache(
        self,
        theme_id: UUID,
        canonical_event_key: str,
        primary_entities: Dict[str, Any],
        centroid: Optional[List[float]] = None
    ) -> None:
        """
        Update the cache with new theme signature data.

        Args:
            theme_id: Theme UUID
            canonical_event_key: Canonical key for the event
            primary_entities: Dict with people, organizations, locations
            centroid: Optional embedding centroid
        """
        theme_key = str(theme_id)

        if theme_key in self._theme_signature_cache:
            self._theme_signature_cache[theme_key].update({
                'canonical_event_key': canonical_event_key,
                'primary_entities': primary_entities
            })
            if centroid:
                self._theme_signature_cache[theme_key]['centroid'] = centroid
        else:
            self._theme_signature_cache[theme_key] = {
                'id': theme_id,
                'canonical_event_key': canonical_event_key,
                'primary_entities': primary_entities,
                'centroid': centroid,
                'article_count': 1
            }

        logger.debug(f"Updated theme signature cache for {theme_id}")


# Singleton instance
_event_matching_service: Optional[EventMatchingService] = None


def get_event_matching_service(
    db_service=None,
    llm_verification_service=None
) -> EventMatchingService:
    """
    Get or create the event matching service singleton.

    Args:
        db_service: Optional DatabaseService to inject
        llm_verification_service: Optional LLMVerificationService to inject

    Returns:
        EventMatchingService instance
    """
    global _event_matching_service

    if _event_matching_service is None:
        _event_matching_service = EventMatchingService(db_service, llm_verification_service)
    else:
        if db_service is not None and _event_matching_service.db is None:
            _event_matching_service.db = db_service
        if llm_verification_service is not None and _event_matching_service.llm_verifier is None:
            _event_matching_service.llm_verifier = llm_verification_service

    return _event_matching_service


def is_event_matching_enabled() -> bool:
    """Check if event matching is enabled."""
    return EVENT_MATCHING_ENABLED
