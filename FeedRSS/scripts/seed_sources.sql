-- ============================================================================
-- TMC Redacao - Feed RSS Collector
-- Seed Data Script - RSS Sources
-- Target: Azure SQL Database (bi4ia-tmc.database.windows.net / tmc)
-- ============================================================================
-- Version: 1.0.0
-- Created: 2026-01-07
-- Description: Inserts initial RSS feed sources for collection
-- ============================================================================

-- ============================================================================
-- CLEAR EXISTING DATA (Optional - uncomment if needed)
-- ============================================================================
-- DELETE FROM [dbo].[collection_logs];
-- DELETE FROM [dbo].[collected_articles];
-- DELETE FROM [dbo].[sources];
-- GO

-- ============================================================================
-- INSERT RSS SOURCES
-- Total: 27 sources across multiple categories
-- ============================================================================

PRINT 'Inserting RSS feed sources...';
PRINT '';

-- Use MERGE to avoid duplicates on re-run
MERGE INTO [dbo].[sources] AS target
USING (
    VALUES
    -- ========================================================================
    -- G1 (Globo) - 7 feeds
    -- ========================================================================
    (
        N'G1 - Principal',
        N'https://g1.globo.com/rss/g1/',
        N'https://g1.globo.com/favicon.ico',
        N'Geral',
        N'30min'
    ),
    (
        N'G1 - Politica',
        N'https://g1.globo.com/rss/g1/politica/',
        N'https://g1.globo.com/favicon.ico',
        N'Politica',
        N'30min'
    ),
    (
        N'G1 - Economia',
        N'https://g1.globo.com/rss/g1/economia/',
        N'https://g1.globo.com/favicon.ico',
        N'Economia',
        N'1h'
    ),
    (
        N'G1 - Tecnologia',
        N'https://g1.globo.com/rss/g1/tecnologia/',
        N'https://g1.globo.com/favicon.ico',
        N'Tecnologia',
        N'1h'
    ),
    (
        N'G1 - Mundo',
        N'https://g1.globo.com/rss/g1/mundo/',
        N'https://g1.globo.com/favicon.ico',
        N'Internacional',
        N'1h'
    ),
    (
        N'G1 - Ciencia e Saude',
        N'https://g1.globo.com/rss/g1/ciencia-e-saude/',
        N'https://g1.globo.com/favicon.ico',
        N'Ciencia',
        N'2h'
    ),
    (
        N'G1 - Sao Paulo',
        N'https://g1.globo.com/rss/g1/sao-paulo/',
        N'https://g1.globo.com/favicon.ico',
        N'Regional',
        N'1h'
    ),

    -- ========================================================================
    -- GloboEsporte - 1 feed
    -- ========================================================================
    (
        N'GloboEsporte - Futebol',
        N'https://ge.globo.com/rss/ge/futebol/',
        N'https://ge.globo.com/favicon.ico',
        N'Esportes',
        N'30min'
    ),

    -- ========================================================================
    -- Folha de Sao Paulo - 5 feeds
    -- ========================================================================
    (
        N'Folha - Principal',
        N'https://feeds.folha.uol.com.br/folha/emcimadahora/rss091.xml',
        N'https://www.folha.uol.com.br/favicon.ico',
        N'Geral',
        N'30min'
    ),
    (
        N'Folha - Politica',
        N'https://feeds.folha.uol.com.br/poder/rss091.xml',
        N'https://www.folha.uol.com.br/favicon.ico',
        N'Politica',
        N'30min'
    ),
    (
        N'Folha - Mercado',
        N'https://feeds.folha.uol.com.br/mercado/rss091.xml',
        N'https://www.folha.uol.com.br/favicon.ico',
        N'Economia',
        N'1h'
    ),
    (
        N'Folha - Mundo',
        N'https://feeds.folha.uol.com.br/mundo/rss091.xml',
        N'https://www.folha.uol.com.br/favicon.ico',
        N'Internacional',
        N'1h'
    ),
    (
        N'Folha - Esporte',
        N'https://feeds.folha.uol.com.br/esporte/rss091.xml',
        N'https://www.folha.uol.com.br/favicon.ico',
        N'Esportes',
        N'1h'
    ),

    -- ========================================================================
    -- Estadao - 3 feeds
    -- ========================================================================
    (
        N'Estadao - Principal',
        N'https://www.estadao.com.br/rss/ultimas.xml',
        N'https://www.estadao.com.br/favicon.ico',
        N'Geral',
        N'30min'
    ),
    (
        N'Estadao - Politica',
        N'https://www.estadao.com.br/rss/politica.xml',
        N'https://www.estadao.com.br/favicon.ico',
        N'Politica',
        N'30min'
    ),
    (
        N'Estadao - Economia',
        N'https://www.estadao.com.br/rss/economia.xml',
        N'https://www.estadao.com.br/favicon.ico',
        N'Economia',
        N'1h'
    ),

    -- ========================================================================
    -- CNN Brasil - 1 feed
    -- ========================================================================
    (
        N'CNN Brasil',
        N'https://www.cnnbrasil.com.br/feed/',
        N'https://www.cnnbrasil.com.br/favicon.ico',
        N'Geral',
        N'30min'
    ),

    -- ========================================================================
    -- R7 - 1 feed
    -- ========================================================================
    (
        N'R7 - Noticias',
        N'https://noticias.r7.com/feed.xml',
        N'https://noticias.r7.com/favicon.ico',
        N'Geral',
        N'1h'
    ),

    -- ========================================================================
    -- Governo/Institucional - 3 feeds
    -- ========================================================================
    (
        N'Agencia Brasil',
        N'https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml',
        N'https://agenciabrasil.ebc.com.br/favicon.ico',
        N'Governo',
        N'1h'
    ),
    (
        N'Senado Noticias',
        N'https://www12.senado.leg.br/noticias/feed',
        N'https://www12.senado.leg.br/favicon.ico',
        N'Politica',
        N'2h'
    ),
    (
        N'Camara Noticias',
        N'https://www.camara.leg.br/noticias/feed.xml',
        N'https://www.camara.leg.br/favicon.ico',
        N'Politica',
        N'2h'
    ),

    -- ========================================================================
    -- Economia Especializada - 2 feeds
    -- ========================================================================
    (
        N'InfoMoney',
        N'https://www.infomoney.com.br/feed/',
        N'https://www.infomoney.com.br/favicon.ico',
        N'Economia',
        N'1h'
    ),
    (
        N'Valor Economico',
        N'https://valor.globo.com/rss/',
        N'https://valor.globo.com/favicon.ico',
        N'Economia',
        N'1h'
    ),

    -- ========================================================================
    -- Tecnologia - 1 feed
    -- ========================================================================
    (
        N'TecMundo',
        N'https://rss.tecmundo.com.br/feed',
        N'https://www.tecmundo.com.br/favicon.ico',
        N'Tecnologia',
        N'1h'
    ),

    -- ========================================================================
    -- Internacional - 2 feeds
    -- ========================================================================
    (
        N'BBC Brasil',
        N'https://www.bbc.com/portuguese/index.xml',
        N'https://www.bbc.com/favicon.ico',
        N'Internacional',
        N'1h'
    ),
    (
        N'Deutsche Welle Brasil',
        N'https://rss.dw.com/xml/rss-br-all',
        N'https://www.dw.com/favicon.ico',
        N'Internacional',
        N'2h'
    ),

    -- ========================================================================
    -- UOL - 1 feed
    -- ========================================================================
    (
        N'UOL - Noticias',
        N'https://rss.uol.com.br/feed/noticias.xml',
        N'https://www.uol.com.br/favicon.ico',
        N'Geral',
        N'1h'
    )
) AS source ([name], [url], [favicon_url], [category], [frequency])
ON target.[url] = source.[url]
WHEN NOT MATCHED THEN
    INSERT ([name], [url], [favicon_url], [category], [frequency], [active], [created_at], [updated_at])
    VALUES (source.[name], source.[url], source.[favicon_url], source.[category], source.[frequency], 1, GETUTCDATE(), GETUTCDATE())
WHEN MATCHED THEN
    UPDATE SET
        [name] = source.[name],
        [favicon_url] = source.[favicon_url],
        [category] = source.[category],
        [frequency] = source.[frequency],
        [updated_at] = GETUTCDATE();

PRINT 'RSS feed sources inserted/updated successfully.';
GO

-- ============================================================================
-- VERIFICATION
-- ============================================================================
PRINT '';
PRINT '============================================================================';
PRINT 'Seed data completed. Verifying inserted sources...';
PRINT '============================================================================';

-- Summary by category
SELECT
    [category] AS [Categoria],
    COUNT(*) AS [Total Fontes],
    STRING_AGG([name], ', ') WITHIN GROUP (ORDER BY [name]) AS [Fontes]
FROM [dbo].[sources]
GROUP BY [category]
ORDER BY COUNT(*) DESC;

-- Summary by frequency
SELECT
    [frequency] AS [Frequencia],
    COUNT(*) AS [Total Fontes]
FROM [dbo].[sources]
GROUP BY [frequency]
ORDER BY
    CASE [frequency]
        WHEN '15min' THEN 1
        WHEN '30min' THEN 2
        WHEN '1h' THEN 3
        WHEN '2h' THEN 4
        WHEN '6h' THEN 5
        ELSE 6
    END;

-- Full list
SELECT
    [id],
    [name] AS [Nome],
    [category] AS [Categoria],
    [frequency] AS [Frequencia],
    [url] AS [URL],
    [active] AS [Ativo]
FROM [dbo].[sources]
ORDER BY [category], [name];

PRINT '';
PRINT '============================================================================';
PRINT 'Total sources inserted: ' + CAST((SELECT COUNT(*) FROM [dbo].[sources]) AS NVARCHAR(10));
PRINT '============================================================================';
GO
