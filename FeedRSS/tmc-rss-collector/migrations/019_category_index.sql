-- Migration 019: Add index on category for faster GROUP BY in facet queries
-- This speeds up get_categories_filtered() which runs on every initial page load

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_collected_articles_category'
    AND object_id = OBJECT_ID('collected_articles')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_collected_articles_category
    ON collected_articles (category)
    INCLUDE (source_id, published_at, classification)
    WITH (ONLINE = ON);
END
