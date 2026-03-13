"""
Brazilian media credibility database for Article Safety Index (ASI) scoring.

Provides tier-based credibility weights for Brazilian and international
news outlets, fact-checkers, and government sources.
"""

import threading
from typing import Optional
from urllib.parse import urlparse


# === Tier 0: Fact-checkers (highest trust) ===
# === Tier 1: International wire services & major Brazilian outlets ===
# === Tier 2: Established regional/specialized outlets ===
# === Tier 3: Government/institutional ===
# === Tier 4: Unknown/unclassified (default) ===

BRAZILIAN_MEDIA_TIERS = {
    # Tier 0 — Fact-checkers
    "aosfatos.org":              {"tier": 0, "name": "Aos Fatos",          "type": "factcheck"},
    "lupa.uol.com.br":          {"tier": 0, "name": "Agencia Lupa",       "type": "factcheck"},
    "checamos.afp.com":          {"tier": 0, "name": "AFP Checamos",       "type": "factcheck"},
    "boatos.org":                {"tier": 0, "name": "Boatos.org",         "type": "factcheck"},
    "projetocomprova.com.br":    {"tier": 0, "name": "Comprova",           "type": "factcheck"},
    "e-farsas.com":              {"tier": 0, "name": "E-Farsas",           "type": "factcheck"},

    # Tier 1 — Wire services & major outlets
    "reuters.com":               {"tier": 1, "name": "Reuters",            "type": "wire"},
    "apnews.com":                {"tier": 1, "name": "Associated Press",   "type": "wire"},
    "afp.com":                   {"tier": 1, "name": "AFP",                "type": "wire"},
    "folha.uol.com.br":         {"tier": 1, "name": "Folha de S.Paulo",   "type": "print"},
    "oglobo.globo.com":         {"tier": 1, "name": "O Globo",            "type": "print"},
    "estadao.com.br":           {"tier": 1, "name": "Estadao",            "type": "print"},
    "g1.globo.com":             {"tier": 1, "name": "G1",                 "type": "digital"},
    "valor.globo.com":          {"tier": 1, "name": "Valor Economico",    "type": "financial"},
    "agenciabrasil.ebc.com.br": {"tier": 1, "name": "Agencia Brasil",     "type": "government"},
    "bbc.com":                   {"tier": 1, "name": "BBC",                "type": "international"},
    "cnnbrasil.com.br":         {"tier": 1, "name": "CNN Brasil",         "type": "tv"},
    "noticias.uol.com.br":      {"tier": 1, "name": "UOL Noticias",      "type": "digital"},

    # Tier 2 — Established regional/specialized
    "poder360.com.br":           {"tier": 2, "name": "Poder360",           "type": "political"},
    "nexojornal.com.br":         {"tier": 2, "name": "Nexo Jornal",        "type": "analytical"},
    "gazetadopovo.com.br":       {"tier": 2, "name": "Gazeta do Povo",     "type": "regional"},
    "correiobraziliense.com.br": {"tier": 2, "name": "Correio Braziliense","type": "regional"},
    "metropoles.com":            {"tier": 2, "name": "Metropoles",         "type": "digital"},
    "infomoney.com.br":          {"tier": 2, "name": "InfoMoney",          "type": "financial"},
    "gauchazh.clicrbs.com.br":   {"tier": 2, "name": "GauchazH",          "type": "regional"},
    "brazilian.report":          {"tier": 2, "name": "The Brazilian Report","type": "english"},
    "cartacapital.com.br":       {"tier": 2, "name": "Carta Capital",      "type": "magazine"},
    "revistaoeste.com":          {"tier": 2, "name": "Revista Oeste",      "type": "magazine"},

    # Tier 3 — Government/institutional
    "gov.br":                    {"tier": 3, "name": "Portal do Governo",   "type": "government"},
    "planalto.gov.br":           {"tier": 3, "name": "Planalto",           "type": "government"},
    "senado.leg.br":             {"tier": 3, "name": "Senado Federal",     "type": "government"},
    "camara.leg.br":             {"tier": 3, "name": "Camara dos Deputados","type": "government"},
    "stf.jus.br":                {"tier": 3, "name": "STF",                "type": "judiciary"},
    "ibge.gov.br":               {"tier": 3, "name": "IBGE",               "type": "statistics"},
    "bcb.gov.br":                {"tier": 3, "name": "Banco Central",      "type": "financial"},
}

TIER_CREDIBILITY_WEIGHTS = {
    0: 1.00,   # Fact-checkers
    1: 0.95,   # Wire services & major outlets
    2: 0.80,   # Established regional/specialized
    3: 0.90,   # Government/institutional
    4: 0.50,   # Unknown/unclassified
}

TIER_NAMES = {
    0: "Tier 0 - Fact-checker",
    1: "Tier 1 - Agencia internacional / grande veiculo",
    2: "Tier 2 - Veiculo regional / especializado",
    3: "Tier 3 - Governo / institucional",
    4: "Tier 4 - Desconhecido",
}


class BrazilianMediaCredibilityDB:
    """Lookup credibility tier for Brazilian and international media domains."""

    def get_source_credibility(self, domain_or_url: str) -> dict:
        """
        Get credibility info for a domain or URL.

        Uses substring matching against known domains.
        .gov.br domains default to tier 3 (government).

        Returns:
            dict with tier, name, type, weight, tier_name
        """
        # Extract domain from URL if needed
        domain = domain_or_url.lower().strip()
        if "://" in domain:
            try:
                domain = urlparse(domain).netloc
            except Exception:
                pass
        domain = domain.lstrip("www.")

        # Exact match first
        if domain in BRAZILIAN_MEDIA_TIERS:
            info = BRAZILIAN_MEDIA_TIERS[domain]
            return {
                "tier": info["tier"],
                "name": info["name"],
                "type": info["type"],
                "weight": TIER_CREDIBILITY_WEIGHTS[info["tier"]],
                "tier_name": TIER_NAMES[info["tier"]],
            }

        # Substring match (e.g. "www1.folha.uol.com.br" matches "folha.uol.com.br")
        for known_domain, info in BRAZILIAN_MEDIA_TIERS.items():
            if known_domain in domain or domain.endswith("." + known_domain):
                return {
                    "tier": info["tier"],
                    "name": info["name"],
                    "type": info["type"],
                    "weight": TIER_CREDIBILITY_WEIGHTS[info["tier"]],
                    "tier_name": TIER_NAMES[info["tier"]],
                }

        # Special case: .gov.br domains
        if ".gov.br" in domain or ".jus.br" in domain or ".leg.br" in domain:
            return {
                "tier": 3,
                "name": domain,
                "type": "government",
                "weight": TIER_CREDIBILITY_WEIGHTS[3],
                "tier_name": TIER_NAMES[3],
            }

        # Unknown domain
        return {
            "tier": 4,
            "name": domain,
            "type": "unknown",
            "weight": TIER_CREDIBILITY_WEIGHTS[4],
            "tier_name": TIER_NAMES[4],
        }

    def calculate_avg_credibility(self, domains: list) -> float:
        """
        Calculate weighted average credibility for a list of domains.

        Returns:
            float 0.0-1.0
        """
        if not domains:
            return 0.0
        weights = [self.get_source_credibility(d)["weight"] for d in domains]
        return sum(weights) / len(weights)


# Singleton
_media_credibility_db: Optional[BrazilianMediaCredibilityDB] = None
_media_credibility_lock = threading.Lock()


def get_media_credibility_db() -> BrazilianMediaCredibilityDB:
    """Get or create the BrazilianMediaCredibilityDB singleton (thread-safe)."""
    global _media_credibility_db
    if _media_credibility_db is None:
        with _media_credibility_lock:
            if _media_credibility_db is None:
                _media_credibility_db = BrazilianMediaCredibilityDB()
    return _media_credibility_db
