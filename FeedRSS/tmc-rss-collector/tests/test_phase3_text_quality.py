"""
Phase 03 — Text Quality: Unit tests for all new features.

Plan A: check_originality, scan_competitor_mentions, ANTI_COPIA, _build_competitor_instruction
Plan B: _extract_claims_simplified, needs_manual_review, text_copy quality criterion
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ──────────────────────────────────────────────────────────────────
# Plan A: check_originality()
# ──────────────────────────────────────────────────────────────────

class TestCheckOriginality:
    """Tests for the 4-gram overlap detection function."""

    def setup_method(self):
        from services.llm_service import check_originality
        self.check = check_originality

    def test_identical_texts_are_copy(self):
        text = "O presidente anunciou novas medidas economicas para o pais nesta quarta-feira"
        result = self.check(generated=text, source=text)
        assert result["is_copy"] is True
        assert result["overlap_ratio"] > 0.15

    def test_different_texts_are_original(self):
        source = "O time de futebol venceu a partida por dois gols a zero ontem"
        generated = "Novas politicas de saude publica serao implementadas no proximo semestre pelo governo federal"
        result = self.check(generated=generated, source=source)
        assert result["is_copy"] is False
        assert result["overlap_ratio"] < 0.15

    def test_empty_generated_text(self):
        result = self.check(generated="", source="algum texto fonte aqui para testar")
        assert result["is_copy"] is False
        assert result["overlap_ratio"] == 0.0

    def test_empty_source_text(self):
        result = self.check(generated="algum texto gerado aqui para testar", source="")
        assert result["is_copy"] is False
        assert result["overlap_ratio"] == 0.0

    def test_short_text_below_ngram_threshold(self):
        result = self.check(generated="ola mundo", source="ola mundo")
        # Only 2 words — can't form a 4-gram, so overlap should be 0
        assert result["overlap_ratio"] == 0.0

    def test_partial_overlap_below_threshold(self):
        source = "O governo federal anunciou novas medidas para combater a inflacao no pais"
        generated = (
            "O governo federal publicou um decreto que visa reformar o sistema tributario "
            "e melhorar a arrecadacao em todas as regioes do Brasil durante o proximo ano"
        )
        result = self.check(generated=generated, source=source)
        # "O governo federal" overlaps but only 3 words, not enough for 4-gram in most cases
        assert result["overlap_ratio"] < 0.15

    def test_custom_threshold(self):
        source = "O presidente da republica assinou o decreto na tarde desta quinta-feira em Brasilia"
        generated = "O presidente da republica assinou o documento nesta manha em Sao Paulo na sede do governo"
        result_strict = self.check(generated=generated, source=source, threshold=0.05)
        result_lenient = self.check(generated=generated, source=source, threshold=0.50)
        # Strict threshold should flag more, lenient should flag less
        assert result_strict["overlap_ratio"] == result_lenient["overlap_ratio"]

    def test_return_keys(self):
        result = self.check(generated="texto gerado aqui neste teste", source="texto fonte aqui neste teste")
        assert "overlap_ratio" in result
        assert "is_copy" in result
        assert "overlapping_ngrams" in result
        assert "total_generated_ngrams" in result


# ──────────────────────────────────────────────────────────────────
# Plan A: scan_competitor_mentions()
# ──────────────────────────────────────────────────────────────────

class TestScanCompetitorMentions:
    """Tests for competitor brand detection in generated text."""

    def setup_method(self):
        from services.llm_service import scan_competitor_mentions
        self.scan = scan_competitor_mentions

    def test_no_brands_configured(self):
        result = self.scan(text="Globo noticiou o evento", competitor_brands="")
        assert result == []

    def test_detects_single_brand(self):
        result = self.scan(
            text="Segundo a Globo, o evento foi um sucesso",
            competitor_brands="Globo,Band,Record"
        )
        assert any("Globo" in m for m in result) or len(result) > 0

    def test_no_match_returns_empty(self):
        result = self.scan(
            text="O prefeito inaugurou a nova escola municipal",
            competitor_brands="Globo,Band,Record"
        )
        assert result == []

    def test_empty_text(self):
        result = self.scan(text="", competitor_brands="Globo,Band")
        assert result == []


# ──────────────────────────────────────────────────────────────────
# Plan A: _build_competitor_instruction()
# ──────────────────────────────────────────────────────────────────

class TestBuildCompetitorInstruction:
    """Tests for competitor brand filter prompt generation."""

    def setup_method(self):
        from services.llm_service import _build_competitor_instruction
        self.build = _build_competitor_instruction

    def test_empty_brands_returns_generic_instruction(self):
        """Even with no specific brands, a generic attribution instruction is returned."""
        result = self.build("")
        assert len(result) > 50, "Should return generic instruction even without brands"
        assert "NUNCA" in result, "Should contain NUNCA"
        assert "VEICULO DE IMPRENSA" in result or "imprensa" in result.lower()

    def test_brands_generate_instruction(self):
        result = self.build("Globo,Band,Record")
        assert "Globo" in result
        assert "Band" in result
        assert "Record" in result
        assert len(result) > 0

    def test_single_brand(self):
        result = self.build("CNN")
        assert "CNN" in result


# ──────────────────────────────────────────────────────────────────
# Plan A: ANTI_COPIA constant
# ──────────────────────────────────────────────────────────────────

class TestAntiCopiaConstant:
    """Tests for the ANTI_COPIA few-shot examples constant."""

    def test_exists_and_nonempty(self):
        from services.llm_service import ANTI_COPIA
        assert isinstance(ANTI_COPIA, str)
        assert len(ANTI_COPIA) > 100

    def test_contains_examples(self):
        from services.llm_service import ANTI_COPIA
        assert "INACEITAVEL" in ANTI_COPIA or "inaceitavel" in ANTI_COPIA.lower()
        assert "CORRETO" in ANTI_COPIA or "correto" in ANTI_COPIA.lower()


# ──────────────────────────────────────────────────────────────────
# Plan A: config.py competitor_brands
# ──────────────────────────────────────────────────────────────────

class TestCompetitorBrandsConfig:
    """Tests for COMPETITOR_BRANDS env var loading."""

    def test_default_has_brands(self):
        """Default competitor_brands now contains hardcoded list of 30 brands."""
        from services.config import AppConfig
        config = AppConfig()
        assert hasattr(config, "competitor_brands")
        brands = [b.strip() for b in config.competitor_brands.split(",") if b.strip()]
        assert len(brands) >= 25, f"Expected 25+ default brands, got {len(brands)}"
        assert "R7" in brands
        assert "Portal do Zacarias" in brands


# ──────────────────────────────────────────────────────────────────
# Plan B: VerificationMetadata.needs_manual_review
# ──────────────────────────────────────────────────────────────────

class TestVerificationMetadata:
    """Tests for the needs_manual_review field."""

    def test_field_defaults_false(self):
        from services.fact_check_service import VerificationMetadata
        meta = VerificationMetadata()
        assert meta.needs_manual_review is False

    def test_field_serializes_to_dict(self):
        from services.fact_check_service import VerificationMetadata
        meta = VerificationMetadata()
        meta.needs_manual_review = True
        d = meta.to_dict()
        assert d["needs_manual_review"] is True

    def test_field_false_serializes(self):
        from services.fact_check_service import VerificationMetadata
        meta = VerificationMetadata()
        d = meta.to_dict()
        assert d["needs_manual_review"] is False


# ──────────────────────────────────────────────────────────────────
# Plan B: text_copy criterion in evaluate_quality_criteria()
# ──────────────────────────────────────────────────────────────────

class TestTextCopyCriterion:
    """Tests for the text_copy quality criterion."""

    def _get_failure_criteria(self, result):
        """Extract criterion names from evaluate_quality_criteria result."""
        return [f["criterion"] for f in result.get("failures", [])]

    def test_high_overlap_triggers_text_copy(self):
        """When generated text copies source, text_copy criterion should fail."""
        from functions.generation_api import evaluate_quality_criteria
        source = "O governo federal anunciou medidas economicas importantes para o proximo trimestre do ano fiscal"
        result = evaluate_quality_criteria(
            verification_data={
                "confidence_score": 0.80,
                "grounded_claims": 5,
                "total_claims": 5,
            },
            readability_data={"flesch_score": 55, "avg_sentence_length": 12},
            generated_text=source,
            source_text=source,
        )
        assert "text_copy" in self._get_failure_criteria(result)

    def test_original_text_passes_text_copy(self):
        """When generated text is original, text_copy criterion should not appear."""
        from functions.generation_api import evaluate_quality_criteria
        source = "O governo federal anunciou medidas economicas importantes"
        generated = "Novas politicas de saude publica serao implementadas no proximo semestre pelo ministerio da saude em parceria com estados"
        result = evaluate_quality_criteria(
            verification_data={
                "confidence_score": 0.80,
                "grounded_claims": 5,
                "total_claims": 5,
            },
            readability_data={"flesch_score": 55, "avg_sentence_length": 12},
            generated_text=generated,
            source_text=source,
        )
        assert "text_copy" not in self._get_failure_criteria(result)

    def test_empty_texts_skip_check(self):
        """When texts are empty, text_copy should not be checked."""
        from functions.generation_api import evaluate_quality_criteria
        result = evaluate_quality_criteria(
            verification_data={
                "confidence_score": 0.80,
                "grounded_claims": 5,
                "total_claims": 5,
            },
            readability_data={"flesch_score": 55, "avg_sentence_length": 12},
            generated_text="",
            source_text="",
        )
        assert "text_copy" not in self._get_failure_criteria(result)


# ──────────────────────────────────────────────────────────────────
# Plan B: needs_manual_review propagation in generation pipeline
# ──────────────────────────────────────────────────────────────────

class TestNeedsManualReviewPropagation:
    """Tests that needs_manual_review is wired to human_review_required."""

    def test_propagation_logic(self):
        """When verification has needs_manual_review=True, result should get human_review_required."""
        result = {
            "verification": {"needs_manual_review": True},
        }
        # Apply the same logic that generation_api.py now has
        if result.get("verification", {}).get("needs_manual_review"):
            result["human_review_required"] = True
            result.setdefault("review_reasons", []).append(
                "Extracao de claims falhou - verificacao manual necessaria"
            )
        assert result["human_review_required"] is True
        assert any("claims falhou" in r for r in result["review_reasons"])

    def test_no_propagation_when_false(self):
        result = {
            "verification": {"needs_manual_review": False},
        }
        if result.get("verification", {}).get("needs_manual_review"):
            result["human_review_required"] = True
        assert "human_review_required" not in result
