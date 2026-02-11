-- Migration 004: Generation Audit Trail
-- Tracks every article generation request for debugging, quality analysis, and compliance.
-- Created: 2026-02-10

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'generation_audit_trail')
BEGIN
    CREATE TABLE generation_audit_trail (
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        article_id UNIQUEIDENTIFIER NULL,
        theme_id UNIQUEIDENTIFIER NULL,

        -- Request
        request_payload NVARCHAR(MAX) NULL,  -- JSON: texto_base, categoria, tom, etc.
        system_prompt_hash VARCHAR(64) NULL,  -- SHA256 of system prompt (for tracking prompt changes)
        user_prompt_text NVARCHAR(MAX) NULL,

        -- Enrichment (Phase 1)
        enrichment_result NVARCHAR(MAX) NULL,  -- JSON: success, key_facts count, source_urls, verified_chars

        -- Generation (Phase 2)
        raw_llm_response NVARCHAR(MAX) NULL,

        -- Verification (Phase 3)
        verification_result NVARCHAR(MAX) NULL,  -- JSON: full verification metadata

        -- CoVe (Phase 3.5)
        cove_applied BIT DEFAULT 0,
        cove_reclassified INT DEFAULT 0,

        -- Safety gates
        safety_gate_decision VARCHAR(20) NULL,  -- 'allowed' | 'blocked' | 'human_review'
        confidence_score FLOAT NULL,
        risk_level VARCHAR(20) NULL,
        publish_blocked BIT DEFAULT 0,
        block_reason NVARCHAR(500) NULL,

        -- Timings
        phase_timings NVARCHAR(MAX) NULL,  -- JSON: {enrichment_ms, generation_ms, verification_ms, cove_ms}
        total_duration_ms INT NULL,

        created_at DATETIME2 DEFAULT GETUTCDATE()
    );

    -- Index for querying by article
    CREATE INDEX IX_generation_audit_article_id
        ON generation_audit_trail (article_id)
        WHERE article_id IS NOT NULL;

    -- Index for querying by date and risk
    CREATE INDEX IX_generation_audit_created_risk
        ON generation_audit_trail (created_at DESC, risk_level);

    -- Index for blocked articles
    CREATE INDEX IX_generation_audit_blocked
        ON generation_audit_trail (publish_blocked, created_at DESC)
        WHERE publish_blocked = 1;

    PRINT 'Created generation_audit_trail table with indexes';
END
ELSE
BEGIN
    PRINT 'generation_audit_trail table already exists, skipping';
END
