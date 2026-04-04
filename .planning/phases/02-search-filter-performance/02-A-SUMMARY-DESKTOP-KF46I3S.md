---
phase: 02-search-filter-performance
plan: A
subsystem: database
tags: [azure-sql, full-text-search, indexes, migrations, performance]

# Dependency graph
requires: []
provides:
  - ArticleCatalog full-text catalog in Azure SQL (Brazilian Portuguese, Language 1046)
  - Full-text index on collected_articles(title, preview, tags) for FREETEXT predicate
  - IX_llm_usage_created covering index for cost dashboard date-range queries
  - IX_articles_score_filter filtered index for score-only article filter (is_deleted=0)
  - IX_api_usage_created_covering covering index for Exa/embedding cost queries
affects:
  - 02-B-queries (FREETEXT predicate depends on ArticleCatalog being created first)
  - cost_queries.py (IX_llm_usage_created, IX_api_usage_created_covering eliminate key lookups)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Idempotent migrations: all CREATE statements wrapped in IF NOT EXISTS guards"
    - "Covering indexes: INCLUDE clause matches SELECT list in cost_queries.py to avoid key lookups"
    - "Filtered indexes: WHERE is_deleted=0 narrows index scope for soft-deleted tables"

key-files:
  created:
    - FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql
    - FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql
  modified: []

key-decisions:
  - "Used IX_api_usage_created_covering instead of IX_api_usage_created to avoid naming conflict with migration 018 which already creates a basic IX_api_usage_created"
  - "KEY INDEX PK_collected_articles: used convention name since collected_articles predates migration 001 and no migration defines the table schema — added verification query comment in migration"
  - "IX_articles_score_filter adds is_deleted=0 to WHERE clause, making it more selective than existing IX_articles_score_order from migration 013 which only filters total_score IS NOT NULL"

patterns-established:
  - "Migration naming: sequential 3-digit prefix (021, 022) after latest migration (020)"
  - "Idempotency: every statement guarded by IF NOT EXISTS — safe for re-runs and partial failures"

requirements-completed: [D-01, D-02, D-03, D-07, D-08, D-09]

# Metrics
duration: 15min
completed: 2026-04-01
---

# Phase 02 Plan A: DBA Migrations Summary

**Full-text catalog ArticleCatalog with Portuguese Language 1046 and 3 covering/filtered indexes for cost dashboard and score filter performance**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-01T00:00:00Z
- **Completed:** 2026-04-01T00:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created migration 021: ArticleCatalog full-text catalog + full-text index on `collected_articles(title, preview, tags)` with Language 1046 (Brazilian Portuguese), enabling FREETEXT predicate to replace LIKE '%term%' table scans
- Created migration 022: 3 nonclustered indexes — IX_llm_usage_created (covering, for cost page), IX_articles_score_filter (filtered, for score-only filter), IX_api_usage_created_covering (covering, for Exa/embedding cost queries)
- All 5 SQL statements are idempotent (IF NOT EXISTS guards)

## Task Commits

Each task was committed atomically:

1. **Task 1: Full-text search migration (021)** - `f12249d` (feat)
2. **Task 2: Performance indexes migration (022)** - `1e0e49c` (feat)

## Files Created/Modified
- `FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql` - Full-text catalog ArticleCatalog + index on collected_articles(title, preview, tags) with Language 1046
- `FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql` - 3 covering/filtered nonclustered indexes for cost dashboard and score filter

## Decisions Made
- **IX_api_usage_created_covering vs IX_api_usage_created:** Migration 018 already creates `IX_api_usage_created` as a basic index without INCLUDE. Used distinct name `IX_api_usage_created_covering` to avoid the IF NOT EXISTS guard silently skipping the covering version at runtime.
- **KEY INDEX PK_collected_articles:** `collected_articles` predates migration 001 so no SQL DDL defines the table. Added a verification query comment in the migration for the DBA to confirm the actual PK name before running.
- **IX_articles_score_filter vs IX_articles_score_order:** Migration 013 creates `IX_articles_score_order` with `WHERE total_score IS NOT NULL`. The new index adds `AND is_deleted = 0` making it viable for the score filter endpoint that always excludes soft-deleted articles.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Renamed IX_api_usage_created to IX_api_usage_created_covering**
- **Found during:** Task 2 (performance indexes migration)
- **Issue:** Migration 018 already creates `IX_api_usage_created` as a basic index on `api_usage_log(created_at DESC)`. Plan used the same name for the covering version — the IF NOT EXISTS guard would silently skip it, leaving the covering index never created.
- **Fix:** Used `IX_api_usage_created_covering` as the index name and updated the plan note in the migration comment.
- **Files modified:** FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql
- **Verification:** grep IX_api_usage_created_covering migration 022 — unique name, no conflict
- **Committed in:** 1e0e49c (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - naming conflict bug)
**Impact on plan:** Necessary to ensure the covering index is actually created at runtime. Acceptance criteria for D-10 are still fully met; only the index name differs from the plan spec.

## Issues Encountered
- Migration 018 naming conflict: discovered during Task 2 read-first analysis. Resolved with Rule 1 auto-fix (renamed to IX_api_usage_created_covering).

## User Setup Required
Run migrations via the standard migration runner after deploying:
```bash
cd FeedRSS/tmc-rss-collector
python scripts/run_migrations.py
```
Both migrations are idempotent — safe to re-run.

**Note on PK_collected_articles:** Before running migration 021, verify the primary key constraint name with:
```sql
SELECT name FROM sys.indexes WHERE object_id = OBJECT_ID('collected_articles') AND is_primary_key = 1
```
If the name differs from `PK_collected_articles`, update migration 021 accordingly.

## Next Phase Readiness
- Migration 021 provides the ArticleCatalog prerequisite that Plan B (02-B-queries) requires for FREETEXT predicate usage in database.py
- Migration 022 indexes are in place; cost_queries.py will benefit automatically from IX_llm_usage_created and IX_api_usage_created_covering on the next query execution
- No blockers for Plan B or Plan C execution

## Known Stubs
None — migration files contain complete SQL DDL, no placeholders or partial implementations.

---
*Phase: 02-search-filter-performance*
*Completed: 2026-04-01*

## Self-Check: PASSED

- FOUND: FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql
- FOUND: FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql
- FOUND: .planning/phases/02-search-filter-performance/02-A-SUMMARY.md
- FOUND commit: f12249d (Task 1)
- FOUND commit: 1e0e49c (Task 2)
