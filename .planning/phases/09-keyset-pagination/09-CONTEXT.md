# Phase 9: Keyset Pagination - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace OFFSET pagination with cursor-based keyset seek for O(1) deep page performance. The cursor approach eliminates row-scanning overhead on deep pages while maintaining full backward compatibility with existing filter, sort, and pagination UI.

</domain>

<decisions>
## Implementation Decisions

### Cursor Format
- **D-01:** Cursors are **opaque base64-encoded** strings. Internally they encode `published_at|id` but the frontend treats them as opaque tokens. This hides DB schema details and allows format changes without breaking clients.

### API Backward Compatibility
- **D-02:** **Dual mode** — the API response keeps existing `total`, `page`, `pages` fields and adds `nextCursor` and `prevCursor` fields. When the client sends a `cursor` query param, the backend uses keyset seek. When the client sends a `page` param (or no cursor), it falls back to OFFSET. Both return the same response shape.
- **D-03:** Response shape: `{items, total, page, pages, nextCursor, prevCursor}`. The `nextCursor` is null on the last page; `prevCursor` is null on the first page.

### Frontend Pagination UX
- **D-04:** **Keep existing page number buttons** — no visible UX change. Sequential "next page" clicks use the cursor for O(1) performance. Non-sequential page jumps (e.g., "jump to page 15") fall back to OFFSET. The `Pagination` component stays unchanged.
- **D-05:** The `useArticlesQuery` hook stores the current cursor internally. When filters change, the cursor is reset to null (same pattern as existing `filtersChanged ? 1 : currentPage` logic in RedacaoPage.jsx:126-128).

### Backward Navigation
- **D-06:** **Bidirectional cursors** — both forward (next) and backward (prev) use keyset seek. The reverse seek flips the comparison operator (`>` instead of `<`) and reverses the ORDER BY, then reverses the result set in Python. Both directions use the same covering index from Phase 6.

### Score-Ordered Queries
- **D-07:** When `order_by=score`, the API falls back to OFFSET pagination (PAG-03). Score ordering doesn't have a deterministic keyset-compatible index. The cursor fields in the response are null when OFFSET is active.

### Filter Interaction
- **D-08:** Filters are unaffected — the cursor seek predicate is added alongside existing WHERE conditions. Any filter change (category, source, urgency, search, classification, sort order) invalidates the cursor and resets to page 1.

### Claude's Discretion
- Cursor encoding implementation details (separator character, field ordering)
- Error handling for invalid/expired cursors (recommend: treat as page 1 fallback)
- Whether to add cursor support to `user_articles` endpoint (recommend: yes, same pattern)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend Pagination
- `FeedRSS/tmc-rss-collector/services/database.py` §568-620 — Current `get_articles()` with OFFSET, `_build_article_filters()` method
- `FeedRSS/tmc-rss-collector/services/database.py` §623-644 — `get_articles_with_urgency()` — the actual method called by the API handler
- `FeedRSS/tmc-rss-collector/functions/articles_api.py` §48-139 — `list_articles_handler` with page/limit parsing and response construction

### Frontend Pagination
- `tmc-redacao/src/pages/RedacaoPage.jsx` §71-72,126-128 — currentPage state, filter-change reset logic
- `tmc-redacao/src/hooks/useArticles.js` §15-24 — `useArticlesQuery` TanStack Query hook
- `tmc-redacao/src/services/api.js` §233-247 — `getArticles()` API call with page/limit params

### Database Indexes (Phase 6)
- `FeedRSS/tmc-rss-collector/migrations/` — Covering indexes on `collected_articles(published_at DESC)` that support keyset seeks

### Requirements
- `.planning/REQUIREMENTS.md` §42-48 — PAG-01 through PAG-04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_build_article_filters()` in `database.py` — existing filter builder that constructs WHERE clauses. Cursor seek predicate should be added here.
- `Pagination` component in `tmc-redacao/src/components/ui/Pagination.jsx` — existing page-number pagination UI, no changes needed.
- `useArticlesQuery` hook — already wraps TanStack Query with filters+page. Add cursor tracking here.
- `COUNT(*) OVER()` window function already in the query — keeps `total` available without a separate count query.

### Established Patterns
- Filter hash cache key pattern (`_facet_cache_key`) — cursor should be excluded from cache keys since it's positional, not filter-based.
- `skip_facets` optimization for page > 1 — same pattern applies to cursor-based requests.
- `run_db()` async wrapper for sync DB calls — all DB methods go through this.

### Integration Points
- `list_articles_handler` in `articles_api.py` — parse `cursor` query param, pass to DB method, include cursors in response.
- `getArticles()` in `api.js` — add `cursor` param to query string.
- `RedacaoPage.jsx` — store cursor from last response, pass to next request on sequential navigation.

</code_context>

<specifics>
## Specific Ideas

- The cursor format `published_at|id` uses the composite key that matches the existing covering index `(published_at DESC, id)` from Phase 6 DB-01.
- For tie-breaking on `published_at` (multiple articles at same timestamp), the `id` (UUID) provides deterministic ordering.
- The bidirectional seek uses: forward = `(published_at < @d OR (published_at = @d AND id < @i))`, backward = `(published_at > @d OR (published_at = @d AND id > @i))` with reversed ORDER BY.

</specifics>

<deferred>
## Deferred Ideas

- Infinite scroll / "load more" UX — would require `@tanstack/react-virtual` (listed in REQUIREMENTS.md as future)
- Cursor support for semantic themes endpoint (`/api/semantic-themes`) — not in PAG requirements
- Cursor-based RSS collection pagination — internal timer, not user-facing

</deferred>

---

*Phase: 09-keyset-pagination*
*Context gathered: 2026-04-02*
