"""
Fact Check Service for TMC Article Generation

Anti-hallucination pipeline with 4 components:
1. Pre-generation enrichment via Exa web search
2. Post-generation claim verification
3. Chain-of-Verification (CoVe) for fabricated claims
4. Confidence scoring and risk assessment

Verification failures NEVER block article generation - progressive degradation.
"""

import os
import re
import json
import time
import math
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field
from collections import Counter

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from services.config import get_config

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

FACT_CHECK_ENABLED = os.environ.get("FACT_CHECK_ENABLED", "true").lower() == "true"
ENRICHMENT_ENABLED = os.environ.get("FACT_CHECK_ENRICHMENT_ENABLED", "true").lower() == "true"
VERIFICATION_ENABLED = os.environ.get("FACT_CHECK_VERIFICATION_ENABLED", "true").lower() == "true"
MAX_CLAIMS = int(os.environ.get("FACT_CHECK_MAX_CLAIMS", "10"))

# CoVe (Chain-of-Verification) configuration
COVE_ENABLED = os.environ.get("COVE_ENABLED", "true").lower() == "true"
COVE_MAX_CLAIMS = int(os.environ.get("COVE_MAX_CLAIMS", "5"))
COVE_QUESTIONS_PER_CLAIM = int(os.environ.get("COVE_QUESTIONS_PER_CLAIM", "3"))

EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
EXA_ENDPOINT = os.environ.get("EXA_API_ENDPOINT", "https://api.exa.ai/search")
EXA_MAX_RESULTS = int(os.environ.get("EXA_MAX_RESULTS", "5"))
EXA_SEARCH_DAYS = int(os.environ.get("EXA_SEARCH_DAYS", "7"))
EXA_TIMEOUT = int(os.environ.get("EXA_TIMEOUT_SECONDS", "15"))

# Confidence scoring weights (calibrated for journalism safety)
# v7: Entities 20% → 15% to reduce false positive rate (30% FP from novel entities)
WEIGHT_CLAIM_GROUNDING = 0.45
WEIGHT_ENTITY_OVERLAP = 0.15
WEIGHT_EXPANSION_RATIO = 0.10
WEIGHT_QUOTE_VERIFICATION = 0.10
WEIGHT_MATERIAL_SUFFICIENCY = 0.10
WEIGHT_CLAIM_SIMILARITY = 0.10  # v7: raised from 0.05 to absorb entity weight reduction


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ExtractedClaim:
    """Individual factual claim extracted from generated article."""
    text: str
    verdict: str = "unverifiable"  # grounded | fabricated | unverifiable | inaccurate | opinion | context
    source_evidence: str = ""
    source_reference: str = ""  # Best matching source sentence
    category: str = "fact"  # fact | statistic | quote | outcome | attribution | opinion


@dataclass
class EntityComparisonResult:
    """Source vs output entity overlap analysis."""
    source_entities: list = field(default_factory=list)
    output_entities: list = field(default_factory=list)
    common_entities: list = field(default_factory=list)
    novel_entities: list = field(default_factory=list)
    overlap_score: float = 0.0


@dataclass
class QuoteVerificationResult:
    """Quote traceability check."""
    total_quotes: int = 0
    verified_quotes: int = 0
    unverified_quotes: list = field(default_factory=list)
    verification_rate: float = 1.0


@dataclass
class EnrichmentContext:
    """Web search enrichment context from Exa."""
    context_text: str = ""
    key_facts: list = field(default_factory=list)
    source_urls: list = field(default_factory=list)
    search_queries: list = field(default_factory=list)
    success: bool = False
    verified_chars: int = 0  # Total chars of verified material (source + enrichment)


@dataclass
class CoVeVerification:
    """Chain-of-Verification result for a single claim."""
    original_claim: str = ""
    original_verdict: str = "fabricated"
    questions: list = field(default_factory=list)
    answers: list = field(default_factory=list)
    final_verdict: str = "fabricated"
    confidence_delta: float = 0.0  # positive = confidence boost
    evidence_strength: str = "weak"  # strong | moderate | weak


@dataclass
class VerificationMetadata:
    """Complete verification output."""
    confidence_score: float = 0.0
    risk_level: str = "high"  # low | medium | high | critical
    expansion_ratio: float = 0.0
    source_sufficiency: str = "unknown"  # sufficient | marginal | insufficient
    total_claims: int = 0
    grounded_claims: int = 0
    fabricated_claims: int = 0
    unverifiable_claims: int = 0
    context_claims: int = 0
    claims: list = field(default_factory=list)
    entity_comparison: dict = field(default_factory=dict)
    quote_verification: dict = field(default_factory=dict)
    requires_human_review: bool = True
    review_reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    is_verified: bool = False
    verification_duration_ms: int = 0
    enrichment_used: bool = False
    cove_applied: bool = False
    cove_reclassified: int = 0
    cove_results: list = field(default_factory=list)  # List[CoVeVerification]
    truncation: dict = field(default_factory=dict)  # Truncation metadata (4A)
    claim_extraction_failed: bool = False  # Empty claims fallback (4B)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        claims_list = []
        for c in self.claims:
            if isinstance(c, ExtractedClaim):
                claims_list.append({
                    "text": c.text,
                    "verdict": c.verdict,
                    "source_evidence": c.source_evidence,
                    "source_reference": c.source_reference,
                    "category": c.category,
                })
            elif isinstance(c, dict):
                claims_list.append(c)

        return {
            "confidence_score": round(self.confidence_score, 3),
            "risk_level": self.risk_level,
            "expansion_ratio": round(self.expansion_ratio, 2),
            "source_sufficiency": self.source_sufficiency,
            "total_claims": self.total_claims,
            "grounded_claims": self.grounded_claims,
            "fabricated_claims": self.fabricated_claims,
            "unverifiable_claims": self.unverifiable_claims,
            "context_claims": self.context_claims,
            "claims": claims_list,
            "entity_comparison": self.entity_comparison,
            "quote_verification": self.quote_verification,
            "requires_human_review": self.requires_human_review,
            "review_reasons": self.review_reasons,
            "warnings": self.warnings,
            "is_verified": self.is_verified,
            "verification_duration_ms": self.verification_duration_ms,
            "enrichment_used": self.enrichment_used,
            "cove_applied": self.cove_applied,
            "cove_reclassified": self.cove_reclassified,
            "truncation": self.truncation,
            "claim_extraction_failed": self.claim_extraction_failed,
        }


# =============================================================================
# Helper Functions
# =============================================================================

def _lcs_length(a: list, b: list) -> int:
    """Compute Longest Common Subsequence length between two word lists."""
    m, n = len(a), len(b)
    if m == 0 or n == 0:
        return 0
    # Space-optimized: only keep previous row
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    return prev[n]


# =============================================================================
# Phase 2.3: Temporal Decontamination Patterns
# =============================================================================

# Temporal patterns NOT typically found in wire/source text
_TEMPORAL_DECONTAMINATION_PATTERNS = [
    # Days of the week (nesta segunda-feira, nesta terca, etc.)
    re.compile(r'\b(?:nesta|nesse|naquele|na)\s+(?:segunda|terca|quarta|quinta|sexta|sabado|domingo)(?:-feira)?\b', re.IGNORECASE),
    # Specific times (às 14h, às 10h30, por volta das 15h)
    re.compile(r'\b(?:as|por volta das|desde as|ate as)\s+\d{1,2}h\d{0,2}\b', re.IGNORECASE),
    # "na manhã/tarde/noite de hoje"
    re.compile(r'\b(?:na|pela)\s+(?:manha|tarde|noite)\s+de\s+(?:hoje|ontem)\b', re.IGNORECASE),
    # "nesta madrugada"
    re.compile(r'\bnesta\s+madrugada\b', re.IGNORECASE),
]


def decontaminate_article(article_text: str, source_text: str, enrichment_text: str = "") -> tuple:
    """
    Remove temporal specifics from article that don't appear in any source.

    Phase 2.3: Post-generation regex pass removing invented temporal details.
    Runs between generation and verification.

    Args:
        article_text: Generated article content
        source_text: Original source text
        enrichment_text: Enrichment context text (optional)

    Returns:
        Tuple of (cleaned_text, removals_count, removed_patterns)
    """
    all_source = (source_text + " " + enrichment_text).lower()
    cleaned = article_text
    removals = []

    for pattern in _TEMPORAL_DECONTAMINATION_PATTERNS:
        for match in pattern.finditer(article_text):
            matched_text = match.group().lower().strip()
            # Check if this temporal reference appears in ANY source
            if matched_text not in all_source:
                # Replace with empty string, clean up double spaces
                cleaned = cleaned[:match.start()] + cleaned[match.end():]
                removals.append(matched_text)
                # Re-run on cleaned text to handle shifted positions
                break  # One removal at a time due to position shifts

    # Second pass for any remaining patterns (after first pass shifts)
    if removals:
        for pattern in _TEMPORAL_DECONTAMINATION_PATTERNS:
            for match in pattern.finditer(cleaned):
                matched_text = match.group().lower().strip()
                if matched_text not in all_source:
                    cleaned = pattern.sub("", cleaned, count=1)
                    removals.append(matched_text)

    # Clean up double spaces and leading spaces after removal
    cleaned = re.sub(r'  +', ' ', cleaned)
    cleaned = re.sub(r'\n +', '\n', cleaned)

    return cleaned, len(removals), removals


# =============================================================================
# Phase 3.3: Readability Measurement
# =============================================================================

def _strip_markdown(text: str) -> str:
    """Strip markdown formatting before readability analysis."""
    # Remove bold/italic markers
    text = text.replace('**', '').replace('__', '')
    text = text.replace('*', '').replace('_', ' ')
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove markdown links [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove stray markdown artifacts
    text = re.sub(r'[`~]', '', text)
    return text


def compute_readability(text: str) -> dict:
    """
    Compute Flesch readability score for Brazilian Portuguese text.

    Formula: 248.835 - 1.015 * ASL - 84.6 * ASY
    Where ASL = average sentence length, ASY = average syllables per word.

    Returns dict with flesch_score, avg_sentence_length, long_sentence_pct, readability_level.
    """
    # Strip markdown before analysis to avoid inflated counts
    clean_text = _strip_markdown(text)

    # Split into sentences
    sentences = re.split(r'[.!?]+', clean_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    if not sentences:
        return {"flesch_score": 0, "avg_sentence_length": 0, "long_sentence_pct": 0, "readability_level": "unknown"}

    # Count words per sentence
    word_counts = [len(s.split()) for s in sentences]
    total_words = sum(word_counts)
    avg_sentence_length = total_words / len(sentences) if sentences else 0

    # Long sentence percentage (>20 words)
    long_sentences = sum(1 for wc in word_counts if wc > 20)
    long_sentence_pct = long_sentences / len(sentences) if sentences else 0

    # Count syllables (Portuguese approximation)
    all_words = clean_text.split()
    total_syllables = sum(_count_syllables_pt(w) for w in all_words if len(w) > 0)
    avg_syllables_per_word = total_syllables / total_words if total_words > 0 else 0

    # Flesch-PT formula
    flesch_score = 248.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
    flesch_score = max(0, min(100, flesch_score))

    # Readability level (calibrated for PT-BR journalism: 45-55 is normal)
    if flesch_score >= 75:
        level = "muito_facil"
    elif flesch_score >= 60:
        level = "facil"
    elif flesch_score >= 45:
        level = "medio"
    elif flesch_score >= 30:
        level = "dificil"
    else:
        level = "muito_dificil"

    # Count bold elements in original (pre-stripped) text
    bold_count = len(re.findall(r'\*\*[^*]+\*\*', text))

    return {
        "flesch_score": round(flesch_score, 1),
        "avg_sentence_length": round(avg_sentence_length, 1),
        "avg_syllables_per_word": round(avg_syllables_per_word, 2),
        "long_sentence_pct": round(long_sentence_pct * 100, 1),
        "readability_level": level,
        "words": total_words,
        "bold_count": bold_count,
    }


# Portuguese diphthongs (count as 1 syllable, not 2)
_PT_DIPHTHONGS = {
    'ai', 'au', 'ei', 'eu', 'iu', 'oi', 'ou', 'ui', 'io',
    'ão', 'ãe', 'õe',
    'ái', 'áu', 'éi', 'éu', 'ói',
    'âi',
}

# Portuguese hiatus pairs (count as 2 syllables despite being adjacent vowels)
_PT_HIATUS = {
    'aí', 'aú', 'eí', 'oí', 'uí',
    'ía', 'íe', 'ío', 'úa', 'úe', 'úo',
}


def _count_syllables_pt(word: str) -> int:
    """
    Improved syllable count for Portuguese words.

    Handles diphthongs (ai, ei, oi, ou, ão, õe, etc.) as single syllables
    and hiatus pairs (aí, oí, etc.) as two syllables.
    """
    # Strip markdown and punctuation
    word = word.replace('**', '').replace('*', '')
    word = word.lower().strip(".,;:!?\"'()[]{}—–-_@#/\\")

    if not word:
        return 1
    # Pure numbers get 1 syllable
    if word.isdigit() or re.match(r'^\d+[.,]?\d*$', word):
        return 1

    vowels = set("aeiouáéíóúâêîôûãõàü")
    count = 0
    i = 0
    length = len(word)

    while i < length:
        if word[i] not in vowels:
            i += 1
            continue

        # Found a vowel — start a new syllable
        count += 1

        # Check for diphthong/hiatus (2-char vowel combo)
        if i + 1 < length and word[i + 1] in vowels:
            pair = word[i:i + 2]
            if pair in _PT_HIATUS:
                # Hiatus: each vowel is a separate syllable
                i += 1
                continue
            if pair in _PT_DIPHTHONGS:
                # Diphthong: skip the second vowel (already counted)
                i += 2
                # Check for true triphthong (only uai, uei, uou in Portuguese)
                if i < length and word[i] in vowels:
                    triplet = word[i - 2:i + 1]
                    if triplet in ('uai', 'uei', 'uou'):
                        i += 1
                continue
            # Unrecognized pair — default to diphthong (1 syllable)
            # Most adjacent vowels in PT-BR function as diphthongs in practice
            while i + 1 < length and word[i + 1] in vowels:
                pair = word[i:i + 2]
                if pair in _PT_HIATUS:
                    break
                i += 1
            i += 1
        else:
            i += 1

    return max(1, count)


# =============================================================================
# FactCheckService
# =============================================================================

class FactCheckService:
    """
    Orchestrates the anti-hallucination pipeline.

    - enrich_context(): Pre-generation web search via Exa
    - verify_article(): Post-generation claim/entity/quote verification
    """

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=float(EXA_TIMEOUT))
        self._llm_service = None
        # Circuit breaker state for Exa API
        self._exa_failures = 0
        self._exa_circuit_open = False
        self._exa_circuit_open_until = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        if self.http_client:
            await self.http_client.aclose()

    def _get_llm(self):
        """Lazy-load LLM service to avoid circular imports."""
        if self._llm_service is None:
            from services.llm_service import get_llm_service
            self._llm_service = get_llm_service()
        return self._llm_service

    def _parse_json_response(self, response_text: str) -> Optional[dict]:
        """Extract and parse JSON from an LLM response text."""
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            try:
                return json.loads(response_text[json_start:json_end])
            except json.JSONDecodeError:
                return None
        return None

    # CoVe evidence strength -> confidence delta mapping
    _EVIDENCE_DELTA_MAP = {"strong": 0.08, "moderate": 0.05, "weak": 0.02}

    # =========================================================================
    # Phase 1: Pre-Generation Enrichment
    # =========================================================================

    async def enrich_context(
        self,
        texto_base: str,
        titulo_fonte: Optional[str] = None,
        tags: Optional[list] = None,
        correlation_id: str = "",
    ) -> EnrichmentContext:
        """
        Search for verified external context to enrich article generation.

        When source text is short (<500 chars), uses aggressive mode:
        more results, more text per result, more key facts extracted.

        Args:
            texto_base: Source text content
            titulo_fonte: Source article title (better search queries)
            tags: Tags for search refinement

        Returns:
            EnrichmentContext with verified facts and source URLs
        """
        result = EnrichmentContext()
        source_len = len(texto_base.strip())

        if not ENRICHMENT_ENABLED:
            logger.info("Enrichment disabled via config")
            return result

        if not EXA_API_KEY:
            logger.warning("EXA_API_KEY not set, skipping enrichment")
            return result

        # Aggressive mode for short sources - need more external material
        aggressive = source_len < 500
        num_queries = 3 if aggressive else 2
        num_results = min(EXA_MAX_RESULTS + 3, 10) if aggressive else EXA_MAX_RESULTS
        max_text_chars = 4000 if aggressive else 2000
        max_facts = 15 if aggressive else 8
        context_limit = 6000 if aggressive else 3000

        if aggressive:
            logger.info(f"Aggressive enrichment: source={source_len} chars, "
                       f"queries={num_queries}, results={num_results}")

        try:
            # Build search queries - more queries for short sources
            queries = self._build_search_queries(texto_base, titulo_fonte, tags)
            result.search_queries = queries

            if not queries:
                return result

            # Execute parallel Exa searches
            search_tasks = [
                self._search_exa(q, num_results=num_results, max_text=max_text_chars)
                for q in queries[:num_queries]
            ]
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            # Collect all results, deduplicate by URL and domain, filter non-article pages
            from urllib.parse import urlparse
            all_texts = []
            all_urls = set()
            seen_domains = set()
            filtered_count = 0
            for sr in search_results:
                if isinstance(sr, Exception):
                    logger.warning(f"Exa search failed: {sr}")
                    continue
                if sr:
                    for item in sr:
                        text = item.get("text", "")
                        url = item.get("url", "")
                        title = item.get("title", "")
                        if url in all_urls:
                            continue  # Skip exact URL duplicates
                        # Deduplicate by domain (keep first per domain)
                        domain = urlparse(url).netloc if url else ""
                        if domain and domain in seen_domains:
                            continue
                        if not self._is_quality_url(url, text):
                            logger.debug(f"Filtered non-article URL: {url[:80]}")
                            filtered_count += 1
                            continue
                        if text and len(text.strip()) > 50:
                            all_texts.append(f"[{title}]({url}) {text[:max_text_chars]}")
                        if url:
                            all_urls.add(url)
                        if domain:
                            seen_domains.add(domain)

            result.source_urls = list(all_urls)[:15]
            logger.info(f"Exa quality filter: {len(all_urls)} quality URLs kept, {filtered_count} filtered out")

            if not all_texts:
                logger.info("No enrichment results from Exa")
                return result

            # Extract key facts from search results using LLM
            combined_text = "\n\n---\n\n".join(all_texts[:8])
            key_facts = await self._extract_key_facts(
                combined_text, texto_base, titulo_fonte, max_facts=max_facts
            )

            result.context_text = combined_text[:context_limit]
            result.key_facts = key_facts
            result.success = len(key_facts) > 0 or len(result.context_text.strip()) > 200
            result.verified_chars = source_len + len(result.context_text)

            logger.info(
                f"Enrichment: {len(key_facts)} key facts, "
                f"{len(all_urls)} sources, "
                f"verified_chars={result.verified_chars}, "
                f"context_text_len={len(result.context_text)}, "
                f"success={result.success}"
            )
            return result

        except Exception as e:
            logger.error(f"Enrichment failed (non-blocking): {e}")
            return result

    def _build_search_queries(
        self,
        texto_base: str,
        titulo_fonte: Optional[str],
        tags: Optional[list]
    ) -> list:
        """
        Build 1-3 search queries from source material.

        Priority: titulo_fonte > texto_base sentence > tags + entities.
        The titulo_fonte is the most specific description of the event and
        produces the best Exa results for the SAME subject.
        """
        queries = []

        # Query 1 (best): Full title - most specific, gets same-event results
        if titulo_fonte and len(titulo_fonte.strip()) > 10:
            queries.append(titulo_fonte.strip())

        # Query 2: First meaningful sentence from texto_base
        text_clean = texto_base.strip().replace("\n", " ")
        first_sentence = text_clean[:150].rsplit(".", 1)[0]
        if len(first_sentence) > 15 and first_sentence not in queries:
            queries.append(first_sentence)

        # Query 3: Tags combined (for broader context)
        if tags and len(tags) >= 2:
            tag_query = " ".join(tags[:5])
            if tag_query not in queries:
                queries.append(tag_query)

        # Fallback: extract proper nouns from texto_base
        if len(queries) < 2 and len(texto_base) > 30:
            words = texto_base.strip().split()
            key_words = [w for w in words if len(w) > 2 and w[0].isupper()][:6]
            if len(key_words) >= 2:
                entity_query = " ".join(key_words)
                if entity_query not in queries:
                    queries.append(entity_query)

        return queries[:3]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ConnectTimeout)),
        reraise=True,
    )
    async def _search_exa(
        self,
        query: str,
        num_results: int = EXA_MAX_RESULTS,
        max_text: int = 2000
    ) -> list:
        """
        Execute a single Exa search with retry and circuit breaker.

        Retries on connection errors (up to 3 attempts with exponential backoff).
        Circuit breaker opens after 3 consecutive failures, stays open for 60s.

        Args:
            query: Search query string
            num_results: Number of results to fetch
            max_text: Max characters of article text per result

        Returns list of {title, url, text, publishedDate} dicts.
        """
        # Circuit breaker check
        if self._exa_circuit_open:
            if time.time() < self._exa_circuit_open_until:
                logger.warning("Exa circuit breaker OPEN, skipping search")
                return []
            else:
                # Half-open: allow one attempt
                logger.info("Exa circuit breaker half-open, attempting request")
                self._exa_circuit_open = False

        headers = {
            "Content-Type": "application/json",
            "x-api-key": EXA_API_KEY,
        }

        payload = {
            "query": query,
            "type": "neural",
            "useAutoprompt": True,
            "numResults": num_results,
            "category": "news",
            "startPublishedDate": self._get_date_range_start(),
            "contents": {
                "text": {"maxCharacters": max_text},
                "highlights": {"numSentences": 3}
            }
        }

        try:
            response = await self.http_client.post(
                EXA_ENDPOINT,
                headers=headers,
                json=payload,
            )
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            self._exa_failures += 1
            if self._exa_failures >= 3:
                self._exa_circuit_open = True
                self._exa_circuit_open_until = time.time() + 60
                logger.warning(f"Exa circuit breaker OPENED after {self._exa_failures} failures")
            raise  # Let tenacity handle retry

        if response.status_code != 200:
            logger.warning(f"Exa API returned {response.status_code}: {response.text[:200]}")
            self._exa_failures += 1
            if self._exa_failures >= 3:
                self._exa_circuit_open = True
                self._exa_circuit_open_until = time.time() + 60
                logger.warning(f"Exa circuit breaker OPENED after {self._exa_failures} consecutive errors")
            return []

        # Success: reset circuit breaker
        self._exa_failures = 0

        data = response.json()
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "text": item.get("text", ""),
                "publishedDate": item.get("publishedDate", ""),
                "highlights": item.get("highlights", []),
            })

        logger.info(f"Exa search '{query[:50]}...' returned {len(results)} results")
        return results

    def _get_date_range_start(self) -> str:
        """Get ISO date string for search range start."""
        from datetime import datetime, timedelta
        start = datetime.utcnow() - timedelta(days=EXA_SEARCH_DAYS)
        return start.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    async def verify_claim_with_exa(
        self,
        claim: ExtractedClaim,
        timeout: float = 3.0,
    ) -> dict:
        """
        Verify a specific claim using Exa web search.

        Searches for the claim text, then uses LLM to compare search results
        with the original claim to determine if it's confirmed, contradicted,
        or inconclusive.

        Args:
            claim: The claim to verify
            timeout: Max seconds for the Exa search

        Returns:
            dict with keys: verdict (confirmed|contradicted|inconclusive),
            corrective_instruction (str|None), evidence (str)
        """
        try:
            # Build search query from claim text (first 100 chars)
            query = claim.text[:100]

            # Search with timeout
            try:
                results = await asyncio.wait_for(
                    self._search_exa(query, num_results=3, max_text=1000),
                    timeout=timeout,
                )
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning(f"Exa claim search failed for '{query[:50]}': {e}")
                return {
                    "verdict": "inconclusive",
                    "corrective_instruction": f'REMOVER: "{claim.text}"',
                    "evidence": "",
                }

            if not results:
                return {
                    "verdict": "inconclusive",
                    "corrective_instruction": f'REMOVER: "{claim.text}"',
                    "evidence": "",
                }

            # Combine search results for LLM comparison
            search_context = "\n".join(
                f"[{r.get('title', '')}] {r.get('text', '')[:500]}"
                for r in results[:3]
            )

            # LLM comparison: is the claim confirmed or contradicted?
            llm = self._get_llm()
            system_prompt = "Verificador factual objetivo."
            comparison_prompt = f"""Compare esta AFIRMACAO com as FONTES encontradas na web.

AFIRMACAO: "{claim.text}"

FONTES:
{search_context}

Responda em JSON:
```json
{{
  "verdict": "confirmed|contradicted|inconclusive",
  "correct_data": "Se contradicted, qual e a informacao correta? Null se confirmed/inconclusive",
  "evidence": "Resumo breve da evidencia encontrada"
}}
```

Regras:
- "confirmed": as fontes CONFIRMAM a afirmacao (dados batem)
- "contradicted": as fontes CONTRADIZEM a afirmacao (dados diferentes)
- "inconclusive": as fontes nao falam sobre este assunto especifico"""

            response = await llm.call_api(system_prompt, comparison_prompt, 512, task_type='source_comparison')
            parsed = self._parse_json_response(response)

            if not parsed:
                return {
                    "verdict": "inconclusive",
                    "corrective_instruction": f'REMOVER: "{claim.text}"',
                    "evidence": "",
                }

            verdict = parsed.get("verdict", "inconclusive")
            correct_data = parsed.get("correct_data")
            evidence = parsed.get("evidence", "")

            if verdict == "confirmed":
                return {
                    "verdict": "confirmed",
                    "corrective_instruction": None,
                    "evidence": evidence,
                }
            elif verdict == "contradicted" and correct_data:
                return {
                    "verdict": "contradicted",
                    "corrective_instruction": (
                        f'CORRIGIR: "{claim.text}" esta ERRADO. '
                        f'Informacao correta: {correct_data}'
                    ),
                    "evidence": evidence,
                }
            else:
                return {
                    "verdict": "inconclusive",
                    "corrective_instruction": f'REMOVER: "{claim.text}"',
                    "evidence": evidence,
                }

        except Exception as e:
            logger.warning(f"Claim verification failed (non-blocking): {e}")
            return {
                "verdict": "inconclusive",
                "corrective_instruction": f'REMOVER: "{claim.text}"',
                "evidence": "",
            }

    # URL patterns that indicate non-article pages (topic indexes, portals, docs)
    _BAD_URL_PATTERNS = [
        "/topicos/", "/folha-topicos/", "/assuntos/", "/tag/",
        "/tags/", "/categoria/", "/categorias/", "/editoria/",
        "/index.php", "/index.html",
        "/c/mundo/", "/c/brasil/",
        "blogspot.com",
        "/docs/", "/developers/", "/api/",
        "/acompanhamento-", "/orcamento-cidadao",
        "/transparencia.",
    ]

    # Whitelisted .gov.br domains (quality official sources)
    _GOV_BR_WHITELIST = [
        "agenciabrasil.ebc.com.br",
        "gov.br/planalto",
        "gov.br/saude",
        "gov.br/economia",
        "bcb.gov.br",
        "ibge.gov.br",
        "inpe.br",
        "anatel.gov.br",
        # v7: expanded high-authority government domains
        "tse.jus.br",
        "stf.jus.br",
        "stj.jus.br",
        "camara.leg.br",
        "senado.leg.br",
        "planalto.gov.br",
        "gov.br/defesa",
        "gov.br/justica",
        "gov.br/educacao",
        "gov.br/trabalho",
        "gov.br/mre",
        "gov.br/fazenda",
        "bndes.gov.br",
        "cvm.gov.br",
        "susep.gov.br",
        "anvisa.gov.br",
        "ans.gov.br",
    ]

    def _is_quality_url(self, url: str, text: str) -> bool:
        """Filter out non-article URLs (topic pages, portals, indexes)."""
        url_lower = url.lower()

        # .gov.br / .leg.br / .jus.br: whitelist known quality sources
        # Also accept any .gov.br, .leg.br, .jus.br URL with article-like paths
        if ".gov.br" in url_lower or ".leg.br" in url_lower or ".jus.br" in url_lower:
            # Always allow explicitly whitelisted domains
            if any(domain in url_lower for domain in self._GOV_BR_WHITELIST):
                pass  # allowed
            # Block generic portal/index pages from .gov.br
            elif url_lower.rstrip("/").endswith(".gov.br") or url_lower.count("/") <= 3:
                return False

        for pattern in self._BAD_URL_PATTERNS:
            if pattern in url_lower:
                return False

        if not text or len(text.strip()) < 150:
            return False

        return True

    async def _extract_key_facts(
        self,
        search_text: str,
        texto_base: str,
        titulo_fonte: Optional[str] = None,
        max_facts: int = 8
    ) -> list:
        """
        Extract verified key facts from search results relevant to the source.

        For short sources, extracts more detailed facts to serve as
        verified material for article generation.
        """
        try:
            llm = self._get_llm()
            source_len = len(texto_base.strip())

            # For short sources, use a more detailed extraction prompt
            if source_len < 500:
                system = ("Voce e um editor jornalistico. Extraia TODOS os fatos verificados "
                         "sobre o MESMO ASSUNTO da noticia original.")
                titulo_ref = f"\nTITULO DA NOTICIA: {titulo_fonte}" if titulo_fonte else ""
                prompt = f"""A noticia original tem poucos detalhes. Use os resultados de busca
para extrair TODOS os fatos verificados sobre o MESMO ASSUNTO.
{titulo_ref}

TEXTO-BASE (noticia original - curto):
{texto_base}

RESULTADOS DE BUSCA (fontes jornalisticas verificadas):
{search_text[:5000]}

Retorne APENAS um JSON:
```json
{{
  "key_facts": [
    "Fato verificado detalhado 1",
    "Fato verificado detalhado 2"
  ]
}}
```

Regras IMPORTANTES:
- Maximo {max_facts} fatos
- Para cada fato extraido, verifique: este fato e sobre o MESMO EVENTO ESPECIFICO descrito no texto-base{' e titulo "' + titulo_fonte + '"' if titulo_fonte else ''}?
- Inclua APENAS fatos sobre o MESMO EVENTO. Descarte fatos sobre eventos similares mas diferentes, informacoes institucionais genericas, ou contexto nao relacionado
- NAO inclua fatos de noticias diferentes, mesmo que relacionadas
- Extraia: nomes completos, cargos, numeros exatos, datas, decisoes, cronologia
- Cada fato deve ser uma frase completa e informativa
- Foque em informacoes que ajudem a escrever uma materia completa
- NAO inclua opinioes, analises ou especulacoes"""
            else:
                system = "Voce e um assistente de verificacao factual. Extraia fatos verificados."
                titulo_ref = f"\nTITULO: {titulo_fonte}" if titulo_fonte else ""
                prompt = f"""Dado o TEXTO-BASE de uma noticia e RESULTADOS DE BUSCA,
extraia os fatos-chave VERIFICADOS relevantes ao texto-base.
{titulo_ref}

TEXTO-BASE:
{texto_base[:1000]}

RESULTADOS DE BUSCA:
{search_text[:3000]}

Retorne APENAS um JSON:
```json
{{
  "key_facts": [
    "Fato verificado 1",
    "Fato verificado 2"
  ]
}}
```

Regras:
- Maximo {max_facts} fatos
- Para cada fato extraido, verifique: este fato e sobre o MESMO EVENTO ESPECIFICO descrito no texto-base{' e titulo "' + titulo_fonte + '"' if titulo_fonte else ''}?
- Inclua APENAS fatos sobre o mesmo evento. Descarte fatos sobre eventos similares mas diferentes, informacoes institucionais genericas, ou contexto nao relacionado
- Foque em: nomes corretos, numeros, datas, decisoes, resultados
- Nao inclua opinioes ou analises"""

            max_tokens = 2048 if source_len < 500 else 1024
            response_text = await llm.call_api(system, prompt, max_tokens, model=get_config().enrichment_extraction_model, task_type='enrichment_extraction')

            # Try standard JSON extraction
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                try:
                    data = json.loads(response_text[json_start:json_end])
                    raw_facts = data.get("key_facts", [])[:max_facts]
                    # Phase 2.4: Cross-contamination guard
                    return self._filter_cross_contaminated_facts(raw_facts, texto_base)
                except json.JSONDecodeError:
                    logger.warning("JSON parse failed, trying text fallback")

            # Fallback: extract facts from bullet points/numbered lists
            facts = []
            for line in response_text.split("\n"):
                line = line.strip()
                if line and (line.startswith("- ") or line.startswith("* ")):
                    fact = line[2:].strip().strip('"').strip("'")
                    if len(fact) > 20:
                        facts.append(fact)
                elif line and len(line) > 2 and line[0].isdigit() and line[1] in ".)":
                    fact = line[2:].strip().strip('"').strip("'")
                    if len(fact) > 20:
                        facts.append(fact)

            if facts:
                logger.info(f"Recovered {len(facts)} facts from text fallback")
                return facts[:max_facts]

            return []
        except Exception as e:
            logger.warning(f"Key fact extraction failed: {e}")
            return []

    def _filter_cross_contaminated_facts(self, facts: list, source_text: str) -> list:
        """
        Phase 2.4: Filter enrichment facts that have zero entity overlap with source.

        Prevents enrichment from injecting data about SIMILAR but DIFFERENT events.
        A fact must share at least one proper noun (capitalized word > 3 chars)
        with the source text to be kept.
        """
        if not facts:
            return facts

        # Extract proper nouns from source
        source_words = set()
        for word in source_text.split():
            clean = word.strip(".,;:!?\"'()[]{}—–-")
            if len(clean) > 3 and clean[0].isupper():
                source_words.add(clean.lower())

        if not source_words:
            return facts  # Can't filter without entity reference

        filtered = []
        removed = 0
        for fact in facts:
            fact_words = set()
            for word in fact.split():
                clean = word.strip(".,;:!?\"'()[]{}—–-")
                if len(clean) > 3 and clean[0].isupper():
                    fact_words.add(clean.lower())

            # Require at least one overlapping proper noun
            if fact_words & source_words:
                filtered.append(fact)
            else:
                removed += 1

        if removed > 0:
            logger.info(f"Cross-contamination guard: removed {removed}/{len(facts)} enrichment facts")

        # Minimum retention: when ALL facts would be removed, keep top 2.
        # Removing ALL enrichment is worse than keeping marginally related facts,
        # since the enrichment search already filtered by topic relevance.
        if not filtered and len(facts) >= 2:
            logger.info(
                f"Cross-contamination guard: keeping top 2 facts "
                f"(all {len(facts)} would have been removed)"
            )
            filtered = facts[:2]
        elif not filtered:
            logger.warning(
                f"Cross-contamination guard: ALL {len(facts)} enrichment facts "
                f"removed (zero entity overlap with source)"
            )

        return filtered

    # =========================================================================
    # Phase 3: Post-Generation Verification
    # =========================================================================

    async def verify_article(
        self,
        texto_base: str,
        generated_article: str,
        citacoes: Optional[list] = None,
        enrichment: Optional[EnrichmentContext] = None,
        correlation_id: str = "",
    ) -> VerificationMetadata:
        """
        Verify a generated article against source material.

        Runs 3 checks in parallel:
        1. Claim extraction + grounding (LLM)
        2. Entity comparison (regex)
        3. Quote verification (string matching)

        Args:
            texto_base: Original source text
            generated_article: Generated article content
            citacoes: Quotes provided by user
            enrichment: Enrichment context from Phase 1

        Returns:
            VerificationMetadata with confidence score and risk assessment
        """
        if not VERIFICATION_ENABLED:
            return VerificationMetadata(
                is_verified=False,
                warnings=["Verification disabled via config"],
                requires_human_review=True,
            )

        start_time = time.time()
        metadata = VerificationMetadata()

        # Calculate expansion ratio
        # Use verified_chars (source + enrichment) when enrichment was used,
        # since enrichment context is verified material the LLM can draw from
        source_len = len(texto_base.strip())
        output_len = len(generated_article.strip())
        effective_source = source_len
        if enrichment and enrichment.success and enrichment.verified_chars > source_len:
            effective_source = enrichment.verified_chars
        metadata.expansion_ratio = output_len / max(effective_source, 1)

        # Classify source sufficiency
        if effective_source < 150:
            metadata.source_sufficiency = "insufficient"
        elif effective_source < 500:
            metadata.source_sufficiency = "marginal"
        else:
            metadata.source_sufficiency = "sufficient"

        try:
            # Run 3 checks in parallel
            claim_task = self._extract_and_verify_claims(
                texto_base, generated_article, enrichment
            )
            enrichment_text_for_entities = ""
            if enrichment and enrichment.success:
                enrichment_text_for_entities = enrichment.context_text or ""
            entity_task = asyncio.to_thread(
                self._compare_entities, texto_base, generated_article,
                enrichment_text_for_entities,
            )
            quote_task = asyncio.to_thread(
                self._verify_quotes, generated_article, texto_base, citacoes
            )

            results = await asyncio.gather(
                claim_task, entity_task, quote_task,
                return_exceptions=True
            )

            # Process claim results
            if isinstance(results[0], Exception):
                logger.error(f"Claim verification failed: {results[0]}")
                metadata.warnings.append("Claim verification failed")
            else:
                claims = results[0]
                metadata.claims = claims
                metadata.total_claims = len(claims)
                # Empty claims fallback (4B)
                if not claims:
                    logger.warning("Claim extraction returned 0 claims — article passes with reduced confidence")
                    metadata.claim_extraction_failed = True
                # Opinion claims don't count toward factual accuracy metrics
                # Context claims DO count (they must be factually correct)
                metadata.grounded_claims = sum(
                    1 for c in claims if c.verdict == "grounded"
                )
                metadata.fabricated_claims = sum(
                    1 for c in claims if c.verdict == "fabricated"
                )
                metadata.unverifiable_claims = sum(
                    1 for c in claims if c.verdict == "unverifiable"
                )
                opinion_count = sum(
                    1 for c in claims if c.verdict == "opinion"
                )
                context_count = sum(
                    1 for c in claims if c.verdict == "context"
                )
                metadata.context_claims = context_count
                # Backwards compat: also count legacy "editorial" as opinion
                editorial_count = sum(
                    1 for c in claims if c.verdict == "editorial"
                )
                if opinion_count + editorial_count > 0:
                    logger.info(f"Opinion claims excluded from scoring: {opinion_count + editorial_count}")
                if context_count > 0:
                    logger.info(f"Context claims (factual, counted in scoring): {context_count}")

            # Process entity results
            if isinstance(results[1], Exception):
                logger.error(f"Entity comparison failed: {results[1]}")
                metadata.warnings.append("Entity comparison failed")
                entity_result = EntityComparisonResult()
            else:
                entity_result = results[1]
                metadata.entity_comparison = {
                    "source_entities": entity_result.source_entities[:20],
                    "output_entities": entity_result.output_entities[:20],
                    "common_entities": entity_result.common_entities[:20],
                    "novel_entities": entity_result.novel_entities[:20],
                    "overlap_score": round(entity_result.overlap_score, 3),
                }
                if entity_result.novel_entities:
                    metadata.warnings.append(
                        f"Novel entities not in source: {', '.join(entity_result.novel_entities[:5])}"
                    )

            # Process quote results
            if isinstance(results[2], Exception):
                logger.error(f"Quote verification failed: {results[2]}")
                metadata.warnings.append("Quote verification failed")
                quote_result = QuoteVerificationResult()
            else:
                quote_result = results[2]
                metadata.quote_verification = {
                    "total_quotes": quote_result.total_quotes,
                    "verified_quotes": quote_result.verified_quotes,
                    "unverified_quotes": quote_result.unverified_quotes[:10],
                    "verification_rate": round(quote_result.verification_rate, 3),
                }

            # ==============================================================
            # CoVe: Chain-of-Verification for fabricated claims
            # ==============================================================
            if metadata.fabricated_claims > 0:
                try:
                    claims, cove_results, reclassified = await self._cove_verify_claims(
                        metadata.claims, texto_base, enrichment
                    )
                    metadata.claims = claims
                    metadata.cove_applied = True
                    metadata.cove_reclassified = reclassified
                    metadata.cove_results = cove_results

                    # Recount verdicts after CoVe reclassification
                    if reclassified > 0:
                        metadata.grounded_claims = sum(
                            1 for c in claims
                            if (isinstance(c, ExtractedClaim) and c.verdict == "grounded")
                            or (isinstance(c, dict) and c.get("verdict") == "grounded")
                        )
                        metadata.fabricated_claims = sum(
                            1 for c in claims
                            if (isinstance(c, ExtractedClaim) and c.verdict == "fabricated")
                            or (isinstance(c, dict) and c.get("verdict") == "fabricated")
                        )
                        metadata.unverifiable_claims = sum(
                            1 for c in claims
                            if (isinstance(c, ExtractedClaim) and c.verdict == "unverifiable")
                            or (isinstance(c, dict) and c.get("verdict") == "unverifiable")
                        )
                        logger.info(
                            f"Post-CoVe verdicts: grounded={metadata.grounded_claims}, "
                            f"fabricated={metadata.fabricated_claims}, "
                            f"unverifiable={metadata.unverifiable_claims}"
                        )
                except Exception as e:
                    logger.warning(f"CoVe failed (non-blocking): {e}")

            # Compute TF-IDF claim-source similarity (pure CPU, no API calls)
            claim_similarities = []
            if metadata.claims:
                enrichment_text = ""
                if enrichment and enrichment.success:
                    enrichment_text = enrichment.context_text or ""
                claim_similarities = self._compute_claim_source_similarity(
                    metadata.claims, texto_base, enrichment_text
                )
                # Fill in missing source_reference using TF-IDF best match
                self._fill_source_references(
                    metadata.claims, texto_base, enrichment_text
                )

            # Compute confidence score
            metadata.confidence_score = self._compute_confidence(
                metadata, entity_result, quote_result, claim_similarities
            )

            # Determine risk level
            metadata.risk_level = self._determine_risk_level(
                metadata, entity_result, quote_result
            )

            # Determine review requirement
            metadata.requires_human_review = metadata.risk_level in ("high", "critical")
            if metadata.requires_human_review:
                if metadata.fabricated_claims > 0:
                    metadata.review_reasons.append(
                        f"{metadata.fabricated_claims} claim(s) identified as fabricated"
                    )
                if metadata.expansion_ratio > 25:
                    metadata.review_reasons.append(
                        f"Extreme expansion ratio: {metadata.expansion_ratio:.1f}x"
                    )
                if metadata.source_sufficiency == "insufficient":
                    metadata.review_reasons.append("Source text insufficient (<150 chars)")
                if entity_result.novel_entities:
                    metadata.review_reasons.append(
                        f"Novel entities: {', '.join(entity_result.novel_entities[:3])}"
                    )
                if quote_result.verification_rate < 0.5 and quote_result.total_quotes > 0:
                    metadata.review_reasons.append(
                        f"Low quote verification: {quote_result.verification_rate:.0%}"
                    )

            # Force human review when article was truncated for verification (4A)
            if article_truncated_for_review:
                metadata.requires_human_review = True
                unverified_chars = len(generated_article) - 5000
                metadata.review_reasons.append(
                    f"Article truncated for verification: {unverified_chars} chars unverified (tail content not checked)"
                )
                logger.warning(f"Article flagged for mandatory human review due to truncation ({unverified_chars} chars unverified)")

            metadata.is_verified = True
            metadata.enrichment_used = bool(enrichment and enrichment.success)

            # Truncation metadata (4A) — limits: source=8000, article=5000
            metadata.truncation = {
                "source_truncated": len(texto_base.strip()) > 8000,
                "article_truncated": len(generated_article.strip()) > 5000,
                "unverified_chars": max(0, len(generated_article.strip()) - 5000),
            }

        except Exception as e:
            logger.error(f"Verification pipeline failed: {e}")
            metadata.warnings.append(f"Verification error: {str(e)[:100]}")
            metadata.is_verified = False
            metadata.requires_human_review = True
            metadata.risk_level = "high"
            metadata.review_reasons.append("Verification pipeline error")

        metadata.verification_duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"Verification complete: score={metadata.confidence_score:.3f}, "
            f"risk={metadata.risk_level}, duration={metadata.verification_duration_ms}ms"
        )
        return metadata

    # =========================================================================
    # Claim Extraction & Grounding
    # =========================================================================

    async def _extract_and_verify_claims(
        self,
        texto_base: str,
        generated_article: str,
        enrichment: Optional[EnrichmentContext] = None
    ) -> list:
        """
        Extract factual claims from generated article and verify against source.

        Uses 1 LLM call for extraction + grounding.
        """
        try:
            llm = self._get_llm()

            # Build verification context - enrichment as AUTHORIZED MATERIAL
            source_context = texto_base
            enrichment_section = ""
            if enrichment and enrichment.success:
                enrichment_parts = []
                if enrichment.key_facts:
                    facts_text = "\n".join(f"- {f}" for f in enrichment.key_facts)
                    enrichment_parts.append(f"FATOS VERIFICADOS por fontes externas:\n{facts_text}")
                    source_context += f"\n\nFATOS VERIFICADOS (fontes externas):\n{facts_text}"
                if enrichment.context_text:
                    ctx_budget = 3000 if not enrichment.key_facts else 2000
                    enrichment_parts.append(f"CONTEXTO BRUTO de fontes externas:\n{enrichment.context_text[:ctx_budget]}")
                    if not enrichment.key_facts:
                        source_context += f"\n\nCONTEXTO DE FONTES EXTERNAS (material bruto):\n{enrichment.context_text[:ctx_budget]}"
                if enrichment_parts:
                    enrichment_section = "\n\n".join(enrichment_parts)

            # Truncation warning (4A) — increased limits for better verification coverage
            source_for_verification = texto_base[:8000]
            article_for_verification = generated_article[:5000]
            article_truncated_for_review = False
            if len(texto_base) > 8000:
                logger.warning(f"Source truncated for verification: {len(texto_base)} -> 8000 chars")
            if len(generated_article) > 5000:
                logger.warning(f"Article truncated for verification: {len(generated_article)} -> 5000 chars ({len(generated_article)-5000} chars unverified)")
                article_truncated_for_review = True

            system = ("Voce e um verificador factual rigoroso de artigos "
                      "jornalisticos. Seu papel e proteger o leitor contra desinformacao, "
                      "mas tambem reconhecer informacoes legitimas de fontes verificadas.")
            prompt = f"""Compare o ARTIGO GERADO com o MATERIAL AUTORIZADO (texto-fonte + contexto verificado) e verifique a fidelidade factual.

TEXTO-FONTE (material original):
{source_for_verification}

{f"MATERIAL AUTORIZADO - CONTEXTO VERIFICADO (fontes jornalisticas externas - informacoes abaixo sao VALIDAS para fundamentar o artigo):{chr(10)}{enrichment_section}" if enrichment_section else ""}

ARTIGO GERADO (para verificar):
{article_for_verification}

Extraia ate {MAX_CLAIMS} afirmacoes do artigo gerado e classifique cada uma:

Responda em JSON:
```json
{{
  "claims": [
    {{
      "text": "Afirmacao extraida do artigo",
      "verdict": "grounded|fabricated|unverifiable|inaccurate|opinion|context",
      "source_evidence": "Trecho do texto-fonte OU contexto verificado que sustenta (ou contradiz) a afirmacao",
      "source_reference": "Sentenca EXATA do material autorizado que sustenta esta afirmacao (copiar literal)",
      "category": "fact|statistic|quote|outcome|attribution|opinion"
    }}
  ]
}}
```

Regras de classificacao:
- **grounded**: Informacao factual presente no texto-fonte OU no contexto verificado acima
- **fabricated**: Informacao factual INCORRETA, DESCONEXA do tema, ou dados especificos inventados que CONTRADIZEM ou DISTORCEM os fatos (ex: inventar placar, atribuir fala a pessoa errada, criar evento que nao aconteceu)
- **inaccurate**: Informacao factual distorcida (ex: numeros errados, nomes trocados)
- **unverifiable**: Informacao factual especifica (nomes, numeros, datas, eventos concretos) que NAO aparece em NENHUM material autorizado acima E nao e conhecimento publico obvio
- **opinion**: Opiniao subjetiva, analise valorativa, previsao, enquadramento editorial ("o cenario e preocupante", "analistas esperam", "a decisao e considerada importante", "o caso ganha destaque"). NAO verificavel factualmente.
- **context**: Contexto factual que enriquece a materia: background de organizacoes, dados historicos de conhecimento publico, inferencias logicas RAZOAVEIS e DIRETAS dos fatos, descricoes fatuais corretas. DEVE ser factualmente correto.

IMPORTANTE - REGRAS DE CLASSIFICACAO:
- "fabricated" deve ser usado APENAS para informacoes que sao INCORRETAS, DESCONEXAS do tema, ou que DISTORCEM os fatos. Informacao factualmente correta que enriquece a materia com coesao tematica e "context", NAO "fabricated"
- Exemplos de "fabricated" (erros reais):
  * Inventar resultado de jogo/eleicao que nao aconteceu -> fabricated
  * Atribuir citacao a pessoa errada -> fabricated
  * Criar estatistica/numero falso -> fabricated
  * Adicionar detalhes desconexos do tema (misturar eventos diferentes) -> fabricated
- Exemplos de "opinion" (subjetivo, NAO verificavel):
  * "O cenario e preocupante" -> opinion
  * "Analistas esperam melhoras" -> opinion
  * "Isso sugere que o caso e prioritario" -> opinion
  * "A decisao pode afetar o mercado" -> opinion
  * "O tema ganha relevancia" -> opinion
  * "A medida e considerada positiva" -> opinion
  * Frases de ENQUADRAMENTO jornalistico que dao tom a materia -> opinion
- Exemplos de "context" (factual correto, enriquece materia):
  * Descrever uma organizacao mencionada na fonte ("e um dos maiores jornais") -> context
  * Contexto historico/geografico correto e relevante ao tema -> context
  * Generalizacoes fatuais de conhecimento publico ("ataques a oficiais sao raros") -> context
  * Informacao presente no CONTEXTO VERIFICADO acima (fontes externas) -> context
  * Inferencia logica DIRETA e OBVIA dos fatos na fonte -> context
- Exemplos de "unverifiable" (RESTRITO - usar com parcimonia):
  * Numeros, datas ou nomes especificos que NAO aparecem em nenhum material autorizado -> unverifiable
  * Eventos concretos nao mencionados em nenhuma fonte -> unverifiable
  * NAO classificar como "unverifiable" se: a informacao e uma inferencia logica dos fatos, e opiniao/enquadramento editorial, ou e conhecimento publico basico
- PRIORIDADE DE CLASSIFICACAO: Antes de marcar como "unverifiable", verifique se a afirmacao se encaixa melhor como "opinion" (subjetiva) ou "context" (factual correta de conhecimento publico). Use "unverifiable" APENAS para dados especificos sem fonte.
- NA DUVIDA entre "context" e "unverifiable": se a informacao e factualmente plausivel, tem coesao com o tema, e nao contem dados especificos inventados, prefira "context"
- NA DUVIDA entre "opinion" e "unverifiable": se a afirmacao e subjetiva, valorativa ou de enquadramento editorial, classifique como "opinion"
- Afirmacoes "opinion" NAO contam na avaliacao de precisao factual
- Afirmacoes "context" CONTAM na avaliacao (devem ser factualmente corretas)"""

            response_text = await llm.call_api(system, prompt, 4096, task_type='claim_extraction')

            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start == -1 or json_end <= json_start:
                logger.warning("Claim extraction: no JSON found in response")
                return []

            try:
                data = json.loads(response_text[json_start:json_end])
            except json.JSONDecodeError as je:
                # Retry with repaired JSON (common when max_tokens truncates output)
                logger.warning(f"Claim extraction JSON parse failed, attempting repair: {je}")
                try:
                    from services.llm_service import repair_json
                    repaired = repair_json(response_text[json_start:json_end])
                    data = json.loads(repaired)
                    logger.info("Claim extraction JSON repaired successfully")
                except Exception:
                    logger.error(f"Claim extraction JSON repair also failed")
                    return []

            claims = []
            for c in data.get("claims", [])[:MAX_CLAIMS]:
                # Backwards compat: map legacy "editorial" to "context"
                verdict = c.get("verdict", "unverifiable")
                if verdict == "editorial":
                    verdict = "context"
                claims.append(ExtractedClaim(
                    text=c.get("text", ""),
                    verdict=verdict,
                    source_evidence=c.get("source_evidence", ""),
                    source_reference=c.get("source_reference", ""),
                    category=c.get("category", "fact"),
                ))

            return claims

        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            return []

    # =========================================================================
    # Entity Comparison (pure regex, no API calls)
    # =========================================================================

    def _compare_entities(self, texto_base: str, generated_article: str,
                          enrichment_context: str = "") -> EntityComparisonResult:
        """
        Compare named entities between source and generated article.

        Uses regex patterns with substring and abbreviation matching.
        Enrichment context entities are treated as legitimate source entities.
        No API calls needed.
        """
        result = EntityComparisonResult()

        # Combine source + enrichment for entity extraction (enrichment entities are legitimate)
        combined_source = texto_base
        if enrichment_context:
            combined_source = texto_base + "\n" + enrichment_context
        source_entities = self._extract_entities_regex(combined_source)
        output_entities = self._extract_entities_regex(generated_article)

        result.source_entities = list(source_entities)
        result.output_entities = list(output_entities)

        # Normalize for comparison
        source_normalized = {self._normalize(e) for e in source_entities}
        output_normalized = {self._normalize(e) for e in output_entities}

        # Exact match
        common = source_normalized & output_normalized

        # Substring matching: "Lula" matches "Luiz Inacio Lula da Silva"
        remaining_output = output_normalized - common
        remaining_source = source_normalized - common
        substring_matched = set()
        for out_ent in remaining_output:
            for src_ent in remaining_source:
                if len(out_ent) >= 3 and len(src_ent) >= 3:
                    if out_ent in src_ent or src_ent in out_ent:
                        substring_matched.add(out_ent)
                        break

        # Abbreviation matching: "STF" matches "Supremo Tribunal Federal"
        abbreviation_matched = set()
        for out_ent in (remaining_output - substring_matched):
            for src_ent in remaining_source:
                if self._is_abbreviation_match(out_ent, src_ent):
                    abbreviation_matched.add(out_ent)
                    break
        for src_ent in remaining_source:
            for out_ent in (remaining_output - substring_matched - abbreviation_matched):
                if self._is_abbreviation_match(src_ent, out_ent):
                    abbreviation_matched.add(out_ent)
                    break

        all_matched = common | substring_matched | abbreviation_matched
        novel = output_normalized - all_matched

        # Filter out known false-positive novel entities:
        # - TMC boilerplate (CTA text, brand mentions)
        # - Common PT-BR generic words that regex picks up as entities
        # - Common news source names injected by enrichment/CTA
        _NOVEL_ENTITY_STOPWORDS = {
            # TMC boilerplate / CTA
            "tmc", "brasil", "siga a tmc", "whatsapp",
            # News sources
            "globo", "estadao", "folha", "uol", "cnn", "g1", "infomoney",
            "extra", "correio", "reuters", "bloomberg", "agencia brasil",
            # Common generic words picked up by regex
            "pressao", "impacto", "creio", "amizade", "sincerao", "vitima",
            "motociclistas", "estatisticas", "especialistas", "publico",
            "taxas", "titulos", "rivais", "emprestimo", "paulo",
            "crescimento", "queda", "alta", "baixa", "mercado", "investidores",
            "analistas", "governo", "presidente", "ministro", "senado",
            "congresso", "camara", "economia", "inflacao", "juros",
            "campeonato", "temporada", "rodada", "classico", "gol",
            "jogador", "tecnico", "selecao", "copa", "mundial",
            "defesa", "ataque", "preparacao", "classificacao",
            # Common enrichment-injected context words
            "cenario", "contexto", "perspectiva", "expectativa",
            "movimentacao", "negociacao", "operacao", "transacao",
            "regiao", "setor", "area", "segmento",
        }
        novel = {e for e in novel if e.lower() not in _NOVEL_ENTITY_STOPWORDS and len(e) > 2}

        result.common_entities = list(all_matched)[:20]
        result.novel_entities = list(novel)[:20]

        # Jaccard overlap using enhanced matching
        union = source_normalized | output_normalized
        result.overlap_score = len(all_matched) / max(len(union), 1)

        return result

    def _is_abbreviation_match(self, abbrev: str, full_name: str) -> bool:
        """Check if abbrev is an abbreviation of full_name or vice-versa."""
        # Check known abbreviation map
        if abbrev in self._ABBREVIATION_MAP:
            if self._ABBREVIATION_MAP[abbrev] in full_name or full_name in self._ABBREVIATION_MAP[abbrev]:
                return True
        if full_name in self._ABBREVIATION_MAP:
            if self._ABBREVIATION_MAP[full_name] in abbrev or abbrev in self._ABBREVIATION_MAP[full_name]:
                return True

        # Heuristic: check if uppercase letters of full_name form the abbreviation
        if len(abbrev) <= 6 and abbrev.replace(" ", "").isalpha():
            words = full_name.split()
            # Skip small connector words
            skip = {"de", "da", "do", "dos", "das", "e", "para", "em", "com", "por", "o", "a", "os", "as"}
            initials = "".join(w[0] for w in words if w not in skip and len(w) > 1)
            if initials == abbrev:
                return True

        return False

    # Portuguese stopwords that get falsely detected as named entities
    _ENTITY_STOPWORDS = {
        # Prepositions / articles / conjunctions
        "segundo", "como", "durante", "formado", "composto", "apos", "sobre",
        "ainda", "mais", "outros", "entre", "tambem", "desde", "antes", "depois",
        "quando", "onde", "porque", "porem", "assim", "apenas", "cerca", "foram",
        "seria", "sendo", "feito", "tendo", "todas", "todos", "toda", "cada",
        "muito", "pouco", "outro", "outra", "algumas", "alguns", "essa", "esse",
        "esta", "este", "pelo", "pela", "pelos", "pelas", "numa", "neste",
        "nesta", "desta", "deste", "aquele", "aquela",
        # Common verbs / adverbs that appear capitalized at sentence start
        "pode", "deve", "seria", "estava", "estao", "esteve", "ficou", "disse",
        "afirmou", "declarou", "segundo", "conforme", "enquanto", "embora",
        "portanto", "entretanto", "contudo", "todavia", "inclusive", "sobretudo",
        "principalmente", "praticamente", "atualmente", "recentemente",
        # Common nouns that appear capitalized at start of sentence
        "governo", "estado", "pais", "cidade", "empresa", "grupo", "parte",
        "caso", "forma", "meio", "modo", "area", "fonte", "dados", "acordo",
        "medida", "projeto", "plano", "programa", "processo", "relacao",
        "situacao", "condicao", "resultado", "informacao", "decisao",
        # Common journalistic filler
        "neste", "nesta", "nesse", "nessa", "deste", "desta", "desse", "dessa",
        "aqui", "ali", "agora", "hoje", "ontem", "amanha", "semana", "ano",
        # Extra verbs, adverbs, common nouns (v3 expansion)
        "quanto", "qual", "quais", "alem", "contra", "trata", "diz", "mostra",
        "segue", "ocorreu", "houve", "permite", "garante", "busca", "visa",
    }

    # Known abbreviation → full name mappings for Brazilian entities
    _ABBREVIATION_MAP = {
        "stf": "supremo tribunal federal",
        "stj": "superior tribunal de justica",
        "tse": "tribunal superior eleitoral",
        "tcu": "tribunal de contas da uniao",
        "pf": "policia federal",
        "prf": "policia rodoviaria federal",
        "mpf": "ministerio publico federal",
        "cgu": "controladoria-geral da uniao",
        "bc": "banco central",
        "bcb": "banco central do brasil",
        "pib": "produto interno bruto",
        "ipca": "indice de precos ao consumidor amplo",
        "selic": "taxa selic",
        "inss": "instituto nacional do seguro social",
        "sus": "sistema unico de saude",
        "onu": "organizacao das nacoes unidas",
        "otan": "organizacao do tratado do atlantico norte",
        "eua": "estados unidos",
        "ue": "uniao europeia",
        "cbf": "confederacao brasileira de futebol",
        "conmebol": "confederacao sul-americana de futebol",
        "fifa": "federacao internacional de futebol",
        "cpi": "comissao parlamentar de inquerito",
        "pl": "projeto de lei",
        "pec": "proposta de emenda constitucional",
        "pt": "partido dos trabalhadores",
        "mdb": "movimento democratico brasileiro",
        "psdb": "partido da social democracia brasileira",
    }

    # Known names that should never be filtered by the sentence-start heuristic
    _ENTITY_KNOWN_NAMES = {
        "lula", "bolsonaro", "musk", "trump", "biden", "neymar", "mbappe",
        "putin", "zelensky", "macron", "haddad", "campos", "tarcisio",
    }

    def _extract_entities_regex(self, text: str) -> set:
        """
        Extract named entities using regex patterns.

        Captures: proper nouns, organizations, numbers, dates, acronyms.
        Filters out Portuguese stopwords, sentence starters, and fragments.
        """
        entities = set()

        # Split text into sentences for sentence-start detection
        sentences = re.split(r'[.!?]\s+', text)
        sentence_starters = set()
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                first_word = sentence.split()[0] if sentence.split() else ""
                if first_word:
                    sentence_starters.add(self._normalize(first_word))

        # Capitalized multi-word names (e.g., "Jair Bolsonaro", "Supremo Tribunal Federal")
        for match in re.finditer(r'\b([A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ][a-záàâãéèêíóòôõúç]+(?:\s+(?:de|da|do|dos|das|e|para|em|com|por)?\s*[A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ][a-záàâãéèêíóòôõúç]+)*)\b', text):
            name = match.group(1).strip()
            name_normalized = self._normalize(name)

            # Filter: reject fragments < 3 chars
            if len(name) < 3:
                continue

            # Filter: require 2+ words or be specific (4+ chars)
            if len(name.split()) < 2 and len(name) < 4:
                continue

            # Filter: stopwords
            if name_normalized in self._ENTITY_STOPWORDS:
                continue

            # Filter: single-word entities that are sentence starters
            # (likely generic nouns capitalized at start of sentence)
            # Skip filter for known names (e.g., "Lula", "Trump")
            if len(name.split()) == 1 and name_normalized in sentence_starters:
                if name_normalized not in self._ENTITY_KNOWN_NAMES:
                    # Only filter if the word doesn't also appear capitalized mid-sentence
                    mid_sentence_pattern = r'[a-záàâãéèêíóòôõúç]\s+' + re.escape(name) + r'\b'
                    if not re.search(mid_sentence_pattern, text):
                        continue

            entities.add(name)

        # Hyphenated proper nouns: "Al-Assad", "Minas-Gerais"
        for match in re.finditer(r'\b([A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ][a-záàâãéèêíóòôõúç]*(?:-[A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ][a-záàâãéèêíóòôõúç]+)+)\b', text):
            name = match.group(1)
            if len(name) >= 4 and self._normalize(name) not in self._ENTITY_STOPWORDS:
                entities.add(name)

        # All-caps multi-word: "VINI JR", "NATO OTAN"
        for match in re.finditer(r'\b([A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ]{2,}(?:\s+[A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ]{2,})+)\b', text):
            name = match.group(1)
            if len(name) >= 4 and self._normalize(name) not in self._ENTITY_STOPWORDS:
                entities.add(name)

        # Names with particles: "Mohammed bin Salman", "Ludwig van Beethoven"
        for match in re.finditer(r'\b([A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ][a-záàâãéèêíóòôõúç]+(?:\s+(?:bin|van|von|al|el|ibn|ben|di|du|de|da)\s+[A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ][a-záàâãéèêíóòôõúç]+)+)\b', text):
            name = match.group(1)
            if len(name) >= 4 and self._normalize(name) not in self._ENTITY_STOPWORDS:
                entities.add(name)

        # Acronyms (PF, STF, PIB, etc.)
        for match in re.finditer(r'\b([A-Z]{2,6})\b', text):
            entities.add(match.group(1))

        # Monetary values
        for match in re.finditer(r'R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es|trilh[oõ]es))?', text):
            entities.add(match.group(0).strip())

        # Percentages
        for match in re.finditer(r'\d+[.,]?\d*\s*%', text):
            entities.add(match.group(0).strip())

        # Dates (various formats)
        for match in re.finditer(r'\d{1,2}\s+de\s+\w+(?:\s+de\s+\d{4})?', text):
            entities.add(match.group(0).strip())

        return entities

    def _normalize(self, entity: str) -> str:
        """Normalize entity for comparison (lowercase, strip accents)."""
        import unicodedata
        text = entity.lower().strip()
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = re.sub(r'\s+', ' ', text)
        return text

    # =========================================================================
    # TF-IDF Claim-Source Similarity (pure computation, no API calls)
    # =========================================================================

    # Portuguese stopwords for TF-IDF (improves signal-to-noise ratio)
    _PT_STOPWORDS = {
        "que", "nao", "para", "por", "com", "uma", "mas", "dos", "das",
        "mais", "como", "foi", "tem", "ser", "seu", "sua", "sao", "nos",
        "ele", "ela", "isso", "este", "esta", "entre", "tambem", "apos",
        "sobre", "quando", "muito", "ainda", "mesmo", "pode", "seus",
        "suas", "cada", "desde", "ate", "aqui", "havia", "onde", "pelo",
        "pela", "eram", "esse", "essa", "esses", "essas", "num",
        "numa", "pelos", "pelas", "algum", "alguma", "outros", "outras",
    }

    @staticmethod
    def _pt_stem(word: str) -> str:
        """Basic Portuguese suffix removal (not full Snowball, just common suffixes)."""
        for suffix in ("mente", "acao", "agem", "ando", "endo", "indo",
                       "aram", "eram", "iram", "ados", "idos", "veis"):
            if len(word) > len(suffix) + 3 and word.endswith(suffix):
                return word[:-len(suffix)]
        for suffix in ("ar", "er", "ir", "ou", "am", "em"):
            if len(word) > len(suffix) + 4 and word.endswith(suffix):
                return word[:-len(suffix)]
        return word

    @staticmethod
    def _compute_claim_source_similarity(
        claims: list,
        source_text: str,
        enrichment_text: str = ""
    ) -> list:
        """
        Compute TF-IDF cosine similarity between each claim and best source sentence.

        Pure computation, zero API calls. Uses Portuguese stopwords and basic stemming.
        Returns list of floats [0,1].
        """
        if not claims or not source_text:
            return []

        # Combine sources
        full_source = source_text
        if enrichment_text:
            full_source += " " + enrichment_text

        # Split source into sentences
        sentences = re.split(r'[.!?]\s+', full_source)
        sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 10]
        if not sentences:
            return [0.0] * len(claims)

        # Tokenize with Portuguese stopwords and basic stemming
        pt_stops = FactCheckService._PT_STOPWORDS
        pt_stem = FactCheckService._pt_stem

        def tokenize(text):
            words = re.findall(r'\b\w{2,}\b', text.lower())
            return [pt_stem(w) for w in words if w not in pt_stops]

        sentence_tokens = [tokenize(s) for s in sentences]

        # Build vocabulary and IDF
        all_docs = sentence_tokens[:]
        vocab = set()
        for doc in all_docs:
            vocab.update(doc)

        doc_count = len(all_docs)
        df = Counter()
        for doc in all_docs:
            for word in set(doc):
                df[word] += 1

        idf = {}
        for word in vocab:
            idf[word] = math.log((doc_count + 1) / (df[word] + 1)) + 1

        def tfidf_vector(tokens):
            tf = Counter(tokens)
            total = len(tokens) if tokens else 1
            vec = {}
            for word in set(tokens):
                vec[word] = (tf[word] / total) * idf.get(word, 1.0)
            return vec

        def cosine_sim(v1, v2):
            common = set(v1.keys()) & set(v2.keys())
            if not common:
                return 0.0
            dot = sum(v1[w] * v2[w] for w in common)
            norm1 = math.sqrt(sum(v ** 2 for v in v1.values()))
            norm2 = math.sqrt(sum(v ** 2 for v in v2.values()))
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot / (norm1 * norm2)

        # Pre-compute sentence vectors
        sent_vectors = [tfidf_vector(tokens) for tokens in sentence_tokens]

        # For each claim, compute max similarity with any sentence
        similarities = []
        for claim in claims:
            claim_text = claim.text if isinstance(claim, ExtractedClaim) else claim.get("text", "")
            claim_tokens = tokenize(claim_text)
            if not claim_tokens:
                similarities.append(0.0)
                continue
            claim_vec = tfidf_vector(claim_tokens)
            max_sim = max(cosine_sim(claim_vec, sv) for sv in sent_vectors) if sent_vectors else 0.0
            similarities.append(round(max_sim, 4))

        return similarities

    @staticmethod
    def _fill_source_references(
        claims: list,
        source_text: str,
        enrichment_text: str = ""
    ):
        """
        Fill in missing source_reference for claims using TF-IDF best sentence match.

        Modifies claims in-place. Only fills when source_reference is empty.
        """
        if not claims or not source_text:
            return

        full_source = source_text
        if enrichment_text:
            full_source += " " + enrichment_text

        sentences = re.split(r'[.!?]\s+', full_source)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if not sentences:
            return

        pt_stops = FactCheckService._PT_STOPWORDS
        pt_stem = FactCheckService._pt_stem

        def tokenize(text):
            words = re.findall(r'\b\w{2,}\b', text.lower())
            return [pt_stem(w) for w in words if w not in pt_stops]

        # Simple word overlap for speed (no full TF-IDF needed for reference matching)
        sent_token_sets = [set(tokenize(s)) for s in sentences]

        for claim in claims:
            if isinstance(claim, ExtractedClaim):
                if claim.source_reference:
                    continue  # Already filled by LLM
                claim_tokens = set(tokenize(claim.text))
                if not claim_tokens:
                    continue
                best_idx = 0
                best_overlap = 0.0
                for i, sent_tokens in enumerate(sent_token_sets):
                    if not sent_tokens:
                        continue
                    overlap = len(claim_tokens & sent_tokens) / len(claim_tokens)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_idx = i
                if best_overlap > 0.2:
                    claim.source_reference = sentences[best_idx]

    # =========================================================================
    # Quote Verification (string matching, no API calls)
    # =========================================================================

    def _verify_quotes(
        self,
        generated_article: str,
        texto_base: str,
        citacoes: Optional[list] = None
    ) -> QuoteVerificationResult:
        """
        Verify quoted text in generated article against sources.

        Uses dynamic thresholds, LCS matching, and position-aware search.
        No API calls needed.
        """
        result = QuoteVerificationResult()

        # Extract quotes from generated article
        quote_patterns = [
            r'"([^"]{10,})"',           # "quoted text"
            r'\u201c([^\u201d]{10,})\u201d',  # "quoted text" (smart quotes)
            r"'([^']{10,})'",           # 'quoted text'
        ]

        generated_quotes = set()
        for pattern in quote_patterns:
            for match in re.finditer(pattern, generated_article):
                generated_quotes.add(match.group(1).strip())

        result.total_quotes = len(generated_quotes)
        if result.total_quotes == 0:
            # Neutral default: no quotes = not a problem, score 0.5 (not 1.0 or 0.0)
            result.verification_rate = 0.5
            return result

        # Build reference text pool
        reference_text = texto_base.lower()
        if citacoes:
            reference_text += " " + " ".join(c.lower() for c in citacoes)

        # Split reference into paragraphs for position-aware matching
        ref_paragraphs = [p.lower() for p in texto_base.split("\n") if p.strip()]

        verified = 0
        for quote in generated_quotes:
            quote_lower = quote.lower()
            quote_words = quote_lower.split()
            num_words = len(quote_words)

            # Dynamic threshold: shorter quotes need higher overlap
            if num_words <= 8:
                word_threshold = 0.70  # Short quotes: strict
            elif num_words <= 20:
                word_threshold = 0.50  # Medium quotes: moderate
            else:
                word_threshold = 0.40  # Long quotes: relaxed

            # Method 1: Word overlap with dynamic threshold
            if num_words > 0:
                ref_words = set(reference_text.split())
                word_overlap = len(set(quote_words) & ref_words) / num_words
                if word_overlap >= word_threshold:
                    verified += 1
                    continue

            # Method 2: Position-aware paragraph search
            para_matched = False
            for para in ref_paragraphs:
                if len(para) > 10:
                    para_words = set(para.split())
                    if num_words > 0:
                        overlap = len(set(quote_words) & para_words) / num_words
                        if overlap >= word_threshold + 0.1:  # Slightly stricter for paragraph match
                            para_matched = True
                            break
            if para_matched:
                verified += 1
                continue

            # Method 3: LCS (Longest Common Subsequence) matching for paraphrases
            lcs_ratio = self._lcs_ratio(quote_lower, reference_text)
            if lcs_ratio >= 0.50:
                verified += 1
                continue

            # Method 4: Substring chunk matching (original fallback)
            found = False
            chunk_size = min(20, len(quote_lower) - 5)
            if chunk_size > 10:
                for i in range(0, len(quote_lower) - chunk_size, 5):
                    chunk = quote_lower[i:i + chunk_size]
                    if chunk in reference_text:
                        found = True
                        break
            if found:
                verified += 1
            else:
                result.unverified_quotes.append(quote[:100])

        result.verified_quotes = verified
        result.verification_rate = verified / max(result.total_quotes, 1)

        return result

    @staticmethod
    def _lcs_ratio(s1: str, s2: str) -> float:
        """
        Compute LCS length ratio between s1 and the best matching window in s2.

        For efficiency, uses a sliding window approach: checks s2 windows of
        len(s1)*2 and computes LCS against s1. Returns ratio = LCS / len(s1).
        """
        if not s1 or not s2:
            return 0.0

        s1_words = s1.split()
        s2_words = s2.split()
        n = len(s1_words)

        if n == 0:
            return 0.0

        # Sliding window on s2 for efficiency
        window_size = min(n * 3, len(s2_words))
        best_ratio = 0.0

        step = max(1, n // 2)
        for start in range(0, max(1, len(s2_words) - window_size + 1), step):
            window = s2_words[start:start + window_size]
            lcs_len = _lcs_length(s1_words, window)
            ratio = lcs_len / n
            if ratio > best_ratio:
                best_ratio = ratio
                if best_ratio >= 0.7:  # Early exit for strong matches
                    break

        return best_ratio

    # =========================================================================
    # Chain-of-Verification (CoVe) - Phase 2
    # =========================================================================

    async def _cove_verify_claims(
        self,
        claims: list,
        source_text: str,
        enrichment: Optional[EnrichmentContext] = None
    ) -> tuple:
        """
        Apply Chain-of-Verification to fabricated claims.

        Only processes claims with verdict "fabricated" to minimize LLM costs.
        For each fabricated claim, generates verification questions, answers
        them from source material, and re-classifies.

        Returns:
            Tuple of (updated_claims, cove_results, reclassified_count)
        """
        if not COVE_ENABLED:
            return claims, [], 0

        fabricated = [
            (i, c) for i, c in enumerate(claims)
            if (isinstance(c, ExtractedClaim) and c.verdict == "fabricated")
            or (isinstance(c, dict) and c.get("verdict") == "fabricated")
        ]

        if not fabricated:
            logger.info("CoVe: no fabricated claims, skipping (0 LLM calls)")
            return claims, [], 0

        # Limit to COVE_MAX_CLAIMS to control cost
        fabricated = fabricated[:COVE_MAX_CLAIMS]
        logger.info(f"CoVe: verifying {len(fabricated)} fabricated claims")

        # Build enrichment context
        enrichment_text = ""
        if enrichment and enrichment.success:
            if enrichment.key_facts:
                enrichment_text = "\n".join(f"- {f}" for f in enrichment.key_facts)
            elif enrichment.context_text:
                enrichment_text = enrichment.context_text[:3000]

        cove_results = []
        reclassified = 0

        # Run all claim verifications in parallel
        cove_tasks = [
            self._cove_single_claim(claim, source_text, enrichment_text)
            for _idx, claim in fabricated
        ]
        results = await asyncio.gather(*cove_tasks, return_exceptions=True)

        for (idx, claim), result in zip(fabricated, results):
            if isinstance(result, Exception):
                logger.warning(f"CoVe failed for claim (non-blocking): {result}")
                continue
            cove_results.append(result)

            if result.final_verdict != "fabricated":
                # Reclassify the claim
                reclassified += 1
                if isinstance(claim, ExtractedClaim):
                    claims[idx] = ExtractedClaim(
                        text=claim.text,
                        verdict=result.final_verdict,
                        source_evidence=claim.source_evidence + " [CoVe reclassified]",
                        category=claim.category,
                    )
                elif isinstance(claim, dict):
                    claims[idx] = {
                        **claim,
                        "verdict": result.final_verdict,
                        "source_evidence": claim.get("source_evidence", "") + " [CoVe reclassified]",
                    }
                logger.info(
                    f"CoVe reclassified: '{claim.text[:60] if isinstance(claim, ExtractedClaim) else claim.get('text', '')[:60]}...' "
                    f"fabricated -> {result.final_verdict}"
                )

        logger.info(f"CoVe complete: {reclassified}/{len(fabricated)} reclassified")
        return claims, cove_results, reclassified

    async def _cove_single_claim(
        self,
        claim,
        source_text: str,
        enrichment_text: str
    ) -> CoVeVerification:
        """
        Apply CoVe to a single fabricated claim using 2 isolated LLM calls.

        Call 1: Generate verification questions and answer from source material only.
        Call 2: Re-classify the claim based on Q&A (does not see the source directly,
                preventing confirmation bias).
        """
        claim_text = claim.text if isinstance(claim, ExtractedClaim) else claim.get("text", "")

        result = CoVeVerification(
            original_claim=claim_text,
            original_verdict="fabricated",
        )

        llm = self._get_llm()

        # ---- Call 1: Q&A only (no verdict) ----
        system_qa = (
            "Voce e um verificador factual. Gere perguntas de verificacao "
            "e responda APENAS com base no material fornecido."
        )
        prompt_qa = f"""Gere {COVE_QUESTIONS_PER_CLAIM} perguntas de verificacao sobre a seguinte afirmacao e responda cada uma usando APENAS o material abaixo.

AFIRMACAO:
"{claim_text}"

TEXTO-FONTE:
{source_text[:4000]}

{f"CONTEXTO VERIFICADO:{chr(10)}{enrichment_text[:2000]}" if enrichment_text else ""}

Responda em JSON:
```json
{{
  "questions": ["Pergunta 1?", "Pergunta 2?", "Pergunta 3?"],
  "answers": ["Resposta baseada no material 1", "Resposta 2", "Resposta 3"]
}}
```

NAO classifique. Apenas gere perguntas e respostas factuais."""

        qa_response = await llm.call_api(system_qa, prompt_qa, 768, task_type='cove_qa')
        qa_data = self._parse_json_response(qa_response)

        if qa_data:
            result.questions = qa_data.get("questions", [])
            result.answers = qa_data.get("answers", [])

        # ---- Call 2: Verdict only (receives Q&A, does not see source directly) ----
        qa_summary = ""
        for i, (q, a) in enumerate(zip(result.questions, result.answers), 1):
            qa_summary += f"P{i}: {q}\nR{i}: {a}\n"

        system_verdict = (
            "Voce e um classificador factual. Re-classifique a afirmacao "
            "com base APENAS nas perguntas e respostas fornecidas."
        )
        prompt_verdict = f"""Re-classifique a seguinte afirmacao com base nas perguntas e respostas de verificacao.

AFIRMACAO SUSPEITA:
"{claim_text}"

PERGUNTAS E RESPOSTAS DE VERIFICACAO:
{qa_summary}

Responda em JSON:
```json
{{
  "final_verdict": "grounded|context|opinion|unverifiable|fabricated",
  "reasoning": "Breve explicacao da decisao",
  "evidence_strength": "strong|moderate|weak"
}}
```

Regras:
- **grounded**: Respostas confirmam que a informacao esta nas fontes
- **context**: Contexto factual correto que enriquece a materia (background, dados publicos)
- **opinion**: Opiniao subjetiva, analise valorativa, previsao - nao verificavel factualmente
- **unverifiable**: Impossivel confirmar nem negar
- **fabricated**: Respostas confirmam que a informacao e INCORRETA ou DESCONEXA"""

        verdict_response = await llm.call_api(system_verdict, prompt_verdict, 512, task_type='cove_verdict')
        verdict_data = self._parse_json_response(verdict_response)

        if verdict_data:
            result.final_verdict = verdict_data.get("final_verdict", "fabricated")
            result.evidence_strength = verdict_data.get("evidence_strength", "weak")
            # Proportional confidence delta based on evidence strength
            if result.final_verdict != "fabricated":
                result.confidence_delta = self._EVIDENCE_DELTA_MAP.get(
                    result.evidence_strength, 0.02
                )
            else:
                result.confidence_delta = 0.0

        return result

    # =========================================================================
    # Confidence Scoring
    # =========================================================================

    def _compute_confidence(
        self,
        metadata: VerificationMetadata,
        entity_result: EntityComparisonResult,
        quote_result: QuoteVerificationResult,
        claim_similarities: list = None
    ) -> float:
        """
        Compute composite confidence score (0-1).

        Weights:
        - Claim grounding: 40%
        - Entity overlap: 25%
        - Expansion ratio: 10%
        - Quote verification: 10%
        - Material sufficiency: 10%
        - Claim-source similarity: 5% (TF-IDF, non-LLM signal)
        """
        # Claim grounding score (excluding opinion claims; context claims ARE factual)
        # Backwards compat: also exclude legacy "editorial" verdict
        _non_factual = {"opinion", "editorial"}
        factual_claims = [c for c in metadata.claims
                         if (isinstance(c, ExtractedClaim) and c.verdict not in _non_factual)
                         or (isinstance(c, dict) and c.get("verdict") not in _non_factual)]
        num_factual = len(factual_claims)
        if num_factual > 0:
            grounded_count = sum(1 for c in factual_claims
                               if (isinstance(c, ExtractedClaim) and c.verdict == "grounded")
                               or (isinstance(c, dict) and c.get("verdict") == "grounded"))
            # Context claims are factually correct (by definition) — count at 80% weight
            # This prevents enrichment-sourced facts from tanking the grounded ratio
            context_count = sum(1 for c in factual_claims
                               if (isinstance(c, ExtractedClaim) and c.verdict == "context")
                               or (isinstance(c, dict) and c.get("verdict") == "context"))
            fabricated_count = sum(1 for c in factual_claims
                                 if (isinstance(c, ExtractedClaim) and c.verdict == "fabricated")
                                 or (isinstance(c, dict) and c.get("verdict") == "fabricated"))
            effective_grounded = grounded_count + (context_count * 0.8)
            grounded_ratio = effective_grounded / num_factual
            # Phase 2.6: Non-linear fabrication penalty
            # 1 fabricated = 0.30, 2 = 0.55, 3+ = 0.80
            if fabricated_count == 0:
                fabrication_penalty = 0.0
            elif fabricated_count == 1:
                fabrication_penalty = 0.30
            elif fabricated_count == 2:
                fabrication_penalty = 0.55
            else:
                fabrication_penalty = 0.80
            claim_score = max(0, grounded_ratio - fabrication_penalty)
        else:
            # Empty claims fallback (4B): penalize if extraction failed
            if metadata.claim_extraction_failed:
                config = get_config()
                if config.production_safety_mode:
                    # In production, zero verification = hard block
                    claim_score = 0.0
                    logger.warning("Claim extraction failed in production mode - setting claim_score=0.0 for hard block")
                else:
                    claim_score = 0.35  # pessimistic, not neutral
                metadata.risk_level = "high"
                metadata.requires_human_review = True
                if "Claim extraction failed — zero claims extracted" not in metadata.review_reasons:
                    metadata.review_reasons.append("Claim extraction failed — zero claims extracted")
            else:
                claim_score = 0.5  # No claims = uncertain

        # Entity overlap score (floor 0.3 when enrichment provided context)
        entity_score = entity_result.overlap_score
        if metadata.enrichment_used and entity_score < 0.3:
            entity_score = 0.3  # Enriched articles legitimately introduce new entities

        # Expansion ratio score
        ratio = metadata.expansion_ratio
        if ratio <= 3:
            expansion_score = 1.0
        elif ratio <= 5:
            expansion_score = 0.8
        elif ratio <= 10:
            expansion_score = 0.5
        elif ratio <= 25:
            expansion_score = 0.2
        else:
            expansion_score = 0.0

        # Quote verification score - neutral default when no quotes
        if quote_result.total_quotes == 0:
            quote_score = 0.5  # No quotes = neutral (not 0.0 which penalizes)
        else:
            quote_score = quote_result.verification_rate

        # Material sufficiency score
        if metadata.source_sufficiency == "sufficient":
            sufficiency_score = 1.0
        elif metadata.source_sufficiency == "marginal":
            sufficiency_score = 0.5
        else:
            sufficiency_score = 0.2

        # Claim-source TF-IDF similarity score
        if claim_similarities and len(claim_similarities) > 0:
            similarity_score = sum(claim_similarities) / len(claim_similarities)
        else:
            similarity_score = 0.5  # Neutral when unavailable

        # Weighted composite
        confidence = (
            WEIGHT_CLAIM_GROUNDING * claim_score
            + WEIGHT_ENTITY_OVERLAP * entity_score
            + WEIGHT_EXPANSION_RATIO * expansion_score
            + WEIGHT_QUOTE_VERIFICATION * quote_score
            + WEIGHT_MATERIAL_SUFFICIENCY * sufficiency_score
            + WEIGHT_CLAIM_SIMILARITY * similarity_score
        )

        # CoVe bonus: proportional to evidence strength of each reclassified claim
        if metadata.cove_applied and metadata.cove_reclassified > 0:
            cove_bonus = 0.0
            for cove_result in metadata.cove_results:
                if isinstance(cove_result, CoVeVerification) and cove_result.final_verdict != "fabricated":
                    cove_bonus += self._EVIDENCE_DELTA_MAP.get(
                        cove_result.evidence_strength, 0.02
                    )
            if cove_bonus == 0.0:
                # Fallback: flat bonus if no cove_results available
                cove_bonus = 0.05 * metadata.cove_reclassified
            confidence = min(confidence + cove_bonus, 1.0)
            logger.info(f"CoVe bonus: +{cove_bonus:.2f} ({metadata.cove_reclassified} reclassified)")

        # P2-10: Expansion ratio guard - cap confidence for extreme expansion
        if ratio > 10:
            confidence = min(confidence, 0.5)
            metadata.warnings.append(
                f"Expansao {ratio:.1f}x: confianca limitada a 50% (alto risco de fabricacao)"
            )

        # Novel entity guard - penalize when many entities are new
        novel_count = len(entity_result.novel_entities)
        output_count = len(entity_result.output_entities)
        if output_count > 0 and novel_count >= 3:
            novel_pct = novel_count / output_count
            if novel_pct > 0.50:
                confidence = min(confidence, 0.55)
                metadata.warnings.append(
                    f"Entidades novas: {novel_count}/{output_count} "
                    f"({novel_pct:.0%}) - confianca limitada"
                )

        return max(0.0, min(1.0, confidence))

    def _determine_risk_level(
        self,
        metadata: VerificationMetadata,
        entity_result: EntityComparisonResult,
        quote_result: QuoteVerificationResult
    ) -> str:
        """
        Determine risk level with override rules.

        Base levels from confidence:
        - >= 0.8: low
        - >= 0.5: medium
        - >= 0.3: high
        - < 0.3: critical

        Override rules (zero tolerance for journalism):
        - ANY fabricated claim -> CRITICAL (one wrong fact destroys credibility)
        - Fabricated + low confidence -> CRITICAL
        - Expansion > 25x -> at least HIGH
        - >50% ungrounded quotes -> HIGH
        """
        score = metadata.confidence_score

        # Base level from score
        if score >= 0.8:
            level = "low"
        elif score >= 0.5:
            level = "medium"
        elif score >= 0.3:
            level = "high"
        else:
            level = "critical"

        # Override: fabricated claims escalate risk
        # NOTE: With the updated classifier, "fabricated" means genuinely incorrect
        # or thematically disconnected info (not factually correct editorial context).
        # 3+ fabricated = critical (multiple real errors)
        # 2 fabricated = high (likely real issues)
        # 1 fabricated = keep base level (may be verifier false positive)
        if metadata.fabricated_claims >= 3:
            level = "critical"
        elif metadata.fabricated_claims == 2:
            if score < 0.35:
                level = "critical"
            elif level in ("low", "medium"):
                level = "high"
        elif metadata.fabricated_claims == 1:
            # Phase 2.6: 1 fabricated + score < 0.50 → high (was 0.30)
            if score < 0.50:
                level = "high"

        # Override: extreme expansion
        if metadata.expansion_ratio > 25 and level in ("low", "medium"):
            level = "high"

        # Override: unverified quotes (only escalate when confidence is genuinely low)
        # Paraphrased or enrichment-sourced quotes often fail exact matching but
        # the article may still be well-grounded based on claims verification
        if (quote_result.total_quotes > 0
                and quote_result.verification_rate < 0.5
                and level in ("low", "medium")
                and metadata.confidence_score < 0.65):
            level = "high"

        # Override: novel entity percentage
        novel_count = len(entity_result.novel_entities)
        output_count = len(entity_result.output_entities)
        if output_count > 0 and novel_count >= 3:
            novel_pct = novel_count / output_count
            if novel_pct > 0.50 and level in ("low", "medium"):
                level = "high"
                metadata.warnings.append(
                    f"Entidades novas: {novel_count}/{output_count} "
                    f"({novel_pct:.0%}) nao presentes na fonte"
                )

        # Override: excessive unverifiable claims
        if metadata.total_claims > 0 and metadata.unverifiable_claims >= 3:
            unverifiable_pct = metadata.unverifiable_claims / metadata.total_claims
            if unverifiable_pct > 0.40 and level in ("low", "medium"):
                level = "high"

        # Override: expansion > 15x at least medium
        if metadata.expansion_ratio > 15 and level == "low":
            level = "medium"

        return level


# =============================================================================
# Singleton
# =============================================================================

import threading
_fact_check_service: Optional[FactCheckService] = None
_fact_check_service_lock = threading.Lock()


def get_fact_check_service() -> FactCheckService:
    """Get or create the FactCheckService singleton (thread-safe)."""
    global _fact_check_service
    if _fact_check_service is None:
        with _fact_check_service_lock:
            if _fact_check_service is None:
                import atexit
                _fact_check_service = FactCheckService()
                atexit.register(_cleanup_fact_check_service)
    return _fact_check_service


def _cleanup_fact_check_service():
    """Cleanup FactCheckService HTTP client on process exit."""
    global _fact_check_service
    if _fact_check_service:
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_fact_check_service.close())
            loop.close()
        except Exception:
            pass
        _fact_check_service = None


def is_fact_check_enabled() -> bool:
    """Check if fact checking is enabled."""
    return FACT_CHECK_ENABLED
