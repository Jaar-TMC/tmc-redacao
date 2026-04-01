---
phase: 02-search-filter-performance
verified: 2026-04-01T21:00:00Z
status: human_needed
score: 7/7 automated must-haves verified
human_verification:
  - test: "Search for 'seleção brasileira' after migration 021 runs in production"
    expected: "Results appear in under 2 seconds (FREETEXT index is active)"
    why_human: "Full-text catalog is created by migration 021 which runs on Azure SQL — cannot verify index population or FREETEXT routing without a live database connection"
  - test: "Score filter A / B / C / All tabs in RedacaoPage"
    expected: "Each tab responds in under 1 second"
    why_human: "IX_articles_score_filter is a database-side index — response time requires live production data with the migration applied"
  - test: "Costs page (/configuracoes/custos) initial load"
    expected: "Page loads and all 6 cost charts render in under 3 seconds"
    why_human: "IX_llm_usage_created covering index requires production data volume and the migration applied to observe speedup; page also requires manage_users permission"
  - test: "Typing in the search input on the main feed page (/)"
    expected: "UI does not freeze; requests fire at most once per 500ms burst; no visible lag while typing"
    why_human: "Debounce behavior and AbortController cancellation require interactive browser testing; cannot be verified by static analysis"
---

# Phase 02: Search/Filter Performance Verification Report

**Phase Goal:** Fix LIKE query freezes, add missing indexes, optimize costs page, fix facet cache thrashing
**Verified:** 2026-04-01T21:00:00Z
**Status:** human_needed — all automated checks pass; 4 performance outcomes require production deployment to confirm
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | FREETEXT replaces LIKE scan for search, with LIKE fallback when catalog absent | VERIFIED | `database.py:525` `FREETEXT((a.title, a.preview, a.tags), %s)`; `_has_fulltext_index()` method at line 449; `_fulltext_available = None` module-level flag at line 32 |
| 2 | CAST removed from UUID JOIN in cost_by_user | VERIFIED | `cost_queries.py:333` `LEFT JOIN users u ON l.user_id = u.id`; display CAST at line 325 preserved |
| 3 | Facet cache uses TTL-only invalidation (no filter_key) | VERIFIED | `articles_api.py:23-27` `_facet_cache` dict has no `filter_key` key; zero matches for `filter_key` in file; cache hit check at line 106-108 uses only `cache_age < FACET_CACHE_TTL` |
| 4 | Tag search uses CONTAINS with exact match fallback | VERIFIED | `database.py:554` `CONTAINS(a.tags, %s)` with `f'"{tag}"'` exact quote wrapping; LIKE fallback at lines 559-562 |
| 5 | Search debounce is 500ms in FilterBar | VERIFIED | `FilterBar.jsx:101` `}, 500);`; no `}, 300)` in debounce handler; `clearTimeout` cleanup preserved |
| 6 | Full-text migration file is complete and idempotent | VERIFIED | `021_fulltext_search.sql`: `FULLTEXT CATALOG ArticleCatalog`, `LANGUAGE 1046` x3, `KEY INDEX PK_collected_articles`, both `IF NOT EXISTS` guards present |
| 7 | Performance index migration is complete and idempotent | VERIFIED | `022_cost_performance_indexes.sql`: `IX_llm_usage_created` with INCLUDE, `IX_articles_score_filter` with WHERE filter, `IX_api_usage_created_covering` with INCLUDE; 3 `IF NOT EXISTS` guards; no DROP statements |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `FeedRSS/tmc-rss-collector/migrations/021_fulltext_search.sql` | Full-text catalog + index for Portuguese search | VERIFIED | Contains `CREATE FULLTEXT CATALOG ArticleCatalog AS DEFAULT`, `LANGUAGE 1046` on title/preview/tags, idempotent IF NOT EXISTS guards |
| `FeedRSS/tmc-rss-collector/migrations/022_cost_performance_indexes.sql` | 3 performance indexes | VERIFIED | IX_llm_usage_created (covering), IX_articles_score_filter (filtered WHERE is_deleted=0), IX_api_usage_created_covering (covering); all idempotent |
| `FeedRSS/tmc-rss-collector/services/database.py` | FREETEXT + LIKE fallback in _build_article_filters | VERIFIED | `_fulltext_available` module flag, `_has_fulltext_index()` method, FREETEXT branch at 522-526, LIKE fallback at 527-549, return signature unchanged at line 566 |
| `FeedRSS/tmc-rss-collector/services/cost_queries.py` | Direct UNIQUEIDENTIFIER JOIN | VERIFIED | Line 333: `LEFT JOIN users u ON l.user_id = u.id`; no CAST on JOIN; display CAST at line 325 preserved |
| `FeedRSS/tmc-rss-collector/functions/articles_api.py` | Time-only facet cache | VERIFIED | `_facet_cache` has 3 keys (categories, tags, timestamp); zero `filter_key` references; cache hit on TTL only |
| `tmc-redacao/src/components/ui/FilterBar.jsx` | 500ms search debounce | VERIFIED | Line 101: `}, 500);`; useCallback and clearTimeout cleanup intact |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `database.py _build_article_filters()` | `migrations/021_fulltext_search.sql` | `_has_fulltext_index()` queries `sys.fulltext_indexes` before using FREETEXT | WIRED | Method probes for the index at runtime; graceful LIKE fallback if catalog absent — code deploys safely before migration runs |
| `database.py _build_article_filters()` | `database.py get_articles()` | Returns `(where_clause, params, needs_scores_join)` tuple | WIRED | Return signature at line 566 unchanged; `get_articles()` caller unaffected |
| `cost_queries.py get_cost_by_user()` | Azure SQL `llm_usage_log` + `users` | Direct UNIQUEIDENTIFIER JOIN | WIRED | Both columns confirmed UNIQUEIDENTIFIER in migrations 005 + 017; optimizer can now use indexes on both sides |
| `articles_api.py list_articles_handler()` | `_facet_cache` dict | TTL-only cache hit check | WIRED | Cache hit check at lines 104-108 checks only `cache_age < FACET_CACHE_TTL` and `categories is not None` |
| `FilterBar.jsx debounce timer` | `RedacaoPage.jsx fetch debounce` | FilterBar dispatches `updateFilter` after 500ms; RedacaoPage coalesces with 150ms fetch debounce | WIRED | Combined effective delay ~650ms; AbortController in RedacaoPage at lines 77/157-163 verified present in 02-C-SUMMARY |

---

### Data-Flow Trace (Level 4)

Not applicable for migration files (DDL only). Backend Python files are service modules, not rendering components. FilterBar is a UI input component — data flows to `updateFilter` which updates FiltersContext state; RedacaoPage reads that state to trigger API calls. No hollow props or static returns detected.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All three backend modules import without errors | `py -c "from services.database import DatabaseService; from services.cost_queries import get_cost_by_user; from functions.articles_api import list_articles_handler; print('All imports OK')"` | `All imports OK` | PASS |
| Frontend build succeeds with no errors | `npm run build` | Built in 5.06s, 2554 modules transformed, 0 errors | PASS |
| 500ms debounce in FilterBar | `grep "}, 500)" FilterBar.jsx` | Line 101: `}, 500);` | PASS |
| No 300ms debounce remaining in handler | No match for `}, 300)` in FilterBar debounce block | Color class `*-300` matches only (unrelated to debounce) | PASS |
| filter_key fully removed from articles_api.py | `grep filter_key articles_api.py` | 0 matches | PASS |
| Direct UUID JOIN in cost_queries.py | `grep "l.user_id = u.id" cost_queries.py` | Line 333 matches | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| D-01 | 02-A-PLAN | Use FREETEXT (not CONTAINS) for general search | SATISFIED | `database.py:525` uses FREETEXT for `search` parameter |
| D-02 | 02-A-PLAN | ArticleCatalog with Language 1046 on title/preview/tags | SATISFIED | `021_fulltext_search.sql` lines 23-29 |
| D-03 | 02-A-PLAN | Migration file 021_fulltext_search.sql | SATISFIED | File exists and is complete |
| D-04 | 02-B-PLAN | Graceful fallback to LIKE when catalog absent | SATISFIED | `_has_fulltext_index()` returns False on failure; LIKE branch in else at lines 527-549 |
| D-05 | 02-B-PLAN | Replace 5 LIKE conditions with single FREETEXT | SATISFIED | Single `FREETEXT((a.title, a.preview, a.tags), %s)` at line 525 |
| D-06 | 02-B-PLAN | No COLLATE inside FREETEXT branch | SATISFIED | COLLATE only appears in the LIKE fallback `else` branch |
| D-07 | 02-A-PLAN | Migration file 022_cost_performance_indexes.sql | SATISFIED | File exists and is complete |
| D-08 | 02-A-PLAN | Covering index on llm_usage_log(created_at) | SATISFIED | IX_llm_usage_created with INCLUDE (model, task_type, input_tokens, output_tokens, input_cost_usd, output_cost_usd, user_id) |
| D-09 | 02-A-PLAN | Filtered index on collected_articles for score filter | SATISFIED | IX_articles_score_filter with WHERE is_deleted=0 AND total_score IS NOT NULL |
| D-10 | 02-A-PLAN | Covering index on api_usage_log (discretionary) | SATISFIED (with rename) | IX_api_usage_created_covering — renamed from plan spec to avoid silent conflict with basic IX_api_usage_created created by migration 018 |
| D-11 | 02-B-PLAN | Both columns are UNIQUEIDENTIFIER — CAST unnecessary | SATISFIED | Confirmed in migrations 005 (users.id) and 017 (llm_usage_log.user_id) |
| D-12 | 02-B-PLAN | Replace double CAST JOIN with direct comparison | SATISFIED | `cost_queries.py:333` `l.user_id = u.id` |
| D-13 | 02-B-PLAN | Identify cache keyed on filter combination | SATISFIED | Context only — no code change required |
| D-14 | 02-B-PLAN | Remove filter_key from cache invalidation | SATISFIED | 0 references to filter_key in articles_api.py |
| D-15 | 02-B-PLAN | Rationale: facet counts are approximate navigation aids | SATISFIED | TTL-only cache in place |
| D-16 | 02-B-PLAN | Remove filter_key from dict, check, storage, and logging | SATISFIED | All 4 edit locations removed per SUMMARY.md |
| D-17 | 02-C-PLAN | AbortController already present in RedacaoPage — verify only | SATISFIED | Confirmed in 02-C-SUMMARY lines 1-5: ref at 77, new controller at 157, signal passed to fetch |
| D-18 | 02-C-PLAN | Increase FilterBar debounce from 300ms to 500ms | SATISFIED | `FilterBar.jsx:101` `}, 500);` |
| D-19 | 02-C-PLAN | No additional dedup needed (apiCache.js handles it) | SATISFIED | No changes to apiCache.js; apiCache.js TTL dedup unaffected |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `021_fulltext_search.sql` | 15 | Comment notes DBA must verify PK name before running | Info | Not a blocker — the comment is an explicit pre-run checklist item; IF NOT EXISTS guard prevents double-creation if name differs |

No TODO/FIXME markers, no return null stubs, no hardcoded empty arrays, no placeholder implementations found in any of the 5 modified/created files.

---

### Human Verification Required

#### 1. FREETEXT search in production

**Test:** After running `python scripts/run_migrations.py` in production, go to the main feed (`/`), type "seleção brasileira" in the search box, and observe response time.
**Expected:** Results appear in under 2 seconds. Backend logs should show `[DatabaseService] Full-text index detected on collected_articles` on the first search, confirming FREETEXT routing is active.
**Why human:** Full-text catalog population takes variable time on Azure SQL depending on table size. The `_has_fulltext_index()` check will return False until the index is built, silently falling back to LIKE. Only a production run confirms the FREETEXT path activates and performs as expected.

#### 2. Score filter A / B / C / All response time

**Test:** On the main feed, click the score filter tabs: All, A, B, C in sequence. Observe the time between click and results appearing.
**Expected:** Each tab change produces results within 1 second. The IX_articles_score_filter index should be used for unclassified "All" queries.
**Why human:** Index effectiveness depends on Azure SQL query optimizer choosing the new index over the older IX_articles_score_order (migration 013). Only execution plan analysis on production data confirms the index is being used.

#### 3. Costs page load time

**Test:** Log in as a user with `manage_users` permission, navigate to `/configuracoes/custos`, measure time to first contentful chart render.
**Expected:** All 6 cost sections (overview, trends, breakdown, by-user, Exa, embeddings) render within 3 seconds of page load.
**Why human:** Speedup from IX_llm_usage_created is proportional to llm_usage_log row count. Only measurable in production with real data volume. Also requires `manage_users` permission which cannot be automated without credentials.

#### 4. Search input typing UX

**Test:** On the main feed, type a 5–10 character search term character by character at normal typing speed. Observe whether the UI remains responsive and how many API requests fire.
**Expected:** UI does not freeze or stutter. Network tab shows requests firing at most once per burst of typing (not on every keystroke). Previous in-flight requests are cancelled when a new character is typed.
**Why human:** Debounce timing and AbortController cancellation require interactive browser testing with DevTools network tab open. Static analysis confirms the code is correct but cannot simulate real typing cadence and network latency.

---

### Gaps Summary

No gaps. All 7 automated must-haves verified. The one plan deviation (IX_api_usage_created renamed to IX_api_usage_created_covering) is a documented, intentional auto-fix that improves correctness — the plan's acceptance criteria named an index that would have conflicted with migration 018. The implementation chose the correct unique name. Goal is fully achieved at the code level.

The 4 human verification items are performance outcomes that require production database state (migrations applied, data volume, query optimizer decisions) and cannot be measured through static analysis.

---

_Verified: 2026-04-01T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
