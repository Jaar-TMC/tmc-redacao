# Phase 9: Keyset Pagination - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 09-keyset-pagination
**Areas discussed:** Cursor Format, API Backward Compatibility, Frontend Pagination UX, Backward Navigation

---

## Cursor Format

| Option | Description | Selected |
|--------|-------------|----------|
| Opaque (base64) | Hides internals, can change schema without breaking clients, tamper-resistant | ✓ |
| Transparent (`published_at,id`) | Easy to debug, simple to implement, but leaks DB schema | |

**User's choice:** Opaque base64 — accepted specialist recommendation
**Notes:** Standard practice across Stripe, GitHub, Slack APIs. Negligible encoding cost.

---

## API Backward Compatibility

| Option | Description | Selected |
|--------|-------------|----------|
| Dual mode | Keep page/pages/total, add nextCursor/prevCursor. Zero breaking change. | ✓ |
| Full replace | Remove page/pages, cursor-only. Cleaner but breaking change. | |
| New endpoint (/api/articles/v2) | Total isolation but duplicated code. | |

**User's choice:** Dual mode — accepted specialist recommendation
**Notes:** Frontend can migrate gradually. Both page and cursor params accepted simultaneously.

---

## Frontend Pagination UX

| Option | Description | Selected |
|--------|-------------|----------|
| Keep page numbers + keyset under the hood | Familiar UX, no visible change. Sequential clicks use cursor, jumps use OFFSET fallback. | ✓ |
| Prev/Next only | Pure keyset, no OFFSET ever. Removes page number orientation. | |
| Load more / infinite scroll | Modern feel but needs react-virtual, big frontend change. | |

**User's choice:** Keep page numbers — accepted specialist recommendation
**Notes:** 95%+ of pagination is sequential next-page clicks which benefit from keyset. Rare page jumps fall back to OFFSET transparently.

---

## Backward Navigation

| Option | Description | Selected |
|--------|-------------|----------|
| Bidirectional cursors (next + prev) | Full keyset performance in both directions. Reverse seek flips comparison operator. | ✓ |
| Forward-only | Simpler but "previous" needs OFFSET fallback or cache. | |
| Cache visited pages | Fast back-nav from memory but grows with pages, stale data risk. | |

**User's choice:** Bidirectional cursors — accepted specialist recommendation
**Notes:** Both directions use the same covering index from Phase 6.

---

## Additional Discussion: Filter Interaction

User asked whether keyset pagination affects page filters. Confirmed:
- Filters work exactly the same — cursor seek predicate is added alongside existing WHERE conditions
- Filter change = cursor reset (same pattern as existing `filtersChanged ? 1 : currentPage`)
- Score-ordered queries fall back to OFFSET (PAG-03)

---

## Claude's Discretion

- Cursor encoding details (separator, field ordering)
- Invalid/expired cursor error handling
- Whether to extend cursor to user_articles endpoint

## Deferred Ideas

- Infinite scroll / load more UX (needs react-virtual)
- Cursor for semantic themes endpoint
- Cursor for RSS collection pagination
