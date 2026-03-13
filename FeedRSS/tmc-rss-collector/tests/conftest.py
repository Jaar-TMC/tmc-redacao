"""
Shared test fixtures for TMC pipeline tests.
"""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set test environment defaults (before any config module import).
# PRODUCTION_SAFETY_MODE=false avoids requiring JWT_SECRET_KEY in tests.
os.environ.setdefault("PRODUCTION_SAFETY_MODE", "false")


@pytest.fixture(autouse=True)
def _reset_config_singleton():
    """Reset config singleton before each test so env changes take effect."""
    import services.config as cfg_mod
    cfg_mod._config = None
    yield
    cfg_mod._config = None


@pytest.fixture
def fact_check_service():
    """Create a FactCheckService instance for testing."""
    from services.fact_check_service import FactCheckService
    return FactCheckService()


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service with call_api."""
    mock = AsyncMock()
    mock.call_api = AsyncMock(return_value='{"key_facts": ["Fact 1"]}')
    mock._call_api = AsyncMock(return_value='{"key_facts": ["Fact 1"]}')
    return mock


@pytest.fixture
def sample_source_text():
    """Sample source text for testing."""
    return (
        "O presidente Luiz Inácio Lula da Silva sancionou a lei que cria o "
        "programa Bolsa Família Digital. A medida foi anunciada pelo Ministério "
        "da Fazenda em Brasília nesta segunda-feira. O PIB cresceu 2,5% no "
        "último trimestre, segundo dados do IBGE. O Supremo Tribunal Federal "
        "deve julgar a constitucionalidade da medida na próxima semana."
    )


@pytest.fixture
def sample_generated_article():
    """Sample generated article for testing."""
    return (
        "O presidente **Luiz Inácio Lula da Silva** sancionou nesta segunda-feira "
        "a lei que institui o programa **Bolsa Família Digital**, uma iniciativa do "
        "**Ministério da Fazenda** que visa modernizar a distribuição de benefícios "
        "sociais no país.\n\n"
        "A medida foi anunciada em **Brasília** e representa um avanço significativo "
        "na digitalização dos serviços públicos. Segundo dados do **IBGE**, o **PIB** "
        "brasileiro cresceu **2,5%** no último trimestre, o que reforça o cenário "
        "positivo para novos investimentos em programas sociais.\n\n"
        "O **Supremo Tribunal Federal** (STF) deve julgar a constitucionalidade da "
        "medida na próxima semana, em sessão plenária que promete ser acompanhada "
        "de perto pelo governo e pela oposição."
    )


@pytest.fixture
def sample_verification_data():
    """Sample verification result dict."""
    return {
        "confidence_score": 0.72,
        "risk_level": "medium",
        "expansion_ratio": 2.5,
        "source_sufficiency": "sufficient",
        "total_claims": 5,
        "grounded_claims": 4,
        "fabricated_claims": 0,
        "unverifiable_claims": 1,
        "is_verified": True,
        "entity_comparison": {
            "source_entities": ["Lula", "Ministério da Fazenda", "STF"],
            "output_entities": ["Lula", "Ministério da Fazenda", "STF", "IBGE"],
            "common_entities": ["Lula", "Ministério da Fazenda", "STF"],
            "novel_entities": ["IBGE"],
            "overlap_score": 0.75,
        },
        "quote_verification": {
            "total_quotes": 0,
            "verified_quotes": 0,
            "unverified_quotes": [],
            "verification_rate": 0.5,
        },
    }


# =============================================================================
# Safety gate test fixtures and factories
# =============================================================================

@pytest.fixture
def production_mode():
    """Enable production safety mode for a test."""
    with patch.dict(os.environ, {
        "PRODUCTION_SAFETY_MODE": "true",
        "JWT_SECRET_KEY": "a" * 32,
    }):
        import services.config as cfg_mod
        cfg_mod._config = None
        yield
        cfg_mod._config = None


@pytest.fixture
def legacy_mode():
    """Disable production safety mode."""
    with patch.dict(os.environ, {
        "PRODUCTION_SAFETY_MODE": "false",
    }):
        import services.config as cfg_mod
        cfg_mod._config = None
        yield
        cfg_mod._config = None


def make_verification_data(**overrides):
    """Factory for verification data dicts with safe defaults.

    Returns a dict representing a clean, passing verification result.
    Override any field via keyword arguments.
    """
    base = {
        "risk_level": "low",
        "confidence_score": 0.80,
        "fabricated_claims": 0,
        "unverifiable_claims": 0,
        "total_claims": 10,
        "grounded_claims": 8,
        "context_claims": 0,
        "expansion_ratio": 2.0,
        "is_verified": True,
        "entity_comparison": {
            "novel_entities": [],
            "output_entities": ["E1", "E2", "E3"],
            "source_entities": ["E1", "E2", "E3"],
            "common_entities": ["E1", "E2", "E3"],
        },
    }
    base.update(overrides)
    return base
