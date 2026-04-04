# Phase 2: Search/Filter Performance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 02-search-filter-performance
**Areas discussed:** Full-text search approach, LIKE fallback, Facet cache decoupling, Frontend debounce/abort, CAST fix on JOIN, Index strategy
**Mode:** --auto (all decisions auto-selected)

---

## Full-Text Search Approach

| Option | Description | Selected |
|--------|-------------|----------|
| FREETEXT | Simple word-based search, Portuguese word breaker handles compounds | auto |
| CONTAINS | Boolean operators, proximity search, more control | |

**User's choice:** [auto] FREETEXT — recommended default. Simpler, handles "seleção brasileira" natively.
**Notes:** Plan already specified FREETEXT. Language 1046 (Brazilian Portuguese) provides native word-breaking.

---

## LIKE Fallback Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful fallback | Try FREETEXT, fall back to LIKE if catalog not ready | auto |
| Hard requirement | Require full-text index, fail if not available | |
| Feature flag | ENV var to toggle between FREETEXT and LIKE | |

**User's choice:** [auto] Graceful fallback — recommended for migration safety.
**Notes:** Allows deploying code before index finishes building. Critical for zero-downtime deployment.

---

## Facet Cache Decoupling

| Option | Description | Selected |
|--------|-------------|----------|
| Time-only TTL | Drop filter_key, use 5-min TTL only | auto |
| Reduced key | Remove only search from cache key, keep other filters | |
| Background refresh | Refresh facets on timer, serve stale during refresh | |

**User's choice:** [auto] Time-only TTL — recommended. Facet counts are approximate, don't need per-query freshness.
**Notes:** FACET_CACHE_TTL=300 already correct. Only change: remove filter_key check at articles_api.py:111.

---

## Frontend Debounce/Abort

| Option | Description | Selected |
|--------|-------------|----------|
| 500ms FilterBar | Increase FilterBar debounce from 300ms to 500ms | auto |
| 300ms (keep) | Keep current debounce, rely on AbortController | |
| 400ms compromise | Split the difference | |

**User's choice:** [auto] 500ms FilterBar — matches plan specification.
**Notes:** AbortController already exists in RedacaoPage.jsx:77. No new abort logic needed. Separate 150ms fetch debounce stays.

---

## CAST Fix on JOIN

| Option | Description | Selected |
|--------|-------------|----------|
| Remove CASTs | Both columns are UNIQUEIDENTIFIER, just join directly | auto |
| Computed column | Add persisted computed column for indexed joins | |

**User's choice:** [auto] Remove CASTs — confirmed both columns are same type (UNIQUEIDENTIFIER).
**Notes:** Verified in migrations 005 (users.id) and 017 (llm_usage_log.user_id). Pure fix, no migration needed.

---

## Index Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Covering indexes | INCLUDE columns to avoid key lookups | auto |
| Minimal indexes | Key columns only, smaller storage | |

**User's choice:** [auto] Covering indexes — plan specifies INCLUDE columns for cost queries.
**Notes:** Migration 022. Covering index trades storage for faster reads — correct for read-heavy analytics page.

---

## Claude's Discretion

- ONLINE=ON for index creation (depends on Azure SQL tier)
- api_usage_log index (D-10) — depends on table size analysis
- FREETEXT fallback implementation approach (try/except vs pre-check)
- Whether 150ms RedacaoPage debounce needs adjustment

## Deferred Ideas

- Cost query parallelization with asyncio.gather()
- Costs page default filter "today" (P2 backlog item)
- CONTAINS-based advanced search (future P1)
