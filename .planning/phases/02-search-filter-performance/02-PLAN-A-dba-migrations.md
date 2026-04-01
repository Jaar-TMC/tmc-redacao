---
phase: 02-search-filter-performance
plan: A
type: execute
wave: 1
depends_on: []
files_modified:
  - FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql
  - FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql
autonomous: true
requirements: [D-01, D-02, D-03, D-07, D-08, D-09]

must_haves:
  truths:
    - "Full-text catalog ArticleCatalog exists in Azure SQL with Portuguese word breaker (Language 1046)"
    - "Full-text index covers title, preview, tags columns on collected_articles"
    - "Covering index on llm_usage_log(created_at) eliminates key lookups for cost page queries"
    - "Filtered index on collected_articles(total_score) serves score-only filter without table scan"
    - "Compound word search is enabled by this catalog — Plan B FREETEXT predicate depends on it to replace full table scans"
  artifacts:
    - path: "FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql"
      provides: "Full-text catalog and index for Portuguese search"
      contains: "FULLTEXT CATALOG"
    - path: "FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql"
      provides: "Performance indexes for cost page and score filter"
      contains: "IX_llm_usage_created"
  key_links:
    - from: "migrations/021_fulltext_search.sql"
      to: "database.py FREETEXT queries (Track B)"
      via: "Full-text index enables FREETEXT predicate"
      pattern: "FULLTEXT INDEX ON collected_articles"
    - from: "migrations/022_cost_performance_indexes.sql"
      to: "cost_queries.py date-range queries"
      via: "Covering index serves WHERE created_at >= X queries"
      pattern: "IX_llm_usage_created"
---

<objective>
Create two SQL migration files that add full-text search infrastructure and performance indexes to Azure SQL.

Purpose: Track A provides the database-level foundation that makes Track B's query optimizations effective. The full-text index enables FREETEXT to replace LIKE (D-01/D-02), and the covering/filtered indexes eliminate table scans on the cost and score filter pages (D-08/D-09).

Output: Two migration files (021, 022) ready to run via `scripts/run_migrations.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-search-filter-performance/02-CONTEXT.md

<interfaces>
<!-- Migration runner expects .sql files in numeric order in migrations/ directory -->
<!-- scripts/run_migrations.py executes them sequentially by filename -->

From FeedRSS/tmc-rss-collector/migrations/ (existing numbering):
- Latest: 020_tag_aggregations.sql
- Next available: 021, 022

From FeedRSS/tmc-rss-collector/services/database.py (table the index targets):
- Table: collected_articles
- Columns for full-text: title, preview, tags
- Primary key: PK_collected_articles (needed as KEY INDEX for full-text)

From FeedRSS/tmc-rss-collector/migrations/013_denormalize_scores.sql:
- Columns: total_score, classification (denormalized into collected_articles)
- Column: is_deleted (soft-delete flag)

From FeedRSS/tmc-rss-collector/migrations/017_cost_tracking_extensions.sql:
- Table: llm_usage_log
- Columns: created_at, model, task_type, input_tokens, output_tokens, cost_usd, user_id

From FeedRSS/tmc-rss-collector/migrations/018_api_usage_and_daily_summary.sql:
- Table: api_usage_log
- Columns: created_at, provider, status, cost_usd
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create full-text search migration (021)</name>
  <files>FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql</files>

  <read_first>
    - FeedRSS/tmc-rss-collector/migrations/020_tag_aggregations.sql (see migration style/patterns)
    - FeedRSS/tmc-rss-collector/migrations/012_performance_indexes.sql (see existing index patterns)
    - .planning/phases/02-search-filter-performance/02-CONTEXT.md (decisions D-01 through D-06)
  </read_first>

  <action>
    Create `FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql` with the following SQL (per D-01, D-02, D-03):

    ```sql
    -- Migration 021: Full-text search catalog and index for Portuguese word breaking
    -- Enables FREETEXT queries to replace LIKE '%term%' full table scans
    -- Language 1046 = Brazilian Portuguese (handles compound words like "selecao brasileira")

    -- Step 1: Create full-text catalog (idempotent check)
    IF NOT EXISTS (SELECT 1 FROM sys.fulltext_catalogs WHERE name = 'ArticleCatalog')
    BEGIN
        CREATE FULLTEXT CATALOG ArticleCatalog AS DEFAULT;
    END;
    GO

    -- Step 2: Create full-text index on collected_articles
    -- KEY INDEX must reference the table's primary key
    -- LANGUAGE 1046 enables Portuguese word breaker for all 3 columns
    IF NOT EXISTS (
        SELECT 1 FROM sys.fulltext_indexes fi
        JOIN sys.objects o ON fi.object_id = o.object_id
        WHERE o.name = 'collected_articles'
    )
    BEGIN
        CREATE FULLTEXT INDEX ON collected_articles (
            title LANGUAGE 1046,
            preview LANGUAGE 1046,
            tags LANGUAGE 1046
        )
        KEY INDEX PK_collected_articles
        ON ArticleCatalog;
    END;
    GO
    ```

    Notes:
    - Both statements are wrapped in IF NOT EXISTS for idempotent re-runs.
    - The index population starts automatically after creation (Azure SQL default).
    - Do NOT add `ONLINE = ON` — Azure SQL Full-Text is always online by default; the syntax would error on non-Enterprise tiers.
    - The KEY INDEX name `PK_collected_articles` must match the actual primary key constraint name. If the executor finds a different PK name, substitute it. Verify with: `SELECT name FROM sys.indexes WHERE object_id = OBJECT_ID('collected_articles') AND is_primary_key = 1`.
  </action>

  <verify>
    <automated>grep -c "FULLTEXT CATALOG\|FULLTEXT INDEX\|LANGUAGE 1046\|PK_collected_articles" "FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql"</automated>
  </verify>

  <acceptance_criteria>
    - File `FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql` exists
    - Contains `CREATE FULLTEXT CATALOG ArticleCatalog` (per D-02)
    - Contains `LANGUAGE 1046` exactly 3 times (title, preview, tags per D-02)
    - Contains `KEY INDEX PK_collected_articles` (or actual PK name)
    - Contains `IF NOT EXISTS` guards for both CREATE statements
    - Does NOT contain `ONLINE = ON` (Azure SQL full-text is always online)
    - Contains `title`, `preview`, and `tags` as indexed columns (per D-02)
  </acceptance_criteria>

  <done>Migration 021 creates ArticleCatalog and full-text index on collected_articles(title, preview, tags) with Language 1046 (Brazilian Portuguese). File is idempotent and ready for run_migrations.py.</done>
</task>

<task type="auto">
  <name>Task 2: Create performance indexes migration (022)</name>
  <files>FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql</files>

  <read_first>
    - FeedRSS/tmc-rss-collector/migrations/012_performance_indexes.sql (see existing index naming/style)
    - FeedRSS/tmc-rss-collector/services/cost_queries.py:127-189 (see which columns the cost queries filter/select)
    - FeedRSS/tmc-rss-collector/services/cost_queries.py:145-164 (see api_usage_log query patterns)
    - .planning/phases/02-search-filter-performance/02-CONTEXT.md (decisions D-07 through D-10)
  </read_first>

  <action>
    Create `FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql` with the following SQL (per D-07, D-08, D-09, D-10):

    ```sql
    -- Migration 022: Performance indexes for cost dashboard and score filter
    -- Eliminates key lookups on cost page queries and table scans on score-only filter

    -- Index 1 (D-08): Covering index for cost page date-range queries on llm_usage_log
    -- Covers: get_cost_overview, get_cost_trends, get_cost_breakdown, get_cost_by_user
    -- The INCLUDE columns match the SELECT list in cost_queries.py:128-137
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_llm_usage_created' AND object_id = OBJECT_ID('llm_usage_log'))
    BEGIN
        CREATE NONCLUSTERED INDEX IX_llm_usage_created
        ON llm_usage_log (created_at)
        INCLUDE (model, task_type, input_tokens, output_tokens, input_cost_usd, output_cost_usd, user_id);
    END;
    GO

    -- Index 2 (D-09): Filtered index for "All scores" view (no classification filter)
    -- Serves queries where user selects "All" in score filter dropdown
    -- filtered to skip deleted articles and null scores (the majority of lookups)
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_articles_score_filter' AND object_id = OBJECT_ID('collected_articles'))
    BEGIN
        CREATE NONCLUSTERED INDEX IX_articles_score_filter
        ON collected_articles (total_score DESC, published_at DESC)
        WHERE is_deleted = 0 AND total_score IS NOT NULL;
    END;
    GO

    -- Index 3 (D-10): Covering index for Exa/embedding cost queries on api_usage_log
    -- Covers: cost_queries.py:145-164 (Exa costs + embedding costs by date range)
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_api_usage_created' AND object_id = OBJECT_ID('api_usage_log'))
    BEGIN
        CREATE NONCLUSTERED INDEX IX_api_usage_created
        ON api_usage_log (created_at)
        INCLUDE (provider, status, cost_usd);
    END;
    GO
    ```

    Notes:
    - All three indexes are wrapped in IF NOT EXISTS for idempotent re-runs.
    - Index names follow existing convention: `IX_{table}_{key_column}`.
    - The filtered index on collected_articles uses `WHERE is_deleted = 0` matching the soft-delete pattern.
    - Column names verified from migration 009: `input_cost_usd DECIMAL(10,6)`, `output_cost_usd DECIMAL(10,6)`, `total_cost_usd` (computed persisted). The INCLUDE clause uses the stored columns that cost_queries.py:131 references in its SUM.
    - Note: migration 009 already creates a basic index `IX_llm_usage_log_created ON llm_usage_log(created_at DESC)` with INCLUDE (model, input_tokens, output_tokens, total_cost_usd, latency_ms). Our new index `IX_llm_usage_created` has a broader INCLUDE set (adds task_type, user_id, input_cost_usd, output_cost_usd) to serve the cost page queries without key lookups.
    - D-10 (IX_api_usage_created) is a discretionary addition — included because the table is small and the index is cheap, but not a locked requirement.
  </action>

  <verify>
    <automated>grep -c "IX_llm_usage_created\|IX_articles_score_filter\|IX_api_usage_created\|IF NOT EXISTS" "FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql"</automated>
  </verify>

  <acceptance_criteria>
    - File `FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql` exists
    - Contains `IX_llm_usage_created` index on `llm_usage_log(created_at)` with INCLUDE clause containing `input_cost_usd, output_cost_usd` (per D-08)
    - Contains `IX_articles_score_filter` index on `collected_articles(total_score DESC, published_at DESC)` with WHERE filter (per D-09)
    - Contains `IX_api_usage_created` index on `api_usage_log(created_at)` with INCLUDE clause (per D-10)
    - Contains `IF NOT EXISTS` guard for each CREATE INDEX (3 guards total)
    - Contains `WHERE is_deleted = 0 AND total_score IS NOT NULL` in the filtered index
    - Does NOT contain `DROP INDEX` (additive only, no destructive operations)
  </acceptance_criteria>

  <done>Migration 022 creates 3 performance indexes: covering index on llm_usage_log for cost page, filtered index on collected_articles for score filter, and covering index on api_usage_log for Exa/embedding queries. All idempotent.</done>
</task>

</tasks>

<verification>
After both tasks complete:
1. Both files exist in `FeedRSS/tmc-rss-collector/migrations/` directory
2. Files sort correctly after 020_tag_aggregations.sql (021 before 022)
3. All SQL statements are idempotent (IF NOT EXISTS guards)
4. No destructive operations (no DROP statements)
5. Full-text index targets correct columns: title, preview, tags
6. Performance indexes target correct tables and columns per cost_queries.py query patterns
</verification>

<success_criteria>
- Two migration files created: 021_fulltext_search.sql and 022_cost_performance_indexes.sql
- 021 creates ArticleCatalog + full-text index with Language 1046 on collected_articles(title, preview, tags)
- 022 creates 3 nonclustered indexes: IX_llm_usage_created, IX_articles_score_filter, IX_api_usage_created
- All statements have IF NOT EXISTS idempotency guards
- Files are ready for `python scripts/run_migrations.py`
</success_criteria>

<output>
After completion, create `.planning/phases/02-search-filter-performance/02-A-SUMMARY.md`
</output>
