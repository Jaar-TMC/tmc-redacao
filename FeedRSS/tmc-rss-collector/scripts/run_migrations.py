"""Run migrations 005-008 against Azure SQL."""
import os
import sys
import json

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

    conn = pymssql.connect(
        server=os.environ["SQL_SERVER"],
        user=os.environ["SQL_USERNAME"],
        password=os.environ["SQL_PASSWORD"],
        database=os.environ["SQL_DATABASE"],
        login_timeout=30,
        timeout=60
    )
    cursor = conn.cursor()

    migrations_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "migrations"
    )

    migration_files = [
        "005_auth_users.sql",
        "006_token_blacklist.sql",
        "007_user_articles_add_user_id.sql",
        "008_auth_audit_log.sql",
    ]

    for mfile in migration_files:
        path = os.path.join(migrations_dir, mfile)
        print(f"Running {mfile}...", end=" ")
        try:
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()
            cursor.execute(sql)
            conn.commit()
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            conn.rollback()

    # Verify
    cursor.execute("""
        SELECT name FROM sys.tables
        WHERE name IN ('users', 'token_blacklist', 'auth_audit_log')
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\nTables created: {tables}")

    cursor.execute("""
        SELECT COUNT(*) FROM sys.columns
        WHERE object_id = OBJECT_ID('user_articles') AND name = 'user_id'
    """)
    has_col = cursor.fetchone()[0]
    print(f"user_articles.user_id exists: {bool(has_col)}")

    conn.close()

if __name__ == "__main__":
    main()
