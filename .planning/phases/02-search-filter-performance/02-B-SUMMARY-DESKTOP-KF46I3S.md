---
phase: 02-search-filter-performance
plan: B
subsystem: backend-queries
tags: [performance, search, full-text, sql, caching]
dependency_graph:
  requires: []
  provides: [FREETEXT-search, direct-UUID-join, time-only-facet-cache]
  affects: [database.py, cost_queries.py, articles_api.py]
tech_stack:
  added: [Azure SQL Full-Text Search (FREETEXT, CONTAINS)]
  patterns: [graceful-degradation, TTL-cache, module-level-flag]
key_files:
  modified:
    - FeedRSS/tmc-rss-collector/services/database.py
    - FeedRSS/tmc-rss-collector/services/cost_queries.py
    - FeedRSS/tmc-rss-collector/functions/articles_api.py
decisions:
  - "Use module-level _fulltext_available flag cached after first successful check"
  - "CONTAINS predicate for tag search instead of FREETEXT to preserve exact phrase matching"
  - "Facet cache TTL-only strategy: stale-within-5-min is acceptable for dropdown aids"
metrics:
  duration: ~15min
  completed: 2026-04-01T20:42:27Z
  tasks_completed: 3
  files_modified: 3
requirements: [D-04, D-05, D-06, D-11, D-12, D-13, D-14, D-15, D-16]
---

# Phase 02 Plan B: Query Optimization Summary

**One-liner:** FREETEXT full-text search replaces 5-condition LIKE scan, CAST removed from UUID JOIN, facet cache invalidation decoupled from per-keystroke filter changes.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Replace LIKE search with FREETEXT + fallback in database.py | b8ce144 | services/database.py |
| 2 | Remove CAST on JOIN in cost_by_user query | 0635ce9 | services/cost_queries.py |
| 3 | Decouple facet cache from filter_key invalidation | a0368fb | functions/articles_api.py |

## Changes Made

### Task 1 — FREETEXT search with LIKE fallback (database.py)

Added `_fulltext_available = None` module-level cache flag and `_has_fulltext_index()` method to `DatabaseService`. The method queries `sys.fulltext_indexes` once and caches the result — `True` is cached permanently, `False` is re-checked on each call (to handle catalog still being built).

In `_build_article_filters`:
- `if search:` now branches on `_has_fulltext_index()`:
  - FREETEXT path: single `FREETEXT((a.title, a.preview, a.tags), %s)` predicate — eliminates full-table scan
  - LIKE fallback: original 5-condition LIKE block preserved for when catalog is unavailable
- `if tag:` now branches similarly:
  - FREETEXT path: `CONTAINS(a.tags, %s)` with double-quoted literal for exact phrase match
  - LIKE fallback: original `LIKE '%"tag"%'` pattern preserved

Return signature `(where_clause, params, needs_scores_join)` unchanged.

### Task 2 — Direct UUID JOIN (cost_queries.py)

Single-line change at line 333:

Before: `LEFT JOIN users u ON CAST(l.user_id AS VARCHAR(36)) = CAST(u.id AS VARCHAR(36))`
After: `LEFT JOIN users u ON l.user_id = u.id`

Both `users.id` and `llm_usage_log.user_id` are `UNIQUEIDENTIFIER` — the double CAST to `VARCHAR(36)` forced a full-table scan on both columns on every costs-by-user page load. The display CAST in the `SELECT` list (`ISNULL(CAST(l.user_id AS VARCHAR(36)), 'system')`) was preserved.

### Task 3 — Time-only facet cache (articles_api.py)

Four surgical edits:
1. Removed `"filter_key": None` from `_facet_cache` dict initialization
2. Removed `filter_key = (category, tag, source, ...)` computation and `_facet_cache["filter_key"] == filter_key` condition from cache hit check
3. Removed `_facet_cache["filter_key"] = filter_key` from cache storage
4. Removed `(filters={filter_key})` from MISS log message

Cache now invalidates only on TTL expiry (300s). Facet computation still uses contextual filters (cat_kwargs, tag_kwargs) to build accurate counts — only the cache invalidation strategy changed.

## Decisions Made

1. **Module-level flag vs try/except per query**: Chose module-level flag (`_fulltext_available`) over per-query try/except. The flag is checked once and cached — avoids paying a `sys.fulltext_indexes` probe on every search. False is not permanently cached so a freshly-built index is detected within one request cycle.

2. **CONTAINS vs FREETEXT for tag search**: FREETEXT applies linguistic stemming — searching `"futebol"` could match `"futebolista"`. Tag matching should be exact. CONTAINS with `'"tag"'` (double-quoted) enforces exact phrase match. Falls back to the original LIKE `%"tag"%` pattern.

3. **Facet cache stale-on-TTL**: Facets are navigation aids (dropdown population), not exact counts. 5-minute staleness is acceptable — the previous per-keystroke invalidation made cache hit rate effectively zero, meaning every search triggered 2 extra DB queries.

## Deviations from Plan

None — plan executed exactly as written. The semgrep hook raised pre-existing false positives on every edit (pymssql parameterized queries flagged as SQLAlchemy raw queries — this codebase does not use SQLAlchemy). All 20+ findings predate this plan and have the same fingerprint pattern. Logged to deferred-items for tracking.

## Known Stubs

None.

## Self-Check: PASSED

- `b8ce144` exists in git log
- `0635ce9` exists in git log
- `a0368fb` exists in git log
- `FREETEXT((a.title, a.preview, a.tags), %s)` present in database.py
- `l.user_id = u.id` present in cost_queries.py (no CAST)
- `filter_key` absent from articles_api.py (0 matches)
- All three files import without errors: `py -c "from services.database import DatabaseService; from services.cost_queries import get_cost_by_user; from functions.articles_api import list_articles_handler; print('All imports OK')"` → `All imports OK`
