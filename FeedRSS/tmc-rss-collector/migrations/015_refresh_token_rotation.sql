-- Migration 015: Refresh Token Rotation Support
-- Adds token_family tracking and rotation metadata to token_blacklist

-- Add token_family column
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('token_blacklist') AND name = 'token_family'
)
BEGIN
    ALTER TABLE token_blacklist ADD token_family VARCHAR(64) NULL;
    CREATE INDEX IX_token_blacklist_family ON token_blacklist (token_family);
    PRINT 'Added token_family column with index';
END

-- Add replaced_at column (NULL means revoked by logout, not rotated)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('token_blacklist') AND name = 'replaced_at'
)
BEGIN
    ALTER TABLE token_blacklist ADD replaced_at DATETIME2 NULL;
    PRINT 'Added replaced_at column';
END

-- Add replaced_by_jti column
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('token_blacklist') AND name = 'replaced_by_jti'
)
BEGIN
    ALTER TABLE token_blacklist ADD replaced_by_jti VARCHAR(64) NULL;
    PRINT 'Added replaced_by_jti column';
END
