-- Migration: 002_semantic_themes_fix.sql
-- Versão simplificada sem VECTOR type (usa NVARCHAR(MAX) para JSON)
-- Execute este script no banco tmc

-- ============================================================================
-- PRIMEIRO: Verificar se collected_articles existe
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'collected_articles')
BEGIN
    RAISERROR('ERRO: Tabela collected_articles não existe! Verifique o nome correto.', 16, 1);
    RETURN;
END
GO

-- ============================================================================
-- TABLE: themes (criar primeiro, sem dependências)
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'themes')
BEGIN
    CREATE TABLE themes (
        id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        name NVARCHAR(200) NOT NULL,
        slug NVARCHAR(200) NULL,
        description NVARCHAR(MAX) NULL,
        centroid NVARCHAR(MAX) NULL,  -- JSON array dos embeddings
        article_count INT NOT NULL DEFAULT 0,
        avg_score DECIMAL(5,2) NULL,
        max_score INT NULL,
        min_score INT NULL,
        classification CHAR(1) NULL,
        status NVARCHAR(20) NOT NULL DEFAULT 'active',
        first_seen_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        last_updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        expires_at DATETIME2 NULL,

        CONSTRAINT PK_themes PRIMARY KEY (id),
        CONSTRAINT CK_themes_classification CHECK (classification IN ('A', 'B', 'C') OR classification IS NULL)
    );
    PRINT 'Tabela themes criada com sucesso.';
END
ELSE
    PRINT 'Tabela themes já existe.';
GO

-- ============================================================================
-- TABLE: article_embeddings
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'article_embeddings')
BEGIN
    CREATE TABLE article_embeddings (
        id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        article_id UNIQUEIDENTIFIER NOT NULL,
        embedding NVARCHAR(MAX) NOT NULL,  -- JSON array dos embeddings (1536 floats)
        model_version NVARCHAR(50) NOT NULL DEFAULT 'text-embedding-3-small',
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

        CONSTRAINT PK_article_embeddings PRIMARY KEY (id),
        CONSTRAINT UQ_article_embeddings_article UNIQUE (article_id)
    );

    CREATE NONCLUSTERED INDEX IX_article_embeddings_article_id
        ON article_embeddings(article_id);

    PRINT 'Tabela article_embeddings criada com sucesso.';
END
ELSE
    PRINT 'Tabela article_embeddings já existe.';
GO

-- ============================================================================
-- TABLE: article_themes
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'article_themes')
BEGIN
    CREATE TABLE article_themes (
        id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        article_id UNIQUEIDENTIFIER NOT NULL,
        theme_id UNIQUEIDENTIFIER NOT NULL,
        similarity_score DECIMAL(5,4) NOT NULL,
        is_primary BIT NOT NULL DEFAULT 0,
        is_seed BIT NOT NULL DEFAULT 0,
        assigned_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

        CONSTRAINT PK_article_themes PRIMARY KEY (id),
        CONSTRAINT FK_article_themes_theme FOREIGN KEY (theme_id)
            REFERENCES themes(id) ON DELETE CASCADE,
        CONSTRAINT UQ_article_themes_pair UNIQUE (article_id, theme_id)
    );

    CREATE NONCLUSTERED INDEX IX_article_themes_theme_id
        ON article_themes(theme_id);

    CREATE NONCLUSTERED INDEX IX_article_themes_article_id
        ON article_themes(article_id);

    PRINT 'Tabela article_themes criada com sucesso.';
END
ELSE
    PRINT 'Tabela article_themes já existe.';
GO

-- ============================================================================
-- TABLE: article_scores
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'article_scores')
BEGIN
    CREATE TABLE article_scores (
        id UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
        article_id UNIQUEIDENTIFIER NOT NULL,

        -- Signal values
        sinal_inesperado NVARCHAR(10) NOT NULL DEFAULT 'no',
        sinal_impacto NVARCHAR(10) NOT NULL DEFAULT 'low',
        sinal_busca_agora NVARCHAR(10) NOT NULL DEFAULT 'no',
        sinal_conversa NVARCHAR(10) NOT NULL DEFAULT 'no',

        -- Calculated point values
        score_inesperado INT NOT NULL DEFAULT 0,
        score_impacto INT NOT NULL DEFAULT 0,
        score_busca_agora INT NOT NULL DEFAULT 0,
        score_conversa INT NOT NULL DEFAULT 0,

        -- Total score and classification
        total_score INT NOT NULL DEFAULT 0,
        classification CHAR(1) NOT NULL DEFAULT 'C',

        -- Metadata
        scored_by NVARCHAR(50) NOT NULL DEFAULT 'ai',
        reasoning NVARCHAR(MAX) NULL,
        scored_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

        CONSTRAINT PK_article_scores PRIMARY KEY (id),
        CONSTRAINT UQ_article_scores_article UNIQUE (article_id),
        CONSTRAINT CK_article_scores_classification CHECK (classification IN ('A', 'B', 'C'))
    );

    CREATE NONCLUSTERED INDEX IX_article_scores_classification
        ON article_scores(classification);

    CREATE NONCLUSTERED INDEX IX_article_scores_total
        ON article_scores(total_score DESC);

    CREATE NONCLUSTERED INDEX IX_article_scores_article_id
        ON article_scores(article_id);

    PRINT 'Tabela article_scores criada com sucesso.';
END
ELSE
    PRINT 'Tabela article_scores já existe.';
GO

-- ============================================================================
-- ALTER TABLE: collected_articles - adicionar colunas
-- ============================================================================

-- Adicionar has_embedding se não existir
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('collected_articles') AND name = 'has_embedding')
BEGIN
    ALTER TABLE collected_articles ADD has_embedding BIT NOT NULL DEFAULT 0;
    PRINT 'Coluna has_embedding adicionada.';
END
ELSE
    PRINT 'Coluna has_embedding já existe.';
GO

-- Adicionar has_score se não existir
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('collected_articles') AND name = 'has_score')
BEGIN
    ALTER TABLE collected_articles ADD has_score BIT NOT NULL DEFAULT 0;
    PRINT 'Coluna has_score adicionada.';
END
ELSE
    PRINT 'Coluna has_score já existe.';
GO

-- Adicionar primary_theme_id se não existir
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('collected_articles') AND name = 'primary_theme_id')
BEGIN
    ALTER TABLE collected_articles ADD primary_theme_id UNIQUEIDENTIFIER NULL;
    PRINT 'Coluna primary_theme_id adicionada.';
END
ELSE
    PRINT 'Coluna primary_theme_id já existe.';
GO

-- ============================================================================
-- ÍNDICES para collected_articles
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_collected_articles_has_embedding')
BEGIN
    CREATE NONCLUSTERED INDEX IX_collected_articles_has_embedding
        ON collected_articles(has_embedding)
        WHERE has_embedding = 0;
    PRINT 'Índice IX_collected_articles_has_embedding criado.';
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_collected_articles_has_score')
BEGIN
    CREATE NONCLUSTERED INDEX IX_collected_articles_has_score
        ON collected_articles(has_score)
        WHERE has_score = 0;
    PRINT 'Índice IX_collected_articles_has_score criado.';
END
GO

-- ============================================================================
-- VERIFICAÇÃO FINAL
-- ============================================================================
PRINT '';
PRINT '=== VERIFICAÇÃO FINAL ===';

SELECT 'themes' AS tabela, COUNT(*) AS registros FROM themes
UNION ALL
SELECT 'article_embeddings', COUNT(*) FROM article_embeddings
UNION ALL
SELECT 'article_themes', COUNT(*) FROM article_themes
UNION ALL
SELECT 'article_scores', COUNT(*) FROM article_scores;

PRINT '';
PRINT 'Migration 002_semantic_themes_fix concluída com sucesso!';
PRINT 'Próximo passo: Deploy da Function App';
GO
