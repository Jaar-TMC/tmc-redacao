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
from functions.generation_api import evaluate_quality_criteria, build_corrective_instructions


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
        svc._llm_service = None
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
        mock_llm = MagicMock()
        mock_llm.call_api = AsyncMock(return_value='{"verdict": "confirmed", "correct_data": null, "evidence": "PIB cresceu 3.1%"}')
        fact_checker._get_llm = MagicMock(return_value=mock_llm)

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
        mock_llm = MagicMock()
        mock_llm.call_api = AsyncMock(return_value='{"verdict": "contradicted", "correct_data": "O PIB cresceu 3.1% em 2024, nao 5%", "evidence": "IBGE confirma 3.1%"}')
        fact_checker._get_llm = MagicMock(return_value=mock_llm)

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


class TestQualityLoopOrchestration:
    """Test the quality loop integration flow."""

    def test_quality_loop_result_fields(self):
        """Quality loop result should have expected fields."""
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
