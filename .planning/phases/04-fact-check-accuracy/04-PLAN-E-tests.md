---
wave: 2
depends_on:
  - 04-PLAN-B-temporal-classification-exa.md
  - 04-PLAN-C-embedding-crossref-cove-safety.md
files_modified:
  - FeedRSS/tmc-rss-collector/tests/test_phase4_temporal.py
  - FeedRSS/tmc-rss-collector/tests/test_generation_api.py
autonomous: true
---

# Plan E: Tests — Temporal Awareness Unit + Integration Tests

Creates test_phase4_temporal.py with unit tests for all Phase 4 components, and extends
test_generation_api.py with safety gate tests for recent_unverifiable.

## must_haves

- `test_phase4_temporal.py` exists with at least 10 test functions
- Tests cover: ExtractedClaim temporalidade field, temporal tier classification, cosine_sim, embedding cross-reference graceful degradation, recent_unverifiable confidence scoring, safety gate exclusion, feature flag behavior, _determine_risk_level temporal exclusion
- Existing `test_generation_api.py` has new tests for recent_unverifiable safety gate behavior
- All tests pass when run with `pytest`

## Tasks

<task id="E1" title="Create test_phase4_temporal.py with comprehensive temporal awareness tests">
<read_first>
- FeedRSS/tmc-rss-collector/tests/test_fact_check_improvements.py (lines 1–50 — existing test patterns, fixtures, imports)
- FeedRSS/tmc-rss-collector/tests/test_safety_gates.py (lines 1–50 — safety gate test patterns)
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 80–95 — ExtractedClaim dataclass)
- FeedRSS/tmc-rss-collector/services/fact_check_service.py (lines 135–205 — VerificationMetadata and to_dict)
</read_first>
<action>
Create `FeedRSS/tmc-rss-collector/tests/test_phase4_temporal.py`:

```python
"""Phase 4: Temporal awareness tests for breaking news fact-check pipeline."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta


# ==========================================
# 1. ExtractedClaim temporal field
# ==========================================

class TestExtractedClaimTemporalField:
    def test_default_temporalidade_is_historico(self):
        from services.fact_check_service import ExtractedClaim
        claim = ExtractedClaim(text="test claim")
        assert claim.temporalidade == "historico"

    def test_temporalidade_can_be_set(self):
        from services.fact_check_service import ExtractedClaim
        claim = ExtractedClaim(text="test", temporalidade="breaking")
        assert claim.temporalidade == "breaking"

    def test_temporalidade_in_to_dict(self):
        from services.fact_check_service import ExtractedClaim, VerificationMetadata
        claim = ExtractedClaim(text="test", temporalidade="recente")
        meta = VerificationMetadata(claims=[claim])
        d = meta.to_dict()
        assert d["claims"][0]["temporalidade"] == "recente"


# ==========================================
# 2. Temporal tier classification
# ==========================================

class TestTemporalTierClassification:
    @pytest.fixture
    def service(self):
        from services.fact_check_service import FactCheckService
        return FactCheckService()

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.fact_check_service._get_temporal_recent_days", return_value=7)
    def test_breaking_tier_for_1h_old(self, _days, _hours, _enabled, service):
        pub = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert service._get_temporal_tier(pub) == "breaking"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.fact_check_service._get_temporal_recent_days", return_value=7)
    def test_recente_tier_for_3d_old(self, _days, _hours, _enabled, service):
        pub = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        assert service._get_temporal_tier(pub) == "recente"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    @patch("services.fact_check_service._get_temporal_recent_days", return_value=7)
    def test_historico_tier_for_30d_old(self, _days, _hours, _enabled, service):
        pub = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        assert service._get_temporal_tier(pub) == "historico"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    def test_none_published_at_defaults_to_breaking(self, _enabled, service):
        assert service._get_temporal_tier(None) == "breaking"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    def test_invalid_date_defaults_to_breaking(self, _enabled, service):
        assert service._get_temporal_tier("not-a-date") == "breaking"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=False)
    def test_flag_off_always_returns_historico(self, _enabled, service):
        pub = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert service._get_temporal_tier(pub) == "historico"


# ==========================================
# 3. Cosine similarity
# ==========================================

class TestCosineSimPython:
    def test_identity_vectors(self):
        from services.fact_check_service import FactCheckService
        assert abs(FactCheckService._cosine_sim([1, 0, 0], [1, 0, 0]) - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        from services.fact_check_service import FactCheckService
        assert abs(FactCheckService._cosine_sim([1, 0, 0], [0, 1, 0])) < 0.001

    def test_zero_vector(self):
        from services.fact_check_service import FactCheckService
        assert FactCheckService._cosine_sim([0, 0, 0], [1, 0, 0]) == 0.0

    def test_opposite_vectors(self):
        from services.fact_check_service import FactCheckService
        sim = FactCheckService._cosine_sim([1, 0], [-1, 0])
        assert sim <= 0.0


# ==========================================
# 4. Embedding cross-reference
# ==========================================

class TestEmbeddingCrossReference:
    @pytest.fixture
    def service(self):
        from services.fact_check_service import FactCheckService
        return FactCheckService()

    @pytest.mark.asyncio
    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    async def test_corroborated_returns_true(self, _hours, _enabled, service):
        """3+ articles with high similarity → returns True."""
        mock_embedding = [0.5] * 1536
        mock_articles = [
            {"id": i, "title": f"Article {i}", "embedding": mock_embedding}
            for i in range(5)
        ]

        with patch("services.fact_check_service.EmbeddingService", autospec=True) as MockEmbed, \
             patch("services.fact_check_service.get_db") as mock_get_db:
            MockEmbed.return_value.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get_db.return_value.get_recent_articles_with_embeddings.return_value = mock_articles

            result = await service._cross_reference_with_embeddings("test claim")
            assert result is True

    @pytest.mark.asyncio
    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    async def test_few_articles_returns_false(self, _hours, _enabled, service):
        """Less than min_corroborating articles → returns False."""
        with patch("services.fact_check_service.EmbeddingService", autospec=True) as MockEmbed, \
             patch("services.fact_check_service.get_db") as mock_get_db:
            MockEmbed.return_value.generate_embedding = AsyncMock(return_value=[0.5] * 1536)
            mock_get_db.return_value.get_recent_articles_with_embeddings.return_value = [
                {"id": 1, "title": "A1", "embedding": [0.5] * 1536}
            ]

            result = await service._cross_reference_with_embeddings("test claim")
            assert result is False

    @pytest.mark.asyncio
    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=True)
    @patch("services.fact_check_service._get_temporal_breaking_hours", return_value=48)
    async def test_exception_returns_false(self, _hours, _enabled, service):
        """DB or embedding error → returns False (graceful degradation)."""
        with patch("services.fact_check_service.EmbeddingService", side_effect=Exception("DB down")):
            result = await service._cross_reference_with_embeddings("test claim")
            assert result is False

    @pytest.mark.asyncio
    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=False)
    async def test_flag_off_returns_false(self, _enabled, service):
        """Feature flag OFF → returns False immediately."""
        result = await service._cross_reference_with_embeddings("test claim")
        assert result is False


# ==========================================
# 5. VerificationMetadata count split
# ==========================================

class TestVerificationMetadataCountSplit:
    def test_recent_unverifiable_in_to_dict(self):
        from services.fact_check_service import VerificationMetadata
        m = VerificationMetadata(
            unverifiable_claims=2,
            recent_unverifiable_claims=3,
        )
        d = m.to_dict()
        assert d["unverifiable_claims"] == 2
        assert d["recent_unverifiable_claims"] == 3

    def test_default_recent_unverifiable_is_zero(self):
        from services.fact_check_service import VerificationMetadata
        m = VerificationMetadata()
        assert m.recent_unverifiable_claims == 0
        assert m.to_dict()["recent_unverifiable_claims"] == 0


# ==========================================
# 6. Safety gate: recent_unverifiable excluded
# ==========================================

class TestSafetyGateTemporalExclusion:
    def test_recent_unverifiable_does_not_hard_block(self):
        """Many recent_unverifiable + zero standard unverifiable → no block."""
        from functions.generation_api import evaluate_safety_gates
        decision = evaluate_safety_gates(
            verification_data={
                "confidence_score": 0.80,
                "risk_level": "medium",
                "fabricated_claims": 0,
                "unverifiable_claims": 0,
                "recent_unverifiable_claims": 5,
                "total_claims": 10,
                "grounded_claims": 5,
                "context_claims": 0,
                "is_verified": True,
            },
            content_length=2000,
            effective_source_len=1000,
        )
        assert not decision.publish_blocked, f"Should NOT block: {decision.block_reasons}"

    def test_standard_unverifiable_still_blocks(self):
        """Standard unverifiable >= 3 and > 40% → still blocks."""
        from functions.generation_api import evaluate_safety_gates
        decision = evaluate_safety_gates(
            verification_data={
                "confidence_score": 0.80,
                "risk_level": "medium",
                "fabricated_claims": 0,
                "unverifiable_claims": 5,
                "recent_unverifiable_claims": 0,
                "total_claims": 10,
                "grounded_claims": 5,
                "context_claims": 0,
                "is_verified": True,
            },
            content_length=2000,
            effective_source_len=1000,
        )
        assert decision.publish_blocked, "Standard unverifiable should still block"

    def test_fabricated_still_blocks_with_temporal(self):
        """Fabricated claims still block even when recent_unverifiable present (D-14)."""
        from functions.generation_api import evaluate_safety_gates
        decision = evaluate_safety_gates(
            verification_data={
                "confidence_score": 0.80,
                "risk_level": "medium",
                "fabricated_claims": 2,
                "unverifiable_claims": 0,
                "recent_unverifiable_claims": 3,
                "total_claims": 10,
                "grounded_claims": 5,
                "context_claims": 0,
                "is_verified": True,
            },
            content_length=2000,
            effective_source_len=1000,
        )
        assert decision.publish_blocked, "Fabricated should block regardless of temporal"

    def test_recent_unverifiable_triggers_human_review(self):
        """recent_unverifiable > 0 → human_review_required = True."""
        from functions.generation_api import evaluate_safety_gates
        decision = evaluate_safety_gates(
            verification_data={
                "confidence_score": 0.85,
                "risk_level": "low",
                "fabricated_claims": 0,
                "unverifiable_claims": 0,
                "recent_unverifiable_claims": 2,
                "total_claims": 10,
                "grounded_claims": 8,
                "context_claims": 0,
                "is_verified": True,
            },
            content_length=2000,
            effective_source_len=1000,
        )
        assert decision.human_review_required, "recent_unverifiable should require human review"
        assert any("recente" in r for r in decision.review_reasons)


# ==========================================
# 7. Feature flag OFF restores pre-Phase-4 behavior
# ==========================================

class TestTemporalAwarenessFeatureFlag:
    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=False)
    def test_flag_off_temporalidade_defaults_historico(self, _enabled):
        from services.fact_check_service import ExtractedClaim
        # When flag off, parsing should always default to historico
        claim = ExtractedClaim(text="test")
        assert claim.temporalidade == "historico"

    @patch("services.fact_check_service._get_temporal_awareness_enabled", return_value=False)
    def test_flag_off_tier_always_historico(self, _enabled):
        from services.fact_check_service import FactCheckService
        svc = FactCheckService()
        pub = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert svc._get_temporal_tier(pub) == "historico"


# ==========================================
# 8. Risk level excludes recent_unverifiable
# ==========================================

class TestRiskLevelTemporalExclusion:
    """Verify _determine_risk_level() does NOT escalate based on recent_unverifiable.

    Issue 4/5: When recent_unverifiable >= 3 and standard unverifiable == 0,
    risk level must NOT escalate to "high". The split count in C3 ensures
    metadata.unverifiable_claims only contains standard unverifiable.
    """

    def test_recent_unverifiable_high_count_no_escalation(self):
        """3+ recent_unverifiable + 0 standard unverifiable → risk stays low/medium."""
        from services.fact_check_service import FactCheckService, VerificationMetadata, ExtractedClaim
        from services.fact_check_service import EntityComparisonResult, QuoteVerificationResult

        svc = FactCheckService()
        metadata = VerificationMetadata()
        # 10 claims: 5 grounded, 5 recent_unverifiable, 0 standard unverifiable
        metadata.total_claims = 10
        metadata.grounded_claims = 5
        metadata.fabricated_claims = 0
        metadata.unverifiable_claims = 0  # Standard unverifiable = 0
        metadata.recent_unverifiable_claims = 5  # All temporal
        metadata.confidence_score = 0.80
        metadata.expansion_ratio = 3.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult()
        entity_result.overlap_score = 0.8
        entity_result.novel_entities = []

        quote_result = QuoteVerificationResult()

        risk = svc._determine_risk_level(metadata, entity_result, quote_result)
        assert risk != "high", (
            f"Risk should NOT be 'high' when only recent_unverifiable present, got '{risk}'"
        )
        assert risk != "critical", (
            f"Risk should NOT be 'critical' when only recent_unverifiable present, got '{risk}'"
        )

    def test_standard_unverifiable_still_escalates(self):
        """3+ standard unverifiable at >40% → risk DOES escalate (regression guard)."""
        from services.fact_check_service import FactCheckService, VerificationMetadata
        from services.fact_check_service import EntityComparisonResult, QuoteVerificationResult

        svc = FactCheckService()
        metadata = VerificationMetadata()
        metadata.total_claims = 6
        metadata.grounded_claims = 2
        metadata.fabricated_claims = 0
        metadata.unverifiable_claims = 4  # Standard: 4/6 = 67% > 40%
        metadata.recent_unverifiable_claims = 0
        metadata.confidence_score = 0.50
        metadata.expansion_ratio = 3.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult()
        entity_result.overlap_score = 0.8
        entity_result.novel_entities = []

        quote_result = QuoteVerificationResult()

        risk = svc._determine_risk_level(metadata, entity_result, quote_result)
        assert risk == "high", (
            f"Risk should be 'high' when standard unverifiable >= 3 and > 40%, got '{risk}'"
        )

    def test_mixed_counts_only_standard_triggers(self):
        """Mix of standard + recent: only standard count triggers escalation."""
        from services.fact_check_service import FactCheckService, VerificationMetadata
        from services.fact_check_service import EntityComparisonResult, QuoteVerificationResult

        svc = FactCheckService()
        metadata = VerificationMetadata()
        metadata.total_claims = 10
        metadata.grounded_claims = 3
        metadata.fabricated_claims = 0
        metadata.unverifiable_claims = 2  # Standard: 2/10 = 20% — below threshold
        metadata.recent_unverifiable_claims = 5  # These should NOT count
        metadata.confidence_score = 0.60
        metadata.expansion_ratio = 3.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult()
        entity_result.overlap_score = 0.8
        entity_result.novel_entities = []

        quote_result = QuoteVerificationResult()

        risk = svc._determine_risk_level(metadata, entity_result, quote_result)
        # 2 standard unverifiable < 3 threshold, so should NOT escalate
        assert risk != "high", (
            f"Risk should NOT be 'high' when standard unverifiable=2 < 3 threshold, got '{risk}'"
        )
```

This file contains 25 test functions across 8 test classes.
</action>
<acceptance_criteria>
- File `FeedRSS/tmc-rss-collector/tests/test_phase4_temporal.py` exists
- `grep -c "def test_" FeedRSS/tmc-rss-collector/tests/test_phase4_temporal.py` returns at least 23
- `grep -c "class Test" FeedRSS/tmc-rss-collector/tests/test_phase4_temporal.py` returns at least 8
- `grep "pytest.mark.asyncio" FeedRSS/tmc-rss-collector/tests/test_phase4_temporal.py` returns at least 3 matches
- `grep "recent_unverifiable" FeedRSS/tmc-rss-collector/tests/test_phase4_temporal.py` returns at least 10 matches
- `cd FeedRSS/tmc-rss-collector && python -m pytest tests/test_phase4_temporal.py -v` exits 0
</acceptance_criteria>
</task>

<task id="E2" title="Extend test_generation_api.py with temporal safety gate tests">
<read_first>
- FeedRSS/tmc-rss-collector/tests/test_generation_api.py (lines 1–50 — existing imports and test patterns for evaluate_safety_gates)
</read_first>
<action>
At the end of `tests/test_generation_api.py`, add:

```python

# ==========================================
# Phase 4: Temporal safety gate tests
# ==========================================

class TestSafetyGatesTemporalPhase4:
    """Verify evaluate_safety_gates() correctly handles recent_unverifiable (Phase 4)."""

    def test_recent_unverifiable_not_blocked(self):
        """D-13: recent_unverifiable excluded from hard block count."""
        decision = evaluate_safety_gates(
            verification_data={
                "confidence_score": 0.80,
                "risk_level": "medium",
                "fabricated_claims": 0,
                "unverifiable_claims": 0,
                "recent_unverifiable_claims": 6,
                "total_claims": 10,
                "grounded_claims": 4,
                "context_claims": 0,
                "is_verified": True,
            },
            content_length=2000,
            effective_source_len=1000,
        )
        assert not decision.publish_blocked

    def test_fabricated_still_blocks_with_recent_unverifiable(self):
        """D-14: fabricated claims still hard-block regardless of temporal status."""
        decision = evaluate_safety_gates(
            verification_data={
                "confidence_score": 0.80,
                "risk_level": "medium",
                "fabricated_claims": 2,
                "unverifiable_claims": 0,
                "recent_unverifiable_claims": 3,
                "total_claims": 10,
                "grounded_claims": 5,
                "context_claims": 0,
                "is_verified": True,
            },
            content_length=2000,
            effective_source_len=1000,
        )
        assert decision.publish_blocked

    def test_mixed_standard_and_recent_unverifiable(self):
        """Standard unverifiable triggers block even if recent_unverifiable is also present."""
        decision = evaluate_safety_gates(
            verification_data={
                "confidence_score": 0.80,
                "risk_level": "medium",
                "fabricated_claims": 0,
                "unverifiable_claims": 5,
                "recent_unverifiable_claims": 3,
                "total_claims": 10,
                "grounded_claims": 2,
                "context_claims": 0,
                "is_verified": True,
            },
            content_length=2000,
            effective_source_len=1000,
        )
        assert decision.publish_blocked
```

Ensure the `evaluate_safety_gates` import exists at the top of the file. If not already imported, add it.
</action>
<acceptance_criteria>
- `grep "TestSafetyGatesTemporalPhase4" FeedRSS/tmc-rss-collector/tests/test_generation_api.py` returns 1 match
- `grep -c "recent_unverifiable" FeedRSS/tmc-rss-collector/tests/test_generation_api.py` returns at least 6
- `cd FeedRSS/tmc-rss-collector && python -m pytest tests/test_generation_api.py -v -k "Phase4"` exits 0
</acceptance_criteria>
</task>

## Verification

```bash
cd FeedRSS/tmc-rss-collector
python -m pytest tests/test_phase4_temporal.py tests/test_generation_api.py -v --tb=short
```
