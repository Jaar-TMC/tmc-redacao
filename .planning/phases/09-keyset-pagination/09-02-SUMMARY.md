---
phase: 09-keyset-pagination
plan: 02
subsystem: frontend-cursor-pagination
tags: [keyset-pagination, cursor, frontend, react-query, performance]
dependency_graph:
  requires: [encode_cursor, decode_cursor, keyset-seek-predicate, cursor-api-response]
  provides: [cursor-state-management, cursor-param-forwarding, filter-reset-cursor-clear]
  affects: [api.js, useArticles.js, hooks/index.js]
tech_stack:
  added: []
  patterns: [useRef-cursor-map, filter-change-detection-via-json-stringify, sequential-vs-jump-navigation]
key_files:
  created:
    - tmc-redacao/src/hooks/useArticles.js
  modified:
    - tmc-redacao/src/services/api.js
    - tmc-redacao/src/hooks/index.js
decisions:
  - queryKey excludes cursor to prevent unnecessary TanStack Query refetches on same logical page
  - cursor_direction param not needed on frontend -- cursorMap stores the right cursor per page number implicitly
  - Filter change detection uses JSON.stringify comparison on filters object (simple, reliable)
  - Non-sequential page jumps (missing cursor) silently fall back to OFFSET without special handling
metrics:
  duration: 4m26s
  completed: 2026-04-02
  tasks_completed: 2
  tasks_total: 2
  tests_added: 0
  files_modified: 3
---

# Phase 09 Plan 02: Frontend Cursor Pagination Summary

Frontend cursor state management via useRef cursorMap in useArticlesQuery, with cursor/cursor_direction URL params forwarded through getArticles in api.js.

## What Was Done

### Task 1: Add cursor param support to getArticles in api.js

Added two new URLSearchParams lines to the `getArticles` function:
- `if (params.cursor) queryParams.append('cursor', params.cursor)` -- only appends when cursor is truthy, preventing URLSearchParams from coercing `undefined`/`null` to the string `"undefined"`
- `if (params.cursor_direction) queryParams.append('cursor_direction', params.cursor_direction)` -- forwards direction when explicitly set

Updated JSDoc to document `params.cursor` and `params.cursor_direction`, and `@returns` to include `nextCursor`/`prevCursor`.

### Task 2: Add cursor state management to useArticlesQuery hook

Updated `useArticles.js` with cursor-aware state management:

- **cursorMapRef** (`useRef({})`): Stores cursors keyed by page number. `nextCursor` stored at `page + 1`, `prevCursor` at `page - 1`.
- **Filter change detection**: `prevFiltersRef` tracks `JSON.stringify(filters)`. When filters change, `cursorMapRef.current` is reset to `{}`.
- **Sequential navigation**: When `cursorMapRef.current[page]` has a value, it's passed as `params.cursor` for O(1) keyset seek.
- **Non-sequential jumps**: No cursor available = OFFSET fallback (automatic).
- **queryKey exclusion**: Cursor intentionally excluded from TanStack Query key.

## Verification Results

- Frontend build (`npx vite build`) succeeds with exit code 0
- `useArticles.js` stores cursors from API response in cursorMapRef
- `useArticles.js` resets cursorMapRef when filters change
- `api.js` sends cursor param only when non-null/non-undefined
- Pagination component unchanged (D-04)
- queryKey does NOT include cursor

## Self-Check: PASSED
