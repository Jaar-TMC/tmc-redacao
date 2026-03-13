"""Run migration 013 (denormalize scores) against Azure SQL production database."""
import os
import sys
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_local_settings():
    settings_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "local.settings.json"
    )
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            settings = json.load(f)
            for key, value in settings.get("Values", {}).items():
                os.environ.setdefault(key, str(value))


def main():
    load_local_settings()

    import pymssql

    print(f"Connecting to {os.environ.get('SQL_SERVER')} / {os.environ.get('SQL_DATABASE')}...")
    conn = pymssql.connect(
        server=os.environ["SQL_SERVER"],
        user=os.environ["SQL_USERNAME"],
        password=os.environ["SQL_PASSWORD"],
        database=os.environ["SQL_DATABASE"],
        login_timeout=30,
        timeout=120
    )
    cursor = conn.cursor()

    # Verify current state before running
    cursor.execute("""
        SELECT COUNT(*) FROM sys.columns
        WHERE object_id = OBJECT_ID('collected_articles')
        AND name IN ('total_score', 'classification')
    """)
    existing_cols = cursor.fetchone()[0]
    print(f"Existing denormalized columns: {existing_cols}/2")

    if existing_cols == 2:
        print("Migration 013 already applied — columns exist. Verifying backfill...")
        cursor.execute("""
            SELECT COUNT(*) FROM collected_articles WHERE total_score IS NOT NULL
        """)
        backfilled = cursor.fetchone()[0]
        print(f"Articles with scores backfilled: {backfilled}")
        conn.close()
        return

    migrations_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "migrations"
    )

    path = os.path.join(migrations_dir, "013_denormalize_scores.sql")
    with open(path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # pymssql doesn't support GO - split on it and run each batch
    batches = [b.strip() for b in re.split(r'\bGO\b', sql_content, flags=re.IGNORECASE) if b.strip()]

    print(f"\nRunning migration 013 ({len(batches)} batches)...")
    for i, batch in enumerate(batches, 1):
        print(f"  Batch {i}/{len(batches)}...", end=" ")
        try:
            cursor.execute(batch)
            conn.commit()
            print("OK")
        except Exception as e:
            conn.rollback()
            print(f"ERROR: {e}")
            raise

    # Verify
    cursor.execute("""
        SELECT COUNT(*) FROM sys.columns
        WHERE object_id = OBJECT_ID('collected_articles')
        AND name IN ('total_score', 'classification')
    """)
    cols = cursor.fetchone()[0]
    print(f"\nColumns after migration: {cols}/2")

    cursor.execute("SELECT COUNT(*) FROM collected_articles WHERE total_score IS NOT NULL")
    backfilled = cursor.fetchone()[0]
    print(f"Articles backfilled with scores: {backfilled}")

    cursor.execute("""
        SELECT name FROM sys.indexes
        WHERE object_id = OBJECT_ID('collected_articles')
        AND name IN ('IX_articles_score_order', 'IX_articles_class_score', 'IX_articles_category_score')
    """)
    indexes = [row[0] for row in cursor.fetchall()]
    print(f"Indexes created: {indexes}")

    conn.close()
    print("\nMigration 013 complete. The /api/articles 500 error should be resolved.")


if __name__ == "__main__":
    main()
