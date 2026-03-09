import pymssql, json, os
from datetime import datetime

SQ = chr(39)
SERVER = os.environ.get("SQL_SERVER", "")
DATABASE = os.environ.get("SQL_DATABASE", "")
USER = os.environ.get("SQL_USERNAME", "")
PASSWORD = os.environ.get("SQL_PASSWORD", "")

conn = pymssql.connect(server=SERVER, database=DATABASE, user=USER, password=PASSWORD, timeout=120, login_timeout=30)
cursor = conn.cursor()
print("Connected!")

def rq(sql, params=None):
    cursor.execute(sql, params) if params else cursor.execute(sql)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

print(chr(10) + "=" * 80)
print("QUERY 1: 5 Recent articles with substantial content")
print("=" * 80)
Q1 = """SELECT TOP 5 ca.id, ca.title, s.name as source_name,
    SUBSTRING(ca.content, 1, 500) as content_preview,
    LEN(ca.content) as content_len, ca.published_at, ca.category
FROM collected_articles ca JOIN sources s ON ca.source_id = s.id
WHERE ca.content IS NOT NULL AND LEN(ca.content) > 300
ORDER BY ca.published_at DESC"""
q1 = rq(Q1)
for a in q1:
    print("  ID:", a["id"])
    print("  Title:", a["title"])
    print("  Source:", a["source_name"])
    print("  Len:", a["content_len"], "chars")
    print("  Date:", a["published_at"])
    print("  Cat:", a["category"])
    print("  Preview:", str(a.get("content_preview",""))[:200])
    print()
recent_ids = [a["id"] for a in q1]

print("=" * 80)
print("QUERY 2: Articles sharing themes")
print("=" * 80)
Q2 = """SELECT TOP 10 at1.article_id, ca.title, s.name as source_name,
    at1.theme_id, t.name as theme_name, LEN(ca.content) as content_len
FROM article_themes at1
JOIN collected_articles ca ON at1.article_id = ca.id
JOIN sources s ON ca.source_id = s.id
JOIN themes t ON at1.theme_id = t.id
WHERE ca.content IS NOT NULL AND LEN(ca.content) > 300
AND t.article_count >= 2
ORDER BY ca.published_at DESC"""
q2 = rq(Q2)
themes_seen = {}
for a in q2:
    print("  Article ID:", a["article_id"])
    print("  Title:", a["title"])
    print("  Source:", a["source_name"])
    print("  Theme:", a["theme_id"], "-", a["theme_name"])
    print("  Len:", a["content_len"], "chars")
    print()
    tid = str(a["theme_id"])
    themes_seen.setdefault(tid, []).append(a)

print("  --- Theme Groupings ---")
for tid, arts in themes_seen.items():
    if len(arts) >= 2:
        print("  Theme ID:", tid, "-", arts[0]["theme_name"], "has", len(arts), "articles:")
        for a in arts:
            print("    -", a["article_id"], a["title"], "("+a["source_name"]+")")
has_groups = any(len(arts) >= 2 for arts in themes_seen.values())
if not has_groups:
    print("  (No theme has 2+ articles in top 10)")
    for tid, arts in themes_seen.items():
        for a in arts:
            print("    Theme", tid, ":", a["article_id"], a["title"])

themed_ids = list(set(str(a["article_id"]) for a in q2))
all_ids = list(set([str(x) for x in recent_ids] + themed_ids))

print(chr(10) + "=" * 80)
print("QUERY 3: Full content")
print("=" * 80)
if all_ids:
    quoted = [chr(39) + x + chr(39) for x in all_ids]
    id_csv = ",".join(quoted)
    q3sql = "SELECT ca.id, ca.title, s.name as source_name, ca.content, ca.published_at, ca.category FROM collected_articles ca JOIN sources s ON ca.source_id = s.id WHERE ca.id IN (" + id_csv + ")"
    q3 = rq(q3sql)
else:
    q3 = rq("SELECT TOP 10 ca.id, ca.title, s.name as source_name, ca.content, ca.published_at, ca.category FROM collected_articles ca JOIN sources s ON ca.source_id = s.id WHERE ca.content IS NOT NULL AND LEN(ca.content) > 300 ORDER BY ca.published_at DESC")

for a in q3:
    clen = len(a["content"]) if a.get("content") else 0
    a["content_len"] = clen
    print("  ID:", a["id"])
    print("  Title:", a["title"])
    print("  Source:", a["source_name"])
    print("  Category:", a.get("category"))
    print("  Date:", a["published_at"])
    print("  Content len:", clen, "chars")
    cp = (a.get("content") or "(empty)")[:300]
    print("  Content preview:", cp)
    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
content_map = {str(a["id"]): a for a in q3}

print(chr(10) + "--- Single Articles ---")
singles = []
for aid in recent_ids:
    k = str(aid)
    if k in content_map:
        a = content_map[k]
        singles.append({"id": str(a["id"]), "title": a["title"], "source_name": a["source_name"], "category": a.get("category"), "content_len": a.get("content_len",0), "published_at": str(a.get("published_at"))})
        print("  ["+str(a["id"])+"]", a["title"], "-", a["source_name"], "("+str(a.get("content_len",0))+" chars)")

print(chr(10) + "--- Theme Groups ---")
groups = []
for tid, arts in themes_seen.items():
    if len(arts) >= 2:
        g = {"theme_id": tid, "theme_name": arts[0]["theme_name"], "articles": []}
        print("  Theme:", arts[0]["theme_name"], "(ID:", tid, ")")
        for a in arts:
            k = str(a["article_id"])
            if k in content_map:
                c = content_map[k]
                g["articles"].append({"id": str(c["id"]), "title": c["title"], "source_name": c["source_name"], "content_len": c.get("content_len",0)})
                print("    ["+str(c["id"])+"]", c["title"], "("+str(c.get("content_len",0))+" chars)")
        groups.append(g)

out_dir = "C:\\Users\\enzoc\\OneDrive - jaarconsult.com.br\\JaarConsult - Oficial - TMC\\Projeto Ferramenta TMC\\FeedRSS\\tmc-rss-collector\\scripts"
out_path = os.path.join(out_dir, "fetch_test_articles_results.json")
output = {
    "fetched_at": datetime.now().isoformat(),
    "summary": {"single_articles": singles, "theme_groups": groups},
    "full_articles": [{"id": str(a["id"]), "title": a["title"], "source_name": a["source_name"], "category": a.get("category"), "content": a.get("content"), "content_len": a.get("content_len",0), "published_at": str(a.get("published_at"))} for a in q3],
}
with open(out_path, "w", encoding="utf-8") as fout:
    json.dump(output, fout, ensure_ascii=False, indent=2)
print(chr(10) + "Results saved to:", out_path)
cursor.close()
conn.close()
print("Done!")
