import pymssql

conn = pymssql.connect(
    server='bi4ia-tmc.database.windows.net',
    user='admjaar',
    password='mbfb)Zxkxehpv%NQD8ba',
    database='tmc'
)

cursor = conn.cursor()

print("=" * 50)
print("DATABASE SCHEMA VALIDATION")
print("=" * 50)

# Check tables exist
print("\n1. CHECKING TABLES:")
print("-" * 30)
tables = ['themes', 'article_embeddings', 'article_themes', 'article_scores']
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table}'")
    exists = cursor.fetchone()[0] > 0
    print(f"   Table {table}: {'EXISTS' if exists else 'MISSING'}")

# Check columns on collected_articles
print("\n2. CHECKING NEW COLUMNS IN collected_articles:")
print("-" * 30)
cursor.execute("""
    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'collected_articles'
    AND COLUMN_NAME IN ('has_embedding', 'has_score', 'primary_theme_id')
""")
cols = [row[0] for row in cursor.fetchall()]
print(f"   New columns found: {cols}")

expected_cols = ['has_embedding', 'has_score', 'primary_theme_id']
missing = [c for c in expected_cols if c not in cols]
if missing:
    print(f"   MISSING columns: {missing}")
else:
    print("   All expected columns present!")

# Count articles
print("\n3. ARTICLE STATISTICS:")
print("-" * 30)
cursor.execute("SELECT COUNT(*) FROM collected_articles")
total = cursor.fetchone()[0]
print(f"   Total articles: {total}")

# Count articles without embeddings
cursor.execute("SELECT COUNT(*) FROM collected_articles WHERE has_embedding = 0 OR has_embedding IS NULL")
pending_embedding = cursor.fetchone()[0]
print(f"   Articles pending embedding: {pending_embedding}")

# Check themes table content
print("\n4. THEMES TABLE:")
print("-" * 30)
cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'themes'")
if cursor.fetchone()[0] > 0:
    cursor.execute("SELECT id, name, slug FROM themes ORDER BY id")
    themes = cursor.fetchall()
    if themes:
        print(f"   Themes defined: {len(themes)}")
        for theme in themes:
            print(f"      - {theme[0]}: {theme[1]} ({theme[2]})")
    else:
        print("   No themes defined yet")
else:
    print("   Table does not exist")

# Check article_embeddings structure
print("\n5. ARTICLE_EMBEDDINGS TABLE STRUCTURE:")
print("-" * 30)
cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'article_embeddings'")
if cursor.fetchone()[0] > 0:
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'article_embeddings'
        ORDER BY ORDINAL_POSITION
    """)
    columns = cursor.fetchall()
    for col in columns:
        length = f"({col[2]})" if col[2] else ""
        print(f"   - {col[0]}: {col[1]}{length}")
else:
    print("   Table does not exist")

print("\n" + "=" * 50)
print("VALIDATION COMPLETE")
print("=" * 50)

conn.close()
