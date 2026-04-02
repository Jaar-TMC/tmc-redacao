# Milestone v2.0: Performance Optimization — Requirements

## Quick Wins (QW)

- [ ] **QW-01**: API responses include `Access-Control-Max-Age: 86400` on CORS preflight, eliminating redundant OPTIONS requests
- [ ] **QW-02**: All read-only API endpoints return appropriate `Cache-Control` headers (articles 60s, single article 3600s, categories/tags 300s)
- [ ] **QW-03**: Article list queries exclude full `content` column, returning only `preview` for list mode
- [ ] **QW-04**: ArticleCard uses custom memo comparator (`article.id + isSelected`) preventing unnecessary re-renders
- [ ] **QW-05**: Timer triggers are staggered to avoid thundering-herd at minute 0 of each hour
- [ ] **QW-06**: Article card favicon images use `loading="lazy"` attribute
- [ ] **QW-07**: AiStatusContext compares status before calling `setStatus()` to prevent no-op re-renders

## Database Optimization (DB)

- [ ] **DB-01**: Composite covering index on `collected_articles(published_at DESC)` with INCLUDE for all list-query columns eliminates key lookups
- [ ] **DB-02**: Category+date composite index `(category, published_at DESC)` accelerates the most common filter
- [ ] **DB-03**: Score ordering index `(total_score DESC, published_at DESC)` accelerates score-sorted queries
- [ ] **DB-04**: Azure SQL automatic tuning enabled (`CREATE_INDEX = ON`)
- [ ] **DB-05**: Urgency counts are cached with 30-60s TTL, eliminating the duplicate full-table scan per request
- [ ] **DB-06**: Source filtering uses `a.source_id` (UUID) instead of `s.name` (string), leveraging existing FK index
- [ ] **DB-07**: Facet queries (categories + tags) execute in parallel via `asyncio.gather()` instead of sequential awaits
- [ ] **DB-08**: `get_all_tags_filtered()` uses `FREETEXT()` when full-text index is available instead of `LIKE '%term%'`
- [ ] **DB-09**: Facet cache is keyed by filter combination hash (not a single global slot), capping at 20 entries

## Frontend State (FE)

- [ ] **FE-01**: RedacaoPage data fetching uses TanStack Query (`useQuery`) with stale-while-revalidate, replacing hand-rolled useEffect + manual cache
- [ ] **FE-02**: Custom hooks `useArticles(filters, page)`, `useCategories()`, `useTrendingTags()` wrap API calls with TanStack Query
- [ ] **FE-03**: `ArticlesCacheContext` and `apiCache.js` retired for endpoints migrated to TanStack Query
- [ ] **FE-04**: SmartEmptyState uses facet counts from main API response or a single batch endpoint instead of firing N parallel API calls
- [ ] **FE-05**: FiltersContext uses selector pattern (`useFilter('urgency')`) so only the affected component re-renders on filter change
- [ ] **FE-06**: All data-fetching pages (MinhasMaterias, BuscadorPage) have consistent debounce (150ms) and AbortController patterns

## Server-Side Caching (CACHE)

- [ ] **CACHE-01**: Azure Cache for Redis provisioned in East US 2 (Basic C0 for dev, Standard C0 for production)
- [ ] **CACHE-02**: `services/cache_service.py` implements cache-aside pattern: check Redis → miss → query Azure SQL → store in Redis
- [ ] **CACHE-03**: Article list queries use Redis cache with 120s TTL, facets with 300s TTL, single articles with 600s TTL
- [ ] **CACHE-04**: RSS collector timer invalidates article list cache keys after inserting new articles
- [ ] **CACHE-05**: Cache service handles Redis unavailability gracefully, falling back to direct DB queries

## Keyset Pagination (PAG)

- [x] **PAG-01**: `GET /api/articles` accepts a `cursor` parameter (format: `published_at,id`) for keyset seek
- [x] **PAG-02**: When cursor is provided, `_build_article_filters` uses seek predicate (`WHERE published_at < @last AND id < @last_id`) instead of OFFSET
- [x] **PAG-03**: OFFSET pagination retained as fallback for score-ordered queries
- [x] **PAG-04**: Frontend sends cursor from last article on current page when navigating forward

## Infrastructure (INFRA)

- [ ] **INFRA-01**: Azure Functions migrated from Consumption to Flex Consumption or Premium EP1 plan
- [ ] **INFRA-02**: numpy dependency replaced with pure-Python cosine similarity (reduces cold start by 2-3s)
- [ ] **INFRA-03**: Unused dependencies removed (google-auth, nest-asyncio)
- [ ] **INFRA-04**: `SQL_POOL_SIZE` reduced to 5 (Consumption/Flex) or 8-10 (Premium)
- [ ] **INFRA-05**: `nest_asyncio.apply()` calls in 4 services replaced with native `await`
- [ ] **INFRA-06**: Azure SQL server region verified as East US 2 (co-located with Function App)

## Future Requirements (deferred)

- Virtual scrolling with `@tanstack/react-virtual` (only needed if switching to infinite scroll or >50 items)
- CriarContext split into smaller contexts (FonteContext, TextoBaseContext, ConfigContext)
- SWA API proxy routing to eliminate CORS entirely
- React Server Components (major architecture change)

## Out of Scope

- **Full rewrite of database.py** — Too risky for a 131KB file. Surgical edits only.
- **Redux/Zustand migration** — TanStack Query handles server state; Context is fine for client state.
- **GraphQL** — Over-engineering for TMC's API surface.
- **Multi-region deployment** — Single-region is sufficient for Brazilian newsroom users.

## Traceability

| Requirement | Phase | Plan |
|-------------|-------|------|
| QW-01..QW-07 | Phase 5 | — |
| DB-01..DB-09 | Phase 6 | — |
| FE-01..FE-06 | Phase 7 | — |
| CACHE-01..CACHE-05 | Phase 8 | — |
| PAG-01..PAG-04 | Phase 9 | — |
| INFRA-01..INFRA-06 | Phase 10 | — |
