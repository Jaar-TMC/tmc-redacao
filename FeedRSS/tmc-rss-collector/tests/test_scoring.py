"""
Tests for ScoringService._calculate_scores() and _heuristic_score_article().

Covers:
- Signal-to-point mapping for all 4 signals
- Classification boundaries (A >= 75, B >= 35, C < 35)
- Edge cases (missing/invalid signals, max/min scores)
- Heuristic keyword matching fallback
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.scoring_service import (
    ScoringService,
    _heuristic_score_article,
    SCORE_INESPERADO,
    SCORE_IMPACTO,
    SCORE_BUSCA_AGORA,
    SCORE_CONVERSA,
    THRESHOLD_A,
    THRESHOLD_B,
)


# =============================================================================
# _calculate_scores tests
# =============================================================================

class TestCalculateScores:
    """Tests for ScoringService._calculate_scores()."""

    def setup_method(self):
        """Create a ScoringService with no dependencies (only _calculate_scores is used)."""
        self.service = ScoringService(llm_service=None, db_service=None)

    # --- Signal-to-point mapping (parametrized) ---

    @pytest.mark.parametrize(
        "signal_value,expected_points",
        [
            ("yes", 25),
            ("partial", 12),
            ("no", 0),
        ],
    )
    def test_inesperado_signal_mapping(self, signal_value, expected_points):
        """Each inesperado signal value maps to correct points."""
        signals = {"sinal_inesperado": signal_value}
        scores, _, _ = self.service._calculate_scores(signals)
        assert scores["score_inesperado"] == expected_points

    @pytest.mark.parametrize(
        "signal_value,expected_points",
        [
            ("high", 30),
            ("medium", 15),
            ("low", 0),
        ],
    )
    def test_impacto_signal_mapping(self, signal_value, expected_points):
        """Each impacto signal value maps to correct points."""
        signals = {"sinal_impacto": signal_value}
        scores, _, _ = self.service._calculate_scores(signals)
        assert scores["score_impacto"] == expected_points

    @pytest.mark.parametrize(
        "signal_value,expected_points",
        [
            ("yes", 25),
            ("maybe", 12),
            ("no", 0),
        ],
    )
    def test_busca_agora_signal_mapping(self, signal_value, expected_points):
        """Each busca_agora signal value maps to correct points."""
        signals = {"sinal_busca_agora": signal_value}
        scores, _, _ = self.service._calculate_scores(signals)
        assert scores["score_busca_agora"] == expected_points

    @pytest.mark.parametrize(
        "signal_value,expected_points",
        [
            ("yes", 20),
            ("maybe", 10),
            ("no", 0),
        ],
    )
    def test_conversa_signal_mapping(self, signal_value, expected_points):
        """Each conversa signal value maps to correct points."""
        signals = {"sinal_conversa": signal_value}
        scores, _, _ = self.service._calculate_scores(signals)
        assert scores["score_conversa"] == expected_points

    # --- Total score and classification ---

    def test_max_score_100_class_a(self):
        """All max signals yield 100 points and class A."""
        signals = {
            "sinal_inesperado": "yes",      # 25
            "sinal_impacto": "high",         # 30
            "sinal_busca_agora": "yes",      # 25
            "sinal_conversa": "yes",         # 20
        }
        scores, total, classification = self.service._calculate_scores(signals)
        assert total == 100
        assert classification == "A"

    def test_min_score_0_class_c(self):
        """All min signals yield 0 points and class C."""
        signals = {
            "sinal_inesperado": "no",
            "sinal_impacto": "low",
            "sinal_busca_agora": "no",
            "sinal_conversa": "no",
        }
        scores, total, classification = self.service._calculate_scores(signals)
        assert total == 0
        assert classification == "C"

    def test_all_partial_maybe_49_class_b(self):
        """All partial/maybe signals yield 49 points -> class B."""
        signals = {
            "sinal_inesperado": "partial",   # 12
            "sinal_impacto": "medium",       # 15
            "sinal_busca_agora": "maybe",    # 12
            "sinal_conversa": "maybe",       # 10
        }
        scores, total, classification = self.service._calculate_scores(signals)
        assert total == 49
        assert classification == "B"

    def test_class_a_boundary_at_75(self):
        """Score == 75 is class A."""
        # 25 + 30 + 0 + 20 = 75
        signals = {
            "sinal_inesperado": "yes",      # 25
            "sinal_impacto": "high",         # 30
            "sinal_busca_agora": "no",       # 0
            "sinal_conversa": "yes",         # 20
        }
        _, total, classification = self.service._calculate_scores(signals)
        assert total == 75
        assert classification == "A"

    def test_class_b_at_67_below_a_threshold(self):
        """Highest B-class reachable score (67) is below A threshold (75)."""
        # 25 + 30 + 12 + 0 = 67 -> B (74 is unreachable with valid signals)
        signals = {
            "sinal_inesperado": "yes",       # 25
            "sinal_impacto": "high",          # 30
            "sinal_busca_agora": "maybe",    # 12
            "sinal_conversa": "no",           # 0
        }
        _, total, classification = self.service._calculate_scores(signals)
        assert total == 67
        assert classification == "B"

    def test_class_b_boundary_at_35(self):
        """Score == 35 is class B (at B threshold)."""
        # 0 + 15 + 0 + 20 = 35
        signals = {
            "sinal_inesperado": "no",        # 0
            "sinal_impacto": "medium",       # 15
            "sinal_busca_agora": "no",       # 0
            "sinal_conversa": "yes",         # 20
        }
        _, total, classification = self.service._calculate_scores(signals)
        assert total == 35
        assert classification == "B"

    def test_class_c_boundary_at_34(self):
        """Score < 35 is class C."""
        # 12 + 0 + 12 + 10 = 34
        signals = {
            "sinal_inesperado": "partial",   # 12
            "sinal_impacto": "low",          # 0
            "sinal_busca_agora": "maybe",    # 12
            "sinal_conversa": "maybe",       # 10
        }
        _, total, classification = self.service._calculate_scores(signals)
        assert total == 34
        assert classification == "C"

    # --- Missing/invalid signal handling ---

    def test_missing_signals_default_to_zero(self):
        """Missing signal keys default to 0 points."""
        scores, total, classification = self.service._calculate_scores({})
        assert total == 0
        assert classification == "C"
        assert scores["score_inesperado"] == 0
        assert scores["score_impacto"] == 0
        assert scores["score_busca_agora"] == 0
        assert scores["score_conversa"] == 0

    def test_invalid_signal_value_defaults_to_zero(self):
        """Invalid signal value (e.g. typo) defaults to 0 points."""
        signals = {
            "sinal_inesperado": "invalid_value",
            "sinal_impacto": "XXXX",
        }
        scores, total, _ = self.service._calculate_scores(signals)
        assert scores["score_inesperado"] == 0
        assert scores["score_impacto"] == 0

    def test_return_tuple_structure(self):
        """_calculate_scores returns (scores_dict, total_int, classification_str)."""
        scores, total, classification = self.service._calculate_scores({})
        assert isinstance(scores, dict)
        assert isinstance(total, int)
        assert isinstance(classification, str)
        assert classification in ("A", "B", "C")


# =============================================================================
# _heuristic_score_article tests
# =============================================================================

class TestHeuristicScoring:
    """Tests for _heuristic_score_article() keyword-based fallback."""

    def test_no_keywords_low_scores(self):
        """Article with no relevant keywords gets lowest signals."""
        result = _heuristic_score_article(
            "Comunicado generico",
            "Texto sem nenhuma palavra chave relevante para pontuacao editorial.",
        )
        assert result["sinal_inesperado"] == "no"
        assert result["sinal_impacto"] == "low"
        assert result["sinal_busca_agora"] == "no"
        assert result["sinal_conversa"] == "no"

    def test_inesperado_2_keywords_yes(self):
        """2+ inesperado keywords yield 'yes' signal."""
        result = _heuristic_score_article(
            "Surpresa: demissao inesperada",
            "O ministro renunciou de forma surpreendente e inesperada.",
        )
        assert result["sinal_inesperado"] == "yes"

    def test_inesperado_1_keyword_partial(self):
        """1 inesperado keyword yields 'partial' signal."""
        result = _heuristic_score_article(
            "Noticia do dia",
            "O tema tomou uma dimensao surpreendente na regiao.",
        )
        # 'surpreendente' is 1 match -> partial (avoid 'titulo' in title which is also a keyword)
        assert result["sinal_inesperado"] == "partial"

    def test_impacto_with_relevance_boost(self):
        """1 impacto keyword + relevance term yields 'high'."""
        result = _heuristic_score_article(
            "Governo anuncia aumento de precos",
            "O presidente Lula anunciou aumento de precos.",
        )
        # 'aumento' is impacto keyword, 'presidente' and 'lula' are relevance terms
        assert result["sinal_impacto"] == "high"

    def test_impacto_1_keyword_no_boost_medium(self):
        """1 impacto keyword without relevance boost yields 'medium'."""
        result = _heuristic_score_article(
            "Noticia do dia",
            "Houve uma votacao hoje na cidade.",
        )
        # 'votacao' is 1 impacto keyword, no relevance terms -> medium
        assert result["sinal_impacto"] == "medium"

    def test_busca_with_relevance_boost(self):
        """1 busca keyword + relevance term yields 'yes'."""
        result = _heuristic_score_article(
            "Resultado do jogo do Flamengo",
            "O resultado do jogo do Flamengo foi decidido.",
        )
        # 'resultado' and 'jogo' are busca keywords, 'flamengo' is relevance term
        assert result["sinal_busca_agora"] == "yes"

    def test_conversa_2_keywords_yes(self):
        """2+ conversa keywords yield 'yes' (even without relevance boost)."""
        result = _heuristic_score_article(
            "Polemica e discussao",
            "A polemica gerou uma grande discussao nas redes sociais.",
        )
        assert result["sinal_conversa"] == "yes"

    def test_heuristic_returns_justificativa(self):
        """Heuristic result includes justificativa field."""
        result = _heuristic_score_article("Titulo", "Conteudo")
        assert "justificativa" in result
        assert "heuristica" in result["justificativa"].lower()

    def test_heuristic_handles_empty_content(self):
        """Handles empty/None content gracefully."""
        result = _heuristic_score_article("Titulo", "")
        assert "sinal_inesperado" in result
        result2 = _heuristic_score_article("Titulo", None)
        assert "sinal_inesperado" in result2
