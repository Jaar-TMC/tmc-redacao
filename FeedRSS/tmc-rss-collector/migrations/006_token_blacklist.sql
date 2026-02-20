-- Migration 006: Token Blacklist
-- Token blacklist for JWT logout/revocation.
-- Created: 2026-02-20

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'token_blacklist')
BEGIN
    CREATE TABLE token_blacklist (
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        token_jti VARCHAR(64) NOT NULL,
        user_id UNIQUEIDENTIFIER NOT NULL,
        expires_at DATETIME2 NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

        CONSTRAINT FK_token_blacklist_user FOREIGN KEY (user_id)
            REFERENCES users (id)
    );

    -- Unique index on JTI for fast lookup during token validation
    CREATE UNIQUE INDEX IX_token_blacklist_jti
        ON token_blacklist (token_jti);

    -- Index for cleanup of expired tokens
    CREATE INDEX IX_token_blacklist_expires
        ON token_blacklist (expires_at);

    PRINT 'Created token_blacklist table with indexes';
END
ELSE
BEGIN
    PRINT 'token_blacklist table already exists, skipping';
END
