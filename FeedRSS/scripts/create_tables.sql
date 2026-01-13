-- ============================================================================
-- TMC Redacao - Feed RSS Collector
-- Database Schema Creation Script
-- Target: Azure SQL Database (bi4ia-tmc.database.windows.net / tmc)
-- ============================================================================
-- Version: 1.0.0
-- Created: 2026-01-07
-- Description: Creates tables for RSS feed collection system
-- ============================================================================

-- ============================================================================
-- TABLE: sources
-- Description: Stores RSS feed source configurations
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[sources]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[sources] (
        [id]              UNIQUEIDENTIFIER    PRIMARY KEY DEFAULT NEWID(),
        [name]            NVARCHAR(255)       NOT NULL,
        [url]             NVARCHAR(2048)      NOT NULL,
        [favicon_url]     NVARCHAR(2048)      NULL,
        [active]          BIT                 DEFAULT 1,
        [frequency]       NVARCHAR(10)        DEFAULT '1h',  -- '15min', '30min', '1h', '2h', '6h'
        [category]        NVARCHAR(100)       NULL,
        [last_fetch]      DATETIME2           NULL,
        [last_error]      NVARCHAR(MAX)       NULL,
        [articles_count]  INT                 DEFAULT 0,
        [created_at]      DATETIME2           DEFAULT GETUTCDATE(),
        [updated_at]      DATETIME2           DEFAULT GETUTCDATE()
    );

    PRINT 'Table [sources] created successfully.';
END
ELSE
BEGIN
    PRINT 'Table [sources] already exists.';
END
GO

-- ============================================================================
-- TABLE: collected_articles
-- Description: Stores articles collected from RSS feeds
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[collected_articles]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[collected_articles] (
        [id]              UNIQUEIDENTIFIER    PRIMARY KEY DEFAULT NEWID(),
        [source_id]       UNIQUEIDENTIFIER    NOT NULL,
        [title]           NVARCHAR(1000)      NOT NULL,
        [content]         NVARCHAR(MAX)       NULL,
        [preview]         NVARCHAR(500)       NULL,
        [url]             NVARCHAR(2048)      NOT NULL,
        [image_url]       NVARCHAR(2048)      NULL,
        [author]          NVARCHAR(255)       NULL,
        [category]        NVARCHAR(100)       NULL,
        [tags]            NVARCHAR(MAX)       NULL,  -- JSON array
        [published_at]    DATETIME2           NULL,
        [collected_at]    DATETIME2           DEFAULT GETUTCDATE(),
        [hash]            NVARCHAR(64)        NOT NULL,

        CONSTRAINT [FK_articles_source] FOREIGN KEY ([source_id])
            REFERENCES [dbo].[sources]([id]) ON DELETE CASCADE,
        CONSTRAINT [UQ_articles_hash] UNIQUE ([hash]),
        CONSTRAINT [UQ_articles_url] UNIQUE ([url])
    );

    PRINT 'Table [collected_articles] created successfully.';
END
ELSE
BEGIN
    PRINT 'Table [collected_articles] already exists.';
END
GO

-- ============================================================================
-- TABLE: collection_logs
-- Description: Stores logs of feed collection operations
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[collection_logs]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[collection_logs] (
        [id]                  UNIQUEIDENTIFIER    PRIMARY KEY DEFAULT NEWID(),
        [source_id]           UNIQUEIDENTIFIER    NULL,
        [started_at]          DATETIME2           NOT NULL,
        [finished_at]         DATETIME2           NULL,
        [status]              NVARCHAR(20)        NOT NULL,  -- 'success', 'partial', 'error'
        [articles_found]      INT                 DEFAULT 0,
        [articles_new]        INT                 DEFAULT 0,
        [articles_duplicate]  INT                 DEFAULT 0,
        [error_message]       NVARCHAR(MAX)       NULL,
        [duration_ms]         INT                 NULL,

        CONSTRAINT [FK_logs_source] FOREIGN KEY ([source_id])
            REFERENCES [dbo].[sources]([id]) ON DELETE SET NULL
    );

    PRINT 'Table [collection_logs] created successfully.';
END
ELSE
BEGIN
    PRINT 'Table [collection_logs] already exists.';
END
GO

-- ============================================================================
-- INDEXES: sources
-- ============================================================================

-- Index for active sources (filtered index)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_sources_active' AND object_id = OBJECT_ID('dbo.sources'))
BEGIN
    CREATE INDEX [IX_sources_active]
    ON [dbo].[sources] ([active])
    WHERE [active] = 1;

    PRINT 'Index [IX_sources_active] created successfully.';
END
GO

-- Index for scheduling (frequency + last_fetch)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_sources_frequency' AND object_id = OBJECT_ID('dbo.sources'))
BEGIN
    CREATE INDEX [IX_sources_frequency]
    ON [dbo].[sources] ([frequency], [last_fetch]);

    PRINT 'Index [IX_sources_frequency] created successfully.';
END
GO

-- ============================================================================
-- INDEXES: collected_articles
-- ============================================================================

-- Index for recent articles (published_at DESC)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_published' AND object_id = OBJECT_ID('dbo.collected_articles'))
BEGIN
    CREATE INDEX [IX_articles_published]
    ON [dbo].[collected_articles] ([published_at] DESC);

    PRINT 'Index [IX_articles_published] created successfully.';
END
GO

-- Index for source filtering
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_source' AND object_id = OBJECT_ID('dbo.collected_articles'))
BEGIN
    CREATE INDEX [IX_articles_source]
    ON [dbo].[collected_articles] ([source_id]);

    PRINT 'Index [IX_articles_source] created successfully.';
END
GO

-- Index for category filtering
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_category' AND object_id = OBJECT_ID('dbo.collected_articles'))
BEGIN
    CREATE INDEX [IX_articles_category]
    ON [dbo].[collected_articles] ([category]);

    PRINT 'Index [IX_articles_category] created successfully.';
END
GO

-- Index for collection date
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_collected' AND object_id = OBJECT_ID('dbo.collected_articles'))
BEGIN
    CREATE INDEX [IX_articles_collected]
    ON [dbo].[collected_articles] ([collected_at] DESC);

    PRINT 'Index [IX_articles_collected] created successfully.';
END
GO

-- Index for hash lookups (deduplication)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_hash' AND object_id = OBJECT_ID('dbo.collected_articles'))
BEGIN
    CREATE INDEX [IX_articles_hash]
    ON [dbo].[collected_articles] ([hash]);

    PRINT 'Index [IX_articles_hash] created successfully.';
END
GO

-- Composite index for source + date queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_source_date' AND object_id = OBJECT_ID('dbo.collected_articles'))
BEGIN
    CREATE INDEX [IX_articles_source_date]
    ON [dbo].[collected_articles] ([source_id], [published_at] DESC);

    PRINT 'Index [IX_articles_source_date] created successfully.';
END
GO

-- Composite index for category + date queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_category_date' AND object_id = OBJECT_ID('dbo.collected_articles'))
BEGIN
    CREATE INDEX [IX_articles_category_date]
    ON [dbo].[collected_articles] ([category], [published_at] DESC);

    PRINT 'Index [IX_articles_category_date] created successfully.';
END
GO

-- ============================================================================
-- INDEXES: collection_logs
-- ============================================================================

-- Composite index for source logs by date
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_logs_source_date' AND object_id = OBJECT_ID('dbo.collection_logs'))
BEGIN
    CREATE INDEX [IX_logs_source_date]
    ON [dbo].[collection_logs] ([source_id], [started_at] DESC);

    PRINT 'Index [IX_logs_source_date] created successfully.';
END
GO

-- Composite index for status monitoring
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_logs_status' AND object_id = OBJECT_ID('dbo.collection_logs'))
BEGIN
    CREATE INDEX [IX_logs_status]
    ON [dbo].[collection_logs] ([status], [started_at] DESC);

    PRINT 'Index [IX_logs_status] created successfully.';
END
GO

-- ============================================================================
-- VERIFICATION
-- ============================================================================
PRINT '';
PRINT '============================================================================';
PRINT 'Schema creation completed. Verifying objects...';
PRINT '============================================================================';

SELECT
    'Table' AS [Object Type],
    t.name AS [Object Name],
    SUM(p.rows) AS [Row Count]
FROM sys.tables t
INNER JOIN sys.partitions p ON t.object_id = p.object_id
WHERE t.name IN ('sources', 'collected_articles', 'collection_logs')
  AND p.index_id IN (0, 1)
GROUP BY t.name
ORDER BY t.name;

SELECT
    'Index' AS [Object Type],
    i.name AS [Index Name],
    t.name AS [Table Name],
    i.type_desc AS [Index Type]
FROM sys.indexes i
INNER JOIN sys.tables t ON i.object_id = t.object_id
WHERE t.name IN ('sources', 'collected_articles', 'collection_logs')
  AND i.name IS NOT NULL
  AND i.name NOT LIKE 'PK_%'
ORDER BY t.name, i.name;

PRINT '';
PRINT '============================================================================';
PRINT 'TMC Feed RSS schema creation script completed successfully!';
PRINT '============================================================================';
GO
