-- Migration 005: Auth Users
-- Users table for authentication and authorization.
-- Created: 2026-02-20

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'users')
BEGIN
    CREATE TABLE users (
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        name NVARCHAR(255) NOT NULL,
        email NVARCHAR(255) NOT NULL,
        password_hash NVARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'user',
        avatar NVARCHAR(500) NULL,
        is_new_user BIT NOT NULL DEFAULT 1,
        is_active BIT NOT NULL DEFAULT 1,
        last_login DATETIME2 NULL,
        failed_login_attempts INT NOT NULL DEFAULT 0,
        locked_until DATETIME2 NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

        CONSTRAINT UQ_users_email UNIQUE (email),
        CONSTRAINT CK_users_role CHECK (role IN ('admin', 'user'))
    );

    -- Index for email lookups (active users only)
    CREATE INDEX IX_users_email
        ON users (email)
        WHERE is_active = 1;

    -- Index for role-based queries (active users only)
    CREATE INDEX IX_users_role
        ON users (role)
        WHERE is_active = 1;

    PRINT 'Created users table with indexes';
END
ELSE
BEGIN
    PRINT 'users table already exists, skipping';
END
