-- Migration 013: Denormalize scores into collected_articles for query performance
-- Eliminates expensive LEFT JOIN to article_scores on every query
-- Expected improvement: 60s+ queries → <500ms

-- Step 1: Add score columns to collected_articles
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('collected_articles') AND name = 'total_score')
ALTER TABLE collected_articles ADD total_score INT NULL;

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('collected_articles') AND name = 'classification')
ALTER TABLE collected_articles ADD classification CHAR(1) NULL;
GO

-- Step 2: Backfill from article_scores
UPDATE a SET
    a.total_score = sc.total_score,
    a.classification = sc.classification
FROM collected_articles a
INNER JOIN article_scores sc ON sc.article_id = a.id
WHERE a.total_score IS NULL;

-- Step 3: Create composite indexes for score-based queries

-- Primary index: score ordering (most common query with order_by=score)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_score_order')
CREATE NONCLUSTERED INDEX IX_articles_score_order
    ON collected_articles(total_score DESC, published_at DESC)
    INCLUDE (id, title, source_id, category, tags, preview, image_url, author, content, collected_at, hash, classification)
    WHERE total_score IS NOT NULL;

-- Index for classification filter + score ordering (e.g., show all A articles by score)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_class_score')
CREATE NONCLUSTERED INDEX IX_articles_class_score
    ON collected_articles(classification, total_score DESC, published_at DESC)
    INCLUDE (id, title, source_id, category, tags, preview);

-- Index for category + score ordering (cross-filter: category + score)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_articles_category_score')
CREATE NONCLUSTERED INDEX IX_articles_category_score
    ON collected_articles(category, total_score DESC, published_at DESC)
    INCLUDE (id, classification);
