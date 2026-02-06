"""
Event Signature Service for Specific Event Clustering

Extracts unique event signatures from articles using LLM to identify:
- WHO: Named entities (people, organizations)
- WHERE: Specific locations
- WHAT: Main action/event
- WHEN: Event date if mentioned

This enables clustering by SPECIFIC EVENT rather than generic semantic concepts.
"""

import os
import json
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from uuid import UUID

from models.event_signature import (
    EventSignature,
    EventSignatureCreate,
    normalize_entity
)
from services.llm_service import LLMService, is_llm_configured

logger = logging.getLogger(__name__)

# Configuration
EVENT_EXTRACTION_ENABLED = os.environ.get("EVENT_EXTRACTION_ENABLED", "true").lower() == "true"
EVENT_EXTRACTION_MODEL = os.environ.get("EVENT_EXTRACTION_MODEL", "claude-sonnet-4-5")
EVENT_EXTRACTION_MAX_TOKENS = 1024


# Extraction prompt for event signature
EVENT_EXTRACTION_SYSTEM = """Voce e um especialista em identificacao de eventos jornalisticos.

Sua tarefa e extrair a ASSINATURA DO EVENTO ESPECIFICO descrito no artigo.

IMPORTANTE:
- Extraia NOMES PROPRIOS de pessoas, nao descricoes genericas
- Extraia ORGANIZACOES ESPECIFICAS mencionadas (ICE, STF, Petrobras, Flamengo)
- Identifique a ACAO PRINCIPAL do evento (verbo no participio ou infinitivo)
- Liste DETALHES UNICOS que identificam ESTE evento especifico

REGRAS:
- Se nao ha nome proprio, use a descricao mais especifica disponivel
- "Empresario brasileiro" e valido se nao ha nome
- Sempre extraia pelo menos 1 pessoa OU 1 organizacao
- event_action deve ser UM verbo (detido, morreu, anunciou, venceu, fechou)
- Para datas, use formato YYYY-MM-DD ou null se nao mencionado

RESPONDA APENAS com JSON valido, sem texto adicional."""


EVENT_EXTRACTION_USER_TEMPLATE = """Analise o artigo e extraia a ASSINATURA DO EVENTO ESPECIFICO:

TITULO: {title}

PREVIEW/CONTEUDO:
{content}

RESPONDA EM JSON:
{{
  "people": ["lista de nomes proprios de pessoas"],
  "organizations": ["organizacoes especificas (ICE, STF, Petrobras)"],
  "locations": ["locais especificos do evento"],
  "event_action": "verbo principal (detido, morreu, anunciou, venceu)",
  "unique_details": ["detalhes unicos: pai de trigemeos, empresario, etc"],
  "event_date": "YYYY-MM-DD ou null se nao mencionado",
  "confidence": 0.95
}}"""


class EventSignatureService:
    """
    Service for extracting event signatures from articles.

    Uses LLM to identify specific event identifiers that allow
    clustering articles about the SAME specific event.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Initialize the event signature service.

        Args:
            llm_service: Optional LLMService instance for extraction
        """
        self.llm = llm_service
        self._extraction_cache: Dict[str, EventSignatureCreate] = {}

        logger.info(
            f"EventSignatureService initialized: enabled={EVENT_EXTRACTION_ENABLED}"
        )

    async def extract(
        self,
        title: str,
        content: str,
        article_id: Optional[UUID] = None,
        reference_date: Optional[date] = None
    ) -> Optional[EventSignatureCreate]:
        """
        Extract event signature from article title and content.

        Args:
            title: Article title
            content: Article preview or full content
            article_id: Optional article ID for the signature
            reference_date: Reference date for canonical key (defaults to today)

        Returns:
            EventSignatureCreate with extracted data, or None if extraction fails
        """
        if not EVENT_EXTRACTION_ENABLED:
            logger.debug("Event extraction disabled")
            return None

        if not is_llm_configured() or self.llm is None:
            logger.warning("LLM not configured for event extraction")
            return self._extract_fallback(title, content, article_id, reference_date)

        # Check cache
        cache_key = f"{title[:100]}|{content[:200]}"
        if cache_key in self._extraction_cache:
            cached = self._extraction_cache[cache_key]
            if article_id:
                cached.article_id = article_id
            return cached

        try:
            # Build prompt
            user_prompt = EVENT_EXTRACTION_USER_TEMPLATE.format(
                title=title[:500],
                content=content[:2000] if content else title
            )

            # Call LLM
            response_text = await self.llm._call_api(
                system=EVENT_EXTRACTION_SYSTEM,
                user_content=user_prompt,
                max_tokens=EVENT_EXTRACTION_MAX_TOKENS
            )

            # Parse response
            signature = self._parse_extraction_response(
                response_text,
                article_id,
                reference_date
            )

            if signature:
                # Cache result
                self._extraction_cache[cache_key] = signature

                logger.info(
                    f"Extracted event signature: action='{signature.event_action}', "
                    f"people={len(signature.people)}, orgs={len(signature.organizations)}, "
                    f"confidence={signature.confidence:.2f}"
                )

            return signature

        except Exception as e:
            logger.error(f"Error extracting event signature: {e}")
            return self._extract_fallback(title, content, article_id, reference_date)

    def _parse_extraction_response(
        self,
        response_text: str,
        article_id: Optional[UUID],
        reference_date: Optional[date]
    ) -> Optional[EventSignatureCreate]:
        """
        Parse LLM response into EventSignatureCreate.

        Args:
            response_text: Raw LLM response
            article_id: Article ID
            reference_date: Reference date for canonical key

        Returns:
            EventSignatureCreate or None if parsing fails
        """
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end <= json_start:
                logger.error("No valid JSON found in extraction response")
                return None

            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            # Parse event date
            event_date = None
            if data.get("event_date") and data["event_date"] != "null":
                try:
                    event_date = datetime.strptime(
                        data["event_date"], "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass

            # Create signature
            from uuid import uuid4
            signature = EventSignatureCreate(
                article_id=article_id or uuid4(),
                people=data.get("people", []) or [],
                organizations=data.get("organizations", []) or [],
                locations=data.get("locations", []) or [],
                event_action=data.get("event_action", "") or "",
                unique_details=data.get("unique_details", []) or [],
                event_date=event_date,
                confidence=float(data.get("confidence", 0.8))
            )

            # Generate canonical key
            signature.canonical_key = signature.generate_canonical_key(reference_date)

            return signature

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing extraction response: {e}")
            return None

    def _extract_fallback(
        self,
        title: str,
        content: str,
        article_id: Optional[UUID],
        reference_date: Optional[date]
    ) -> Optional[EventSignatureCreate]:
        """
        Fallback extraction using simple heuristics when LLM is unavailable.

        Uses regex patterns to extract:
        - Capitalized names (potential people/organizations)
        - Location patterns (em/no/na + capitalized)
        - Action verbs from title

        Args:
            title: Article title
            content: Article content
            article_id: Article ID
            reference_date: Reference date

        Returns:
            EventSignatureCreate with basic extraction
        """
        from uuid import uuid4

        text = f"{title} {content}" if content else title

        # Extract potential people/organizations (capitalized sequences)
        # Pattern: 2+ words starting with capital letters
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        names = re.findall(name_pattern, text)

        # Filter common non-names
        stop_names = {
            'Estados Unidos', 'Sao Paulo', 'Rio Janeiro', 'Minas Gerais',
            'Porto Alegre', 'Belo Horizonte', 'Santa Catarina'
        }
        people = [n for n in names if n not in stop_names][:5]

        # Extract organizations (common patterns)
        org_patterns = [
            r'\b(ICE|FBI|CIA|STF|STJ|TSE|PF|PRF|MPF)\b',
            r'\b([A-Z]{2,})\b',  # Acronyms
            r'\b(Ministerio\s+\w+|Secretaria\s+\w+)\b'
        ]
        organizations = []
        for pattern in org_patterns:
            orgs = re.findall(pattern, text)
            organizations.extend(orgs)
        organizations = list(set(organizations))[:5]

        # Extract locations (em/no/na + name)
        location_pattern = r'\b(?:em|no|na|nos|nas)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        locations = re.findall(location_pattern, text)
        locations = list(set(locations))[:3]

        # Extract action verb from title
        action_verbs = [
            'detido', 'preso', 'morreu', 'morre', 'morto',
            'anunciou', 'anuncia', 'venceu', 'vence', 'ganhou',
            'perdeu', 'perde', 'fechou', 'fecha', 'abre',
            'lanca', 'lancou', 'demite', 'demitiu', 'contrata'
        ]
        event_action = ""
        title_lower = title.lower()
        for verb in action_verbs:
            if verb in title_lower:
                event_action = verb
                break

        # Create signature with low confidence
        signature = EventSignatureCreate(
            article_id=article_id or uuid4(),
            people=people,
            organizations=organizations,
            locations=locations,
            event_action=event_action,
            unique_details=[],
            event_date=None,
            confidence=0.4  # Low confidence for fallback
        )

        signature.canonical_key = signature.generate_canonical_key(reference_date)

        logger.info(f"Fallback extraction: {signature.canonical_key}")
        return signature

    def extract_sync(
        self,
        title: str,
        content: str,
        article_id: Optional[UUID] = None,
        reference_date: Optional[date] = None
    ) -> Optional[EventSignatureCreate]:
        """
        Synchronous wrapper for extract.

        Use in non-async contexts.
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.extract(title, content, article_id, reference_date))
        except RuntimeError:
            return asyncio.run(self.extract(title, content, article_id, reference_date))

    def clear_cache(self) -> None:
        """Clear the extraction cache."""
        self._extraction_cache.clear()
        logger.info("Event signature extraction cache cleared")


# Singleton instance
_event_signature_service: Optional[EventSignatureService] = None


def get_event_signature_service(
    llm_service: Optional[LLMService] = None
) -> EventSignatureService:
    """
    Get or create the event signature service singleton.

    Args:
        llm_service: Optional LLMService to inject

    Returns:
        EventSignatureService instance
    """
    global _event_signature_service

    if _event_signature_service is None:
        _event_signature_service = EventSignatureService(llm_service)
    elif llm_service is not None and _event_signature_service.llm is None:
        _event_signature_service.llm = llm_service

    return _event_signature_service


def is_event_extraction_enabled() -> bool:
    """Check if event extraction is enabled."""
    return EVENT_EXTRACTION_ENABLED
