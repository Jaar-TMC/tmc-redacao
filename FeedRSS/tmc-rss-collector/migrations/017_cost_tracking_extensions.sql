-- Migration 017: Extend llm_usage_log with user/action tracking for cost dashboard
-- Adds user attribution, source attribution, action classification, and cache token tracking

-- Add new columns to existing llm_usage_log table
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('llm_usage_log') AND name = 'user_id')
    ALTER TABLE llm_usage_log ADD user_id UNIQUEIDENTIFIER NULL;

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('llm_usage_log') AND name = 'source_id')
    ALTER TABLE llm_usage_log ADD source_id UNIQUEIDENTIFIER NULL;

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('llm_usage_log') AND name = 'action_type')
    ALTER TABLE llm_usage_log ADD action_type VARCHAR(50) NULL;
-- action_type values: 'generate_article', 'edit_article', 'fact_check_scan',
--   'deep_verify', 'extract_topics', 'merge_topics', 'generate_tags',
--   'research', 'system_rss', 'system_embedding', 'system_scoring',
--   'system_clustering', 'system_clustering_maintenance'

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('llm_usage_log') AND name = 'cache_read_tokens')
    ALTER TABLE llm_usage_log ADD cache_read_tokens INT NULL;

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('llm_usage_log') AND name = 'cache_creation_tokens')
    ALTER TABLE llm_usage_log ADD cache_creation_tokens INT NULL;

-- Indexes for cost dashboard queries
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_llm_usage_user' AND object_id = OBJECT_ID('llm_usage_log'))
    CREATE INDEX IX_llm_usage_user ON llm_usage_log (user_id, created_at DESC);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_llm_usage_source' AND object_id = OBJECT_ID('llm_usage_log'))
    CREATE INDEX IX_llm_usage_source ON llm_usage_log (source_id, created_at DESC)
    WHERE source_id IS NOT NULL;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_llm_usage_action' AND object_id = OBJECT_ID('llm_usage_log'))
    CREATE INDEX IX_llm_usage_action ON llm_usage_log (action_type, created_at DESC);

-- Covering index for "today" view with granularity=hour
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_llm_usage_hourly' AND object_id = OBJECT_ID('llm_usage_log'))
    CREATE INDEX IX_llm_usage_hourly ON llm_usage_log (created_at, action_type)
    INCLUDE (user_id, input_cost_usd, output_cost_usd, input_tokens, output_tokens);
