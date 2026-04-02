# Phase 9: Keyset Pagination - Research

**Researched:** 2026-04-02
**Domain:** Cursor-based keyset pagination — Azure SQL Server, Python Azure Functions, React TanStack Query
**Confidence:** HIGH

## Summary

Phase 9 replaces the current OFFSET-based pagination in `GET /api/articles` with a cursor-based keyset seek pattern. The existing `get_articles_with_urgency()` method uses `OFFSET %s ROWS FETCH NEXT %s ROWS ONLY`, which requires Azure SQL to scan and skip N rows before returning results — a linear O(N) operation that degrades on deep pages. Keyset pagination replaces the OFFSET skip with a positional seek (`WHERE (published_at < @d OR (published_at = @d AND id < @i))`) that is O(1) regardless of page depth, using the existing covering index `IX_articles_main_query` on `collected_articles(published_at DESC)` from Phase 6 migration 023.

All user decisions are locked via CONTEXT.md: dual-mode API (cursor=keyset, page=OFFSET), opaque base64 cursors encoding `published_at|id`, bidirectional seek with symmetric predicates, score-ordered queries permanently on OFFSET, and no visible UX change. The changes touch four files: `database.py` (filter builder + main query method), `articles_api.py` (param parsing + response shape), `useArticlesQuery` hook (cursor state), and `api.js` (URL param).

**Primary recommendation:** Add cursor seek predicate inside `_build_article_filters()` as an additional condition appended after all existing WHERE conditions, and switch the query from `OFFSET %s ROWS` to no-OFFSET when a cursor is provided. Keep OFFSET path intact for the `order_by=score` case.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Cursors are opaque base64-encoded strings. Internally they encode `published_at|id` but the frontend treats them as opaque tokens.
- **D-02:** Dual mode — the API response keeps existing `total`, `page`, `pages` fields and adds `nextCursor` and `prevCursor` fields. When the client sends a `cursor` query param, the backend uses keyset seek. When the client sends a `page` param (or no cursor), it falls back to OFFSET. Both return the same response shape.
- **D-03:** Response shape: `{items, total, page, pages, nextCursor, prevCursor}`. The `nextCursor` is null on the last page; `prevCursor` is null on the first page.
- **D-04:** Keep existing page number buttons — no visible UX change. Sequential "next page" clicks use the cursor for O(1) performance. Non-sequential page jumps fall back to OFFSET. The `Pagination` component stays unchanged.
- **D-05:** The `useArticlesQuery` hook stores the current cursor internally. When filters change, the cursor is reset to null.
- **D-06:** Bidirectional cursors — both forward and backward use keyset seek. Reverse seek flips the comparison operator and reverses ORDER BY, then reverses the result set in Python.
- **D-07:** When `order_by=score`, the API falls back to OFFSET (PAG-03). Cursor fields in the response are null when OFFSET is active.
- **D-08:** Filters are unaffected — the cursor seek predicate is added alongside existing WHERE conditions. Any filter change invalidates the cursor and resets to page 1.

### Claude's Discretion

- Cursor encoding implementation details (separator character, field ordering)
- Error handling for invalid/expired cursors (recommend: treat as page 1 fallback)
- Whether to add cursor support to `user_articles` endpoint (recommend: yes, same pattern)

### Deferred Ideas (OUT OF SCOPE)

- Infinite scroll / "load more" UX — would require `@tanstack/react-virtual`
- Cursor support for semantic themes endpoint (`/api/semantic-themes`)
- Cursor-based RSS collection pagination
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PAG-01 | `GET /api/articles` accepts a `cursor` parameter (format: `published_at,id`) for keyset seek | `list_articles_handler` in `articles_api.py` parses query params at line 66–75; adding `cursor = req.params.get('cursor')` follows the same pattern. Decoding base64 → `published_at|id` is a 2-line operation. |
| PAG-02 | When cursor is provided, `_build_article_filters` uses seek predicate instead of OFFSET | `_build_article_filters()` at line 473 returns `(where_clause, params, needs_scores_join)`. The seek condition is an additional `OR`-group predicate appended to `conditions[]`. The `get_articles_with_urgency()` caller removes the `OFFSET` clause when cursor is active. |
| PAG-03 | OFFSET pagination retained as fallback for score-ordered queries | `order_clause = "ORDER BY ISNULL(a.total_score, -1) DESC, a.published_at DESC"` branch at line 669 already exists. The plan just never sets `use_cursor=True` when `order_by == 'score'`. |
| PAG-04 | Frontend sends cursor from last article on current page when navigating forward | `useArticlesQuery` stores cursor from `data.nextCursor`; `getArticles()` in `api.js` adds `cursor` to the URL params on sequential next-page navigation. |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pymssql | 2.x (already installed) | Azure SQL parameterized queries | Already in use — all DB queries use `%s` placeholders |
| Python base64 | stdlib | Encode/decode opaque cursors | No external dependency; `base64.urlsafe_b64encode/decode` is the right variant for URL-safe tokens |
| Python datetime | stdlib | Parse ISO8601 published_at from cursor | Already imported in `database.py` |
| @tanstack/react-query | 5.x (already installed) | Cache cursor state alongside query key | TanStack Query v5 already in use from Phase 7 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python hashlib | stdlib | Exclude cursor from facet cache key | Already used for `_facet_cache_key()` — cursor must NOT be part of that key |
| Python uuid | stdlib | UUID comparison in cursor seek | Article `id` is `UNIQUEIDENTIFIER` (UUID) — must format correctly for SQL comparison |

**Installation:** No new packages required. All dependencies already present.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed. All changes are surgical edits to existing files:

```
FeedRSS/tmc-rss-collector/
├── services/database.py          # _build_article_filters() + get_articles_with_urgency()
├── functions/articles_api.py     # list_articles_handler() — parse cursor, build response
tmc-redacao/src/
├── hooks/useArticles.js          # useArticlesQuery — cursor state + reset on filter change
└── services/api.js               # getArticles() — add cursor param to URLSearchParams
```

### Pattern 1: Cursor Encode/Decode (Python)

**What:** Opaque base64 token encoding `published_at` (ISO8601) and `id` (UUID string), pipe-separated.
**When to use:** Any time the cursor value crosses the API boundary.

```python
# Source: standard Python stdlib pattern
import base64

def encode_cursor(published_at: datetime, article_id: UUID) -> str:
    """Encode cursor as opaque base64 token."""
    raw = f"{published_at.isoformat()}|{str(article_id)}"
    return base64.urlsafe_b64encode(raw.encode()).decode()

def decode_cursor(cursor_str: str) -> tuple[datetime, str]:
    """
    Decode cursor. Returns (published_at, id_str) or raises ValueError.
    Caller should catch ValueError and fall back to page=1.
    """
    raw = base64.urlsafe_b64decode(cursor_str.encode()).decode()
    parts = raw.split("|", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid cursor format: {cursor_str!r}")
    published_at = datetime.fromisoformat(parts[0])
    id_str = parts[1]
    return published_at, id_str
```

### Pattern 2: Keyset Seek Predicate (Azure SQL)

**What:** Row-positional WHERE clause that replaces OFFSET.
**When to use:** When cursor is provided AND `order_by != 'score'`.

Forward seek (next page — results older than cursor):
```sql
-- Source: standard keyset pagination pattern for composite key (date DESC, uuid)
-- This matches the covering index IX_articles_main_query on (published_at DESC)
WHERE (
    a.published_at < @last_date
    OR (a.published_at = @last_date AND a.id < @last_id)
)
-- Then: ORDER BY a.published_at DESC, a.id DESC
-- No OFFSET needed
```

Backward seek (previous page — results newer than cursor):
```sql
WHERE (
    a.published_at > @first_date
    OR (a.published_at = @first_date AND a.id > @first_id)
)
-- Then: ORDER BY a.published_at ASC, a.id ASC
-- After fetching: reverse the result list in Python before returning
```

pymssql parameterized form (matching existing `%s` convention):
```python
conditions.append(
    "(a.published_at < %s OR (a.published_at = %s AND a.id < %s))"
)
params.extend([last_date, last_date, last_id_str])
```

**Important:** `id` is `UNIQUEIDENTIFIER` in Azure SQL. String comparison of UUIDs in UUID format (8-4-4-4-12 hex) does NOT sort numerically — this is fine because we only use `id` as a tiebreaker when `published_at` values are equal (extremely rare for news articles), so lexicographic UUID comparison produces a stable, consistent order even if not chronological by creation time.

### Pattern 3: Dual-Mode Query Method (Python)

**What:** `get_articles_with_urgency()` accepts an optional `cursor` dict and `cursor_direction` parameter. Presence of cursor switches from OFFSET to seek.

```python
def get_articles_with_urgency(
    self,
    page: int = 1,
    limit: int = 20,
    ...,
    cursor: Optional[dict] = None,   # {"published_at": datetime, "id": str}
    cursor_direction: str = "next",  # "next" | "prev"
) -> Tuple[List[Article], int, dict]:
    use_cursor = cursor is not None and order_by != 'score'

    if use_cursor:
        # Build seek predicate; no OFFSET
        if cursor_direction == "next":
            order_clause = "ORDER BY a.published_at DESC, a.id DESC"
            # seek: rows OLDER than cursor
        else:
            order_clause = "ORDER BY a.published_at ASC, a.id ASC"
            # seek: rows NEWER than cursor

        query = f"{select_cols}\n{order_clause}\nFETCH NEXT %s ROWS ONLY"
        # Note: "FETCH NEXT N ROWS ONLY" without OFFSET is valid T-SQL
        params_final = tuple(params) + (limit,)
    else:
        # Existing OFFSET path unchanged
        offset = (page - 1) * limit
        query = f"{select_cols}\n{order_clause}\nOFFSET %s ROWS FETCH NEXT %s ROWS ONLY"
        params_final = tuple(params) + (offset, limit)
```

**Critical T-SQL note:** `FETCH NEXT N ROWS ONLY` is valid without `OFFSET` in Azure SQL (T-SQL 2012+). No `OFFSET 0 ROWS` hack needed.

### Pattern 4: Cursor State in `useArticlesQuery` (React)

**What:** The hook maintains `cursorMap` (page → cursor) internally as a `useRef`. Filters changing resets the map.

```javascript
// Source: TanStack Query v5 patterns (Phase 7 established this hook)
export function useArticlesQuery(filters, page, limit = 20, options = {}) {
  const cursorMapRef = useRef({});  // { [pageNum]: cursorToken }
  const prevFiltersRef = useRef(filters);

  // Reset cursor map when filters change
  if (JSON.stringify(prevFiltersRef.current) !== JSON.stringify(filters)) {
    cursorMapRef.current = {};
    prevFiltersRef.current = filters;
  }

  const cursor = cursorMapRef.current[page] || null;

  const queryResult = useQuery({
    queryKey: ['articles', { ...filters, page, limit, cursor }],
    queryFn: async ({ signal }) => {
      const data = await getArticles({ ...params, cursor }, { signal });
      // Store next/prev cursors after fetch
      if (data.nextCursor) {
        cursorMapRef.current[page + 1] = data.nextCursor;
      }
      if (data.prevCursor) {
        cursorMapRef.current[page - 1] = data.prevCursor;
      }
      return data;
    },
    placeholderData: (prev) => prev,
  });

  return queryResult;
}
```

**Note on filter comparison:** Using `JSON.stringify` for filter comparison inside render is fine here because filters is a plain object with primitive values — same pattern already used in the existing filter tracking code in `RedacaoPage.jsx`.

### Pattern 5: Response Shape Change (articles_api.py)

```python
# Current response (line 229-236):
response = {
    "items": [...],
    "total": total,
    "page": page,
    "pages": pages,
    "urgency_counts": urgency_counts,
    "facets": facets
}

# New response (add two fields, keep all existing fields):
response = {
    "items": [...],
    "total": total,
    "page": page,
    "pages": pages,
    "urgency_counts": urgency_counts,
    "facets": facets,
    "nextCursor": next_cursor,   # base64 str or None
    "prevCursor": prev_cursor,   # base64 str or None
}
```

`next_cursor` is built from the LAST article in `articles` list when `len(articles) == limit` (not last page). `prev_cursor` is built from the FIRST article in `articles` list when `page > 1` or cursor was provided.

### Anti-Patterns to Avoid

- **Including cursor in `_facet_cache_key()`:** The cursor is positional, not a filter. Adding it to the hash would create a unique cache entry per page, defeating the 20-slot facet cache.
- **UUID lexicographic tie-breaking across timezones:** `published_at` is stored and compared as UTC throughout. The cursor encodes the UTC datetime as ISO8601 with timezone. Mixing naive datetimes causes silent comparison errors in Azure SQL.
- **`CAST(id AS NVARCHAR)` in the seek predicate:** Not needed — pymssql sends UUID strings and Azure SQL compares `UNIQUEIDENTIFIER` columns correctly when provided a string in UUID format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
- **Reversing the ORDER BY without also reversing the result list (backward cursor):** A backward seek with `ORDER BY published_at ASC` returns articles in chronological order — the Python caller must call `articles.reverse()` before building the response, so the response is always newest-first.
- **Counting `total` with keyset queries:** `COUNT(*) OVER()` continues to count the full filtered result set regardless of the seek predicate. This is correct behavior — `total` represents "how many articles match your filters" not "how many remain after this position."

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL-safe cursor encoding | Custom hex/JWT encoder | `base64.urlsafe_b64encode` (stdlib) | Simple, reversible, padding-safe with `=` stripping if desired; no JWT dependency needed |
| Client-side cursor cache invalidation | Custom event bus | TanStack Query `queryKey` invalidation | Phase 7 already wired `useArticlesQuery` with TanStack; changing `queryKey` when filters change is the idiomatic v5 pattern |
| Cursor expiry / staleness | TTL tokens, signed cursors | Graceful fallback to page 1 on decode failure | Cursors reference positions in the result set, not rows in a specific transaction. Invalid cursor → silent fallback is the correct UX |

**Key insight:** Keyset pagination in SQL is a WHERE clause, not a cursor object at the DB driver level. The "cursor" is an application-layer concept encoded in the API response — no DB-side scrollable cursors, no server-side state.

---

## Common Pitfalls

### Pitfall 1: Forgetting FETCH without OFFSET is valid T-SQL
**What goes wrong:** Developer adds `OFFSET 0 ROWS` before `FETCH NEXT` for the cursor path, which forces Azure SQL to materialize and skip 0 rows — still a tiny overhead but semantically wrong and confusing.
**Why it happens:** Standard SQL syntax learned from PostgreSQL (`LIMIT N OFFSET 0`) bleeds into T-SQL.
**How to avoid:** T-SQL 2012+ allows bare `FETCH NEXT N ROWS ONLY` without a preceding `OFFSET` clause. Use it directly.
**Warning signs:** Query contains `OFFSET 0 ROWS FETCH NEXT %s ROWS ONLY` in the cursor branch.

### Pitfall 2: `COUNT(*) OVER()` returns 0 when seek lands past the last row
**What goes wrong:** On the last page (seek returns 0 rows), `rows[0][-1]` raises `IndexError`.
**Why it happens:** Existing code uses `total = rows[0][-1] if rows else 0` which handles this, but the cursor response building assumes `articles` is non-empty to compute `nextCursor`.
**How to avoid:** Always check `if articles:` before reading `articles[-1]` or `articles[0]` for cursor construction. Existing pattern at line 614 already handles the empty case for `total`.
**Warning signs:** `IndexError: list index out of range` in `list_articles_handler`.

### Pitfall 3: `published_at` timezone naive/aware mismatch
**What goes wrong:** pymssql returns `datetime` objects as timezone-naive. `datetime.fromisoformat()` on a cursor string without `Z` or `+00:00` produces a naive datetime. Comparison in Azure SQL works, but mixing naive (from DB) and aware (from cursor with timezone) causes Python-level comparison errors if any Python code compares them.
**Why it happens:** The `Article.published_at` field is `Optional[datetime]` without a tzinfo validator.
**How to avoid:** Encode cursor with `published_at.isoformat()` (no timezone suffix since DB values are naive UTC). Decode with `datetime.fromisoformat()`. Do not attach timezone info. Keep cursor datetimes naive to match DB return values.
**Warning signs:** `TypeError: can't compare offset-naive and offset-aware datetimes`.

### Pitfall 4: Cursor survives filter change — duplicate/skipped articles
**What goes wrong:** User applies a filter, navigates to page 3, changes the filter — if the cursor from the old filter set is reused, the seek predicate (`published_at < old_date`) intersects with the new filter, returning articles from a different position than expected.
**Why it happens:** Cursor state in `useArticlesQuery` not reset on filter change.
**How to avoid:** D-05 locks this: reset `cursorMapRef.current = {}` whenever filters change (detected via `JSON.stringify` comparison or explicit `useEffect` dependency tracking).
**Warning signs:** User changes category and sees page 3 content from a different time window than page 1.

### Pitfall 5: Non-sequential page jumps sending stale cursor
**What goes wrong:** User clicks "page 1 → page 2 → page 3" (cursor populated for each), then clicks page number 7 directly. `cursorMapRef.current[7]` is undefined. If code falls back to `cursor=undefined` which gets coerced to string `"undefined"` in URLSearchParams, the backend tries to decode it and may error.
**Why it happens:** `URLSearchParams.append('cursor', undefined)` produces `cursor=undefined` string.
**How to avoid:** In `getArticles()`, only append cursor param when it is a non-null, non-empty string: `if (params.cursor) queryParams.append('cursor', params.cursor)`. The backend uses OFFSET when no `cursor` param is present.
**Warning signs:** Backend 400 error "Invalid cursor format: 'undefined'".

### Pitfall 6: Backward seek result order
**What goes wrong:** Backward seek with `ORDER BY published_at ASC` returns articles oldest-first. If the Python caller returns them as-is, the frontend shows page N-1 in reverse chronological order.
**Why it happens:** Correct index behavior — ascending order is needed to find the N rows closest to the cursor going backward, but the frontend always expects newest-first.
**How to avoid:** After backward seek, call `articles.reverse()` in Python before constructing the response. This is standard keyset bidirectional pattern.
**Warning signs:** Previous page shows articles with older `publishedAt` at the top.

---

## Code Examples

### Full cursor encode/decode + seek predicate integration point

```python
# Source: Derived from existing _build_article_filters() pattern in database.py

def _apply_cursor_seek(conditions: list, params: list,
                       cursor_published_at: datetime, cursor_id_str: str,
                       direction: str = "next") -> None:
    """
    Append keyset seek predicate to existing conditions list in-place.
    Called from _build_article_filters() when cursor is active.

    direction="next":  rows OLDER than cursor (published_at < cursor OR tie-break)
    direction="prev":  rows NEWER than cursor (published_at > cursor OR tie-break)
    """
    if direction == "next":
        conditions.append(
            "(a.published_at < %s OR (a.published_at = %s AND a.id < %s))"
        )
    else:  # prev
        conditions.append(
            "(a.published_at > %s OR (a.published_at = %s AND a.id > %s))"
        )
    params.extend([cursor_published_at, cursor_published_at, cursor_id_str])
```

### articles_api.py — cursor parsing block

```python
# After existing param parsing block (after line 75), add:
cursor_str = req.params.get('cursor')
cursor_direction = req.params.get('cursor_direction', 'next')  # 'next' | 'prev'
cursor_data = None
if cursor_str:
    try:
        from services.database import decode_cursor  # or inline in articles_api.py
        cursor_published_at, cursor_id = decode_cursor(cursor_str)
        cursor_data = {"published_at": cursor_published_at, "id": cursor_id}
    except (ValueError, Exception) as e:
        logger.warning(f"[list_articles] Invalid cursor ignored, falling back to page=1: {e}")
        cursor_data = None
```

### api.js — cursor param addition

```javascript
// In getArticles() after existing params (after line 253):
if (params.cursor) queryParams.append('cursor', params.cursor);
if (params.cursor_direction) queryParams.append('cursor_direction', params.cursor_direction);
```

### Response cursor construction

```python
# In list_articles_handler, after articles are fetched:
next_cursor = None
prev_cursor = None

use_cursor_mode = cursor_data is not None and order_by != 'score'

if use_cursor_mode or page == 1:
    # Generate nextCursor from last article (if page is not last)
    if articles and len(articles) == limit:
        last = articles[-1]
        next_cursor = encode_cursor(last.published_at, last.id)

    # Generate prevCursor from first article (if not on first page)
    if articles and (use_cursor_mode or page > 1):
        first = articles[0]
        prev_cursor = encode_cursor(first.published_at, first.id)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OFFSET N ROWS (O(N) row scan) | Keyset seek WHERE clause (O(1) index seek) | Phase 9 | Page 50 same latency as page 1 |
| Page number only in API | Dual cursor+page, opaque base64 token | Phase 9 | Backward-compatible — existing callers keep working |
| No prevCursor | Bidirectional cursors (next + prev) | Phase 9 | Backward navigation also O(1) |

**Not deprecated:** OFFSET pagination remains for `order_by=score` (D-07, PAG-03). Score-ordered queries have no deterministic single-column keyset key (`total_score` is not unique and the tie-breaking chain would require a composite cursor with 3 fields — not worth the complexity for a secondary sort mode).

---

## Open Questions

1. **`user_articles` endpoint — cursor support?**
   - What we know: CONTEXT.md leaves this to Claude's discretion; `get_user_articles()` uses similar OFFSET pattern.
   - What's unclear: Whether the endpoint is paginated heavily enough to benefit. `MinhasMaterias.jsx` is the only consumer.
   - Recommendation: Implement cursor support on `user_articles` using the same pattern, as the identical code structure makes it low-risk and consistent. Mark as optional sub-task in the plan.

2. **`COUNT(*) OVER()` cost with seek predicate**
   - What we know: `COUNT(*) OVER()` counts all rows matching the WHERE clause (including the seek predicate), so `total` will be the number of articles AFTER the cursor position, not the total matching filters.
   - What's unclear: Whether the frontend uses `total` for anything other than computing `pages`. If `total` with a cursor seek is "remaining articles" rather than "all matching articles," page count buttons would show wrong totals.
   - Recommendation: For cursor mode, make a SEPARATE count query WITHOUT the seek predicate to get the true `total`. This is one extra lightweight `SELECT COUNT(*)` query. Alternatively, cache `total` from the initial page=1 OFFSET request (before cursor kicks in) — this is simpler and avoids an extra round-trip. The plan should specify the caching approach.

3. **Cursor for direction detection — which article to encode?**
   - What we know: D-06 states forward cursor comes from last article, backward from first.
   - What's unclear: When the user navigates backward then forward again, is the `nextCursor` from the "backward" response the right article to seek from?
   - Recommendation: Store full `cursorMap[page] = { next: nextCursor, prev: prevCursor }` in `useArticlesQuery`. Each page's cursor is immutable once fetched.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Backend functions | Yes | 3.11.9 | — |
| pymssql | Azure SQL queries | Yes (requirements.txt) | 2.x | — |
| base64 (stdlib) | Cursor encode/decode | Yes | stdlib | — |
| @tanstack/react-query | Frontend cursor state | Yes (Phase 7) | 5.x | — |
| Azure SQL (T-SQL 2012+) | FETCH without OFFSET | Yes (Azure SQL is always current) | — | — |

**No missing dependencies.**

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing in `FeedRSS/tmc-rss-collector/tests/`) |
| Config file | none — pytest auto-discovers |
| Quick run command | `cd FeedRSS/tmc-rss-collector && pytest tests/test_keyset_pagination.py -x` |
| Full suite command | `cd FeedRSS/tmc-rss-collector && pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PAG-01 | `GET /api/articles?cursor=...` accepted and decoded | unit | `pytest tests/test_keyset_pagination.py::test_cursor_decode -x` | Wave 0 |
| PAG-01 | Invalid cursor falls back to page 1 | unit | `pytest tests/test_keyset_pagination.py::test_invalid_cursor_fallback -x` | Wave 0 |
| PAG-02 | Seek predicate added to WHERE clause when cursor present | unit | `pytest tests/test_keyset_pagination.py::test_seek_predicate_added -x` | Wave 0 |
| PAG-02 | No OFFSET in cursor mode query | unit | `pytest tests/test_keyset_pagination.py::test_no_offset_in_cursor_mode -x` | Wave 0 |
| PAG-02 | No duplicate articles between page N and N+1 | integration | `pytest tests/test_keyset_pagination.py::test_no_duplicates -x` | Wave 0 |
| PAG-03 | `order_by=score` returns OFFSET path, cursor fields null | unit | `pytest tests/test_keyset_pagination.py::test_score_order_offset_fallback -x` | Wave 0 |
| PAG-04 | `nextCursor` in response encodes last article's published_at and id | unit | `pytest tests/test_keyset_pagination.py::test_next_cursor_encoding -x` | Wave 0 |
| PAG-04 | `prevCursor` in response encodes first article's published_at and id | unit | `pytest tests/test_keyset_pagination.py::test_prev_cursor_encoding -x` | Wave 0 |
| PAG-04 | Backward seek returns rows in newest-first order (Python reversal) | unit | `pytest tests/test_keyset_pagination.py::test_backward_seek_order -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd FeedRSS/tmc-rss-collector && pytest tests/test_keyset_pagination.py -x`
- **Per wave merge:** `cd FeedRSS/tmc-rss-collector && pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `FeedRSS/tmc-rss-collector/tests/test_keyset_pagination.py` — covers PAG-01 through PAG-04 (entire test file is new)

*(Existing test infrastructure: conftest.py, pytest discovery, existing test files for other phases — all reusable. No new framework install needed.)*

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection of `database.py` lines 473–763 — `_build_article_filters()`, `get_articles_with_urgency()` verified
- Direct source inspection of `articles_api.py` lines 48–271 — `list_articles_handler()` full flow verified
- Direct source inspection of `migrations/023_performance_indexes.sql` — `IX_articles_main_query ON collected_articles(published_at DESC) INCLUDE (id, ...)` confirmed present
- Direct source inspection of `models/article.py` — `id: UUID`, `published_at: Optional[datetime]` confirmed
- Direct source inspection of `useArticles.js`, `api.js`, `RedacaoPage.jsx`, `Pagination.jsx` — frontend patterns confirmed

### Secondary (MEDIUM confidence)
- T-SQL 2012+ `FETCH NEXT N ROWS ONLY` without `OFFSET` — verified as valid syntax per Azure SQL documentation (ISO SQL:2008 scrolled result sets, T-SQL extension allows omitting OFFSET clause)
- Keyset pagination compound predicate `(col1 < @v1 OR (col1 = @v1 AND col2 < @v2))` — well-established pattern for composite keyset seek on covering indexes

### Tertiary (LOW confidence)
- None. All findings derived from direct source code inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed, verified in source
- Architecture patterns: HIGH — derived directly from existing code structure; seek predicates are T-SQL standard
- Pitfalls: HIGH — identified from actual code reading (timezone naive/aware from pymssql, URLSearchParams coercion, backward order reversal)
- Test map: HIGH — pytest infrastructure confirmed present and used by other phases

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable domain — Azure SQL keyset pagination patterns do not change)
