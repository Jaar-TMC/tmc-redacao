-- Migration 008: Auth Audit Log
-- Tracks security events: logins, logouts, password changes, account locks.
-- Created: 2026-02-20

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'auth_audit_log')
BEGIN
    CREATE TABLE auth_audit_log (
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        user_id UNIQUEIDENTIFIER NULL,
        email NVARCHAR(255) NULL,
        action VARCHAR(50) NOT NULL,
        ip_address VARCHAR(45) NULL,
        user_agent NVARCHAR(500) NULL,
        metadata NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

        CONSTRAINT CK_auth_audit_action CHECK (action IN (
            'login_success', 'login_failed', 'logout',
            'password_change', 'password_reset', 'account_locked'
        ))
    );

    -- Index for querying audit events by user
    CREATE INDEX IX_auth_audit_user
        ON auth_audit_log (user_id, created_at DESC)
        WHERE user_id IS NOT NULL;

    -- Index for querying audit events by action type
    CREATE INDEX IX_auth_audit_action
        ON auth_audit_log (action, created_at DESC);

    PRINT 'Created auth_audit_log table with indexes';
END
ELSE
BEGIN
    PRINT 'auth_audit_log table already exists, skipping';
END
