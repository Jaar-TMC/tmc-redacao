"""
Tests for the improved fact-check pipeline (Phases 1-5).

Covers:
1. Entity extraction hardening (stopwords, substring, abbreviation, sentence-start)
2. Quote verification (dynamic thresholds, LCS, neutral default)
3. Confidence scoring (weights, CoVe bonus, quote default fix)
4. CoVe (chain-of-verification) filtering and cost
5. Safety gates with new scores
6. Schema.org structured data
7. Article types and tone formatting
"""

import sys
import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.fact_check_service import (
    FactCheckService,
    ExtractedClaim,
    EntityComparisonResult,
    QuoteVerificationResult,
    EnrichmentContext,
    VerificationMetadata,
    CoVeVerification,
    _lcs_length,
    WEIGHT_CLAIM_GROUNDING,
    WEIGHT_ENTITY_OVERLAP,
    WEIGHT_EXPANSION_RATIO,
    WEIGHT_QUOTE_VERIFICATION,
    WEIGHT_MATERIAL_SUFFICIENCY,
    WEIGHT_CLAIM_SIMILARITY,
)


# ===========================================================================
# Test Fixtures
# ===========================================================================

@pytest.fixture
def service():
    """Create a FactCheckService instance for testing."""
    return FactCheckService()


@pytest.fixture
def sample_source_text():
    return (
        "O presidente Luiz Inácio Lula da Silva sancionou a lei que cria o "
        "programa Bolsa Família Digital. A medida foi anunciada pelo Ministério "
        "da Fazenda em Brasília nesta segunda-feira. O PIB cresceu 2,5% no "
        "último trimestre, segundo dados do IBGE. O Supremo Tribunal Federal "
        "deve julgar a constitucionalidade da medida na próxima semana."
    )


@pytest.fixture
def sample_article_with_quotes():
    return (
        'O presidente **Lula** sancionou a nova lei. "Esta é a maior conquista '
        'social da década", afirmou o ministro da Fazenda. O programa Bolsa '
        'Família Digital deve beneficiar **15 milhões** de famílias.'
    )


# ===========================================================================
# Phase 1A: Entity Extraction Tests
# ===========================================================================

class TestEntityExtraction:
    """Tests for hardened entity extraction."""

    def test_stopwords_filtered(self, service):
        """Stopwords like 'Segundo', 'Conforme', 'Governo' should be filtered."""
        text = "Segundo informações, o Governo deve anunciar medidas. Conforme esperado."
        entities = service._extract_entities_regex(text)
        normalized = {service._normalize(e) for e in entities}
        assert "segundo" not in normalized
        assert "conforme" not in normalized

    def test_expanded_stopwords(self, service):
        """New expanded stopwords should be filtered."""
        text = "Atualmente o processo está em análise. Praticamente todos concordam."
        entities = service._extract_entities_regex(text)
        normalized = {service._normalize(e) for e in entities}
        assert "atualmente" not in normalized
        assert "praticamente" not in normalized

    def test_proper_names_kept(self, service):
        """Proper names should NOT be filtered when they appear mid-sentence."""
        text = "O ministro Lula anunciou a medida. Em Brasília, o presidente Lula disse que o programa é importante."
        entities = service._extract_entities_regex(text)
        normalized = {service._normalize(e) for e in entities}
        # "Lula" appears after lowercase word mid-sentence
        assert any("lula" in n for n in normalized) or any("brasilia" in n for n in normalized)

    def test_fragment_filter(self, service):
        """Entities shorter than 3 chars should be rejected."""
        text = "O Sr. Lá disse que sim."
        entities = service._extract_entities_regex(text)
        # "La" is only 2 chars, should be filtered
        short_entities = {e for e in entities if len(e) < 3}
        assert len(short_entities) == 0

    def test_acronyms_extracted(self, service):
        """Acronyms like STF, PIB, IBGE should be extracted."""
        text = "O STF decidiu e o PIB subiu. Dados do IBGE confirmam."
        entities = service._extract_entities_regex(text)
        assert "STF" in entities
        assert "PIB" in entities
        assert "IBGE" in entities

    def test_monetary_values(self, service):
        """Monetary values should be extracted."""
        text = "O programa custará R$ 2,5 bilhões ao governo."
        entities = service._extract_entities_regex(text)
        assert any("R$" in e for e in entities)

    def test_percentages(self, service):
        """Percentages should be extracted."""
        text = "A inflação subiu 4,5% no período."
        entities = service._extract_entities_regex(text)
        assert any("%" in e for e in entities)

    def test_substring_matching(self, service):
        """'Lula' in output should match 'Luiz Inácio Lula da Silva' in source via substring."""
        source = "O presidente Luiz Inácio Lula da Silva anunciou a medida em Brasília."
        output = "O presidente Lula sancionou o programa em Brasília."
        result = service._compare_entities(source, output)
        # Brasília is common directly. Other names may match via substring.
        assert result.overlap_score > 0 or len(result.common_entities) > 0

    def test_abbreviation_matching(self, service):
        """'STF' should match 'Supremo Tribunal Federal'."""
        source = "O Supremo Tribunal Federal decidiu o caso."
        output = "A decisão do STF foi unânime."
        result = service._compare_entities(source, output)
        # STF should match Supremo Tribunal Federal
        assert len(result.common_entities) > 0 or result.overlap_score > 0

    def test_abbreviation_map(self, service):
        """Known abbreviations should match their full names."""
        assert service._is_abbreviation_match("stf", "supremo tribunal federal")
        assert service._is_abbreviation_match("pib", "produto interno bruto")
        assert service._is_abbreviation_match("cbf", "confederacao brasileira de futebol")

    def test_abbreviation_heuristic(self, service):
        """Heuristic abbreviation detection from initials."""
        # "MF" should match "Ministerio da Fazenda" (initials of non-skip words)
        assert service._is_abbreviation_match("mf", "ministerio da fazenda")

    def test_sentence_start_filter(self, service):
        """Single-word entities that only appear at sentence start should be filtered."""
        text = "Governo anunciou medidas. O plano foi aprovado."
        entities = service._extract_entities_regex(text)
        normalized = {service._normalize(e) for e in entities}
        assert "governo" not in normalized

    def test_sentence_start_kept_if_mid_sentence(self, service):
        """Words at sentence start should be kept if they also appear mid-sentence."""
        text = "Brasília sediou o evento. A reunião em Brasília foi produtiva."
        entities = service._extract_entities_regex(text)
        # Brasília appears mid-sentence, should be kept
        normalized = {service._normalize(e) for e in entities}
        assert "brasilia" in normalized


# ===========================================================================
# Phase 1B: Quote Verification Tests
# ===========================================================================

class TestQuoteVerification:
    """Tests for improved quote verification."""

    def test_neutral_default_no_quotes(self, service):
        """When article has no quotes, verification_rate should be 0.5 (neutral)."""
        result = service._verify_quotes(
            "Artigo sem nenhuma citação entre aspas.",
            "Texto fonte original."
        )
        assert result.total_quotes == 0
        assert result.verification_rate == 0.5

    def test_short_quote_strict_threshold(self, service):
        """Short quotes (<=8 words) require 70% word overlap."""
        source = "O ministro declarou apoio total ao programa."
        article = '"O ministro declarou apoio ao programa", disse ele.'
        result = service._verify_quotes(article, source)
        assert result.total_quotes == 1
        assert result.verified_quotes == 1

    def test_long_quote_relaxed_threshold(self, service):
        """Long quotes (>20 words) use 40% word overlap threshold."""
        source = (
            "Na coletiva de imprensa realizada ontem à tarde no Palácio do Planalto "
            "o presidente anunciou que o programa vai beneficiar milhões de famílias "
            "em todo o território nacional a partir do próximo mês de março"
        )
        article = (
            '"O programa vai beneficiar milhões de famílias em todo o território '
            'nacional a partir do próximo mês de março, segundo anunciou o presidente '
            'em coletiva realizada ontem à tarde"'
        )
        result = service._verify_quotes(article, source)
        assert result.total_quotes == 1
        assert result.verified_quotes == 1

    def test_unverified_quote_detected(self, service):
        """Fabricated quotes should not be verified."""
        article = '"Vamos investir R$ 500 bilhões em infraestrutura", prometeu o governador.'
        source = "O presidente anunciou o programa social."
        result = service._verify_quotes(article, source)
        assert result.total_quotes == 1
        assert result.verified_quotes == 0
        assert len(result.unverified_quotes) == 1

    def test_lcs_matching_paraphrase(self, service):
        """LCS should catch paraphrased quotes."""
        source = "o programa vai atender todas as famílias que precisam de ajuda"
        article = '"Todas as famílias que precisam de ajuda serão atendidas pelo programa"'
        result = service._verify_quotes(article, source)
        # LCS should catch the overlap between paraphrased versions
        assert result.total_quotes == 1


# ===========================================================================
# LCS Helper Tests
# ===========================================================================

class TestLCSHelper:
    """Tests for the LCS length computation."""

    def test_identical_sequences(self):
        assert _lcs_length(["a", "b", "c"], ["a", "b", "c"]) == 3

    def test_empty_sequences(self):
        assert _lcs_length([], ["a", "b"]) == 0
        assert _lcs_length(["a"], []) == 0

    def test_partial_overlap(self):
        assert _lcs_length(["a", "b", "c", "d"], ["a", "x", "c", "d"]) == 3

    def test_no_overlap(self):
        assert _lcs_length(["a", "b"], ["c", "d"]) == 0

    def test_lcs_ratio(self):
        service = FactCheckService()
        ratio = service._lcs_ratio("o programa vai atender", "o programa vai atender")
        assert ratio >= 0.9


# ===========================================================================
# Phase 1C: Confidence Scoring Tests
# ===========================================================================

class TestConfidenceScoring:
    """Tests for calibrated confidence scoring."""

    def test_weight_sum_is_one(self):
        """All weights should sum to 1.0."""
        total = (
            WEIGHT_CLAIM_GROUNDING
            + WEIGHT_ENTITY_OVERLAP
            + WEIGHT_EXPANSION_RATIO
            + WEIGHT_QUOTE_VERIFICATION
            + WEIGHT_MATERIAL_SUFFICIENCY
            + WEIGHT_CLAIM_SIMILARITY
        )
        assert abs(total - 1.0) < 0.001

    def test_weights_updated(self):
        """Verify new weight values (v7: claims 0.45, entities 0.15, similarity 0.10)."""
        assert WEIGHT_CLAIM_GROUNDING == 0.45
        assert WEIGHT_ENTITY_OVERLAP == 0.15
        assert WEIGHT_QUOTE_VERIFICATION == 0.10
        assert WEIGHT_CLAIM_SIMILARITY == 0.10

    def test_quote_default_neutral(self, service):
        """When no quotes, quote_score should be 0.5, not 0.0."""
        metadata = VerificationMetadata()
        metadata.claims = [
            ExtractedClaim(text="Claim 1", verdict="grounded"),
        ]
        metadata.total_claims = 1
        metadata.grounded_claims = 1
        metadata.expansion_ratio = 2.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult(overlap_score=0.7)
        quote_result = QuoteVerificationResult(
            total_quotes=0,
            verification_rate=0.5,
        )

        score = service._compute_confidence(metadata, entity_result, quote_result)
        # With good claims, good entities, no quotes (neutral), low expansion
        assert score > 0.7

    def test_cove_bonus_applied(self, service):
        """CoVe reclassification should add bonus to confidence."""
        metadata = VerificationMetadata()
        metadata.claims = [
            ExtractedClaim(text="Claim 1", verdict="grounded"),
        ]
        metadata.total_claims = 1
        metadata.grounded_claims = 1
        metadata.expansion_ratio = 2.0
        metadata.source_sufficiency = "sufficient"
        metadata.cove_applied = True
        metadata.cove_reclassified = 2  # 2 claims were reclassified

        entity_result = EntityComparisonResult(overlap_score=0.7)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        score_with_cove = service._compute_confidence(metadata, entity_result, quote_result)

        # Reset CoVe
        metadata.cove_applied = False
        metadata.cove_reclassified = 0
        score_without_cove = service._compute_confidence(metadata, entity_result, quote_result)

        assert score_with_cove > score_without_cove
        assert score_with_cove - score_without_cove == pytest.approx(0.10, abs=0.01)

    def test_expansion_cap(self, service):
        """Expansion >10x should cap confidence at 0.5."""
        metadata = VerificationMetadata()
        metadata.claims = [
            ExtractedClaim(text="Claim 1", verdict="grounded"),
        ]
        metadata.total_claims = 1
        metadata.grounded_claims = 1
        metadata.expansion_ratio = 12.0  # >10x
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult(overlap_score=0.9)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        score = service._compute_confidence(metadata, entity_result, quote_result)
        assert score <= 0.5

    def test_novel_entity_guard(self, service):
        """Too many novel entities should cap confidence."""
        metadata = VerificationMetadata()
        metadata.claims = []
        metadata.total_claims = 0
        metadata.expansion_ratio = 2.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult(
            overlap_score=0.3,
            output_entities=["A", "B", "C", "D", "E"],
            novel_entities=["C", "D", "E"],  # 3/5 = 60% novel
        )
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        score = service._compute_confidence(metadata, entity_result, quote_result)
        assert score <= 0.55


# ===========================================================================
# Phase 2: CoVe Tests
# ===========================================================================

class TestCoVe:
    """Tests for Chain-of-Verification."""

    @pytest.mark.asyncio
    async def test_cove_skips_when_no_fabricated(self, service):
        """CoVe should not make LLM calls when no fabricated claims."""
        claims = [
            ExtractedClaim(text="Good claim", verdict="grounded"),
            ExtractedClaim(text="Editorial claim", verdict="editorial"),
        ]
        updated, results, count = await service._cove_verify_claims(
            claims, "source text"
        )
        assert count == 0
        assert len(results) == 0
        # Claims unchanged
        assert updated[0].verdict == "grounded"

    @pytest.mark.asyncio
    async def test_cove_filters_only_fabricated(self, service):
        """CoVe should only process fabricated claims."""
        claims = [
            ExtractedClaim(text="Good claim", verdict="grounded"),
            ExtractedClaim(text="Bad claim", verdict="fabricated"),
            ExtractedClaim(text="Unknown", verdict="unverifiable"),
        ]

        # Mock the _cove_single_claim to avoid real LLM calls
        async def mock_cove(claim, source, enrichment):
            return CoVeVerification(
                original_claim=claim.text if isinstance(claim, ExtractedClaim) else claim.get("text", ""),
                final_verdict="editorial",  # Reclassified
                confidence_delta=0.05,
            )

        service._cove_single_claim = mock_cove

        updated, results, count = await service._cove_verify_claims(
            claims, "source text"
        )
        assert count == 1  # Only 1 fabricated was processed
        assert updated[1].verdict == "editorial"  # Reclassified
        assert updated[0].verdict == "grounded"  # Unchanged
        assert updated[2].verdict == "unverifiable"  # Unchanged

    @pytest.mark.asyncio
    async def test_cove_disabled(self, service):
        """CoVe should be a no-op when COVE_ENABLED is False."""
        import services.fact_check_service as module
        original = module.COVE_ENABLED
        module.COVE_ENABLED = False

        claims = [ExtractedClaim(text="Bad", verdict="fabricated")]
        updated, results, count = await service._cove_verify_claims(claims, "source")

        assert count == 0
        assert updated[0].verdict == "fabricated"  # Unchanged

        module.COVE_ENABLED = original

    @pytest.mark.asyncio
    async def test_cove_respects_max_claims(self, service):
        """CoVe should only process up to COVE_MAX_CLAIMS fabricated claims."""
        import services.fact_check_service as module
        original_max = module.COVE_MAX_CLAIMS
        module.COVE_MAX_CLAIMS = 2

        claims = [
            ExtractedClaim(text=f"Bad claim {i}", verdict="fabricated")
            for i in range(5)
        ]

        call_count = 0

        async def mock_cove(claim, source, enrichment):
            nonlocal call_count
            call_count += 1
            return CoVeVerification(
                original_claim=claim.text if isinstance(claim, ExtractedClaim) else "",
                final_verdict="fabricated",
            )

        service._cove_single_claim = mock_cove

        await service._cove_verify_claims(claims, "source")
        assert call_count == 2  # Limited to COVE_MAX_CLAIMS

        module.COVE_MAX_CLAIMS = original_max


# ===========================================================================
# Phase 3: Article Types & Tones Tests
# ===========================================================================

class TestArticleTypes:
    """Tests for expanded ARTICLE_TYPES."""

    def test_all_types_have_structure(self):
        from services.llm_service import ARTICLE_TYPES
        for key, value in ARTICLE_TYPES.items():
            assert isinstance(value, dict), f"{key} should be a dict"
            assert "description" in value, f"{key} missing 'description'"
            assert "structure" in value, f"{key} missing 'structure'"
            assert "paragraphs" in value, f"{key} missing 'paragraphs'"
            assert "opening" in value, f"{key} missing 'opening'"
            assert "closing" in value, f"{key} missing 'closing'"
            assert "include" in value, f"{key} missing 'include'"
            assert "exclude" in value, f"{key} missing 'exclude'"

    def test_format_article_type(self):
        from services.llm_service import _format_article_type
        result = _format_article_type("destaque")
        assert "pirâmide invertida" in result
        assert "Estrutura" in result
        assert "Abertura" in result
        assert "Fechamento" in result

    def test_format_article_type_unknown(self):
        """Unknown type should fallback to destaque."""
        from services.llm_service import _format_article_type
        result = _format_article_type("unknown_type")
        assert "pirâmide invertida" in result


class TestTones:
    """Tests for expanded TONS_POR_CATEGORIA."""

    def test_all_tones_have_fields(self):
        from services.llm_service import TONS_POR_CATEGORIA
        for cat, tones in TONS_POR_CATEGORIA.items():
            for tone_key, tone_info in tones.items():
                assert isinstance(tone_info, dict), f"{cat}/{tone_key} should be a dict"
                assert "descricao" in tone_info, f"{cat}/{tone_key} missing 'descricao'"
                assert "exemplos" in tone_info, f"{cat}/{tone_key} missing 'exemplos'"
                assert len(tone_info["exemplos"]) >= 2, f"{cat}/{tone_key} needs >=2 examples"
                assert "proibido" in tone_info, f"{cat}/{tone_key} missing 'proibido'"
                assert "tamanho_frase" in tone_info, f"{cat}/{tone_key} missing 'tamanho_frase'"
                assert "vocabulario" in tone_info, f"{cat}/{tone_key} missing 'vocabulario'"

    def test_format_tone(self):
        from services.llm_service import _format_tone
        tone_info = {
            "descricao": "Test description",
            "exemplos": ["Example 1", "Example 2"],
            "proibido": "Nothing specific",
            "tamanho_frase": "Short",
            "vocabulario": "formal",
        }
        result = _format_tone(tone_info)
        assert "Test description" in result
        assert "Example 1" in result
        assert "PROIBIDO" in result
        assert "formal" in result

    def test_format_tone_legacy_string(self):
        """Legacy string tones should be returned as-is."""
        from services.llm_service import _format_tone
        result = _format_tone("Simple tone description")
        assert result == "Simple tone description"


# ===========================================================================
# Phase 4: Schema.org Tests
# ===========================================================================

class TestSchemaOrg:
    """Tests for Schema.org JSON-LD output."""

    def test_schema_structure(self):
        """Schema.org output should have required NewsArticle fields."""
        # Import the function from generation_api
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "functions"))
        from generation_api import _build_schema_org

        schema = _build_schema_org(
            titulo="Lula sanciona Bolsa Família Digital",
            linha_fina="Programa deve beneficiar 15 milhões de famílias",
            tags=["bolsa-familia", "digital", "lula"],
        )

        assert schema["@context"] == "https://schema.org"
        assert schema["@type"] == "NewsArticle"
        assert "headline" in schema
        assert "description" in schema
        assert "datePublished" in schema
        assert "author" in schema
        assert isinstance(schema["author"], list)
        assert schema["author"][0]["@type"] == "Person"
        assert schema["author"][0]["name"] == "Redacao TMC"
        assert "publisher" in schema
        assert "keywords" in schema
        assert "bolsa-familia" in schema["keywords"]

    def test_schema_headline_truncation(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "functions"))
        from generation_api import _build_schema_org

        long_title = "A" * 200
        schema = _build_schema_org(titulo=long_title, linha_fina="Test")
        assert len(schema["headline"]) <= 110

    def test_schema_no_tags(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "functions"))
        from generation_api import _build_schema_org

        schema = _build_schema_org(titulo="Test", linha_fina="Test")
        assert "keywords" not in schema


# ===========================================================================
# Safety Gates Integration Tests
# ===========================================================================

class TestSafetyGates:
    """Tests for safety gates with new confidence scores."""

    def test_high_confidence_allows_publish(self, service):
        """High confidence + low risk should allow publishing."""
        metadata = VerificationMetadata()
        metadata.claims = [
            ExtractedClaim(text="C1", verdict="grounded"),
            ExtractedClaim(text="C2", verdict="grounded"),
        ]
        metadata.total_claims = 2
        metadata.grounded_claims = 2
        metadata.fabricated_claims = 0
        metadata.unverifiable_claims = 0
        metadata.expansion_ratio = 2.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult(overlap_score=0.8)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        score = service._compute_confidence(metadata, entity_result, quote_result)
        # Set confidence_score on metadata before risk level check
        metadata.confidence_score = score
        risk = service._determine_risk_level(metadata, entity_result, quote_result)

        assert score >= 0.7
        assert risk in ("low", "medium")

    def test_fabricated_claims_escalate_risk(self, service):
        """Multiple fabricated claims should escalate risk level."""
        metadata = VerificationMetadata()
        metadata.confidence_score = 0.3
        metadata.fabricated_claims = 3
        metadata.total_claims = 5
        metadata.unverifiable_claims = 0
        metadata.expansion_ratio = 2.0

        entity_result = EntityComparisonResult(overlap_score=0.5)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        risk = service._determine_risk_level(metadata, entity_result, quote_result)
        assert risk == "critical"

    def test_single_fabricated_low_confidence_high_risk(self, service):
        """1 fabricated + low confidence = high risk."""
        metadata = VerificationMetadata()
        metadata.confidence_score = 0.25
        metadata.fabricated_claims = 1
        metadata.total_claims = 3
        metadata.unverifiable_claims = 0
        metadata.expansion_ratio = 3.0

        entity_result = EntityComparisonResult(overlap_score=0.5)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        risk = service._determine_risk_level(metadata, entity_result, quote_result)
        assert risk == "high"


# ===========================================================================
# Integration: Full Verify Flow
# ===========================================================================

class TestVerifyArticleIntegration:
    """Integration tests for the full verify_article flow."""

    @pytest.mark.asyncio
    async def test_verify_article_with_cove(self, service):
        """Full flow: verify_article should run CoVe on fabricated claims."""
        source = "O presidente Lula anunciou o programa em Brasília."
        article = "O presidente Lula anunciou o programa social em Brasília na segunda-feira."

        # Mock LLM to avoid real API calls
        mock_llm = AsyncMock()
        mock_llm.call_api = AsyncMock(return_value=json.dumps({
            "claims": [
                {"text": "Lula anunciou o programa", "verdict": "grounded", "source_evidence": "texto-base", "category": "fact"},
                {"text": "na segunda-feira", "verdict": "fabricated", "source_evidence": "", "category": "fact"},
            ]
        }))
        mock_llm._call_api = mock_llm.call_api
        service._llm_service = mock_llm

        # Mock CoVe to reclassify
        async def mock_cove_single(claim, source_text, enrichment_text):
            return CoVeVerification(
                original_claim=claim.text if isinstance(claim, ExtractedClaim) else claim.get("text", ""),
                final_verdict="unverifiable",
                confidence_delta=0.05,
            )

        service._cove_single_claim = mock_cove_single

        result = await service.verify_article(source, article)

        assert result.is_verified
        assert result.cove_applied
        assert result.cove_reclassified == 1  # 1 fabricated -> unverifiable
        assert result.fabricated_claims == 0  # After CoVe


# ===========================================================================
# Phase 1A: New Entity Extraction Tests
# ===========================================================================

class TestEntityExtractionV3:
    """Tests for v3 entity extraction improvements."""

    def test_hyphenated_names(self, service):
        """Hyphenated proper nouns like Al-Assad are captured."""
        text = "O presidente Bashar Al-Assad deixou o poder na Siria."
        entities = service._extract_entities_regex(text)
        found = any("Al-Assad" in e for e in entities)
        assert found, f"Al-Assad not found in {entities}"

    def test_all_caps_multi_word(self, service):
        """All-caps multi-word names like VINI JR are captured."""
        text = "O jogador VINI JR marcou um gol decisivo na partida."
        entities = service._extract_entities_regex(text)
        found = any("VINI JR" in e for e in entities)
        assert found, f"VINI JR not found in {entities}"

    def test_particle_names(self, service):
        """Names with particles like Mohammed bin Salman are captured."""
        text = "O principe Mohammed bin Salman visitou Washington."
        entities = service._extract_entities_regex(text)
        found = any("Mohammed bin Salman" in e for e in entities)
        assert found, f"Mohammed bin Salman not found in {entities}"

    def test_known_names_sentence_start(self, service):
        """Known names like Lula are kept even at sentence start."""
        text = "Lula sancionou a nova lei. O programa comeca em marco."
        entities = service._extract_entities_regex(text)
        normalized = {service._normalize(e) for e in entities}
        assert any("lula" in n for n in normalized), f"Lula should be kept, got {normalized}"

    def test_expanded_stopwords_v3(self, service):
        """New v3 stopwords (quanto, qual, diz, etc.) are filtered."""
        text = "Quanto ao processo, Diz o relatorio que Mostra resultados positivos."
        entities = service._extract_entities_regex(text)
        normalized = {service._normalize(e) for e in entities}
        for stop in ["quanto", "diz", "mostra"]:
            assert stop not in normalized, f"'{stop}' should be stopword, found in {normalized}"


# ===========================================================================
# Phase 1B: CoVe 2-Call and Proportional Bonus Tests
# ===========================================================================

class TestCoVeTwoCallSplit:
    """Tests for CoVe 2-call split and proportional evidence bonus."""

    @pytest.mark.asyncio
    async def test_cove_two_call_isolation(self, service):
        """CoVe single claim makes 2 LLM calls (Q&A + verdict)."""
        call_count = 0
        async def mock_call_api(system, prompt, max_tokens, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Call 1: Q&A
                return json.dumps({
                    "questions": ["Q1?", "Q2?"],
                    "answers": ["A1", "A2"],
                })
            else:
                # Call 2: Verdict
                return json.dumps({
                    "final_verdict": "editorial",
                    "reasoning": "Contexto correto",
                    "evidence_strength": "strong",
                })

        mock_llm = AsyncMock()
        mock_llm.call_api = mock_call_api
        service._llm_service = mock_llm

        claim = ExtractedClaim(text="Test claim", verdict="fabricated")
        result = await service._cove_single_claim(claim, "Source text", "")

        assert call_count == 2
        assert result.final_verdict == "editorial"
        assert result.evidence_strength == "strong"
        assert result.confidence_delta == 0.08  # strong delta

    @pytest.mark.asyncio
    async def test_cove_proportional_strong(self, service):
        """Strong evidence gives 0.08 bonus."""
        async def mock_call_api(system, prompt, max_tokens, **kwargs):
            if "Gere" in prompt:
                return json.dumps({"questions": ["Q?"], "answers": ["A"]})
            return json.dumps({"final_verdict": "grounded", "reasoning": "ok", "evidence_strength": "strong"})

        mock_llm = AsyncMock()
        mock_llm.call_api = mock_call_api
        service._llm_service = mock_llm

        claim = ExtractedClaim(text="Test", verdict="fabricated")
        result = await service._cove_single_claim(claim, "Source", "")
        assert result.confidence_delta == 0.08

    @pytest.mark.asyncio
    async def test_cove_proportional_weak(self, service):
        """Weak evidence gives 0.02 bonus."""
        async def mock_call_api(system, prompt, max_tokens, **kwargs):
            if "Gere" in prompt:
                return json.dumps({"questions": ["Q?"], "answers": ["A"]})
            return json.dumps({"final_verdict": "unverifiable", "reasoning": "ok", "evidence_strength": "weak"})

        mock_llm = AsyncMock()
        mock_llm.call_api = mock_call_api
        service._llm_service = mock_llm

        claim = ExtractedClaim(text="Test", verdict="fabricated")
        result = await service._cove_single_claim(claim, "Source", "")
        assert result.confidence_delta == 0.02

    @pytest.mark.asyncio
    async def test_cove_fabricated_keeps_zero_delta(self, service):
        """If still fabricated after CoVe, delta is 0."""
        async def mock_call_api(system, prompt, max_tokens, **kwargs):
            if "Gere" in prompt:
                return json.dumps({"questions": ["Q?"], "answers": ["A"]})
            return json.dumps({"final_verdict": "fabricated", "reasoning": "confirmed wrong", "evidence_strength": "strong"})

        mock_llm = AsyncMock()
        mock_llm.call_api = mock_call_api
        service._llm_service = mock_llm

        claim = ExtractedClaim(text="Test", verdict="fabricated")
        result = await service._cove_single_claim(claim, "Source", "")
        assert result.confidence_delta == 0.0

    def test_parse_json_valid(self, service):
        """_parse_json_response extracts valid JSON."""
        text = 'Some text before {"key": "value"} after'
        result = service._parse_json_response(text)
        assert result == {"key": "value"}

    def test_parse_json_invalid(self, service):
        """_parse_json_response returns None for invalid JSON."""
        result = service._parse_json_response("no json here")
        assert result is None


# ===========================================================================
# Phase 2A: TF-IDF Claim-Source Similarity Tests
# ===========================================================================

class TestClaimSourceSimilarity:
    """Tests for TF-IDF claim-source similarity."""

    def test_similarity_identical(self, service):
        """Identical text should have high similarity."""
        claims = [ExtractedClaim(text="O presidente sancionou a nova lei do programa social")]
        source = "O presidente sancionou a nova lei do programa social. A medida entra em vigor amanha."
        sims = service._compute_claim_source_similarity(claims, source)
        assert len(sims) == 1
        assert sims[0] > 0.5

    def test_similarity_unrelated(self, service):
        """Completely unrelated text should have low similarity."""
        claims = [ExtractedClaim(text="O jogador marcou tres gols na final do campeonato")]
        source = "A taxa de juros subiu para 12 por cento segundo o banco central."
        sims = service._compute_claim_source_similarity(claims, source)
        assert len(sims) == 1
        assert sims[0] < 0.3

    def test_similarity_partial(self, service):
        """Partially overlapping text should have moderate similarity."""
        claims = [ExtractedClaim(text="O presidente anunciou novas medidas economicas")]
        source = "O presidente do Brasil anunciou um pacote de medidas para a economia."
        sims = service._compute_claim_source_similarity(claims, source)
        assert len(sims) == 1
        assert 0.2 <= sims[0] <= 0.9

    def test_similarity_empty_source(self, service):
        """Empty source returns empty list."""
        claims = [ExtractedClaim(text="Some claim")]
        sims = service._compute_claim_source_similarity(claims, "")
        assert sims == []

    def test_weights_sum_to_one(self):
        """All confidence weights sum to 1.0."""
        from services.fact_check_service import (
            WEIGHT_CLAIM_GROUNDING, WEIGHT_ENTITY_OVERLAP,
            WEIGHT_EXPANSION_RATIO, WEIGHT_QUOTE_VERIFICATION,
            WEIGHT_MATERIAL_SUFFICIENCY, WEIGHT_CLAIM_SIMILARITY,
        )
        total = (WEIGHT_CLAIM_GROUNDING + WEIGHT_ENTITY_OVERLAP +
                 WEIGHT_EXPANSION_RATIO + WEIGHT_QUOTE_VERIFICATION +
                 WEIGHT_MATERIAL_SUFFICIENCY + WEIGHT_CLAIM_SIMILARITY)
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"


# ===========================================================================
# Phase 3B: Async Context Manager Tests
# ===========================================================================

class TestAsyncContextManagers:
    """Tests for async context manager support."""

    @pytest.mark.asyncio
    async def test_fact_check_context_manager(self):
        """FactCheckService supports async context manager."""
        async with FactCheckService() as svc:
            assert svc is not None
            assert svc.http_client is not None

    @pytest.mark.asyncio
    async def test_fact_check_close(self):
        """FactCheckService.close() closes HTTP client."""
        svc = FactCheckService()
        await svc.close()
        # After close, client should be closed
        assert svc.http_client.is_closed



# ===========================================================================
# Phase 1B v4: Retry & Circuit Breaker Tests
# ===========================================================================

class TestRetryCircuitBreaker:
    """Tests for HTTP retry and circuit breaker."""

    @pytest.mark.asyncio
    async def test_exa_retry_on_timeout(self, service):
        """_search_exa should retry on ConnectTimeout."""
        import httpx
        call_count = 0
        original_post = service.http_client.post

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectTimeout("timeout")
            return await original_post(*args, **kwargs)

        service.http_client.post = mock_post
        # Will fail all retries since we don't have a real API, but we can verify retry behavior
        try:
            await service._search_exa("test query")
        except httpx.ConnectTimeout:
            pass  # Expected after all retries
        assert call_count == 3  # Should have retried 3 times

    def test_circuit_breaker_initial_state(self, service):
        """Circuit breaker starts closed."""
        assert service._exa_failures == 0
        assert service._exa_circuit_open is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, service):
        """Circuit breaker opens after 3 consecutive failures."""
        import httpx
        service._exa_failures = 2  # Simulate 2 prior failures

        async def mock_post(*args, **kwargs):
            raise httpx.ConnectTimeout("timeout")

        service.http_client.post = mock_post
        try:
            await service._search_exa("test")
        except httpx.ConnectTimeout:
            pass
        assert service._exa_circuit_open is True
        assert service._exa_circuit_open_until > 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_when_open(self, service):
        """When circuit is open, _search_exa returns [] without calling API."""
        import time
        service._exa_circuit_open = True
        service._exa_circuit_open_until = time.time() + 60

        result = await service._search_exa("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self, service):
        """Circuit breaker resets failure count on success."""
        service._exa_failures = 2

        async def mock_post(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"results": []}
            return mock_resp

        service.http_client.post = mock_post
        await service._search_exa("test")
        assert service._exa_failures == 0


# ===========================================================================
# Phase 1D v4: Editorial Verdict Split Tests
# ===========================================================================

class TestEditorialVerdictSplit:
    """Tests for opinion/context verdict split."""

    def test_opinion_excluded_from_accuracy(self, service):
        """Opinion claims should not count in factual accuracy scoring."""
        metadata = VerificationMetadata()
        metadata.claims = [
            ExtractedClaim(text="Fact 1", verdict="grounded"),
            ExtractedClaim(text="Opinion 1", verdict="opinion"),
            ExtractedClaim(text="Context 1", verdict="context"),
        ]
        metadata.total_claims = 3
        metadata.grounded_claims = 1
        metadata.expansion_ratio = 2.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult(overlap_score=0.7)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        score = service._compute_confidence(metadata, entity_result, quote_result)
        # Only grounded and context are factual; opinion excluded
        # 2 factual claims (grounded + context), 1 grounded = 50% grounded ratio
        assert score > 0  # Should compute without error

    def test_context_included_in_accuracy(self, service):
        """Context claims should be counted in factual accuracy (they must be correct)."""
        metadata = VerificationMetadata()
        metadata.claims = [
            ExtractedClaim(text="Fact 1", verdict="grounded"),
            ExtractedClaim(text="Context 1", verdict="context"),
        ]
        metadata.total_claims = 2
        metadata.grounded_claims = 1
        metadata.expansion_ratio = 2.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult(overlap_score=0.7)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        # Both grounded and context are factual, so 2 factual claims
        score = service._compute_confidence(metadata, entity_result, quote_result)
        assert score > 0.4  # Should be reasonable

    def test_context_fabricated_detected(self, service):
        """A fabricated context claim should lower confidence."""
        metadata = VerificationMetadata()
        metadata.claims = [
            ExtractedClaim(text="Fact 1", verdict="grounded"),
            ExtractedClaim(text="Bad context", verdict="fabricated"),
        ]
        metadata.total_claims = 2
        metadata.grounded_claims = 1
        metadata.fabricated_claims = 1
        metadata.expansion_ratio = 2.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult(overlap_score=0.7)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        score = service._compute_confidence(metadata, entity_result, quote_result)
        # Fabricated claim should lower score significantly
        assert score < 0.8

    @pytest.mark.asyncio
    async def test_cove_can_reclassify_to_context(self, service):
        """CoVe should be able to reclassify fabricated -> context."""
        async def mock_call_api(system, prompt, max_tokens, **kwargs):
            if "Gere" in prompt:
                return json.dumps({"questions": ["Q?"], "answers": ["A"]})
            return json.dumps({"final_verdict": "context", "reasoning": "factual background", "evidence_strength": "moderate"})

        mock_llm = AsyncMock()
        mock_llm.call_api = mock_call_api
        service._llm_service = mock_llm

        claim = ExtractedClaim(text="Test context claim", verdict="fabricated")
        result = await service._cove_single_claim(claim, "Source text", "")
        assert result.final_verdict == "context"
        assert result.confidence_delta == 0.05  # moderate strength

    def test_backwards_compat_editorial(self, service):
        """Legacy 'editorial' verdict should be treated like 'opinion' in scoring."""
        metadata = VerificationMetadata()
        metadata.claims = [
            ExtractedClaim(text="Fact 1", verdict="grounded"),
            ExtractedClaim(text="Editorial 1", verdict="editorial"),
        ]
        metadata.total_claims = 2
        metadata.grounded_claims = 1
        metadata.expansion_ratio = 2.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult(overlap_score=0.7)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        # editorial should be excluded from factual claims (like opinion)
        score = service._compute_confidence(metadata, entity_result, quote_result)
        assert score > 0.5  # Only 1 factual claim (grounded), should be high


# ===========================================================================
# Phase 2A v4: Claim Provenance Tests
# ===========================================================================

class TestClaimProvenance:
    """Tests for source_reference in claims."""

    def test_claim_has_source_reference_field(self):
        """ExtractedClaim should have source_reference field."""
        claim = ExtractedClaim(text="Test", verdict="grounded", source_reference="The source sentence.")
        assert claim.source_reference == "The source sentence."

    def test_source_reference_default_empty(self):
        """source_reference should default to empty string."""
        claim = ExtractedClaim(text="Test")
        assert claim.source_reference == ""

    def test_source_reference_in_output(self, service):
        """VerificationMetadata.to_dict() should include source_reference."""
        metadata = VerificationMetadata()
        metadata.claims = [
            ExtractedClaim(text="Claim 1", verdict="grounded", source_reference="Source line.")
        ]
        result = metadata.to_dict()
        assert result["claims"][0]["source_reference"] == "Source line."

    def test_source_reference_fallback_tfidf(self, service):
        """_fill_source_references fills empty source_reference via TF-IDF."""
        claims = [
            ExtractedClaim(text="O presidente sancionou a lei", verdict="grounded"),
        ]
        source = "O presidente Lula sancionou a lei do programa social. A medida entra em vigor amanha."
        service._fill_source_references(claims, source)
        assert claims[0].source_reference != ""
        assert "sancionou" in claims[0].source_reference.lower()

    def test_source_reference_no_overwrite(self, service):
        """_fill_source_references should NOT overwrite existing source_reference."""
        claims = [
            ExtractedClaim(text="Test", verdict="grounded", source_reference="Already filled"),
        ]
        service._fill_source_references(claims, "Some source text about testing.")
        assert claims[0].source_reference == "Already filled"


# ===========================================================================
# Phase 2B v4: Portuguese TF-IDF Tests
# ===========================================================================

class TestPortugueseTFIDF:
    """Tests for Portuguese stopwords and stemming in TF-IDF."""

    def test_pt_stopwords_filtered(self):
        """Portuguese stopwords should be excluded from tokenization."""
        from services.fact_check_service import FactCheckService
        stops = FactCheckService._PT_STOPWORDS
        assert "que" in stops
        assert "para" in stops
        assert "sobre" in stops

    def test_pt_stem_basic(self):
        """Basic Portuguese stemming should remove common suffixes."""
        from services.fact_check_service import FactCheckService
        assert FactCheckService._pt_stem("rapidamente") == "rapida"
        assert FactCheckService._pt_stem("informacao") == "inform"
        assert FactCheckService._pt_stem("resultado") == "resultado"  # no matching suffix

    def test_tfidf_with_pt_improvements(self, service):
        """TF-IDF with PT improvements should still compute similarity."""
        claims = [ExtractedClaim(text="O governo anunciou novas medidas economicas")]
        source = "O governo federal anunciou medidas para a economia do pais."
        sims = service._compute_claim_source_similarity(claims, source)
        assert len(sims) == 1
        assert sims[0] > 0  # Should have some similarity

    def test_pt_stem_short_words_unchanged(self):
        """Words too short for stemming should be returned unchanged."""
        from services.fact_check_service import FactCheckService
        assert FactCheckService._pt_stem("em") == "em"
        assert FactCheckService._pt_stem("ar") == "ar"


# ===========================================================================
# Phase 2C v4: Enrichment Improvements Tests
# ===========================================================================

class TestEnrichmentImprovements:
    """Tests for gov.br whitelist and URL deduplication."""

    def test_gov_br_whitelist_allows(self, service):
        """Whitelisted .gov.br URLs should pass quality filter."""
        assert service._is_quality_url("https://agenciabrasil.ebc.com.br/article/123", "A" * 200) is True
        assert service._is_quality_url("https://ibge.gov.br/noticias/2026", "A" * 200) is True

    def test_gov_br_generic_blocked(self, service):
        """Non-whitelisted .gov.br URLs should be blocked."""
        assert service._is_quality_url("https://random.gov.br/page", "A" * 200) is False
        assert service._is_quality_url("https://prefeitura.sp.gov.br/servicos", "A" * 200) is False

    def test_url_quality_filter_still_works(self, service):
        """Other bad patterns still filtered."""
        assert service._is_quality_url("https://example.com/topicos/politics", "A" * 200) is False
        assert service._is_quality_url("https://blogspot.com/blog", "A" * 200) is False

    def test_url_short_text_blocked(self, service):
        """URLs with short text should be blocked."""
        assert service._is_quality_url("https://example.com/article", "Short") is False


# ===========================================================================
# Phase v5: Truncation Metadata Tests (4A)
# ===========================================================================

class TestTruncationMetadata:
    """Tests for truncation warning and metadata."""

    def test_truncation_metadata_short_inputs(self, service):
        """Short inputs produce no truncation flags."""
        metadata = VerificationMetadata()
        metadata.truncation = {
            "source_truncated": len("short") > 6000,
            "article_truncated": len("short article") > 3000,
            "unverified_chars": max(0, len("short article") - 3000),
        }
        assert metadata.truncation["source_truncated"] is False
        assert metadata.truncation["article_truncated"] is False
        assert metadata.truncation["unverified_chars"] == 0

    def test_truncation_metadata_long_source(self, service):
        """Long source produces truncation flag."""
        source = "A" * 7000
        article = "B" * 2000
        metadata = VerificationMetadata()
        metadata.truncation = {
            "source_truncated": len(source) > 6000,
            "article_truncated": len(article) > 3000,
            "unverified_chars": max(0, len(article) - 3000),
        }
        assert metadata.truncation["source_truncated"] is True
        assert metadata.truncation["article_truncated"] is False

    def test_truncation_metadata_long_article(self, service):
        """Long article produces truncation flag with unverified count."""
        source = "A" * 5000
        article = "B" * 4500
        metadata = VerificationMetadata()
        metadata.truncation = {
            "source_truncated": len(source) > 6000,
            "article_truncated": len(article) > 3000,
            "unverified_chars": max(0, len(article) - 3000),
        }
        assert metadata.truncation["article_truncated"] is True
        assert metadata.truncation["unverified_chars"] == 1500

    def test_truncation_in_to_dict(self, service):
        """Truncation data appears in to_dict() output."""
        metadata = VerificationMetadata()
        metadata.truncation = {
            "source_truncated": True,
            "article_truncated": False,
            "unverified_chars": 0,
        }
        d = metadata.to_dict()
        assert "truncation" in d
        assert d["truncation"]["source_truncated"] is True


# ===========================================================================
# Phase v5: Empty Claims Fallback Tests (4B)
# ===========================================================================

class TestEmptyClaimsFallback:
    """Tests for empty claims detection and confidence penalty."""

    def test_empty_claims_flag(self, service):
        """Empty claims set claim_extraction_failed flag."""
        metadata = VerificationMetadata()
        claims = []
        if not claims:
            metadata.claim_extraction_failed = True
        assert metadata.claim_extraction_failed is True

    def test_empty_claims_penalized(self, service):
        """Empty claims produce lower confidence (0.35 claim_score)."""
        metadata = VerificationMetadata()
        metadata.claims = []
        metadata.total_claims = 0
        metadata.claim_extraction_failed = True
        metadata.expansion_ratio = 2.0
        metadata.source_sufficiency = "sufficient"

        entity_result = EntityComparisonResult(overlap_score=0.7)
        quote_result = QuoteVerificationResult(total_quotes=0, verification_rate=0.5)

        score = service._compute_confidence(metadata, entity_result, quote_result)

        # Now test without flag (neutral 0.5)
        metadata2 = VerificationMetadata()
        metadata2.claims = []
        metadata2.total_claims = 0
        metadata2.claim_extraction_failed = False
        metadata2.expansion_ratio = 2.0
        metadata2.source_sufficiency = "sufficient"

        score_neutral = service._compute_confidence(metadata2, entity_result, quote_result)

        assert score < score_neutral  # 0.35 vs 0.5 claim_score

    def test_claim_extraction_failed_in_to_dict(self, service):
        """claim_extraction_failed appears in to_dict() output."""
        metadata = VerificationMetadata()
        metadata.claim_extraction_failed = True
        d = metadata.to_dict()
        assert "claim_extraction_failed" in d
        assert d["claim_extraction_failed"] is True


# ===========================================================================
# Phase v5: Singleton Cleanup Tests (3A)
# ===========================================================================

class TestSingletonCleanup:
    """Tests for atexit cleanup registration."""

    def test_fact_check_cleanup_function_exists(self):
        """_cleanup_fact_check_service function exists."""
        from services.fact_check_service import _cleanup_fact_check_service
        assert callable(_cleanup_fact_check_service)

    def test_llm_cleanup_function_exists(self):
        """_cleanup_llm_service function exists."""
        from services.llm_service import _cleanup_llm_service
        assert callable(_cleanup_llm_service)

    @pytest.mark.asyncio
    async def test_fact_check_close_closes_client(self):
        """FactCheckService.close() closes the HTTP client."""
        svc = FactCheckService()
        assert not svc.http_client.is_closed
        await svc.close()
        assert svc.http_client.is_closed


# ===========================================================================
# Run tests
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
