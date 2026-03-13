# Spec: Fact-Check Scan (Article Safety Validator)

**Status:** Draft
**Author:** Claude (agentic spec generation)
**Date:** 2026-03-12
**Priority:** High

## 1. Vision

Add an on-demand "Verificar" (Fact-Check Scan) button to the article editor that runs a comprehensive safety assessment on the current article text — regardless of how it was created (AI-generated, manually written, or AI-edited). The scan produces a human-readable **Article Safety Index (ASI)** from 0-100 with actionable, claim-by-claim feedback that journalists can use to fix issues before publishing.

**User story:** "As a journalist, I want to click a button in the editor to scan my article for factual errors, unverified claims, and potential misinformation — so I can fix problems before publishing and have confidence in what I'm putting out."

## 2. How It Differs from Existing Verification

| Aspect | Existing (Inline Verification) | Fact-Check Scan (New) |
|--------|-------------------------------|----------------------|
| **When** | Runs automatically during generation | On-demand, user clicks button |
| **Scope** | Only AI-generated articles | Any article in the editor (AI or manual) |
| **Source dependency** | Requires `texto_base` source material | Works without source — uses Exa to find corroborating evidence |
| **External checks** | None | Google Fact Check API + Exa fact-checker search |
| **Source credibility** | All sources treated equally | Weighted by media tier (1-4) |
| **Claim severity** | All claims treated equally | Critical/high/medium/low severity |
| **Output** | Bag of metrics (confidence, grounded ratio) | Single ASI score (0-100) + inline claim highlighting |
| **Re-scannable** | No (snapshot at generation time) | Yes — scan, edit, scan again |
| **Stale data** | Becomes stale after edits | Always reflects current text |

**Key principle:** The scan is a **safety net**, not a gate. It provides information and recommendations — the journalist decides whether to act on them. Only the existing safety gates can block publication.

## 3. User Experience

### 3.1 Button Placement

The "Verificar" button lives in the editor's right sidebar (Assistente tab), above the chat messages:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Left (70%)                        │  Right (30%)                   │
│                                     │                                │
│  [B][I][U][H2][•][1.]["][—][🔗][📷]│  [Assistente] [SEO]           │
│  ──────────────────────────────────│                                │
│                                     │  ┌────────────────────────┐   │
│  Article editor (TipTap)           │  │ 🛡️ Verificar Segurança │   │
│                                     │  │    Scan article safety  │   │
│  "O presidente anunciou hoje       │  └────────────────────────┘   │
│   investimentos de R$2,5 bilhões   │                                │
│   no programa de infraestrutura.   │  ┌─ Verification Banner ───┐  │
│   A medida foi confirmada pelo     │  │ (shows after scan)       │  │
│   ministro da Economia durante     │  └─────────────────────────┘  │
│   coletiva em Brasília..."         │                                │
│                                     │  ┌─ Chat Messages ────────┐  │
│                                     │  │ ...                      │  │
│                                     │  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Scan States

**Idle (default):**
```
┌───────────────────────────────────┐
│  🛡️ Verificar Segurança          │
│  Analise o artigo em busca de     │
│  informações imprecisas           │
│  [Iniciar Verificação]            │
└───────────────────────────────────┘
```

**Scanning (in progress):**
```
┌───────────────────────────────────┐
│  🛡️ Verificando...               │
│  ━━━━━━━━━━━━━░░░░░░░  60%       │
│                                    │
│  ✅ Extraindo afirmações          │
│  ✅ Buscando fontes externas      │
│  🔄 Verificando com fact-checkers │
│  ○ Calculando score de segurança  │
│                                    │
│  Tempo estimado: ~15s             │
└───────────────────────────────────┘
```

**Phases (4 steps, ~15-25 seconds total):**
1. Extraindo afirmações (claim extraction via Claude Haiku)
2. Buscando fontes externas (Exa corroboration + Google Fact Check)
3. Verificando com fact-checkers (cross-reference + credibility scoring)
4. Calculando score de segurança (ASI computation)

### 3.3 Results Panel

**After scan completes, the sidebar shows:**

```
┌───────────────────────────────────┐
│  🛡️ Verificação de Segurança     │
│                                    │
│       ┌─────┐                     │
│       │  82 │  Confiável          │
│       └─────┘  🟢                 │
│                                    │
│  ┌─ Resumo ─────────────────────┐ │
│  │ 8/10 afirmações verificadas  │ │
│  │ 1 não verificável            │ │
│  │ 1 possivelmente incorreta   │ │
│  │ 3 fontes Tier-1 confirmam   │ │
│  │ 0 fact-checks externos      │ │
│  └──────────────────────────────┘ │
│                                    │
│  ┌─ Afirmações ─── [Expandir] ──┐ │
│  │                               │ │
│  │ ✅ "O presidente anunciou    │ │
│  │    investimentos no programa" │ │
│  │    Reuters, G1 · Alta conf.  │ │
│  │                               │ │
│  │ ✅ "A medida foi confirmada  │ │
│  │    pelo ministro"             │ │
│  │    Folha · Média conf.       │ │
│  │                               │ │
│  │ ⚠️ "investimentos de R$2,5   │ │
│  │    bilhões"                   │ │
│  │    Fontes indicam R$2,1 bi   │ │
│  │    Severidade: Alta           │ │
│  │    [Ver fontes] [Corrigir]    │ │
│  │                               │ │
│  │ ❔ "coletiva em Brasília"    │ │
│  │    Sem fonte para verificar   │ │
│  │    Severidade: Baixa          │ │
│  │                               │ │
│  └──────────────────────────────┘ │
│                                    │
│  ┌─ Fontes Utilizadas ──────────┐ │
│  │ 🏆 reuters.com (Tier 1)      │ │
│  │ 🏆 g1.globo.com (Tier 1)     │ │
│  │ 🏆 folha.uol.com.br (Tier 1) │ │
│  │ 📰 poder360.com.br (Tier 2)  │ │
│  └──────────────────────────────┘ │
│                                    │
│  [🔄 Verificar novamente]         │
│                                    │
│  Última verificação: há 2 min     │
└───────────────────────────────────┘
```

### 3.4 Inline Claim Highlighting (Editor Integration)

When scan results are available, flagged claims in the TipTap editor get colored underlines:

| Verdict | Color | Style |
|---------|-------|-------|
| Grounded | None | No highlight (clean) |
| Fabricated/Incorrect | `#EF4444` (red) | Wavy underline + tooltip |
| Unverifiable | `#F59E0B` (amber) | Dotted underline + tooltip |
| External fact-check found | `#3B82F6` (blue) | Solid underline + tooltip |

**Tooltip on hover:**
```
┌─────────────────────────────────────────┐
│ ⚠️ Possivelmente incorreta              │
│ "investimentos de R$2,5 bilhões"        │
│                                          │
│ Fontes encontradas indicam R$2,1 bi     │
│ → Reuters (11/03/2026)                   │
│ → Folha de S.Paulo (11/03/2026)         │
│                                          │
│ Severidade: Alta (financial claim)       │
│ [Ir para claim] [Ignorar]               │
└─────────────────────────────────────────┘
```

**Implementation:** TipTap Mark extension (similar to spell-check underlines). Marks are applied as decorations over the editor content, not modifying the actual HTML. Cleared when the user edits the highlighted text or starts a new scan.

### 3.5 ASI Score Visual

| Score | Label | Color | Icon | Meaning |
|-------|-------|-------|------|---------|
| 90-100 | Seguro | `#10B981` green | ShieldCheck | All claims verified, high-credibility sources |
| 75-89 | Confiavel | `#3B82F6` blue | Shield | Minor unverifiable claims, review recommended |
| 60-74 | Atencao | `#F59E0B` amber | AlertTriangle | Some unverified claims, needs human review |
| 40-59 | Risco | `#E87722` orange | ShieldAlert | Fabrication detected or low confidence |
| 0-39 | Critico | `#EF4444` red | ShieldX | Multiple fabrications, unreliable |

The score is displayed as a large number with a colored ring (similar to Lighthouse scores).

## 4. Backend Architecture

### 4.1 New Endpoint: `POST /api/fact-check-scan`

**Purpose:** Runs on-demand article safety assessment, independent of the generation pipeline.

**Request:**
```python
class FactCheckScanRequest(BaseModel):
    article_text: str               # Plain text or HTML (max 15000 chars)
    article_title: str = ""         # Optional: article title for context
    source_urls: list[str] = []     # Optional: known source URLs (from generation)
    source_text: str = ""           # Optional: original source material
    user_article_id: str = ""       # Optional: link scan to saved article
    language: str = "pt"            # Article language
```

**Response:**
```python
class FactCheckScanResponse(BaseModel):
    # Composite score
    safety_index: int                               # 0-100 ASI
    safety_label: str                               # "seguro" | "confiavel" | "atencao" | "risco" | "critico"

    # Claim analysis
    claims: list[ScanClaim]                         # All extracted claims with verdicts
    total_claims: int
    grounded_claims: int
    fabricated_claims: int
    unverifiable_claims: int

    # Source credibility
    source_credibility: SourceCredibilityReport
    corroboration_score: float                      # 0.0-1.0

    # External fact-checks
    external_fact_checks: list[ExternalFactCheck]   # From Google Fact Check API
    fact_check_matches: int                         # How many claims matched known fact-checks

    # Metadata
    scan_duration_ms: int
    scan_id: str                                    # Correlation ID for logging
    scanned_at: str                                 # ISO timestamp

class ScanClaim(BaseModel):
    text: str                                       # The claim text
    verdict: str                                    # "grounded" | "fabricated" | "unverifiable" | "opinion"
    severity: str                                   # "critical" | "high" | "medium" | "low"
    category: str                                   # "fact" | "statistic" | "quote" | "attribution"
    evidence: str                                   # Supporting/refuting evidence summary
    sources: list[ClaimSource]                      # Corroborating sources found
    external_fact_check: ExternalFactCheck | None   # If matched in Google API
    position_hint: str                              # Approximate text to locate in article

class ClaimSource(BaseModel):
    domain: str                                     # "reuters.com"
    title: str                                      # Article title
    url: str                                        # Source URL
    tier: int                                       # 1-4 credibility tier
    tier_name: str                                  # "Tier 1 - Agencia internacional"
    snippet: str                                    # Relevant excerpt

class ExternalFactCheck(BaseModel):
    claim_text: str                                 # Original claim reviewed
    rating: str                                     # "Falso", "Verdadeiro", etc.
    publisher: str                                  # "Aos Fatos", "Agencia Lupa", etc.
    review_url: str                                 # Link to full fact-check
    review_date: str                                # When reviewed

class SourceCredibilityReport(BaseModel):
    sources_found: int                              # Total unique sources
    tier_breakdown: dict[str, int]                  # {"tier_1": 3, "tier_2": 1, ...}
    avg_credibility: float                          # 0.0-1.0 weighted average
    highest_tier_sources: list[str]                 # ["Reuters", "G1"]
    unknown_sources: list[str]                      # Domains not in credibility DB
```

### 4.2 New Service: `article_safety_service.py`

This is a **new service file** (~300-400 lines) that orchestrates the scan. It does NOT modify `fact_check_service.py` — it wraps and extends it.

```python
class ArticleSafetyService:
    """On-demand article safety assessment service."""

    def __init__(self):
        self.fact_checker = FactCheckService()
        self.llm_service = LLMService()
        self.credibility_db = BrazilianMediaCredibilityDB()

    async def scan(
        self,
        article_text: str,
        article_title: str = "",
        source_urls: list[str] = None,
        source_text: str = "",
        language: str = "pt",
        correlation_id: str = "",
    ) -> FactCheckScanResponse:
        """
        Run comprehensive article safety scan.

        Pipeline:
        1. Extract claims (Claude Haiku — fast, cheap)
        2. Parallel: Exa corroboration + Google Fact Check API
        3. Source credibility scoring
        4. Claim severity classification
        5. Composite ASI calculation
        """
```

**Scan Pipeline (4 phases):**

```
Phase 1: Claim Extraction (~3s)
├── Strip HTML tags from article
├── Claude Haiku extracts up to 15 claims
├── Each claim: text, category (fact/statistic/quote/attribution/opinion)
└── Returns: list[RawClaim]

Phase 2: Evidence Gathering (~8-12s, parallel)
├── 2a: Exa Corroboration Search (per claim, batched)
│   ├── Neural search for each claim (top 3 results)
│   ├── Domain-filtered search on fact-checker sites
│   └── Returns: {claim → [sources]}
├── 2b: Google Fact Check API (per claim, batched)
│   ├── Query for each claim in Portuguese
│   ├── Filter by max age 365 days
│   └── Returns: {claim → [fact_checks]}
└── 2c: Source Credibility Lookup (from Exa results)
    ├── Map each domain to credibility tier
    └── Returns: {domain → tier_info}

Phase 3: Claim Verdict & Severity (~3s)
├── Claude Haiku classifies each claim:
│   ├── Verdict: grounded | fabricated | unverifiable | opinion
│   ├── Based on: Exa evidence + Google fact-checks
│   └── Evidence summary: why this verdict
├── Severity classification:
│   ├── Critical: deaths, accusations, health claims, legal outcomes
│   ├── High: financial figures, policy decisions, attributions
│   ├── Medium: dates, locations, minor statistics
│   └── Low: descriptions, adjectives, general context
└── Returns: list[ScanClaim]

Phase 4: ASI Calculation (~0ms, pure math)
├── Weighted composite from all signals
└── Returns: safety_index (0-100), safety_label
```

### 4.3 Article Safety Index (ASI) Formula

```python
def calculate_asi(
    claims: list[ScanClaim],
    source_credibility: SourceCredibilityReport,
    corroboration_score: float,
    external_fact_checks: list[ExternalFactCheck],
) -> int:
    """
    Calculate Article Safety Index (0-100).

    Components (weights sum to 1.0):
    - Claim grounding ratio:     35%
    - Claim severity penalty:    20%
    - Source credibility:         15%
    - Corroboration score:        15%
    - External fact-check bonus:  10%
    - Opinion/context bonus:       5%
    """
    if not claims:
        return 50  # No claims = neutral (can't assess)

    total = len(claims)
    factual_claims = [c for c in claims if c.verdict != "opinion"]
    if not factual_claims:
        return 85  # All opinion = generally safe

    # --- Component 1: Claim Grounding (35%) ---
    grounded = sum(1 for c in factual_claims if c.verdict == "grounded")
    grounding_ratio = grounded / len(factual_claims)
    grounding_score = grounding_ratio * 100  # 0-100

    # --- Component 2: Severity-Weighted Penalty (20%) ---
    severity_weights = {"critical": 25, "high": 15, "medium": 8, "low": 3}
    penalty = 0
    for c in factual_claims:
        if c.verdict in ("fabricated", "unverifiable"):
            penalty += severity_weights.get(c.severity, 5)
    severity_score = max(0, 100 - penalty)  # 0-100

    # --- Component 3: Source Credibility (15%) ---
    credibility_score = source_credibility.avg_credibility * 100  # 0-100

    # --- Component 4: Corroboration (15%) ---
    corroboration_pct = corroboration_score * 100  # 0-100

    # --- Component 5: External Fact-Check (10%) ---
    # Bonus if no contradicting fact-checks found
    contradicting = sum(
        1 for fc in external_fact_checks
        if fc.rating.lower() in ("falso", "enganoso", "distorcido", "insustentavel")
    )
    if contradicting > 0:
        factcheck_score = max(0, 100 - (contradicting * 40))
    elif len(external_fact_checks) > 0:
        factcheck_score = 100  # Fact-checks exist and none contradict
    else:
        factcheck_score = 70  # No data = neutral

    # --- Component 6: Opinion/Context (5%) ---
    opinion_count = sum(1 for c in claims if c.verdict == "opinion")
    opinion_ratio = opinion_count / total
    # High opinion ratio is fine (editorials), but pure opinion = slightly lower
    opinion_score = 90 if opinion_ratio > 0.5 else 100

    # --- Weighted ASI ---
    asi = (
        grounding_score * 0.35
        + severity_score * 0.20
        + credibility_score * 0.15
        + corroboration_pct * 0.15
        + factcheck_score * 0.10
        + opinion_score * 0.05
    )

    return max(0, min(100, round(asi)))
```

### 4.4 Brazilian Media Credibility Database

Static configuration stored in `services/media_credibility.py`:

```python
BRAZILIAN_MEDIA_TIERS = {
    # === Tier 1: International wire services & major Brazilian outlets ===
    # Credibility weight: 0.95
    "reuters.com":              {"tier": 1, "name": "Reuters",           "type": "wire"},
    "apnews.com":               {"tier": 1, "name": "Associated Press",  "type": "wire"},
    "afp.com":                  {"tier": 1, "name": "AFP",               "type": "wire"},
    "folha.uol.com.br":        {"tier": 1, "name": "Folha de S.Paulo",  "type": "print"},
    "oglobo.globo.com":        {"tier": 1, "name": "O Globo",           "type": "print"},
    "estadao.com.br":          {"tier": 1, "name": "Estadao",           "type": "print"},
    "g1.globo.com":            {"tier": 1, "name": "G1",                "type": "digital"},
    "valor.globo.com":         {"tier": 1, "name": "Valor Economico",   "type": "financial"},
    "agenciabrasil.ebc.com.br": {"tier": 1, "name": "Agencia Brasil",   "type": "government"},
    "bbc.com":                  {"tier": 1, "name": "BBC",               "type": "international"},
    "cnnbrasil.com.br":        {"tier": 1, "name": "CNN Brasil",        "type": "tv"},
    "noticias.uol.com.br":     {"tier": 1, "name": "UOL Noticias",     "type": "digital"},

    # === Tier 2: Established regional/specialized outlets ===
    # Credibility weight: 0.80
    "poder360.com.br":         {"tier": 2, "name": "Poder360",          "type": "political"},
    "nexojornal.com.br":       {"tier": 2, "name": "Nexo Jornal",       "type": "analytical"},
    "gazetadopovo.com.br":     {"tier": 2, "name": "Gazeta do Povo",    "type": "regional"},
    "correiobraziliense.com.br": {"tier": 2, "name": "Correio Braziliense", "type": "regional"},
    "metropoles.com":          {"tier": 2, "name": "Metropoles",        "type": "digital"},
    "infomoney.com.br":        {"tier": 2, "name": "InfoMoney",         "type": "financial"},
    "gauchazh.clicrbs.com.br": {"tier": 2, "name": "GauchazH",         "type": "regional"},
    "brazilian.report":        {"tier": 2, "name": "The Brazilian Report", "type": "english"},
    "cartacapital.com.br":     {"tier": 2, "name": "Carta Capital",     "type": "magazine"},
    "revistaoeste.com":        {"tier": 2, "name": "Revista Oeste",     "type": "magazine"},

    # === Tier 3: Government/institutional (.gov.br) ===
    # Credibility weight: 0.90 (official data, high for factual claims)
    "gov.br":                  {"tier": 3, "name": "Portal do Governo",  "type": "government"},
    "planalto.gov.br":         {"tier": 3, "name": "Planalto",          "type": "government"},
    "senado.leg.br":           {"tier": 3, "name": "Senado Federal",    "type": "government"},
    "camara.leg.br":           {"tier": 3, "name": "Camara dos Deputados", "type": "government"},
    "stf.jus.br":              {"tier": 3, "name": "STF",               "type": "judiciary"},
    "ibge.gov.br":             {"tier": 3, "name": "IBGE",              "type": "statistics"},
    "bcb.gov.br":              {"tier": 3, "name": "Banco Central",     "type": "financial"},

    # === Fact-Checkers (highest trust for verdicts) ===
    # Credibility weight: 1.0
    "aosfatos.org":            {"tier": 0, "name": "Aos Fatos",         "type": "factcheck", "ifcn": True},
    "lupa.uol.com.br":        {"tier": 0, "name": "Agencia Lupa",      "type": "factcheck", "ifcn": True},
    "checamos.afp.com":        {"tier": 0, "name": "AFP Checamos",      "type": "factcheck", "ifcn": True},
    "boatos.org":              {"tier": 0, "name": "Boatos.org",        "type": "factcheck"},
    "projetocomprova.com.br":  {"tier": 0, "name": "Comprova",          "type": "factcheck"},
    "e-farsas.com":            {"tier": 0, "name": "E-Farsas",          "type": "factcheck"},
}

# Credibility weights by tier (used in ASI calculation)
TIER_CREDIBILITY_WEIGHTS = {
    0: 1.00,   # Fact-checkers
    1: 0.95,   # Wire services & major outlets
    2: 0.80,   # Established regional/specialized
    3: 0.90,   # Government/institutional
    4: 0.50,   # Unknown/unclassified domains
}
```

### 4.5 Google Fact Check API Integration

```python
GOOGLE_FACTCHECK_ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

async def search_google_fact_checks(
    claim_text: str,
    language: str = "pt",
    max_age_days: int = 365,
    max_results: int = 5,
) -> list[ExternalFactCheck]:
    """
    Search Google Fact Check Tools API for existing fact-checks.

    Free API. Covers Brazilian fact-checkers:
    Aos Fatos, Agencia Lupa, Estadao Verifica, AFP Checamos,
    Fato ou Fake, Boatos.org.
    """
    api_key = os.environ.get("GOOGLE_FACTCHECK_API_KEY", "")
    if not api_key:
        return []

    params = {
        "query": claim_text,
        "languageCode": language,
        "maxAgeDays": max_age_days,
        "pageSize": max_results,
        "key": api_key,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(GOOGLE_FACTCHECK_ENDPOINT, params=params)

    if resp.status_code != 200:
        logger.warning(f"Google FactCheck API error {resp.status_code}")
        return []

    results = []
    for claim in resp.json().get("claims", []):
        for review in claim.get("claimReview", []):
            results.append(ExternalFactCheck(
                claim_text=claim.get("text", ""),
                rating=review.get("textualRating", ""),
                publisher=review.get("publisher", {}).get("name", ""),
                review_url=review.get("url", ""),
                review_date=review.get("reviewDate", ""),
            ))

    return results
```

### 4.6 Exa Fact-Checker Domain Search

Extends existing `_search_exa()` with a domain-filtered variant:

```python
async def search_factcheck_sites(self, claim: str) -> list[dict]:
    """Search Brazilian fact-checking sites specifically for this claim."""
    payload = {
        "query": claim,
        "type": "neural",
        "useAutoprompt": True,
        "numResults": 5,
        "includeDomains": [
            "aosfatos.org",
            "lupa.uol.com.br",
            "boatos.org",
            "projetocomprova.com.br",
            "e-farsas.com",
            "estadao.com.br",
            "g1.globo.com",
            "checamos.afp.com",
        ],
        "contents": {
            "text": {"maxCharacters": 2000},
            "highlights": {"numSentences": 3},
        },
    }
    # Execute with existing httpx client + circuit breaker
```

### 4.7 Claim Severity Classification

Uses Claude Haiku (fast, cheap) to classify claim severity:

```python
SEVERITY_PROMPT = """Classifique a severidade de cada afirmação abaixo.

Severidades:
- critical: mortes, acusações criminais, saúde pública, decisões judiciais
- high: valores financeiros, decisões políticas, atribuições de falas
- medium: datas, localizações, estatísticas menores
- low: descrições, adjetivos, contexto geral

Afirmações:
{claims_json}

Responda em JSON: [{{"claim": "...", "severity": "..."}}]"""
```

### 4.8 Rate Limiting

```python
# New rate limit for scan endpoint
RATE_LIMITS["fact-check-scan"] = {"rate": 0.25, "burst": 2}
# 1 scan per 4 seconds, max burst of 2
# (more restrictive than generate — scans are expensive)
```

### 4.9 Model Routing for Scan

| Task | Model | Rationale |
|------|-------|-----------|
| Claim extraction (Phase 1) | `claude-haiku-4-5` | Fast, simple extraction task |
| Claim verdict + severity (Phase 3) | `claude-haiku-4-5` | Classification with evidence |
| Exa search (Phase 2a) | Exa API | Existing integration |
| Google Fact Check (Phase 2b) | Google API | Free external API |

**Total estimated cost per scan: ~$0.02-0.04** (2 Haiku calls + Exa searches)
This is ~10x cheaper than a full generation cycle.

## 5. Frontend Architecture

### 5.1 New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `FactCheckScanPanel.jsx` | `src/components/editor/FactCheckScanPanel.jsx` | Main scan UI (button, progress, results) |
| `ClaimCard.jsx` | `src/components/editor/ClaimCard.jsx` | Individual claim display with verdict |
| `SafetyScoreRing.jsx` | `src/components/ui/SafetyScoreRing.jsx` | Circular ASI score display |
| `useFactCheckScan.js` | `src/hooks/useFactCheckScan.js` | Scan state management hook |

### 5.2 FactCheckScanPanel Component

```jsx
function FactCheckScanPanel({ articleText, articleTitle, sourceUrls }) {
  const {
    scanResult,       // FactCheckScanResponse | null
    isScanning,       // boolean
    scanProgress,     // { phase: number, message: string, percent: number }
    error,            // string | null
    startScan,        // () => Promise<void>
    clearResults,     // () => void
    lastScannedAt,    // Date | null
  } = useFactCheckScan()

  return (
    <div className="border border-gray-200 rounded-xl p-4 bg-white">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <ShieldCheck size={18} className="text-tmc-orange" />
        <h3 className="font-semibold text-sm">Verificar Seguranca</h3>
      </div>

      {/* Idle state */}
      {!isScanning && !scanResult && (
        <IdleState onStart={() => startScan(articleText, articleTitle, sourceUrls)} />
      )}

      {/* Scanning state */}
      {isScanning && <ScanProgress progress={scanProgress} />}

      {/* Results state */}
      {scanResult && <ScanResults result={scanResult} onRescan={startScan} />}
    </div>
  )
}
```

### 5.3 useFactCheckScan Hook

```jsx
function useFactCheckScan() {
  const [scanResult, setScanResult] = useState(null)
  const [isScanning, setIsScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState(null)
  const [error, setError] = useState(null)
  const [lastScannedAt, setLastScannedAt] = useState(null)

  const startScan = useCallback(async (articleText, articleTitle, sourceUrls) => {
    if (!articleText || articleText.trim().length < 100) {
      setError('O artigo precisa ter pelo menos 100 caracteres para verificacao')
      return
    }

    setIsScanning(true)
    setError(null)
    setScanProgress({ phase: 1, message: 'Extraindo afirmacoes...', percent: 10 })

    try {
      // Simulated progress updates via intervals
      const progressInterval = setInterval(() => {
        setScanProgress(prev => {
          if (!prev) return prev
          if (prev.percent < 30) return { phase: 1, message: 'Extraindo afirmacoes...', percent: prev.percent + 5 }
          if (prev.percent < 55) return { phase: 2, message: 'Buscando fontes externas...', percent: prev.percent + 3 }
          if (prev.percent < 80) return { phase: 3, message: 'Verificando com fact-checkers...', percent: prev.percent + 2 }
          return { phase: 4, message: 'Calculando score de seguranca...', percent: Math.min(prev.percent + 1, 95) }
        })
      }, 800)

      const result = await factCheckScan({
        article_text: articleText,
        article_title: articleTitle,
        source_urls: sourceUrls || [],
      })

      clearInterval(progressInterval)
      setScanResult(result)
      setLastScannedAt(new Date())
      setScanProgress({ phase: 4, message: 'Concluido!', percent: 100 })
    } catch (err) {
      setError(err.message || 'Erro ao verificar artigo')
    } finally {
      setIsScanning(false)
    }
  }, [])

  return { scanResult, isScanning, scanProgress, error, startScan, clearResults, lastScannedAt }
}
```

### 5.4 TipTap Inline Highlighting Extension

Custom TipTap decoration plugin to highlight flagged claims:

```jsx
// src/components/editor/extensions/factCheckHighlight.js
import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'

const FactCheckHighlight = Extension.create({
  name: 'factCheckHighlight',

  addOptions() {
    return {
      claims: [],  // Array of { text, verdict, severity }
    }
  },

  addProseMirrorPlugins() {
    const { claims } = this.options
    return [
      new Plugin({
        key: new PluginKey('factCheckHighlight'),
        props: {
          decorations(state) {
            const decorations = []
            const doc = state.doc

            for (const claim of claims) {
              if (claim.verdict === 'grounded' || claim.verdict === 'opinion') continue

              // Find claim text position in document
              doc.descendants((node, pos) => {
                if (!node.isText) return
                const index = node.text.indexOf(claim.position_hint)
                if (index !== -1) {
                  const from = pos + index
                  const to = from + claim.position_hint.length
                  const className = claim.verdict === 'fabricated'
                    ? 'fact-check-fabricated'
                    : 'fact-check-unverifiable'
                  decorations.push(
                    Decoration.inline(from, to, {
                      class: className,
                      'data-claim-id': claim.text,
                      'data-verdict': claim.verdict,
                      'data-severity': claim.severity,
                    })
                  )
                }
              })
            }
            return DecorationSet.create(doc, decorations)
          },
        },
      }),
    ]
  },
})
```

**CSS for highlights:**
```css
/* In src/index.css */
.fact-check-fabricated {
  text-decoration: wavy underline #EF4444;
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
  cursor: help;
}

.fact-check-unverifiable {
  text-decoration: dotted underline #F59E0B;
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
  cursor: help;
}
```

### 5.5 Integration in CriarPostPage

The FactCheckScanPanel replaces/augments the existing VerificationBanner in the sidebar:

```jsx
// In CriarPostPage.jsx, inside the Assistente tab:

{/* Existing verification banner (from generation) */}
{verificationData && !factCheckScanResult && (
  <VerificationBanner
    verification={verificationData}
    publishBlocked={publishBlocked}
    blockReason={blockReason}
    humanReviewRequired={humanReviewRequired}
    reviewReasons={reviewReasons}
  />
)}

{/* NEW: Fact-Check Scan Panel */}
<FactCheckScanPanel
  articleText={content}
  articleTitle={title}
  sourceUrls={resultado?.sourceUrls || []}
/>
```

When a scan is active, its results take precedence over the stale generation-time verification banner.

### 5.6 API Service Addition

```js
// In src/services/api.js

export async function factCheckScan({ article_text, article_title, source_urls }) {
  return fetchApi('/fact-check-scan', {
    method: 'POST',
    body: JSON.stringify({
      article_text,
      article_title,
      source_urls,
    }),
    signal: AbortSignal.timeout(60000),  // 60 second timeout
  })
}
```

## 6. Endpoint Registration

**File:** `function_app.py`

```python
from functions.fact_check_scan_api import fact_check_scan_handler

app.route(route="fact-check-scan", methods=["POST", "OPTIONS"])(fact_check_scan_handler)
```

**Handler file:** `functions/fact_check_scan_api.py`

```python
@with_cors
@require_auth
async def fact_check_scan_handler(req: func.HttpRequest) -> func.HttpResponse:
    """On-demand article safety scan."""
    # 1. Rate limit check
    # 2. Parse FactCheckScanRequest
    # 3. Validate (article_text 100-15000 chars)
    # 4. Run ArticleSafetyService.scan()
    # 5. Log to llm_usage_log
    # 6. Return FactCheckScanResponse
```

## 7. Database Changes

### 7.1 New Table: `fact_check_scans`

```sql
CREATE TABLE fact_check_scans (
    id INT IDENTITY(1,1) PRIMARY KEY,
    scan_id VARCHAR(64) NOT NULL,
    user_id INT NOT NULL,
    user_article_id INT NULL,               -- FK to user_articles (optional)
    article_text_hash VARCHAR(64) NOT NULL,  -- SHA-256 of scanned text
    article_char_count INT NOT NULL,
    safety_index INT NOT NULL,               -- 0-100
    safety_label VARCHAR(20) NOT NULL,
    total_claims INT NOT NULL DEFAULT 0,
    grounded_claims INT NOT NULL DEFAULT 0,
    fabricated_claims INT NOT NULL DEFAULT 0,
    unverifiable_claims INT NOT NULL DEFAULT 0,
    corroboration_score FLOAT NULL,
    external_factcheck_matches INT NOT NULL DEFAULT 0,
    scan_result NVARCHAR(MAX) NULL,          -- Full JSON result (truncated to 10000 chars)
    scan_duration_ms INT NULL,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IX_fact_check_scans_user ON fact_check_scans(user_id, created_at DESC);
CREATE INDEX IX_fact_check_scans_article ON fact_check_scans(user_article_id);
```

**Purpose:** Track scan history for analytics, rate limiting, and showing last scan result when re-opening an article.

### 7.2 Migration File

`migrations/014_create_fact_check_scans.sql`

## 8. Environment Variables

### New Required (when feature enabled)
```
GOOGLE_FACTCHECK_API_KEY           # Google Fact Check Tools API key (free)
```

### New Optional
```
FACT_CHECK_SCAN_ENABLED=true       # Feature flag (default: true)
FACT_CHECK_SCAN_MAX_CLAIMS=15      # Max claims to extract (default: 15)
FACT_CHECK_SCAN_EXA_RESULTS=3      # Exa results per claim (default: 3)
```

## 9. Cost Analysis

### Per Scan
| Operation | Provider | Est. Cost |
|-----------|----------|-----------|
| Claim extraction (Haiku) | Anthropic/Azure | ~$0.005 |
| Severity classification (Haiku) | Anthropic/Azure | ~$0.005 |
| Exa corroboration (15 claims x 3 results) | Exa | ~$0.03 |
| Google Fact Check API (15 queries) | Google | Free |
| Credibility lookup | Local | Free |
| ASI calculation | Local | Free |
| **Total per scan** | | **~$0.04** |

### Comparison
| Operation | Cost |
|-----------|------|
| Full article generation | ~$0.25-0.30 |
| Fact-Check Scan | ~$0.04 |
| **Scan is ~7x cheaper** | |

### Monthly Estimate (10 journalists, 5 scans/day each)
- 50 scans/day x 30 days = 1,500 scans/month
- 1,500 x $0.04 = **~$60/month**

## 10. Edge Cases

| Scenario | Handling |
|----------|----------|
| Article too short (<100 chars) | Disable scan button, show tooltip: "Artigo precisa ter pelo menos 100 caracteres" |
| Article too long (>15000 chars) | Truncate to first 15000 chars, show warning: "Apenas os primeiros 15.000 caracteres foram verificados" |
| No claims extractable | Return ASI=50 with message: "Nao foi possivel extrair afirmacoes verificaveis" |
| All claims are opinion | Return ASI=85 with message: "Artigo predominantemente opinativo" |
| Exa API down | Graceful degradation: skip corroboration, rely on Google API + Haiku classification. Lower ASI by 15 points. |
| Google Fact Check API down | Skip external fact-checks. Note in response: "Verificacao externa indisponivel" |
| Both APIs down | Haiku-only verification: extract claims, classify based on internal analysis. Floor ASI at 50. |
| User scans while editing | Scan uses text snapshot at click time. Edits during scan don't affect results. |
| Rapid re-scans | Rate limiter: 1 scan per 4 seconds. Show "Aguarde X segundos" message. |
| Article in non-Portuguese | Detect language. If not Portuguese, use English in API queries. Show note: "Artigo detectado em outro idioma" |
| HTML content with tags | Strip HTML before sending to backend. Only analyze visible text. |
| Empty source_urls | No source credibility context — scan relies entirely on Exa discovery. This is fine. |
| Same article re-scanned | Check `fact_check_scans` table by text hash. If scanned <5 min ago, return cached result. |

## 11. Security Considerations

- **Input validation:** Max 15000 chars, strip HTML server-side, reject non-text content
- **Rate limiting:** 0.25 req/sec to prevent API abuse
- **Authentication:** Requires valid JWT (`@require_auth` decorator)
- **No PII in external queries:** Claims sent to Google/Exa are extracted phrases, not full articles
- **API key security:** `GOOGLE_FACTCHECK_API_KEY` stored in environment, never logged
- **Audit logging:** All scans logged with user_id for accountability

## 12. Implementation Plan

### Phase 1: Backend Core (~1 task)
1. Create `services/media_credibility.py` with Brazilian media tier database
2. Create `services/article_safety_service.py` with scan pipeline
3. Integrate Google Fact Check API client
4. Add Exa domain-filtered search method
5. Implement ASI calculation formula
6. Unit test the ASI formula with known inputs

### Phase 2: Backend Endpoint (~1 task)
1. Create `functions/fact_check_scan_api.py` handler
2. Create migration `014_create_fact_check_scans.sql`
3. Register route in `function_app.py`
4. Add rate limiting for `fact-check-scan`
5. Add LLM usage logging for scan calls
6. Test endpoint with curl/Postman

### Phase 3: Frontend Scan Panel (~1 task)
1. Create `useFactCheckScan.js` hook
2. Create `FactCheckScanPanel.jsx` component
3. Create `SafetyScoreRing.jsx` component
4. Create `ClaimCard.jsx` component
5. Add `factCheckScan()` to `api.js`
6. Integrate panel into CriarPostPage sidebar

### Phase 4: Inline Highlighting (~1 task)
1. Create `factCheckHighlight.js` TipTap extension
2. Add CSS for underline styles
3. Wire scan results to editor decorations
4. Add hover tooltips for highlighted claims
5. Handle decoration cleanup on edit/rescan

### Phase 5: Testing & Polish (~1 task)
1. Test with real articles (AI-generated and manual)
2. Test with known false claims (should flag them)
3. Test graceful degradation (Exa down, Google down)
4. Test rate limiting
5. Verify scan caching works
6. Performance test (target: <25 seconds for full scan)

## 13. Files to Create/Modify

### New Files
| File | Purpose | Est. Size |
|------|---------|-----------|
| `FeedRSS/tmc-rss-collector/services/article_safety_service.py` | Scan orchestration service | ~400 lines |
| `FeedRSS/tmc-rss-collector/services/media_credibility.py` | Brazilian media tier DB | ~120 lines |
| `FeedRSS/tmc-rss-collector/functions/fact_check_scan_api.py` | HTTP endpoint handler | ~120 lines |
| `FeedRSS/tmc-rss-collector/migrations/014_create_fact_check_scans.sql` | DB migration | ~25 lines |
| `tmc-redacao/src/components/editor/FactCheckScanPanel.jsx` | Scan panel UI | ~250 lines |
| `tmc-redacao/src/components/editor/ClaimCard.jsx` | Claim display card | ~80 lines |
| `tmc-redacao/src/components/ui/SafetyScoreRing.jsx` | ASI score ring | ~60 lines |
| `tmc-redacao/src/hooks/useFactCheckScan.js` | Scan state hook | ~80 lines |
| `tmc-redacao/src/components/editor/extensions/factCheckHighlight.js` | TipTap extension | ~60 lines |

### Modified Files
| File | Change |
|------|--------|
| `FeedRSS/tmc-rss-collector/function_app.py` | Register `/api/fact-check-scan` route |
| `FeedRSS/tmc-rss-collector/services/rate_limiter.py` | Add `fact-check-scan` rate limit |
| `tmc-redacao/src/pages/CriarPostPage.jsx` | Add FactCheckScanPanel to sidebar |
| `tmc-redacao/src/services/api.js` | Add `factCheckScan()` function |
| `tmc-redacao/src/index.css` | Add fact-check highlight CSS |

## 14. Success Criteria

1. Scan completes in <25 seconds for a 2000-word article
2. Known false claims (e.g., debunked by Aos Fatos) are flagged with external fact-check data
3. ASI score correlates with human editorial judgment (±15 points)
4. Fabricated claims in AI-generated articles get `severity: critical/high` appropriately
5. Cost per scan stays under $0.05
6. Graceful degradation when external APIs are down (never crashes, always returns a score)
7. Inline highlights render correctly without modifying article HTML
8. Journalists can scan → edit → rescan iteratively
