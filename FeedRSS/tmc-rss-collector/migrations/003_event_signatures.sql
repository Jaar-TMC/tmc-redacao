-- Migration 003: Event Signatures for Specific Event Clustering
-- This migration adds support for clustering by SPECIFIC EVENT rather than
-- generic semantic concepts.

-- ============================================
-- Table: event_signatures
-- Stores unique event identifiers extracted from articles
-- ============================================

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'event_signatures')
BEGIN
    CREATE TABLE event_signatures (
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        article_id UNIQUEIDENTIFIER NOT NULL UNIQUE,
        theme_id UNIQUEIDENTIFIER NULL,

        -- Named entities (WHO)
        people NVARCHAR(MAX) NULL,           -- JSON array: ["Joao Silva", "Maria Santos"]
        organizations NVARCHAR(MAX) NULL,     -- JSON array: ["ICE", "STF", "Petrobras"]

        -- Location (WHERE)
        locations NVARCHAR(MAX) NULL,         -- JSON array: ["Estados Unidos", "Miami"]

        -- Event action (WHAT)
        event_action NVARCHAR(100) NULL,      -- Main verb: "detido", "morreu", "anunciou"

        -- Unique identifiers
        unique_details NVARCHAR(MAX) NULL,    -- JSON array: ["pai de trigemeos", "empresario"]
        canonical_key NVARCHAR(500) NULL,     -- Normalized key for fast lookup

        -- Temporal context
        event_date DATE NULL,                 -- Date of the event if mentioned

        -- Metadata
        confidence DECIMAL(5,4) NULL,         -- 0.0000 to 1.0000
        extracted_at DATETIME2 DEFAULT GETUTCDATE(),

        CONSTRAINT FK_event_signatures_article
            FOREIGN KEY (article_id) REFERENCES collected_articles(id)
            ON DELETE CASCADE,
        CONSTRAINT FK_event_signatures_theme
            FOREIGN KEY (theme_id) REFERENCES themes(id)
            ON DELETE SET NULL
    );

    PRINT 'Created table: event_signatures';
END
GO

-- ============================================
-- Indexes for event_signatures
-- ============================================

-- Index for fast canonical key lookup (primary matching method)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_event_signatures_canonical_key')
BEGIN
    CREATE INDEX IX_event_signatures_canonical_key
        ON event_signatures(canonical_key);
    PRINT 'Created index: IX_event_signatures_canonical_key';
END
GO

-- Index for theme lookup
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_event_signatures_theme_id')
BEGIN
    CREATE INDEX IX_event_signatures_theme_id
        ON event_signatures(theme_id)
        WHERE theme_id IS NOT NULL;
    PRINT 'Created index: IX_event_signatures_theme_id';
END
GO

-- Index for extraction date (for maintenance queries)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_event_signatures_extracted_at')
BEGIN
    CREATE INDEX IX_event_signatures_extracted_at
        ON event_signatures(extracted_at DESC);
    PRINT 'Created index: IX_event_signatures_extracted_at';
END
GO

-- ============================================
-- Modifications to themes table
-- ============================================

-- Add canonical_event_key to themes for fast event matching
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('themes') AND name = 'canonical_event_key')
BEGIN
    ALTER TABLE themes ADD
        canonical_event_key NVARCHAR(500) NULL;
    PRINT 'Added column: themes.canonical_event_key';
END
GO

-- Add primary_entities to themes (JSON of main entities in the event)
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('themes') AND name = 'primary_entities')
BEGIN
    ALTER TABLE themes ADD
        primary_entities NVARCHAR(MAX) NULL;
    PRINT 'Added column: themes.primary_entities';
END
GO

-- Add seed_article_id to track the article that started the theme
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('themes') AND name = 'seed_article_id')
BEGIN
    ALTER TABLE themes ADD
        seed_article_id UNIQUEIDENTIFIER NULL;
    PRINT 'Added column: themes.seed_article_id';
END
GO

-- Index for canonical event key on themes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_themes_canonical_event_key')
BEGIN
    CREATE INDEX IX_themes_canonical_event_key
        ON themes(canonical_event_key)
        WHERE canonical_event_key IS NOT NULL;
    PRINT 'Created index: IX_themes_canonical_event_key';
END
GO

-- ============================================
-- Modifications to article_themes table
-- ============================================

-- Add match_type to track how the article was matched to the theme
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('article_themes') AND name = 'match_type')
BEGIN
    ALTER TABLE article_themes ADD
        match_type NVARCHAR(20) NULL;  -- 'exact', 'entity', 'verified', 'embedding'
    PRINT 'Added column: article_themes.match_type';
END
GO

-- ============================================
-- Helper Views
-- ============================================

-- View to see themes with their event signatures
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_themes_with_signatures')
    DROP VIEW v_themes_with_signatures;
GO

CREATE VIEW v_themes_with_signatures AS
SELECT
    t.id AS theme_id,
    t.name AS theme_name,
    t.slug,
    t.article_count,
    t.status,
    t.canonical_event_key,
    t.primary_entities,
    t.seed_article_id,
    t.first_seen_at,
    t.last_updated_at,
    (
        SELECT COUNT(*)
        FROM event_signatures es
        WHERE es.theme_id = t.id
    ) AS signature_count
FROM themes t
WHERE t.status = 'active';
GO

PRINT 'Created view: v_themes_with_signatures';

-- View to see articles pending event signature extraction
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_articles_pending_signature')
    DROP VIEW v_articles_pending_signature;
GO

CREATE VIEW v_articles_pending_signature AS
SELECT
    a.id AS article_id,
    a.title,
    a.preview,
    a.collected_at
FROM collected_articles a
LEFT JOIN event_signatures es ON a.id = es.article_id
WHERE es.id IS NULL
  AND a.collected_at >= DATEADD(day, -7, GETUTCDATE());  -- Only recent articles
GO

PRINT 'Created view: v_articles_pending_signature';

-- ============================================
-- Stored Procedure: Find themes by canonical key
-- ============================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_find_theme_by_canonical_key')
    DROP PROCEDURE sp_find_theme_by_canonical_key;
GO

CREATE PROCEDURE sp_find_theme_by_canonical_key
    @canonical_key NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;

    -- First, try exact match on theme's canonical key
    SELECT TOP 1
        t.id AS theme_id,
        t.name,
        t.canonical_event_key,
        t.centroid,
        'exact' AS match_type,
        1.0 AS match_confidence
    FROM themes t
    WHERE t.canonical_event_key = @canonical_key
      AND t.status = 'active'
    ORDER BY t.article_count DESC;

    IF @@ROWCOUNT = 0
    BEGIN
        -- If no exact match, try to find themes with similar canonical keys
        -- Use STRING_SPLIT to parse the 5-part canonical key: person|org|action|location|period
        -- Compare individual parts for partial matching

        ;WITH ParsedInput AS (
            SELECT
                value,
                ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS part_num
            FROM STRING_SPLIT(@canonical_key, '|')
        ),
        InputParts AS (
            SELECT
                MAX(CASE WHEN part_num = 1 THEN value END) AS person,
                MAX(CASE WHEN part_num = 2 THEN value END) AS org,
                MAX(CASE WHEN part_num = 3 THEN value END) AS action,
                MAX(CASE WHEN part_num = 4 THEN value END) AS location,
                MAX(CASE WHEN part_num = 5 THEN value END) AS period
            FROM ParsedInput
        ),
        ThemeParts AS (
            SELECT
                t.id,
                t.name,
                t.canonical_event_key,
                t.centroid,
                t.article_count,
                p.value AS part_value,
                ROW_NUMBER() OVER (PARTITION BY t.id ORDER BY (SELECT NULL)) AS part_num
            FROM themes t
            CROSS APPLY STRING_SPLIT(t.canonical_event_key, '|') p
            WHERE t.status = 'active'
              AND t.canonical_event_key IS NOT NULL
        ),
        ThemePartsPivot AS (
            SELECT
                id,
                name,
                canonical_event_key,
                centroid,
                article_count,
                MAX(CASE WHEN part_num = 1 THEN part_value END) AS person,
                MAX(CASE WHEN part_num = 2 THEN part_value END) AS org,
                MAX(CASE WHEN part_num = 3 THEN part_value END) AS action,
                MAX(CASE WHEN part_num = 4 THEN part_value END) AS location,
                MAX(CASE WHEN part_num = 5 THEN part_value END) AS period
            FROM ThemeParts
            GROUP BY id, name, canonical_event_key, centroid, article_count
        )
        SELECT TOP 5
            tp.id AS theme_id,
            tp.name,
            tp.canonical_event_key,
            tp.centroid,
            'partial' AS match_type,
            0.7 AS match_confidence
        FROM ThemePartsPivot tp
        CROSS JOIN InputParts ip
        WHERE
            -- Match if person OR org OR action matches (key identifiers)
            (tp.person = ip.person AND ip.person != 'null')
            OR (tp.org = ip.org AND ip.org != 'null')
            OR (tp.action = ip.action AND ip.action != 'null')
        ORDER BY
            -- Prioritize by number of matching parts
            CASE WHEN tp.person = ip.person THEN 1 ELSE 0 END +
            CASE WHEN tp.org = ip.org THEN 1 ELSE 0 END +
            CASE WHEN tp.action = ip.action THEN 1 ELSE 0 END DESC,
            tp.article_count DESC;
    END
END
GO

PRINT 'Created procedure: sp_find_theme_by_canonical_key';

-- ============================================
-- Stored Procedure: Get event signatures for clustering
-- ============================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_get_signatures_for_clustering')
    DROP PROCEDURE sp_get_signatures_for_clustering;
GO

CREATE PROCEDURE sp_get_signatures_for_clustering
    @limit INT = 100
AS
BEGIN
    SET NOCOUNT ON;

    -- Get articles with signatures but no theme assignment
    SELECT TOP (@limit)
        es.id AS signature_id,
        es.article_id,
        es.people,
        es.organizations,
        es.locations,
        es.event_action,
        es.unique_details,
        es.canonical_key,
        es.event_date,
        es.confidence,
        a.title,
        a.preview,
        ae.embedding
    FROM event_signatures es
    JOIN collected_articles a ON es.article_id = a.id
    LEFT JOIN article_embeddings ae ON es.article_id = ae.article_id
    LEFT JOIN article_themes at ON es.article_id = at.article_id
    WHERE es.theme_id IS NULL
      AND at.theme_id IS NULL  -- Not yet assigned to a theme
      AND es.confidence >= 0.3  -- Minimum confidence threshold
    ORDER BY es.extracted_at DESC;
END
GO

PRINT 'Created procedure: sp_get_signatures_for_clustering';

-- ============================================
-- Migration complete
-- ============================================

PRINT '';
PRINT '========================================';
PRINT 'Migration 003: Event Signatures - COMPLETE';
PRINT '========================================';
PRINT '';
PRINT 'New table: event_signatures';
PRINT 'New columns: themes.canonical_event_key, themes.primary_entities, themes.seed_article_id';
PRINT 'New column: article_themes.match_type';
PRINT 'New views: v_themes_with_signatures, v_articles_pending_signature';
PRINT 'New procedures: sp_find_theme_by_canonical_key, sp_get_signatures_for_clustering';
