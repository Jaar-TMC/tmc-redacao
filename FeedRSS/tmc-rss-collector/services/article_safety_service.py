"""
Article Safety Service — on-demand fact-check scanning for any article text.

Produces an Article Safety Index (ASI) from 0-100 with claim-by-claim feedback.
Independent of the generation pipeline: works on AI-generated, manually written,
or AI-edited articles.

Pipeline:
  Phase 1: Claim extraction (Haiku)
  Phase 2: Evidence gathering (Exa + Google Fact Check API, parallel)
  Phase 3: Claim verdict + severity classification (Haiku)
  Phase 4: ASI calculation (pure math)
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ========================================
# CONFIGURATION
# ========================================

GOOGLE_FACTCHECK_ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
EXA_ENDPOINT = "https://api.exa.ai/search"

FACTCHECK_DOMAINS = [
    "aosfatos.org",
    "lupa.uol.com.br",
    "boatos.org",
    "projetocomprova.com.br",
    "e-farsas.com",
    "estadao.com.br",
    "g1.globo.com",
    "checamos.afp.com",
]

SEVERITY_WEIGHTS = {"critical": 25, "high": 15, "medium": 8, "low": 3}

SAFETY_LABELS = [
    (90, "seguro"),
    (75, "confiavel"),
    (60, "atencao"),
    (40, "risco"),
    (0, "critico"),
]


# ========================================
# RESPONSE MODELS
# ========================================

class ClaimSource(BaseModel):
    domain: str = ""
    title: str = ""
    url: str = ""
    tier: int = 4
    tier_name: str = ""
    snippet: str = ""


class ExternalFactCheck(BaseModel):
    claim_text: str = ""
    rating: str = ""
    publisher: str = ""
    review_url: str = ""
    review_date: str = ""


class ScanClaim(BaseModel):
    text: str = ""
    verdict: str = "unverifiable"
    severity: str = "low"
    category: str = "fact"
    evidence: str = ""
    sources: list[ClaimSource] = Field(default_factory=list)
    external_fact_check: Optional[ExternalFactCheck] = None
    position_hint: str = ""


class SourceCredibilityReport(BaseModel):
    sources_found: int = 0
    tier_breakdown: dict = Field(default_factory=dict)
    avg_credibility: float = 0.0
    highest_tier_sources: list[str] = Field(default_factory=list)
    unknown_sources: list[str] = Field(default_factory=list)


class FactCheckScanResponse(BaseModel):
    safety_index: int = 50
    safety_label: str = "atencao"
    claims: list[ScanClaim] = Field(default_factory=list)
    total_claims: int = 0
    grounded_claims: int = 0
    fabricated_claims: int = 0
    unverifiable_claims: int = 0
    source_credibility: SourceCredibilityReport = Field(default_factory=SourceCredibilityReport)
    corroboration_score: float = 0.0
    external_fact_checks: list[ExternalFactCheck] = Field(default_factory=list)
    fact_check_matches: int = 0
    scan_duration_ms: int = 0
    scan_id: str = ""
    scanned_at: str = ""
    error: Optional[str] = None


# ========================================
# ASI CALCULATION
# ========================================

def calculate_asi(
    claims: list[ScanClaim],
    source_credibility: SourceCredibilityReport,
    corroboration_score: float,
    external_fact_checks: list[ExternalFactCheck],
) -> int:
    """
    Calculate Article Safety Index (0-100).

    Components (weights sum to 1.0):
    - Claim grounding ratio:     35%
    - Claim severity penalty:    20%
    - Source credibility:         15%
    - Corroboration score:        15%
    - External fact-check bonus:  10%
    - Opinion/context bonus:       5%
    """
    if not claims:
        return 50  # No claims = neutral

    total = len(claims)
    factual_claims = [c for c in claims if c.verdict != "opinion"]
    if not factual_claims:
        return 85  # All opinion = generally safe

    # Component 1: Claim Grounding (35%)
    grounded = sum(1 for c in factual_claims if c.verdict == "grounded")
    grounding_ratio = grounded / len(factual_claims)
    grounding_score = grounding_ratio * 100

    # Component 2: Severity-Weighted Penalty (20%)
    penalty = 0
    for c in factual_claims:
        if c.verdict in ("fabricated", "unverifiable"):
            penalty += SEVERITY_WEIGHTS.get(c.severity, 5)
    severity_score = max(0, 100 - penalty)

    # Component 3: Source Credibility (15%)
    credibility_score = source_credibility.avg_credibility * 100

    # Component 4: Corroboration (15%)
    corroboration_pct = corroboration_score * 100

    # Component 5: External Fact-Check (10%)
    contradicting = sum(
        1 for fc in external_fact_checks
        if fc.rating.lower() in ("falso", "enganoso", "distorcido", "insustentavel")
    )
    if contradicting > 0:
        factcheck_score = max(0, 100 - (contradicting * 40))
    elif len(external_fact_checks) > 0:
        factcheck_score = 100
    else:
        factcheck_score = 70  # No data = neutral

    # Component 6: Opinion/Context (5%)
    opinion_count = sum(1 for c in claims if c.verdict == "opinion")
    opinion_ratio = opinion_count / total
    opinion_score = 90 if opinion_ratio > 0.5 else 100

    # Weighted ASI
    asi = (
        grounding_score * 0.35
        + severity_score * 0.20
        + credibility_score * 0.15
        + corroboration_pct * 0.15
        + factcheck_score * 0.10
        + opinion_score * 0.05
    )

    return max(0, min(100, round(asi)))


def _get_safety_label(asi: int) -> str:
    """Map ASI score to safety label."""
    for threshold, label in SAFETY_LABELS:
        if asi >= threshold:
            return label
    return "critico"


# ========================================
# SERVICE
# ========================================

class ArticleSafetyService:
    """On-demand article safety assessment service."""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=15.0)
        self._exa_failures = 0
        self._exa_circuit_open = False
        self._exa_circuit_open_until = 0.0

    async def scan(
        self,
        article_text: str,
        article_title: str = "",
        source_urls: list = None,
        source_text: str = "",
        language: str = "pt",
        correlation_id: str = "",
    ) -> FactCheckScanResponse:
        """
        Run comprehensive article safety scan.

        Returns FactCheckScanResponse with ASI score and claim-by-claim analysis.
        """
        start_time = time.time()
        source_urls = source_urls or []

        # Strip HTML
        clean_text = _strip_html(article_text)

        max_claims = int(os.environ.get("FACT_CHECK_SCAN_MAX_CLAIMS", "15"))

        # --- Phase 1: Claim Extraction ---
        logger.info(f"[{correlation_id}] Phase 1: Extracting claims from {len(clean_text)} chars")
        raw_claims, extraction_error = await self._extract_claims(clean_text, article_title, max_claims, correlation_id)

        if not raw_claims:
            duration_ms = int((time.time() - start_time) * 1000)
            return FactCheckScanResponse(
                safety_index=50,
                safety_label="atencao",
                scan_duration_ms=duration_ms,
                scan_id=correlation_id,
                scanned_at=datetime.now(timezone.utc).isoformat(),
                error=extraction_error,
            )

        # --- Phase 2: Evidence Gathering (parallel) ---
        logger.info(f"[{correlation_id}] Phase 2: Gathering evidence for {len(raw_claims)} claims")
        evidence = await self._gather_evidence(raw_claims, language, correlation_id)

        # --- Phase 3: Verdict + Severity ---
        logger.info(f"[{correlation_id}] Phase 3: Classifying claims")
        classified_claims = await self._classify_claims(raw_claims, evidence, correlation_id)

        # --- Phase 4: ASI Calculation ---
        logger.info(f"[{correlation_id}] Phase 4: Calculating ASI")

        # Build source credibility report
        all_domains = set()
        for claim in classified_claims:
            for src in claim.sources:
                all_domains.add(src.domain)

        source_credibility = self._build_credibility_report(list(all_domains))

        # Calculate corroboration score
        factual_claims = [c for c in classified_claims if c.verdict != "opinion"]
        if factual_claims:
            corroborated = sum(1 for c in factual_claims if len(c.sources) > 0)
            corroboration_score = corroborated / len(factual_claims)
        else:
            corroboration_score = 0.0

        # Collect all external fact-checks
        all_external = evidence.get("external_factchecks", [])

        # Calculate ASI
        asi = calculate_asi(classified_claims, source_credibility, corroboration_score, all_external)
        safety_label = _get_safety_label(asi)

        duration_ms = int((time.time() - start_time) * 1000)

        # Count verdicts
        grounded = sum(1 for c in classified_claims if c.verdict == "grounded")
        fabricated = sum(1 for c in classified_claims if c.verdict == "fabricated")
        unverifiable = sum(1 for c in classified_claims if c.verdict == "unverifiable")

        logger.info(
            f"[{correlation_id}] Scan complete: ASI={asi} ({safety_label}), "
            f"{len(classified_claims)} claims, {grounded} grounded, "
            f"{fabricated} fabricated, {duration_ms}ms"
        )

        return FactCheckScanResponse(
            safety_index=asi,
            safety_label=safety_label,
            claims=classified_claims,
            total_claims=len(classified_claims),
            grounded_claims=grounded,
            fabricated_claims=fabricated,
            unverifiable_claims=unverifiable,
            source_credibility=source_credibility,
            corroboration_score=round(corroboration_score, 3),
            external_fact_checks=all_external,
            fact_check_matches=len(all_external),
            scan_duration_ms=duration_ms,
            scan_id=correlation_id,
            scanned_at=datetime.now(timezone.utc).isoformat(),
        )

    # ========================================
    # PHASE 1: CLAIM EXTRACTION
    # ========================================

    async def _extract_claims(
        self, text: str, title: str, max_claims: int, correlation_id: str
    ) -> tuple[list[dict], Optional[str]]:
        """
        Extract verifiable claims from article text using Haiku.

        Returns:
            Tuple of (claims_list, error_message). error_message is None on success.
        """
        from services.llm_service import get_llm_service, repair_json
        from services.config import get_config

        config = get_config()
        llm = get_llm_service()

        system_prompt = (
            "Voce e um analista de verificacao de fatos. Extraia as afirmacoes verificaveis "
            "de um artigo jornalistico. Para cada afirmacao, identifique:\n"
            "- text: o texto exato da afirmacao\n"
            "- category: 'fact' | 'statistic' | 'quote' | 'attribution' | 'opinion'\n"
            "- position_hint: trecho curto (~30 chars) que ajuda a localizar no texto original\n\n"
            "Regras:\n"
            "- Extraia no maximo {max_claims} afirmacoes\n"
            "- Priorize afirmacoes factuais (numeros, datas, nomes, eventos)\n"
            "- Marque opinioes como 'opinion'\n"
            "- Responda APENAS em JSON: {{\"claims\": [...]}}"
        ).format(max_claims=max_claims)

        user_content = f"Titulo: {title}\n\nArtigo:\n{text[:8000]}"

        try:
            response = await llm.call_api(
                system=system_prompt,
                user_content=user_content,
                max_tokens=2000,
                correlation_id=correlation_id,
                model=config.classification_model,
                task_type="scan_claim_extraction",
            )

            # Parse JSON response
            json_str = _extract_json(response)
            repaired = repair_json(json_str)
            parsed = json.loads(repaired)

            claims = parsed.get("claims", [])
            logger.info(f"[{correlation_id}] Extracted {len(claims)} claims")
            return claims[:max_claims], None

        except Exception as e:
            logger.error(f"[{correlation_id}] Claim extraction failed: {e}")
            return [], f"Falha na extração de claims: {e}"

    # ========================================
    # PHASE 2: EVIDENCE GATHERING
    # ========================================

    async def _gather_evidence(
        self, raw_claims: list[dict], language: str, correlation_id: str
    ) -> dict:
        """
        Gather evidence for claims in parallel:
        2a: Exa corroboration per claim
        2b: Google Fact Check API per claim
        2c: Exa fact-checker domain search (once)
        """
        evidence = {
            "exa_results": {},       # claim_text -> [sources]
            "external_factchecks": [],  # ExternalFactCheck list
            "factcheck_site_results": [],  # results from fact-checker sites
        }

        semaphore = asyncio.Semaphore(5)

        async def _search_exa_for_claim(claim_text: str):
            async with semaphore:
                return await self._search_exa_corroboration(claim_text, correlation_id)

        async def _search_google_for_claim(claim_text: str):
            async with semaphore:
                return await self._search_google_fact_checks(claim_text, language)

        # Build tasks
        exa_tasks = []
        google_tasks = []
        claim_texts = []

        for claim in raw_claims:
            ct = claim.get("text", "")
            if not ct or claim.get("category") == "opinion":
                continue
            claim_texts.append(ct)
            exa_tasks.append(_search_exa_for_claim(ct))
            google_tasks.append(_search_google_for_claim(ct))

        # Fact-checker site search (single query for the whole article)
        combined_query = " ".join(ct[:50] for ct in claim_texts[:3])
        factcheck_task = self._search_factcheck_sites(combined_query, correlation_id)

        # Execute all in parallel
        all_tasks = exa_tasks + google_tasks + [factcheck_task]
        if not all_tasks:
            return evidence

        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Parse results
        n_exa = len(exa_tasks)
        n_google = len(google_tasks)

        for i, ct in enumerate(claim_texts):
            # Exa results
            exa_result = results[i]
            if isinstance(exa_result, Exception):
                logger.warning(f"[{correlation_id}] Exa search failed for claim: {exa_result}")
                evidence["exa_results"][ct] = []
            else:
                evidence["exa_results"][ct] = exa_result or []

            # Google results
            google_result = results[n_exa + i]
            if isinstance(google_result, Exception):
                logger.warning(f"[{correlation_id}] Google fact-check failed: {google_result}")
            elif google_result:
                evidence["external_factchecks"].extend(google_result)

        # Fact-checker site results
        fc_result = results[-1]
        if not isinstance(fc_result, Exception) and fc_result:
            evidence["factcheck_site_results"] = fc_result

        return evidence

    async def _search_exa_corroboration(self, claim_text: str, correlation_id: str) -> list[dict]:
        """Search Exa for corroborating evidence for a claim."""
        exa_api_key = os.environ.get("EXA_API_KEY", "")
        if not exa_api_key:
            return []

        # Circuit breaker
        if self._exa_circuit_open:
            if time.time() < self._exa_circuit_open_until:
                return []
            self._exa_circuit_open = False
            self._exa_failures = 0

        num_results = int(os.environ.get("FACT_CHECK_SCAN_EXA_RESULTS", "3"))

        payload = {
            "query": claim_text,
            "type": "neural",
            "useAutoprompt": True,
            "numResults": num_results,
            "category": "news",
            "contents": {
                "text": {"maxCharacters": 1500},
                "highlights": {"numSentences": 2},
            },
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": exa_api_key,
        }

        try:
            response = await self.http_client.post(
                EXA_ENDPOINT, headers=headers, json=payload
            )
        except (httpx.ConnectError, httpx.ConnectTimeout):
            self._exa_failures += 1
            if self._exa_failures >= 3:
                self._exa_circuit_open = True
                self._exa_circuit_open_until = time.time() + 60
                logger.warning(f"[{correlation_id}] Exa circuit breaker OPENED")
            return []

        if response.status_code != 200:
            self._exa_failures += 1
            if self._exa_failures >= 3:
                self._exa_circuit_open = True
                self._exa_circuit_open_until = time.time() + 60
            return []

        self._exa_failures = 0
        data = response.json()
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "text": item.get("text", ""),
                "highlights": item.get("highlights", []),
            })

        # Cost logging
        try:
            from services.request_context import current_user_id, current_action_type, current_correlation_id
            from services.config import get_config
            from services.cost_queries import insert_api_usage_log
            insert_api_usage_log({
                'correlation_id': current_correlation_id.get() or correlation_id,
                'user_id': current_user_id.get(),
                'action_type': current_action_type.get(),
                'provider': 'exa',
                'operation': 'claim_corroboration',
                'request_count': 1,
                'input_units': num_results,
                'cost_usd': get_config().exa_cost_per_search,
                'status': 'success',
            })
        except Exception:
            pass

        return results

    async def _search_google_fact_checks(
        self, claim_text: str, language: str = "pt", max_age_days: int = 365, max_results: int = 5
    ) -> list[ExternalFactCheck]:
        """Search Google Fact Check Tools API for existing fact-checks."""
        api_key = os.environ.get("GOOGLE_FACTCHECK_API_KEY", "")
        if not api_key:
            return []

        params = {
            "query": claim_text[:200],
            "languageCode": language,
            "maxAgeDays": max_age_days,
            "pageSize": max_results,
            "key": api_key,
        }

        try:
            resp = await self.http_client.get(GOOGLE_FACTCHECK_ENDPOINT, params=params)
        except Exception as e:
            logger.warning(f"Google FactCheck API error: {e}")
            return []

        if resp.status_code != 200:
            logger.warning(f"Google FactCheck API returned {resp.status_code}")
            return []

        results = []
        for claim in resp.json().get("claims", []):
            for review in claim.get("claimReview", []):
                results.append(ExternalFactCheck(
                    claim_text=claim.get("text", ""),
                    rating=review.get("textualRating", ""),
                    publisher=review.get("publisher", {}).get("name", ""),
                    review_url=review.get("url", ""),
                    review_date=review.get("reviewDate", ""),
                ))
        return results

    async def _search_factcheck_sites(self, query: str, correlation_id: str) -> list[dict]:
        """Search Brazilian fact-checking sites for relevant articles."""
        exa_api_key = os.environ.get("EXA_API_KEY", "")
        if not exa_api_key or self._exa_circuit_open:
            return []

        payload = {
            "query": query,
            "type": "neural",
            "useAutoprompt": True,
            "numResults": 5,
            "includeDomains": FACTCHECK_DOMAINS,
            "contents": {
                "text": {"maxCharacters": 2000},
                "highlights": {"numSentences": 3},
            },
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": exa_api_key,
        }

        try:
            response = await self.http_client.post(
                EXA_ENDPOINT, headers=headers, json=payload
            )
            if response.status_code != 200:
                return []
            data = response.json()
            fc_results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "text": item.get("text", ""),
                    "highlights": item.get("highlights", []),
                }
                for item in data.get("results", [])
            ]

            # Cost logging
            try:
                from services.request_context import current_user_id, current_action_type, current_correlation_id
                from services.config import get_config
                from services.cost_queries import insert_api_usage_log
                insert_api_usage_log({
                    'correlation_id': current_correlation_id.get() or correlation_id,
                    'user_id': current_user_id.get(),
                    'action_type': current_action_type.get(),
                    'provider': 'exa',
                    'operation': 'factcheck_site_search',
                    'request_count': 1,
                    'input_units': 5,
                    'cost_usd': get_config().exa_cost_per_search,
                    'status': 'success',
                })
            except Exception:
                pass

            return fc_results
        except Exception as e:
            logger.warning(f"[{correlation_id}] Fact-checker site search failed: {e}")
            return []

    # ========================================
    # PHASE 3: CLAIM CLASSIFICATION
    # ========================================

    async def _classify_claims(
        self, raw_claims: list[dict], evidence: dict, correlation_id: str
    ) -> list[ScanClaim]:
        """Classify each claim using evidence from Phase 2."""
        from services.llm_service import get_llm_service, repair_json
        from services.config import get_config
        from services.media_credibility import get_media_credibility_db

        config = get_config()
        llm = get_llm_service()
        credibility_db = get_media_credibility_db()

        # Build evidence context per claim
        claims_with_evidence = []
        for claim in raw_claims:
            ct = claim.get("text", "")
            exa_sources = evidence.get("exa_results", {}).get(ct, [])

            evidence_summary = ""
            if exa_sources:
                snippets = []
                for src in exa_sources[:3]:
                    title = src.get("title", "")
                    highlights = src.get("highlights", [])
                    snippet = highlights[0] if highlights else src.get("text", "")[:200]
                    snippets.append(f"- {title}: {snippet}")
                evidence_summary = "\n".join(snippets)

            claims_with_evidence.append({
                "text": ct,
                "category": claim.get("category", "fact"),
                "position_hint": claim.get("position_hint", ct[:30]),
                "evidence": evidence_summary,
                "source_count": len(exa_sources),
            })

        # LLM classification
        system_prompt = (
            "Voce e um verificador de fatos. Para cada afirmacao abaixo, classifique:\n"
            "- verdict: 'grounded' (confirmada por evidencias), 'fabricated' (contradita), "
            "'unverifiable' (sem evidencia), 'opinion' (opiniao subjetiva)\n"
            "- severity: 'critical' (mortes, acusacoes criminais, saude publica), "
            "'high' (valores financeiros, decisoes politicas), "
            "'medium' (datas, localizacoes), 'low' (descricoes, contexto geral)\n"
            "- evidence: resumo curto de por que este veredicto\n\n"
            "Responda APENAS em JSON: {{\"verdicts\": [{{"
            "\"text\": \"...\", \"verdict\": \"...\", \"severity\": \"...\", \"evidence\": \"...\"}}]}}"
        )

        claims_json = json.dumps(claims_with_evidence, ensure_ascii=False)
        user_content = f"Afirmacoes com evidencias:\n{claims_json}"

        classified = []

        try:
            response = await llm.call_api(
                system=system_prompt,
                user_content=user_content,
                max_tokens=3000,
                correlation_id=correlation_id,
                model=config.classification_model,
                task_type="scan_claim_verdict",
            )

            json_str = _extract_json(response)
            repaired = repair_json(json_str)
            parsed = json.loads(repaired)
            verdicts = parsed.get("verdicts", [])

        except Exception as e:
            logger.error(f"[{correlation_id}] Claim classification failed: {e}")
            verdicts = []

        # Merge LLM verdicts with evidence sources
        for i, claim in enumerate(raw_claims):
            ct = claim.get("text", "")
            exa_sources = evidence.get("exa_results", {}).get(ct, [])

            # Get LLM verdict for this claim
            verdict_data = {}
            for v in verdicts:
                if v.get("text", "").strip() == ct.strip():
                    verdict_data = v
                    break
            # Fallback: match by index if text doesn't match exactly
            if not verdict_data and i < len(verdicts):
                verdict_data = verdicts[i]

            # Build claim sources with credibility
            sources = []
            for src in exa_sources[:3]:
                url = src.get("url", "")
                domain = _extract_domain(url)
                cred = credibility_db.get_source_credibility(domain)
                highlights = src.get("highlights", [])
                snippet = highlights[0] if highlights else src.get("text", "")[:200]
                sources.append(ClaimSource(
                    domain=domain,
                    title=src.get("title", ""),
                    url=url,
                    tier=cred["tier"],
                    tier_name=cred["tier_name"],
                    snippet=snippet[:300],
                ))

            # Check if any external fact-check matches this claim
            external_fc = None
            for fc in evidence.get("external_factchecks", []):
                if ct[:30].lower() in fc.claim_text.lower() or fc.claim_text.lower() in ct.lower():
                    external_fc = fc
                    break

            classified.append(ScanClaim(
                text=ct,
                verdict=verdict_data.get("verdict", claim.get("category", "unverifiable") if claim.get("category") == "opinion" else "unverifiable"),
                severity=verdict_data.get("severity", "low"),
                category=claim.get("category", "fact"),
                evidence=verdict_data.get("evidence", ""),
                sources=sources,
                external_fact_check=external_fc,
                position_hint=claim.get("position_hint", ct[:30]),
            ))

        return classified

    # ========================================
    # SOURCE CREDIBILITY
    # ========================================

    def _build_credibility_report(self, domains: list[str]) -> SourceCredibilityReport:
        """Build source credibility report from discovered domains."""
        from services.media_credibility import get_media_credibility_db

        credibility_db = get_media_credibility_db()

        if not domains:
            return SourceCredibilityReport()

        tier_breakdown = {}
        highest_tier_sources = []
        unknown_sources = []

        for domain in domains:
            cred = credibility_db.get_source_credibility(domain)
            tier_key = f"tier_{cred['tier']}"
            tier_breakdown[tier_key] = tier_breakdown.get(tier_key, 0) + 1

            if cred["tier"] <= 1:
                highest_tier_sources.append(cred["name"])
            elif cred["tier"] == 4:
                unknown_sources.append(domain)

        avg_cred = credibility_db.calculate_avg_credibility(domains)

        return SourceCredibilityReport(
            sources_found=len(domains),
            tier_breakdown=tier_breakdown,
            avg_credibility=round(avg_cred, 3),
            highest_tier_sources=highest_tier_sources[:5],
            unknown_sources=unknown_sources[:5],
        )

    # ========================================
    # DEEP VERIFY (batch re-verify unverifiable claims)
    # ========================================

    async def deep_verify(
        self,
        claims: list[dict],
        article_title: str = "",
        language: str = "pt",
        correlation_id: str = "",
    ) -> dict:
        """
        Batch deep-verify unverifiable claims using Exa search + Haiku reclassification.

        Runs up to MAX_ROUNDS rounds so that claims not resolved in the first pass
        (due to Exa non-determinism or timeouts) are retried automatically.
        The user only needs a single click.
        """
        MAX_ROUNDS = 3
        start_time = time.time()

        # Step 1: Filter unverifiable claims, keeping their original index
        unverifiable = []
        for i, claim in enumerate(claims):
            verdict = claim.get("verdict", "")
            if verdict == "unverifiable":
                unverifiable.append({"index": i, **claim})

        if not unverifiable:
            return {
                "updated_claims": [],
                "sources_searched": 0,
                "claims_resolved": 0,
                "deep_verify_duration_ms": 0,
            }

        logger.info(
            f"[{correlation_id}] Deep verify: {len(unverifiable)} unverifiable claims (max {MAX_ROUNDS} rounds)"
        )

        title_prefix = (article_title[:80] + " ") if article_title else ""
        semaphore = asyncio.Semaphore(5)

        all_updated = {}  # index -> claim dict (accumulates across rounds)
        total_sources = 0
        still_unverifiable = list(unverifiable)
        rounds_executed = 0

        for round_num in range(1, MAX_ROUNDS + 1):
            if not still_unverifiable:
                break

            rounds_executed = round_num
            logger.info(
                f"[{correlation_id}] Deep verify round {round_num}/{MAX_ROUNDS}: "
                f"{len(still_unverifiable)} claims to process"
            )

            # Parallel per-claim Exa searches (avoid query dilution)
            async def _search_claim(claim):
                async with semaphore:
                    query = f"{title_prefix}{claim.get('text', '')[:200]}".strip()
                    return await self._deep_verify_exa_search(query, correlation_id)

            exa_tasks = [_search_claim(c) for c in still_unverifiable]
            per_claim_results = await asyncio.gather(*exa_tasks, return_exceptions=True)

            # Merge results, deduplicating by URL
            seen_urls = set()
            exa_results = []
            per_claim_evidence = {}

            for i, result in enumerate(per_claim_results):
                claim_idx = still_unverifiable[i]["index"]
                claim_evidence = []
                if isinstance(result, Exception):
                    logger.warning(
                        f"[{correlation_id}] Deep verify Exa failed for claim {claim_idx} (round {round_num}): {result}"
                    )
                    per_claim_evidence[claim_idx] = []
                    continue
                for item in (result or []):
                    url = item.get("url", "")
                    claim_evidence.append(item)
                    if url not in seen_urls:
                        seen_urls.add(url)
                        exa_results.append(item)
                per_claim_evidence[claim_idx] = claim_evidence

            total_sources += len(exa_results)

            # Haiku classification
            round_updated = await self._deep_verify_classify(
                still_unverifiable, exa_results, per_claim_evidence, language, correlation_id
            )

            # Accumulate resolved claims, track still-unverifiable for next round
            next_unverifiable = []
            for claim_result in round_updated:
                idx = claim_result.get("index")
                if claim_result.get("verdict") == "grounded":
                    all_updated[idx] = claim_result
                else:
                    # Still unverifiable — keep latest evidence for next round
                    all_updated[idx] = claim_result
                    # Find original claim data for retry
                    original = next((c for c in still_unverifiable if c["index"] == idx), None)
                    if original:
                        next_unverifiable.append(original)

            resolved_this_round = sum(1 for c in round_updated if c.get("verdict") == "grounded")
            logger.info(
                f"[{correlation_id}] Deep verify round {round_num}: "
                f"{resolved_this_round} resolved, {len(next_unverifiable)} still unverifiable"
            )

            still_unverifiable = next_unverifiable

            # Stop early if no progress this round (avoid wasting API calls)
            if resolved_this_round == 0 and round_num > 1:
                logger.info(f"[{correlation_id}] Deep verify: no progress in round {round_num}, stopping")
                break

        # Final results
        final_updated = list(all_updated.values())
        claims_resolved = sum(1 for c in final_updated if c.get("verdict") == "grounded")
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[{correlation_id}] Deep verify complete: "
            f"{claims_resolved}/{len(unverifiable)} resolved in {rounds_executed} round(s), {duration_ms}ms"
        )

        return {
            "updated_claims": final_updated,
            "sources_searched": total_sources,
            "claims_resolved": claims_resolved,
            "deep_verify_duration_ms": duration_ms,
        }

    async def _deep_verify_exa_search(
        self, query: str, correlation_id: str
    ) -> list[dict]:
        """Single Exa search for deep verification evidence."""
        exa_api_key = os.environ.get("EXA_API_KEY", "")
        if not exa_api_key:
            logger.warning(f"[{correlation_id}] Deep verify: EXA_API_KEY not set")
            return []

        # Respect circuit breaker
        if self._exa_circuit_open:
            if time.time() < self._exa_circuit_open_until:
                logger.warning(f"[{correlation_id}] Deep verify: Exa circuit open")
                return []
            self._exa_circuit_open = False
            self._exa_failures = 0

        payload = {
            "query": query,
            "type": "neural",
            "useAutoprompt": True,
            "numResults": 5,
            "category": "news",
            "contents": {
                "text": {"maxCharacters": 2000},
                "highlights": {"numSentences": 3},
            },
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": exa_api_key,
        }

        try:
            response = await self.http_client.post(
                EXA_ENDPOINT, headers=headers, json=payload
            )
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            self._exa_failures += 1
            if self._exa_failures >= 3:
                self._exa_circuit_open = True
                self._exa_circuit_open_until = time.time() + 60
                logger.warning(f"[{correlation_id}] Exa circuit breaker OPENED")
            logger.warning(f"[{correlation_id}] Deep verify Exa connection error: {e}")
            return []

        if response.status_code != 200:
            self._exa_failures += 1
            if self._exa_failures >= 3:
                self._exa_circuit_open = True
                self._exa_circuit_open_until = time.time() + 60
            logger.warning(
                f"[{correlation_id}] Deep verify Exa returned {response.status_code}"
            )
            return []

        self._exa_failures = 0
        data = response.json()
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "text": item.get("text", ""),
                "highlights": item.get("highlights", []),
            })

        # Cost logging
        try:
            from services.request_context import current_user_id, current_action_type, current_correlation_id
            from services.config import get_config
            from services.cost_queries import insert_api_usage_log
            insert_api_usage_log({
                'correlation_id': current_correlation_id.get() or correlation_id,
                'user_id': current_user_id.get(),
                'action_type': current_action_type.get(),
                'provider': 'exa',
                'operation': 'deep_verify_search',
                'request_count': 1,
                'input_units': 5,
                'cost_usd': get_config().exa_cost_per_search,
                'status': 'success',
            })
        except Exception:
            pass

        return results

    async def _deep_verify_classify(
        self,
        unverifiable_claims: list[dict],
        exa_results: list[dict],
        per_claim_evidence: dict,
        language: str,
        correlation_id: str,
    ) -> list[dict]:
        """
        Single Haiku call to match Exa evidence to each unverifiable claim
        and reclassify them. Evidence is grouped per claim for better matching.
        """
        from services.llm_service import get_llm_service, repair_json
        from services.config import get_config

        config = get_config()
        llm = get_llm_service()

        # Build evidence context grouped by claim for better Haiku matching
        evidence_block = ""
        if exa_results:
            parts = []
            for claim in unverifiable_claims:
                idx = claim["index"]
                claim_ev = per_claim_evidence.get(idx, [])
                if claim_ev:
                    ev_lines = []
                    for j, src in enumerate(claim_ev, 1):
                        title = src.get("title", "")
                        url = src.get("url", "")
                        highlights = src.get("highlights", [])
                        snippet = (
                            " ".join(highlights[:3])
                            if highlights
                            else src.get("text", "")[:500]
                        )
                        ev_lines.append(
                            f"  [{j}] {title}\n      URL: {url}\n      Trecho: {snippet}"
                        )
                    parts.append(
                        f"--- Evidencias para claim index={idx} ---\n"
                        + "\n\n".join(ev_lines)
                    )
                else:
                    parts.append(
                        f"--- Evidencias para claim index={idx} ---\n"
                        "  (Nenhuma evidencia encontrada)"
                    )
            evidence_block = "\n\n".join(parts)
        else:
            evidence_block = "(Nenhuma evidencia encontrada)"

        # Build claims list
        claims_list = []
        for c in unverifiable_claims:
            claims_list.append({
                "index": c["index"],
                "text": c.get("text", ""),
                "severity": c.get("severity", "low"),
            })

        lang_instruction = (
            "Responda em portugues." if language == "pt" else "Respond in English."
        )

        system_prompt = (
            "Voce e um verificador de fatos especializado. "
            "Abaixo estao afirmacoes previamente classificadas como 'unverifiable' "
            "e novas evidencias encontradas na web.\n\n"
            "Para CADA afirmacao, analise se as evidencias agora permitem confirma-la.\n"
            "Retorne para cada uma:\n"
            "- index: o indice original da afirmacao\n"
            "- verdict: 'grounded' (se as evidencias agora confirmam) ou "
            "'unverifiable' (se ainda nao ha evidencia suficiente)\n"
            "- evidence: resumo curto da evidencia encontrada (ou por que continua inverificavel)\n"
            "- sources: lista de URLs das evidencias usadas (pode ser vazia)\n"
            "- severity: manter a severidade original\n\n"
            f"{lang_instruction}\n\n"
            "Responda APENAS em JSON: "
            '{"results": [{"index": 0, "verdict": "...", "evidence": "...", '
            '"sources": ["..."], "severity": "..."}]}'
        )

        claims_json = json.dumps(claims_list, ensure_ascii=False)
        user_content = (
            f"AFIRMACOES INVERIFICAVEIS:\n{claims_json}\n\n"
            f"EVIDENCIAS ENCONTRADAS:\n{evidence_block}"
        )

        try:
            response = await llm.call_api(
                system=system_prompt,
                user_content=user_content,
                max_tokens=3000,
                correlation_id=correlation_id,
                model=config.classification_model,
                task_type="deep_verify_claims",
            )

            json_str = _extract_json(response)
            repaired = repair_json(json_str)
            parsed = json.loads(repaired)
            llm_results = parsed.get("results", [])

        except Exception as e:
            logger.error(f"[{correlation_id}] Deep verify classification failed: {e}")
            # Return claims unchanged
            return [
                {
                    "index": c["index"],
                    "verdict": "unverifiable",
                    "evidence": c.get("evidence", ""),
                    "sources": [],
                    "severity": c.get("severity", "low"),
                }
                for c in unverifiable_claims
            ]

        # Build results, merging LLM output with fallbacks
        updated = []
        for i, claim in enumerate(unverifiable_claims):
            # Match by index from LLM response
            llm_entry = {}
            for r in llm_results:
                if r.get("index") == claim["index"]:
                    llm_entry = r
                    break
            verdict = llm_entry.get("verdict", "unverifiable")
            # Only allow grounded or unverifiable from deep verify
            if verdict not in ("grounded", "unverifiable"):
                verdict = "unverifiable"

            updated.append({
                "index": claim["index"],
                "verdict": verdict,
                "evidence": llm_entry.get("evidence", claim.get("evidence", "")),
                "sources": llm_entry.get("sources", []),
                "severity": llm_entry.get("severity", claim.get("severity", "low")),
            })

        return updated


# ========================================
# HELPERS
# ========================================

def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def _extract_json(text: str) -> str:
    """Extract JSON object or array from LLM response text."""
    # Try to find JSON block in markdown code fence
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if match:
        return match.group(1)
    # Try to find raw JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]
    return text


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url


# ========================================
# SINGLETON
# ========================================

_article_safety_service: Optional[ArticleSafetyService] = None
_article_safety_service_lock = threading.Lock()


def get_article_safety_service() -> ArticleSafetyService:
    """Get or create the ArticleSafetyService singleton (thread-safe)."""
    global _article_safety_service
    if _article_safety_service is None:
        with _article_safety_service_lock:
            if _article_safety_service is None:
                _article_safety_service = ArticleSafetyService()
    return _article_safety_service
