-- Migration 024: Covering index for cost dashboard — eliminates all key lookups
--
-- ROOT CAUSE: The `status` column is absent from every existing index on llm_usage_log.
-- Every cost query has AND status = 'success' in its WHERE clause. Without `status` in
-- the index, SQL Server must do a key lookup into the clustered index (NEWID-fragmented,
-- random I/O) for every row that passes the date-range seek — catastrophic at scale.
--
-- Additionally `action_type`, `source_id`, and `correlation_id` are missing from the
-- covering index, causing further key lookups for GROUP BY and COUNT(DISTINCT) operations.
--
-- This migration:
-- 1. Drops IX_llm_usage_log_created (009) — narrow, superseded by 022
-- 2. Drops IX_llm_usage_created (022) — replaces with wider version below
-- 3. Creates IX_llm_usage_cost_covering — fully covers all 5 cost dashboard queries
--
-- After this migration, all cost queries use index seek + INCLUDE columns only.
-- No key lookups. Expected query time reduction: ~100x for large tables.

-- Step 1: Drop narrow 009 index (superseded)
IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_usage_log_created'
      AND object_id = OBJECT_ID('llm_usage_log')
)
    DROP INDEX IX_llm_usage_log_created ON llm_usage_log;
GO

-- Step 2: Drop 022 index (being replaced with wider version)
IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_usage_created'
      AND object_id = OBJECT_ID('llm_usage_log')
)
    DROP INDEX IX_llm_usage_created ON llm_usage_log;
GO

-- Step 3: Create the fully-covering index
-- Key column : created_at   (date-range seek used by every cost query)
-- INCLUDE    : status        (eliminates lookup for AND status = 'success')
--              action_type   (eliminates lookup for GROUP BY + filter in breakdown/overview)
--              model         (eliminates lookup for sonnet/haiku CASE expressions)
--              task_type     (retained from 022)
--              input_tokens, output_tokens, input_cost_usd, output_cost_usd  (aggregates)
--              user_id       (eliminates lookup for per-user JOIN key)
--              source_id     (eliminates lookup for per-source filter/JOIN)
--              correlation_id (eliminates lookup for COUNT(DISTINCT correlation_id))
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_llm_usage_cost_covering'
      AND object_id = OBJECT_ID('llm_usage_log')
)
    CREATE NONCLUSTERED INDEX IX_llm_usage_cost_covering
    ON llm_usage_log (created_at)
    INCLUDE (
        status,
        action_type,
        model,
        task_type,
        input_tokens,
        output_tokens,
        input_cost_usd,
        output_cost_usd,
        user_id,
        source_id,
        correlation_id
    );
GO
