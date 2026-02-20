# Quality Loop + Clean UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current "show problems to user" approach with an auto-correcting Quality Loop that delivers publishable articles, and clean up the editor UI by removing technical banners.

**Architecture:** The backend `generation_api.py` gains a new Phase 4 (Quality Loop) that evaluates quality criteria after verification, uses Exa to fact-check problematic claims, builds corrective instructions, and regenerates until all criteria pass (max 3 attempts). The frontend removes all technical banners when the quality loop passes, keeping only sensitive content warnings and metadata fields.

**Tech Stack:** Python (Azure Functions backend), React (frontend), Exa API (web search), existing LLM service (Claude/Azure AI)

**Design Doc:** `docs/plans/2026-02-20-quality-loop-clean-ui-design.md`

---

### Task 1: Add `verify_claim_with_exa` to fact_check_service.py

**Files:**
- Modify: `FeedRSS/tmc-rss-collector/services/fact_check_service.py`
- Test: `FeedRSS/tmc-rss-collector/tests/test_quality_loop.py`

This is the core new capability: given a specific fabricated/unverifiable claim, search Exa for that claim and determine if it's true, false, or inconclusive.

**Step 1: Write the failing test**

Create `tests/test_quality_loop.py`:

```python
"""Tests for Quality Loop: Exa claim verification and quality evaluation."""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.fact_check_service import (
    FactCheckService,
    ExtractedClaim,
    EnrichmentContext,
)


@pytest.fixture
def fact_checker():
    """Create a FactCheckService with mocked LLM."""
    with patch.dict(os.environ, {"EXA_API_KEY": "test-key", "FACT_CHECK_ENABLED": "true"}):
        svc = FactCheckService.__new__(FactCheckService)
        svc.llm = MagicMock()
        svc.http_client = AsyncMock()
        svc._exa_circuit_open = False
        svc._exa_circuit_open_until = 0
        svc._exa_failures = 0
        return svc


class TestVerifyClaimWithExa:
    """Test Exa-based claim verification."""

    @pytest.mark.asyncio
    async def test_confirmed_claim(self, fact_checker):
        """Exa search confirms the claim is true."""
        claim = ExtractedClaim(
            text="O PIB do Brasil cresceu 3.1% em 2024",
            verdict="fabricated",
        )

        # Mock Exa returning confirming result
        fact_checker._search_exa = AsyncMock(return_value=[
            {"title": "PIB Brasil 2024", "text": "O PIB brasileiro registrou crescimento de 3.1% em 2024", "url": "https://ibge.gov.br/pib"}
        ])
        # Mock LLM verdict
        fact_checker._get_llm = MagicMock()
        fact_checker._get_llm().chat.return_value = '{"verdict": "confirmed", "correct_data": null, "evidence": "PIB cresceu 3.1%"}'

        result = await fact_checker.verify_claim_with_exa(claim)

        assert result["verdict"] == "confirmed"
        assert result["corrective_instruction"] is None

    @pytest.mark.asyncio
    async def test_contradicted_claim(self, fact_checker):
        """Exa search finds the claim is wrong and provides correct data."""
        claim = ExtractedClaim(
            text="O PIB do Brasil cresceu 5% em 2024",
            verdict="fabricated",
        )

        fact_checker._search_exa = AsyncMock(return_value=[
            {"title": "PIB Brasil 2024", "text": "O PIB brasileiro cresceu 3.1% em 2024", "url": "https://ibge.gov.br/pib"}
        ])
        fact_checker._get_llm = MagicMock()
        fact_checker._get_llm().chat.return_value = '{"verdict": "contradicted", "correct_data": "O PIB cresceu 3.1% em 2024, nao 5%", "evidence": "IBGE confirma 3.1%"}'

        result = await fact_checker.verify_claim_with_exa(claim)

        assert result["verdict"] == "contradicted"
        assert "3.1%" in result["corrective_instruction"]

    @pytest.mark.asyncio
    async def test_inconclusive_claim(self, fact_checker):
        """Exa search finds nothing relevant."""
        claim = ExtractedClaim(
            text="O prefeito declarou que vai construir 500 escolas",
            verdict="fabricated",
        )

        fact_checker._search_exa = AsyncMock(return_value=[])

        result = await fact_checker.verify_claim_with_exa(claim)

        assert result["verdict"] == "inconclusive"
        assert "REMOVER" in result["corrective_instruction"]

    @pytest.mark.asyncio
    async def test_exa_timeout_returns_inconclusive(self, fact_checker):
        """Exa search timeout should not crash, returns inconclusive."""
        claim = ExtractedClaim(text="Algo fabricado", verdict="fabricated")

        fact_checker._search_exa = AsyncMock(side_effect=Exception("timeout"))

        result = await fact_checker.verify_claim_with_exa(claim)

        assert result["verdict"] == "inconclusive"
```

**Step 2: Run test to verify it fails**

Run: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/test_quality_loop.py -v -x`
Expected: FAIL with `AttributeError: 'FactCheckService' object has no attribute 'verify_claim_with_exa'`

**Step 3: Implement `verify_claim_with_exa`**

Add to `FactCheckService` class in `services/fact_check_service.py` (after the `_search_exa` method, around line 730):

```python
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

        response = await llm.chat(comparison_prompt, system="Verificador factual objetivo.")
        parsed = self._extract_json(response)

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
```

**Step 4: Run test to verify it passes**

Run: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/test_quality_loop.py::TestVerifyClaimWithExa -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add FeedRSS/tmc-rss-collector/services/fact_check_service.py FeedRSS/tmc-rss-collector/tests/test_quality_loop.py
git commit -m "feat: add Exa claim-level verification for quality loop"
```

---

### Task 2: Add `evaluate_quality_criteria` function to generation_api.py

**Files:**
- Modify: `FeedRSS/tmc-rss-collector/functions/generation_api.py`
- Test: `FeedRSS/tmc-rss-collector/tests/test_quality_loop.py`

Pure function that evaluates ALL quality criteria and returns which ones failed with corrective instructions.

**Step 1: Write the failing tests**

Append to `tests/test_quality_loop.py`:

```python
from functions.generation_api import evaluate_quality_criteria


class TestEvaluateQualityCriteria:
    """Test quality criteria evaluation."""

    def test_all_pass(self):
        """Article with good scores passes all criteria."""
        verification = {
            "confidence_score": 0.75,
            "fabricated_claims": 0,
            "unverifiable_claims": 1,
            "total_claims": 10,
            "claims": [],
            "entity_comparison": {
                "novel_entities": ["a"],
                "output_entities": ["a", "b", "c", "d", "e"],
            },
        }
        readability = {"flesch_score": 50, "avg_sentence_length": 14}

        result = evaluate_quality_criteria(verification, readability)

        assert result["all_passed"] is True
        assert len(result["failures"]) == 0

    def test_fabrication_fails(self):
        """1+ fabricated claims triggers failure."""
        verification = {
            "confidence_score": 0.60,
            "fabricated_claims": 1,
            "unverifiable_claims": 0,
            "total_claims": 10,
            "claims": [
                {"text": "PIB cresceu 5%", "verdict": "fabricated"},
            ],
            "entity_comparison": {"novel_entities": [], "output_entities": ["a"]},
        }
        readability = {"flesch_score": 50}

        result = evaluate_quality_criteria(verification, readability)

        assert result["all_passed"] is False
        assert "fabrication" in [f["criterion"] for f in result["failures"]]

    def test_readability_fails(self):
        """Flesch < 42 triggers readability failure."""
        verification = {
            "confidence_score": 0.75,
            "fabricated_claims": 0,
            "unverifiable_claims": 0,
            "total_claims": 10,
            "claims": [],
            "entity_comparison": {"novel_entities": [], "output_entities": ["a"]},
        }
        readability = {"flesch_score": 38}

        result = evaluate_quality_criteria(verification, readability)

        assert result["all_passed"] is False
        assert "readability" in [f["criterion"] for f in result["failures"]]

    def test_low_confidence_fails(self):
        """Confidence < 0.50 triggers failure."""
        verification = {
            "confidence_score": 0.45,
            "fabricated_claims": 0,
            "unverifiable_claims": 0,
            "total_claims": 10,
            "claims": [],
            "entity_comparison": {"novel_entities": [], "output_entities": ["a"]},
            "is_verified": True,
        }
        readability = {"flesch_score": 50}

        result = evaluate_quality_criteria(verification, readability)

        assert result["all_passed"] is False
        assert "confidence" in [f["criterion"] for f in result["failures"]]

    def test_novel_entities_fails(self):
        """More than 60% novel entities triggers failure."""
        verification = {
            "confidence_score": 0.70,
            "fabricated_claims": 0,
            "unverifiable_claims": 0,
            "total_claims": 10,
            "claims": [],
            "entity_comparison": {
                "novel_entities": ["a", "b", "c", "d"],
                "output_entities": ["a", "b", "c", "d", "e"],
            },
        }
        readability = {"flesch_score": 50}

        result = evaluate_quality_criteria(verification, readability)

        assert result["all_passed"] is False
        assert "novel_entities" in [f["criterion"] for f in result["failures"]]

    def test_multiple_failures(self):
        """Multiple criteria can fail simultaneously."""
        verification = {
            "confidence_score": 0.40,
            "fabricated_claims": 2,
            "unverifiable_claims": 0,
            "total_claims": 10,
            "claims": [
                {"text": "Claim 1", "verdict": "fabricated"},
                {"text": "Claim 2", "verdict": "fabricated"},
            ],
            "entity_comparison": {"novel_entities": [], "output_entities": ["a"]},
            "is_verified": True,
        }
        readability = {"flesch_score": 35}

        result = evaluate_quality_criteria(verification, readability)

        assert result["all_passed"] is False
        criteria = [f["criterion"] for f in result["failures"]]
        assert "fabrication" in criteria
        assert "readability" in criteria
        assert "confidence" in criteria
```

**Step 2: Run test to verify it fails**

Run: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/test_quality_loop.py::TestEvaluateQualityCriteria -v -x`
Expected: FAIL with `ImportError: cannot import name 'evaluate_quality_criteria'`

**Step 3: Implement `evaluate_quality_criteria`**

Add to `functions/generation_api.py` (after `evaluate_safety_gates`, around line 320):

```python
# Quality Loop Configuration
QUALITY_LOOP_ENABLED = os.environ.get("QUALITY_LOOP_ENABLED", "true").lower() == "true"
QUALITY_LOOP_MAX_ATTEMPTS = int(os.environ.get("QUALITY_LOOP_MAX_ATTEMPTS", "3"))
QUALITY_LOOP_MAX_CLAIM_SEARCHES = int(os.environ.get("QUALITY_LOOP_MAX_CLAIM_SEARCHES", "5"))
QUALITY_LOOP_FLESCH_THRESHOLD = float(os.environ.get("QUALITY_LOOP_FLESCH_THRESHOLD", "42"))
QUALITY_LOOP_CONFIDENCE_THRESHOLD = float(os.environ.get("QUALITY_LOOP_CONFIDENCE_THRESHOLD", "0.50"))
QUALITY_LOOP_NOVEL_ENTITY_THRESHOLD = float(os.environ.get("QUALITY_LOOP_NOVEL_ENTITY_THRESHOLD", "0.60"))


def evaluate_quality_criteria(
    verification_data: dict,
    readability_data: dict,
) -> dict:
    """
    Evaluate all quality criteria for the Quality Loop.

    Pure function. Returns which criteria passed/failed with details.

    Args:
        verification_data: From fact_check_service verify_article
        readability_data: From compute_readability

    Returns:
        dict with all_passed (bool), failures (list of criterion dicts)
    """
    failures = []

    # 1. Fabrication check
    fabricated = verification_data.get("fabricated_claims", 0)
    fabricated_claims_list = [
        c for c in verification_data.get("claims", [])
        if (isinstance(c, dict) and c.get("verdict") == "fabricated")
    ]
    if fabricated >= 1:
        failures.append({
            "criterion": "fabrication",
            "detail": f"{fabricated} afirmacao(oes) fabricada(s)",
            "claims": fabricated_claims_list,
        })

    # 2. Readability check
    flesch = readability_data.get("flesch_score", 100)
    if flesch < QUALITY_LOOP_FLESCH_THRESHOLD:
        failures.append({
            "criterion": "readability",
            "detail": f"Flesch {flesch} abaixo do minimo {QUALITY_LOOP_FLESCH_THRESHOLD}",
            "instruction": (
                "Reescreva com frases mais curtas (maximo 20 palavras por frase). "
                "Evite oracoes subordinadas longas. Use vocabulario mais acessivel."
            ),
        })

    # 3. Confidence check
    confidence = verification_data.get("confidence_score", 1.0)
    is_verified = verification_data.get("is_verified", False)
    if is_verified and confidence < QUALITY_LOOP_CONFIDENCE_THRESHOLD:
        failures.append({
            "criterion": "confidence",
            "detail": f"Confianca {confidence:.0%} abaixo do minimo {QUALITY_LOOP_CONFIDENCE_THRESHOLD:.0%}",
            "instruction": (
                "Restrinja-se APENAS ao material-fonte. "
                "NAO adicione informacoes externas que nao possam ser verificadas."
            ),
        })

    # 4. Novel entities check
    entity_data = verification_data.get("entity_comparison", {})
    novel = entity_data.get("novel_entities", [])
    output_entities = entity_data.get("output_entities", [])
    if output_entities and len(novel) >= 4:
        ratio = len(novel) / len(output_entities)
        if ratio > QUALITY_LOOP_NOVEL_ENTITY_THRESHOLD:
            failures.append({
                "criterion": "novel_entities",
                "detail": f"{len(novel)}/{len(output_entities)} entidades novas ({ratio:.0%})",
                "instruction": (
                    "NAO introduza nomes de pessoas, lugares ou organizacoes "
                    "que nao estejam no texto-fonte original. "
                    f"Entidades problematicas: {', '.join(novel[:5])}"
                ),
            })

    return {
        "all_passed": len(failures) == 0,
        "failures": failures,
    }
```

**Step 4: Run test to verify it passes**

Run: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/test_quality_loop.py::TestEvaluateQualityCriteria -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add FeedRSS/tmc-rss-collector/functions/generation_api.py FeedRSS/tmc-rss-collector/tests/test_quality_loop.py
git commit -m "feat: add evaluate_quality_criteria for quality loop"
```

---

### Task 3: Implement Quality Loop orchestration in generation_api.py

**Files:**
- Modify: `FeedRSS/tmc-rss-collector/functions/generation_api.py` (replace Phase 2.1 block, lines ~607-694)
- Test: `FeedRSS/tmc-rss-collector/tests/test_quality_loop.py`

This replaces the existing auto-regeneration (Phase 2.1) with the full Quality Loop.

**Step 1: Write the failing test**

Append to `tests/test_quality_loop.py`:

```python
class TestQualityLoopOrchestration:
    """Test the quality loop integration flow."""

    def test_quality_loop_result_fields(self):
        """Quality loop result should have expected fields."""
        # Test that the response schema includes quality_loop fields
        from functions.generation_api import evaluate_quality_criteria

        verification = {
            "confidence_score": 0.80,
            "fabricated_claims": 0,
            "unverifiable_claims": 0,
            "total_claims": 5,
            "claims": [],
            "entity_comparison": {"novel_entities": [], "output_entities": ["a"]},
        }
        readability = {"flesch_score": 55}

        result = evaluate_quality_criteria(verification, readability)
        assert "all_passed" in result
        assert "failures" in result
        assert result["all_passed"] is True

    def test_build_corrective_instructions_from_failures(self):
        """Build corrective prompt from quality failures."""
        from functions.generation_api import build_corrective_instructions

        failures = [
            {
                "criterion": "readability",
                "instruction": "Reescreva com frases mais curtas",
            },
            {
                "criterion": "confidence",
                "instruction": "Restrinja-se ao material-fonte",
            },
        ]
        exa_corrections = [
            'CORRIGIR: "PIB cresceu 5%" esta ERRADO. Informacao correta: PIB cresceu 3.1%',
        ]

        result = build_corrective_instructions(failures, exa_corrections)

        assert "CORRECAO OBRIGATORIA" in result
        assert "frases mais curtas" in result
        assert "3.1%" in result
        assert "material-fonte" in result
```

**Step 2: Run test to verify it fails**

Run: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/test_quality_loop.py::TestQualityLoopOrchestration -v -x`
Expected: FAIL with `ImportError: cannot import name 'build_corrective_instructions'`

**Step 3: Implement `build_corrective_instructions` and Quality Loop**

Add `build_corrective_instructions` to `functions/generation_api.py` (after `evaluate_quality_criteria`):

```python
def build_corrective_instructions(
    failures: list,
    exa_corrections: list = None,
) -> str:
    """
    Build a corrective instruction prompt from quality loop failures.

    Combines Exa-verified corrections with readability/confidence instructions
    into a single prompt section injected into regeneration.

    Args:
        failures: List of failure dicts from evaluate_quality_criteria
        exa_corrections: List of corrective instruction strings from Exa claim verification

    Returns:
        Formatted instruction string for LLM regeneration prompt
    """
    parts = ["\n\n## CORRECAO OBRIGATORIA\n"]
    parts.append("A versao anterior teve problemas que DEVEM ser corrigidos:\n")

    # Exa-verified corrections first (most specific)
    if exa_corrections:
        for correction in exa_corrections:
            parts.append(f"- {correction}")

    # General instructions from other criteria
    for failure in failures:
        instruction = failure.get("instruction")
        if instruction:
            parts.append(f"- {instruction}")

    parts.append(
        "\nReescreva o artigo corrigindo TODOS os problemas acima. "
        "NAO invente informacoes para substituir as removidas. "
        "Se nao ha informacao suficiente, escreva um texto MAIS CURTO."
    )

    return "\n".join(parts)
```

Then **replace the Phase 2.1 block** (lines ~607-694 in `generation_api.py`) with the Quality Loop:

```python
        # ==============================================================
        # Phase 4: Quality Loop (replaces Phase 2.1 auto-regeneration)
        # ==============================================================
        quality_loop_result = {
            "quality_loop_passed": True,
            "quality_loop_attempts": 0,
            "quality_loop_issues_fixed": [],
            "quality_loop_claims_corrected": 0,
            "quality_loop_claims_removed": 0,
            "quality_loop_claims_confirmed": 0,
        }

        if (QUALITY_LOOP_ENABLED
                and is_fact_check_enabled()
                and not request_data.skip_verification
                and result.get("verification", {}).get("is_verified")):

            quality_loop_start = time.time()

            # Compute readability for quality evaluation
            readability = {}
            if result.get("conteudo"):
                from services.fact_check_service import compute_readability
                readability = compute_readability(result["conteudo"])
                result["readability"] = readability

            verification_data = result.get("verification", {})
            quality_eval = evaluate_quality_criteria(verification_data, readability)
            best_result = dict(result)  # Track best version

            attempt = 0
            while not quality_eval["all_passed"] and attempt < QUALITY_LOOP_MAX_ATTEMPTS:
                attempt += 1
                quality_loop_result["quality_loop_attempts"] = attempt
                logger.info(
                    f"[{correlation_id}] Quality Loop attempt {attempt}/{QUALITY_LOOP_MAX_ATTEMPTS}: "
                    f"failures={[f['criterion'] for f in quality_eval['failures']]}"
                )

                # Step 1: Exa claim verification for fabricated claims
                exa_corrections = []
                fabrication_failure = next(
                    (f for f in quality_eval["failures"] if f["criterion"] == "fabrication"),
                    None,
                )
                if fabrication_failure:
                    fact_checker = get_fact_check_service()
                    claims_to_check = fabrication_failure.get("claims", [])[:QUALITY_LOOP_MAX_CLAIM_SEARCHES]

                    for claim_dict in claims_to_check:
                        claim_obj = ExtractedClaim(
                            text=claim_dict.get("text", ""),
                            verdict=claim_dict.get("verdict", "fabricated"),
                        )
                        exa_result = await fact_checker.verify_claim_with_exa(claim_obj)

                        if exa_result["verdict"] == "confirmed":
                            quality_loop_result["quality_loop_claims_confirmed"] += 1
                        elif exa_result["verdict"] == "contradicted":
                            quality_loop_result["quality_loop_claims_corrected"] += 1
                            if exa_result.get("corrective_instruction"):
                                exa_corrections.append(exa_result["corrective_instruction"])
                        else:  # inconclusive
                            quality_loop_result["quality_loop_claims_removed"] += 1
                            if exa_result.get("corrective_instruction"):
                                exa_corrections.append(exa_result["corrective_instruction"])

                # Step 2: Build corrective instructions
                corrective_prompt = build_corrective_instructions(
                    quality_eval["failures"], exa_corrections
                )

                # Step 3: Regenerate with corrective instructions
                regen_sensitive = list(sensitive_instructions or [])
                regen_sensitive.append(corrective_prompt)

                try:
                    regen_result = await llm.generate_article(
                        texto_base=request_data.texto_base,
                        persona=request_data.persona,
                        tom=request_data.tom,
                        tipo_materia=request_data.tipo_materia,
                        orientacao_lide=request_data.orientacao_lide,
                        citacoes=request_data.citacoes,
                        contexto=request_data.contexto,
                        creditos=request_data.creditos,
                        tags=request_data.tags,
                        categoria=request_data.categoria,
                        modo_opinativo=request_data.modo_opinativo,
                        enrichment_context=enrichment_context,
                        enrichment_key_facts=enrichment_key_facts,
                        verified_chars=verified_chars,
                        sensitive_instructions=regen_sensitive,
                        correlation_id=correlation_id,
                    )

                    # Step 4: Re-verify
                    fact_checker = get_fact_check_service()
                    regen_verification = await fact_checker.verify_article(
                        texto_base=request_data.texto_base,
                        generated_article=regen_result.get("conteudo", ""),
                        citacoes=request_data.citacoes,
                        enrichment=enrichment,
                        correlation_id=correlation_id,
                    )
                    regen_result["verification"] = regen_verification.to_dict()

                    # Compute readability for regenerated version
                    regen_readability = compute_readability(regen_result.get("conteudo", ""))
                    regen_result["readability"] = regen_readability

                    # Re-evaluate quality
                    regen_eval = evaluate_quality_criteria(
                        regen_result["verification"], regen_readability
                    )

                    # Accept if better (fewer failures)
                    if len(regen_eval["failures"]) < len(quality_eval["failures"]):
                        # Track which issues were fixed
                        old_criteria = {f["criterion"] for f in quality_eval["failures"]}
                        new_criteria = {f["criterion"] for f in regen_eval["failures"]}
                        fixed = old_criteria - new_criteria
                        quality_loop_result["quality_loop_issues_fixed"].extend(list(fixed))

                        result = regen_result
                        quality_eval = regen_eval
                        best_result = dict(result)
                        logger.info(
                            f"[{correlation_id}] Quality Loop attempt {attempt} improved: "
                            f"fixed={fixed}, remaining={new_criteria}"
                        )
                    elif regen_eval["all_passed"]:
                        quality_loop_result["quality_loop_issues_fixed"] = [
                            f["criterion"] for f in quality_eval["failures"]
                        ]
                        result = regen_result
                        quality_eval = regen_eval
                        best_result = dict(result)
                        logger.info(f"[{correlation_id}] Quality Loop attempt {attempt}: ALL PASSED")
                    else:
                        logger.info(
                            f"[{correlation_id}] Quality Loop attempt {attempt} did not improve, keeping best"
                        )

                except Exception as e:
                    logger.warning(f"[{correlation_id}] Quality Loop attempt {attempt} failed: {e}")
                    break

            quality_loop_result["quality_loop_passed"] = quality_eval["all_passed"]

            # If loop didn't pass, use best version
            if not quality_loop_result["quality_loop_passed"]:
                result = best_result
                logger.warning(
                    f"[{correlation_id}] Quality Loop exhausted {attempt} attempts, "
                    f"using best version. Remaining: {[f['criterion'] for f in quality_eval['failures']]}"
                )

            result["quality_loop"] = quality_loop_result
            result["regenerated"] = quality_loop_result["quality_loop_attempts"] > 0
            phase_timings["quality_loop_ms"] = int((time.time() - quality_loop_start) * 1000)
```

Also add the import at the top of generation_api.py:

```python
from services.fact_check_service import ExtractedClaim
```

**Step 4: Run all quality loop tests**

Run: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/test_quality_loop.py -v`
Expected: All tests PASS

**Step 5: Run full test suite to check no regressions**

Run: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/ -v --timeout=60`
Expected: All existing tests still PASS

**Step 6: Commit**

```bash
git add FeedRSS/tmc-rss-collector/functions/generation_api.py FeedRSS/tmc-rss-collector/tests/test_quality_loop.py
git commit -m "feat: implement Quality Loop replacing Phase 2.1 auto-regeneration"
```

---

### Task 4: Add "Refinamento" phase to RevisarPage progress

**Files:**
- Modify: `tmc-redacao/src/pages/criar/RevisarPage.jsx` (lines 85-90, PHASES array)

**Step 1: Update PHASES array**

In `RevisarPage.jsx`, update the PHASES useMemo (line 85-90):

```jsx
const PHASES = useMemo(() => [
  { id: 'enrichment', label: 'Enriquecimento', description: 'Buscando fontes e verificando fatos...', Icon: Search, targetProgress: 15, durationMs: 7000 },
  { id: 'generation', label: 'Geração', description: 'Escrevendo matéria com IA Claude...', Icon: Sparkles, targetProgress: 50, durationMs: 20000 },
  { id: 'verification', label: 'Verificação', description: 'Conferindo claims e informações...', Icon: ShieldCheck, targetProgress: 70, durationMs: 12000 },
  { id: 'refinement', label: 'Refinamento', description: 'Corrigindo e aprimorando automaticamente...', Icon: Sparkles, targetProgress: 90, durationMs: 15000 },
  { id: 'finishing', label: 'Finalização', description: 'Aplicando SEO e revisão final...', Icon: CheckCircle2, targetProgress: 95, durationMs: 3000 },
], []);
```

**Step 2: Verify frontend builds**

Run: `cd tmc-redacao && npm run build`
Expected: Build succeeds with no errors

**Step 3: Commit**

```bash
git add tmc-redacao/src/pages/criar/RevisarPage.jsx
git commit -m "feat: add Refinamento phase to generation progress UI"
```

---

### Task 5: Clean up editor UI — remove technical banners

**Files:**
- Modify: `tmc-redacao/src/pages/CriarPostPage.jsx` (lines ~828-1049)

**Step 1: Conditionally hide banners based on quality_loop_passed**

Add a computed value near line 82 in CriarPostPage.jsx (after other resultado destructuring):

```jsx
const qualityLoopPassed = resultado?.qualityLoop?.quality_loop_passed ?? false;
```

Note: the backend sends `quality_loop` which the frontend maps via `setResultado` in RevisarPage.jsx. We need to add `qualityLoop` to the resultado mapping.

**Step 1a: Update setResultado in RevisarPage.jsx**

In RevisarPage.jsx, add to the `setResultado` call (around line 311-341):

```jsx
// Quality Loop result
qualityLoop: result.quality_loop || null,
```

**Step 2: Conditionally hide banners in CriarPostPage.jsx**

Replace the verification banner block (lines ~928-939) with:

```jsx
{/* v7: Verification Banner — ONLY show when quality loop did NOT pass */}
{verificationData && !qualityLoopPassed && (
  <div className="px-4 pt-3">
    <VerificationBanner
      verification={verificationData}
      publishBlocked={publishBlocked}
      blockReason={blockReason}
      humanReviewRequired={humanReviewRequired}
      reviewReasons={reviewReasons}
    />
  </div>
)}
```

Replace readability bar block (lines ~941-958) with:

```jsx
{/* v7: Readability display — ONLY show when quality loop did NOT pass */}
{readabilityData && !qualityLoopPassed && (
  <div className="px-4 pb-1">
    {/* ... existing readability UI ... */}
  </div>
)}
```

Replace enrichment degradation block (lines ~960-968) with:

```jsx
{/* v7: Enrichment degradation — ONLY show when quality loop did NOT pass */}
{enrichmentDegraded && !qualityLoopPassed && (
  <div className="px-4 pb-1">
    {/* ... existing enrichment warning ... */}
  </div>
)}
```

Replace regenerated notice block (lines ~999-1007) with:

```jsx
{/* v7.1: Regeneration notice — HIDE (quality loop handles this internally) */}
{/* Removed: regenerated notice is internal pipeline detail */}
```

Replace publication status badges (lines ~828-845) with:

```jsx
{/* v7: Publication status badge — only show blocked/review states */}
{publicationStatus === 'blocked' && (
  <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-700 font-medium flex items-center gap-1">
    <ShieldAlert size={12} />
    Bloqueado
  </span>
)}
{publicationStatus === 'draft_review' && !qualityLoopPassed && (
  <span className="text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700 font-medium flex items-center gap-1">
    <AlertTriangle size={12} />
    Revisao necessaria
  </span>
)}
{/* Removed: "Verificado" badge — if quality loop passed, it's obvious */}
```

**Step 3: Add Quality Loop failure banner**

After the blocked publish banner (line ~926), add:

```jsx
{/* Quality Loop failed — simple, non-technical message */}
{resultado?.qualityLoop && !qualityLoopPassed && !publishBlocked && (
  <div className="bg-amber-50 border-t border-amber-200 px-4 py-3">
    <div className="flex items-start gap-3">
      <AlertTriangle size={18} className="text-amber-500 mt-0.5 flex-shrink-0" />
      <div className="flex-1">
        <p className="text-sm font-medium text-amber-800">
          A materia precisa de revisao manual
        </p>
        <p className="text-xs text-amber-600 mt-1">
          A IA nao conseguiu resolver todos os pontos automaticamente. Revise o texto antes de publicar.
        </p>
        <div className="flex gap-2 mt-2">
          <button
            onClick={() => navigate('/criar/texto-base')}
            className="text-xs px-3 py-1.5 bg-white text-amber-700 border border-amber-300 rounded font-medium hover:bg-amber-50"
          >
            Adicionar mais fontes
          </button>
        </div>
      </div>
    </div>
  </div>
)}
```

**Step 4: Verify frontend builds**

Run: `cd tmc-redacao && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add tmc-redacao/src/pages/CriarPostPage.jsx tmc-redacao/src/pages/criar/RevisarPage.jsx
git commit -m "feat: clean editor UI — hide technical banners when quality loop passes"
```

---

### Task 6: Update backend response field + remove old Phase 2.1 code

**Files:**
- Modify: `FeedRSS/tmc-rss-collector/functions/generation_api.py`

**Step 1: Remove the old Phase 2.1 auto-regeneration block**

The old code from Phase 2.1 (lines ~607-694 in the original file) should have been replaced in Task 3. Verify that the old `MAX_REGENERATION_ATTEMPTS` / `REGEN_FABRICATION_THRESHOLD` code is fully removed and no dead code remains.

Also ensure the `quality_loop` dict is included in the final response. Add after the safety gate evaluation:

```python
# Include quality loop data in response
if "quality_loop" not in result:
    result["quality_loop"] = {
        "quality_loop_passed": True,
        "quality_loop_attempts": 0,
        "quality_loop_issues_fixed": [],
    }
```

**Step 2: Run full test suite**

Run: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/ -v --timeout=60`
Expected: All tests PASS (some old Phase 2.1 tests may need updating)

**Step 3: Commit**

```bash
git add FeedRSS/tmc-rss-collector/functions/generation_api.py
git commit -m "refactor: remove old Phase 2.1, clean up quality loop response"
```

---

### Task 7: End-to-end verification

**Files:** None (manual testing)

**Step 1: Run full backend test suite**

Run: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/ -v --timeout=60`
Expected: All tests PASS

**Step 2: Run frontend build**

Run: `cd tmc-redacao && npm run build`
Expected: Build succeeds

**Step 3: Manual smoke test checklist**

1. Generate an article with good source material → No banners shown (except sensitive if applicable)
2. Generate with minimal source → Quality loop kicks in, article improves, no technical banners
3. Sensitive content (suicide, minors) → Warning banner ALWAYS shows
4. Schema.org, slug, correlation ID → Still visible as before
5. Quality loop fails after 3 attempts → Simple "precisa de revisao manual" message

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: Quality Loop v2 + Clean UI — auto-correct articles, remove technical banners"
```

---

## Summary

| Task | Description | Files | Est. Complexity |
|------|-------------|-------|----------------|
| 1 | `verify_claim_with_exa` | fact_check_service.py, test_quality_loop.py | Medium |
| 2 | `evaluate_quality_criteria` | generation_api.py, test_quality_loop.py | Low |
| 3 | Quality Loop orchestration | generation_api.py, test_quality_loop.py | High |
| 4 | "Refinamento" progress phase | RevisarPage.jsx | Low |
| 5 | Clean editor UI | CriarPostPage.jsx, RevisarPage.jsx | Medium |
| 6 | Remove old Phase 2.1 | generation_api.py | Low |
| 7 | E2E verification | Manual testing | Low |
