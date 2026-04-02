"""
Integration tests for the generate_article_handler.

Tests the full handler with mocked LLM, Exa, and Database services.
Covers: happy path, phase failures, input validation, safety integration.
"""

import sys
import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_http_request(body: dict) -> MagicMock:
    """Create a mock Azure Functions HttpRequest."""
    req = MagicMock()
    req.get_json.return_value = body
    return req


def _make_llm_result():
    """Create a standard LLM generation result."""
    return {
        "titulo": "Titulo de Teste",
        "linha_fina": "Linha fina de teste para a materia",
        "conteudo": "Conteudo de teste. " * 100,  # ~1900 chars
        "tags_sugeridas": ["teste", "integracao"],
        "_user_prompt": "prompt text",
        "_raw_response": "raw response text",
    }


def _make_verification_metadata():
    """Create a mock VerificationMetadata."""
    from services.fact_check_service import VerificationMetadata
    meta = VerificationMetadata()
    meta.confidence_score = 0.75
    meta.risk_level = "medium"
    meta.is_verified = True
    meta.total_claims = 5
    meta.grounded_claims = 4
    meta.fabricated_claims = 0
    meta.unverifiable_claims = 1
    meta.expansion_ratio = 2.0
    meta.source_sufficiency = "sufficient"
    meta.entity_comparison = {
        "source_entities": ["Lula", "Brasilia"],
        "output_entities": ["Lula", "Brasilia", "STF"],
        "common_entities": ["Lula", "Brasilia"],
        "novel_entities": ["STF"],
        "overlap_score": 0.66,
    }
    meta.quote_verification = {
        "total_quotes": 0,
        "verified_quotes": 0,
        "unverified_quotes": [],
        "verification_rate": 0.5,
    }
    return meta


VALID_BODY = {
    "texto_base": (
        "O presidente Lula sancionou a nova lei que cria o programa social. "
        "A medida foi anunciada pelo Ministerio da Fazenda em Brasilia. "
        "O programa deve beneficiar milhoes de familias brasileiras em todo o pais. "
        "O Ministerio estima que cerca de 20 milhoes de pessoas serao atendidas pelo programa. "
        "A iniciativa faz parte do pacote de medidas sociais do governo federal para 2026."
    ),
    "categoria": "politica",
    "tom": "sobrio",
    "tipo_materia": "destaque",
}


# ===========================================================================
# Test: Happy Path
# ===========================================================================

class TestHandlerHappyPath:
    """Tests for the happy path of the full pipeline."""

    @pytest.mark.asyncio
    @patch("functions.generation_api._persist_audit", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.verify_article", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.enrich_context", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.generate_article", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.__init__", return_value=None)
    @patch("services.fact_check_service.is_fact_check_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_enrichment_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_verification_enabled", new=lambda: True)
    async def test_full_pipeline_returns_200(
        self, mock_llm_init, mock_generate, mock_enrich, mock_verify, mock_audit
    ):
        """Full pipeline returns 200 with all fields."""
        from functions.generation_api import generate_article_handler
        from services.fact_check_service import EnrichmentContext

        mock_generate.return_value = _make_llm_result()
        mock_enrich.return_value = EnrichmentContext(success=False)
        mock_verify.return_value = _make_verification_metadata()

        req = _make_http_request(VALID_BODY)
        response = await generate_article_handler(req)

        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert "titulo" in data
        assert "conteudo" in data
        assert "verification" in data

    @pytest.mark.asyncio
    @patch("functions.generation_api._persist_audit", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.verify_article", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.enrich_context", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.generate_article", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.__init__", return_value=None)
    @patch("services.fact_check_service.is_fact_check_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_enrichment_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_verification_enabled", new=lambda: True)
    async def test_response_contains_all_fields(
        self, mock_llm_init, mock_generate, mock_enrich, mock_verify, mock_audit
    ):
        """Response has titulo, linha_fina, conteudo, tags, verification, structured_data, correlation_id."""
        from functions.generation_api import generate_article_handler
        from services.fact_check_service import EnrichmentContext

        mock_generate.return_value = _make_llm_result()
        mock_enrich.return_value = EnrichmentContext(success=False)
        mock_verify.return_value = _make_verification_metadata()

        req = _make_http_request(VALID_BODY)
        response = await generate_article_handler(req)
        data = json.loads(response.get_body())

        assert "titulo" in data
        assert "linha_fina" in data
        assert "conteudo" in data
        assert "tags_sugeridas" in data
        assert "structured_data" in data
        assert "correlation_id" in data
        assert "publish_blocked" in data
        assert "material_sufficiency" in data

    @pytest.mark.asyncio
    @patch("functions.generation_api._persist_audit", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.verify_article", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.enrich_context", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.generate_article", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.__init__", return_value=None)
    @patch("services.fact_check_service.is_fact_check_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_enrichment_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_verification_enabled", new=lambda: True)
    async def test_correlation_id_in_response(
        self, mock_llm_init, mock_generate, mock_enrich, mock_verify, mock_audit
    ):
        """Response includes an 8-char correlation_id."""
        from functions.generation_api import generate_article_handler
        from services.fact_check_service import EnrichmentContext

        mock_generate.return_value = _make_llm_result()
        mock_enrich.return_value = EnrichmentContext(success=False)
        mock_verify.return_value = _make_verification_metadata()

        req = _make_http_request(VALID_BODY)
        response = await generate_article_handler(req)
        data = json.loads(response.get_body())

        assert "correlation_id" in data
        assert len(data["correlation_id"]) == 8


# ===========================================================================
# Test: Phase Failures
# ===========================================================================

class TestHandlerPhaseFailures:
    """Tests for graceful degradation when individual phases fail."""

    @pytest.mark.asyncio
    @patch("functions.generation_api._persist_audit", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.verify_article", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.enrich_context", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.generate_article", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.__init__", return_value=None)
    @patch("services.fact_check_service.is_fact_check_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_enrichment_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_verification_enabled", new=lambda: True)
    async def test_enrichment_failure_still_generates(
        self, mock_llm_init, mock_generate, mock_enrich, mock_verify, mock_audit
    ):
        """If enrichment fails, generation still proceeds."""
        from functions.generation_api import generate_article_handler
        from services.fact_check_service import EnrichmentContext

        mock_enrich.side_effect = Exception("Exa API down")
        mock_generate.return_value = _make_llm_result()
        mock_verify.return_value = _make_verification_metadata()

        req = _make_http_request(VALID_BODY)
        response = await generate_article_handler(req)

        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert "titulo" in data

    @pytest.mark.asyncio
    @patch("functions.generation_api._persist_audit", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.verify_article", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.enrich_context", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.generate_article", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.__init__", return_value=None)
    @patch("services.fact_check_service.is_fact_check_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_enrichment_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_verification_enabled", new=lambda: True)
    async def test_verification_failure_flags_review(
        self, mock_llm_init, mock_generate, mock_enrich, mock_verify, mock_audit
    ):
        """If verification fails, human review is flagged."""
        from functions.generation_api import generate_article_handler
        from services.fact_check_service import EnrichmentContext

        mock_enrich.return_value = EnrichmentContext(success=False)
        mock_generate.return_value = _make_llm_result()
        mock_verify.side_effect = Exception("Verification error")

        req = _make_http_request(VALID_BODY)
        response = await generate_article_handler(req)

        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert data.get("human_review_required") is True

    @pytest.mark.asyncio
    @patch("services.llm_service.LLMService.generate_article", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.__init__", return_value=None)
    @patch("services.fact_check_service.is_fact_check_enabled", new=lambda: False)
    async def test_generation_failure_returns_502(
        self, mock_llm_init, mock_generate
    ):
        """If generation fails, returns 502."""
        from functions.generation_api import generate_article_handler

        mock_generate.side_effect = Exception("LLM API timeout")

        req = _make_http_request(VALID_BODY)
        response = await generate_article_handler(req)

        assert response.status_code == 502


# ===========================================================================
# Test: Input Validation
# ===========================================================================

class TestHandlerInputValidation:
    """Tests for request validation."""

    @pytest.mark.asyncio
    async def test_empty_body_returns_400(self):
        """Empty/invalid JSON returns 400."""
        from functions.generation_api import generate_article_handler

        req = MagicMock()
        req.get_json.side_effect = ValueError("No JSON")
        response = await generate_article_handler(req)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_short_texto_base_returns_400(self):
        """texto_base shorter than 20 chars returns 400."""
        from functions.generation_api import generate_article_handler

        req = _make_http_request({"texto_base": "Short"})
        response = await generate_article_handler(req)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self):
        """Invalid JSON body returns 400."""
        from functions.generation_api import generate_article_handler

        req = MagicMock()
        req.get_json.side_effect = ValueError("Bad JSON")
        response = await generate_article_handler(req)
        assert response.status_code == 400


# ===========================================================================
# Test: Safety Integration
# ===========================================================================

class TestHandlerSafetyIntegration:
    """Tests for safety gate integration in handler response."""

    @pytest.mark.asyncio
    @patch("functions.generation_api._persist_audit", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.verify_article", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.enrich_context", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.generate_article", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.__init__", return_value=None)
    @patch("services.fact_check_service.is_fact_check_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_enrichment_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_verification_enabled", new=lambda: True)
    async def test_critical_risk_blocks_in_response(
        self, mock_llm_init, mock_generate, mock_enrich, mock_verify, mock_audit
    ):
        """Critical risk level results in publish_blocked=True."""
        from functions.generation_api import generate_article_handler
        from services.fact_check_service import EnrichmentContext, VerificationMetadata

        mock_enrich.return_value = EnrichmentContext(success=False)
        mock_generate.return_value = _make_llm_result()

        critical_meta = _make_verification_metadata()
        critical_meta.risk_level = "critical"
        critical_meta.confidence_score = 0.2
        critical_meta.fabricated_claims = 5
        mock_verify.return_value = critical_meta

        req = _make_http_request(VALID_BODY)
        response = await generate_article_handler(req)
        data = json.loads(response.get_body())

        assert data["publish_blocked"] is True
        assert len(data["block_reason"]) > 0

    @pytest.mark.asyncio
    @patch("functions.generation_api._persist_audit", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.verify_article", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.enrich_context", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.generate_article", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.__init__", return_value=None)
    @patch("services.fact_check_service.is_fact_check_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_enrichment_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_verification_enabled", new=lambda: True)
    async def test_entity_tags_merged_in_response(
        self, mock_llm_init, mock_generate, mock_enrich, mock_verify, mock_audit
    ):
        """Entity tags are merged into tags_sugeridas."""
        from functions.generation_api import generate_article_handler
        from services.fact_check_service import EnrichmentContext

        mock_enrich.return_value = EnrichmentContext(success=False)
        result = _make_llm_result()
        result["tags_sugeridas"] = ["politica"]
        mock_generate.return_value = result
        mock_verify.return_value = _make_verification_metadata()

        req = _make_http_request(VALID_BODY)
        response = await generate_article_handler(req)
        data = json.loads(response.get_body())

        # Should have original + entity-derived tags
        assert "politica" in data["tags_sugeridas"]
        # Entity tags should be present (Lula, Brasilia from verification mock)
        assert len(data["tags_sugeridas"]) > 1

    @pytest.mark.asyncio
    @patch("functions.generation_api._persist_audit", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.verify_article", new_callable=AsyncMock)
    @patch("services.fact_check_service.FactCheckService.enrich_context", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.generate_article", new_callable=AsyncMock)
    @patch("services.llm_service.LLMService.__init__", return_value=None)
    @patch("services.fact_check_service.is_fact_check_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_enrichment_enabled", new=lambda: True)
    @patch("services.fact_check_service._get_verification_enabled", new=lambda: True)
    async def test_structured_data_in_response(
        self, mock_llm_init, mock_generate, mock_enrich, mock_verify, mock_audit
    ):
        """Response includes structured_data with Schema.org fields."""
        from functions.generation_api import generate_article_handler
        from services.fact_check_service import EnrichmentContext

        mock_enrich.return_value = EnrichmentContext(success=False)
        mock_generate.return_value = _make_llm_result()
        mock_verify.return_value = _make_verification_metadata()

        req = _make_http_request(VALID_BODY)
        response = await generate_article_handler(req)
        data = json.loads(response.get_body())

        sd = data["structured_data"]
        assert sd["@type"] == "NewsArticle"
        assert "dateCreated" in sd
        assert sd["isAccessibleForFree"] is True
        assert "sameAs" in sd["publisher"]


# ===========================================================================
# Run tests
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
