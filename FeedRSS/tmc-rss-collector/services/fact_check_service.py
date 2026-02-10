"""
Fact Check Service for TMC Article Generation

Anti-hallucination pipeline with 3 components:
1. Pre-generation enrichment via Exa web search
2. Post-generation claim verification
3. Confidence scoring and risk assessment

Verification failures NEVER block article generation - progressive degradation.
"""

import os
import re
import json
import time
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

FACT_CHECK_ENABLED = os.environ.get("FACT_CHECK_ENABLED", "true").lower() == "true"
ENRICHMENT_ENABLED = os.environ.get("FACT_CHECK_ENRICHMENT_ENABLED", "true").lower() == "true"
VERIFICATION_ENABLED = os.environ.get("FACT_CHECK_VERIFICATION_ENABLED", "true").lower() == "true"
MAX_CLAIMS = int(os.environ.get("FACT_CHECK_MAX_CLAIMS", "10"))

EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
EXA_ENDPOINT = os.environ.get("EXA_API_ENDPOINT", "https://api.exa.ai/search")
EXA_MAX_RESULTS = int(os.environ.get("EXA_MAX_RESULTS", "5"))
EXA_SEARCH_DAYS = int(os.environ.get("EXA_SEARCH_DAYS", "7"))
EXA_TIMEOUT = int(os.environ.get("EXA_TIMEOUT_SECONDS", "15"))

# Confidence scoring weights (calibrated for journalism safety)
WEIGHT_CLAIM_GROUNDING = 0.50
WEIGHT_ENTITY_OVERLAP = 0.25
WEIGHT_EXPANSION_RATIO = 0.10
WEIGHT_QUOTE_VERIFICATION = 0.05
WEIGHT_MATERIAL_SUFFICIENCY = 0.10


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ExtractedClaim:
    """Individual factual claim extracted from generated article."""
    text: str
    verdict: str = "unverifiable"  # grounded | fabricated | unverifiable | inaccurate | editorial
    source_evidence: str = ""
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
    claims: list = field(default_factory=list)
    entity_comparison: dict = field(default_factory=dict)
    quote_verification: dict = field(default_factory=dict)
    requires_human_review: bool = True
    review_reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    is_verified: bool = False
    verification_duration_ms: int = 0
    enrichment_used: bool = False

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        claims_list = []
        for c in self.claims:
            if isinstance(c, ExtractedClaim):
                claims_list.append({
                    "text": c.text,
                    "verdict": c.verdict,
                    "source_evidence": c.source_evidence,
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
            "claims": claims_list,
            "entity_comparison": self.entity_comparison,
            "quote_verification": self.quote_verification,
            "requires_human_review": self.requires_human_review,
            "review_reasons": self.review_reasons,
            "warnings": self.warnings,
            "is_verified": self.is_verified,
            "verification_duration_ms": self.verification_duration_ms,
            "enrichment_used": self.enrichment_used,
        }


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

    def _get_llm(self):
        """Lazy-load LLM service to avoid circular imports."""
        if self._llm_service is None:
            from services.llm_service import get_llm_service
            self._llm_service = get_llm_service()
        return self._llm_service

    # =========================================================================
    # Phase 1: Pre-Generation Enrichment
    # =========================================================================

    async def enrich_context(
        self,
        texto_base: str,
        titulo_fonte: Optional[str] = None,
        tags: Optional[list] = None
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

            # Collect all results, deduplicate by URL, filter non-article pages
            all_texts = []
            all_urls = set()
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
                            continue  # Skip duplicates
                        if not self._is_quality_url(url, text):
                            logger.debug(f"Filtered non-article URL: {url[:80]}")
                            filtered_count += 1
                            continue
                        if text and len(text.strip()) > 50:
                            all_texts.append(f"[{title}] {text[:max_text_chars]}")
                        if url:
                            all_urls.add(url)

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

    async def _search_exa(
        self,
        query: str,
        num_results: int = EXA_MAX_RESULTS,
        max_text: int = 2000
    ) -> list:
        """
        Execute a single Exa search.

        Args:
            query: Search query string
            num_results: Number of results to fetch
            max_text: Max characters of article text per result

        Returns list of {title, url, text, publishedDate} dicts.
        """
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

        response = await self.http_client.post(
            EXA_ENDPOINT,
            headers=headers,
            json=payload,
        )

        if response.status_code != 200:
            logger.warning(f"Exa API returned {response.status_code}: {response.text[:200]}")
            return []

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

    # URL patterns that indicate non-article pages (topic indexes, portals, docs)
    _BAD_URL_PATTERNS = [
        "/topicos/", "/folha-topicos/", "/assuntos/", "/tag/",
        "/tags/", "/categoria/", "/categorias/", "/editoria/",
        "/index.php", "/index.html",
        "/c/mundo/", "/c/brasil/",
        "blogspot.com",
        ".gov.br/",
        "/docs/", "/developers/", "/api/",
        "/acompanhamento-", "/orcamento-cidadao",
        "/transparencia.",
    ]

    def _is_quality_url(self, url: str, text: str) -> bool:
        """Filter out non-article URLs (topic pages, portals, indexes)."""
        url_lower = url.lower()

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
            response_text = await llm._call_api(system, prompt, max_tokens)

            # Try standard JSON extraction
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                try:
                    data = json.loads(response_text[json_start:json_end])
                    return data.get("key_facts", [])[:max_facts]
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

    # =========================================================================
    # Phase 3: Post-Generation Verification
    # =========================================================================

    async def verify_article(
        self,
        texto_base: str,
        generated_article: str,
        citacoes: Optional[list] = None,
        enrichment: Optional[EnrichmentContext] = None
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
        if source_len < 150:
            metadata.source_sufficiency = "insufficient"
        elif source_len < 500:
            metadata.source_sufficiency = "marginal"
        else:
            metadata.source_sufficiency = "sufficient"

        try:
            # Run 3 checks in parallel
            claim_task = self._extract_and_verify_claims(
                texto_base, generated_article, enrichment
            )
            entity_task = asyncio.to_thread(
                self._compare_entities, texto_base, generated_article
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
                # Editorial claims don't count toward factual accuracy metrics
                metadata.grounded_claims = sum(
                    1 for c in claims if c.verdict == "grounded"
                )
                metadata.fabricated_claims = sum(
                    1 for c in claims if c.verdict == "fabricated"
                )
                metadata.unverifiable_claims = sum(
                    1 for c in claims if c.verdict == "unverifiable"
                )
                editorial_count = sum(
                    1 for c in claims if c.verdict == "editorial"
                )
                if editorial_count > 0:
                    logger.info(f"Editorial claims excluded from scoring: {editorial_count}")

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

            # Compute confidence score
            metadata.confidence_score = self._compute_confidence(
                metadata, entity_result, quote_result
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

            metadata.is_verified = True
            metadata.enrichment_used = bool(enrichment and enrichment.success)

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

            # Build verification context
            source_context = texto_base
            if enrichment and enrichment.success:
                if enrichment.key_facts:
                    facts_text = "\n".join(f"- {f}" for f in enrichment.key_facts)
                    source_context += f"\n\nFATOS VERIFICADOS (fontes externas):\n{facts_text}"
                elif enrichment.context_text:
                    source_context += f"\n\nCONTEXTO DE FONTES EXTERNAS (material bruto):\n{enrichment.context_text[:2000]}"

            system = ("Voce e um verificador factual EXTREMAMENTE rigoroso de artigos "
                      "jornalisticos. Seu papel e proteger o leitor contra desinformacao. "
                      "Na duvida, erre para o lado da cautela.")
            prompt = f"""Compare o ARTIGO GERADO com o TEXTO-FONTE e verifique a fidelidade factual.

TEXTO-FONTE (material original):
{texto_base[:6000]}

ARTIGO GERADO (para verificar):
{generated_article[:3000]}

{f"CONTEXTO VERIFICADO (fontes externas):{chr(10)}{source_context[len(texto_base):]}" if enrichment and enrichment.success else ""}

Extraia ate {MAX_CLAIMS} afirmacoes do artigo gerado e classifique cada uma:

Responda em JSON:
```json
{{
  "claims": [
    {{
      "text": "Afirmacao extraida do artigo",
      "verdict": "grounded|fabricated|unverifiable|inaccurate|editorial",
      "source_evidence": "Trecho do texto-fonte que sustenta (ou contradiz) a afirmacao",
      "category": "fact|statistic|quote|outcome|attribution|opinion"
    }}
  ]
}}
```

Regras de classificacao:
- **grounded**: Informacao factual presente no texto-fonte ou contexto verificado
- **fabricated**: Informacao factual INCORRETA, DESCONEXA do tema, ou dados especificos inventados que CONTRADIZEM ou DISTORCEM os fatos (ex: inventar placar, atribuir fala a pessoa errada, criar evento que nao aconteceu)
- **inaccurate**: Informacao factual distorcida (ex: numeros errados, nomes trocados)
- **unverifiable**: Informacao factual impossivel de confirmar com o material disponivel
- **editorial**: Inclui TODAS as seguintes situacoes:
  1. Opinioes, analises, previsoes ou comentarios editoriais ("o cenario e preocupante", "analistas esperam melhoras")
  2. Contexto factual correto que ENRIQUECE a materia com coesao tematica, mesmo que nao esteja nas fontes (ex: "O Kommersant e um dos principais jornais da Russia", "tentativas de assassinato contra oficiais de inteligencia sao raras")
  3. Inferencias logicas razoaveis baseadas nos fatos apresentados (ex: "a detencao rapida sugere que o caso e prioritario")
  4. Background factual de conhecimento publico que contextualiza a noticia

IMPORTANTE - REGRAS DE CLASSIFICACAO:
- "fabricated" deve ser usado APENAS para informacoes que sao INCORRETAS, DESCONEXAS do tema, ou que DISTORCEM os fatos. Informacao factualmente correta que enriquece a materia com coesao tematica e "editorial", NAO "fabricated"
- Exemplos de "fabricated" (erros reais):
  * Inventar resultado de jogo/eleicao que nao aconteceu -> fabricated
  * Atribuir citacao a pessoa errada -> fabricated
  * Criar estatistica/numero falso -> fabricated
  * Adicionar detalhes desconexos do tema (misturar eventos diferentes) -> fabricated
- Exemplos de "editorial" (contexto correto, NAO fabricated):
  * Descrever uma organizacao mencionada na fonte ("e um dos maiores jornais") -> editorial
  * Analise razoavel dos fatos ("isso sugere que...") -> editorial
  * Contexto historico/geografico correto e relevante ao tema -> editorial
  * Generalizacoes fatuais de conhecimento publico ("ataques a oficiais sao raros") -> editorial
- NA DUVIDA entre "editorial" e "fabricated": se a informacao e factualmente correta e tem coesao com o tema, prefira "editorial"
- Afirmacoes editoriais NAO contam na avaliacao de precisao factual"""

            response_text = await llm._call_api(system, prompt, 2048)

            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start == -1 or json_end <= json_start:
                return []

            data = json.loads(response_text[json_start:json_end])
            claims = []
            for c in data.get("claims", [])[:MAX_CLAIMS]:
                claims.append(ExtractedClaim(
                    text=c.get("text", ""),
                    verdict=c.get("verdict", "unverifiable"),
                    source_evidence=c.get("source_evidence", ""),
                    category=c.get("category", "fact"),
                ))

            return claims

        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            return []

    # =========================================================================
    # Entity Comparison (pure regex, no API calls)
    # =========================================================================

    def _compare_entities(self, texto_base: str, generated_article: str) -> EntityComparisonResult:
        """
        Compare named entities between source and generated article.

        Uses regex patterns - no API calls needed.
        """
        result = EntityComparisonResult()

        source_entities = self._extract_entities_regex(texto_base)
        output_entities = self._extract_entities_regex(generated_article)

        result.source_entities = list(source_entities)
        result.output_entities = list(output_entities)

        # Normalize for comparison
        source_normalized = {self._normalize(e) for e in source_entities}
        output_normalized = {self._normalize(e) for e in output_entities}

        common = source_normalized & output_normalized
        novel = output_normalized - source_normalized

        result.common_entities = list(common)[:20]
        result.novel_entities = list(novel)[:20]

        # Jaccard overlap
        union = source_normalized | output_normalized
        result.overlap_score = len(common) / max(len(union), 1)

        return result

    # Portuguese stopwords that get falsely detected as named entities
    _ENTITY_STOPWORDS = {
        "segundo", "como", "durante", "formado", "composto", "apos", "sobre",
        "ainda", "mais", "outros", "entre", "tambem", "desde", "antes", "depois",
        "quando", "onde", "porque", "porem", "assim", "apenas", "cerca", "foram",
        "seria", "sendo", "feito", "tendo", "todas", "todos", "toda", "cada",
        "muito", "pouco", "outro", "outra", "algumas", "alguns", "essa", "esse",
        "esta", "este", "pelo", "pela", "pelos", "pelas", "numa", "neste",
        "nesta", "desta", "deste", "aquele", "aquela",
    }

    def _extract_entities_regex(self, text: str) -> set:
        """
        Extract named entities using regex patterns.

        Captures: proper nouns, organizations, numbers, dates, acronyms.
        Filters out Portuguese stopwords that match capitalized patterns.
        """
        entities = set()

        # Capitalized multi-word names (e.g., "Jair Bolsonaro", "Supremo Tribunal Federal")
        for match in re.finditer(r'\b([A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ][a-záàâãéèêíóòôõúç]+(?:\s+(?:de|da|do|dos|das|e|para|em|com|por)?\s*[A-ZÁÀÂÃÉÈÊÍÓÒÔÕÚÇ][a-záàâãéèêíóòôõúç]+)*)\b', text):
            name = match.group(1).strip()
            # Filter out sentence starters (require 2+ words or be specific)
            if len(name.split()) >= 2 or len(name) >= 4:
                # Filter out stopwords (case-insensitive, accent-stripped)
                name_lower = self._normalize(name)
                if name_lower not in self._ENTITY_STOPWORDS:
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
        """Normalize entity for comparison."""
        import unicodedata
        text = entity.lower().strip()
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = re.sub(r'\s+', ' ', text)
        return text

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

        Uses string matching - no API calls needed.
        """
        result = QuoteVerificationResult()

        # Extract quotes from generated article
        # Matches text between various quote styles
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
            result.verification_rate = 1.0  # No quotes = no problem
            return result

        # Build reference text pool
        reference_text = texto_base.lower()
        if citacoes:
            reference_text += " " + " ".join(c.lower() for c in citacoes)

        verified = 0
        for quote in generated_quotes:
            quote_lower = quote.lower()
            # Check for substantial overlap (at least 50% of words match)
            quote_words = set(quote_lower.split())
            ref_words = set(reference_text.split())
            if len(quote_words) > 0:
                word_overlap = len(quote_words & ref_words) / len(quote_words)
                if word_overlap >= 0.5:
                    verified += 1
                    continue

            # Check for substring match (at least 60% of quote found in source)
            found = False
            for i in range(0, len(quote_lower) - 10, 5):
                chunk = quote_lower[i:i+20]
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

    # =========================================================================
    # Confidence Scoring
    # =========================================================================

    def _compute_confidence(
        self,
        metadata: VerificationMetadata,
        entity_result: EntityComparisonResult,
        quote_result: QuoteVerificationResult
    ) -> float:
        """
        Compute composite confidence score (0-1).

        Weights:
        - Claim grounding: 50%
        - Entity overlap: 25%
        - Expansion ratio: 10%
        - Quote verification: 5%
        - Material sufficiency: 10%
        """
        # Claim grounding score (excluding editorial claims)
        factual_claims = [c for c in metadata.claims
                         if isinstance(c, ExtractedClaim) and c.verdict != "editorial"
                         or isinstance(c, dict) and c.get("verdict") != "editorial"]
        num_factual = len(factual_claims)
        if num_factual > 0:
            grounded_count = sum(1 for c in factual_claims
                               if (isinstance(c, ExtractedClaim) and c.verdict == "grounded")
                               or (isinstance(c, dict) and c.get("verdict") == "grounded"))
            fabricated_count = sum(1 for c in factual_claims
                                 if (isinstance(c, ExtractedClaim) and c.verdict == "fabricated")
                                 or (isinstance(c, dict) and c.get("verdict") == "fabricated"))
            grounded_ratio = grounded_count / num_factual
            # Penalty for fabricated claims (worse than unverifiable)
            fabrication_penalty = fabricated_count / num_factual * 0.5
            claim_score = max(0, grounded_ratio - fabrication_penalty)
        else:
            claim_score = 0.5  # No claims = uncertain

        # Entity overlap score
        entity_score = entity_result.overlap_score

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

        # Quote verification score
        quote_score = quote_result.verification_rate

        # Material sufficiency score
        if metadata.source_sufficiency == "sufficient":
            sufficiency_score = 1.0
        elif metadata.source_sufficiency == "marginal":
            sufficiency_score = 0.5
        else:
            sufficiency_score = 0.2

        # Weighted composite
        confidence = (
            WEIGHT_CLAIM_GROUNDING * claim_score
            + WEIGHT_ENTITY_OVERLAP * entity_score
            + WEIGHT_EXPANSION_RATIO * expansion_score
            + WEIGHT_QUOTE_VERIFICATION * quote_score
            + WEIGHT_MATERIAL_SUFFICIENCY * sufficiency_score
        )

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
            if score < 0.30:
                level = "high"

        # Override: extreme expansion
        if metadata.expansion_ratio > 25 and level in ("low", "medium"):
            level = "high"

        # Override: unverified quotes
        if (quote_result.total_quotes > 0
                and quote_result.verification_rate < 0.5
                and level in ("low", "medium")):
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

_fact_check_service: Optional[FactCheckService] = None


def get_fact_check_service() -> FactCheckService:
    """Get or create the FactCheckService singleton."""
    global _fact_check_service
    if _fact_check_service is None:
        _fact_check_service = FactCheckService()
    return _fact_check_service


def is_fact_check_enabled() -> bool:
    """Check if fact checking is enabled."""
    return FACT_CHECK_ENABLED
