---
phase: 09-keyset-pagination
plan: 01
subsystem: backend-pagination
tags: [keyset-pagination, cursor, database, api, performance]
dependency_graph:
  requires: []
  provides: [encode_cursor, decode_cursor, keyset-seek-predicate, cursor-api-response]
  affects: [database.py, articles_api.py]
tech_stack:
  added: [base64-cursor-encoding]
  patterns: [keyset-seek, dual-mode-pagination, filter-only-count]
key_files:
  created:
    - FeedRSS/tmc-rss-collector/tests/test_keyset_pagination.py
  modified:
    - FeedRSS/tmc-rss-collector/services/database.py
    - FeedRSS/tmc-rss-collector/functions/articles_api.py
decisions:
  - Cursor format uses base64url-encoded "published_at|id" string (opaque to frontend)
  - COUNT query separated from data query in cursor path so total/pages remain stable
  - Score-ordered queries always use OFFSET (PAG-03) since score is not monotonic
  - Backward seek reverses ORDER BY to ASC then reverses result list for consistent DESC display
  - Top-level imports for encode_cursor/decode_cursor in articles_api.py (avoids reload issues)
metrics:
  duration: 9m8s
  completed: 2026-04-02
  tasks_completed: 2
  tasks_total: 2
  tests_added: 15
  files_modified: 3
---

# Phase 09 Plan 01: Backend Keyset Pagination Summary

Keyset (cursor-based) pagination on GET /api/articles with base64 opaque cursors, dual-mode query switching, and stable total/pages counts via filter-only COUNT.

## What Was Done

### Task 1: Cursor encode/decode + seek predicate in database.py (d835049)

Added module-level `encode_cursor(published_at, article_id)` and `decode_cursor(cursor_str)` functions that produce/parse opaque base64url tokens in the format `{iso_datetime}|{uuid}`.

Extended `_build_article_filters` with three new parameters (`cursor_published_at`, `cursor_id`, `cursor_direction`) that append keyset seek predicates:
- Forward: `(a.published_at < %s OR (a.published_at = %s AND a.id < %s))`
- Backward: `(a.published_at > %s OR (a.published_at = %s AND a.id > %s))`

Refactored `get_articles_with_urgency` with dual-mode pagination:
- **Cursor path**: Calls `_build_article_filters` twice -- once without cursor (filter-only WHERE for COUNT) and once with cursor (seek WHERE for data). Runs separate `SELECT COUNT(*)` for stable total/pages. Uses `FETCH NEXT %s ROWS ONLY` without OFFSET.
- **OFFSET path**: Unchanged behavior with `COUNT(*) OVER()` window function.
- Added `a.id DESC` to default ORDER BY for deterministic keyset ordering.
- Backward cursor reverses ORDER BY to ASC, then `articles.reverse()` for consistent DESC display.

Created 11 unit tests covering: roundtrip encode/decode, invalid base64, invalid format, forward/backward seek predicates, combined category+cursor filters, no-seek-without-cursor, score-order-skips-cursor, no-duplicates guarantee, backward seek order reversal.

### Task 2: Cursor parsing and response fields in articles_api.py (9eb6693)

Wired cursor support into `list_articles_handler`:
- Parses `cursor` and `cursor_direction` query params
- Invalid cursors silently fall back to page=1 with warning log
- Passes `cursor_data` and `cursor_direction` to `get_articles_with_urgency`
- Builds `nextCursor` (from last article, only when page is full) and `prevCursor` (from first article, only when not on first page)
- Score-ordered queries return null cursors (PAG-03)
- Response now includes `"nextCursor"` and `"prevCursor"` fields

Added 4 API-level tests: nextCursor encoding, prevCursor encoding, null cursor on last page, null cursors for score order.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mock rows needed valid UUIDs**
- **Found during:** Task 1, test 10 (backward seek order)
- **Issue:** Mock article rows used string IDs like "id-1" which fail Pydantic UUID validation
- **Fix:** Changed to valid UUID format "550e8400-e29b-41d4-a716-44665544000X"
- **Files modified:** tests/test_keyset_pagination.py
- **Commit:** d835049

**2. [Rule 1 - Bug] Top-level import to avoid module reload interference**
- **Found during:** Task 2, full test suite verification
- **Issue:** Inline `from services.database import decode_cursor` inside function body caused `importlib.reload(api_mod)` in existing test_phase2_performance.py to produce different module state
- **Fix:** Moved encode_cursor/decode_cursor imports to top-level `from services.database import get_db, encode_cursor, decode_cursor`
- **Files modified:** functions/articles_api.py
- **Commit:** 9eb6693

## Deferred Issues

**test_facet_cache_has_required_keys** in `test_phase2_performance.py` fails because pre-existing uncommitted changes from phases 05-07 changed `_facet_cache` from a dict with default keys to an empty dict `{}`. The test expects keys `{"categories", "tags", "timestamp"}` but the current module-level `_facet_cache = {}` starts empty. This is NOT caused by Plan 09-01 changes. Logged for resolution in a future phase.

## Verification Results

- 15/15 keyset pagination tests pass
- 526/527 total tests pass (1 pre-existing failure unrelated to this plan)
- `database.py` contains `encode_cursor` and `decode_cursor` module-level functions
- `_build_article_filters` accepts and processes cursor seek predicates (forward and backward)
- `get_articles_with_urgency` calls `_build_article_filters` twice in cursor mode
- `get_articles_with_urgency` runs separate `SELECT COUNT(*)` with filter-only WHERE in cursor mode
- `total` and `pages` remain stable across cursor-navigated pages
- `list_articles_handler` response includes `nextCursor` and `prevCursor` fields
- Score-ordered queries always use OFFSET, cursor fields are null

## Known Stubs

None -- all functionality is fully wired and operational.

## Self-Check: PASSED

- FOUND: FeedRSS/tmc-rss-collector/tests/test_keyset_pagination.py
- FOUND: FeedRSS/tmc-rss-collector/services/database.py
- FOUND: FeedRSS/tmc-rss-collector/functions/articles_api.py
- FOUND: .planning/phases/09-keyset-pagination/09-01-SUMMARY.md
- FOUND: commit d835049
- FOUND: commit 9eb6693
