-- Migration 014: Fact-Check Scans
-- On-demand article safety assessments with ASI (Article Safety Index).
-- Stores scan history for caching, analytics, and audit trail.
-- Created: 2026-03-12

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'fact_check_scans')
BEGIN
    CREATE TABLE fact_check_scans (
        id INT IDENTITY(1,1) PRIMARY KEY,
        scan_id VARCHAR(64) NOT NULL,
        user_id UNIQUEIDENTIFIER NOT NULL,
        user_article_id INT NULL,
        article_text_hash VARCHAR(64) NOT NULL,
        article_char_count INT NOT NULL,
        safety_index INT NOT NULL,
        safety_label VARCHAR(20) NOT NULL,
        total_claims INT NOT NULL DEFAULT 0,
        grounded_claims INT NOT NULL DEFAULT 0,
        fabricated_claims INT NOT NULL DEFAULT 0,
        unverifiable_claims INT NOT NULL DEFAULT 0,
        corroboration_score FLOAT NULL,
        external_factcheck_matches INT NOT NULL DEFAULT 0,
        scan_result NVARCHAR(MAX) NULL,
        scan_duration_ms INT NULL,
        created_at DATETIME2 DEFAULT GETUTCDATE(),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE INDEX IX_fact_check_scans_user
        ON fact_check_scans (user_id, created_at DESC);

    CREATE INDEX IX_fact_check_scans_article
        ON fact_check_scans (user_article_id)
        WHERE user_article_id IS NOT NULL;

    CREATE INDEX IX_fact_check_scans_hash
        ON fact_check_scans (article_text_hash, created_at DESC);

    PRINT 'Created fact_check_scans table with indexes';
END
ELSE
BEGIN
    PRINT 'fact_check_scans table already exists, skipping';
END
