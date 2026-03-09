-- Migration 011: Add resumo and titulo_curto columns to user_articles
-- These columns support the editorial summary (resumo) and short title (titulo_curto)
-- fields used by the generation pipeline and the user article CRUD flow.
-- Both are stored as NVARCHAR(MAX): resumo as a JSON array, titulo_curto as plain text.

-- Add titulo_curto if missing
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('user_articles') AND name = 'titulo_curto'
)
BEGIN
    ALTER TABLE user_articles ADD titulo_curto NVARCHAR(70) NULL;
    PRINT 'Added titulo_curto column to user_articles';
END
ELSE
BEGIN
    PRINT 'user_articles.titulo_curto already exists, skipping';
END

-- Add resumo if missing
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('user_articles') AND name = 'resumo'
)
BEGIN
    ALTER TABLE user_articles ADD resumo NVARCHAR(MAX) NULL;
    PRINT 'Added resumo column to user_articles';
END
ELSE
BEGIN
    PRINT 'user_articles.resumo already exists, skipping';
END
