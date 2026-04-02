# Phase 4: Fact-Check Accuracy - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Add temporal awareness to the fact-check pipeline so breaking news articles aren't hard-blocked as "unverifiable." Currently, claim verification treats a 15-minute-old breaking story identically to a 3-day-old follow-up — both get the same static thresholds, and breaking news with sparse corroboration gets wrongly rejected.

**2 parallel implementation tracks (both edit `fact_check_service.py` in different sections):**
- Track A (Enrichment): Temporal claim classification + date-scoped Exa queries
- Track B (Verification): Embedding cross-reference + temporal CoVe + softer confidence for `recent_unverifiable`

</domain>

<decisions>
## Implementation Decisions

### Temporal Thresholds (Task 4.1)
- **D-01:** Three temporal tiers: `breaking` (<48h), `recent` (48h-7d), `historico` (>7d). These map to claim extraction prompt additions.
- **D-02:** Thresholds MUST be env vars for editorial tuning: `TEMPORAL_BREAKING_HOURS=48` (default), `TEMPORAL_RECENT_DAYS=7` (default). Load via `config.py` AppConfig frozen dataclass, same pattern as existing env vars.
- **D-03:** Temporal classification added to claim extraction prompt at `fact_check_service.py:1468-1577`. Each claim gets a `temporalidade` field: `breaking`, `recente`, or `historico`.

### Date-Scoped Exa Queries (Task 4.2)
- **D-04:** Pass article's `published_at` to enrichment step at `fact_check_service.py:710-721`.
- **D-05:** Exa search date ranges by temporal tier: `breaking` claims → last 48h only; `recente` → last 7d; `historico` → standard date range (existing behavior).
- **D-06:** Recency boost: prioritize Exa results closest to article publication date.

### Embedding Cross-Reference (Task 4.3)
- **D-07:** Implement internal cross-reference using existing `article_embeddings` table. This is the PRIMARY verification mechanism for breaking news — runs BEFORE Exa.
- **D-08:** Threshold: cosine similarity > 0.7, 3+ independent collected articles reporting same claim = confidence boost (treat as `grounded`).
- **D-09:** For `breaking` claims: if embedding cross-reference confirms → mark as `grounded`, skip Exa for that claim (saves cost + latency).
- **D-10:** For `recente` claims: embedding cross-reference boosts confidence but still runs Exa for enrichment.
- **D-11:** Cost: FREE — no API calls, uses existing embedding infrastructure.

### Confidence Adjustments (Task 4.5)
- **D-12:** New verdict type `recent_unverifiable` with confidence weight 0.7 (vs 0.35 for standard `unverifiable`). Only applies when source < 48h AND claim lacks corroboration.
- **D-13:** CRITICAL: Exclude `recent_unverifiable` from the hard block count at `generation_api.py:350-354`. Only standard `unverifiable` triggers the `>=3 AND ratio >40%` block. Breaking news must never be blocked because its claims are too new to verify.
- **D-14:** `fabricated` claims STILL hard-block regardless of temporal status. Temporal awareness relaxes "unverifiable," never "fabricated."
- **D-15:** Breaking news articles with `recent_unverifiable` claims → publication status `review` (not `published`). Editor must eyeball before publication. Standard newsroom practice.

### Temporal CoVe (Task 4.4)
- **D-16:** Add temporal question to CoVe Q&A at `fact_check_service.py:2242-2343`: "Quando este evento foi reportado? A informacao e atual (ultimas 48h) ou contexto historico?"
- **D-17:** CoVe temporal answer informs whether to apply `recent_unverifiable` vs standard `unverifiable` classification.

### Rollout Strategy
- **D-18:** Ship directly with feature flag `TEMPORAL_AWARENESS_ENABLED=true` (default ON, env var). No logging-only phase — the current behavior is the bug (wrongly blocking breaking news).
- **D-19:** Feature flag allows instant revert: set env var to `false` if fabrication rate spikes post-deploy.
- **D-20:** Monitor `generation_audit_trail` for 48h post-deploy. Success metric: breaking news articles that were previously blocked now pass with `review` status, no increase in fabrication rate.

### Claude's Discretion
- Exact embedding query implementation (SQL vs Python cosine computation)
- Whether to log temporal classification distribution for operational insight (useful but not blocking)
- Exact wording of CoVe temporal question (D-16) — optimize through testing
- Whether embedding cross-reference should use a new method or extend `_extract_and_verify_claims()`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Plan
- `docs/plans/2026-04-01-p0-implementation-plan.md` §Phase 4 (lines 359-448) — Full task breakdown with line numbers, verification checklist, 2-track parallel structure

### Backlog
- `docs/backlog-prioritizado-abril-2026.md` — "Fact-check nao reconhece informacoes novas" P0 bug description

### Backend — Fact-Check Pipeline (Track A: enrichment)
- `FeedRSS/tmc-rss-collector/services/fact_check_service.py:500-621` — Enrichment section, Exa result handling (where date-scoping goes)
- `FeedRSS/tmc-rss-collector/services/fact_check_service.py:710-721` — Exa search query construction (where `published_at` passthrough goes)
- `FeedRSS/tmc-rss-collector/services/fact_check_service.py:784-788` — Current global date range for Exa (root cause)

### Backend — Fact-Check Pipeline (Track B: verification)
- `FeedRSS/tmc-rss-collector/services/fact_check_service.py:1152-1415` — `verify_article()` main flow
- `FeedRSS/tmc-rss-collector/services/fact_check_service.py:1424-1528` — `_extract_and_verify_claims()` + claim classification prompt (where temporal field goes)
- `FeedRSS/tmc-rss-collector/services/fact_check_service.py:2242-2343` — CoVe verification (where temporal question goes)
- `FeedRSS/tmc-rss-collector/services/fact_check_service.py:2349-2430` — `_compute_confidence()` weights (where `recent_unverifiable` weight goes)

### Backend — Safety Gates
- `FeedRSS/tmc-rss-collector/functions/generation_api.py:237-410` — `evaluate_safety_gates()` — hard block logic (where `recent_unverifiable` exclusion goes)

### Backend — Config
- `FeedRSS/tmc-rss-collector/services/config.py:41-167` — AppConfig frozen dataclass, env var loading (where temporal env vars go)

### Backend — Embeddings (for cross-reference)
- `FeedRSS/tmc-rss-collector/services/embedding_service.py` — Existing embedding infrastructure
- `FeedRSS/tmc-rss-collector/services/database.py` — `article_embeddings` table CRUD

### Prior Phase Context
- `.planning/phases/03-text-quality/03-CONTEXT.md` — Phase 3 established claim extraction retry (D-15/D-16), quality criteria pattern, env var config pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `article_embeddings` table + `embedding_service.py` — existing 1536-dim vectors for all collected articles. Can query for cosine similarity without any new infrastructure.
- `_extract_and_verify_claims()` at `fact_check_service.py:1424` — already extracts claims with structured JSON. Adding `temporalidade` field is additive.
- `_compute_confidence()` at `fact_check_service.py:2349` — weighted scoring already handles multiple verdict types. Adding `recent_unverifiable` follows established pattern.
- `evaluate_safety_gates()` at `generation_api.py:237` — already counts `unverifiable_claims` separately. Splitting into `recent_unverifiable` vs `standard_unverifiable` is a targeted change.
- `decontaminate_article()` at `fact_check_service.py:242` — already does temporal decontamination (removes invented temporal details). Adjacent concern, no conflict.
- `AppConfig` at `config.py` — frozen dataclass with `_bool_env`/`_float_env` helpers for env var loading.

### Established Patterns
- Claim verdicts: `grounded | fabricated | unverifiable | inaccurate | opinion | context` — adding `recent_unverifiable` follows same structure
- Env var config: `SCREAMING_SNAKE_CASE` loaded in `AppConfig.__init__()`, accessed via `get_config().attribute`
- LLM prompts: Portuguese instructions in prompt constants at top of `fact_check_service.py`
- Error handling: `logger.warning()` + metadata flags for soft failures
- Confidence weights: Currently claims=0.40, entities=0.25, expansion=0.10, quotes=0.10, sufficiency=0.10, similarity=0.05

### Integration Points
- Temporal classification: Extends claim extraction prompt (additive to existing JSON structure)
- Date-scoped Exa: Modifies `enrich_context()` Exa query parameters (isolated to enrichment section)
- Embedding cross-reference: New method in `fact_check_service.py`, called before Exa in verification flow
- Safety gate exclusion: Targeted change to `unverifiable_claims` count logic in `generation_api.py`
- Both tracks edit `fact_check_service.py` in DIFFERENT sections — safe for parallel execution if merge is careful

</code_context>

<specifics>
## Specific Ideas

- Embedding cross-reference is the highest-value change — multiple RSS sources confirming the same claim IS verification in newsroom terms. Prioritize this.
- The `published_at` field is already available on `collected_articles` — no new data pipeline needed.
- `recent_unverifiable` weight of 0.7 means a breaking news article with 3 `recent_unverifiable` claims out of 10 total would score ~0.79 claim component (vs ~0.47 if they were standard `unverifiable`). This passes the 0.65 confidence floor.
- Feature flag `TEMPORAL_AWARENESS_ENABLED` should gate the entire temporal pipeline — when OFF, all behavior reverts to pre-Phase-4 (static thresholds, no temporal classification).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-fact-check-accuracy*
*Context gathered: 2026-04-02*
