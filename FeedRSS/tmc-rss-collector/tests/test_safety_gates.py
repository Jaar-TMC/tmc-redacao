"""
Comprehensive tests for evaluate_safety_gates() in generation_api.py.

This is the MOST CRITICAL code path: it decides whether fabricated news
gets published. Every branching condition in the function is tested with
positive and negative cases, boundary values, and mode-specific behavior.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from functions.generation_api import evaluate_safety_gates, SafetyDecision
sys.path.insert(0, os.path.dirname(__file__))
from conftest import make_verification_data


# =============================================================================
# Helper
# =============================================================================

def _call(vdata, content_length=2000, effective_source_len=1000, **kwargs):
    """Shorthand to call evaluate_safety_gates with defaults."""
    return evaluate_safety_gates(
        verification_data=vdata,
        content_length=content_length,
        effective_source_len=effective_source_len,
        **kwargs,
    )


# =============================================================================
# HARD BLOCKS - Critical risk
# =============================================================================

class TestCriticalRisk:
    """Critical risk level is an unconditional hard block."""

    def test_critical_risk_blocks_in_legacy(self, legacy_mode):
        """Critical risk blocks even in legacy mode."""
        data = make_verification_data(risk_level="critical")
        result = _call(data)
        assert result.publish_blocked
        assert any("CRITICO" in r for r in result.block_reasons)

    def test_critical_risk_blocks_in_production(self, production_mode):
        """Critical risk blocks in production mode."""
        data = make_verification_data(risk_level="critical")
        result = _call(data)
        assert result.publish_blocked
        assert any("CRITICO" in r for r in result.block_reasons)


# =============================================================================
# HARD BLOCKS - High risk (production-only block)
# =============================================================================

class TestHighRisk:
    """High risk is a hard block in production, soft gate in legacy."""

    def test_high_risk_blocks_in_production(self, production_mode):
        """Production mode: high risk is a hard block."""
        data = make_verification_data(risk_level="high")
        result = _call(data)
        assert result.publish_blocked
        assert any("ALTO" in r and "producao" in r for r in result.block_reasons)

    def test_high_risk_does_not_block_in_legacy(self, legacy_mode):
        """Legacy mode: high risk does NOT hard-block."""
        data = make_verification_data(risk_level="high", is_verified=False)
        result = _call(data)
        # Should not be blocked (high risk is only a soft gate in legacy)
        high_risk_blocked = any(
            "ALTO" in r and "producao" in r for r in result.block_reasons
        )
        assert not high_risk_blocked

    def test_high_risk_triggers_review_in_legacy(self, legacy_mode):
        """Legacy mode: high risk triggers human review (soft gate)."""
        data = make_verification_data(risk_level="high", is_verified=False)
        result = _call(data)
        assert result.human_review_required
        assert any("ALTO" in r for r in result.review_reasons)


# =============================================================================
# HARD BLOCKS - Confidence floor
# =============================================================================

class TestConfidenceFloor:
    """Confidence floor hard blocks when is_verified=True."""

    def test_confidence_below_050_blocks_production(self, production_mode):
        """Production: confidence < 0.50 with is_verified=True blocks."""
        data = make_verification_data(confidence_score=0.49, is_verified=True, risk_level="low")
        result = _call(data)
        assert result.publish_blocked
        assert any("baixa" in r.lower() or "piso" in r.lower() for r in result.block_reasons)

    def test_confidence_below_040_blocks_legacy(self, legacy_mode):
        """Legacy: confidence < 0.40 with is_verified=True blocks."""
        data = make_verification_data(confidence_score=0.39, is_verified=True)
        result = _call(data)
        assert result.publish_blocked
        assert any("baixa" in r.lower() for r in result.block_reasons)

    def test_confidence_at_040_does_not_block_legacy(self, legacy_mode):
        """Legacy: confidence == 0.40 does NOT block (floor is strict <)."""
        data = make_verification_data(confidence_score=0.40, is_verified=True)
        result = _call(data)
        confidence_blocked = any("baixa" in r.lower() for r in result.block_reasons)
        assert not confidence_blocked

    def test_confidence_at_050_does_not_block_production(self, production_mode):
        """Production: confidence == 0.50 does NOT block (floor is strict <)."""
        data = make_verification_data(confidence_score=0.50, is_verified=True, risk_level="low")
        result = _call(data)
        # The 0.50 passes the confidence_floor check, but may fail publish_confidence_floor (0.65)
        confidence_floor_blocked = any("baixa" in r.lower() for r in result.block_reasons)
        assert not confidence_floor_blocked

    def test_confidence_unverified_does_not_block(self, legacy_mode):
        """Confidence < 0.40 with is_verified=False does NOT trigger confidence block."""
        data = make_verification_data(confidence_score=0.10, is_verified=False)
        result = _call(data)
        confidence_blocked = any("baixa" in r.lower() for r in result.block_reasons)
        assert not confidence_blocked

    def test_confidence_unverified_does_not_block_production(self, production_mode):
        """Production: confidence < 0.50 with is_verified=False does NOT trigger confidence block."""
        data = make_verification_data(
            confidence_score=0.10, is_verified=False, risk_level="low"
        )
        result = _call(data)
        confidence_blocked = any("baixa" in r.lower() for r in result.block_reasons)
        assert not confidence_blocked


# =============================================================================
# HARD BLOCKS - Publication-readiness floors (production only)
# =============================================================================

class TestPublishFloors:
    """publish_confidence_floor (0.65) and publish_grounded_floor (0.70) in production."""

    def test_publish_confidence_floor_blocks(self, production_mode):
        """Production: confidence < 0.65 (publish floor) blocks when verified."""
        data = make_verification_data(confidence_score=0.64, is_verified=True, risk_level="low")
        result = _call(data)
        assert result.publish_blocked
        assert any("piso" in r.lower() or "publicacao" in r.lower() for r in result.block_reasons)

    def test_publish_confidence_at_065_passes(self, production_mode):
        """Production: confidence == 0.65 passes publish floor (< check)."""
        data = make_verification_data(confidence_score=0.65, is_verified=True, risk_level="low")
        result = _call(data)
        pub_floor_blocked = any("piso" in r.lower() for r in result.block_reasons)
        assert not pub_floor_blocked

    def test_publish_grounded_floor_blocks(self, production_mode):
        """Production: grounded ratio < 0.70 blocks when verified."""
        data = make_verification_data(
            confidence_score=0.80, is_verified=True, risk_level="low",
            grounded_claims=6, total_claims=10, context_claims=0,
        )
        # grounded_ratio = 6/10 = 0.60 < 0.70
        result = _call(data)
        assert result.publish_blocked
        assert any("fundamentados" in r for r in result.block_reasons)

    def test_publish_grounded_at_070_passes(self, production_mode):
        """Production: grounded ratio == 0.70 passes (< check)."""
        data = make_verification_data(
            confidence_score=0.80, is_verified=True, risk_level="low",
            grounded_claims=7, total_claims=10, context_claims=0,
        )
        result = _call(data)
        grounded_blocked = any("fundamentados" in r for r in result.block_reasons)
        assert not grounded_blocked

    def test_context_claims_contribute_to_grounded(self, production_mode):
        """context_claims weighted at 0.8 contribute to effective_grounded."""
        # grounded=5, context=3 => effective = 5 + 3*0.8 = 7.4 => ratio = 7.4/10 = 0.74 >= 0.70
        data = make_verification_data(
            confidence_score=0.80, is_verified=True, risk_level="low",
            grounded_claims=5, context_claims=3, total_claims=10,
        )
        result = _call(data)
        grounded_blocked = any("fundamentados" in r for r in result.block_reasons)
        assert not grounded_blocked

    def test_context_claims_not_enough(self, production_mode):
        """context_claims at 0.8 weight still not enough to reach floor."""
        # grounded=4, context=3 => effective = 4 + 3*0.8 = 6.4 => ratio = 6.4/10 = 0.64 < 0.70
        data = make_verification_data(
            confidence_score=0.80, is_verified=True, risk_level="low",
            grounded_claims=4, context_claims=3, total_claims=10,
        )
        result = _call(data)
        assert result.publish_blocked
        assert any("fundamentados" in r for r in result.block_reasons)

    def test_publish_floors_not_checked_in_legacy(self, legacy_mode):
        """Legacy mode does NOT check publish floors."""
        data = make_verification_data(
            confidence_score=0.50, is_verified=True,
            grounded_claims=3, total_claims=10,
        )
        result = _call(data)
        pub_blocked = any("piso" in r.lower() or "publicacao" in r.lower() for r in result.block_reasons)
        assert not pub_blocked


# =============================================================================
# HARD BLOCKS - Fabrication gates
# =============================================================================

class TestFabricationGates:
    """Fabrication-based hard blocks differ between production and legacy."""

    def test_2_fabricated_blocks_production(self, production_mode):
        """Production: 2+ fabricated always blocks."""
        data = make_verification_data(
            fabricated_claims=2, confidence_score=0.90, risk_level="low",
        )
        result = _call(data)
        assert result.publish_blocked
        assert any("fabricadas" in r for r in result.block_reasons)

    def test_1_fabricated_low_confidence_blocks_production(self, production_mode):
        """Production: 1 fabricated + confidence < 0.50 blocks."""
        data = make_verification_data(
            fabricated_claims=1, confidence_score=0.49, risk_level="low",
            is_verified=False,  # avoid confidence floor block
        )
        result = _call(data)
        assert result.publish_blocked
        assert any("fabricada" in r for r in result.block_reasons)

    def test_1_fabricated_high_confidence_does_not_block_production(self, production_mode):
        """Production: 1 fabricated + confidence >= 0.50 does NOT block (review instead)."""
        data = make_verification_data(
            fabricated_claims=1, confidence_score=0.80, risk_level="low",
        )
        result = _call(data)
        fabrication_blocked = any("fabricada" in r for r in result.block_reasons)
        assert not fabrication_blocked

    def test_3_fabricated_blocks_legacy(self, legacy_mode):
        """Legacy: 3+ fabricated blocks."""
        data = make_verification_data(fabricated_claims=3, confidence_score=0.90)
        result = _call(data)
        assert result.publish_blocked
        assert any("fabricadas" in r for r in result.block_reasons)

    def test_2_fabricated_low_confidence_blocks_legacy(self, legacy_mode):
        """Legacy: 2 fabricated + confidence < 0.40 blocks."""
        data = make_verification_data(fabricated_claims=2, confidence_score=0.39)
        result = _call(data)
        assert result.publish_blocked

    def test_2_fabricated_high_confidence_does_not_block_legacy(self, legacy_mode):
        """Legacy: 2 fabricated + confidence >= 0.40 does NOT block (review instead)."""
        data = make_verification_data(fabricated_claims=2, confidence_score=0.40)
        result = _call(data)
        fabrication_blocked = any("fabricadas" in r for r in result.block_reasons)
        assert not fabrication_blocked

    def test_1_fabricated_does_not_block_legacy(self, legacy_mode):
        """Legacy: 1 fabricated never blocks."""
        data = make_verification_data(fabricated_claims=1, confidence_score=0.10)
        result = _call(data)
        fabrication_blocked = any("fabricada" in r for r in result.block_reasons)
        assert not fabrication_blocked


# =============================================================================
# HARD BLOCKS - Unverifiable claims
# =============================================================================

class TestUnverifiableBlocks:
    """Unverifiable claims >= 3 at > 40% ratio blocks."""

    def test_3_unverifiable_over_40pct_blocks(self, legacy_mode):
        """3 unverifiable out of 5 (60%) blocks."""
        data = make_verification_data(
            unverifiable_claims=3, total_claims=5,
        )
        result = _call(data)
        assert result.publish_blocked
        assert any("inverificaveis" in r for r in result.block_reasons)

    def test_3_unverifiable_at_40pct_does_not_block(self, legacy_mode):
        """3 unverifiable out of 8 (37.5%) does NOT block (ratio <= 0.40)."""
        data = make_verification_data(
            unverifiable_claims=3, total_claims=8,
        )
        result = _call(data)
        unverifiable_blocked = any("inverificaveis" in r for r in result.block_reasons)
        assert not unverifiable_blocked

    def test_2_unverifiable_does_not_block(self, legacy_mode):
        """2 unverifiable never triggers the hard block (requires >= 3)."""
        data = make_verification_data(
            unverifiable_claims=2, total_claims=3,
        )
        result = _call(data)
        unverifiable_blocked = any("inverificaveis" in r for r in result.block_reasons)
        assert not unverifiable_blocked


# =============================================================================
# HARD BLOCKS - Expansion ratio
# =============================================================================

class TestExpansionBlocks:
    """Expansion ratio hard blocks differ between production (8x) and legacy (15x)."""

    def test_expansion_over_8x_blocks_production(self, production_mode):
        """Production: expansion > 8.0x blocks."""
        data = make_verification_data(risk_level="low")
        result = _call(data, content_length=8100, effective_source_len=1000)
        assert result.publish_blocked
        assert any("Expansao extrema" in r for r in result.block_reasons)

    def test_expansion_at_8x_does_not_block_production(self, production_mode):
        """Production: expansion == 8.0x does NOT block (> check)."""
        data = make_verification_data(risk_level="low")
        result = _call(data, content_length=8000, effective_source_len=1000)
        expansion_blocked = any("Expansao extrema" in r for r in result.block_reasons)
        assert not expansion_blocked

    def test_expansion_over_15x_blocks_legacy(self, legacy_mode):
        """Legacy: expansion > 15x blocks."""
        data = make_verification_data()
        result = _call(data, content_length=15100, effective_source_len=1000)
        assert result.publish_blocked
        assert any("Expansao extrema" in r for r in result.block_reasons)

    def test_expansion_at_15x_does_not_block_legacy(self, legacy_mode):
        """Legacy: expansion == 15x does NOT block (> check)."""
        data = make_verification_data()
        result = _call(data, content_length=15000, effective_source_len=1000)
        expansion_blocked = any("Expansao extrema" in r for r in result.block_reasons)
        assert not expansion_blocked

    def test_expansion_fallback_to_expansion_ratio_when_source_zero(self, legacy_mode):
        """When effective_source_len == 0, uses expansion_ratio from verification data."""
        data = make_verification_data(expansion_ratio=16.0)
        result = _call(data, content_length=2000, effective_source_len=0)
        assert result.publish_blocked
        assert any("Expansao extrema" in r for r in result.block_reasons)

    def test_expansion_fallback_safe_when_ratio_low(self, legacy_mode):
        """When effective_source_len == 0, low expansion_ratio does not block."""
        data = make_verification_data(expansion_ratio=5.0)
        result = _call(data, content_length=2000, effective_source_len=0)
        expansion_blocked = any("Expansao extrema" in r for r in result.block_reasons)
        assert not expansion_blocked


# =============================================================================
# SOFT REVIEW GATES
# =============================================================================

class TestSoftGates:
    """Human review (soft) gates."""

    def test_1_fabricated_review_production(self, production_mode):
        """Production: 1 fabricated + confidence >= 0.50 triggers review."""
        data = make_verification_data(
            fabricated_claims=1, confidence_score=0.80, risk_level="low",
        )
        result = _call(data)
        assert not result.publish_blocked
        assert result.human_review_required
        assert any("fabricada" in r for r in result.review_reasons)

    def test_2_fabricated_review_legacy(self, legacy_mode):
        """Legacy: 2 fabricated + confidence >= 0.40 triggers review."""
        data = make_verification_data(fabricated_claims=2, confidence_score=0.60)
        result = _call(data)
        assert not result.publish_blocked
        assert result.human_review_required
        assert any("fabricadas" in r for r in result.review_reasons)

    def test_unverifiable_2_over_30pct_review(self, legacy_mode):
        """2+ unverifiable at > 30% triggers review."""
        data = make_verification_data(
            unverifiable_claims=2, total_claims=5,
        )
        result = _call(data)
        assert result.human_review_required
        assert any("inverificaveis" in r for r in result.review_reasons)

    def test_unverifiable_2_at_30pct_no_review(self, legacy_mode):
        """2 unverifiable at exactly 30% does NOT trigger review (> check)."""
        # 2/6.666... = 0.30 -- use exact: 2 out of 7 = 0.2857 < 0.30
        data = make_verification_data(
            unverifiable_claims=2, total_claims=7,
        )
        result = _call(data)
        unverifiable_review = any("inverificaveis" in r for r in result.review_reasons)
        assert not unverifiable_review

    def test_novel_entities_4_over_60pct_review(self, legacy_mode):
        """4+ novel entities at > 60% with confidence < 0.80 triggers review."""
        data = make_verification_data(
            confidence_score=0.75,
            entity_comparison={
                "novel_entities": ["A", "B", "C", "D"],
                "output_entities": ["A", "B", "C", "D", "E", "F"],
                "source_entities": ["E", "F"],
                "common_entities": ["E", "F"],
            },
        )
        result = _call(data)
        assert result.human_review_required
        assert any("entidades novas" in r for r in result.review_reasons)

    def test_novel_entities_skipped_high_confidence(self, legacy_mode):
        """Novel entity gate skipped when confidence >= 0.80."""
        data = make_verification_data(
            confidence_score=0.80,
            entity_comparison={
                "novel_entities": ["A", "B", "C", "D"],
                "output_entities": ["A", "B", "C", "D", "E", "F"],
                "source_entities": ["E", "F"],
                "common_entities": ["E", "F"],
            },
        )
        result = _call(data)
        entity_review = any("entidades novas" in r for r in result.review_reasons)
        assert not entity_review

    def test_novel_entities_below_4_no_review(self, legacy_mode):
        """3 novel entities does NOT trigger review (requires >= 4)."""
        data = make_verification_data(
            confidence_score=0.70,
            entity_comparison={
                "novel_entities": ["A", "B", "C"],
                "output_entities": ["A", "B", "C", "D"],
                "source_entities": ["D"],
                "common_entities": ["D"],
            },
        )
        result = _call(data)
        entity_review = any("entidades novas" in r for r in result.review_reasons)
        assert not entity_review

    def test_expansion_10_to_15_review_legacy(self, legacy_mode):
        """Legacy: expansion between 10 and 15 triggers review."""
        data = make_verification_data()
        result = _call(data, content_length=12000, effective_source_len=1000)
        assert result.human_review_required
        assert any("Expansao elevada" in r for r in result.review_reasons)

    def test_expansion_at_10_no_review_legacy(self, legacy_mode):
        """Legacy: expansion == 10.0 does NOT trigger review (> 10 required)."""
        data = make_verification_data()
        result = _call(data, content_length=10000, effective_source_len=1000)
        expansion_review = any("Expansao elevada" in r for r in result.review_reasons)
        assert not expansion_review

    def test_expansion_review_not_in_production(self, production_mode):
        """Production: expansion 7.9x does NOT trigger soft review (no soft gate in prod)."""
        data = make_verification_data(risk_level="low")
        # 7.9x is below the 8x hard block but would trigger legacy 10x review if it existed
        result = _call(data, content_length=7900, effective_source_len=1000)
        expansion_review = any("Expansao elevada" in r for r in result.review_reasons)
        assert not expansion_review

    def test_high_risk_review_legacy(self, legacy_mode):
        """Legacy: high risk that is not blocked triggers review."""
        data = make_verification_data(risk_level="high", is_verified=False)
        result = _call(data)
        assert result.human_review_required
        assert any("ALTO" in r for r in result.review_reasons)


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Edge cases and structural behavior."""

    def test_empty_verification_data(self, legacy_mode):
        """Empty dict uses safe defaults without errors."""
        result = _call({})
        assert isinstance(result, SafetyDecision)
        # risk_level defaults to "high", is_verified to False
        # In legacy mode, high risk is a review gate
        assert result.human_review_required

    def test_zero_total_claims_no_division_error(self, legacy_mode):
        """Zero total_claims does not cause division by zero."""
        data = make_verification_data(total_claims=0, unverifiable_claims=0)
        result = _call(data)
        assert isinstance(result, SafetyDecision)

    def test_prior_review_carried_forward(self, legacy_mode):
        """Prior human_review flag is preserved."""
        data = make_verification_data()
        result = _call(data, prior_human_review=True)
        assert result.human_review_required

    def test_prior_review_reasons_carried_forward(self, legacy_mode):
        """Prior review reasons are included in output."""
        data = make_verification_data()
        result = _call(
            data,
            prior_human_review=True,
            prior_review_reasons=["Reason A", "Reason B"],
        )
        assert "Reason A" in result.review_reasons
        assert "Reason B" in result.review_reasons

    def test_multiple_block_reasons_accumulated(self, production_mode):
        """Multiple block conditions accumulate reasons."""
        data = make_verification_data(
            risk_level="critical",
            confidence_score=0.30,
            is_verified=True,
            fabricated_claims=5,
        )
        result = _call(data)
        assert result.publish_blocked
        assert len(result.block_reasons) >= 3  # critical + confidence + fabricated

    def test_clean_pass(self, legacy_mode):
        """Clean data results in no blocks and no reviews."""
        data = make_verification_data()
        result = _call(data)
        assert not result.publish_blocked
        assert not result.human_review_required
        assert len(result.block_reasons) == 0
        assert len(result.review_reasons) == 0

    def test_clean_pass_production(self, production_mode):
        """Clean data in production mode also passes."""
        data = make_verification_data(risk_level="low", confidence_score=0.90)
        result = _call(data)
        assert not result.publish_blocked

    def test_block_prevents_fabrication_soft_review_production(self, production_mode):
        """Production: fabricated_claims=2 blocks; no duplicate review reason for fabrication."""
        data = make_verification_data(
            fabricated_claims=2, confidence_score=0.80, risk_level="low",
        )
        result = _call(data)
        assert result.publish_blocked
        # The soft gate for 1 fabricated should NOT fire since publish_blocked is True
        # and fabricated_claims != 1
        fabrication_review = any("fabricada" in r for r in result.review_reasons)
        assert not fabrication_review

    def test_returns_safety_decision_type(self, legacy_mode):
        """Return type is SafetyDecision dataclass."""
        result = _call({})
        assert isinstance(result, SafetyDecision)
        assert hasattr(result, "publish_blocked")
        assert hasattr(result, "block_reasons")
        assert hasattr(result, "human_review_required")
        assert hasattr(result, "review_reasons")


# =============================================================================
# BOUNDARY TESTS (parametrized)
# =============================================================================

class TestBoundaries:
    """Exact boundary and off-by-one tests for critical thresholds."""

    @pytest.mark.parametrize(
        "confidence,should_block",
        [
            (0.49, True),   # below floor
            (0.50, False),  # at floor (strict <)
            (0.51, False),  # above floor
        ],
    )
    def test_confidence_floor_production_boundary(
        self, production_mode, confidence, should_block
    ):
        """Production confidence floor boundary at 0.50."""
        data = make_verification_data(
            confidence_score=confidence, is_verified=True, risk_level="low",
            # Need to pass publish floors too
            grounded_claims=10, total_claims=10,
        )
        result = _call(data)
        confidence_blocked = any("baixa" in r.lower() for r in result.block_reasons)
        assert confidence_blocked == should_block

    @pytest.mark.parametrize(
        "confidence,should_block",
        [
            (0.39, True),   # below floor
            (0.40, False),  # at floor (strict <)
            (0.41, False),  # above floor
        ],
    )
    def test_confidence_floor_legacy_boundary(
        self, legacy_mode, confidence, should_block
    ):
        """Legacy confidence floor boundary at 0.40."""
        data = make_verification_data(
            confidence_score=confidence, is_verified=True,
        )
        result = _call(data)
        confidence_blocked = any("baixa" in r.lower() for r in result.block_reasons)
        assert confidence_blocked == should_block

    @pytest.mark.parametrize(
        "confidence,should_block",
        [
            (0.64, True),   # below floor
            (0.65, False),  # at floor
            (0.66, False),  # above floor
        ],
    )
    def test_publish_confidence_floor_boundary(
        self, production_mode, confidence, should_block
    ):
        """Production publish_confidence_floor boundary at 0.65."""
        data = make_verification_data(
            confidence_score=confidence, is_verified=True, risk_level="low",
            grounded_claims=10, total_claims=10,
        )
        result = _call(data)
        pub_blocked = any("piso" in r.lower() or "publicacao" in r.lower() for r in result.block_reasons)
        assert pub_blocked == should_block

    @pytest.mark.parametrize(
        "grounded,total,should_block",
        [
            (6, 10, True),   # 0.60 < 0.70
            (7, 10, False),  # 0.70 == floor
            (8, 10, False),  # 0.80 > floor
        ],
    )
    def test_grounded_floor_boundary(
        self, production_mode, grounded, total, should_block
    ):
        """Production grounded_ratio boundary at 0.70."""
        data = make_verification_data(
            confidence_score=0.80, is_verified=True, risk_level="low",
            grounded_claims=grounded, total_claims=total, context_claims=0,
        )
        result = _call(data)
        grounded_blocked = any("fundamentados" in r for r in result.block_reasons)
        assert grounded_blocked == should_block

    @pytest.mark.parametrize(
        "content_length,should_block",
        [
            (8000, False),  # 8.0x == limit (not >)
            (8001, True),   # 8.001x > limit
            (9000, True),   # 9.0x > limit
        ],
    )
    def test_expansion_production_boundary(
        self, production_mode, content_length, should_block
    ):
        """Production expansion boundary at 8.0x."""
        data = make_verification_data(risk_level="low")
        result = _call(data, content_length=content_length, effective_source_len=1000)
        expansion_blocked = any("Expansao extrema" in r for r in result.block_reasons)
        assert expansion_blocked == should_block

    @pytest.mark.parametrize(
        "content_length,should_block",
        [
            (15000, False),  # 15.0x == limit (not >)
            (15001, True),   # 15.001x > limit
            (20000, True),   # 20.0x > limit
        ],
    )
    def test_expansion_legacy_boundary(
        self, legacy_mode, content_length, should_block
    ):
        """Legacy expansion boundary at 15x."""
        data = make_verification_data()
        result = _call(data, content_length=content_length, effective_source_len=1000)
        expansion_blocked = any("Expansao extrema" in r for r in result.block_reasons)
        assert expansion_blocked == should_block
