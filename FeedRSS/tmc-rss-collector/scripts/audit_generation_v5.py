"""
TMC Article Generation — Comprehensive Quality Audit v5

This script runs the full 3-phase pipeline (enrichment → generation → verification)
across diverse test cases and produces a detailed quality report covering:

1. ANTI-HALLUCINATION: Confidence, fabrication rate, claim grounding
2. SEO SCORING: Mirrors the frontend SEOAnalyzerPanel (90 raw pts → 0-100)
3. JOURNALISM: BLUF compliance, structure, tone consistency
4. CONSISTENCY: Variance across repeated runs on the same source

Scoring dimensions match the frontend exactly:
  - Content Quality (30 pts): word count, structure, readability
  - On-Page Optimization (25 pts): title, linha_fina, keywords, slug
  - E-E-A-T Signals (20 pts): experience, expertise, authority, trust
  - Technical Excellence (5 pts): external links (manual items excluded)
  - AI & SERP Optimization (10 pts): featured snippet, AI overview
  Total raw = 90, normalized to 0-100

Usage:
  python scripts/audit_generation_v5.py                    # DB articles
  python scripts/audit_generation_v5.py --synthetic        # Synthetic cases only
  python scripts/audit_generation_v5.py --repeat 3         # 3 runs per case (consistency)
  python scripts/audit_generation_v5.py --category politica  # Single category
"""

import os
import sys
import json
import math
import asyncio
import time
import re
import logging
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load local.settings.json
def load_local_settings():
    settings_path = Path(__file__).parent.parent / "local.settings.json"
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key, value in data.get("Values", {}).items():
                os.environ[key] = str(value)
        print(f"[OK] Loaded {len(data.get('Values', {}))} env vars from local.settings.json")
    else:
        print("[WARN] local.settings.json not found — using existing env vars")

load_local_settings()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("audit_v5")
logger.setLevel(logging.INFO)


# =============================================================================
# SEO Scoring Engine (mirrors frontend SEOAnalyzerPanel / seoUtils.js)
# =============================================================================

# --- Constants (from seoConstants.js) ---

POWER_WORDS = {
    "exclusivo", "revela", "urgente", "novo", "inedito", "descubra",
    "surpreendente", "revelado", "confirmado", "historico", "polemico",
    "decisivo", "crucial", "impressionante", "chocante", "bombástico",
}

CTA_WORDS = {
    "saiba", "veja", "confira", "entenda", "descubra", "acompanhe",
    "leia", "conheça", "acesse", "participe",
}

TRANSITION_WORDS = {
    "além disso", "portanto", "no entanto", "por outro lado", "dessa forma",
    "diante disso", "sendo assim", "por fim", "nesse contexto",
    "em contrapartida", "contudo", "todavia", "ademais", "consequentemente",
    "entretanto", "assim", "logo", "enfim", "ou seja", "isto é",
    "em resumo", "de fato", "na verdade", "aliás", "inclusive",
    "sobretudo", "principalmente", "porém", "embora", "apesar de",
}

REPORTING_VERBS = {
    "disse", "afirmou", "declarou", "informou", "explicou", "destacou",
    "ressaltou", "pontuou", "acrescentou", "revelou", "comentou",
    "segundo", "conforme", "de acordo com",
}

EXPERIENCE_PATTERNS = [
    r"segundo apura[cç][aã]o", r"em entrevista", r"nossa reportagem",
    r"no local", r"testemunhou", r"presenciou", r"apurou",
]

OFFICIAL_SOURCES = [
    r"\bministério\b", r"\bprefeitura\b", r"\btribunal\b", r"\bsenado\b",
    r"\bpolícia\b", r"\bbombeiros\b", r"\bexército\b", r"\bIBGE\b",
    r"\bANVISA\b", r"\bCBF\b", r"\bSTF\b", r"\bSTJ\b", r"\bTSE\b",
    r"\bBanco Central\b", r"\bgoverno\b",
]

EXPERT_TITLES = [
    r"\bespecialista\b", r"\badvogado\b", r"\bmédico\b", r"\bpesquisador\b",
    r"\bprofessor\b", r"\bdoutor\b", r"\banalista\b", r"\beconomista\b",
]

CLICKBAIT_PATTERNS = [
    r"você não vai acreditar", r"ninguém esperava", r"chocante!",
    r"impressionante!", r"inacreditável", r"imperdível",
]


def _count_syllables_pt(word: str) -> int:
    """Rough Portuguese syllable count via vowel clusters."""
    word = word.lower().strip()
    vowels = "aeiouáéíóúâêôãõü"
    count = 0
    prev_vowel = False
    for ch in word:
        if ch in vowels:
            if not prev_vowel:
                count += 1
            prev_vowel = True
        else:
            prev_vowel = False
    return max(count, 1)


def _flesch_pt(text: str) -> float:
    """Flesch readability adapted for Portuguese."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
    if not sentences:
        return 0.0
    words = re.findall(r"\b\w+\b", text)
    if not words:
        return 0.0
    avg_words_per_sentence = len(words) / len(sentences)
    avg_syllables_per_word = sum(_count_syllables_pt(w) for w in words) / len(words)
    return 248.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)


def _passive_voice_ratio(text: str) -> float:
    """Estimate passive voice ratio via Portuguese patterns."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
    if not sentences:
        return 0.0
    passive_count = sum(
        1 for s in sentences
        if re.search(r"\b(foi|foram|é|são|será|serão|sido|sendo)\s+\w+(ado|ido|ada|ida|ados|idos|adas|idas)\b", s, re.IGNORECASE)
    )
    return passive_count / len(sentences)


def _transition_ratio(text: str) -> float:
    """Ratio of sentences containing transition words."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 3]
    if not sentences:
        return 0.0
    count = sum(
        1 for s in sentences
        if any(tw in s for tw in TRANSITION_WORDS)
    )
    return count / len(sentences)


@dataclass
class SEOScore:
    """Detailed SEO score mirroring frontend analyzer."""
    # Category 1: Content Quality (30 pts)
    word_count_score: int = 0          # /10
    structure_score: int = 0           # /10
    readability_score: int = 0         # /10

    # Category 2: On-Page Optimization (25 pts)
    title_score: int = 0               # /8
    linha_fina_score: int = 0          # /7
    keyword_score: int = 0             # /5
    slug_score: int = 0                # /5 (always 0 — backend can't control slug)

    # Category 3: E-E-A-T (20 pts)
    experience_score: int = 0          # /5
    expertise_score: int = 0           # /5
    authority_score: int = 0           # /5
    trust_score: int = 0               # /5

    # Category 4: Technical Excellence (5 pts)
    external_links_score: int = 0      # /5 (usually 0 — backend doesn't add links)

    # Category 5: AI & SERP (10 pts)
    featured_snippet_score: int = 0    # /5
    ai_overview_score: int = 0         # /5

    # Diagnostics
    diagnostics: dict = field(default_factory=dict)

    # Computed totals (call finalize() after scoring)
    raw_total: int = 0
    normalized: float = 0.0
    grade: str = ""

    def finalize(self):
        """Compute totals after all sub-scores are set."""
        self.raw_total = (
            self.word_count_score + self.structure_score + self.readability_score
            + self.title_score + self.linha_fina_score + self.keyword_score + self.slug_score
            + self.experience_score + self.expertise_score + self.authority_score + self.trust_score
            + self.external_links_score
            + self.featured_snippet_score + self.ai_overview_score
        )
        self.normalized = round((self.raw_total / 90) * 100, 1)
        if self.normalized >= 80:
            self.grade = "EXCELENTE"
        elif self.normalized >= 60:
            self.grade = "BOM"
        elif self.normalized >= 40:
            self.grade = "REGULAR"
        else:
            self.grade = "CRITICO"


def compute_seo_score(
    titulo: str,
    linha_fina: str,
    conteudo: str,
    tags: list = None,
    tipo_materia: str = "destaque",
) -> SEOScore:
    """Compute SEO score mirroring the frontend SEOAnalyzerPanel."""
    score = SEOScore()
    tags = tags or []
    primary_keyword = tags[0].lower() if tags else ""
    text_lower = conteudo.lower()
    words = re.findall(r"\b\w+\b", conteudo)
    word_count = len(words)

    # =========================================================================
    # 1. Content Quality (30 pts)
    # =========================================================================

    # 1A. Word Count & Depth (/10)
    type_ranges = {
        "nota": (200, 500, 350),
        "destaque": (400, 2000, 800),
        "reportagem": (800, 3000, 1500),
        "analise": (1000, 4000, 2000),
        "coluna": (400, 1200, 700),
        "servico": (400, 2000, 800),
    }
    wmin, wmax, ideal = type_ranges.get(tipo_materia, (400, 2000, 800))
    if wmin <= word_count <= wmax:
        if abs(word_count - ideal) <= ideal * 0.3:
            score.word_count_score = 10
        else:
            score.word_count_score = 7
    elif word_count >= wmin * 0.7:
        score.word_count_score = 4
    elif word_count > 0:
        score.word_count_score = 2
    score.diagnostics["word_count"] = word_count

    # 1B. Structure (/10)
    paragraphs = [p.strip() for p in conteudo.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in conteudo.split("\n") if p.strip()]
    headings = re.findall(r"^#{2,3}\s+.+", conteudo, re.MULTILINE)
    has_lists = bool(re.search(r"^[\-\*]\s+|^\d+\.\s+", conteudo, re.MULTILINE))
    has_quotes = bool(re.search(r'["""].*["""]', conteudo))
    first_para_words = len(re.findall(r"\b\w+\b", paragraphs[0])) if paragraphs else 0
    last_para_words = len(re.findall(r"\b\w+\b", paragraphs[-1])) if paragraphs else 0
    avg_para_words = word_count / max(len(paragraphs), 1)

    struct = 0
    if 30 <= first_para_words <= 100:
        struct += 2
    elif first_para_words > 0:
        struct += 1
    if len(headings) >= 2:
        struct += 2
    elif len(headings) >= 1:
        struct += 1
    if last_para_words >= 50:
        struct += 2
    elif last_para_words >= 20:
        struct += 1
    if avg_para_words <= 150:
        struct += 2
    elif avg_para_words <= 200:
        struct += 1
    if has_lists:
        struct += 1
    if has_quotes:
        struct += 1
    score.structure_score = min(struct, 10)
    score.diagnostics["headings"] = len(headings)
    score.diagnostics["paragraphs"] = len(paragraphs)
    score.diagnostics["first_para_words"] = first_para_words
    score.diagnostics["avg_para_words"] = round(avg_para_words, 1)

    # 1C. Readability (/10)
    flesch = _flesch_pt(conteudo)
    sentences = re.split(r"[.!?]+", conteudo)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
    avg_sentence_words = word_count / max(len(sentences), 1)
    passive_ratio = _passive_voice_ratio(conteudo)
    trans_ratio = _transition_ratio(conteudo)

    read = 0
    if flesch >= 60:
        read += 4
    elif flesch >= 40:
        read += 2
    elif flesch >= 20:
        read += 1
    if avg_sentence_words <= 20:
        read += 2
    elif avg_sentence_words <= 25:
        read += 1
    if passive_ratio < 0.10:
        read += 2
    elif passive_ratio < 0.20:
        read += 1
    if trans_ratio >= 0.30:
        read += 2
    elif trans_ratio >= 0.05:
        read += 1
    score.readability_score = min(read, 10)
    score.diagnostics["flesch"] = round(flesch, 1)
    score.diagnostics["avg_sentence_words"] = round(avg_sentence_words, 1)
    score.diagnostics["passive_ratio"] = round(passive_ratio, 3)
    score.diagnostics["transition_ratio"] = round(trans_ratio, 3)

    # =========================================================================
    # 2. On-Page Optimization (25 pts)
    # =========================================================================

    # 2A. Title (/8)
    titulo_clean = titulo.strip()
    titulo_chars = len(titulo_clean)
    titulo_words = titulo_clean.split()
    titulo_lower = titulo_clean.lower()
    t = 0
    if 50 <= titulo_chars <= 60:
        t += 2
    elif 40 <= titulo_chars <= 70:
        t += 1
    if primary_keyword and primary_keyword in " ".join(titulo_lower.split()[:3]):
        t += 2
    elif primary_keyword and primary_keyword in titulo_lower:
        t += 1
    if any(pw in titulo_lower for pw in POWER_WORDS):
        t += 1
    if re.search(r"\d", titulo_clean):
        t += 1
    # Emotional appeal
    if any(w in titulo_lower for w in ["exclusivo", "chocante", "histórico", "polêmico", "decisivo", "crucial"]):
        t += 1
    # Uniqueness (not generic)
    if not titulo_lower.startswith(("notícia sobre", "noticia sobre", "matéria sobre", "materia sobre")):
        t += 1
    score.title_score = min(t, 8)
    score.diagnostics["titulo_chars"] = titulo_chars
    score.diagnostics["titulo_words"] = len(titulo_words)

    # 2B. Linha Fina (/7)
    lf_clean = linha_fina.strip()
    lf_chars = len(lf_clean)
    lf_words = lf_clean.split()
    lf_lower = lf_clean.lower()
    lf = 0
    if 150 <= lf_chars <= 160:
        lf += 2
    elif 120 <= lf_chars <= 180:
        lf += 1
    if primary_keyword and primary_keyword in lf_lower:
        lf += 2
    elif any(t.lower() in lf_lower for t in tags[:3]):
        lf += 1
    if any(cta in lf_lower for cta in CTA_WORDS):
        lf += 1
    # Unique from title
    titulo_set = set(titulo_lower.split())
    lf_set = set(lf_lower.split())
    overlap = len(titulo_set & lf_set) / max(len(titulo_set | lf_set), 1)
    if overlap < 0.70:
        lf += 1
    # Ends with punctuation
    if lf_clean and lf_clean[-1] in ".!?":
        lf += 1
    score.linha_fina_score = min(lf, 7)
    score.diagnostics["lf_chars"] = lf_chars
    score.diagnostics["lf_words"] = len(lf_words)

    # 2C. Keyword Strategy (/5)
    kw = 0
    if primary_keyword and word_count > 0:
        kw_count = text_lower.count(primary_keyword)
        density = (kw_count * len(primary_keyword.split())) / word_count
        if 0.01 <= density <= 0.025:
            kw += 2
        elif 0.005 <= density <= 0.03:
            kw += 1
        # LSI (secondary keywords)
        secondary = [t.lower() for t in tags[1:5]]
        lsi_found = sum(1 for s in secondary if s in text_lower)
        if lsi_found >= 2:
            kw += 1
        # Keyword in first paragraph
        first_para_lower = paragraphs[0].lower() if paragraphs else ""
        if primary_keyword in first_para_lower:
            kw += 1
        # Top keyword variations
        if lsi_found >= 3:
            kw += 1
        score.diagnostics["keyword_density"] = round(density, 4) if primary_keyword else 0
    score.keyword_score = min(kw, 5)

    # 2D. Slug (/5) — backend can't control, always 0
    score.slug_score = 0

    # =========================================================================
    # 3. E-E-A-T (20 pts)
    # =========================================================================

    # 3A. Experience (/5)
    exp = 0
    exp_patterns_found = sum(1 for p in EXPERIENCE_PATTERNS if re.search(p, text_lower))
    if exp_patterns_found >= 2:
        exp += 2
    elif exp_patterns_found >= 1:
        exp += 1
    # Specific details: numbers, names, dates
    has_numbers = bool(re.search(r"\b\d+[.,]?\d*\b", conteudo))
    has_named = bool(re.search(r"\b[A-Z][a-záéíóúâêôãõ]+\s+[A-Z][a-záéíóúâêôãõ]+", conteudo))
    has_dates = bool(re.search(r"\b\d{1,2}\s+de\s+\w+|\b\d{4}\b", conteudo))
    details = sum([has_numbers, has_named, has_dates])
    if details >= 2:
        exp += 2
    elif details >= 1:
        exp += 1
    # Original insights (no vague language)
    vague = sum(1 for p in [r"dizem que", r"segundo rumores", r"possivelmente"] if re.search(p, text_lower))
    if vague == 0:
        exp += 1
    score.experience_score = min(exp, 5)

    # 3B. Expertise (/5)
    expt = 0
    # Author byline (unlikely from backend, but check)
    if re.search(r"\bpor\s+[A-Z]", conteudo):
        expt += 1
    # Sources cited
    reporting_found = sum(1 for rv in REPORTING_VERBS if rv in text_lower)
    if reporting_found >= 2:
        expt += 2
    elif reporting_found >= 1:
        expt += 1
    # Expert quotes
    expert_found = sum(1 for et in EXPERT_TITLES if re.search(et, text_lower))
    if expert_found >= 2:
        expt += 2
    elif expert_found >= 1:
        expt += 1
    score.expertise_score = min(expt, 5)

    # 3C. Authority (/5)
    auth = 0
    official_found = sum(1 for pat in OFFICIAL_SOURCES if re.search(pat, conteudo, re.IGNORECASE))
    if official_found >= 2:
        auth += 2
    elif official_found >= 1:
        auth += 1
    # Reporting verbs in context
    verbs_with_name = len(re.findall(r"[A-Z]\w+\s+(disse|afirmou|declarou|informou|explicou|destacou)", conteudo))
    if verbs_with_name >= 2:
        auth += 2
    elif verbs_with_name >= 1:
        auth += 1
    # Institutional references
    if re.search(r"\b(universidade|instituto|fundação|federação)\b", text_lower):
        auth += 1
    score.authority_score = min(auth, 5)

    # 3D. Trust (/5)
    tr = 0
    factual_patterns = sum(1 for p in [r"dados mostram", r"estatísticas indicam", r"segundo pesquisa", r"de acordo com dados"] if re.search(p, text_lower))
    if factual_patterns >= 2:
        tr += 2
    elif factual_patterns >= 1:
        tr += 1
    # Balanced perspective
    balance = sum(1 for p in [r"por outro lado", r"em contrapartida", r"críticos apontam", r"ambos os lados"] if re.search(p, text_lower))
    if balance >= 1:
        tr += 1
    # Transparent sourcing
    named_sources = len(re.findall(r'segundo\s+[A-Z]\w+|[A-Z]\w+\s+disse', conteudo))
    if named_sources >= 1:
        tr += 1
    # No clickbait
    clickbait_found = sum(1 for p in CLICKBAIT_PATTERNS if re.search(p, text_lower))
    if clickbait_found == 0:
        tr += 1
    score.trust_score = min(tr, 5)

    # =========================================================================
    # 4. Technical Excellence (5 pts) — Backend usually 0
    # =========================================================================
    ext_links = len(re.findall(r"https?://[^\s\)]+", conteudo))
    if ext_links >= 1:
        score.external_links_score = min(ext_links + 1, 5)
    score.diagnostics["external_links"] = ext_links

    # =========================================================================
    # 5. AI & SERP Optimization (10 pts)
    # =========================================================================

    # 5A. Featured Snippet (/5)
    fs = 0
    if 40 <= first_para_words <= 60:
        fs += 2 + 1  # direct_answer + concise_answer
    elif 20 <= first_para_words <= 80:
        fs += 1
    if has_lists:
        fs += 1
    # Table check
    if re.search(r"\|.*\|.*\|", conteudo):
        fs += 1
    score.featured_snippet_score = min(fs, 5)

    # 5B. AI Overview (/5)
    ai = 0
    if len(headings) >= 1 and len(paragraphs) >= 3:
        ai += 2
    elif len(paragraphs) >= 3:
        ai += 1
    if has_numbers or has_dates:
        ai += 1
    if avg_sentence_words <= 25:
        ai += 1
    if clickbait_found == 0:
        ai += 1
    score.ai_overview_score = min(ai, 5)

    score.finalize()
    return score


# =============================================================================
# Journalism Quality Metrics
# =============================================================================

@dataclass
class JournalismScore:
    """Journalism quality metrics."""
    bluf_compliant: bool = False          # First para answers WHO/WHAT/WHY
    bluf_word_count: int = 0
    title_word_count: int = 0
    title_char_count: int = 0
    lf_word_count: int = 0
    lf_char_count: int = 0
    has_subtitles: bool = False
    subtitle_count: int = 0
    paragraph_count: int = 0
    avg_paragraph_sentences: float = 0.0
    active_voice_ratio: float = 0.0
    total_score: float = 0.0              # /10

    def compute(self, titulo: str, linha_fina: str, conteudo: str):
        paragraphs = [p.strip() for p in conteudo.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in conteudo.split("\n") if p.strip()]
        first_para = paragraphs[0] if paragraphs else ""
        first_words = re.findall(r"\b\w+\b", first_para)
        self.bluf_word_count = len(first_words)
        self.bluf_compliant = 30 <= self.bluf_word_count <= 80

        self.title_word_count = len(titulo.split())
        self.title_char_count = len(titulo)
        self.lf_word_count = len(linha_fina.split())
        self.lf_char_count = len(linha_fina)

        headings = re.findall(r"^#{2,3}\s+.+", conteudo, re.MULTILINE)
        self.has_subtitles = len(headings) > 0
        self.subtitle_count = len(headings)
        self.paragraph_count = len(paragraphs)

        all_sentences = re.split(r"[.!?]+", conteudo)
        all_sentences = [s.strip() for s in all_sentences if len(s.strip()) > 3]
        if paragraphs:
            self.avg_paragraph_sentences = len(all_sentences) / len(paragraphs)

        passive = _passive_voice_ratio(conteudo)
        self.active_voice_ratio = round(1.0 - passive, 3)

        # Compute score /10
        pts = 0
        if self.bluf_compliant:
            pts += 2
        if 7 <= self.title_word_count <= 12:
            pts += 1
        if 50 <= self.title_char_count <= 65:
            pts += 1
        if 18 <= self.lf_word_count <= 28:
            pts += 1
        if self.has_subtitles:
            pts += 1
        if self.active_voice_ratio >= 0.80:
            pts += 2
        elif self.active_voice_ratio >= 0.70:
            pts += 1
        if self.avg_paragraph_sentences <= 4.5:
            pts += 1
        if _transition_ratio(conteudo) >= 0.20:
            pts += 1
        self.total_score = min(pts, 10)


# =============================================================================
# Test Case Definitions
# =============================================================================

SYNTHETIC_CASES = [
    # --- Category coverage ---
    {
        "id": "SYN-POL-01",
        "title": "Governo anuncia novo pacote de medidas econômicas",
        "content": (
            "O governo federal anunciou nesta terça-feira um novo pacote de medidas econômicas "
            "que prevê a redução de impostos para pequenas empresas e o aumento do salário mínimo. "
            "O ministro da Fazenda, Fernando Haddad, afirmou que as medidas devem gerar 500 mil "
            "novos empregos até o final de 2026. 'Este é o maior programa de incentivo fiscal "
            "da última década', declarou Haddad em coletiva de imprensa no Palácio do Planalto. "
            "O pacote também inclui linhas de crédito com juros subsidiados para microempreendedores "
            "individuais e programas de qualificação profissional em parceria com o SENAI. "
            "Economistas do mercado reagiram com cautela, apontando que o impacto fiscal das medidas "
            "pode chegar a R$ 45 bilhões nos próximos dois anos. O Banco Central informou que "
            "acompanha a situação e que a política monetária será ajustada conforme necessário."
        ),
        "category": "politica",
        "tags": ["pacote econômico", "governo", "impostos", "salário mínimo", "Haddad"],
        "tipo_materia": "destaque",
        "tom": "formal",
    },
    {
        "id": "SYN-ESP-01",
        "title": "Flamengo vence Palmeiras por 3 a 1 no Maracanã",
        "content": (
            "O Flamengo venceu o Palmeiras por 3 a 1 na noite deste sábado no Maracanã, em jogo "
            "válido pela 12ª rodada do Campeonato Brasileiro 2026. Os gols rubro-negros foram "
            "marcados por Pedro (aos 15 e 67 minutos) e Gerson (aos 42 do segundo tempo). "
            "Raphael Veiga descontou para o Palmeiras aos 30 minutos do segundo tempo, de pênalti. "
            "Com o resultado, o Flamengo assume a liderança com 28 pontos, dois a mais que o "
            "Botafogo. O técnico Filipe Luís elogiou a atuação do time: 'Foi nossa melhor "
            "partida na temporada'. O próximo compromisso do Flamengo é contra o Athletico-PR, "
            "quarta-feira, na Arena da Baixada."
        ),
        "category": "esportes",
        "tags": ["Flamengo", "Palmeiras", "Brasileirão", "Maracanã", "Pedro"],
        "tipo_materia": "destaque",
        "tom": "informal",
    },
    {
        "id": "SYN-ECO-01",
        "title": "Inflação acumula 5,2% em 12 meses, aponta IBGE",
        "content": (
            "A inflação medida pelo IPCA acumulou alta de 5,2% nos últimos 12 meses, segundo dados "
            "divulgados nesta sexta-feira pelo IBGE. No mês de janeiro, o índice subiu 0,65%, acima "
            "da expectativa do mercado de 0,55%. O grupo Alimentação e Bebidas foi o principal "
            "vilão, com alta de 1,8% no mês, puxado pelo preço da carne bovina (+4,2%) e do "
            "tomate (+12,5%). Transportes subiram 0,9% com o reajuste dos combustíveis. "
            "O Banco Central já sinalizou que pode elevar a taxa Selic na próxima reunião do Copom, "
            "marcada para março. Analistas do Itaú projetam que os juros podem chegar a 14,25% ao "
            "ano até junho. 'O cenário inflacionário é preocupante', avaliou o economista-chefe do "
            "banco, Mario Mesquita."
        ),
        "category": "economia",
        "tags": ["inflação", "IPCA", "IBGE", "Banco Central", "Selic"],
        "tipo_materia": "analise",
        "tom": "formal",
    },
    {
        "id": "SYN-ENT-01",
        "title": "Netflix confirma segunda temporada de série brasileira",
        "content": (
            "A Netflix confirmou nesta quinta-feira a produção da segunda temporada da série "
            "brasileira 'Cidade de Ferro', que estreou em novembro de 2025 e alcançou o top 10 "
            "global da plataforma. A produção, ambientada em uma cidade fictícia de Minas Gerais, "
            "conta com Wagner Moura no papel principal. 'Estamos muito felizes com a repercussão "
            "internacional', disse a diretora Anna Muylaert. As gravações devem começar no segundo "
            "semestre de 2026 em locações no interior de Minas Gerais e Rio de Janeiro. "
            "A série acumulou 45 milhões de horas assistidas nas primeiras quatro semanas."
        ),
        "category": "entretenimento",
        "tags": ["Netflix", "Cidade de Ferro", "Wagner Moura", "série brasileira"],
        "tipo_materia": "destaque",
        "tom": "informal",
    },
    {
        "id": "SYN-GER-01",
        "title": "São Paulo registra maior temperatura do ano nesta quarta",
        "content": (
            "A cidade de São Paulo registrou a maior temperatura do ano nesta quarta-feira, com "
            "os termômetros marcando 38,5°C na estação do Mirante de Santana, zona norte. "
            "O recorde anterior era de 37,8°C, registrado em janeiro. O Inmet emitiu alerta "
            "laranja para toda a Grande São Paulo, com previsão de calor intenso até sexta-feira. "
            "A Defesa Civil recomendou hidratação constante e evitar exposição ao sol entre 10h e 16h. "
            "Pelo menos 12 pessoas foram atendidas em hospitais da rede municipal com sintomas "
            "de desidratação e insolação."
        ),
        "category": "geral",
        "tags": ["São Paulo", "temperatura", "calor", "Inmet", "Defesa Civil"],
        "tipo_materia": "destaque",
        "tom": "formal",
    },

    # --- Edge cases ---
    {
        "id": "SYN-SHORT-01",
        "title": "Preço do dólar sobe",
        "content": "O dólar comercial subiu 1,2% e fechou cotado a R$ 6,15 nesta segunda-feira.",
        "category": "economia",
        "tags": ["dólar", "câmbio"],
        "tipo_materia": "nota",
        "tom": "formal",
    },
    {
        "id": "SYN-LONG-01",
        "title": "Reforma tributária: tudo o que você precisa saber sobre as mudanças",
        "content": (
            "A reforma tributária aprovada pelo Congresso Nacional em dezembro de 2025 representa "
            "a maior mudança no sistema de impostos brasileiro desde a Constituição de 1988. "
            "O texto substitui cinco tributos (PIS, Cofins, IPI, ICMS e ISS) por dois novos "
            "impostos: o IBS (Imposto sobre Bens e Serviços) e a CBS (Contribuição sobre Bens "
            "e Serviços). A alíquota-padrão combinada será de 26,5%, segundo estimativas do "
            "Ministério da Fazenda, podendo variar conforme o setor. Setores como saúde, educação "
            "e transporte público terão alíquota reduzida de 40% sobre a alíquota-padrão. "
            "A cesta básica nacional terá isenção total de impostos, beneficiando as famílias de "
            "menor renda. A transição será gradual: a CBS começa a ser cobrada em 2026 com "
            "alíquota-teste de 0,9%, e o IBS em 2029. A transição completa está prevista para "
            "2033. Estados e municípios terão compensação automática por eventuais perdas de "
            "arrecadação durante o período de transição. O Comitê Gestor do IBS, com "
            "representantes de todos os entes federativos, será responsável pela administração "
            "do imposto estadual/municipal. Críticos apontam que a alíquota de 26,5% é uma das "
            "mais altas do mundo para impostos sobre consumo. O economista Bernard Appy, "
            "secretário extraordinário da reforma tributária, rebateu: 'A alíquota reflete a "
            "carga tributária atual, não há aumento real de impostos'. A Confederação Nacional "
            "da Indústria (CNI) apoiou a reforma, enquanto o setor de serviços expressou "
            "preocupação com possível aumento de carga. A Febraban estimou que a simplificação "
            "pode reduzir em 60% os custos de compliance tributário. Para o consumidor, a "
            "principal mudança visível será a transparência: cada nota fiscal mostrará exatamente "
            "quanto de imposto foi pago. Especialistas recomendam que empresas comecem a se "
            "adaptar aos novos sistemas desde já, pois a complexidade da transição exigirá "
            "investimentos em tecnologia e treinamento."
        ),
        "category": "economia",
        "tags": ["reforma tributária", "IBS", "CBS", "impostos", "Congresso", "Fazenda"],
        "tipo_materia": "reportagem",
        "tom": "formal",
    },
    {
        "id": "SYN-NOTAGS-01",
        "title": "Acidente na BR-101 deixa três feridos",
        "content": (
            "Um acidente envolvendo dois caminhões e um carro de passeio na BR-101, na altura do "
            "km 245, em Itajaí (SC), deixou três pessoas feridas na manhã desta terça-feira. "
            "Segundo a Polícia Rodoviária Federal, o motorista do carro perdeu o controle ao "
            "tentar ultrapassar um dos caminhões. Os feridos foram socorridos pelo SAMU e levados "
            "ao Hospital Marieta Konder Bornhausen. Nenhuma vítima corre risco de morte. A pista "
            "ficou interditada por duas horas para remoção dos veículos."
        ),
        "category": "geral",
        "tags": [],
        "tipo_materia": "destaque",
        "tom": "formal",
    },
    {
        "id": "SYN-SENSITIVE-01",
        "title": "Polícia prende suspeito de abuso sexual contra menor",
        "content": (
            "A Polícia Civil do Rio de Janeiro prendeu nesta quarta-feira um homem de 42 anos "
            "suspeito de abuso sexual contra uma criança de 8 anos no bairro de Campo Grande, "
            "zona oeste da capital. Segundo a delegada responsável pelo caso, o suspeito era "
            "vizinho da família da vítima. A prisão foi realizada após denúncia da mãe da criança "
            "ao Conselho Tutelar. O caso está sendo investigado pela Delegacia da Criança e do "
            "Adolescente (DCAV)."
        ),
        "category": "geral",
        "tags": ["polícia", "Rio de Janeiro"],
        "tipo_materia": "destaque",
        "tom": "formal",
    },
    {
        "id": "SYN-OPINION-01",
        "title": "Por que o Brasil precisa investir em energia solar",
        "content": (
            "O Brasil tem um dos maiores potenciais de energia solar do mundo, com incidência "
            "solar média de 5,5 kWh/m² por dia. Apesar disso, a matriz energética solar "
            "representa apenas 4,5% da capacidade instalada do país, segundo dados da ANEEL de "
            "2025. O investimento em energia fotovoltaica poderia reduzir a dependência de "
            "hidrelétricas, especialmente vulneráveis a secas prolongadas como a de 2024. "
            "A geração distribuída cresceu 180% entre 2023 e 2025, com mais de 2 milhões de "
            "unidades consumidoras gerando sua própria energia. Programas de financiamento "
            "subsidiado, como o linha verde do BNDES, podem acelerar essa transição. "
            "Especialistas da USP estimam que o Brasil pode alcançar 30% de energia solar "
            "na matriz até 2035, criando 1,5 milhão de empregos diretos e indiretos."
        ),
        "category": "economia",
        "tags": ["energia solar", "ANEEL", "Brasil", "fotovoltaica", "BNDES"],
        "tipo_materia": "analise",
        "tom": "formal",
    },
]


# =============================================================================
# Pipeline Runner
# =============================================================================

async def run_pipeline(test_case: dict) -> dict:
    """Run the full 3-phase pipeline on a test case."""
    from services.llm_service import get_llm_service
    from services.fact_check_service import get_fact_check_service, is_fact_check_enabled
    from functions.generation_api import _detect_sensitive_topics

    llm = get_llm_service()
    cat = test_case["category"]
    tags = test_case.get("tags", [])
    tom = test_case.get("tom", "formal")
    tipo = test_case.get("tipo_materia", "destaque")

    result = {
        "id": test_case["id"],
        "title": test_case["title"],
        "category": cat,
        "source_chars": len(test_case["content"]),
        "phases": {},
        "errors": [],
        "seo": None,
        "journalism": None,
        "verification": None,
    }

    # Sensitive topic detection
    sensitive = _detect_sensitive_topics(test_case["content"])
    result["sensitive_topics"] = sensitive

    # Phase 1: Enrichment
    enrichment = None
    enrichment_context = None
    enrichment_key_facts = None
    verified_chars = len(test_case["content"].strip())

    if is_fact_check_enabled():
        try:
            t0 = time.time()
            fc = get_fact_check_service()
            enrichment = await fc.enrich_context(
                texto_base=test_case["content"],
                titulo_fonte=test_case["title"],
                tags=tags,
            )
            ms = int((time.time() - t0) * 1000)
            if enrichment.success:
                enrichment_context = enrichment.context_text
                enrichment_key_facts = enrichment.key_facts if enrichment.key_facts else None
                verified_chars = enrichment.verified_chars
            result["phases"]["enrichment"] = {
                "success": enrichment.success,
                "key_facts": len(enrichment.key_facts),
                "urls": len(enrichment.source_urls),
                "verified_chars": verified_chars,
                "ms": ms,
            }
        except Exception as e:
            result["phases"]["enrichment"] = {"success": False, "error": str(e)[:200]}
            result["errors"].append(f"Enrichment: {e}")

    # Phase 2: Generation
    try:
        t0 = time.time()
        generated = await llm.generate_article(
            texto_base=test_case["content"],
            tom=tom,
            tipo_materia=tipo,
            categoria=cat,
            tags=tags,
            enrichment_context=enrichment_context,
            enrichment_key_facts=enrichment_key_facts,
            verified_chars=verified_chars,
            sensitive_instructions=sensitive if sensitive else None,
        )
        ms = int((time.time() - t0) * 1000)
        result["phases"]["generation"] = {"success": True, "ms": ms}
        result["generated"] = generated
    except Exception as e:
        result["phases"]["generation"] = {"success": False, "error": str(e)[:200]}
        result["errors"].append(f"Generation: {e}")
        return result

    # Phase 3: Verification
    if is_fact_check_enabled() and generated:
        try:
            t0 = time.time()
            fc = get_fact_check_service()
            verification = await fc.verify_article(
                texto_base=test_case["content"],
                generated_article=generated.get("conteudo", ""),
                enrichment=enrichment,
            )
            ms = int((time.time() - t0) * 1000)
            result["verification"] = {
                "confidence": verification.confidence_score,
                "risk": verification.risk_level,
                "expansion": verification.expansion_ratio,
                "total_claims": verification.total_claims,
                "grounded": verification.grounded_claims,
                "fabricated": verification.fabricated_claims,
                "unverifiable": verification.unverifiable_claims,
                "human_review": verification.requires_human_review,
                "review_reasons": verification.review_reasons,
                "claims": [
                    {"text": c.text[:120], "verdict": c.verdict}
                    for c in verification.claims
                ],
                "truncation": verification.truncation,
                "cove_applied": verification.cove_applied,
                "cove_reclassified": verification.cove_reclassified,
                "ms": ms,
            }
        except Exception as e:
            result["errors"].append(f"Verification: {e}")

    # Compute SEO score
    if generated:
        titulo = generated.get("titulo", "")
        lf = generated.get("linha_fina", "")
        conteudo = generated.get("conteudo", "")
        gen_tags = generated.get("tags_sugeridas", tags)
        result["seo"] = asdict(compute_seo_score(titulo, lf, conteudo, gen_tags or tags, tipo))

        j = JournalismScore()
        j.compute(titulo, lf, conteudo)
        result["journalism"] = asdict(j)

    return result


# =============================================================================
# Report Printer
# =============================================================================

def print_case_report(r: dict, idx: int):
    """Print detailed report for a single test case."""
    gen = r.get("generated", {})
    seo = r.get("seo", {})
    journ = r.get("journalism", {})
    verif = r.get("verification", {})

    print(f"\n{'='*90}")
    print(f"  #{idx+1} [{r['category'].upper()}] {r['title'][:70]}")
    print(f"  Source: {r['source_chars']} chars | Type: {r.get('phases',{}).get('generation',{}).get('ms','?')}ms generation")
    if r.get("sensitive_topics"):
        print(f"  *** SENSITIVE TOPICS DETECTED: {len(r['sensitive_topics'])} ***")
    print(f"{'='*90}")

    if not gen:
        print("  GENERATION FAILED:", r.get("errors"))
        return

    titulo = gen.get("titulo", "")
    lf = gen.get("linha_fina", "")
    conteudo = gen.get("conteudo", "")

    print(f"\n  TITULO: {titulo}")
    print(f"    {journ.get('title_char_count',0)} chars | {journ.get('title_word_count',0)} words")
    print(f"  LINHA FINA: {lf}")
    print(f"    {journ.get('lf_char_count',0)} chars | {journ.get('lf_word_count',0)} words")

    # SEO Breakdown
    norm = seo.get("normalized", 0) if seo else 0
    raw = seo.get("raw_total", 0) if seo else 0
    grade = "EXCELENTE" if norm >= 80 else "BOM" if norm >= 60 else "REGULAR" if norm >= 40 else "CRITICO"
    diag = seo.get("diagnostics", {}) if seo else {}

    print(f"\n  SEO SCORE: {norm}/100 ({raw}/90 raw) [{grade}]")
    cq = (seo or {}).get("word_count_score", 0) + (seo or {}).get("structure_score", 0) + (seo or {}).get("readability_score", 0)
    op = (seo or {}).get("title_score", 0) + (seo or {}).get("linha_fina_score", 0) + (seo or {}).get("keyword_score", 0)
    eeat = (seo or {}).get("experience_score", 0) + (seo or {}).get("expertise_score", 0) + (seo or {}).get("authority_score", 0) + (seo or {}).get("trust_score", 0)
    serp = (seo or {}).get("featured_snippet_score", 0) + (seo or {}).get("ai_overview_score", 0)
    print(f"    Content Quality: {cq}/30  (words={diag.get('word_count',0)}, headings={diag.get('headings',0)}, flesch={diag.get('flesch',0)})")
    print(f"    On-Page:         {op}/20  (title={seo.get('title_score',0)}/8, lf={seo.get('linha_fina_score',0)}/7, kw={seo.get('keyword_score',0)}/5)")
    print(f"    E-E-A-T:         {eeat}/20 (exp={seo.get('experience_score',0)} expt={seo.get('expertise_score',0)} auth={seo.get('authority_score',0)} trust={seo.get('trust_score',0)})")
    print(f"    AI & SERP:       {serp}/10 (snippet={seo.get('featured_snippet_score',0)}/5, ai={seo.get('ai_overview_score',0)}/5)")
    print(f"    Readability:     flesch={diag.get('flesch',0)} | sent_len={diag.get('avg_sentence_words',0)} | passive={diag.get('passive_ratio',0)} | transitions={diag.get('transition_ratio',0)}")

    # Journalism
    print(f"\n  JOURNALISM: {journ.get('total_score',0)}/10")
    print(f"    BLUF: {'OK' if journ.get('bluf_compliant') else 'FAIL'} ({journ.get('bluf_word_count',0)} words)")
    print(f"    Active voice: {journ.get('active_voice_ratio',0)*100:.0f}% | Subtitles: {journ.get('subtitle_count',0)} | Paragraphs: {journ.get('paragraph_count',0)}")

    # Verification
    if verif:
        risk_map = {"low": "LOW", "medium": "MEDIUM", "high": "HIGH", "critical": "CRITICAL"}
        print(f"\n  VERIFICATION: confidence={verif.get('confidence',0):.3f} | risk={risk_map.get(verif.get('risk','?'),'?')}")
        print(f"    Claims: {verif.get('total_claims',0)} total | {verif.get('grounded',0)} grounded | {verif.get('fabricated',0)} fabricated | {verif.get('unverifiable',0)} unverifiable")
        print(f"    Expansion: {verif.get('expansion',0):.1f}x | CoVe: applied={verif.get('cove_applied',False)}, reclassified={verif.get('cove_reclassified',0)}")
        if verif.get("human_review"):
            print(f"    HUMAN REVIEW: {', '.join(verif.get('review_reasons',[]))}")
        fabricated = [c for c in verif.get("claims", []) if c["verdict"] == "fabricated"]
        if fabricated:
            print(f"    FABRICATED CLAIMS:")
            for c in fabricated:
                print(f"      -> {c['text']}")

    # Content preview
    print(f"\n  CONTENT PREVIEW (first 300 chars):")
    print(f"    {conteudo[:300]}...")


def print_summary(results: list, elapsed_s: float):
    """Print aggregate summary."""
    total = len(results)
    success = sum(1 for r in results if r.get("generated"))
    seo_scores = [r["seo"]["normalized"] for r in results if r.get("seo")]
    journ_scores = [r["journalism"]["total_score"] for r in results if r.get("journalism")]
    conf_scores = [r["verification"]["confidence"] for r in results if r.get("verification")]
    fab_counts = [r["verification"]["fabricated"] for r in results if r.get("verification")]

    print(f"\n\n{'#'*90}")
    print(f"  AUDIT SUMMARY — {total} test cases, {success} generated, {elapsed_s:.0f}s total")
    print(f"{'#'*90}")

    if seo_scores:
        avg_seo = sum(seo_scores) / len(seo_scores)
        min_seo = min(seo_scores)
        max_seo = max(seo_scores)
        std_seo = (sum((s - avg_seo) ** 2 for s in seo_scores) / len(seo_scores)) ** 0.5
        print(f"\n  SEO SCORES (n={len(seo_scores)}):")
        print(f"    Average: {avg_seo:.1f}/100 | Min: {min_seo:.1f} | Max: {max_seo:.1f} | StdDev: {std_seo:.1f}")
        # Histogram
        buckets = {"80-100 EXCELENTE": 0, "60-79 BOM": 0, "40-59 REGULAR": 0, "0-39 CRITICO": 0}
        for s in seo_scores:
            if s >= 80:
                buckets["80-100 EXCELENTE"] += 1
            elif s >= 60:
                buckets["60-79 BOM"] += 1
            elif s >= 40:
                buckets["40-59 REGULAR"] += 1
            else:
                buckets["0-39 CRITICO"] += 1
        for label, count in buckets.items():
            bar = "#" * count + "." * (total - count)
            print(f"    {label:20s} {bar} {count}/{total}")

    if journ_scores:
        avg_j = sum(journ_scores) / len(journ_scores)
        print(f"\n  JOURNALISM SCORES (n={len(journ_scores)}):")
        print(f"    Average: {avg_j:.1f}/10 | Min: {min(journ_scores):.1f} | Max: {max(journ_scores):.1f}")

    if conf_scores:
        avg_c = sum(conf_scores) / len(conf_scores)
        total_fab = sum(fab_counts)
        total_claims = sum(r["verification"]["total_claims"] for r in results if r.get("verification"))
        fab_rate = total_fab / max(total_claims, 1)
        print(f"\n  ANTI-HALLUCINATION (n={len(conf_scores)}):")
        print(f"    Avg confidence: {avg_c:.3f} | Min: {min(conf_scores):.3f} | Max: {max(conf_scores):.3f}")
        print(f"    Total claims: {total_claims} | Fabricated: {total_fab} ({fab_rate*100:.1f}%)")
        risk_counts = {}
        for r in results:
            if r.get("verification"):
                risk = r["verification"]["risk"]
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
        print(f"    Risk distribution: {risk_counts}")

    # Sensitive topic handling
    sensitive_cases = [r for r in results if r.get("sensitive_topics")]
    if sensitive_cases:
        print(f"\n  SENSITIVE TOPICS: {len(sensitive_cases)} cases detected")
        for r in sensitive_cases:
            print(f"    [{r['id']}] {len(r['sensitive_topics'])} topics")

    # Per-category breakdown
    categories = sorted(set(r["category"] for r in results))
    print(f"\n  PER-CATEGORY BREAKDOWN:")
    print(f"    {'Category':<16} {'SEO':>6} {'Journ':>6} {'Conf':>6} {'Fab':>4}")
    print(f"    {'-'*40}")
    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat]
        cat_seo = [r["seo"]["normalized"] for r in cat_results if r.get("seo")]
        cat_j = [r["journalism"]["total_score"] for r in cat_results if r.get("journalism")]
        cat_c = [r["verification"]["confidence"] for r in cat_results if r.get("verification")]
        cat_f = sum(r["verification"]["fabricated"] for r in cat_results if r.get("verification"))
        avg_s = sum(cat_seo) / len(cat_seo) if cat_seo else 0
        avg_j = sum(cat_j) / len(cat_j) if cat_j else 0
        avg_c = sum(cat_c) / len(cat_c) if cat_c else 0
        print(f"    {cat:<16} {avg_s:>5.1f} {avg_j:>5.1f} {avg_c:>5.3f} {cat_f:>4}")

    # Consistency check (if repeated runs)
    ids = [r["id"] for r in results]
    dupes = set(i for i in ids if ids.count(i) > 1)
    if dupes:
        print(f"\n  CONSISTENCY CHECK (repeated runs):")
        for dup_id in sorted(dupes):
            runs = [r for r in results if r["id"] == dup_id]
            seos = [r["seo"]["normalized"] for r in runs if r.get("seo")]
            confs = [r["verification"]["confidence"] for r in runs if r.get("verification")]
            if seos:
                seo_std = (sum((s - sum(seos)/len(seos))**2 for s in seos) / len(seos)) ** 0.5
                print(f"    {dup_id}: SEO={[f'{s:.1f}' for s in seos]} (std={seo_std:.1f})", end="")
            if confs:
                conf_std = (sum((c - sum(confs)/len(confs))**2 for c in confs) / len(confs)) ** 0.5
                print(f" | Conf={[f'{c:.3f}' for c in confs]} (std={conf_std:.3f})", end="")
            print()


# =============================================================================
# Main
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="TMC Article Generation Audit v5")
    parser.add_argument("--synthetic", action="store_true", help="Use only synthetic test cases")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat each case N times (consistency)")
    parser.add_argument("--category", type=str, help="Filter to single category")
    parser.add_argument("--max-cases", type=int, default=20, help="Max test cases to run")
    args = parser.parse_args()

    print("=" * 90)
    print("  TMC ARTICLE GENERATION — COMPREHENSIVE QUALITY AUDIT v5")
    print(f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode: {'Synthetic only' if args.synthetic else 'DB + Synthetic'} | Repeat: {args.repeat}x")
    print("=" * 90)

    test_cases = []

    # Synthetic cases
    synth = SYNTHETIC_CASES
    if args.category:
        synth = [c for c in synth if c["category"] == args.category]
    test_cases.extend(synth)
    print(f"\n  Loaded {len(synth)} synthetic test cases")

    # DB cases (unless --synthetic)
    if not args.synthetic:
        try:
            print("\n  Fetching articles from database...")
            from services.database import DatabaseService
            db = DatabaseService()
            categories = [args.category] if args.category else ["politica", "esportes", "economia", "entretenimento", "geral"]
            for cat in categories:
                try:
                    articles, _, _ = db.get_articles_with_urgency(page=1, limit=3, category=cat)
                    for article in articles[:2]:
                        content = article.content or article.preview or ""
                        if len(content.strip()) > 80:
                            atags = article.tags if hasattr(article, "tags") and article.tags else []
                            if isinstance(atags, str):
                                try:
                                    atags = json.loads(atags)
                                except Exception:
                                    atags = []
                            test_cases.append({
                                "id": f"DB-{cat[:3].upper()}-{str(article.id)[:8]}",
                                "title": article.title,
                                "content": content,
                                "category": cat,
                                "tags": atags[:6],
                                "tipo_materia": "destaque",
                                "tom": "formal" if cat in ("politica", "economia") else "informal",
                            })
                            print(f"    [{cat}] {article.title[:70]}... ({len(content)} chars)")
                except Exception as e:
                    print(f"    [{cat}] Error: {e}")
        except Exception as e:
            print(f"  DB fetch failed: {e} — continuing with synthetic only")

    # Apply limits
    test_cases = test_cases[:args.max_cases]
    print(f"\n  Total test cases: {len(test_cases)} x {args.repeat} repeats = {len(test_cases) * args.repeat} runs")

    # Expand for repeats
    all_cases = []
    for rep in range(args.repeat):
        for tc in test_cases:
            case = dict(tc)
            if args.repeat > 1:
                case["id"] = tc["id"]  # Keep same ID for consistency check
            all_cases.append(case)

    # Run pipeline
    print(f"\n  Running pipeline...\n")
    all_results = []
    t_start = time.time()

    for i, tc in enumerate(all_cases):
        label = f"[{i+1}/{len(all_cases)}] {tc['id']}: {tc['title'][:50]}..."
        print(f"  {label}", end="", flush=True)
        try:
            result = await run_pipeline(tc)
            all_results.append(result)
            seo_n = result.get("seo", {}).get("normalized", 0) if result.get("seo") else 0
            conf = result.get("verification", {}).get("confidence", 0) if result.get("verification") else 0
            print(f" -> SEO={seo_n:.0f} Conf={conf:.3f}")
        except Exception as e:
            print(f" -> ERROR: {e}")
            all_results.append({"id": tc["id"], "title": tc["title"], "category": tc["category"],
                                "source_chars": len(tc["content"]), "phases": {}, "errors": [str(e)]})

    elapsed = time.time() - t_start

    # Detailed reports
    print(f"\n\n{'='*90}")
    print("  DETAILED REPORTS")
    print(f"{'='*90}")
    for i, r in enumerate(all_results):
        print_case_report(r, i)

    # Summary
    print_summary(all_results, elapsed)

    # Save JSON
    output_path = Path(__file__).parent / f"audit_v5_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    serializable = []
    for r in all_results:
        s = dict(r)
        if "generated" in s:
            s.pop("generated", None)  # Don't save full content to reduce file size
        serializable.append(s)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": {"synthetic_only": args.synthetic, "repeat": args.repeat, "category": args.category},
            "summary": {
                "total_runs": len(all_results),
                "successful": sum(1 for r in all_results if r.get("seo")),
                "avg_seo": round(sum(r["seo"]["normalized"] for r in all_results if r.get("seo")) / max(sum(1 for r in all_results if r.get("seo")), 1), 1),
                "avg_confidence": round(sum(r["verification"]["confidence"] for r in all_results if r.get("verification")) / max(sum(1 for r in all_results if r.get("verification")), 1), 3),
                "total_fabricated": sum(r["verification"]["fabricated"] for r in all_results if r.get("verification")),
                "elapsed_seconds": round(elapsed, 1),
            },
            "results": serializable,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n  Results saved to: {output_path}")
    print(f"  Total time: {elapsed:.0f}s ({elapsed/len(all_results):.1f}s per article)")


if __name__ == "__main__":
    asyncio.run(main())
