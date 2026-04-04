# TMC Roadmap

## Milestone: v1.0 P0 Backlog Resolution (COMPLETE)

### Phase 1: Session Persistence
- **Goal:** Fix auth so users stay logged in after F5 refresh
- **Status:** COMPLETE (commits 020b028, 8ae94c8, c7d2d84)

### Phase 2: Search/Filter Performance
- **Goal:** Fix LIKE query freezes, add missing indexes, optimize costs page, fix facet cache thrashing
- **Status:** COMPLETE
- **Tracks:** 3 parallel (DBA migrations, query optimization, frontend abort/debounce)

### Phase 3: Text Quality
- **Goal:** Fix text copying from sources, add competitor filtering, fix silent hallucination pass
- **Status:** COMPLETE

### Phase 4: Fact-Check Accuracy
- **Goal:** Add temporal awareness to fact-checking, stop blocking breaking news as unverifiable
- **Status:** COMPLETE

---

## Milestone: v2.0 Performance Optimization

> Eliminate RedacaoPage performance bottlenecks to achieve sub-200ms loads and sub-50ms filter responses.
> Source: `docs/plans/2026-04-02-performance-optimization-plan.md`

### Phase 5: Quick Wins
- **Goal:** Deploy zero-risk, high-impact fixes that require minimal code changes
- **Status:** COMPLETE
- **Requirements:** QW-01, QW-02, QW-03, QW-04, QW-05, QW-06, QW-07
- **Success Criteria:**
  1. CORS preflight responses include `Access-Control-Max-Age: 86400`
  2. All read endpoints return appropriate `Cache-Control` headers
  3. Article list API response payload reduced by >50% (no full content)
  4. ArticleCard does not re-render when article data is unchanged (verify with React DevTools)
  5. Timer triggers do not fire simultaneously at minute 0 (verify with Application Insights)
- **Depends on:** Nothing (no dependencies)

### Phase 6: Database Optimization
- **Goal:** Add covering indexes, cache urgency counts, parallelize facets, fix source filtering
- **Status:** COMPLETE (7/9 — DB-07 and DB-09 implemented in current session)
- **Requirements:** DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, DB-07, DB-08, DB-09
- **Success Criteria:**
  1. Main articles query uses covering index (no key lookups in execution plan)
  2. Urgency counts served from cache on >90% of requests
  3. Source filter uses `a.source_id` with index seek (not `s.name` scan)
  4. Facet queries execute in parallel (measurable via timing logs)
  5. Tag search uses FREETEXT when full-text index available
- **Depends on:** Phase 5 (cache headers must be active before optimizing queries)

### Phase 7: Frontend State
- **Goal:** Migrate to TanStack Query, fix SmartEmptyState API explosion, split FiltersContext
- **Status:** IN PROGRESS (FE-02 ✅, FE-04 ✅, FE-05 ✅ — FE-01, FE-03, FE-06 in progress)
- **Requirements:** FE-01, FE-02, FE-03, FE-04, FE-05, FE-06
- **Success Criteria:**
  1. RedacaoPage uses `useQuery` — no manual useEffect for data fetching
  2. Stale data shown instantly on page revisit (stale-while-revalidate working)
  3. SmartEmptyState fires 0-1 API calls (not N per active filter)
  4. Changing urgency filter does NOT re-render TrendsSidebar (measured with React DevTools Profiler)
  5. All data-fetching pages use consistent debounce + AbortController
- **Depends on:** Phase 6 (backend must be fast before frontend caching benefits compound)

### Phase 8: Redis Cache
- **Goal:** Add Redis cache-aside layer between API and Azure SQL for sub-5ms cache hits
- **Status:** NOT STARTED
- **Requirements:** CACHE-01, CACHE-02, CACHE-03, CACHE-04, CACHE-05
- **Success Criteria:**
  1. Redis provisioned and connected (health check passes)
  2. Repeated article list queries return in <5ms (cache hit)
  3. Cache miss falls through to Azure SQL transparently
  4. New articles appear within 3 minutes of RSS collection (TTL + invalidation)
  5. Application functions normally when Redis is unavailable (graceful fallback)
- **Depends on:** Phase 6 (optimized queries should be cached, not slow ones)

### Phase 9: Keyset Pagination
- **Goal:** Replace OFFSET pagination with cursor-based seek for O(1) deep page performance
- **Status:** COMPLETE
- **Requirements:** PAG-01, PAG-02, PAG-03, PAG-04
- **Plans:** 3/3 plans complete
  - [x] 09-01-PLAN.md — Backend: cursor encode/decode, seek predicate, dual-mode query, API response fields
  - [x] 09-02-PLAN.md — Frontend: cursor state in useArticlesQuery, cursor param in api.js
  - [x] 09-03-PLAN.md — Gap closure: wire cursor tracking into RedacaoPage (PAG-04)
- **Success Criteria:**
  1. `GET /api/articles?cursor=...` returns correct next page
  2. Page 50 loads in <10ms (same as page 1)
  3. Score-ordered queries still work with OFFSET fallback
  4. No duplicate or skipped articles when navigating with cursor
- **Depends on:** Phase 6 (indexes must support keyset seeks)

### Phase 10: Infrastructure
- **Goal:** Eliminate cold starts, reduce dependency bloat, tune connection pool
- **Status:** PARTIALLY DONE (INFRA-04 ✅ — INFRA-01/02/03/05/06 NOT STARTED)
- **Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06
- **Success Criteria:**
  1. First request after idle completes in <2s (no 8-15s cold start)
  2. numpy removed, cosine similarity works with pure Python (clustering tests pass)
  3. nest_asyncio removed from all 4 services (grep returns 0 results)
  4. Connection pool size matches plan tier (5 for Flex, 8-10 for Premium)
  5. Azure SQL confirmed in East US 2 (same region as Function App)
- **Depends on:** Can run in parallel with Phases 8-9 (infrastructure-only changes)
- Canonical refs: `docs/plans/2026-04-02-performance-optimization-plan.md` Phase 5 (Infrastructure)
