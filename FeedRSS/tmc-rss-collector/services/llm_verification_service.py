"""
LLM Verification Service for Same Event Detection

Uses LLM to verify if two articles describe the SAME SPECIFIC EVENT,
not just similar topics or concepts.

Key distinction:
- "Two accidents on the same highway" = DIFFERENT events
- "Same accident reported by two sources" = SAME event
"""

import os
import json
import logging
import hashlib
import threading
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from services.config import get_config
from services.llm_service import LLMService, is_llm_configured

logger = logging.getLogger(__name__)

# Configuration
VERIFICATION_ENABLED = os.environ.get("EVENT_VERIFICATION_ENABLED", "true").lower() == "true"
VERIFICATION_MAX_TOKENS = 512
VERIFICATION_CACHE_TTL_HOURS = 24


# Verification prompt
VERIFICATION_SYSTEM = """Voce e um editor jornalistico experiente.

Analise os dois artigos e determine se descrevem o MESMO EVENTO ESPECIFICO.

REGRAS IMPORTANTES:
- "Mesmo tipo de evento" NAO e suficiente
  Dois acidentes diferentes = eventos DIFERENTES

- "Mesmo evento" significa:
  - Mesma pessoa envolvida no MESMO incidente
  - Mesmo acontecimento especifico
  - Mesmo local e periodo aproximado (mesmo dia/semana)

EXEMPLOS:
- "Empresario brasileiro detido pelo ICE" e
  "Pai de trigemeos preso nos EUA"
  → MESMO EVENTO (mesma pessoa, mesmo incidente)

- "Trump anuncia tarifas para China" e
  "Entenda as novas tarifas de Trump para China"
  → MESMO EVENTO (mesmo anuncio, diferentes angulos)

- "Acidente na BR-101 mata 3 pessoas" e
  "Outro acidente na BR-101 deixa feridos"
  → EVENTOS DIFERENTES (acidentes distintos)

- "Lula anuncia programa habitacional" e
  "Lula critica oposicao em discurso"
  → EVENTOS DIFERENTES (ocasioes distintas)

RESPONDA APENAS com JSON valido."""


VERIFICATION_USER_TEMPLATE = """Analise se os artigos descrevem o MESMO EVENTO ESPECIFICO:

ARTIGO 1:
Titulo: {title1}
Preview: {preview1}

ARTIGO 2:
Titulo: {title2}
Preview: {preview2}

RESPONDA EM JSON:
{{
  "is_same_event": true ou false,
  "confidence": 0.0 a 1.0,
  "reasoning": "explicacao em 1 frase"
}}"""


class LLMVerificationService:
    """
    Service for verifying if two articles describe the same specific event.

    Uses LLM to make nuanced judgments that pure algorithmic matching cannot.
    Includes caching to avoid repeated API calls for the same article pairs.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the verification service.

        Args:
            llm_service: Optional LLMService for API calls
        """
        self.llm = llm_service

        # Cache for verification results
        # Key: hash of sorted (title1, title2)
        # Value: {"result": dict, "timestamp": datetime}
        self._verification_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

        logger.info(f"LLMVerificationService initialized: enabled={VERIFICATION_ENABLED}")

    def _get_cache_key(self, title1: str, title2: str) -> str:
        """
        Generate cache key for an article pair.

        Key is deterministic regardless of order (article1 vs article2).
        """
        # Sort titles to ensure same key regardless of order
        sorted_titles = sorted([title1[:200], title2[:200]])
        combined = f"{sorted_titles[0]}||{sorted_titles[1]}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached verification result if still valid.

        Args:
            cache_key: Cache key for the article pair

        Returns:
            Cached result dict or None if not found/expired
        """
        with self._cache_lock:
            if cache_key not in self._verification_cache:
                return None

            cached = self._verification_cache[cache_key]
            timestamp = cached.get('timestamp')

            if timestamp:
                age = datetime.utcnow() - timestamp
                if age < timedelta(hours=VERIFICATION_CACHE_TTL_HOURS):
                    logger.debug(f"Cache hit for verification: {cache_key[:8]}...")
                    return cached.get('result')

            # Expired
            del self._verification_cache[cache_key]
            return None

    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache verification result."""
        with self._cache_lock:
            self._verification_cache[cache_key] = {
                'result': result,
                'timestamp': datetime.utcnow()
            }

            # Limit cache size
            if len(self._verification_cache) > 1000:
                # Remove oldest entries
                oldest_keys = sorted(
                    self._verification_cache.keys(),
                    key=lambda k: self._verification_cache[k].get('timestamp', datetime.min)
                )[:200]
                for key in oldest_keys:
                    del self._verification_cache[key]

    async def verify_same_event(
        self,
        article1: Dict[str, str],
        article2: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Verify if two articles describe the same specific event.

        Args:
            article1: Dict with 'title' and 'preview' of first article
            article2: Dict with 'title' and 'preview' of second article

        Returns:
            Dict with:
                - is_same_event: bool
                - confidence: float (0-1)
                - reasoning: str
                - from_cache: bool
        """
        if not VERIFICATION_ENABLED:
            return {
                'is_same_event': False,
                'confidence': 0.0,
                'reasoning': 'Verification disabled',
                'from_cache': False
            }

        title1 = article1.get('title', '')
        title2 = article2.get('title', '')
        preview1 = article1.get('preview', '')
        preview2 = article2.get('preview', '')

        if not title1 or not title2:
            return {
                'is_same_event': False,
                'confidence': 0.0,
                'reasoning': 'Missing article titles',
                'from_cache': False
            }

        # Check cache
        cache_key = self._get_cache_key(title1, title2)
        cached = self._get_cached_result(cache_key)
        if cached:
            cached['from_cache'] = True
            return cached

        # Quick heuristic: identical titles = same event
        if title1.strip().lower() == title2.strip().lower():
            result = {
                'is_same_event': True,
                'confidence': 0.99,
                'reasoning': 'Titulos identicos',
                'from_cache': False
            }
            self._cache_result(cache_key, result)
            return result

        # Call LLM for verification
        if not is_llm_configured() or self.llm is None:
            logger.warning("LLM not configured for verification")
            return {
                'is_same_event': False,
                'confidence': 0.0,
                'reasoning': 'LLM not configured',
                'from_cache': False
            }

        try:
            user_prompt = VERIFICATION_USER_TEMPLATE.format(
                title1=title1[:300],
                preview1=preview1[:500] if preview1 else title1,
                title2=title2[:300],
                preview2=preview2[:500] if preview2 else title2
            )

            response_text = await self.llm._call_api(
                system=VERIFICATION_SYSTEM,
                user_content=user_prompt,
                max_tokens=VERIFICATION_MAX_TOKENS,
                model=get_config().event_verification_model,
                task_type='event_verification'
            )

            result = self._parse_verification_response(response_text)
            result['from_cache'] = False

            # Cache the result
            self._cache_result(cache_key, result)

            logger.info(
                f"Verification result: is_same={result['is_same_event']}, "
                f"confidence={result['confidence']:.2f}, "
                f"reasoning='{result['reasoning'][:50]}...'"
            )

            return result

        except Exception as e:
            logger.error(f"Error in event verification: {e}")
            return {
                'is_same_event': False,
                'confidence': 0.0,
                'reasoning': f'Error: {str(e)}',
                'from_cache': False
            }

    def _parse_verification_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLM response into verification result.

        Args:
            response_text: Raw LLM response

        Returns:
            Dict with is_same_event, confidence, reasoning
        """
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end <= json_start:
                logger.error("No valid JSON in verification response")
                return {
                    'is_same_event': False,
                    'confidence': 0.0,
                    'reasoning': 'Invalid response format'
                }

            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            return {
                'is_same_event': bool(data.get('is_same_event', False)),
                'confidence': float(data.get('confidence', 0.5)),
                'reasoning': str(data.get('reasoning', 'No reasoning provided'))
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse verification JSON: {e}")
            return {
                'is_same_event': False,
                'confidence': 0.0,
                'reasoning': f'JSON parse error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error parsing verification response: {e}")
            return {
                'is_same_event': False,
                'confidence': 0.0,
                'reasoning': f'Parse error: {str(e)}'
            }

    def verify_same_event_sync(
        self,
        article1: Dict[str, str],
        article2: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for verify_same_event.

        Use in non-async contexts.
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.verify_same_event(article1, article2))
        except RuntimeError:
            return asyncio.run(self.verify_same_event(article1, article2))

    def clear_cache(self) -> None:
        """Clear the verification cache."""
        with self._cache_lock:
            self._verification_cache.clear()
        logger.info("Verification cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        valid_count = 0
        expired_count = 0

        with self._cache_lock:
            entries = list(self._verification_cache.values())
            total = len(self._verification_cache)

        for cached in entries:
            timestamp = cached.get('timestamp')
            if timestamp:
                age = now - timestamp
                if age < timedelta(hours=VERIFICATION_CACHE_TTL_HOURS):
                    valid_count += 1
                else:
                    expired_count += 1

        return {
            'total_entries': total,
            'valid_entries': valid_count,
            'expired_entries': expired_count,
            'ttl_hours': VERIFICATION_CACHE_TTL_HOURS
        }


# Singleton instance
_verification_service: Optional[LLMVerificationService] = None


def get_llm_verification_service(
    llm_service: Optional[LLMService] = None
) -> LLMVerificationService:
    """
    Get or create the verification service singleton.

    Args:
        llm_service: Optional LLMService to inject

    Returns:
        LLMVerificationService instance
    """
    global _verification_service

    if _verification_service is None:
        _verification_service = LLMVerificationService(llm_service)
    elif llm_service is not None and _verification_service.llm is None:
        _verification_service.llm = llm_service

    return _verification_service


def is_verification_enabled() -> bool:
    """Check if event verification is enabled."""
    return VERIFICATION_ENABLED
