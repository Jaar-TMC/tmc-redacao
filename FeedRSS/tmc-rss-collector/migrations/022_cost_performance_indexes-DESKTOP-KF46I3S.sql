-- Migration 022: Performance indexes for cost dashboard and score filter
-- Eliminates key lookups on cost page queries and table scans on score-only filter

-- Index 1 (D-08): Covering index for cost page date-range queries on llm_usage_log
-- Covers: get_cost_overview, get_cost_trends, get_cost_breakdown, get_cost_by_user
-- The INCLUDE columns match the SELECT list in cost_queries.py (input_cost_usd, output_cost_usd,
-- task_type, user_id) so the query engine can satisfy these queries without key lookups.
-- Note: Migration 009 created IX_llm_usage_log_created (basic). This new index IX_llm_usage_created
-- has a broader INCLUDE set (adds task_type, user_id, input_cost_usd, output_cost_usd) to serve
-- the cost page queries without hitting the clustered index.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_llm_usage_created' AND object_id = OBJECT_ID('llm_usage_log'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_llm_usage_created
    ON llm_usage_log (created_at)
    INCLUDE (model, task_type, input_tokens, output_tokens, input_cost_usd, output_cost_usd, user_id);
END;
GO

-- Index 2 (D-09): Filtered index for score-only filter (no classification filter)
-- Serves queries where user selects "All" in score filter dropdown with is_deleted = 0 predicate.
-- More selective than IX_articles_score_order (migration 013) which lacks the is_deleted filter.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_articles_score_filter' AND object_id = OBJECT_ID('collected_articles'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_articles_score_filter
    ON collected_articles (total_score DESC, published_at DESC)
    WHERE is_deleted = 0 AND total_score IS NOT NULL;
END;
GO

-- Index 3 (D-10): Covering index for Exa/embedding cost queries on api_usage_log
-- Covers: cost_queries.py Exa costs and embedding costs queries (provider + status + cost_usd).
-- Note: Migration 018 created IX_api_usage_created (basic, no INCLUDE). This index uses a
-- distinct name IX_api_usage_created_covering and adds INCLUDE (provider, status, cost_usd)
-- to serve WHERE provider = %s AND status = %s queries without key lookups.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_api_usage_created_covering' AND object_id = OBJECT_ID('api_usage_log'))
BEGIN
    CREATE NONCLUSTERED INDEX IX_api_usage_created_covering
    ON api_usage_log (created_at)
    INCLUDE (provider, status, cost_usd);
END;
GO
