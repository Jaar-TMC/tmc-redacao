-- Migration 018: Create api_usage_log, daily_cost_summary, and daily_cost_detail tables
-- Supports non-LLM cost tracking (Exa, embeddings) and pre-aggregated dashboard queries

-- ========================================
-- api_usage_log — for non-LLM API costs
-- ========================================
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'api_usage_log')
CREATE TABLE api_usage_log (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    correlation_id VARCHAR(64) NULL,
    user_id UNIQUEIDENTIFIER NULL,
    source_id UNIQUEIDENTIFIER NULL,
    action_type VARCHAR(50) NULL,
    provider VARCHAR(30) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    request_count INT DEFAULT 1,
    input_units INT NULL,
    cost_usd DECIMAL(10,6) NULL,
    latency_ms INT NULL,
    status VARCHAR(10) DEFAULT 'success',
    error_message NVARCHAR(500) NULL,
    metadata NVARCHAR(MAX) NULL,
    created_at DATETIME2 DEFAULT GETUTCDATE()
);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_api_usage_created' AND object_id = OBJECT_ID('api_usage_log'))
    CREATE INDEX IX_api_usage_created ON api_usage_log (created_at DESC);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_api_usage_provider' AND object_id = OBJECT_ID('api_usage_log'))
    CREATE INDEX IX_api_usage_provider ON api_usage_log (provider, created_at DESC);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_api_usage_action' AND object_id = OBJECT_ID('api_usage_log'))
    CREATE INDEX IX_api_usage_action ON api_usage_log (action_type, created_at DESC);

-- ========================================
-- daily_cost_summary — pre-aggregated for fast overview/trends
-- ========================================
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'daily_cost_summary')
CREATE TABLE daily_cost_summary (
    id INT IDENTITY PRIMARY KEY,
    date DATE NOT NULL,
    provider VARCHAR(30) NOT NULL,
    action_type VARCHAR(50) NOT NULL DEFAULT 'unknown',
    call_count INT DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(12,6) DEFAULT 0,
    avg_latency_ms INT NULL
);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_daily_cost_summary' AND object_id = OBJECT_ID('daily_cost_summary'))
    CREATE UNIQUE INDEX UX_daily_cost_summary ON daily_cost_summary (date, provider, action_type);

-- ========================================
-- daily_cost_detail — per-user/source breakdown for drill-down
-- Uses sentinel UUIDs for NULL handling in unique indexes
-- ========================================
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'daily_cost_detail')
CREATE TABLE daily_cost_detail (
    id INT IDENTITY PRIMARY KEY,
    date DATE NOT NULL,
    provider VARCHAR(30) NOT NULL,
    model VARCHAR(100) NOT NULL DEFAULT '',
    task_type VARCHAR(50) NOT NULL DEFAULT '',
    action_type VARCHAR(50) NOT NULL DEFAULT 'unknown',
    user_id UNIQUEIDENTIFIER NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    source_id UNIQUEIDENTIFIER NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
    call_count INT DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(12,6) DEFAULT 0,
    avg_latency_ms INT NULL
);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_daily_cost_detail' AND object_id = OBJECT_ID('daily_cost_detail'))
    CREATE UNIQUE INDEX UX_daily_cost_detail ON daily_cost_detail (date, provider, model, task_type, action_type, user_id, source_id);
