"""
Tests for Phase 4: Temporal Awareness Pipeline.

Covers:
1. ExtractedClaim.temporalidade field (default, setting, serialization)
2. Temporal tier classification (breaking, recente, historico)
3. Pure-Python cosine similarity
4. Embedding cross-reference (corroborated, few articles, exception, flag off)
5. VerificationMetadata.recent_unverifiable_claims count split
6. Safety gate temporal exclusion (recent_unverifiable doesn't block)
7. Feature flag toggling (temporal_awareness_enabled)
8. Risk level temporal exclusion (recent_unverifiable doesn't escalate)
"""

import sys
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.fact_check_service import (
    FactCheckService,
    ExtractedClaim,
    VerificationMetadata,
    EntityComparisonResult,
    QuoteVerificationResult,
)


# ===========================================================================
# 1. ExtractedClaim.temporalidade field
# ===========================================================================

class TestExtractedClaimTemporalField:
    """Test the temporalidade field on ExtractedClaim."""

    def test_default_is_historico(self):
        """Default temporalidade should be 'historico'."""
        claim = ExtractedClaim(text="Test claim")
        assert claim.temporalidade == "historico"

    def test_setting_breaking(self):
        """Can set temporalidade to 'breaking'."""
        claim = ExtractedClaim(text="Breaking claim", temporalidade="breaking")
        assert claim.temporalidade == "breaking"

    def test_setting_recente(self):
        """Can set temporalidade to 'recente'."""
        claim = ExtractedClaim(text="Recent claim", temporalidade="recente")
        assert claim.temporalidade == "recente"

    def test_serialization_in_to_dict(self):
        """temporalidade appears in VerificationMetadata.to_dict() claims."""
        claim = ExtractedClaim(text="Test", temporalidade="breaking", verdict="grounded")
        metadata = VerificationMetadata(claims=[claim], total_claims=1, grounded_claims=1)
        d = metadata.to_dict()
        assert d["claims"][0]["temporalidade"] == "breaking"

    def test_serialization_historico_default(self):
        """Default temporalidade appears as 'historico' in serialized output."""
        claim = ExtractedClaim(text="Default claim")
        metadata = VerificationMetadata(claims=[claim], total_claims=1)
        d = metadata.to_dict()
        assert d["claims"][0]["temporalidade"] == "historico"


# ===========================================================================
# 2. Temporal tier classification
# ===========================================================================

class TestTemporalTierClassification:
    """Test FactCheckService._get_temporal_tier()."""

    @pytest.fixture
    def service(self):
        return FactCheckService()

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.fact_check_service._get_temporal_recent_days", return_value=7)
    def test_breaking_within_hours(self, _recent, _breaking, _enabled, service):
        """Article published 1 hour ago should be 'breaking'."""
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert service._get_temporal_tier(one_hour_ago) == "breaking"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.fact_check_service._get_temporal_recent_days", return_value=7)
    def test_recente_within_days(self, _recent, _breaking, _enabled, service):
        """Article published 3 days ago should be 'recente'."""
        three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        assert service._get_temporal_tier(three_days_ago) == "recente"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.fact_check_service._get_temporal_recent_days", return_value=7)
    def test_historico_old_article(self, _recent, _breaking, _enabled, service):
        """Article published 30 days ago should be 'historico'."""
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        assert service._get_temporal_tier(thirty_days_ago) == "historico"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.fact_check_service._get_temporal_recent_days", return_value=7)
    def test_none_published_at_returns_breaking(self, _recent, _breaking, _enabled, service):
        """None published_at should default to 'breaking'."""
        assert service._get_temporal_tier(None) == "breaking"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.fact_check_service._get_temporal_recent_days", return_value=7)
    def test_invalid_iso_returns_breaking(self, _recent, _breaking, _enabled, service):
        """Invalid ISO string should fallback to 'breaking'."""
        assert service._get_temporal_tier("not-a-date") == "breaking"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=False)
    def test_flag_off_returns_historico(self, _enabled, service):
        """When temporal_awareness_enabled is False, always return 'historico'."""
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert service._get_temporal_tier(one_hour_ago) == "historico"


# ===========================================================================
# 3. Pure-Python cosine similarity
# ===========================================================================

class TestCosineSimPython:
    """Test FactCheckService._cosine_sim() static method."""

    def test_identity_vectors(self):
        """Identical vectors should have similarity 1.0."""
        v = [1.0, 2.0, 3.0]
        assert abs(FactCheckService._cosine_sim(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity 0.0."""
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(FactCheckService._cosine_sim(a, b)) < 1e-9

    def test_zero_vector(self):
        """Zero vector should return 0.0 (no division error)."""
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert FactCheckService._cosine_sim(a, b) == 0.0

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity -1.0."""
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(FactCheckService._cosine_sim(a, b) - (-1.0)) < 1e-9

    def test_similar_vectors(self):
        """Similar vectors should have high positive similarity."""
        a = [1.0, 2.0, 3.0]
        b = [1.1, 2.1, 3.1]
        sim = FactCheckService._cosine_sim(a, b)
        assert sim > 0.99


# ===========================================================================
# 4. Embedding cross-reference
# ===========================================================================

class TestEmbeddingCrossReference:
    """Test FactCheckService._cross_reference_with_embeddings()."""

    @pytest.fixture
    def service(self):
        return FactCheckService()

    @pytest.mark.asyncio
    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.database.get_db")
    @patch("services.embedding_service.EmbeddingService")
    async def test_corroborated_returns_true(self, MockEmbed, mock_get_db, _breaking, _enabled, service):
        """Returns True when 3+ articles corroborate the claim."""
        import json
        # Mock embedding service
        embed_instance = MockEmbed.return_value
        embed_instance.generate_embedding = AsyncMock(return_value=[1.0, 0.0, 0.0])

        # Mock DB returning 4 articles with similar embeddings
        mock_db = MagicMock()
        mock_db.get_recent_articles_with_embeddings.return_value = [
            {"embedding": json.dumps([1.0, 0.0, 0.0])},
            {"embedding": json.dumps([0.99, 0.01, 0.0])},
            {"embedding": json.dumps([0.98, 0.02, 0.0])},
            {"embedding": json.dumps([0.97, 0.03, 0.0])},
        ]
        mock_get_db.return_value = mock_db

        result = await service._cross_reference_with_embeddings("Test claim")
        assert result is True

    @pytest.mark.asyncio
    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.database.get_db")
    @patch("services.embedding_service.EmbeddingService")
    async def test_few_articles_returns_false(self, MockEmbed, mock_get_db, _breaking, _enabled, service):
        """Returns False when fewer than min_corroborating articles exist."""
        embed_instance = MockEmbed.return_value
        embed_instance.generate_embedding = AsyncMock(return_value=[1.0, 0.0, 0.0])

        mock_db = MagicMock()
        mock_db.get_recent_articles_with_embeddings.return_value = [
            {"embedding": "[1.0, 0.0, 0.0]"},
            {"embedding": "[0.99, 0.01, 0.0]"},
        ]
        mock_get_db.return_value = mock_db

        result = await service._cross_reference_with_embeddings("Test claim")
        assert result is False

    @pytest.mark.asyncio
    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.database.get_db")
    @patch("services.embedding_service.EmbeddingService")
    async def test_exception_returns_false(self, MockEmbed, mock_get_db, _breaking, _enabled, service):
        """Returns False on any exception (graceful degradation)."""
        embed_instance = MockEmbed.return_value
        embed_instance.generate_embedding = AsyncMock(side_effect=Exception("API error"))

        result = await service._cross_reference_with_embeddings("Test claim")
        assert result is False

    @pytest.mark.asyncio
    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=False)
    async def test_flag_off_returns_false(self, _enabled, service):
        """Returns False immediately when feature flag is off."""
        result = await service._cross_reference_with_embeddings("Test claim")
        assert result is False


# ===========================================================================
# 5. VerificationMetadata.recent_unverifiable_claims count split
# ===========================================================================

class TestVerificationMetadataCountSplit:
    """Test recent_unverifiable_claims in VerificationMetadata."""

    def test_default_is_zero(self):
        """Default recent_unverifiable_claims should be 0."""
        metadata = VerificationMetadata()
        assert metadata.recent_unverifiable_claims == 0

    def test_in_to_dict(self):
        """recent_unverifiable_claims should appear in to_dict()."""
        metadata = VerificationMetadata(recent_unverifiable_claims=5)
        d = metadata.to_dict()
        assert d["recent_unverifiable_claims"] == 5

    def test_set_value(self):
        """Can set recent_unverifiable_claims to a custom value."""
        metadata = VerificationMetadata(recent_unverifiable_claims=3)
        assert metadata.recent_unverifiable_claims == 3

    def test_separate_from_unverifiable(self):
        """recent_unverifiable_claims is separate from unverifiable_claims."""
        metadata = VerificationMetadata(
            unverifiable_claims=2,
            recent_unverifiable_claims=4,
        )
        assert metadata.unverifiable_claims == 2
        assert metadata.recent_unverifiable_claims == 4
        d = metadata.to_dict()
        assert d["unverifiable_claims"] == 2
        assert d["recent_unverifiable_claims"] == 4


# ===========================================================================
# 6. Safety gate temporal exclusion
# ===========================================================================

class TestSafetyGateTemporalExclusion:
    """Test that evaluate_safety_gates() handles recent_unverifiable correctly."""

    def _evaluate(self, **overrides):
        from functions.generation_api import evaluate_safety_gates
        base = {
            "confidence_score": 0.80,
            "risk_level": "medium",
            "fabricated_claims": 0,
            "unverifiable_claims": 0,
            "recent_unverifiable_claims": 0,
            "total_claims": 10,
            "grounded_claims": 8,
            "context_claims": 0,
            "is_verified": True,
        }
        base.update(overrides)
        return evaluate_safety_gates(
            verification_data=base,
            content_length=2000,
            effective_source_len=1000,
        )

    def test_recent_unverifiable_does_not_block(self):
        """High recent_unverifiable_claims alone should NOT cause a block."""
        decision = self._evaluate(recent_unverifiable_claims=6)
        assert not decision.publish_blocked

    def test_standard_unverifiable_blocks(self):
        """Standard unverifiable_claims > 40% of total SHOULD block."""
        decision = self._evaluate(
            unverifiable_claims=5,
            total_claims=10,
            grounded_claims=3,
        )
        assert decision.publish_blocked

    def test_fabricated_still_blocks(self):
        """fabricated_claims still block even with recent_unverifiable present."""
        decision = self._evaluate(
            fabricated_claims=3,
            recent_unverifiable_claims=3,
        )
        assert decision.publish_blocked

    def test_recent_unverifiable_triggers_human_review_when_high(self):
        """High recent_unverifiable count should NOT trigger block, but article
        may still get human review from other signals like risk_level=high."""
        decision = self._evaluate(
            recent_unverifiable_claims=8,
            risk_level="medium",
        )
        # recent_unverifiable alone does NOT block
        assert not decision.publish_blocked


# ===========================================================================
# 7. Feature flag toggling
# ===========================================================================

class TestTemporalAwarenessFeatureFlag:
    """Test temporal_awareness_enabled feature flag behavior."""

    @pytest.fixture
    def service(self):
        return FactCheckService()

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=False)
    def test_flag_off_temporalidade_defaults_historico(self, _enabled, service):
        """When flag is off, _get_temporal_tier always returns 'historico'."""
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert service._get_temporal_tier(recent) == "historico"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=False)
    def test_flag_off_tier_always_historico(self, _enabled, service):
        """When flag is off, even None published_at returns 'historico'."""
        assert service._get_temporal_tier(None) == "historico"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.fact_check_service._get_temporal_recent_days", return_value=7)
    def test_flag_on_enables_classification(self, _recent, _breaking, _enabled, service):
        """When flag is on, tier classification works normally."""
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert service._get_temporal_tier(one_hour_ago) == "breaking"

        four_days_ago = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
        assert service._get_temporal_tier(four_days_ago) == "recente"

        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        assert service._get_temporal_tier(thirty_days_ago) == "historico"


# ===========================================================================
# 8. Risk level temporal exclusion
# ===========================================================================

class TestRiskLevelTemporalExclusion:
    """Test that _determine_risk_level() uses only standard unverifiable_claims."""

    @pytest.fixture
    def service(self):
        return FactCheckService()

    def _make_metadata(self, **overrides):
        """Build a VerificationMetadata with safe defaults."""
        defaults = dict(
            confidence_score=0.70,
            risk_level="medium",
            total_claims=10,
            grounded_claims=7,
            fabricated_claims=0,
            unverifiable_claims=0,
            recent_unverifiable_claims=0,
            context_claims=0,
            expansion_ratio=2.0,
            claims=[],
        )
        defaults.update(overrides)
        return VerificationMetadata(**defaults)

    def test_recent_unverifiable_high_count_no_escalation(self, service):
        """High recent_unverifiable_claims should NOT escalate risk level."""
        metadata = self._make_metadata(
            confidence_score=0.70,
            recent_unverifiable_claims=8,
            unverifiable_claims=0,
        )
        entity_result = EntityComparisonResult(overlap_score=0.8, novel_entities=[])
        quote_result = QuoteVerificationResult()

        level = service._determine_risk_level(metadata, entity_result, quote_result)
        # confidence 0.70 -> base level is "medium"; no escalation triggers
        assert level == "medium"

    def test_standard_unverifiable_still_escalates(self, service):
        """Standard unverifiable_claims >= 3 at > 40% SHOULD escalate to 'high'."""
        metadata = self._make_metadata(
            confidence_score=0.70,
            unverifiable_claims=5,
            total_claims=10,
        )
        entity_result = EntityComparisonResult(overlap_score=0.8, novel_entities=[])
        quote_result = QuoteVerificationResult()

        level = service._determine_risk_level(metadata, entity_result, quote_result)
        assert level == "high"

    def test_mixed_only_standard_triggers(self, service):
        """With both standard and recent_unverifiable, only standard triggers escalation."""
        # Only 1 standard unverifiable (below threshold) + 8 recent_unverifiable
        metadata = self._make_metadata(
            confidence_score=0.70,
            unverifiable_claims=1,
            recent_unverifiable_claims=8,
            total_claims=10,
        )
        entity_result = EntityComparisonResult(overlap_score=0.8, novel_entities=[])
        quote_result = QuoteVerificationResult()

        level = service._determine_risk_level(metadata, entity_result, quote_result)
        # 1 unverifiable out of 10 = 10%, below 40% threshold -> no escalation
        assert level == "medium"

    def test_standard_unverifiable_at_threshold_escalates(self, service):
        """Standard unverifiable at exactly the threshold should escalate."""
        metadata = self._make_metadata(
            confidence_score=0.70,
            unverifiable_claims=5,
            recent_unverifiable_claims=0,
            total_claims=10,
        )
        entity_result = EntityComparisonResult(overlap_score=0.8, novel_entities=[])
        quote_result = QuoteVerificationResult()

        level = service._determine_risk_level(metadata, entity_result, quote_result)
        # 5/10 = 50% > 40% -> escalate to "high"
        assert level == "high"

    def test_fabricated_still_escalates(self, service):
        """Fabricated claims still escalate risk regardless of recent_unverifiable."""
        metadata = self._make_metadata(
            confidence_score=0.70,
            fabricated_claims=3,
            recent_unverifiable_claims=5,
        )
        entity_result = EntityComparisonResult(overlap_score=0.8, novel_entities=[])
        quote_result = QuoteVerificationResult()

        level = service._determine_risk_level(metadata, entity_result, quote_result)
        assert level == "critical"
