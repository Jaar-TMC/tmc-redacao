-- Migration 009: LLM Usage Log
-- Tracks every LLM API call for cost analysis, performance monitoring, and model optimization.
-- Created: 2026-03-09

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'llm_usage_log')
BEGIN
    CREATE TABLE llm_usage_log (
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),

        -- Call identification
        correlation_id VARCHAR(64) NULL,          -- Links to generation_audit_trail or other flows
        task_type VARCHAR(50) NOT NULL,            -- 'classification', 'scoring', 'theme_naming', 'event_extraction', 'event_verification', 'enrichment_extraction', 'article_generation', 'claim_extraction', 'cove_verification', 'article_edit', 'story_fusion', 'tag_generation', 'topic_extraction'

        -- Model info
        model VARCHAR(100) NOT NULL,               -- e.g. 'claude-sonnet-4-5', 'claude-haiku-4-5'
        endpoint VARCHAR(500) NULL,                -- API endpoint used
        provider VARCHAR(20) DEFAULT 'anthropic',  -- 'anthropic' or 'azure'

        -- Token usage (from API response)
        input_tokens INT NULL,
        output_tokens INT NULL,
        total_tokens AS (ISNULL(input_tokens, 0) + ISNULL(output_tokens, 0)) PERSISTED,

        -- Cost calculation (USD)
        input_cost_usd DECIMAL(10, 6) NULL,
        output_cost_usd DECIMAL(10, 6) NULL,
        total_cost_usd AS (ISNULL(input_cost_usd, 0) + ISNULL(output_cost_usd, 0)) PERSISTED,

        -- Performance
        latency_ms INT NULL,                       -- Time from request to response
        status VARCHAR(10) NOT NULL DEFAULT 'success',  -- 'success', 'error', 'timeout'
        error_message NVARCHAR(500) NULL,

        -- Response metadata
        response_chars INT NULL,                   -- Length of response text
        stop_reason VARCHAR(20) NULL,              -- 'end_turn', 'max_tokens', etc.

        -- Timestamps
        created_at DATETIME2 DEFAULT GETUTCDATE()
    );

    -- Index for cost analysis by date range
    CREATE INDEX IX_llm_usage_log_created
        ON llm_usage_log (created_at DESC);

    -- Index for model comparison analysis
    CREATE INDEX IX_llm_usage_log_model_task
        ON llm_usage_log (model, task_type, created_at DESC);

    -- Index for correlation with generation audit
    CREATE INDEX IX_llm_usage_log_correlation
        ON llm_usage_log (correlation_id)
        WHERE correlation_id IS NOT NULL;

    -- Index for cost aggregation by task
    CREATE INDEX IX_llm_usage_log_task_cost
        ON llm_usage_log (task_type, created_at DESC)
        INCLUDE (model, input_tokens, output_tokens, total_cost_usd, latency_ms);

    PRINT 'Created llm_usage_log table with indexes';
END
ELSE
BEGIN
    PRINT 'llm_usage_log table already exists, skipping';
END
