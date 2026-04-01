---
phase: 02-search-filter-performance
plan: B
type: execute
wave: 1
depends_on: []
files_modified:
  - FeedRSS/tmc-rss-collector/services/database.py
  - FeedRSS/tmc-rss-collector/services/cost_queries.py
  - FeedRSS/tmc-rss-collector/functions/articles_api.py
autonomous: true
requirements: [D-04, D-05, D-06, D-11, D-12, D-13, D-14, D-15, D-16]

must_haves:
  truths:
    - "Search for 'selecao brasileira' uses FREETEXT when catalog exists and falls back to LIKE when it does not"
    - "CAST on user_id/id JOIN in cost_by_user query is removed — direct UNIQUEIDENTIFIER comparison"
    - "Facet cache uses time-based TTL only, not filter_key invalidation"
    - "Tag search at database.py:519-523 also uses FREETEXT with fallback"
  artifacts:
    - path: "FeedRSS/tmc-rss-collector/services/database.py"
      provides: "FREETEXT search with LIKE fallback in _build_article_filters"
      contains: "FREETEXT"
    - path: "FeedRSS/tmc-rss-collector/services/cost_queries.py"
      provides: "Direct UNIQUEIDENTIFIER JOIN without CAST"
      contains: "l.user_id = u.id"
    - path: "FeedRSS/tmc-rss-collector/functions/articles_api.py"
      provides: "Time-only facet cache without filter_key dependency"
      contains: "cache_age < FACET_CACHE_TTL"
  key_links:
    - from: "database.py _build_article_filters()"
      to: "migrations/021_fulltext_search.sql"
      via: "FREETEXT predicate requires full-text index; fallback to LIKE if catalog missing"
      pattern: "FREETEXT.*title.*preview.*tags"
    - from: "database.py _build_article_filters()"
      to: "database.py get_articles()"
      via: "Returns (where_clause, params, needs_scores_join) — signature unchanged"
      pattern: "return where_clause, params, needs_scores_join"
    - from: "cost_queries.py get_cost_by_user()"
      to: "migrations/005_auth_users.sql + 017_cost_tracking_extensions.sql"
      via: "Both columns are UNIQUEIDENTIFIER — CAST removed"
      pattern: "l\\.user_id = u\\.id"
    - from: "articles_api.py list_articles_handler()"
      to: "_facet_cache dict"
      via: "Cache hit check uses only timestamp TTL, no filter_key"
      pattern: "cache_age < FACET_CACHE_TTL"
---

<objective>
Replace LIKE full-table-scan searches with FREETEXT (with graceful LIKE fallback), remove the unnecessary CAST on the cost-by-user JOIN, and decouple the facet cache from per-keystroke invalidation.

Purpose: These three query-level fixes address the root causes of all 4 P0 performance bugs: compound word search freezes (LIKE scan), costs page slow (CAST kills index usage), and filter degradation (facet cache thrashes on every keystroke).

Output: Surgical edits to 3 existing Python files — no new files created. All edits are at specific line ranges documented in CONTEXT.md.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-search-filter-performance/02-CONTEXT.md

<interfaces>
<!-- _build_article_filters return contract — MUST NOT CHANGE -->
From FeedRSS/tmc-rss-collector/services/database.py:456-527:
```python
def _build_article_filters(self, category=None, source_id=None, period=None,
                           search=None, tag=None, classification=None):
    """Build WHERE clause for article queries.
    Returns: (where_clause: str, params: list, needs_scores_join: bool)
    """
    # ... filter logic ...
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, params, needs_scores_join
```

<!-- get_cost_by_user signature — return dict unchanged -->
From FeedRSS/tmc-rss-collector/services/cost_queries.py:314:
```python
def get_cost_by_user(start_date, end_date) -> dict:
    """Per-user cost breakdown, JOINed with users table."""
```

<!-- Facet cache structure — articles_api.py:23-29 -->
```python
_facet_cache = {
    "categories": None,
    "tags": None,
    "timestamp": 0,
    "filter_key": None,  # THIS KEY IS BEING REMOVED
}
FACET_CACHE_TTL = 300  # seconds — keep as-is
```

<!-- Current LIKE search block — database.py:495-523 -->
```python
# Lines 495-517: 5 LIKE conditions with COLLATE Latin1_General_CI_AI
# Lines 519-523: tag LIKE with COLLATE Latin1_General_CI_AI
# Both blocks to be replaced with FREETEXT + fallback
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace LIKE search with FREETEXT + fallback in database.py</name>
  <files>FeedRSS/tmc-rss-collector/services/database.py</files>

  <read_first>
    - FeedRSS/tmc-rss-collector/services/database.py:456-527 (the full _build_article_filters method)
    - FeedRSS/tmc-rss-collector/services/database.py:529-540 (get_articles signature that calls _build_article_filters — verify return contract)
    - .planning/phases/02-search-filter-performance/02-CONTEXT.md (decisions D-04, D-05, D-06)
  </read_first>

  <action>
    SURGICAL EDIT at database.py lines 495-523. Replace the entire `if search:` block (lines 495-517) AND the `if tag:` block (lines 519-523) with FREETEXT + LIKE fallback.

    **Per D-04:** The code MUST check whether the full-text catalog exists before using FREETEXT. Use a try/except approach — attempt FREETEXT first, catch the specific error if catalog is not ready, then fall back to LIKE.

    However, since `_build_article_filters` only BUILDS the WHERE clause (it does not execute queries), the fallback strategy must be different. Instead, add a module-level flag that caches whether full-text is available, checked once at startup or on first search.

    Replace lines 495-523 with this logic:

    ```python
        if search:
            if self._has_fulltext_index():
                # Per D-05: Single FREETEXT predicate replaces 5 LIKE conditions
                # Per D-06: No COLLATE needed — FREETEXT uses index language config
                conditions.append("FREETEXT((a.title, a.preview, a.tags), %s)")
                params.append(search)
            else:
                # Fallback to LIKE if full-text catalog not yet built (per D-04)
                search_escaped = search.replace('[', '[[]').replace('%', '[%]').replace('_', '[_]')
                search_with_spaces = search_escaped.replace('-', ' ')
                search_param = f"%{search_escaped}%"

                if search_with_spaces != search_escaped:
                    search_param_spaces = f"%{search_with_spaces}%"
                    conditions.append("""(
                        a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                        OR a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                        OR a.preview COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                        OR a.preview COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                        OR a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    )""")
                    params.extend([search_param, search_param_spaces, search_param, search_param_spaces, search_param])
                else:
                    conditions.append("""(
                        a.title COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                        OR a.preview COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                        OR a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                    )""")
                    params.extend([search_param, search_param, search_param])

        if tag:
            if self._has_fulltext_index():
                # Tag search also uses FREETEXT since tags column is in the full-text index
                # Use CONTAINS for exact tag match (FREETEXT would stem the word)
                conditions.append("""
                    CONTAINS(a.tags, %s)
                """)
                # CONTAINS requires double-quoting the literal for exact phrase match
                params.append(f'"{tag}"')
            else:
                # Fallback to LIKE for tag search (per D-04)
                conditions.append("""
                    a.tags COLLATE Latin1_General_CI_AI LIKE %s COLLATE Latin1_General_CI_AI
                """)
                tag_param = f'%"{tag}"%'
                params.append(tag_param)
    ```

    Also add the `_has_fulltext_index` helper method to the DatabaseService class. Place it BEFORE `_build_article_filters` (around line 455):

    ```python
    _fulltext_available = None  # Module-level cache: None=unchecked, True/False=result

    def _has_fulltext_index(self) -> bool:
        """Check if the ArticleCatalog full-text index is available.
        Result is cached after first check — rechecked only if False (index may still be building).
        """
        global _fulltext_available
        if _fulltext_available is True:
            return True
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 1 FROM sys.fulltext_indexes fi
                    JOIN sys.objects o ON fi.object_id = o.object_id
                    WHERE o.name = 'collected_articles'
                """)
                result = cursor.fetchone()
                _fulltext_available = result is not None
                if _fulltext_available:
                    logger.info("[DatabaseService] Full-text index detected on collected_articles")
                return _fulltext_available
        except Exception as e:
            logger.warning(f"[DatabaseService] Full-text check failed, using LIKE fallback: {e}")
            return False
    ```

    Place `_fulltext_available = None` at module level near the top imports (after the existing module-level variables).

    **CRITICAL CONSTRAINTS:**
    - database.py is 131KB — do NOT rewrite beyond lines 455-527
    - The return signature `(where_clause, params, needs_scores_join)` MUST remain identical
    - The `needs_scores_join` variable is NOT affected by search changes
    - Preserve all other filter conditions (classification, category, source_id, period) unchanged
    - For tag search, use CONTAINS (not FREETEXT) because tag matching should be exact phrase, not stemmed
  </action>

  <verify>
    <automated>cd "FeedRSS/tmc-rss-collector" && python -c "from services.database import DatabaseService; print('import OK')" 2>&1</automated>
  </verify>

  <acceptance_criteria>
    - database.py contains `FREETEXT((a.title, a.preview, a.tags), %s)` string (per D-05)
    - database.py contains `_has_fulltext_index` method definition
    - database.py contains `_fulltext_available = None` module-level variable
    - database.py contains `CONTAINS(a.tags, %s)` for tag search with full-text
    - database.py still contains the LIKE fallback code within the `else` branch (per D-04)
    - database.py does NOT contain `COLLATE Latin1_General_CI_AI` inside the FREETEXT branch (per D-06)
    - `return where_clause, params, needs_scores_join` line still exists unchanged at end of method
    - The method still handles all 6 filter parameters: classification, category, source_id, period, search, tag
    - `python -c "from services.database import DatabaseService"` succeeds without import errors
  </acceptance_criteria>

  <done>_build_article_filters uses FREETEXT for search and CONTAINS for tag when full-text index is available, gracefully falls back to original LIKE queries when catalog is not yet built. Return signature unchanged.</done>
</task>

<task type="auto">
  <name>Task 2: Remove CAST on JOIN in cost_by_user query</name>
  <files>FeedRSS/tmc-rss-collector/services/cost_queries.py</files>

  <read_first>
    - FeedRSS/tmc-rss-collector/services/cost_queries.py:314-345 (full get_cost_by_user function)
    - FeedRSS/tmc-rss-collector/migrations/005_auth_users.sql (confirm users.id is UNIQUEIDENTIFIER)
    - FeedRSS/tmc-rss-collector/migrations/017_cost_tracking_extensions.sql (confirm llm_usage_log.user_id is UNIQUEIDENTIFIER)
    - .planning/phases/02-search-filter-performance/02-CONTEXT.md (decisions D-11, D-12)
  </read_first>

  <action>
    SURGICAL EDIT at cost_queries.py line 333. This is a single-line fix (per D-12).

    **Current code (line 333):**
    ```python
                LEFT JOIN users u ON CAST(l.user_id AS VARCHAR(36)) = CAST(u.id AS VARCHAR(36))
    ```

    **Replace with:**
    ```python
                LEFT JOIN users u ON l.user_id = u.id
    ```

    Per D-11: Both `users.id` and `llm_usage_log.user_id` are UNIQUEIDENTIFIER type (confirmed in migrations 005 and 017). The double CAST to VARCHAR(36) is completely unnecessary and prevents the query optimizer from using indexes on either column.

    **CRITICAL CONSTRAINTS:**
    - This is a ONE LINE change at line 333
    - Do NOT modify any other lines in cost_queries.py
    - Preserve the `LEFT JOIN` (not INNER JOIN) — system operations have NULL user_id
    - Preserve the `ISNULL(CAST(l.user_id AS VARCHAR(36)), 'system')` in the SELECT list at line 325 — that CAST is for display purposes (converting UUID to string for the JSON response), NOT for the JOIN
    - The SELECT CAST at line 325 serves a different purpose (display) and must remain
  </action>

  <verify>
    <automated>cd "FeedRSS/tmc-rss-collector" && python -c "from services.cost_queries import get_cost_by_user; print('import OK')" 2>&1</automated>
  </verify>

  <acceptance_criteria>
    - cost_queries.py line 333 (or the LEFT JOIN line) contains `l.user_id = u.id` (per D-12)
    - cost_queries.py line 333 does NOT contain `CAST(l.user_id AS VARCHAR(36)) = CAST(u.id AS VARCHAR(36))`
    - cost_queries.py line 325 still contains `CAST(l.user_id AS VARCHAR(36))` in the SELECT (display cast preserved)
    - cost_queries.py still contains `LEFT JOIN users u` (not changed to INNER JOIN)
    - `python -c "from services.cost_queries import get_cost_by_user"` succeeds without import errors
  </acceptance_criteria>

  <done>The double CAST on the user_id JOIN is removed. Query optimizer can now use indexes on both users.id and llm_usage_log.user_id for the JOIN operation.</done>
</task>

<task type="auto">
  <name>Task 3: Decouple facet cache from filter_key invalidation</name>
  <files>FeedRSS/tmc-rss-collector/functions/articles_api.py</files>

  <read_first>
    - FeedRSS/tmc-rss-collector/functions/articles_api.py:18-30 (facet cache initialization and TTL)
    - FeedRSS/tmc-rss-collector/functions/articles_api.py:96-174 (facet computation block — the full cache check, computation, and storage)
    - .planning/phases/02-search-filter-performance/02-CONTEXT.md (decisions D-13, D-14, D-15, D-16)
  </read_first>

  <action>
    SURGICAL EDITS at 4 specific locations in articles_api.py (per D-14, D-16):

    **Edit 1 — Cache initialization (lines 23-28):**
    Remove `filter_key` from the cache dict. Change from:
    ```python
    _facet_cache = {
        "categories": None,
        "tags": None,
        "timestamp": 0,
        "filter_key": None,  # cache is keyed on active filters
    }
    ```
    To:
    ```python
    _facet_cache = {
        "categories": None,
        "tags": None,
        "timestamp": 0,
    }
    ```

    **Edit 2 — Cache hit check (lines 106-113):**
    Remove the `filter_key` comparison from cache hit logic. Change from:
    ```python
                filter_key = (category, tag, source, period, search, classification)
                now = time.time()
                cache_age = now - _facet_cache["timestamp"]
                cache_hit = (
                    cache_age < FACET_CACHE_TTL
                    and _facet_cache["filter_key"] == filter_key
                    and _facet_cache["categories"] is not None
                )
    ```
    To:
    ```python
                now = time.time()
                cache_age = now - _facet_cache["timestamp"]
                cache_hit = (
                    cache_age < FACET_CACHE_TTL
                    and _facet_cache["categories"] is not None
                )
    ```
    Note: The `filter_key` local variable is also used at line 163 for logging. Keep it there ONLY for the log message, or remove it from logging too. Preferred: remove it from logging since it no longer drives cache behavior.

    **Edit 3 — Cache storage (lines 166-169):**
    Remove `filter_key` from cache storage. Change from:
    ```python
                    _facet_cache["categories"] = cat_list
                    _facet_cache["tags"] = tag_items
                    _facet_cache["timestamp"] = now
                    _facet_cache["filter_key"] = filter_key
    ```
    To:
    ```python
                    _facet_cache["categories"] = cat_list
                    _facet_cache["tags"] = tag_items
                    _facet_cache["timestamp"] = now
    ```

    **Edit 4 — Log message (line 163):**
    The MISS log line references `filter_key`. Update it:
    Change from:
    ```python
                    logger.info(f"[list_articles] Facet cache MISS — computed in {facet_ms:.0f}ms (filters={filter_key})")
    ```
    To:
    ```python
                    logger.info(f"[list_articles] Facet cache MISS — computed in {facet_ms:.0f}ms")
    ```

    Per D-15: Facet counts are global aggregations for dropdown population. They don't need per-search-term freshness. The 5-minute TTL (FACET_CACHE_TTL=300) already provides acceptable staleness.

    **IMPORTANT:** The facet COMPUTATION still uses the contextual filters (cat_kwargs, tag_kwargs at lines 123-158) to compute filtered counts. We are NOT changing what facets are computed — only how the cache invalidation works. The cache now returns the LAST computed facets for up to 5 minutes regardless of filter changes. This is acceptable because facet counts are approximate navigation aids, not exact values.

    **CRITICAL CONSTRAINTS:**
    - Do NOT change FACET_CACHE_TTL value (keep at 300)
    - Do NOT change the facet computation logic (lines 120-160)
    - Do NOT change the facet kwargs building (cat_kwargs, tag_kwargs)
    - Do NOT remove the `skip_facets` optimization (lines 100-101)
    - Only remove `filter_key` from cache dict, cache hit check, cache storage, and logging
  </action>

  <verify>
    <automated>cd "FeedRSS/tmc-rss-collector" && python -c "from functions.articles_api import list_articles_handler; print('import OK')" 2>&1</automated>
  </verify>

  <acceptance_criteria>
    - articles_api.py `_facet_cache` dict does NOT contain `"filter_key"` key
    - articles_api.py cache hit check does NOT contain `_facet_cache["filter_key"]`
    - articles_api.py cache storage block does NOT contain `_facet_cache["filter_key"] = filter_key`
    - articles_api.py cache hit check still contains `cache_age < FACET_CACHE_TTL`
    - articles_api.py still contains `FACET_CACHE_TTL = 300`
    - articles_api.py still contains `_facet_cache["categories"] is not None` in cache hit check
    - articles_api.py still contains `_facet_cache["categories"] = cat_list` in cache storage
    - articles_api.py still contains `skip_facets` check (line 100)
    - `python -c "from functions.articles_api import list_articles_handler"` succeeds without import errors
  </acceptance_criteria>

  <done>Facet cache uses time-based TTL only (300s). No longer invalidates on every search keystroke. Cache hit rate will go from near-zero (invalidated every keypress) to high (refreshes only every 5 minutes).</done>
</task>

</tasks>

<verification>
After all 3 tasks complete:
1. `cd FeedRSS/tmc-rss-collector && python -c "from services.database import DatabaseService; from services.cost_queries import get_cost_by_user; from functions.articles_api import list_articles_handler; print('All imports OK')"` succeeds
2. `grep -n "FREETEXT" FeedRSS/tmc-rss-collector/services/database.py` shows FREETEXT predicate in _build_article_filters
3. `grep -n "l.user_id = u.id" FeedRSS/tmc-rss-collector/services/cost_queries.py` shows direct JOIN without CAST
4. `grep -n "filter_key" FeedRSS/tmc-rss-collector/functions/articles_api.py` returns NO matches (filter_key fully removed)
5. `_build_article_filters` return signature is unchanged: `(where_clause, params, needs_scores_join)`
</verification>

<success_criteria>
- database.py uses FREETEXT for search when full-text catalog available, LIKE fallback otherwise
- cost_queries.py JOIN at line 333 uses direct `l.user_id = u.id` (no CAST)
- articles_api.py facet cache uses time-only TTL, filter_key completely removed
- All 3 files import without errors
- No other lines in these 131KB/cost_queries/articles_api files were modified beyond the specified ranges
</success_criteria>

<output>
After completion, create `.planning/phases/02-search-filter-performance/02-B-SUMMARY.md`
</output>
