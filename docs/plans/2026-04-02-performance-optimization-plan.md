# TMC Performance Optimization Plan

**Date**: 2026-04-02
**Problem**: RedacaoPage is unusable — load times, filter changes, and search operations are unacceptably slow
**Root Cause**: No caching layer, every interaction hits Azure SQL directly, compounded by frontend re-render cascades and infrastructure cold starts
**Scope**: Full-stack optimization across backend, frontend, database, and infrastructure

---

## Executive Summary

Four specialized agents analyzed the entire TMC stack in parallel. They identified **32 distinct bottlenecks** across 4 layers:

| Layer | Bottlenecks Found | Critical/High | Key Issue |
|-------|-------------------|---------------|-----------|
| **Backend DB** | 10 | 2 HIGH | `content` column in list queries + urgency re-scan doubles query time |
| **Frontend** | 10 | 2 HIGH | FiltersContext cascade re-renders + SmartEmptyState fires N API calls |
| **Infrastructure** | 12 | 4 HIGH | Consumption Plan cold starts (8-15s) + no Cache-Control headers |
| **Industry Research** | 7 areas | — | Redis, TanStack Query, cursor pagination, cold start fixes, indexes |

**Expected outcome after full implementation:**
- Initial page load: **8-15s → <2s** (eliminate cold starts + caching)
- Filter change response: **300-500ms → <50ms** (cache hits + re-render elimination)
- Search response: **500-1200ms → <100ms** (full-text search + Redis cache)
- Deep pagination: **2-5s → <10ms** (keyset pagination)

---

## Phase 0: Quick Wins (Zero Cost, 1-2 Days)

These are one-line or small changes that deliver immediate impact with zero risk.

### 0.1 Add `Access-Control-Max-Age: 86400` to CORS preflight
- **File**: `function_app.py:90-99`
- **Problem**: Every cross-origin request triggers a preflight OPTIONS request (~100-300ms each). No `Access-Control-Max-Age` header means browsers never cache the preflight result.
- **Fix**: Add `"Access-Control-Max-Age": "86400"` to the OPTIONS response headers
- **Impact**: Eliminates ~50% of cross-origin HTTP requests for repeat visitors

### 0.2 Call `add_cache_headers()` in HTTP handlers
- **File**: `function_app.py:64-76`
- **Problem**: `add_cache_headers()` is defined but **never called** anywhere. Zero Cache-Control headers on any API response.
- **Fix**: Call it in each read handler with appropriate TTLs:
  - `GET /api/articles` → `private, max-age=60`
  - `GET /api/articles/{id}` → `public, max-age=3600`
  - `GET /api/categories` → `public, max-age=300`
  - `GET /api/tags` → `public, max-age=300`
  - `GET /api/trending-tags` → `public, max-age=300`
  - `GET /api/semantic-themes` → `public, max-age=600`
- **Impact**: Browser-level caching for read-heavy endpoints, significant backend load reduction

### 0.3 Remove `content` from list queries
- **File**: `database.py:678` (`get_articles_with_urgency`)
- **Problem**: Full `a.content` (2-20KB per article) fetched for list view, then truncated to 1000 chars in Python. Forces key lookups + wastes ~100KB network transfer per page.
- **Fix**: Replace `a.content` with `LEFT(a.content, 200) as content` or remove entirely (frontend uses `preview` in list mode)
- **Impact**: 30-100ms per request, ~80% payload reduction

### 0.4 Fix ArticleCard memo comparator
- **File**: `tmc-redacao/src/components/cards/ArticleCard.jsx:205`
- **Problem**: `React.memo` shallow comparison fails because `transformArticle()` creates new object references every time (including new `Date` instances)
- **Fix**: `export default memo(ArticleCard, (prev, next) => prev.article.id === next.article.id && prev.isSelected === next.isSelected)`
- **Impact**: Prevents 20-card re-renders on cached data returns and pagination

### 0.5 Stagger timer trigger schedules
- **Problem**: At minute 0 of every hour, up to 5 timers fire simultaneously (keepalive + embedding + scoring + rss_collector + clustering), exhausting the connection pool
- **Fix**: Offset schedules by a few minutes:
  - `rss_collector`: `0 2 */15 * * *`
  - `scoring_calculator`: `0 7 */10 * * *`
  - `clustering_engine`: `0 4 */30 * * *`
- **Impact**: Eliminates thundering-herd resource contention

### 0.6 Add `loading="lazy"` to favicon images
- **File**: `ArticleCard.jsx:123-126`
- **Problem**: 20 external Google Favicon API requests fire simultaneously on page load
- **Fix**: Add `loading="lazy"` to the `<img>` tag
- **Impact**: Eliminates burst of 20 HTTP requests on cold load

### 0.7 Guard AiStatusContext against no-change polls
- **File**: `tmc-redacao/src/context/AiStatusContext.jsx:41-50`
- **Problem**: Polls every 60s and always calls `setStatus()` even when status hasn't changed, triggering unnecessary re-renders
- **Fix**: Compare `data.paused !== status.aiPaused` before `setStatus()`
- **Impact**: Eliminates wasteful re-renders every 60 seconds

---

## Phase 1: Database Optimization (Zero Cost, 2-3 Days)

### 1.1 Add composite covering indexes

Create a new migration file with:

```sql
-- Primary query: ORDER BY published_at DESC (default)
CREATE NONCLUSTERED INDEX IX_articles_main_query
ON collected_articles (published_at DESC)
INCLUDE (id, source_id, title, preview, url, image_url, author, category,
         tags, collected_at, hash, total_score, classification);

-- Category filter + date sort (most common filter)
CREATE NONCLUSTERED INDEX IX_articles_category_date
ON collected_articles (category, published_at DESC)
INCLUDE (id, source_id, title, preview, total_score, classification);

-- Score ordering
CREATE NONCLUSTERED INDEX IX_articles_score_date
ON collected_articles (total_score DESC, published_at DESC)
INCLUDE (id, source_id, title, preview, category, classification);

-- Enable automatic tuning
ALTER DATABASE CURRENT SET AUTOMATIC_TUNING (CREATE_INDEX = ON);
```

**Impact**: 2-5x improvement on filtered queries by eliminating key lookups

### 1.2 Cache urgency counts (eliminate double table scan)
- **File**: `database.py:726-737`
- **Problem**: A second full-table scan runs to compute urgency bucket counts (1h/3h/8h/total) on every request
- **Fix**: Cache urgency counts with 30-60 second TTL at application level (they represent time-bucket summaries that barely change between requests)
- **Impact**: Cuts query time in half for the most common request pattern

### 1.3 Fix source filter to use `source_id` instead of `s.name`
- **File**: `database.py:501-503`
- **Problem**: Despite parameter named `source_id`, filter compares `s.name = %s` (string comparison on non-indexed column), bypassing the `IX_collected_articles_source_published` index
- **Fix**: Frontend sends `source_id` (UUID), backend filters `a.source_id = %s`
- **Impact**: Enables index usage for source-filtered queries

### 1.4 Parallelize facet queries with `asyncio.gather()`
- **File**: `articles_api.py:116-168`
- **Problem**: Categories and tags facets run as 2 sequential `await` calls, each with its own DB round-trip
- **Fix**: `categories, tags = await asyncio.gather(db.get_categories_filtered(...), db.get_all_tags_filtered(...))`
- **Impact**: First-load latency drops from 3 sequential round-trips to 2 parallel batches

### 1.5 Fix `get_all_tags_filtered` to use full-text search
- **File**: `database.py:1407-1414`
- **Problem**: Always uses `LIKE '%term%'` for search, ignoring the full-text index. Never calls `_has_fulltext_index()`
- **Fix**: Check `_has_fulltext_index()` and use `FREETEXT()` when available
- **Impact**: Eliminates O(N) full table scan for tag queries with search active

### 1.6 Key facet cache by filter combination
- **File**: `articles_api.py:170-173`
- **Problem**: Facet cache is a single global slot — only unfiltered results are cached. Every filter change triggers fresh facet computation
- **Fix**: Use a dict keyed by filter hash, capped at 20 entries
- **Impact**: Eliminates redundant facet queries for repeated filter combinations

---

## Phase 2: Frontend State & Caching (Zero Cost, 4-6 Days)

### 2.1 Migrate to TanStack Query (starting with RedacaoPage)

Replace the hand-rolled 85-line `useEffect` fetch + manual cache with TanStack Query:

```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
```

**Configuration:**
```js
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,    // 2 min (matches RSS cadence)
      gcTime: 10 * 60 * 1000,       // 10 min garbage collection
      retry: 2,
      refetchOnWindowFocus: true,    // newsroom users switch tabs often
    },
  },
});
```

**Migration plan:**
1. Create `useArticles(filters, page)` hook wrapping `getArticles()` 
2. Create `useCategories()`, `useTrendingTags()` hooks
3. Replace `ArticlesCacheContext` entirely (TanStack Query handles caching, dedup, stale-while-revalidate)
4. Keep `ArticlesContext` for selection state (client state, not server state)
5. Retire `apiCache.js` `cachedFetch` for endpoints migrated to TanStack Query

**Benefits:**
- 40-70% faster perceived loads (stale data shown instantly)
- Automatic request deduplication
- Structural sharing prevents re-renders when data hasn't changed
- ~150-200 lines removed from RedacaoPage alone
- React Query DevTools for debugging

### 2.2 Fix SmartEmptyState N+1 API calls
- **File**: `tmc-redacao/src/components/ui/SmartEmptyState.jsx:34-98`
- **Problem**: When filters return zero results, fires 1 API call per active filter to compute "what if I remove this filter?" counts. 4 active filters = 4 extra API calls
- **Fix**: Either (a) return facet counts with zero-result responses from the main API, or (b) batch all suggestions into a single `/api/articles/facet-counts` endpoint
- **Impact**: 3-4x reduction in backend load on zero-result searches

### 2.3 Split FiltersContext to eliminate cascade re-renders
- **File**: `tmc-redacao/src/context/FiltersContext.jsx:16-24`
- **Problem**: Single `filters` object causes all 5+ consumers (RedacaoPage, FilterBar, TrendsSidebar, ActiveFiltersBar, SmartEmptyState) to re-render on any single filter change
- **Fix**: Implement selector pattern — `useFilter('urgency')` that subscribes to one dimension only. Or use `useSyncExternalStore` with per-filter subscriptions
- **Impact**: Reduces per-filter-change re-renders from 5+ components to 1-2

### 2.4 Standardize debounce/AbortController across all pages
- **Problem**: `MinhasMaterias.jsx` has no debounce. `BuscadorPage.jsx` uses a `cancelled` flag instead of AbortController. `cachedFetch` doesn't forward AbortSignal
- **Fix**: Apply RedacaoPage's pattern (150ms debounce + AbortController) to all data-fetching pages. Forward signal through `cachedFetch`
- **Impact**: Reduces API calls by 60-80% during filter interaction on affected pages

---

## Phase 3: Server-Side Caching with Redis (~$16-40/month, 3-5 Days)

### 3.1 Provision Azure Cache for Redis
- **Tier**: Basic C0 ($16/month) for dev, Standard C0 ($40/month) for production
- **Region**: East US 2 (co-locate with Azure Functions)

### 3.2 Implement cache-aside pattern

Create `services/cache_service.py`:

```
Frontend → Azure Functions → Redis (check) → hit? return (~1-5ms)
                                    ↓
                                  miss → Azure SQL → store in Redis → return
```

**TTL strategy:**
| Resource | TTL | Rationale |
|----------|-----|-----------|
| Article list (per filter+page) | 120s | New articles arrive every 15 min |
| Single article | 600s | Rarely changes after insert |
| Categories facets | 300s | Changes only after RSS collection |
| Tags facets | 300s | Same as categories |
| Trending tags | 300s | Same |
| Urgency counts | 60s | Time-bucket summaries |

**Cache key format**: `tmc:articles:${md5(JSON.stringify(filterParams))}`

### 3.3 Add cache invalidation to RSS collector
- After `rss_collector` timer inserts new articles, invalidate article list cache keys
- Use Redis `SCAN` + `DEL` for keys matching `tmc:articles:*`
- Keep facet caches (they'll expire naturally within TTL)

**Expected impact:**
- Cache hit: ~1-5ms vs ~50-200ms (Azure SQL)
- 70-90% fewer DB queries for repeated filter combinations
- P95 response time: 300-500ms → 10-30ms for cached queries

---

## Phase 4: Keyset Pagination (Zero Cost, 2-3 Days)

### 4.1 Add cursor parameter to articles API
- **Endpoint**: `GET /api/articles?cursor=2026-04-01T12:00:00Z,abc123`
- **Cursor format**: `published_at,id` of the last item on the current page

### 4.2 Implement keyset seek in `_build_article_filters`

When `cursor` is provided:
```sql
WHERE (a.published_at < @last_published_at)
   OR (a.published_at = @last_published_at AND a.id < @last_id)
ORDER BY a.published_at DESC, a.id DESC
FETCH NEXT 20 ROWS ONLY
```

### 4.3 Update frontend pagination
- Keep numbered pages for shallow navigation (pages 1-5)
- Add "Load More" button as alternative for deep browsing
- Keep OFFSET as fallback for score ordering (many ties make keyset harder)

**Expected impact:**
- Page 1: same (~5ms)
- Page 50: 2-5s → <10ms (constant O(1) regardless of depth)
- Eliminates result drift when new articles are inserted during browsing

---

## Phase 5: Infrastructure (Variable Cost, 2-3 Days)

### 5.1 Migrate to Flex Consumption Plan (recommended) or Premium EP1
- **Flex Consumption**: Microsoft's recommended replacement for legacy Consumption. Supports always-ready instances with pay-per-execution pricing
- **Premium EP1**: ~$150/month, zero cold starts guaranteed, VNet integration included
- **Current Consumption**: ~$30-50/month estimated, but 8-15s cold starts

**Recommendation**: Start with Flex Consumption (1 always-ready instance). Evaluate Premium EP1 if traffic grows.

### 5.2 Remove numpy dependency
- **Problem**: numpy adds ~500ms to import time, used only for cosine similarity in clustering
- **Fix**: Replace with pure-Python dot product calculation (trivial for 1536-dim vectors)
- **Impact**: 2-3 second cold start reduction if staying on Consumption plan

### 5.3 Remove unused dependencies
- `google-auth` (Gemini integration is dormant per config)
- `nest-asyncio` (anti-pattern, should use native `await`)
- **Impact**: Further cold start reduction + stability improvement

### 5.4 Reduce connection pool size
- **Current**: `SQL_POOL_SIZE = 15`
- **Fix**: Reduce to `5` for Consumption/Flex, `8-10` for Premium
- **Impact**: Fewer idle connections killed by Azure SQL, less memory waste

### 5.5 Verify cross-region alignment
- Function App is in East US 2. Verify Azure SQL is in the same region
- If cross-region: ~100-150ms per query penalty. Migrate to co-locate
- Consider Private Endpoints (~$7/month) for ~0.5ms latency reduction + security

### 5.6 Refactor `nest_asyncio` usage in 4 services
- `event_signature_service.py`, `llm_verification_service.py`, `llm_service.py`, `scoring_service.py`
- Replace with native `await` (all handlers are already `async def`)
- **Impact**: Eliminates deadlock risk under load

---

## Implementation Priority & Timeline

| Phase | Impact | Effort | Cost | When |
|-------|--------|--------|------|------|
| **Phase 0**: Quick Wins | HIGH | 1-2 days | $0 | Week 1 |
| **Phase 1**: DB Optimization | HIGH | 2-3 days | $0 | Week 1 |
| **Phase 2**: Frontend State | HIGH | 4-6 days | $0 | Week 2-3 |
| **Phase 3**: Redis Cache | HIGH | 3-5 days | ~$16-40/mo | Week 3 |
| **Phase 4**: Keyset Pagination | MEDIUM | 2-3 days | $0 | Week 4 |
| **Phase 5**: Infrastructure | HIGH | 2-3 days | ~$100-150/mo | Week 4 |

**Total: 14-22 days, ~$116-190/month additional infrastructure cost**

---

## Expected Performance After Full Implementation

| Metric | Current | After Phase 0-1 | After All Phases |
|--------|---------|------------------|------------------|
| Cold start (first request) | 8-15s | 8-15s | <1s (Flex/Premium) |
| Initial page load (warm) | 1-3s | 300-500ms | <200ms |
| Filter change response | 300-500ms | 100-200ms | <50ms (cache hit) |
| Search response | 500-1200ms | 200-400ms | <100ms |
| Deep page (page 50+) | 2-5s | 1-2s | <10ms (keyset) |
| CORS preflight overhead | 100-300ms/req | 0ms (cached 24h) | 0ms |

---

## Bottleneck Inventory (All 32 Issues)

### Backend Database (10)
| # | Issue | Severity | Phase |
|---|-------|----------|-------|
| B1 | `content` column in list queries | HIGH | 0.3 |
| B2 | Urgency count full-table rescan | HIGH | 1.2 |
| B3 | OFFSET pagination degradation | MEDIUM | 4 |
| B4 | Sequential facet queries (3 round-trips) | MEDIUM | 1.4 |
| B5 | Source filter by `s.name` not `s.id` | MEDIUM | 1.3 |
| B6 | `get_all_tags_filtered` ignores full-text | MEDIUM | 1.5 |
| B7 | OPENJSON for filtered tag counts | MEDIUM | 1.6 |
| B8 | Thread/connection pool under burst | LOW | 5.4 |
| B9 | Facet cache not keyed by filters | LOW | 1.6 |
| B10 | `generate_preview` regex per article | LOW | 0.3 |

### Frontend (10)
| # | Issue | Severity | Phase |
|---|-------|----------|-------|
| F1 | SmartEmptyState fires N API calls | HIGH | 2.2 |
| F2 | FiltersContext cascade re-renders | HIGH | 2.3 |
| F3 | ArticleCard memo ineffective | MEDIUM | 0.4 |
| F4 | formatRelativeTime per card | LOW | 0.4 |
| F5 | No list virtualization | MEDIUM | Future |
| F6 | Dual cache layers, no coordination | MEDIUM | 2.1 |
| F7 | CriarContext monolith | LOW | Future |
| F8 | AiStatusContext polls without diff | LOW | 0.7 |
| F9 | Non-search filters immediate re-renders | MEDIUM | 2.3 |
| F10 | Pagination reads window.innerWidth | LOW | Future |

### Infrastructure (12)
| # | Issue | Severity | Phase |
|---|-------|----------|-------|
| I1 | Credentials in OneDrive-synced file | CRITICAL | Immediate |
| I2 | Consumption Plan cold starts (8-15s) | HIGH | 5.1 |
| I3 | DB pool oversized for concurrency | HIGH | 5.4 |
| I4 | No Cache-Control headers (never called) | HIGH | 0.2 |
| I5 | No CORS `Access-Control-Max-Age` | HIGH | 0.1 |
| I6 | Timer triggers thundering herd | MEDIUM | 0.5 |
| I7 | No explicit TDS version | MEDIUM | 5.4 |
| I8 | Cross-region latency risk | MEDIUM | 5.5 |
| I9 | `nest_asyncio` anti-pattern | MEDIUM | 5.6 |
| I10 | App Insights samples exceptions | LOW | 5.1 |
| I11 | Dynamic throttles over-aggressive | LOW | 5.1 |
| I12 | No SWA API proxy caching | LOW | Future |

---

## Key References

### Industry Sources
- [Cache-Aside Pattern - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside)
- [Azure Functions Flex Consumption Plan](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-plan)
- [TanStack Query v5 Docs](https://tanstack.com/query/v5/docs/react/guides/important-defaults)
- [Keyset Pagination - Use The Index Luke](https://use-the-index-luke.com/sql/partial-results/fetch-next-page)
- [SQL Server Filtered Indexes](https://learn.microsoft.com/en-us/sql/relational-databases/indexes/create-filtered-indexes)
- [Azure Cache for Redis Pricing](https://azure.microsoft.com/en-us/pricing/details/cache/)

### Agent Reports
- Backend DB Analysis: 10 bottlenecks, 2 HIGH severity
- Frontend Performance Analysis: 10 bottlenecks, 2 HIGH severity
- Infrastructure Audit: 12 findings, 1 CRITICAL + 4 HIGH severity
- Industry Research: 7 optimization areas with benchmarks and sources
