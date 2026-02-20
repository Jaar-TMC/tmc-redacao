-- Migration 007: Add user_id to user_articles
-- Links existing user_articles to the new users table.
-- NULL allowed for existing articles that predate auth.
-- Created: 2026-02-20

IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('user_articles') AND name = 'user_id'
)
BEGIN
    ALTER TABLE user_articles
        ADD user_id UNIQUEIDENTIFIER NULL;

    ALTER TABLE user_articles
        ADD CONSTRAINT FK_user_articles_user FOREIGN KEY (user_id)
            REFERENCES users (id);

    CREATE INDEX IX_user_articles_user
        ON user_articles (user_id)
        WHERE user_id IS NOT NULL;

    PRINT 'Added user_id column to user_articles with FK and index';
END
ELSE
BEGIN
    PRINT 'user_articles.user_id column already exists, skipping';
END
