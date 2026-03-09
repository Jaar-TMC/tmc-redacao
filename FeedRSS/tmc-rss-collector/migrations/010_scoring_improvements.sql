-- Migration 010: Scoring System Improvements
-- Updates classification threshold B from 40 to 35
-- Adds 'maybe' as valid value for sinal_conversa
-- Created: 2026-03-09

-- 1. Update the classification function with new threshold
CREATE OR ALTER FUNCTION dbo.fn_get_classification (@total_score INT)
RETURNS CHAR(1)
AS
BEGIN
    RETURN CASE
        WHEN @total_score >= 75 THEN 'A'
        WHEN @total_score >= 35 THEN 'B'
        ELSE 'C'
    END;
END;
GO

-- 2. Reclassify existing articles that scored 35-39 (were C, now B)
UPDATE article_scores
SET classification = 'B'
WHERE total_score >= 35 AND total_score < 40 AND classification = 'C';

DECLARE @reclassified INT = @@ROWCOUNT;
PRINT 'Reclassified ' + CAST(@reclassified AS VARCHAR) + ' articles from C to B (score 35-39)';
GO

-- 3. Update theme classifications with new threshold
UPDATE t
SET t.classification = CASE
    WHEN t.avg_score >= 75 THEN 'A'
    WHEN t.avg_score >= 35 THEN 'B'
    ELSE 'C'
END
FROM themes t
WHERE t.avg_score IS NOT NULL
  AND t.avg_score >= 35 AND t.avg_score < 40
  AND t.classification = 'C';

DECLARE @themes_reclassified INT = @@ROWCOUNT;
PRINT 'Reclassified ' + CAST(@themes_reclassified AS VARCHAR) + ' themes from C to B';
GO
