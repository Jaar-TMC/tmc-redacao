-- Migration 020: Pre-aggregated tag counts for fast sidebar queries
-- Eliminates expensive CROSS APPLY OPENJSON on every trending-tags request.
-- Updated by RSS collector timer (every 15 min) and clustering maintenance (daily).

IF NOT EXISTS (
    SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID('tag_aggregations') AND type = 'U'
)
BEGIN
    CREATE TABLE tag_aggregations (
        tag NVARCHAR(200) NOT NULL,
        article_count INT NOT NULL DEFAULT 0,
        period_hours INT NOT NULL DEFAULT 72,
        last_updated DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        CONSTRAINT PK_tag_aggregations PRIMARY KEY (tag, period_hours)
    );

    CREATE NONCLUSTERED INDEX IX_tag_agg_period_count
    ON tag_aggregations (period_hours, article_count DESC)
    INCLUDE (tag, last_updated);
END
