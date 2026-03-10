-- Performance indexes for article filtering and ordering
-- These indexes speed up the most common filter combinations

-- Composite index for category + time filtering (most common query)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_collected_articles_category_published')
CREATE NONCLUSTERED INDEX IX_collected_articles_category_published
    ON collected_articles(category, published_at DESC)
    INCLUDE (id, title, source_id, tags, preview);

-- Index for source filtering with time ordering
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_collected_articles_source_published')
CREATE NONCLUSTERED INDEX IX_collected_articles_source_published
    ON collected_articles(source_id, published_at DESC)
    INCLUDE (id, title, category, tags);

-- Index for time-based filtering (urgency chips)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_collected_articles_published')
CREATE NONCLUSTERED INDEX IX_collected_articles_published
    ON collected_articles(published_at DESC)
    INCLUDE (id, category, source_id);
