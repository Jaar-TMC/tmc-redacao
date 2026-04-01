# Phase 2: Search/Filter Performance - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 4 P0 performance issues: compound word search freezes (LIKE full table scan), score filter slow (missing composite index), costs page slow (sequential queries + CAST on JOIN + missing date indexes), and general filter degradation (facet cache invalidates on every keystroke).

**3 parallel implementation tracks:**
- Track A (DBA): SQL migrations for full-text index + performance indexes
- Track B (Query): Replace LIKE with FREETEXT, fix CAST on JOIN, decouple facet cache
- Track C (Frontend): Increase search debounce to 500ms (AbortController already exists)

</domain>

<decisions>
## Implementation Decisions

### Full-Text Search (Tasks 2.1 + 2.2)
- **D-01:** Use `FREETEXT` (not `CONTAINS`) — simpler syntax, no boolean operators needed. Azure SQL's Portuguese word breaker (Language 1046) handles compound words like "seleção brasileira" natively.
- **D-02:** Create `FULLTEXT CATALOG ArticleCatalog` and index on `collected_articles(title, preview, tags)` with `LANGUAGE 1046` (Brazilian Portuguese).
- **D-03:** Migration file: `021_fulltext_search.sql` (plan said 014 but migrations are at 020).
- **D-04:** Graceful fallback — code MUST check if full-text catalog exists before using FREETEXT. If not ready, fall back to existing LIKE queries. This allows deploying code before the index finishes building.
  ```python
  # Pseudocode for fallback:
  # try FREETEXT first → except (catalog not found) → fall back to LIKE
  ```
- **D-05:** Replace ALL 5 LIKE conditions at `database.py:503-517` with a single `FREETEXT((a.title, a.preview, a.tags), %s)` predicate. Also replace the tag LIKE at lines 519-523.
- **D-06:** Remove `COLLATE Latin1_General_CI_AI` from search conditions — FREETEXT uses the full-text index's language configuration, not collation.

### Performance Indexes (Task 2.3)
- **D-07:** Migration file: `022_cost_performance_indexes.sql` (plan said 015).
- **D-08:** Covering index on `llm_usage_log(created_at) INCLUDE(model, task_type, input_tokens, output_tokens, cost_usd, user_id)` — avoids key lookups for cost page queries.
- **D-09:** Filtered index on `collected_articles(total_score DESC, published_at DESC) WHERE is_deleted = 0 AND total_score IS NOT NULL` — serves "All scores" view without classification filter.
- **D-10:** Consider adding index on `api_usage_log(created_at) INCLUDE(provider, status, cost_usd)` for Exa/embedding cost queries at `cost_queries.py:145-164`.

### CAST Fix on JOIN (Task 2.4)
- **D-11:** Both `users.id` and `llm_usage_log.user_id` are `UNIQUEIDENTIFIER` (confirmed in migrations 005 and 017). The double `CAST(... AS VARCHAR(36))` at `cost_queries.py:333` is completely unnecessary.
- **D-12:** Fix: Replace `CAST(l.user_id AS VARCHAR(36)) = CAST(u.id AS VARCHAR(36))` with `l.user_id = u.id`. This is the only change needed — column types already match.

### Facet Cache Decoupling (Task 2.5)
- **D-13:** Current problem: cache at `articles_api.py:106` is keyed on `(category, tag, source, period, search, classification)` — invalidates on every search keystroke.
- **D-14:** Fix: Remove `filter_key` from cache invalidation check entirely. Use time-based TTL only (existing `FACET_CACHE_TTL = 300` seconds is already correct).
- **D-15:** Rationale: Facet counts (categories and tags) are global aggregations used for dropdown population. They don't need per-search-term freshness — approximate counts that refresh every 5 minutes are acceptable. Users won't notice stale facet counts.
- **D-16:** Implementation: Remove the `_facet_cache["filter_key"]` check at line 111. Keep only the `cache_age < FACET_CACHE_TTL` check. Delete the `filter_key` storage at line 169.

### Frontend Search Optimization (Task 2.6)
- **D-17:** AbortController already exists in `RedacaoPage.jsx:77,157` with proper cleanup. No new AbortController implementation needed — just verify it correctly cancels on filter changes.
- **D-18:** Increase FilterBar.jsx search debounce from 300ms to 500ms (line 100). The RedacaoPage has a separate 150ms fetch debounce (line 161) — keep that as-is. Combined effective debounce: ~500ms (FilterBar waits) + 150ms (fetch coalescing) = 650ms total, which is fine for search UX.
- **D-19:** Request deduplication already handled by `apiCache.js` — no additional dedup needed.

### Claude's Discretion
- Whether to add `ONLINE = ON` to index creation for zero-downtime migration (depends on Azure SQL tier)
- Whether to add a `created_at` index on `api_usage_log` (D-10) — depends on table size
- Error handling approach for FREETEXT fallback (try/except vs pre-check query)
- Whether the 150ms fetch debounce in RedacaoPage should be adjusted alongside the FilterBar change

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Plan
- `docs/plans/2026-04-01-p0-implementation-plan.md` section Phase 2 — Full task breakdown with line numbers, verification checklist, parallel track structure

### Backlog
- `docs/backlog-prioritizado-abril-2026.md` — P0 Performance section: compound search, score filter, costs page, general filters

### Backend — Search Queries
- `FeedRSS/tmc-rss-collector/services/database.py:495-527` — `_build_article_filters()` with 5 LIKE conditions + tag LIKE. This is the primary search bottleneck.

### Backend — Cost Queries
- `FeedRSS/tmc-rss-collector/services/cost_queries.py:127-189` — `get_cost_overview()` with 6 sequential SQL queries
- `FeedRSS/tmc-rss-collector/services/cost_queries.py:325-338` — `get_cost_by_user()` with double CAST on JOIN

### Backend — Facet Cache
- `FeedRSS/tmc-rss-collector/functions/articles_api.py:29,96-169` — FACET_CACHE_TTL=300, filter_key-based cache invalidation

### Backend — Migrations
- `FeedRSS/tmc-rss-collector/migrations/005_auth_users.sql` — `users.id` is UNIQUEIDENTIFIER
- `FeedRSS/tmc-rss-collector/migrations/017_cost_tracking_extensions.sql` — `llm_usage_log.user_id` is UNIQUEIDENTIFIER
- `FeedRSS/tmc-rss-collector/migrations/013_denormalize_scores.sql` — Score denormalization (context for index design)

### Frontend — Search/Filter
- `tmc-redacao/src/components/ui/FilterBar.jsx:86-101` — 300ms search debounce with useCallback
- `tmc-redacao/src/pages/RedacaoPage.jsx:76-170` — AbortController + 150ms fetch debounce + filter change detection

### Phase 1 Context (prior decisions)
- `.planning/phases/01-session-persistence/01-CONTEXT.md` — Auth fixes complete, surgical edit pattern established

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AbortController` pattern in RedacaoPage.jsx:77,157 — already cancels in-flight requests on filter change
- `apiCache.js` — TTL-based request deduplication already prevents duplicate API calls
- `FACET_CACHE_TTL = 300` at articles_api.py:29 — correct value, just needs decoupling from filter_key
- `fetchDebounceRef` in RedacaoPage.jsx:81 — 150ms debounce timer for fetch coalescing
- `transformCategories()` and `transformSources()` utils — handle facet data transformation

### Established Patterns
- Backend: pymssql with connection pooling (`database.py`), parameterized queries everywhere
- Backend: `run_db()` async wrapper for all database calls from async handlers
- Frontend: React Context for filter state (`FiltersProvider`), not Zustand/Redux
- Frontend: `useCallback` + `useRef` for debounce timers (not lodash.debounce)
- Frontend: AbortController per-effect with cleanup in useEffect return

### Integration Points
- `database.py:_build_article_filters()` — called by `get_articles()` at line 529. Any search change must maintain the same return signature: `(where_clause, params, needs_scores_join)`
- `articles_api.py:list_articles()` — orchestrates articles + facets. Facet cache changes are isolated here.
- `cost_queries.py` — standalone module, no shared state. Changes are safe to make independently.
- Migration runner: `scripts/run_migrations.py` — executes .sql files in numeric order

</code_context>

<specifics>
## Specific Ideas

- The full-text index creation can take time on large tables — consider `ONLINE = ON` and schedule for low-traffic window
- Tag search at `database.py:519-523` also uses LIKE — include this in the FREETEXT conversion since tags are in the full-text index
- The `ISNULL` wrapper in cost queries is correct (handles NULL costs) — preserve these when removing CAST
- Cost page has 6 sequential queries that could potentially be parallelized with `asyncio.gather()` in the handler, but this is a separate optimization beyond the index/CAST fixes

</specifics>

<deferred>
## Deferred Ideas

- **Cost query parallelization**: Could use `asyncio.gather()` to run the 6 cost overview queries concurrently instead of sequentially — belongs in a P2 optimization phase
- **Costs page default filter "today"**: Backlog item P2 — change default period filter to "today" instead of current default
- **Full-text search with boolean operators**: CONTAINS would allow `"seleção" AND "brasileira"` syntax — future P1 enhancement if users want advanced search

</deferred>

---

*Phase: 02-search-filter-performance*
*Context gathered: 2026-04-01*
