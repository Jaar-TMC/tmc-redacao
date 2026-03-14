-- Migration 016: System settings table for runtime feature flags (AI kill switch)
-- Created: 2026-03-13

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'system_settings')
BEGIN
    CREATE TABLE system_settings (
        setting_key VARCHAR(100) NOT NULL PRIMARY KEY,
        setting_value NVARCHAR(500) NOT NULL,
        updated_by NVARCHAR(200) NULL,
        updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );

    INSERT INTO system_settings (setting_key, setting_value)
    VALUES ('ai_paused', 'false');

    PRINT 'Migration 016: Created system_settings table';
END
ELSE
BEGIN
    PRINT 'Migration 016: system_settings table already exists, skipping';
END
