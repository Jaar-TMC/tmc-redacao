# Production Readiness v6 — Implementation Tracker

> **PURPOSE**: Single source of truth for the AI implementing this plan.
> Every sub-task has: status, exact file:line, what to change, acceptance criteria, and anti-hallucination notes.
> **RULE**: Do NOT modify code that isn't listed here. Do NOT invent new constants or files beyond what's specified.

---

## Quick Status Dashboard

| Phase | Description | Status | Items Done | Items Total |
|-------|-------------|--------|------------|-------------|
| **1** | Critical Safety | **DONE** | 4/4 | 4 |
| **2** | Quality & Anti-Hallucination | **IN PROGRESS** | 1/6 | 6 |
| **3** | SEO & Readability | PENDING | 0/6 | 6 |
| **4** | Architecture Hardening | PENDING | 0/9 | 9 |
| **5** | Editorial Workflow | PENDING | 0/2 | 2 |

**Last updated**: Phase 1 complete, Phase 2.2 (ATRIBUICAO_INLINE) done.

---

## File Inventory (ONLY these files are modified)

| File | Relative Path | Role |
|------|--------------|------|
| `generation_api.py` | `FeedRSS/tmc-rss-collector/functions/generation_api.py` | Pipeline orchestrator |
| `llm_service.py` | `FeedRSS/tmc-rss-collector/services/llm_service.py` | Prompt engineering + LLM calls |
| `fact_check_service.py` | `FeedRSS/tmc-rss-collector/services/fact_check_service.py` | Enrichment + verification |
| `database.py` | `FeedRSS/tmc-rss-collector/services/database.py` | DB access layer |
| `function_app.py` | `FeedRSS/tmc-rss-collector/function_app.py` | Azure Functions entry point |
| `health.py` | `FeedRSS/tmc-rss-collector/functions/health.py` | Health check endpoint |
| `metrics.py` | `FeedRSS/tmc-rss-collector/services/metrics.py` | **NEW** — In-process metrics |
| `rate_limiter.py` | `FeedRSS/tmc-rss-collector/services/rate_limiter.py` | **NEW** — Token bucket rate limiter |
| `config.py` | `FeedRSS/tmc-rss-collector/services/config.py` | **NEW** — Centralized config |

---

## Critical Context (Anti-Hallucination for the AI)

### Existing Env Vars (DO NOT duplicate or rename)
```
# LLM
AZURE_AI_API_KEY, AZURE_AI_ENDPOINT, ANTHROPIC_API_KEY, ANTHROPIC_MODEL

# Fact Check
FACT_CHECK_ENABLED, FACT_CHECK_ENRICHMENT_ENABLED, FACT_CHECK_VERIFICATION_ENABLED
EXA_API_KEY, EXA_API_ENDPOINT, EXA_MAX_RESULTS, EXA_SEARCH_DAYS, EXA_TIMEOUT_SECONDS

# CoVe
COVE_ENABLED, COVE_MAX_CLAIMS, COVE_QUESTIONS_PER_CLAIM

# Database
SQL_SERVER (default: bi4ia-tmc.database.windows.net), SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD

# Clustering
CLUSTERING_ENABLED, CLUSTERING_SIMILARITY_THRESHOLD, EVENT_EXTRACTION_ENABLED, EVENT_MATCHING_ENABLED
```

### NEW Env Vars (added in this plan)
```
# Phase 1 (DONE)
PRODUCTION_SAFETY_MODE=true          # generation_api.py line 45
SQL_QUERY_TIMEOUT=30                 # database.py line 39
MIN_SOURCE_CHARS=100                 # generation_api.py line 41
NOTA_ONLY_THRESHOLD=150              # generation_api.py line 42

# Phase 2 (added to generation_api.py but NOT YET USED in code)
MAX_REGENERATION_ATTEMPTS=1          # generation_api.py line 48
REGEN_FABRICATION_THRESHOLD=2        # generation_api.py line 49
DECONTAMINATION_ENABLED=true         # generation_api.py line 52

# Phase 4 (NOT YET ADDED)
CORS_ALLOWED_ORIGINS=...             # Will replace hardcoded list in function_app.py
```

### Existing Confidence Weights (fact_check_service.py lines 49-55)
```python
WEIGHT_CLAIM_GROUNDING = 0.40    # Plan 2.6 changes to 0.45
WEIGHT_ENTITY_OVERLAP = 0.25     # Plan 2.6 changes to 0.20
WEIGHT_EXPANSION_RATIO = 0.10    # No change
WEIGHT_QUOTE_VERIFICATION = 0.10 # No change
WEIGHT_MATERIAL_SUFFICIENCY = 0.10 # No change
WEIGHT_CLAIM_SIMILARITY = 0.05   # No change
```

### Existing SOURCE_LENGTH_TIERS (llm_service.py lines 251-256)
```python
SOURCE_LENGTH_TIERS = [
    (150, 200, 400, "nota curta"),
    (500, 400, 1000, "materia curta"),
    (1500, 800, 2000, "materia media"),
    (3000, 1500, 3500, "materia longa"),
    (float('inf'), 2000, 4000, "materia completa"),
]
```

### Key Function Signatures (DO NOT change signatures unless plan says so)
```python
# generation_api.py
async def generate_article_handler(req) -> HttpResponse  # line 305
def evaluate_safety_gates(verification_data, content_length, effective_source_len, prior_human_review=False, prior_review_reasons=None) -> SafetyDecision  # line 171

# llm_service.py
def get_system_prompt(persona, tom, tipo_materia, categoria, modo_opinativo, source_len, has_enrichment, verified_chars) -> str  # line 914
def _build_category_prompt(categoria, tom, tipo_materia, modo_opinativo, source_len, has_enrichment, verified_chars) -> str  # line 1023
def build_user_prompt(texto_base, orientacao_lide, citacoes, contexto, creditos, tags, enrichment_context, enrichment_key_facts, verified_chars) -> str  # line 1171
def get_dynamic_length_requirement(texto_base, verified_chars) -> tuple  # line 260
async def generate_article(self, texto_base, persona, tom, tipo_materia, ..., sensitive_instructions) -> dict  # line 1437

# fact_check_service.py
async def enrich_context(self, texto_base, titulo_fonte, tags) -> EnrichmentContext  # line 397
async def verify_article(self, texto_base, generated_article, citacoes, enrichment) -> VerificationMetadata  # line 821
def _compute_confidence(self, metadata, entity_result, quote_result, claim_similarities) -> float  # line 1926
def _determine_risk_level(self, metadata, entity_result, quote_result) -> str  # line 2058
```

### Singleton Patterns (ALL now thread-safe with Lock)
```python
# llm_service.py line 1870-1894
_llm_service + _llm_service_lock = threading.Lock()

# fact_check_service.py line 2000-2014
_fact_check_service + _fact_check_service_lock = threading.Lock()

# database.py line 2703-2713
_db_service + _db_service_lock = threading.Lock()
```

---

## PHASE 1: Critical Safety — COMPLETE

### 1.1 Hard Minimum Source Threshold — DONE
- **File**: `generation_api.py`
- **Constants added**: `MIN_SOURCE_CHARS=100` (line 41), `NOTA_ONLY_THRESHOLD=150` (line 42)
- **Logic added**: After request parsing (line ~335), before services import:
  - If `source_char_count < MIN_SOURCE_CHARS` → return 422
  - If `source_char_count < NOTA_ONLY_THRESHOLD` → force `tipo_materia="nota"`, set `nota_forced=True`
- **Response fields**: `nota_forced`, `nota_disclaimer` added after generation
- **Acceptance**: Short source (<100) returns 422. Source 100-149 forces nota type.

### 1.2 Safety Gate Tightening — DONE
- **File**: `generation_api.py`
- **Constant added**: `PRODUCTION_SAFETY_MODE=true` (line 45)
- **Changes to `evaluate_safety_gates()`** (line 171):
  - Production: confidence floor 0.50 (was 0.40)
  - Production: 2+ fabricated → hard block (was: only 3+)
  - Production: 1 fabricated + confidence<0.50 → hard block
  - Production: 1 fabricated + confidence>=0.50 → human review
- **Acceptance**: Production mode blocks more aggressively. Legacy mode unchanged.

### 1.3 DB Query Timeout — DONE
- **File**: `database.py` line 39
- **Change**: Added `timeout=query_timeout` (from `SQL_QUERY_TIMEOUT` env var, default 30) to `pymssql.connect()`
- **Acceptance**: Long queries timeout after 30s instead of hanging forever.

### 1.4 Singleton Thread Safety — DONE
- **Files**: `llm_service.py` (line 1870), `fact_check_service.py` (line 2000), `database.py` (line 2703)
- **Pattern**: `threading.Lock()` with double-check locking on all 3 singletons
- **Acceptance**: Concurrent requests don't create duplicate service instances.

---

## PHASE 2: Quality & Anti-Hallucination — IN PROGRESS

### 2.1 Auto-Regeneration on Fabrication — TODO
- **File**: `generation_api.py` — after Phase 3 verification block (after line ~530)
- **Constants**: `MAX_REGENERATION_ATTEMPTS` (line 48), `REGEN_FABRICATION_THRESHOLD` (line 49) — already defined
- **What to implement**:
  1. After verification completes, check `fabricated_claims >= REGEN_FABRICATION_THRESHOLD`
  2. If yes AND `MAX_REGENERATION_ATTEMPTS > 0`:
     - Build constraint string listing the fabricated claims
     - Add constraint to `sensitive_instructions` list
     - Re-call `llm.generate_article()` with augmented instructions
     - Re-verify the new article
     - Accept if fewer fabrications; keep original otherwise
  3. Add `regenerated: bool`, `regeneration_improvement: str` to response
- **Anti-hallucination note**: The regeneration ONLY adds a constraint to `sensitive_instructions` param (which already exists on `generate_article()`). Do NOT create new parameters.
- **Dependencies**: Phase 3 verification must run first (it already does)
- **Acceptance**: When 2+ fabricated claims detected, system retries once with explicit "avoid these claims" instruction.

### 2.2 Inline Source Attribution Prompt — DONE
- **File**: `llm_service.py`
- **New constant**: `ATRIBUICAO_INLINE` (after line 194)
- **Injected into**: Both legacy prompt (line ~1008) and category prompt (line ~1156) — after quality rules, before `SEO_OTIMIZACAO`
- **Content**: Requires minimum 3 attributions per article, preservation of source names, reporting verbs
- **Acceptance**: Generated articles should have more "segundo X", "conforme Y" attributions.

### 2.3 Temporal Decontamination — TODO
- **File**: `fact_check_service.py` — new static method `decontaminate_article()`
- **Also**: `generation_api.py` — call between Phase 2 (generation) and Phase 3 (verification)
- **What to implement**:
  1. In `fact_check_service.py`, add static method:
     ```python
     @staticmethod
     def decontaminate_article(article_text: str, source_text: str, enrichment_text: str = "") -> tuple:
     ```
  2. Regex patterns to detect temporal specifics:
     - Days of week: `nesta (segunda|terca|quarta|quinta|sexta|sabado|domingo)(-feira)?`
     - Specific times: `as \d{1,2}h\d{0,2}`, `as \d{1,2}:\d{2}`
     - Relative dates: `nesta (manha|tarde|noite)`, `ontem`, `anteontem`
  3. For each match: check if it appears in `source_text` or `enrichment_text`
  4. If NOT found in any source: remove it (replace with empty or generic)
  5. Return `(cleaned_text, removals_count, removals_list)`
  6. In `generation_api.py`: call after generation, before verification, gated by `DECONTAMINATION_ENABLED`
  7. Track `decontamination_applied`, `decontamination_removals` in response
- **Anti-hallucination note**: This is a DETERMINISTIC regex pass, NOT an LLM call. Zero cost.
- **Acceptance**: Temporal specifics not in sources are removed. Source-matching temporals are preserved.

### 2.4 Enrichment Cross-Contamination Guard — TODO
- **File**: `fact_check_service.py` — in `_extract_key_facts()` (line ~701)
- **What to implement**:
  1. After extracting `key_facts` list from LLM response
  2. For each fact: extract named entities (simple capitalized-word regex)
  3. Also extract entities from `texto_base`
  4. If a fact has ZERO entity overlap with `texto_base` entities → filter it out
  5. Log how many facts were filtered
- **Anti-hallucination note**: Only filter facts with ZERO overlap. Even 1 shared entity means the fact might be relevant.
- **Acceptance**: Facts about completely different entities don't leak into enrichment.

### 2.5 Enrichment Inflation Guard — TODO
- **File**: `llm_service.py` — `get_dynamic_length_requirement()` (line 260)
- **What to implement**:
  1. After the existing tier calculation, add guard:
     ```python
     source_len = len(texto_base.strip())
     if source_len < 300 and verified_chars > 0 and verified_chars > source_len * 2:
         inflation_cap = int(source_len * 5)
         capped_max = min(capped_max, max(inflation_cap, min_output))
     ```
  2. This prevents a 100-char source enriched to 3000 chars from producing a full 4000-char article
- **Anti-hallucination note**: Modify the EXISTING function, don't create a new one. The guard goes AFTER the existing expansion_cap logic.
- **Acceptance**: Short sources stay short even when heavily enriched.

### 2.6 Confidence Scoring Rebalance — TODO
- **File**: `fact_check_service.py`
- **Changes**:
  1. Weight constants (lines 49-55):
     - `WEIGHT_CLAIM_GROUNDING`: 0.40 → **0.45**
     - `WEIGHT_ENTITY_OVERLAP`: 0.25 → **0.20**
     - Others unchanged
  2. In `_compute_confidence()` (line ~1926), replace fabrication_penalty calculation:
     ```python
     # Non-linear fabrication penalty
     if fabricated_count == 1:
         fabrication_penalty = 0.30
     elif fabricated_count == 2:
         fabrication_penalty = 0.55
     elif fabricated_count >= 3:
         fabrication_penalty = 0.80
     else:
         fabrication_penalty = 0.0
     claim_score = max(0, grounded_ratio - fabrication_penalty)
     ```
     (Currently it's: `fabrication_penalty = fabricated_count / num_factual * 0.5`)
  3. In `_determine_risk_level()` (line ~2058), update:
     - 1 fabricated + score<0.50 → "high" (currently score<0.30)
- **Anti-hallucination note**: Only change the specific lines listed. The rest of `_compute_confidence` stays the same.
- **Acceptance**: Single fabrication now has 0.30 penalty (was ~0.05). Confidence for fabricated articles drops significantly.

---

## PHASE 3: SEO & Readability — PENDING

### 3.1 E-E-A-T Prompt Enforcement — TODO
- **File**: `llm_service.py` — new constant `EEAT_ENFORCEMENT` after `ATRIBUICAO_INLINE`
- **What to implement**:
  1. New constant with explicit measurable rules:
     - MINIMUM 3 source attributions using "segundo/conforme/de acordo com [Named Source]"
     - MINIMUM 2 declarations with reporting verbs "[Name] disse/afirmou/declarou"
     - MINIMUM 1 specialist title when available (economista, analista, etc.)
     - MINIMUM 2 verifiable data points with patterns ("dados mostram", "segundo pesquisa")
     - All explicitly subordinated to FIDELIDADE (from sources only)
  2. Inject after `SEO_OTIMIZACAO` in both `_build_category_prompt()` and legacy path
- **Anti-hallucination note**: These are PROMPT instructions for the LLM, not validation code. The LLM should try to include these from SOURCE material only.
- **Acceptance**: Prompt now has explicit E-E-A-T minimums. Articles should score higher on authority signals.

### 3.2 Readability Hardening — TODO
- **File**: `llm_service.py` — new constant `LEGIBILIDADE_ALVO`
- **What to implement**:
  1. New constant with:
     - Target 15 words per sentence average (was "max 20")
     - Long sentences (>20 words) max 20% of total
     - Vocabulary simplification table (consequentemente→por isso, implementacao→uso, etc.)
     - Use periods instead of semicolons
     - Explicit Flesch 60+ target
  2. Update ALL `TONS_POR_CATEGORIA` dicts: change `tamanho_frase` values to "max 18 palavras (media 12-14)"
  3. Add readability checks to SEO checklist in `build_user_prompt()` (line ~1278)
  4. Inject `LEGIBILIDADE_ALVO` into both prompt builders
- **Anti-hallucination note**: Update the EXISTING `tamanho_frase` values in TONS_POR_CATEGORIA dict entries. Don't create parallel dicts.
- **Acceptance**: Prompts enforce shorter sentences. Flesch target is explicit.

### 3.3 Post-Generation Readability Measurement — TODO
- **File**: `fact_check_service.py` — new static method `compute_readability()`
- **Also**: `generation_api.py` — call after Phase 2, add `readability` dict to response
- **What to implement**:
  1. Static method in FactCheckService:
     ```python
     @staticmethod
     def compute_readability(text: str) -> dict:
     ```
  2. Flesch-PT formula: `248.835 - 1.015*ASL - 84.6*ASY`
     - ASL = average sentence length (words per sentence)
     - ASY = average syllables per word
  3. Syllable counting: count vowel groups in Portuguese words (a,e,i,o,u + accented)
  4. Returns: `{flesch_score, avg_sentence_length, long_sentence_pct, readability_level}`
     - readability_level: "facil" (>=60), "medio" (40-59), "dificil" (<40)
  5. In `generation_api.py`: call after generation, before verification
  6. If Flesch < 50 → flag `human_review_required` with readability reason
  7. Add `readability` dict to response
- **Anti-hallucination note**: This is a deterministic computation, NOT an LLM call. Use basic regex for sentence splitting (split on `.!?`). Portuguese syllable counting: count groups of [aeiouáéíóúâêôãõ].
- **Acceptance**: Every response includes `readability` dict. Low Flesch flags for review.

### 3.4 Title & Linha Fina Precision — TODO
- **File**: `llm_service.py` — update `SEO_OTIMIZACAO` constant (starts at line ~208)
- **What to implement**:
  1. Add "CONTE os caracteres ANTES de finalizar" instruction
  2. Title: "EXATAMENTE 50-60 caracteres (se >60, CORTE)"
  3. Linha fina: "EXATAMENTE 150-160 caracteres, DEVE terminar com CTA + pontuacao"
- **Anti-hallucination note**: Modify the EXISTING `SEO_OTIMIZACAO` constant. Don't create a new one.
- **Acceptance**: Updated prompt instructs character counting before finalizing.

### 3.5 Content Length Enforcement — TODO
- **File**: `llm_service.py` — `build_user_prompt()` (line ~1298)
- **Also**: `generation_api.py` — after generation
- **What to implement**:
  1. In `build_user_prompt()`: strengthen length instruction from soft to hard:
     "ARTIGOS abaixo de {min_chars} caracteres serao REJEITADOS. Atinja o alvo."
  2. In `generation_api.py`: if article < 70% of min_chars, add `seo_quality.length_warning` to result
- **Acceptance**: Prompt is more forceful about length. Under-length articles get a warning field.

### 3.6 Slug Generation — TODO
- **File**: `llm_service.py` — JSON output format + `SEO_OTIMIZACAO`
- **What to implement**:
  1. `slug_sugerido` field already added to JSON output spec (done in 2.2) — VERIFY it's in both paths
  2. Add slug instruction to `SEO_OTIMIZACAO`: "slug_sugerido: 3-6 palavras separadas por hifen, sem acentos, minusculo"
  3. In `llm_service.py` `generate_article()`: ensure `slug_sugerido` is preserved in result (add fallback if missing)
- **Anti-hallucination note**: The JSON format was already updated in Phase 2.2. Just add the instruction text and handle the field in generate_article().
- **Acceptance**: Response includes `slug_sugerido` field. Slug follows format rules.

---

## PHASE 4: Architecture Hardening — PENDING

### 4.1 Request Correlation Propagation — TODO
- **Files**: `generation_api.py`, `llm_service.py`, `fact_check_service.py`
- **What to implement**:
  1. Add `correlation_id: str = ""` parameter to:
     - `LLMService.generate_article()` (line 1437)
     - `LLMService._call_api()` (line 1377)
     - `FactCheckService.enrich_context()` (line 397)
     - `FactCheckService.verify_article()` (line 821)
  2. Prefix all log messages in those methods with `[{correlation_id}]`
  3. Pass `correlation_id` from `generate_article_handler()` to all service calls
  4. Pass as `X-Correlation-ID` header in `_call_api()` and `_search_exa()`
- **Anti-hallucination note**: `correlation_id` already exists in `generate_article_handler()` (line 317). Just propagate it downstream.
- **Acceptance**: Any request can be traced through enrichment→generation→verification via correlation_id.

### 4.2 Hardcoded CORS & DB Defaults Removal — TODO
- **Files**: `function_app.py` (lines 27-32), `database.py` (lines 32-33)
- **What to implement**:
  1. `function_app.py`: Read `CORS_ALLOWED_ORIGINS` env var (comma-separated), fall back to current list
     ```python
     _cors_env = os.environ.get("CORS_ALLOWED_ORIGINS", "")
     ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else [
         "http://localhost:5173", "http://localhost:3000",
         "https://purple-river-09235a310.azurestaticapps.net",
         "https://purple-river-09235a310.3.azurestaticapps.net",
     ]
     ```
  2. `database.py`: Remove hardcoded default `'bi4ia-tmc.database.windows.net'` for SQL_SERVER.
     If SQL_SERVER not set → raise ValueError at init time.
- **Anti-hallucination note**: Keep the fallback list for CORS (backwards compat). Only DB should fail explicitly.
- **Acceptance**: CORS is configurable via env. Missing SQL_SERVER fails fast.

### 4.3 Audit Trail Error Severity — TODO
- **File**: `generation_api.py` (lines ~620-635)
- **What to implement**: Change `logger.warning` to `logger.error` with `exc_info=True` for audit persist failures:
  ```python
  # Line ~631 (timeout)
  logger.error(f"[{correlation_id}] Audit persist timed out after 2s", exc_info=True)
  # Line ~633 (exception)
  logger.error(f"[{correlation_id}] Audit persist failed: {e}", exc_info=True)
  ```
- **Acceptance**: Audit failures appear as ERROR level in Application Insights.

### 4.4 Verification Failure Escalation — TODO
- **File**: `generation_api.py` (lines ~518-530)
- **What to implement**:
  1. Change `logger.warning` to `logger.error` when Phase 3 verification fails
  2. Add `pipeline_error: True` flag to verification fallback dict
- **Acceptance**: Verification failures are ERROR level. Response includes `pipeline_error` flag.

### 4.5 Enhanced Health Check — TODO
- **File**: `functions/health.py`
- **What to implement**:
  1. Import LLM and FactCheck services (try/except)
  2. Check LLM circuit breaker: `_llm_circuit_open` attribute
  3. Check Exa circuit breaker: `_exa_circuit_open` attribute
  4. Return `degraded` when any circuit breaker is open
  5. Return `unhealthy` when DB is down
  6. Add `llm_status`, `exa_status` fields to response
- **Anti-hallucination note**: Access circuit breaker state via the singleton instances. Don't create new health check methods on the services.
- **Acceptance**: `/api/health` returns circuit breaker status. Degraded state visible.

### 4.6 In-Process Metrics — TODO
- **File**: `services/metrics.py` — **NEW FILE**
- **Also**: `function_app.py` — new `/api/metrics` endpoint
- **What to implement**:
  1. Thread-safe `Metrics` singleton class
  2. `counter(name)` — increment a counter
  3. `histogram(name, value)` — record a timing/value (rolling window of 1000)
  4. `get_all()` → dict with all counters and histogram summaries (min/max/avg/p50/p99)
  5. Instrument in `generation_api.py`:
     - `generation.requests` counter
     - `generation.total_ms` histogram
     - `generation.blocked` counter
1 refills based on elapsed time.
- **Acceptance**: Rapid successive calls to `/api/generate` get 429 after burst exhausted.

### 4.9 Centralized Configuration — TODO
- **File**: `services/config.py` — **NEW FILE**
- **What to implement**:
  1. Frozen `@dataclass` `AppConfig` with all env vars as typed fields
  2. `get_config() -> AppConfig` thread-safe singleton
  3. Validates required vars at startup: `SQL_PASSWORD`, at least one of `AZURE_AI_API_KEY`/`ANTHROPIC_API_KEY`
  4. Logs all non-secret config values at startup
  5. DO NOT replace existing os.environ.get() calls yet — this is foundational. Incremental migration later.
- **Anti-hallucination note**: This is a FOUNDATIONAL file. Don't try to replace all 37+ os.environ.get() calls in one shot. Just create the config class and validate required vars.
- **Acceptance**: Config loads at import time. Missing required vars raise ValueError with clear message.

---

## PHASE 5: Editorial Workflow Backend — PENDING

### 5.1 Publication Status in API Response — TODO
- **File**: `generation_api.py` — before response (after safety gates)
- **What to implement**:
  1. Derive `publication_status` from safety gates + confidence:
     - `publish_blocked=True` → "blocked"
     - `human_review_required=True` → "draft_review"
     - confidence >= 0.70 → "ready_for_review"
     - else → "draft"
  2. Add `can_auto_publish: False` (always false — conservative default)
  3. Add both fields to response
- **Acceptance**: Response includes `publication_status` and `can_auto_publish` fields.

### 5.2 Quality Summary Logging — TODO
- **File**: `generation_api.py` — before response
- **What to implement**:
  1. Structured JSON log line with prefix `[QUALITY_SUMMARY]`:
     ```python
     logger.info(f"[QUALITY_SUMMARY] {json.dumps({
         'correlation_id': correlation_id,
         'confidence': confidence_score,
         'risk_level': risk_level,
         'fabricated_claims': fabricated_claims,
         'publish_blocked': publish_blocked,
         'publication_status': publication_status,
         'total_ms': total_ms,
         'categoria': categoria,
     })}")
     ```
  2. Enables queries like "How many articles had >1 fabrication this week?"
- **Acceptance**: Every generation request logs a structured quality summary line.

---

## Implementation Order & Dependencies

```
Phase 1 (DONE) ──┐
                  ├─→ Phase 2 (IN PROGRESS)
                  │     2.1 (auto-regen) depends on verification working
                  │     2.2 (attribution) DONE
                  │     2.3 (decontamination) independent
                  │     2.4 (cross-contamination) independent
                  │     2.5 (inflation guard) independent
                  │     2.6 (confidence rebalance) independent
                  │
                  ├─→ Phase 3 (after Phase 2)
                  │     3.1 (E-E-A-T) independent
                  │     3.2 (readability) independent
                  │     3.3 (readability measurement) independent
                  │     3.4 (title precision) independent
                  │     3.5 (length enforcement) independent
                  │     3.6 (slug) depends on 2.2 (JSON format already updated)
                  │
                  ├─→ Phase 4 (independent of 2/3, can parallelize)
                  │     4.1-4.4 can be done in parallel
                  │     4.5 depends on knowing circuit breaker attributes
                  │     4.6 (metrics) independent
                  │     4.7 independent
                  │     4.8 (rate limiter) independent
                  │     4.9 (config) independent, foundational
                  │
                  └─→ Phase 5 (after Phase 2 safety gates)
                        5.1 depends on safety gates working
                        5.2 independent
```

---

## Verification Checklist

- [ ] After Phase 2: Run `pytest tests/ -v` — all 227+ tests pass
- [ ] After Phase 2: Manually test with short source (<100 chars) → expect 422
- [ ] After Phase 2: Manually test with source 100-149 chars → expect nota forced
- [ ] After Phase 3: Verify `readability` dict appears in /api/generate response
- [ ] After Phase 3: Verify `slug_sugerido` field appears in response
- [ ] After Phase 4: `GET /api/health` returns circuit breaker status
- [ ] After Phase 4: `GET /api/metrics` returns counters
- [ ] After Phase 4: Rapid calls to /api/generate get 429 after burst
- [ ] After Phase 5: Response includes `publication_status` field
- [ ] Final: Run audit script — fabrication <1%, SEO avg >70
