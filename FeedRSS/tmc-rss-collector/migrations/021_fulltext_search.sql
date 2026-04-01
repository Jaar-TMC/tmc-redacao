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
-- KEY INDEX must reference the table's primary key
-- Verify actual PK name with:
--   SELECT name FROM sys.indexes WHERE object_id = OBJECT_ID('collected_articles') AND is_primary_key = 1
-- LANGUAGE 1046 enables Portuguese word breaker for all 3 columns
IF NOT EXISTS (
    SELECT 1 FROM sys.fulltext_indexes fi
    JOIN sys.objects o ON fi.object_id = o.object_id
    WHERE o.name = 'collected_articles'
)
BEGIN
    CREATE FULLTEXT INDEX ON collected_articles (
        title LANGUAGE 1046,
        preview LANGUAGE 1046,
        tags LANGUAGE 1046
    )
    KEY INDEX PK_collected_articles
    ON ArticleCatalog;
END;
GO
