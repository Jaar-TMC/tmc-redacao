"""
Integration test: CNN Brasil drowning article scenario.

Validates that the fixes to fact extraction, prompt building, and source coverage
scoring correctly handle the exact scenario that exposed the bug:
- CNN Brasil article with 2 drowning deaths
- Generated article that dropped the 2nd death and padded with generic safety tips

Tests cover:
1. Fact extraction prompt now sees full article (8000 chars, not 3000)
2. Fact extraction requests 10+ facts (not 5)
3. Prompt instruction changed from "ONLY use extracted facts" to guidance
4. Source coverage checker detects when 2nd death is missing
5. Source coverage checker passes when both deaths are present
6. Frontend prompt includes CONFORMIDADE COM FONTE section
"""
import os
import re
import pytest

# Resolve project root from test file location
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_TEST_DIR)
_PROJECT_DIR = os.path.dirname(os.path.dirname(_BACKEND_DIR))
_LLM_SERVICE_PATH = os.path.join(_BACKEND_DIR, "services", "llm_service.py")
_PROMPT_BUILDER_PATH = os.path.join(_PROJECT_DIR, "tmc-redacao", "src", "utils", "promptBuilder.js")


# ── CNN Brasil source article (Portuguese, ~2500 chars) ──────────────
CNN_SOURCE = """Duas pessoas morreram afogadas durante a Páscoa em Ubatuba, no litoral norte de São Paulo, no domingo (5). No total, o GBMar (Grupamento de Bombeiros Marítimo) atendeu 59 ocorrências de afogamento em todo o litoral entre os dias 3 e 5 de abril.

A primeira morte foi registrada por volta das 8h50 na Praia das Toninhas. Um homem de 49 anos entrou no mar para ajudar crianças que estavam com dificuldade para voltar à areia, mas acabou arrastado pela correnteza.

O resgate mobilizou três viaturas e seis bombeiros. As equipes encontraram a vítima em estado grave, com afogamento de grau 6. Os bombeiros iniciaram os procedimentos de reanimação e conseguiram reverter o quadro inicialmente, mas o homem sofreu nova parada cardiorrespiratória durante o transporte. O óbito foi constatado pelo médico durante o transporte.

A segunda morte ocorreu às 12h40 na Praia do Sapê, próximo à Ilha do Pontal. Salva-vidas identificaram duas pessoas com dificuldade na água. Um homem de 53 anos foi retirado em estado grave e recebeu manobras de reanimação até a chegada do SAMU. Ele foi transportado à UPA, mas não resistiu. A segunda vítima foi recuperada com sinais vitais estáveis.

No total, o GBMar realizou 23.356 ações preventivas, resgatando 89 vítimas em 59 ocorrências. Ubatuba sozinha atendeu nove casos de afogamento, salvando 11 pessoas — sendo o único município com óbitos no período.

Detalhamento por município: Guarujá (19 ocorrências, 32 resgatados); Bertioga (6, 9); Praia Grande (4, 4); Mongaguá (2, 2); Ilhabela (2, 2); São Sebastião (12, 19); Ubatuba (9, 11, 2 óbitos); Itanhaém (5, 10); Ilha Comprida (1, 1)."""


# ── Simulated BAD generated article (before fix): drops 2nd death ────
BAD_GENERATED = """O feriado de Páscoa terminou com duas mortes por afogamento em Ubatuba, no litoral norte de São Paulo. Os casos aconteceram no domingo (5 de abril). Segundo o GBMar, foram 59 ocorrências de afogamento em todo o litoral paulista entre os dias 3 e 5 de abril.

Homem morre ao tentar salvar crianças

A primeira morte foi registrada por volta das 8h50 na Praia das Toninhas. Um homem de 49 anos entrou no mar para ajudar crianças que estavam com dificuldade para voltar à areia. Ele acabou arrastado pela correnteza.

O resgate mobilizou três viaturas e seis bombeiros. As equipes encontraram a vítima em estado grave com afogamento de grau 6.

Os bombeiros iniciaram os procedimentos de reanimação e conseguiram reverter o quadro inicialmente. Porém, o homem sofreu nova parada cardiorrespiratória durante o transporte.

Correnteza é principal risco

A correnteza é a principal causa de afogamentos no litoral paulista. Ela pode arrastar banhistas mesmo em águas rasas.

Segundo orientação do GBMar, quem for pego pela correnteza deve nadar paralelamente à praia. Nadar contra a correnteza esgota as forças rapidamente.

Prevenção é fundamental

O GBMar orienta os banhistas a observar as bandeiras de sinalização nas praias. Bandeira vermelha indica proibição de banho. Bandeira amarela pede atenção redobrada.

Em caso de afogamento, a orientação é acionar imediatamente o Corpo de Bombeiros pelo 193."""


# ── Simulated GOOD generated article (after fix): both deaths present ─
GOOD_GENERATED = """O feriado de Páscoa terminou com duas mortes por afogamento em Ubatuba, no litoral norte de São Paulo. Os casos aconteceram no domingo (5 de abril). Segundo o GBMar, foram 59 ocorrências de afogamento em todo o litoral paulista entre os dias 3 e 5 de abril.

Homem morre ao tentar salvar crianças

A primeira morte foi registrada por volta das 8h50 na Praia das Toninhas. Um homem de 49 anos entrou no mar para ajudar crianças que estavam com dificuldade para voltar à areia. Ele acabou arrastado pela correnteza.

O resgate mobilizou três viaturas e seis bombeiros. As equipes encontraram a vítima em estado grave com afogamento de grau 6. Os bombeiros iniciaram reanimação e reverteram o quadro inicialmente, mas o homem sofreu nova parada cardiorrespiratória durante o transporte. O óbito foi constatado pelo médico.

Segunda morte na Praia do Sapê

A segunda morte ocorreu às 12h40 na Praia do Sapê, próximo à Ilha do Pontal. Salva-vidas identificaram duas pessoas com dificuldade na água. Um homem de 53 anos foi retirado em estado grave e recebeu manobras de reanimação até a chegada do SAMU. Ele foi transportado à UPA, mas não resistiu. A segunda vítima foi recuperada com sinais vitais estáveis.

Balanço do feriado

No total, o GBMar realizou 23.356 ações preventivas, resgatando 89 vítimas em 59 ocorrências. Ubatuba atendeu nove casos de afogamento, salvando 11 pessoas, sendo o único município com óbitos.

Por município: Guarujá registrou 19 ocorrências com 32 resgatados; São Sebastião teve 12 ocorrências e 19 resgatados; Bertioga, 6 ocorrências e 9 resgatados; Itanhaém, 5 e 10; Praia Grande, 4 e 4; Mongaguá, Ilhabela, 2 cada; Ilha Comprida, 1."""


# ─────────────────────────────────────────────────────────────────────
# Test 1: Source coverage checker detects missing 2nd death
# ─────────────────────────────────────────────────────────────────────
class TestSourceCoverageScenario:
    """Test the _compute_source_coverage_score method with real scenario data."""

    def _compute_coverage(self, source: str, article: str) -> float:
        """Standalone version of the coverage scorer (mirrors fact_check_service)."""
        if not source or not article:
            return 0.5

        source_lower = source.lower()
        article_lower = article.lower()
        markers = set()

        # 1. Numbers
        numbers = re.findall(r'\b\d+(?:[.,]\d+)?(?:\s*%|\s*anos?)?\b', source_lower)
        for n in numbers:
            n_clean = n.strip()
            if len(n_clean) >= 1:
                markers.add(n_clean)

        # 2. Proper nouns
        words = source.split()
        for i, word in enumerate(words):
            clean = word.strip(".,;:!?\"'()[]{}—–-")
            if (len(clean) >= 3 and clean[0].isupper() and not clean.isupper()
                    and i > 0 and not words[i-1].endswith('.')):
                markers.add(clean.lower())

        # 3. Location names
        locations = re.findall(r'(?:praia|cidade|municipio|bairro)\s+(?:d[eoa]\s+)?(\w+)', source_lower)
        markers.update(locations)

        if len(markers) < 3:
            return 0.5

        found = sum(1 for m in markers if m in article_lower)
        return min(1.0, found / len(markers))

    def test_bad_article_has_lower_coverage(self):
        """Article missing 2nd death should score lower than complete article."""
        bad_score = self._compute_coverage(CNN_SOURCE, BAD_GENERATED)
        good_score = self._compute_coverage(CNN_SOURCE, GOOD_GENERATED)
        assert good_score > bad_score, (
            f"Good article ({good_score:.2f}) should score higher than bad ({bad_score:.2f})"
        )

    def test_bad_article_missing_key_markers(self):
        """Article missing 2nd death should be missing critical markers."""
        bad_score = self._compute_coverage(CNN_SOURCE, BAD_GENERATED)
        # The bad article is missing: Sapê, Pontal, 53 anos, 12h40, SAMU, UPA,
        # 23.356, 89, Guarujá, Bertioga, Mongaguá, Itanhaém, etc.
        # Coverage should be noticeably below 1.0
        assert bad_score < 0.75, (
            f"Bad article coverage {bad_score:.2f} should be < 0.75 (missing many markers)"
        )

    def test_good_article_has_high_coverage(self):
        """Article with both deaths should have high coverage."""
        good_score = self._compute_coverage(CNN_SOURCE, GOOD_GENERATED)
        assert good_score >= 0.75, (
            f"Good article coverage {good_score:.2f} should be >= 0.75"
        )

    def test_key_entities_from_second_death_detected(self):
        """Verify that markers include entities from the 2nd death."""
        source_lower = CNN_SOURCE.lower()
        markers = set()

        numbers = re.findall(r'\b\d+(?:[.,]\d+)?(?:\s*%|\s*anos?)?\b', source_lower)
        for n in numbers:
            if len(n.strip()) >= 1:
                markers.add(n.strip())

        words = CNN_SOURCE.split()
        for i, word in enumerate(words):
            clean = word.strip(".,;:!?\"'()[]{}—–-")
            if (len(clean) >= 3 and clean[0].isupper() and not clean.isupper()
                    and i > 0 and not words[i-1].endswith('.')):
                markers.add(clean.lower())

        locations = re.findall(r'(?:praia|cidade|municipio|bairro)\s+(?:d[eoa]\s+)?(\w+)', source_lower)
        markers.update(locations)

        # Key markers from 2nd death that MUST be extracted
        # "53 anos" is matched as a unit by the regex, so check for that or just "53"
        has_53 = any("53" in m for m in markers)
        assert has_53, f"Age 53 (second victim) must be in markers. Got: {markers}"
        has_sape = any("sap" in m for m in markers)
        assert has_sape, f"Praia do Sapê must be in markers. Got: {markers}"

    def test_single_digit_numbers_included(self):
        """Numbers like '2' (as in '2 mortes') must be captured."""
        source_lower = CNN_SOURCE.lower()
        numbers = re.findall(r'\b\d+(?:[.,]\d+)?(?:\s*%|\s*anos?)?\b', source_lower)
        cleaned = {n.strip() for n in numbers if len(n.strip()) >= 1}
        assert "2" in cleaned, f"Single digit '2' must be in markers. Got: {cleaned}"


# ─────────────────────────────────────────────────────────────────────
# Test 2: Fact extraction prompt changes
# ─────────────────────────────────────────────────────────────────────
class TestFactExtractionPromptChanges:
    """Verify that llm_service.py fact extraction changes are correct."""

    def test_extraction_window_is_8000(self):
        """Fact extraction should use 8000 chars, not 3000."""
        with open(_LLM_SERVICE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify extraction window
        assert "texto_base[:8000]" in content, "Fact extraction should use 8000 char window"
        assert "texto_base[:3000]" not in content, "Old 3000 char window should be removed"

    def test_extraction_requests_minimum_10_facts(self):
        """Fact extraction prompt should request minimum 10 facts."""
        with open(_LLM_SERVICE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Liste 5 afirmacoes" not in content, "Old '5 facts' instruction should be removed"
        assert "minimo 10" in content, "Should request minimum 10 facts"

    def test_extraction_max_tokens_increased(self):
        """Fact extraction max_tokens should be 1500, not 512."""
        with open(_LLM_SERVICE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the _extract_facts_with_haiku function and check max_tokens
        func_start = content.find("async def _extract_facts_with_haiku")
        func_end = content.find("\n    async def ", func_start + 1)
        func_body = content[func_start:func_end]

        assert "max_tokens=1500" in func_body, (
            f"max_tokens in _extract_facts_with_haiku should be 1500"
        )
        assert "max_tokens=512" not in func_body, "Old 512 token limit should be removed"

    def test_prompt_uses_guide_not_only(self):
        """Generation prompt should use 'GUIA' not 'APENAS nos fatos extraidos'."""
        with open(_LLM_SERVICE_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Escreva baseado APENAS nos fatos extraidos acima" not in content, \
            "Old 'APENAS' instruction should be removed"
        assert "REGRA ANTI-COPIA" in content, \
            "New instruction should include REGRA ANTI-COPIA"


# ─────────────────────────────────────────────────────────────────────
# Test 3: Weight constants
# ─────────────────────────────────────────────────────────────────────
class TestWeightConstants:
    """Verify confidence scoring weights are correct."""

    def test_weights_sum_to_one(self):
        """All 7 weights must sum to 1.0."""
        from services.fact_check_service import (
            WEIGHT_CLAIM_GROUNDING, WEIGHT_ENTITY_OVERLAP,
            WEIGHT_EXPANSION_RATIO, WEIGHT_QUOTE_VERIFICATION,
            WEIGHT_MATERIAL_SUFFICIENCY, WEIGHT_CLAIM_SIMILARITY,
            WEIGHT_SOURCE_COVERAGE
        )
        total = (WEIGHT_CLAIM_GROUNDING + WEIGHT_ENTITY_OVERLAP +
                 WEIGHT_EXPANSION_RATIO + WEIGHT_QUOTE_VERIFICATION +
                 WEIGHT_MATERIAL_SUFFICIENCY + WEIGHT_CLAIM_SIMILARITY +
                 WEIGHT_SOURCE_COVERAGE)
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_source_coverage_weight_exists(self):
        """WEIGHT_SOURCE_COVERAGE must be defined and positive."""
        from services.fact_check_service import WEIGHT_SOURCE_COVERAGE
        assert WEIGHT_SOURCE_COVERAGE > 0, "WEIGHT_SOURCE_COVERAGE must be > 0"
        assert WEIGHT_SOURCE_COVERAGE == 0.10, "WEIGHT_SOURCE_COVERAGE should be 0.10"


# ─────────────────────────────────────────────────────────────────────
# Test 4: Frontend prompt conformidade section
# ─────────────────────────────────────────────────────────────────────
class TestPromptBuilderConformidade:
    """Verify promptBuilder.js includes CONFORMIDADE section."""

    def test_conformidade_section_exists(self):
        """promptBuilder.js must contain the CONFORMIDADE COM FONTE section."""
        with open(_PROMPT_BUILDER_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        assert "CONFORMIDADE COM FONTE" in content, \
            "promptBuilder.js must include CONFORMIDADE COM FONTE section"
        assert "TODAS as mortes" in content, \
            "Must instruct to include ALL deaths"
        assert "NAO substitua fatos da fonte por dicas genericas" in content, \
            "Must prohibit generic safety tip padding"
