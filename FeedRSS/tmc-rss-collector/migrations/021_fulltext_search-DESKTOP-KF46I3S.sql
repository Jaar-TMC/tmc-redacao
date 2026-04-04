-- Migration 021: Full-text search catalog and index for Portuguese word breaking
-- Enables FREETEXT queries to replace LIKE '%term%' full table scans
-- Language 1046 = Brazilian Portuguese (handles compound words like "selecao brasileira")

-- Step 1: Create full-text catalog (idempotent check)
IF NOT EXISTS (SELECT 1 FROM sys.fulltext_catalogs WHERE name = 'ArticleCatalog')
BEGIN
    CREATE FULLTEXT CATALOG ArticleCatalog AS DEFAULT;
END;
GO

-- Step 2: Create full-text index on collected_articles
-- Dynamically looks up the primary key index name to avoid hardcoding
-- LANGUAGE 1046 enables Portuguese word breaker for all 3 columns
IF NOT EXISTS (
    SELECT 1 FROM sys.fulltext_indexes fi
    JOIN sys.objects o ON fi.object_id = o.object_id
    WHERE o.name = 'collected_articles'
)
BEGIN
    DECLARE @pk_name NVARCHAR(256);
    SELECT @pk_name = i.name
    FROM sys.indexes i
    WHERE i.object_id = OBJECT_ID('collected_articles') AND i.is_primary_key = 1;

    IF @pk_name IS NOT NULL
    BEGIN
        DECLARE @sql NVARCHAR(MAX) = N'
            CREATE FULLTEXT INDEX ON collected_articles (
                title LANGUAGE 1046,
                preview LANGUAGE 1046,
                tags LANGUAGE 1046
            )
            KEY INDEX ' + QUOTENAME(@pk_name) + N'
            ON ArticleCatalog;';
        EXEC sp_executesql @sql;
    END
END;
