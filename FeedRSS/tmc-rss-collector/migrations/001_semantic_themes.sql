-- Migration: 001_semantic_themes.sql
-- Description: Creates tables for semantic themes system with embeddings, scoring, and classification
-- Azure SQL Database with VECTOR support
-- Created: 2026-02-04

-- ============================================================================
-- TABLE: article_embeddings
-- Stores 1536-dimension OpenAI embeddings for articles
-- ============================================================================
CREATE TABLE article_embeddings (
    id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    article_id UNIQUEIDENTIFIER NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    model_version NVARCHAR(50) NOT NULL DEFAULT 'text-embedding-3-small',
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

    CONSTRAINT PK_article_embeddings PRIMARY KEY (id),
    CONSTRAINT FK_article_embeddings_article FOREIGN KEY (article_id)
        REFERENCES collected_articles(id) ON DELETE CASCADE,
    CONSTRAINT UQ_article_embeddings_article UNIQUE (article_id)
);

-- Index for fast lookups by article
CREATE NONCLUSTERED INDEX IX_article_embeddings_article_id
    ON article_embeddings(article_id);

-- Index for vector similarity search (Azure SQL DiskANN index)
CREATE NONCLUSTERED INDEX IX_article_embeddings_vector
    ON article_embeddings(embedding)
    WITH (ONLINE = ON);

-- ============================================================================
-- TABLE: themes
-- Semantic clusters with centroid embeddings and classification
-- ============================================================================
CREATE TABLE themes (
    id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    name NVARCHAR(200) NOT NULL,
    description NVARCHAR(MAX) NULL,
    centroid VECTOR(1536) NULL,
    article_count INT NOT NULL DEFAULT 0,
    avg_score DECIMAL(5,2) NULL,
    classification CHAR(1) NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    expires_at DATETIME2 NULL,

    CONSTRAINT PK_themes PRIMARY KEY (id),
    CONSTRAINT CK_themes_classification CHECK (classification IN ('A', 'B', 'C'))
);

-- Index for active themes lookup
CREATE NONCLUSTERED INDEX IX_themes_active
    ON themes(is_active)
    INCLUDE (name, classification, article_count, avg_score);

-- Index for classification filtering
CREATE NONCLUSTERED INDEX IX_themes_classification
    ON themes(classification, is_active)
    INCLUDE (name, article_count);

-- Index for vector similarity on centroids
CREATE NONCLUSTERED INDEX IX_themes_centroid
    ON themes(centroid)
    WITH (ONLINE = ON);

-- ============================================================================
-- TABLE: article_themes
-- N:N relationship between articles and themes with relevance scoring
-- ============================================================================
CREATE TABLE article_themes (
    id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    article_id UNIQUEIDENTIFIER NOT NULL,
    theme_id UNIQUEIDENTIFIER NOT NULL,
    similarity_score DECIMAL(5,4) NOT NULL,
    is_primary BIT NOT NULL DEFAULT 0,
    assigned_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

    CONSTRAINT PK_article_themes PRIMARY KEY (id),
    CONSTRAINT FK_article_themes_article FOREIGN KEY (article_id)
        REFERENCES collected_articles(id) ON DELETE CASCADE,
    CONSTRAINT FK_article_themes_theme FOREIGN KEY (theme_id)
        REFERENCES themes(id) ON DELETE CASCADE,
    CONSTRAINT UQ_article_themes_pair UNIQUE (article_id, theme_id),
    CONSTRAINT CK_article_themes_similarity CHECK (similarity_score >= 0 AND similarity_score <= 1)
);

-- Index for finding articles by theme
CREATE NONCLUSTERED INDEX IX_article_themes_theme_id
    ON article_themes(theme_id)
    INCLUDE (article_id, similarity_score, is_primary);

-- Index for finding themes by article
CREATE NONCLUSTERED INDEX IX_article_themes_article_id
    ON article_themes(article_id)
    INCLUDE (theme_id, similarity_score, is_primary);

-- Index for primary theme lookups
CREATE NONCLUSTERED INDEX IX_article_themes_primary
    ON article_themes(article_id, is_primary)
    WHERE is_primary = 1;

-- ============================================================================
-- TABLE: article_scores
-- Editorial scoring with 4 signals for news prioritization
-- Scoring System:
--   sinal_inesperado: yes=25, partial=12, no=0
--   sinal_impacto: high=30, medium=15, low=0
--   sinal_busca_agora: yes=25, maybe=12, no=0
--   sinal_conversa: yes=20, no=0
-- Classification: A (>=75), B (40-74), C (<40)
-- ============================================================================
CREATE TABLE article_scores (
    id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    article_id UNIQUEIDENTIFIER NOT NULL,

    -- Signal values (stored as text for auditability)
    sinal_inesperado NVARCHAR(10) NOT NULL,
    sinal_impacto NVARCHAR(10) NOT NULL,
    sinal_busca_agora NVARCHAR(10) NOT NULL,
    sinal_conversa NVARCHAR(10) NOT NULL,

    -- Calculated point values
    pontos_inesperado INT NOT NULL,
    pontos_impacto INT NOT NULL,
    pontos_busca_agora INT NOT NULL,
    pontos_conversa INT NOT NULL,

    -- Total score and classification
    total_score INT NOT NULL,
    classification CHAR(1) NOT NULL,

    -- AI reasoning (optional, for transparency)
    reasoning NVARCHAR(MAX) NULL,

    -- Metadata
    scored_by NVARCHAR(50) NOT NULL DEFAULT 'ai',
    model_version NVARCHAR(50) NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

    CONSTRAINT PK_article_scores PRIMARY KEY (id),
    CONSTRAINT FK_article_scores_article FOREIGN KEY (article_id)
        REFERENCES collected_articles(id) ON DELETE CASCADE,
    CONSTRAINT UQ_article_scores_article UNIQUE (article_id),

    -- Validate signal values
    CONSTRAINT CK_article_scores_inesperado
        CHECK (sinal_inesperado IN ('yes', 'partial', 'no')),
    CONSTRAINT CK_article_scores_impacto
        CHECK (sinal_impacto IN ('high', 'medium', 'low')),
    CONSTRAINT CK_article_scores_busca_agora
        CHECK (sinal_busca_agora IN ('yes', 'maybe', 'no')),
    CONSTRAINT CK_article_scores_conversa
        CHECK (sinal_conversa IN ('yes', 'no')),

    -- Validate point values
    CONSTRAINT CK_article_scores_pontos_inesperado
        CHECK (pontos_inesperado IN (0, 12, 25)),
    CONSTRAINT CK_article_scores_pontos_impacto
        CHECK (pontos_impacto IN (0, 15, 30)),
    CONSTRAINT CK_article_scores_pontos_busca_agora
        CHECK (pontos_busca_agora IN (0, 12, 25)),
    CONSTRAINT CK_article_scores_pontos_conversa
        CHECK (pontos_conversa IN (0, 20)),

    -- Validate total and classification
    CONSTRAINT CK_article_scores_total
        CHECK (total_score >= 0 AND total_score <= 100),
    CONSTRAINT CK_article_scores_classification
        CHECK (classification IN ('A', 'B', 'C'))
);

-- Index for classification filtering
CREATE NONCLUSTERED INDEX IX_article_scores_classification
    ON article_scores(classification)
    INCLUDE (article_id, total_score);

-- Index for score-based sorting
CREATE NONCLUSTERED INDEX IX_article_scores_total
    ON article_scores(total_score DESC)
    INCLUDE (article_id, classification);

-- Index for article lookups
CREATE NONCLUSTERED INDEX IX_article_scores_article_id
    ON article_scores(article_id);

-- ============================================================================
-- ALTER TABLE: collected_articles
-- Add columns for semantic processing status
-- ============================================================================
ALTER TABLE collected_articles
    ADD has_embedding BIT NOT NULL DEFAULT 0;

ALTER TABLE collected_articles
    ADD has_score BIT NOT NULL DEFAULT 0;

ALTER TABLE collected_articles
    ADD primary_theme_id UNIQUEIDENTIFIER NULL;

-- Add foreign key for primary theme
ALTER TABLE collected_articles
    ADD CONSTRAINT FK_collected_articles_primary_theme
    FOREIGN KEY (primary_theme_id) REFERENCES themes(id);

-- Index for finding articles without embeddings (for batch processing)
CREATE NONCLUSTERED INDEX IX_collected_articles_has_embedding
    ON collected_articles(has_embedding)
    WHERE has_embedding = 0;

-- Index for finding articles without scores (for batch processing)
CREATE NONCLUSTERED INDEX IX_collected_articles_has_score
    ON collected_articles(has_score)
    WHERE has_score = 0;

-- Index for primary theme filtering
CREATE NONCLUSTERED INDEX IX_collected_articles_primary_theme
    ON collected_articles(primary_theme_id)
    WHERE primary_theme_id IS NOT NULL;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to calculate points from signal values
GO
CREATE OR ALTER FUNCTION dbo.fn_calculate_signal_points (
    @sinal_inesperado NVARCHAR(10),
    @sinal_impacto NVARCHAR(10),
    @sinal_busca_agora NVARCHAR(10),
    @sinal_conversa NVARCHAR(10)
)
RETURNS TABLE
AS
RETURN (
    SELECT
        CASE @sinal_inesperado
            WHEN 'yes' THEN 25
            WHEN 'partial' THEN 12
            ELSE 0
        END AS pontos_inesperado,
        CASE @sinal_impacto
            WHEN 'high' THEN 30
            WHEN 'medium' THEN 15
            ELSE 0
        END AS pontos_impacto,
        CASE @sinal_busca_agora
            WHEN 'yes' THEN 25
            WHEN 'maybe' THEN 12
            ELSE 0
        END AS pontos_busca_agora,
        CASE @sinal_conversa
            WHEN 'yes' THEN 20
            ELSE 0
        END AS pontos_conversa
);
GO

-- Function to determine classification from total score
CREATE OR ALTER FUNCTION dbo.fn_get_classification (@total_score INT)
RETURNS CHAR(1)
AS
BEGIN
    RETURN CASE
        WHEN @total_score >= 75 THEN 'A'
        WHEN @total_score >= 40 THEN 'B'
        ELSE 'C'
    END;
END;
GO

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger to update collected_articles.has_embedding when embedding is added
CREATE OR ALTER TRIGGER trg_article_embeddings_insert
ON article_embeddings
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE collected_articles
    SET has_embedding = 1,
        updated_at = GETUTCDATE()
    FROM collected_articles ca
    INNER JOIN inserted i ON ca.id = i.article_id;
END;
GO

-- Trigger to update collected_articles.has_score when score is added
CREATE OR ALTER TRIGGER trg_article_scores_insert
ON article_scores
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE collected_articles
    SET has_score = 1,
        updated_at = GETUTCDATE()
    FROM collected_articles ca
    INNER JOIN inserted i ON ca.id = i.article_id;
END;
GO

-- Trigger to update collected_articles.primary_theme_id when primary theme is assigned
CREATE OR ALTER TRIGGER trg_article_themes_primary
ON article_themes
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE collected_articles
    SET primary_theme_id = i.theme_id,
        updated_at = GETUTCDATE()
    FROM collected_articles ca
    INNER JOIN inserted i ON ca.id = i.article_id
    WHERE i.is_primary = 1;
END;
GO

-- Trigger to update theme statistics when articles are assigned
CREATE OR ALTER TRIGGER trg_article_themes_stats
ON article_themes
AFTER INSERT, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    -- Update article count for affected themes
    UPDATE themes
    SET article_count = (
            SELECT COUNT(*)
            FROM article_themes at
            WHERE at.theme_id = themes.id
        ),
        updated_at = GETUTCDATE()
    WHERE id IN (SELECT theme_id FROM inserted)
       OR id IN (SELECT theme_id FROM deleted);

    -- Update average score for affected themes
    UPDATE themes
    SET avg_score = (
            SELECT AVG(CAST(ars.total_score AS DECIMAL(5,2)))
            FROM article_themes at
            INNER JOIN article_scores ars ON at.article_id = ars.article_id
            WHERE at.theme_id = themes.id
        ),
        classification = dbo.fn_get_classification(
            ISNULL((
                SELECT AVG(ars.total_score)
                FROM article_themes at
                INNER JOIN article_scores ars ON at.article_id = ars.article_id
                WHERE at.theme_id = themes.id
            ), 0)
        )
    WHERE id IN (SELECT theme_id FROM inserted)
       OR id IN (SELECT theme_id FROM deleted);
END;
GO

-- ============================================================================
-- SAMPLE QUERIES (for reference)
-- ============================================================================

/*
-- Find similar articles using vector similarity
SELECT TOP 10
    ca.id,
    ca.title,
    VECTOR_DISTANCE('cosine', ae.embedding, @query_embedding) AS distance
FROM collected_articles ca
INNER JOIN article_embeddings ae ON ca.id = ae.article_id
ORDER BY VECTOR_DISTANCE('cosine', ae.embedding, @query_embedding);

-- Get top articles by score
SELECT
    ca.id,
    ca.title,
    ars.total_score,
    ars.classification,
    t.name AS theme_name
FROM collected_articles ca
INNER JOIN article_scores ars ON ca.id = ars.article_id
LEFT JOIN themes t ON ca.primary_theme_id = t.id
WHERE ars.classification = 'A'
ORDER BY ars.total_score DESC;

-- Get theme statistics
SELECT
    t.name,
    t.article_count,
    t.avg_score,
    t.classification,
    COUNT(CASE WHEN ars.classification = 'A' THEN 1 END) AS a_articles,
    COUNT(CASE WHEN ars.classification = 'B' THEN 1 END) AS b_articles,
    COUNT(CASE WHEN ars.classification = 'C' THEN 1 END) AS c_articles
FROM themes t
LEFT JOIN article_themes at ON t.id = at.theme_id
LEFT JOIN article_scores ars ON at.article_id = ars.article_id
WHERE t.is_active = 1
GROUP BY t.id, t.name, t.article_count, t.avg_score, t.classification
ORDER BY t.article_count DESC;

-- Find articles needing processing
SELECT id, title, published_at
FROM collected_articles
WHERE has_embedding = 0 OR has_score = 0
ORDER BY published_at DESC;
*/

PRINT 'Migration 001_semantic_themes completed successfully.';
