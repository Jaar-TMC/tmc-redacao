# Phase 10: Infrastructure - Context

**Gathered:** 2026-04-04
**Status:** Partially implemented (INFRA-02, INFRA-03, INFRA-04, INFRA-05 done; INFRA-01, INFRA-06 deferred)

<domain>
## Phase Boundary

Eliminate cold starts, reduce dependency bloat, and tune connection pool to achieve <2s first-request latency (down from 8-15s on Consumption Plan).

</domain>

<decisions>
## Implementation Decisions

### Hosting Plan (INFRA-01) — DEFERRED
- **D-01:** User chose to defer hosting plan migration (Flex Consumption vs Premium EP1) to a later phase. Cost decision (~$100-150/mo increase) to be revisited separately.

### numpy Replacement (INFRA-02) — IMPLEMENTED
- **D-02:** Replace module-level `import numpy` with pure-Python math for hot paths (cosine similarity, normalize, EMA centroid). Keep numpy as lazy import only inside silhouette score functions (daily 3AM maintenance timer).
- **D-03:** numpy stays in `requirements.txt` for the lazy silhouette import. Cold start savings come from avoiding the 500ms import during function initialization.

### Dependency Cleanup (INFRA-03) — IMPLEMENTED
- **D-04:** Remove `nest-asyncio` from requirements.txt (no longer used after INFRA-05).
- **D-05:** Remove `google-auth` from requirements.txt. Gemini integration is dormant and gated behind config flags. All google-auth imports are lazy (inside methods). Re-adding the dependency is a one-line change if needed.

### Connection Pool (INFRA-04) — ALREADY DONE
- **D-06:** `SQL_POOL_SIZE` defaults to 5 (Consumption/Flex plan). Implemented in prior phase.

### nest_asyncio Removal (INFRA-05) — IMPLEMENTED
- **D-07:** Replace `nest_asyncio.apply()` + `asyncio.run()` anti-pattern with `ThreadPoolExecutor(max_workers=1)` pattern. When a running event loop is detected, the sync wrapper spawns a single-worker thread with its own event loop to avoid nested loop issues.
- **D-08:** Applied to all 4 services: `scoring_service.py`, `event_signature_service.py`, `llm_service.py`, `llm_verification_service.py`.

### Region Verification (INFRA-06) — DEFERRED
- **D-09:** Azure SQL region verification deferred to hosting plan migration phase (needs Azure portal/CLI check).

### Claude's Discretion
- Pure-Python math implementation details (list comprehensions, math.sqrt)
- ThreadPoolExecutor pattern for sync-from-async wrappers

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Performance Plan
- `docs/plans/2026-04-02-performance-optimization-plan.md` §271-304 — Phase 5 (Infrastructure) requirements and recommendations

### Requirements
- `.planning/REQUIREMENTS.md` §INFRA-01 through INFRA-06 — Infrastructure requirements

### Modified Files
- `FeedRSS/tmc-rss-collector/services/clustering_service.py` — Pure-Python cosine_similarity, normalize_vector, EMA centroid
- `FeedRSS/tmc-rss-collector/services/scoring_service.py` — ThreadPoolExecutor sync wrapper
- `FeedRSS/tmc-rss-collector/services/event_signature_service.py` — ThreadPoolExecutor sync wrapper
- `FeedRSS/tmc-rss-collector/services/llm_service.py` — ThreadPoolExecutor sync wrapper
- `FeedRSS/tmc-rss-collector/services/llm_verification_service.py` — ThreadPoolExecutor sync wrapper

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `fact_check_service.py:2378-2384` — Already had pure-Python `_cosine_sim()` as reference implementation
- `async_db.py:run_db()` — Established `run_in_executor` pattern for sync→async bridging
- `ConnectionPool` class in `database.py` — Already configured with `SQL_POOL_SIZE=5` default

### Established Patterns
- Lazy imports inside functions for heavy dependencies (sklearn in silhouette)
- ThreadPoolExecutor for running sync code in async context
- Config-gated feature flags (Gemini behind env vars)

### Integration Points
- All 4 sync wrappers use the same ThreadPoolExecutor pattern
- Pure-Python cosine_similarity is public API from clustering_service (imported by event_matching_service)

</code_context>

<specifics>
## Specific Ideas

- The pure-Python `sum(a * b for a, b in zip(vec1, vec2))` is performant enough for 1536-dim vectors (microseconds per call)
- Silhouette score uses numpy matrix multiplication for pairwise distances — too complex for pure Python, kept as lazy import
- ThreadPoolExecutor with `max_workers=1` ensures no parallel async.run() calls from same sync wrapper

</specifics>

<deferred>
## Deferred Ideas

- **INFRA-01 (Hosting plan migration)** — Flex Consumption vs Premium EP1 cost decision. User wants to handle separately.
- **INFRA-06 (Region verification)** — Azure SQL region check, best done alongside hosting plan migration.
- **Gemini service cleanup** — Service file left in place but dormant. Could be fully removed if Gemini is permanently abandoned.

</deferred>

---

*Phase: 10-infrastructure*
*Context gathered: 2026-04-04*
