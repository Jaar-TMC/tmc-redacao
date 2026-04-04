"""
Clustering Service for Semantic Theme Management

Handles article clustering into semantic themes based on embedding similarity.
Uses cosine similarity with exponential moving average for centroid updates.
"""

import os
import re
import json
import logging
import asyncio
import math
import threading
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4

from models.theme import Theme, ThemeCreate
from services.config import get_config
from services.async_db import run_db
from services.llm_service import LLMService, is_llm_configured

logger = logging.getLogger(__name__)

# Configuration from environment
CLUSTERING_ENABLED = os.environ.get("CLUSTERING_ENABLED", "true").lower() == "true"
# Threshold reduzido de 0.58 para 0.50: menos fragmentacao, melhor agrupamento semantico
CLUSTERING_SIMILARITY_THRESHOLD = float(os.environ.get("CLUSTERING_SIMILARITY_THRESHOLD", "0.50"))
# EMA alpha reduzido de 0.25 para 0.15: centroid mais estavel, menos drift semantico
CLUSTERING_EMA_ALPHA = float(os.environ.get("CLUSTERING_EMA_ALPHA", "0.15"))
CLUSTERING_MERGE_THRESHOLD = float(os.environ.get("CLUSTERING_MERGE_THRESHOLD", "0.90"))
CLUSTERING_BATCH_SIZE = int(os.environ.get("CLUSTERING_BATCH_SIZE", "100"))

# Scoring weights for COMPOSITE strategy
SCORE_MAX_WEIGHT = 0.7
SCORE_AVG_WEIGHT = 0.3
VOLUME_BONUS_MAX = 20
VOLUME_BONUS_PER_ARTICLE = 5

# Temporal boost settings
# Temporal 48h: eventos noticiosos frequentemente se estendem por 2 dias
TEMPORAL_BOOST_HOURS = 48  # Window for temporal boost
TEMPORAL_BOOST_AMOUNT = 0.05  # 5% boost

# Embedding dimension (OpenAI text-embedding-3-small)
EMBEDDING_DIMENSION = 1536


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector (1536 dimensions)
        vec2: Second embedding vector (1536 dimensions)

    Returns:
        Cosine similarity score between 0 and 1

    Raises:
        ValueError: If vectors have different dimensions
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions do not match: {len(vec1)} vs {len(vec2)}")

    # Pure-Python computation (avoids numpy import-time penalty)
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))

    # Handle zero vectors
    if norm_a == 0 or norm_b == 0:
        return 0.0

    similarity = dot / (norm_a * norm_b)

    # Clamp to [0, 1] range (can exceed due to floating point)
    return float(max(0.0, min(1.0, similarity)))


def normalize_vector(vec: List[float]) -> List[float]:
    """
    Normalize a vector to unit length.

    Args:
        vec: Input vector

    Returns:
        Normalized vector with unit length
    """
    norm = math.sqrt(sum(x * x for x in vec))

    if norm == 0:
        return vec

    return [x / norm for x in vec]


def generate_slug(name: str) -> str:
    """
    Generate a URL-friendly slug from a theme name.

    Args:
        name: Theme name in any language

    Returns:
        Lowercase slug with hyphens (e.g., "politica-brasileira")
    """
    # Map common Portuguese accents
    accent_map = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ú': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n'
    }

    slug = name.lower()

    # Replace accents
    for accent, replacement in accent_map.items():
        slug = slug.replace(accent, replacement)

    # Replace spaces and special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)

    # Remove leading/trailing hyphens
    slug = slug.strip('-')

    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)

    return slug[:255]  # Max length


class ClusteringService:
    """
    Service for semantic theme clustering of articles.

    Algorithm:
    1. For each article with embedding but no theme:
       - Calculate cosine similarity with existing theme centroids
       - Apply temporal boost (+5%) if article is within 48h of theme's last article
       - If similarity >= 0.50: add to existing theme
       - If similarity < 0.50: create new theme (article as seed)
    2. Update theme centroid (exponential moving average, alpha=0.15)
    3. Recalculate theme aggregate score
    """

    def __init__(self, db_service=None, llm_service: Optional[LLMService] = None):
        """
        Initialize the clustering service.

        Args:
            db_service: DatabaseService instance for persistence
            llm_service: Optional LLMService for theme naming
        """
        self.db = db_service
        self.llm = llm_service
        self.similarity_threshold = CLUSTERING_SIMILARITY_THRESHOLD
        self.ema_alpha = CLUSTERING_EMA_ALPHA
        self.merge_threshold = CLUSTERING_MERGE_THRESHOLD

        # Cache for active themes with centroids (avoid repeated DB queries)
        self._theme_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_loaded = False
        self._cache_lock = threading.Lock()

        logger.info(
            f"ClusteringService initialized: threshold={self.similarity_threshold}, "
            f"ema_alpha={self.ema_alpha}, merge_threshold={self.merge_threshold}"
        )

    def _load_theme_cache(self) -> None:
        """Load active themes with centroids into memory cache."""
        if self.db is None:
            logger.warning("No database service configured, cache not loaded")
            return

        try:
            # Use get_all_themes with status='active' instead of non-existent method
            themes = self.db.get_all_themes(status='active')
            new_cache = {
                str(theme['id']): {
                    'id': theme['id'],
                    'name': theme['name'],
                    'centroid': theme['centroid'],
                    'article_count': theme['article_count'],
                    'avg_score': theme.get('score_avg', 0),
                    'last_article_at': theme.get('updated_at')  # For temporal boost
                }
                for theme in themes
                if theme.get('centroid') is not None
            }
            with self._cache_lock:
                self._theme_cache = new_cache
                self._cache_loaded = True
            logger.info(f"Loaded {len(new_cache)} themes into cache")
        except Exception as e:
            logger.error(f"Failed to load theme cache: {e}")
            with self._cache_lock:
                self._theme_cache = {}

    def _invalidate_cache(self) -> None:
        """Invalidate the theme cache to force reload."""
        with self._cache_lock:
            self._theme_cache = {}
            self._cache_loaded = False

    def find_best_theme(
        self,
        embedding: List[float],
        exclude_theme_ids: Optional[List[UUID]] = None,
        article_published_at: Optional[datetime] = None
    ) -> Optional[Tuple[UUID, float]]:
        """
        Find the best matching theme for an embedding.

        Args:
            embedding: Article embedding vector (1536 dimensions)
            exclude_theme_ids: Optional list of theme IDs to exclude
            article_published_at: Optional publication date for temporal boost

        Returns:
            Tuple of (theme_id, similarity_score) if match found >= threshold,
            None otherwise
        """
        if not self._cache_loaded:
            self._load_theme_cache()

        if not self._theme_cache:
            logger.debug("No themes in cache, no match possible")
            return None

        exclude_set = set(str(tid) for tid in (exclude_theme_ids or []))

        best_theme_id = None
        best_similarity = 0.0

        for theme_id, theme_data in self._theme_cache.items():
            if theme_id in exclude_set:
                continue

            centroid = theme_data.get('centroid')
            if centroid is None:
                continue

            try:
                similarity = cosine_similarity(embedding, centroid)

                # Apply temporal boost if article is within 48h of theme's last article
                if article_published_at is not None:
                    last_article_at = theme_data.get('last_article_at')
                    if last_article_at is not None:
                        time_diff = abs((article_published_at - last_article_at).total_seconds())
                        if time_diff <= TEMPORAL_BOOST_HOURS * 3600:  # Within 48 hours
                            similarity = min(1.0, similarity + TEMPORAL_BOOST_AMOUNT)
                            logger.debug(
                                f"Applied temporal boost to theme {theme_id}: "
                                f"{similarity - TEMPORAL_BOOST_AMOUNT:.4f} -> {similarity:.4f}"
                            )

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_theme_id = theme_id

            except Exception as e:
                logger.warning(f"Error calculating similarity for theme {theme_id}: {e}")
                continue

        if best_similarity >= self.similarity_threshold and best_theme_id:
            logger.debug(
                f"Found best theme {best_theme_id} with similarity {best_similarity:.4f}"
            )
            return (UUID(best_theme_id), best_similarity)

        logger.debug(
            f"No theme above threshold {self.similarity_threshold}. "
            f"Best was {best_similarity:.4f}"
        )
        return None

    def create_theme(
        self,
        article: Dict[str, Any],
        embedding: List[float],
        name: Optional[str] = None
    ) -> Theme:
        """
        Create a new theme with an article as the seed.

        Args:
            article: Article data dict with id, title, content, etc.
            embedding: Article embedding to use as initial centroid
            name: Optional theme name (will generate if not provided)

        Returns:
            Created Theme object
        """
        if name is None:
            # Use article title as temporary name (will be refined by LLM later)
            name = self._generate_temporary_name(article)

        slug = generate_slug(name)
        centroid = normalize_vector(embedding)

        if self.db:
            # db.create_theme expects (name, slug, centroid, article_count, classification)
            theme_dict = self.db.create_theme(
                name=name,
                slug=slug,
                centroid=centroid,
                article_count=1
            )

            if theme_dict is None:
                raise ValueError(f"Failed to create theme '{name}'")

            # Update cache
            now = datetime.utcnow()
            with self._cache_lock:
                self._theme_cache[str(theme_dict['id'])] = {
                    'id': theme_dict['id'],
                    'name': name,
                    'centroid': centroid,
                    'article_count': 1,
                    'avg_score': 0,
                    'last_article_at': now
                }

            logger.info(f"Created new theme '{name}' (ID: {theme_dict['id']})")

            # Return Theme model object
            return Theme(
                id=theme_dict['id'],
                name=name,
                slug=slug,
                centroid=centroid,
                article_count=1,
                avg_score=0.0,
                status=theme_dict.get('status', 'active'),
                first_seen_at=theme_dict.get('created_at', now),
                last_updated_at=theme_dict.get('updated_at', now)
            )
        else:
            # Return mock theme for testing
            return Theme(
                id=uuid4(),
                name=name,
                slug=slug,
                centroid=centroid,
                article_count=1,
                avg_score=0.0,
                status='active',
                first_seen_at=datetime.utcnow(),
                last_updated_at=datetime.utcnow()
            )

    def _generate_temporary_name(self, article: Dict[str, Any]) -> str:
        """
        Generate a temporary theme name from article data.

        Prefers keeping the full title when possible, only truncating if necessary.
        Will be refined later by LLM when more articles are clustered.

        Args:
            article: Article data dict

        Returns:
            Temporary theme name (max 120 chars)
        """
        title = article.get('title', 'Unknown')

        # Remove common prefixes like dates, source names, news outlet tags
        name = re.sub(r'^[\d/\-\.]+\s*', '', title)
        name = re.sub(r'^[A-Z0-9]+:\s*', '', name)
        name = re.sub(r'^\s*\[[^\]]+\]\s*', '', name)  # Remove [TAG] prefixes
        name = re.sub(r'^\s*\([^\)]+\)\s*', '', name)  # Remove (SOURCE) prefixes
        name = name.strip()

        # If title is short enough, use it entirely
        if len(name) <= 120:
            # Just clean up trailing punctuation
            name = re.sub(r'[,;:\.\-]+$', '', name).strip()
            if name and len(name) >= 3:
                return name

        # Title is too long - need to find a good break point
        # First try natural sentence boundaries (but only if they give us substantial content)
        sentence_delimiters = [
            ('. ', 40),     # Period - only if first sentence is at least 40 chars
            ('? ', 40),     # Question mark
            ('! ', 40),     # Exclamation
        ]

        for delimiter, min_length in sentence_delimiters:
            if delimiter in name:
                first_sentence = name.split(delimiter, 1)[0] + delimiter[0]
                if len(first_sentence) >= min_length and len(first_sentence) <= 120:
                    return first_sentence

        # Try clause delimiters only if they produce complete-looking phrases
        # AND the first part is substantial relative to the whole title
        clause_delimiters = [
            (': ', 50),     # "Main Topic: details here" -> "Main Topic" (only if substantial)
            (' - ', 50),    # "Main Topic - more info" -> "Main Topic"
            (' – ', 50),    # Em-dash variant
            (' — ', 50),    # Another em-dash variant
            (' | ', 50),    # Pipe delimiter
        ]

        for delimiter, min_length in clause_delimiters:
            if delimiter in name:
                first_part = name.split(delimiter, 1)[0].strip()
                # Only use delimiter split if:
                # 1. First part is substantial (at least min_length chars)
                # 2. First part is within length limit
                # 3. First part looks grammatically complete
                # 4. First part is at least 50% of original (not just a label/intro)
                if (len(first_part) >= min_length and
                    len(first_part) <= 120 and
                    len(first_part) >= len(name) * 0.5 and
                    self._looks_complete(first_part)):
                    return first_part

        # Last resort: truncate at word boundary
        truncated = name[:117]  # Leave room for "..."
        last_space = truncated.rfind(' ')
        if last_space > 60:  # Only break at word if we keep at least 60 chars
            return truncated[:last_space] + '...'
        else:
            return truncated + '...'

    def _looks_complete(self, text: str) -> bool:
        """
        Check if text looks like a complete phrase (not truncated mid-word).

        Args:
            text: Text to check

        Returns:
            True if text appears complete
        """
        if not text:
            return False

        # Text ending with common incomplete patterns
        incomplete_patterns = [
            r'\b(da|de|do|das|dos|em|no|na|nos|nas|ao|aos|à|às|com|por|para|que|e|ou|a|o|um|uma)$',  # PT prepositions/articles
            r'\b(the|a|an|of|in|on|at|to|for|and|or|with|by)$',  # EN prepositions/articles
            r'\b[A-Z][a-z]{0,2}$',  # Truncated proper noun (e.g., "Rea" instead of "Reag")
        ]

        for pattern in incomplete_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False

        # Check if last word seems truncated (very short word after longer words)
        words = text.split()
        if len(words) >= 3:
            last_word = words[-1]
            # If last word is very short and doesn't look like a complete word
            if len(last_word) <= 3 and not last_word.lower() in [
                'lei', 'stf', 'stj', 'eua', 'onu', 'pib', 'fmi', 'fgv', 'brb',
                'pec', 'cpi', 'mp', 'go', 'sp', 'rj', 'mg', 'rs', 'pr', 'ba',
                'mil', 'bi', 'tri', 'fda', 'ice', 'ceo', 'app', 'web', 'via'
            ]:
                return False

        return True

    def add_article_to_theme(
        self,
        article_id: UUID,
        theme_id: UUID,
        similarity: float,
        embedding: List[float],
        is_seed: bool = False
    ) -> bool:
        """
        Add an article to an existing theme.

        Args:
            article_id: Article UUID
            theme_id: Theme UUID
            similarity: Cosine similarity score
            embedding: Article embedding for centroid update
            is_seed: Whether this article is a seed article for the theme

        Returns:
            True if successful, False otherwise
        """
        if self.db is None:
            logger.warning("No database service, cannot add article to theme")
            return False

        try:
            # Add article-theme relationship
            # db.add_article_to_theme expects (article_id, theme_id, similarity_score, is_seed)
            self.db.add_article_to_theme(
                article_id=article_id,
                theme_id=theme_id,
                similarity_score=similarity,
                is_seed=is_seed
            )

            # Update theme centroid with EMA
            self.update_theme_centroid(theme_id, embedding)

            logger.debug(
                f"Added article {article_id} to theme {theme_id} "
                f"(similarity={similarity:.4f}, is_seed={is_seed})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add article {article_id} to theme {theme_id}: {e}")
            return False

    def update_theme_centroid(
        self,
        theme_id: UUID,
        new_embedding: List[float]
    ) -> Optional[List[float]]:
        """
        Update theme centroid using exponential moving average.

        Formula: new_centroid = alpha * new_embedding + (1 - alpha) * old_centroid

        Args:
            theme_id: Theme UUID
            new_embedding: New embedding to incorporate

        Returns:
            Updated centroid vector, or None if failed
        """
        theme_key = str(theme_id)

        # Get current centroid from cache or DB
        if theme_key in self._theme_cache:
            current_centroid = self._theme_cache[theme_key].get('centroid')
            current_count = self._theme_cache[theme_key].get('article_count', 0)
        elif self.db:
            theme = self.db.get_theme(theme_id)  # Correct method name
            current_centroid = theme.get('centroid') if theme else None
            current_count = theme.get('article_count', 0) if theme else 0
        else:
            current_centroid = None
            current_count = 0

        if current_centroid is None:
            # First article, use embedding as centroid
            new_centroid = normalize_vector(new_embedding)
        else:
            # Apply EMA (pure Python)
            updated = [
                self.ema_alpha * n + (1 - self.ema_alpha) * o
                for o, n in zip(current_centroid, new_embedding)
            ]
            new_centroid = normalize_vector(updated)

        # Persist to database using update_theme method
        if self.db:
            new_count = current_count + 1
            self.db.update_theme(theme_id, centroid=new_centroid, article_count=new_count)

        # Update cache
        with self._cache_lock:
            if theme_key in self._theme_cache:
                self._theme_cache[theme_key]['centroid'] = new_centroid
                self._theme_cache[theme_key]['article_count'] = current_count + 1
                self._theme_cache[theme_key]['last_article_at'] = datetime.utcnow()

        logger.debug(f"Updated centroid for theme {theme_id}")
        return new_centroid

    def calculate_theme_score(self, theme_id: UUID) -> float:
        """
        Calculate aggregate score for a theme using COMPOSITE strategy.

        Formula: score = max_score * 0.7 + avg_score * 0.3 + volume_bonus
        where volume_bonus = min(20, (article_count - 1) * 5)

        Args:
            theme_id: Theme UUID

        Returns:
            Composite theme score (0-100 range, can exceed with volume bonus)
        """
        if self.db is None:
            return 0.0

        try:
            # Get article scores for this theme
            # Returns list of dicts: [{'article_id': ..., 'scores': {...}, 'classification': ...}]
            article_scores = self.db.get_theme_article_scores(theme_id)

            if not article_scores:
                return 0.0

            # Extract the 'total' or 'composite' score from each article's scores dict
            scores = []
            for article in article_scores:
                score_dict = article.get('scores', {})
                # Try different score keys that might exist
                score = score_dict.get('total') or score_dict.get('composite') or score_dict.get('relevance', 0)
                scores.append(float(score) if score else 0.0)

            if not scores:
                return 0.0

            article_count = len(scores)
            max_score = max(scores)
            avg_score = sum(scores) / article_count

            # Calculate volume bonus
            volume_bonus = min(VOLUME_BONUS_MAX, (article_count - 1) * VOLUME_BONUS_PER_ARTICLE)

            # Composite score
            composite = (
                max_score * SCORE_MAX_WEIGHT +
                avg_score * SCORE_AVG_WEIGHT +
                volume_bonus
            )

            logger.debug(
                f"Theme {theme_id} score: max={max_score}, avg={avg_score:.1f}, "
                f"volume_bonus={volume_bonus}, composite={composite:.1f}"
            )

            return round(composite, 2)

        except Exception as e:
            logger.error(f"Failed to calculate score for theme {theme_id}: {e}")
            return 0.0

    def recalculate_all_theme_scores(self) -> Dict[UUID, float]:
        """
        Recalculate scores for all active themes.

        Returns:
            Dict mapping theme_id to new score
        """
        if self.db is None:
            return {}

        results = {}
        # Use get_all_themes with status='active'
        themes = self.db.get_all_themes(status='active')

        for theme in themes:
            theme_id = theme['id']
            score = self.calculate_theme_score(theme_id)
            results[theme_id] = score

            # Update in database using update_theme method
            self.db.update_theme(theme_id, score_avg=score)

        logger.info(f"Recalculated scores for {len(results)} themes")
        return results

    async def process_pending_articles(self, limit: int = 100) -> int:
        """
        Process articles with embeddings but no theme assignment.

        NEW ALGORITHM (Event-Based Clustering):
        1. Fetch articles with embedding but no theme
        2. For each article:
           a. Extract event signature (WHO, WHERE, WHAT, WHEN)
           b. Try to match by event signature (canonical key, entity overlap)
           c. Fallback to embedding similarity
           d. If no match: create new theme with event signature
        3. Update all affected theme scores

        Args:
            limit: Maximum number of articles to process

        Returns:
            Number of articles processed
        """
        if not CLUSTERING_ENABLED:
            logger.info("Clustering is disabled")
            return 0

        if self.db is None:
            logger.error("No database service configured")
            return 0

        # Load theme cache
        await run_db(self._load_theme_cache)

        # Get pending articles
        pending = await run_db(self.db.get_articles_pending_clustering, limit=limit)

        if not pending:
            logger.info("No pending articles to cluster")
            return 0

        logger.info(f"Processing {len(pending)} articles for event-based clustering")

        processed = 0
        affected_themes: set = set()
        new_themes: List[Theme] = []

        # Import event services (lazy import to avoid circular dependencies)
        from services.event_signature_service import get_event_signature_service, is_event_extraction_enabled
        from services.event_matching_service import get_event_matching_service, is_event_matching_enabled

        event_signature_service = get_event_signature_service(self.llm) if is_event_extraction_enabled() else None
        event_matching_service = get_event_matching_service(self.db) if is_event_matching_enabled() else None

        for article in pending:
            article_id = article['id']
            embedding = article.get('embedding')
            published_at = article.get('published_at')
            title = article.get('title', '')
            preview = article.get('preview', '')

            if embedding is None:
                logger.warning(f"Article {article_id} has no embedding, skipping")
                continue

            try:
                match = None
                match_type = 'embedding'
                signature = None

                # STEP 1: Extract event signature if enabled
                if event_signature_service:
                    signature = await event_signature_service.extract(
                        title=title,
                        content=preview,
                        article_id=UUID(str(article_id))
                    )

                    if signature:
                        # Save signature to database
                        await run_db(
                            self.db.save_event_signature,
                            article_id=UUID(str(article_id)),
                            people=signature.people,
                            organizations=signature.organizations,
                            locations=signature.locations,
                            event_action=signature.event_action,
                            unique_details=signature.unique_details,
                            canonical_key=signature.canonical_key,
                            event_date=signature.event_date.isoformat() if signature.event_date else None,
                            confidence=signature.confidence
                        )

                        # STEP 2: Try event-based matching if enabled
                        if event_matching_service:
                            event_match = await event_matching_service.find_matching_theme(
                                article={'id': article_id, 'title': title, 'preview': preview},
                                signature=signature,
                                embedding=embedding
                            )

                            if event_match:
                                theme_id, match_type, confidence = event_match
                                match = (theme_id, confidence)
                                logger.info(
                                    f"Event match found for article {article_id}: "
                                    f"theme={theme_id}, type={match_type}, confidence={confidence:.2f}"
                                )

                # STEP 3: Fallback to embedding-only matching
                if match is None:
                    match = await run_db(
                        self.find_best_theme,
                        embedding,
                        article_published_at=published_at
                    )
                    if match:
                        match_type = 'embedding'

                # STEP 4: Add to existing theme or create new
                if match is not None:
                    # Add to existing theme
                    theme_id, similarity = match
                    success = await run_db(
                        self._add_article_to_theme_with_type,
                        article_id=UUID(str(article_id)),
                        theme_id=theme_id,
                        similarity=similarity,
                        embedding=embedding,
                        match_type=match_type,
                        is_seed=False
                    )
                    if success:
                        # Update event signature with theme_id
                        if signature:
                            await run_db(
                                self.db.update_event_signature_theme,
                                UUID(str(article_id)), theme_id
                            )
                        affected_themes.add(theme_id)
                        processed += 1
                else:
                    # Create new theme WITH event signature
                    theme = await run_db(
                        self.create_theme_with_signature,
                        article,
                        embedding,
                        signature
                    )

                    # Add article to new theme (as seed article)
                    success = await run_db(
                        self._add_article_to_theme_with_type,
                        article_id=UUID(str(article_id)),
                        theme_id=theme.id,
                        similarity=1.0,  # Perfect match with itself
                        embedding=embedding,
                        match_type='seed',
                        is_seed=True
                    )
                    if success:
                        # Update event signature with theme_id
                        if signature:
                            await run_db(
                                self.db.update_event_signature_theme,
                                UUID(str(article_id)), theme.id
                            )
                        new_themes.append(theme)
                        affected_themes.add(theme.id)
                        processed += 1

            except Exception as e:
                logger.error(f"Error processing article {article_id}: {e}")
                continue

        # Recalculate scores for affected themes
        for theme_id in affected_themes:
            score = await run_db(self.calculate_theme_score, theme_id)
            # Use update_theme method with score_avg parameter
            await run_db(self.db.update_theme, theme_id, score_avg=score)

        # Check for theme merging opportunities
        if new_themes:
            await self._check_theme_merging(new_themes)

        logger.info(
            f"Event-based clustering complete: {processed} articles processed, "
            f"{len(new_themes)} new themes created, "
            f"{len(affected_themes)} themes affected"
        )

        # Log clustering quality metrics after batch processing
        if processed > 0:
            quality_metrics = await run_db(self.evaluate_clustering_quality)
            silhouette = quality_metrics.get('silhouette_score')
            silhouette_str = f"{silhouette:.4f}" if silhouette is not None else "N/A"
            logger.info(
                f"Clustering quality: {quality_metrics.get('total_themes', 0)} themes, "
                f"{quality_metrics.get('total_articles_clustered', 0)} articles, "
                f"silhouette={silhouette_str}, "
                f"coverage={quality_metrics.get('coverage_ratio', 0):.2%}"
            )

        return processed

    def _add_article_to_theme_with_type(
        self,
        article_id: UUID,
        theme_id: UUID,
        similarity: float,
        embedding: List[float],
        match_type: str,
        is_seed: bool = False
    ) -> bool:
        """
        Add an article to a theme with match type tracking.

        Args:
            article_id: Article UUID
            theme_id: Theme UUID
            similarity: Similarity score
            embedding: Article embedding for centroid update
            match_type: Type of match ('exact', 'entity', 'verified', 'embedding', 'seed')
            is_seed: Whether this article is a seed article

        Returns:
            True if successful
        """
        if self.db is None:
            logger.warning("No database service, cannot add article to theme")
            return False

        try:
            # Add article-theme relationship with match type
            self.db.add_article_to_theme_with_match_type(
                article_id=article_id,
                theme_id=theme_id,
                similarity_score=similarity,
                match_type=match_type,
                is_seed=is_seed
            )

            # Update theme centroid with EMA
            self.update_theme_centroid(theme_id, embedding)

            logger.debug(
                f"Added article {article_id} to theme {theme_id} "
                f"(match_type={match_type}, similarity={similarity:.4f})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add article {article_id} to theme {theme_id}: {e}")
            return False

    def create_theme_with_signature(
        self,
        article: Dict[str, Any],
        embedding: List[float],
        signature=None,
        name: Optional[str] = None
    ) -> Theme:
        """
        Create a new theme with event signature data.

        Args:
            article: Article data dict
            embedding: Article embedding to use as initial centroid
            signature: Optional EventSignatureCreate with event data
            name: Optional theme name

        Returns:
            Created Theme object
        """
        if name is None:
            name = self._generate_temporary_name(article)

        slug = generate_slug(name)
        centroid = normalize_vector(embedding)

        # Prepare event data from signature
        canonical_event_key = None
        primary_entities = None

        if signature:
            canonical_event_key = signature.canonical_key
            primary_entities = {
                'people': signature.people or [],
                'organizations': signature.organizations or [],
                'locations': signature.locations or [],
                'event_action': signature.event_action or ''
            }

        if self.db:
            # Create theme in database
            theme_dict = self.db.create_theme(
                name=name,
                slug=slug,
                centroid=centroid,
                article_count=1
            )

            if theme_dict is None:
                raise ValueError(f"Failed to create theme '{name}'")

            # Update theme with event data
            if canonical_event_key or primary_entities:
                self.db.update_theme_event_data(
                    theme_id=theme_dict['id'],
                    canonical_event_key=canonical_event_key,
                    primary_entities=primary_entities,
                    seed_article_id=article.get('id')
                )

            # Update cache
            now = datetime.utcnow()
            with self._cache_lock:
                self._theme_cache[str(theme_dict['id'])] = {
                    'id': theme_dict['id'],
                    'name': name,
                    'centroid': centroid,
                    'article_count': 1,
                    'avg_score': 0,
                    'last_article_at': now
                }

            logger.info(
                f"Created new theme '{name}' (ID: {theme_dict['id']}) "
                f"with event key: {canonical_event_key}"
            )

            return Theme(
                id=theme_dict['id'],
                name=name,
                slug=slug,
                centroid=centroid,
                article_count=1,
                avg_score=0.0,
                status=theme_dict.get('status', 'active'),
                first_seen_at=theme_dict.get('created_at', now),
                last_updated_at=theme_dict.get('updated_at', now)
            )
        else:
            # Return mock theme for testing
            return Theme(
                id=uuid4(),
                name=name,
                slug=slug,
                centroid=centroid,
                article_count=1,
                avg_score=0.0,
                status='active',
                first_seen_at=datetime.utcnow(),
                last_updated_at=datetime.utcnow()
            )

    async def _check_theme_merging(self, themes_to_check: List[Theme]) -> int:
        """
        Check if any themes should be merged due to high similarity.

        Args:
            themes_to_check: List of newly created themes to compare

        Returns:
            Number of themes merged
        """
        if not themes_to_check:
            return 0

        merged_count = 0
        merged_ids: set = set()

        for theme in themes_to_check:
            if theme.id in merged_ids:
                continue

            if theme.centroid is None:
                continue

            # Find similar existing themes (excluding recently merged)
            exclude_ids = list(merged_ids) + [theme.id]
            match = await run_db(self.find_best_theme, theme.centroid, exclude_theme_ids=exclude_ids)

            if match is not None:
                other_id, similarity = match

                if similarity >= self.merge_threshold:
                    # Merge this theme into the other
                    success = await self._merge_themes(theme.id, other_id)
                    if success:
                        merged_ids.add(theme.id)
                        merged_count += 1

        if merged_count > 0:
            logger.info(f"Merged {merged_count} similar themes")
            self._invalidate_cache()

        return merged_count

    async def _merge_themes(
        self,
        source_theme_id: UUID,
        target_theme_id: UUID
    ) -> bool:
        """
        Merge source theme into target theme.

        All articles from source are moved to target, and source is deactivated.

        Args:
            source_theme_id: Theme to merge from (will be deactivated)
            target_theme_id: Theme to merge into

        Returns:
            True if successful
        """
        if self.db is None:
            return False

        try:
            # Note: These operations would require additional database methods
            # that don't currently exist. For now, we just deactivate the source theme.
            # TODO: Implement article transfer when db methods are available

            # Deactivate source theme using update_theme
            await run_db(self.db.update_theme, source_theme_id, status='inactive')

            # Remove from cache
            source_key = str(source_theme_id)
            with self._cache_lock:
                if source_key in self._theme_cache:
                    del self._theme_cache[source_key]

            logger.info(f"Merged theme {source_theme_id} into {target_theme_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to merge themes: {e}")
            return False

    async def generate_theme_name(
        self,
        articles: List[Dict[str, Any]],
        current_name: Optional[str] = None
    ) -> str:
        """
        Use LLM to generate a descriptive theme name.

        Args:
            articles: List of article dicts in the theme
            current_name: Optional current theme name for context

        Returns:
            Generated theme name (max 200 chars)
        """
        if not is_llm_configured() or self.llm is None:
            # Fallback to simple name extraction
            if articles:
                return self._generate_temporary_name(articles[0])
            return current_name or "Tema sem nome"

        # Build prompt with article titles
        titles = [a.get('title', '')[:100] for a in articles[:10]]  # Max 10 articles
        titles_text = "\n".join(f"- {t}" for t in titles if t)

        system_prompt = """Voce e um especialista em curadoria editorial.
Sua tarefa e criar um nome curto e descritivo para um agrupamento tematico de noticias.

Regras:
- Nome deve ter entre 15 e 50 caracteres
- Use palavras-chave que descrevam o tema principal
- Seja especifico (nao use termos genericos como "Noticias do Brasil")
- Em portugues brasileiro, sem acentos
- Formato: substantivo + complemento (ex: "Crise no transporte publico de SP", "Eleicoes Municipais 2024")
- Responda APENAS com o nome, sem aspas, sem explicacao
"""

        user_prompt = f"""Analise os titulos abaixo e crie um nome para este agrupamento tematico:

{titles_text}

Nome atual (se existir): {current_name or 'Nenhum'}

Responda APENAS com o nome do tema (maximo 50 caracteres):"""

        try:
            response = await self.llm._call_api(
                system=system_prompt,
                user_content=user_prompt,
                max_tokens=100,
                model=get_config().theme_naming_model,
                task_type='theme_naming'
            )

            # Clean response
            name = response.strip().strip('"\'')
            name = name[:200]  # Max length

            if not name:
                return current_name or self._generate_temporary_name(articles[0])

            logger.info(f"Generated theme name: {name}")
            return name

        except Exception as e:
            logger.warning(f"Failed to generate theme name via LLM: {e}")
            if articles:
                return self._generate_temporary_name(articles[0])
            return current_name or "Tema sem nome"

    async def refine_theme_names(self, min_articles: int = 3) -> int:
        """
        Refine names for themes that have enough articles.

        Args:
            min_articles: Minimum articles required before refining name

        Returns:
            Number of themes renamed
        """
        if self.db is None or not is_llm_configured():
            return 0

        # Get active themes and filter by article count
        all_themes = self.db.get_all_themes(status='active')
        themes = [t for t in all_themes if t.get('article_count', 0) >= min_articles]

        renamed = 0
        for theme in themes:
            theme_id = theme['id']
            theme_name = theme['name']

            # Get articles for context using get_articles_by_theme
            articles_result = self.db.get_articles_by_theme(theme_id, limit=10)
            articles = articles_result[0] if articles_result else []

            if not articles:
                continue

            # Convert Article objects to dicts for generate_theme_name
            article_dicts = [
                {'title': a.title, 'content': a.content, 'preview': a.preview}
                for a in articles
            ]

            try:
                new_name = await self.generate_theme_name(article_dicts, theme_name)

                if new_name != theme_name:
                    new_slug = generate_slug(new_name)
                    self.db.update_theme(theme_id, name=new_name, slug=new_slug)
                    renamed += 1

            except Exception as e:
                logger.error(f"Failed to refine name for theme {theme_id}: {e}")

        if renamed > 0:
            logger.info(f"Refined names for {renamed} themes")

        return renamed

    def evaluate_clustering_quality(self) -> Dict[str, Any]:
        """
        Avalia a qualidade do clustering atual.

        Returns:
            Dict com metricas:
            - total_themes: int - Total de temas ativos
            - total_articles_clustered: int - Total de artigos em temas
            - avg_articles_per_theme: float - Media de artigos por tema
            - themes_with_multiple_articles: int - Temas com mais de 1 artigo
            - silhouette_score: float (se possivel calcular) - Metrica de qualidade
            - coverage_ratio: float - Artigos com tema / total artigos com embedding
            - singleton_themes: int - Temas com apenas 1 artigo
            - largest_theme_size: int - Tamanho do maior tema
            - evaluated_at: str - Timestamp da avaliacao
        """
        if self.db is None:
            return {
                'error': 'Database not configured',
                'evaluated_at': datetime.utcnow().isoformat()
            }

        try:
            # Get all active themes
            themes = self.db.get_all_themes(status='active')
            total_themes = len(themes)

            if total_themes == 0:
                return {
                    'total_themes': 0,
                    'total_articles_clustered': 0,
                    'avg_articles_per_theme': 0.0,
                    'themes_with_multiple_articles': 0,
                    'silhouette_score': None,
                    'coverage_ratio': 0.0,
                    'singleton_themes': 0,
                    'largest_theme_size': 0,
                    'evaluated_at': datetime.utcnow().isoformat()
                }

            # Calculate article statistics
            article_counts = [t.get('article_count', 0) for t in themes]
            total_articles_clustered = sum(article_counts)
            avg_articles = total_articles_clustered / total_themes if total_themes > 0 else 0.0
            themes_with_multiple = sum(1 for c in article_counts if c > 1)
            singleton_themes = sum(1 for c in article_counts if c == 1)
            largest_theme_size = max(article_counts) if article_counts else 0

            # Calculate coverage ratio
            # We need to count total articles with embeddings
            coverage_ratio = self._calculate_coverage_ratio()

            # Calculate silhouette score (can be expensive)
            silhouette = self.calculate_silhouette_score()

            metrics = {
                'total_themes': total_themes,
                'total_articles_clustered': total_articles_clustered,
                'avg_articles_per_theme': round(avg_articles, 2),
                'themes_with_multiple_articles': themes_with_multiple,
                'silhouette_score': round(silhouette, 4) if silhouette is not None else None,
                'coverage_ratio': round(coverage_ratio, 4),
                'singleton_themes': singleton_themes,
                'largest_theme_size': largest_theme_size,
                'evaluated_at': datetime.utcnow().isoformat()
            }

            logger.info(
                f"Clustering quality: {total_themes} themes, "
                f"{total_articles_clustered} articles, "
                f"silhouette={silhouette:.4f if silhouette else 'N/A'}"
            )

            return metrics

        except Exception as e:
            logger.error(f"Error evaluating clustering quality: {e}")
            return {
                'error': str(e),
                'evaluated_at': datetime.utcnow().isoformat()
            }

    def _calculate_coverage_ratio(self) -> float:
        """
        Calculate the ratio of articles with themes vs total articles with embeddings.

        Returns:
            Coverage ratio between 0 and 1
        """
        if self.db is None:
            return 0.0

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Count articles with embeddings
                cursor.execute("""
                    SELECT COUNT(*) FROM article_embeddings
                """)
                total_with_embedding = cursor.fetchone()[0]

                if total_with_embedding == 0:
                    return 0.0

                # Count articles in themes
                cursor.execute("""
                    SELECT COUNT(DISTINCT article_id) FROM article_themes
                """)
                total_in_themes = cursor.fetchone()[0]

                return total_in_themes / total_with_embedding

        except Exception as e:
            logger.error(f"Error calculating coverage ratio: {e}")
            return 0.0

    def calculate_silhouette_score(self, sample_size: int = 500) -> Optional[float]:
        """
        Calculate silhouette score for the current clustering.

        Uses sklearn if available, otherwise falls back to manual calculation.
        For performance, samples a subset of articles if dataset is large.

        Args:
            sample_size: Maximum number of articles to sample for calculation

        Returns:
            Silhouette score between -1 and 1, or None if not calculable
        """
        if self.db is None:
            return None

        try:
            # Try to use sklearn first
            try:
                from sklearn.metrics import silhouette_score as sklearn_silhouette
                use_sklearn = True
            except ImportError:
                use_sklearn = False
                logger.debug("sklearn not available, using manual silhouette calculation")

            # Fetch articles with embeddings and their theme assignments
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Get articles with themes and embeddings
                # Sample for performance
                query = f"""
                    SELECT TOP {sample_size}
                        e.article_id,
                        e.embedding,
                        r.theme_id
                    FROM article_embeddings e
                    JOIN article_themes r ON e.article_id = r.article_id
                    ORDER BY NEWID()
                """
                cursor.execute(query)
                rows = cursor.fetchall()

            if len(rows) < 10:
                logger.debug("Not enough data for silhouette calculation (< 10 samples)")
                return None

            # Parse embeddings and create label mapping
            import json
            embeddings = []
            theme_ids = []
            theme_id_to_label = {}
            label_counter = 0

            for row in rows:
                embedding = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                theme_id = str(row[2])

                if embedding is None:
                    continue

                embeddings.append(embedding)

                if theme_id not in theme_id_to_label:
                    theme_id_to_label[theme_id] = label_counter
                    label_counter += 1

                theme_ids.append(theme_id_to_label[theme_id])

            if len(embeddings) < 10:
                return None

            # Check we have at least 2 clusters
            if len(set(theme_ids)) < 2:
                logger.debug("Not enough clusters for silhouette (< 2 clusters)")
                return None

            if use_sklearn:
                # Use sklearn for efficiency (lazy import — daily maintenance only)
                import numpy as np
                embeddings_arr = np.array(embeddings, dtype=np.float64)
                labels_arr = np.array(theme_ids)
                score = sklearn_silhouette(embeddings_arr, labels_arr, metric='cosine')
                return float(score)
            else:
                # Use manual calculation
                return calculate_silhouette_score_manual(embeddings, theme_ids)

        except Exception as e:
            logger.error(f"Error calculating silhouette score: {e}")
            return None


# Singleton instance
_clustering_service: Optional[ClusteringService] = None


def get_clustering_service(
    db_service=None,
    llm_service: Optional[LLMService] = None
) -> ClusteringService:
    """
    Get or create the clustering service singleton.

    Args:
        db_service: Optional DatabaseService to inject
        llm_service: Optional LLMService for theme naming

    Returns:
        ClusteringService instance
    """
    global _clustering_service

    if _clustering_service is None:
        _clustering_service = ClusteringService(db_service, llm_service)
    elif db_service is not None and _clustering_service.db is None:
        _clustering_service.db = db_service
    elif llm_service is not None and _clustering_service.llm is None:
        _clustering_service.llm = llm_service

    return _clustering_service


def is_clustering_enabled() -> bool:
    """Check if clustering feature is enabled."""
    return CLUSTERING_ENABLED


def calculate_silhouette_score_manual(
    embeddings: List[List[float]],
    labels: List[int]
) -> Optional[float]:
    """
    Calculate silhouette score manually using numpy.

    The silhouette score measures how similar an object is to its own cluster
    compared to other clusters. Range: -1 to 1, higher is better.

    For each sample i:
    - a(i) = average distance to other samples in the same cluster
    - b(i) = minimum average distance to samples in any other cluster
    - s(i) = (b(i) - a(i)) / max(a(i), b(i))

    Final score = mean of all s(i)

    Args:
        embeddings: List of embedding vectors
        labels: Cluster assignment for each embedding

    Returns:
        Silhouette score between -1 and 1, or None if calculation not possible
    """
    # Lazy import — this function only runs during daily 3AM maintenance
    import numpy as np

    if len(embeddings) < 2:
        return None

    unique_labels = set(labels)
    if len(unique_labels) < 2:
        # Need at least 2 clusters
        return None

    # Filter out noise points (label -1 if any)
    valid_indices = [i for i, l in enumerate(labels) if l >= 0]
    if len(valid_indices) < 2:
        return None

    embeddings_arr = np.array([embeddings[i] for i in valid_indices], dtype=np.float64)
    labels_arr = np.array([labels[i] for i in valid_indices])

    n_samples = len(embeddings_arr)
    unique_labels = set(labels_arr)

    if len(unique_labels) < 2:
        return None

    # Precompute all pairwise cosine distances (1 - similarity)
    # Using broadcasting for efficiency
    norms = np.linalg.norm(embeddings_arr, axis=1, keepdims=True)
    norms[norms == 0] = 1  # Avoid division by zero
    normalized = embeddings_arr / norms
    similarities = np.dot(normalized, normalized.T)
    distances = 1 - similarities

    silhouette_scores = []

    for i in range(n_samples):
        label_i = labels_arr[i]

        # Get indices of same cluster (excluding self)
        same_cluster = [j for j in range(n_samples) if labels_arr[j] == label_i and j != i]

        if len(same_cluster) == 0:
            # Singleton cluster, silhouette not defined
            continue

        # a(i) = mean intra-cluster distance
        a_i = np.mean([distances[i, j] for j in same_cluster])

        # b(i) = min mean distance to other clusters
        b_i = float('inf')
        for other_label in unique_labels:
            if other_label == label_i:
                continue
            other_cluster = [j for j in range(n_samples) if labels_arr[j] == other_label]
            if len(other_cluster) == 0:
                continue
            mean_dist = np.mean([distances[i, j] for j in other_cluster])
            b_i = min(b_i, mean_dist)

        if b_i == float('inf'):
            continue

        # s(i) = (b(i) - a(i)) / max(a(i), b(i))
        max_ab = max(a_i, b_i)
        if max_ab == 0:
            s_i = 0
        else:
            s_i = (b_i - a_i) / max_ab

        silhouette_scores.append(s_i)

    if len(silhouette_scores) == 0:
        return None

    return float(np.mean(silhouette_scores))
