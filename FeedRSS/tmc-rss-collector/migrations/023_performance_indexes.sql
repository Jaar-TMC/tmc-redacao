-- Migration 023: Performance covering indexes for article list queries
-- Phase 6 DB-01, DB-02, DB-03, DB-04
--
-- These indexes eliminate key lookups for the main article list queries.
-- Migration 012 created IX_collected_articles_published and
-- IX_collected_articles_category_published with narrow INCLUDE lists.
-- These new indexes have wider INCLUDE columns that fully cover the
-- SELECT list in get_articles() / get_articles_filtered(), so the query
-- engine never touches the clustered index (key lookup elimination).

-- DB-01: Main query covering index (ORDER BY published_at DESC)
-- Supersedes IX_collected_articles_published (012) which only included
-- (id, category, source_id). This version covers the full SELECT list.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_articles_main_query' AND object_id = OBJECT_ID('collected_articles'))
CREATE NONCLUSTERED INDEX IX_articles_main_query
ON collected_articles (published_at DESC)
INCLUDE (id, source_id, title, preview, url, image_url, author, category,
         tags, collected_at, hash, total_score, classification);
GO

-- DB-02: Category + date composite index (most common filter)
-- Supersedes IX_collected_articles_category_published (012) which lacked
-- url, image_url, author, collected_at, hash, total_score, classification.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_articles_category_date' AND object_id = OBJECT_ID('collected_articles'))
CREATE NONCLUSTERED INDEX IX_articles_category_date
ON collected_articles (category, published_at DESC)
INCLUDE (id, source_id, title, preview, total_score, classification);
GO

-- DB-03: Score ordering index
-- Complements IX_articles_score_order (013) which has a WHERE filter
-- (total_score IS NOT NULL). This unfiltered version serves queries
-- that do not pre-filter on score existence.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_articles_score_date' AND object_id = OBJECT_ID('collected_articles'))
CREATE NONCLUSTERED INDEX IX_articles_score_date
ON collected_articles (total_score DESC, published_at DESC)
INCLUDE (id, source_id, title, preview, category, classification);
GO

-- DB-04: Enable automatic tuning (CREATE_INDEX advisor)
-- Azure SQL can detect missing indexes and create them automatically.
-- Safe to run multiple times; no-op if already enabled.
ALTER DATABASE CURRENT SET AUTOMATIC_TUNING (CREATE_INDEX = ON);
GO
