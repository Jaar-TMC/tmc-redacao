"""
Tests for evaluate_quality_criteria() in generation_api.py.

Covers all quality criteria evaluated in the Quality Loop:
1. Fabrication (any fabricated claim)
2. Readability (Flesch threshold, category-aware relaxation)
3. Confidence (below threshold when verified)
4. Novel entities (5+ at high ratio)
5. Unverifiable claims (3+ at > 40% ratio)
6. Risk level (production mode only)
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from functions.generation_api import evaluate_quality_criteria
sys.path.insert(0, os.path.dirname(__file__))
from conftest import make_verification_data


# =============================================================================
# Helper
# =============================================================================

def _default_readability(**overrides):
    """Factory for readability data with safe defaults."""
    base = {"flesch_score": 70, "avg_sentence_length": 12}
    base.update(overrides)
    return base


def _get_failure_criteria(result):
    """Extract list of criterion names from quality evaluation result."""
    return [f["criterion"] for f in result["failures"]]


# =============================================================================
# All criteria pass
# =============================================================================

class TestAllPass:
    """Tests for clean data that passes all criteria."""

    def test_all_pass_clean_data(self, legacy_mode):
        """Clean verification + good readability passes all criteria."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert result["all_passed"] is True
        assert len(result["failures"]) == 0

    def test_all_pass_production(self, production_mode):
        """Clean data passes in production mode too."""
        vdata = make_verification_data(risk_level="low")
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert result["all_passed"] is True


# =============================================================================
# Fabrication criterion
# =============================================================================

class TestFabricationCriterion:
    """Quality loop fails with any fabricated claims."""

    def test_1_fabricated_fails(self, legacy_mode):
        """1 fabricated claim triggers fabrication failure."""
        vdata = make_verification_data(fabricated_claims=1)
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert not result["all_passed"]
        assert "fabrication" in _get_failure_criteria(result)

    def test_3_fabricated_fails(self, legacy_mode):
        """3 fabricated claims also trigger fabrication failure."""
        vdata = make_verification_data(fabricated_claims=3)
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "fabrication" in _get_failure_criteria(result)

    def test_0_fabricated_passes(self, legacy_mode):
        """0 fabricated claims passes fabrication check."""
        vdata = make_verification_data(fabricated_claims=0)
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "fabrication" not in _get_failure_criteria(result)

    def test_fabricated_claims_list_included(self, legacy_mode):
        """Fabricated claims list is included in failure detail."""
        vdata = make_verification_data(
            fabricated_claims=1,
            claims=[
                {"text": "Claim A", "verdict": "fabricated"},
                {"text": "Claim B", "verdict": "grounded"},
            ],
        )
        # Need to add 'claims' to verification data
        result = evaluate_quality_criteria(vdata, _default_readability())
        fab_failure = [f for f in result["failures"] if f["criterion"] == "fabrication"][0]
        assert len(fab_failure["claims"]) == 1
        assert fab_failure["claims"][0]["text"] == "Claim A"


# =============================================================================
# Readability criterion
# =============================================================================

class TestReadabilityCriterion:
    """Readability check with category-aware threshold."""

    def test_below_threshold_fails(self, legacy_mode):
        """Flesch below 55 (default threshold) fails."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=54)
        )
        assert "readability" in _get_failure_criteria(result)

    def test_at_threshold_passes(self, legacy_mode):
        """Flesch at exactly 55 passes (< check)."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=55)
        )
        assert "readability" not in _get_failure_criteria(result)

    def test_above_threshold_passes(self, legacy_mode):
        """Flesch above 55 passes."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=70)
        )
        assert "readability" not in _get_failure_criteria(result)

    def test_analise_relaxed_threshold(self, legacy_mode):
        """Analise tipo_materia relaxes threshold by 10 (to 45)."""
        vdata = make_verification_data()
        # 50 is below default 55 but above relaxed 45
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=50),
            tipo_materia="analise",
        )
        assert "readability" not in _get_failure_criteria(result)

    def test_economia_relaxed_threshold(self, legacy_mode):
        """Economia categoria relaxes threshold by 10 (to 45)."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=50),
            categoria="economia",
        )
        assert "readability" not in _get_failure_criteria(result)

    def test_politica_relaxed_threshold(self, legacy_mode):
        """Politica categoria relaxes threshold by 10 (to 45)."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=46),
            categoria="politica",
        )
        assert "readability" not in _get_failure_criteria(result)

    def test_editorial_relaxed_threshold(self, legacy_mode):
        """Editorial tipo_materia relaxes threshold."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=50),
            tipo_materia="editorial",
        )
        assert "readability" not in _get_failure_criteria(result)

    def test_coluna_relaxed_threshold(self, legacy_mode):
        """Coluna tipo_materia relaxes threshold."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=50),
            tipo_materia="coluna",
        )
        assert "readability" not in _get_failure_criteria(result)

    def test_relaxed_still_fails_below_45(self, legacy_mode):
        """Relaxed threshold is capped at 45 (max(45, 55-10))."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=44),
            tipo_materia="analise",
        )
        assert "readability" in _get_failure_criteria(result)


# =============================================================================
# Confidence criterion
# =============================================================================

class TestConfidenceCriterion:
    """Confidence check fails below 0.65 when verified."""

    def test_below_065_verified_fails(self, legacy_mode):
        """Confidence < 0.65 with is_verified=True fails."""
        vdata = make_verification_data(confidence_score=0.64, is_verified=True)
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "confidence" in _get_failure_criteria(result)

    def test_at_065_verified_passes(self, legacy_mode):
        """Confidence == 0.65 with is_verified=True passes (< check)."""
        vdata = make_verification_data(confidence_score=0.65, is_verified=True)
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "confidence" not in _get_failure_criteria(result)

    def test_unverified_always_passes(self, legacy_mode):
        """Confidence < 0.65 with is_verified=False passes."""
        vdata = make_verification_data(confidence_score=0.30, is_verified=False)
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "confidence" not in _get_failure_criteria(result)


# =============================================================================
# Novel entities criterion
# =============================================================================

class TestNovelEntitiesCriterion:
    """Novel entities check fails with 5+ and ratio > 0.75."""

    def test_5_novel_high_ratio_fails(self, legacy_mode):
        """5 novel entities at > 0.75 ratio fails."""
        vdata = make_verification_data(
            entity_comparison={
                "novel_entities": ["A", "B", "C", "D", "E"],
                "output_entities": ["A", "B", "C", "D", "E", "F"],
                "source_entities": ["F"],
                "common_entities": ["F"],
            }
        )
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "novel_entities" in _get_failure_criteria(result)

    def test_4_novel_no_fail(self, legacy_mode):
        """4 novel entities does NOT trigger failure (requires >= 5)."""
        vdata = make_verification_data(
            entity_comparison={
                "novel_entities": ["A", "B", "C", "D"],
                "output_entities": ["A", "B", "C", "D", "E"],
                "source_entities": ["E"],
                "common_entities": ["E"],
            }
        )
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "novel_entities" not in _get_failure_criteria(result)

    def test_5_novel_low_ratio_passes(self, legacy_mode):
        """5 novel entities at <= 0.75 ratio passes."""
        vdata = make_verification_data(
            entity_comparison={
                "novel_entities": ["A", "B", "C", "D", "E"],
                # 5/7 = 0.714 < 0.75
                "output_entities": ["A", "B", "C", "D", "E", "F", "G"],
                "source_entities": ["F", "G"],
                "common_entities": ["F", "G"],
            }
        )
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "novel_entities" not in _get_failure_criteria(result)


# =============================================================================
# Unverifiable claims criterion
# =============================================================================

class TestUnverifiableCriterion:
    """Unverifiable claims check fails with 3+ at > 40% ratio."""

    def test_3_unverifiable_high_ratio_fails(self, legacy_mode):
        """3 unverifiable out of 5 (60%) fails."""
        vdata = make_verification_data(
            unverifiable_claims=3, total_claims=5,
        )
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "unverifiable" in _get_failure_criteria(result)

    def test_2_unverifiable_no_fail(self, legacy_mode):
        """2 unverifiable does NOT trigger (requires >= 3)."""
        vdata = make_verification_data(
            unverifiable_claims=2, total_claims=3,
        )
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "unverifiable" not in _get_failure_criteria(result)

    def test_3_unverifiable_low_ratio_passes(self, legacy_mode):
        """3 unverifiable out of 8 (37.5%) passes (ratio <= 0.40)."""
        vdata = make_verification_data(
            unverifiable_claims=3, total_claims=8,
        )
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "unverifiable" not in _get_failure_criteria(result)


# =============================================================================
# Risk level criterion (production only)
# =============================================================================

class TestRiskLevelCriterion:
    """Risk level quality criterion fires only in production mode."""

    def test_high_risk_fails_production(self, production_mode):
        """Production: high risk triggers risk_level failure."""
        vdata = make_verification_data(risk_level="high")
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "risk_level" in _get_failure_criteria(result)

    def test_critical_risk_fails_production(self, production_mode):
        """Production: critical risk triggers risk_level failure."""
        vdata = make_verification_data(risk_level="critical")
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "risk_level" in _get_failure_criteria(result)

    def test_high_risk_passes_legacy(self, legacy_mode):
        """Legacy: high risk does NOT trigger risk_level failure."""
        vdata = make_verification_data(risk_level="high")
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "risk_level" not in _get_failure_criteria(result)

    def test_low_risk_passes_production(self, production_mode):
        """Production: low risk passes."""
        vdata = make_verification_data(risk_level="low")
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "risk_level" not in _get_failure_criteria(result)

    def test_medium_risk_passes_production(self, production_mode):
        """Production: medium risk passes."""
        vdata = make_verification_data(risk_level="medium")
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "risk_level" not in _get_failure_criteria(result)


# =============================================================================
# Multiple failures
# =============================================================================

class TestMultipleFailures:
    """Multiple criteria can fail simultaneously."""

    def test_multiple_failures_accumulated(self, production_mode):
        """Multiple failures accumulate in the failures list."""
        vdata = make_verification_data(
            fabricated_claims=2,
            confidence_score=0.50,
            is_verified=True,
            risk_level="high",
            unverifiable_claims=4,
            total_claims=8,
        )
        result = evaluate_quality_criteria(
            vdata, _default_readability(flesch_score=40),
        )
        criteria = _get_failure_criteria(result)
        assert not result["all_passed"]
        assert "fabrication" in criteria
        assert "readability" in criteria
        assert "confidence" in criteria
        assert "risk_level" in criteria
        assert "unverifiable" in criteria

    def test_return_structure(self, legacy_mode):
        """Return dict has all_passed bool and failures list."""
        vdata = make_verification_data()
        result = evaluate_quality_criteria(vdata, _default_readability())
        assert "all_passed" in result
        assert "failures" in result
        assert isinstance(result["all_passed"], bool)
        assert isinstance(result["failures"], list)
