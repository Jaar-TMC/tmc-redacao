"""
Tests for Phase 2 Search/Filter Performance changes.

Covers:
- _has_fulltext_index() caching behaviour (True is sticky, False is rechecked)
- _build_article_filters() FREETEXT path (fulltext available)
- _build_article_filters() LIKE fallback (fulltext NOT available)
- Tag search with CONTAINS vs LIKE fallback
- Return signature of _build_article_filters (always 3-tuple)
- cost_queries.py JOIN uses l.user_id = u.id without extra CAST
- _facet_cache dict keys (no 'filter_key')
- FACET_CACHE_TTL constant value
"""

import sys
import os
import importlib
import unittest
from unittest.mock import MagicMock, patch, call
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Path setup — must resolve to the project root so relative imports work
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Prevent config module from crashing without real env vars
os.environ.setdefault("PRODUCTION_SAFETY_MODE", "false")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_service():
    """Return a DatabaseService instance whose __init__ does NOT connect."""
    # We patch the ConnectionPool so no real DB connection is attempted
    with patch("services.database.ConnectionPool"), \
         patch("services.database.pymssql"):
        from services.database import DatabaseService
        svc = DatabaseService.__new__(DatabaseService)
        # Minimal attributes that _build_article_filters / _has_fulltext_index need
        svc.pool = MagicMock()
        svc.logger = MagicMock()
        return svc


@contextmanager
def _cursor_returning(rows):
    """Context-manager factory that mimics DatabaseService.get_connection()."""
    cursor = MagicMock()
    cursor.fetchone.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cursor
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    yield cm, cursor


# ---------------------------------------------------------------------------
# Test 1: _has_fulltext_index() caching behaviour
# ---------------------------------------------------------------------------

class TestHasFulltextIndexCaching(unittest.TestCase):

    def setUp(self):
        # Reset the module-level global before every test
        import services.database as db_mod
        db_mod._fulltext_available = None

    def tearDown(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def test_returns_true_when_index_found(self):
        """When DB returns a row, method returns True and caches it."""
        svc = _make_db_service()

        mock_cm, mock_cursor = next(
            _cursor_returning((1,)).__enter__().__iter__()
        ) if False else (None, None)

        # Build proper CM mock
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        svc.get_connection = MagicMock(return_value=mock_ctx)

        result = svc._has_fulltext_index()

        self.assertTrue(result)

    def test_caches_true_no_second_query(self):
        """Once True is cached, a second call must NOT query the DB again."""
        svc = _make_db_service()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        svc.get_connection = MagicMock(return_value=mock_ctx)

        first = svc._has_fulltext_index()
        second = svc._has_fulltext_index()

        self.assertTrue(first)
        self.assertTrue(second)
        # get_connection called exactly once — second call hits the module cache
        self.assertEqual(svc.get_connection.call_count, 1)

    def test_returns_false_when_no_index(self):
        """When DB returns no row, method returns False."""
        svc = _make_db_service()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        svc.get_connection = MagicMock(return_value=mock_ctx)

        result = svc._has_fulltext_index()

        self.assertFalse(result)

    def test_false_is_not_cached_permanently(self):
        """False result must re-query on next call (index may still be building)."""
        import services.database as db_mod

        svc = _make_db_service()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        svc.get_connection = MagicMock(return_value=mock_ctx)

        first = svc._has_fulltext_index()
        self.assertFalse(first)

        # Reset global to None to simulate "False is not permanently cached"
        # (the real code stores False in _fulltext_available; since it is NOT True
        #  the guard `if _fulltext_available is True` does NOT short-circuit, so
        #  the method re-queries every time _fulltext_available is False / None)
        # Verify that calling again DOES issue another DB query
        second = svc._has_fulltext_index()
        self.assertFalse(second)
        self.assertEqual(svc.get_connection.call_count, 2,
                         "False result must re-query the DB on each subsequent call")


# ---------------------------------------------------------------------------
# Test 2: _build_article_filters — FREETEXT path (fulltext available)
# ---------------------------------------------------------------------------

class TestBuildArticleFiltersFreetextPath(unittest.TestCase):

    def setUp(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def tearDown(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def test_freetext_used_when_fulltext_available(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=True)

        where, params, needs_join = svc._build_article_filters(search="seleção brasileira")

        self.assertIn("FREETEXT", where)
        self.assertIn("a.title", where)
        self.assertIn("a.preview", where)
        self.assertIn("a.tags", where)
        self.assertIn("seleção brasileira", params)

    def test_no_collate_in_freetext_path(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=True)

        where, params, _ = svc._build_article_filters(search="copa do mundo")

        self.assertNotIn("COLLATE", where)

    def test_no_like_in_freetext_path(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=True)

        where, params, _ = svc._build_article_filters(search="eleições 2026")

        self.assertNotIn("LIKE", where)

    def test_return_is_three_tuple(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=True)

        result = svc._build_article_filters(search="test")

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], str)   # where_clause
        self.assertIsInstance(result[1], list)  # params
        self.assertIsInstance(result[2], bool)  # needs_scores_join


# ---------------------------------------------------------------------------
# Test 3: _build_article_filters — LIKE fallback (fulltext NOT available)
# ---------------------------------------------------------------------------

class TestBuildArticleFiltersLikeFallback(unittest.TestCase):

    def setUp(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def tearDown(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def test_like_used_when_fulltext_unavailable(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=False)

        where, params, _ = svc._build_article_filters(search="seleção brasileira")

        self.assertIn("LIKE", where)
        self.assertIn("COLLATE Latin1_General_CI_AI", where)

    def test_no_freetext_in_like_fallback(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=False)

        where, params, _ = svc._build_article_filters(search="economia brasileira")

        self.assertNotIn("FREETEXT", where)


# ---------------------------------------------------------------------------
# Test 4: Tag search uses CONTAINS when fulltext is available
# ---------------------------------------------------------------------------

class TestTagSearchContains(unittest.TestCase):

    def setUp(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def tearDown(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def test_contains_used_for_tag_when_fulltext_available(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=True)

        where, params, _ = svc._build_article_filters(tag="política")

        self.assertIn("CONTAINS", where)
        self.assertIn("a.tags", where)

    def test_tag_double_quoted_for_exact_match(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=True)

        where, params, _ = svc._build_article_filters(tag="política")

        # CONTAINS requires double-quoted literal for exact phrase match
        self.assertIn('"política"', params)

    def test_no_like_in_contains_tag_path(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=True)

        where, params, _ = svc._build_article_filters(tag="esporte")

        self.assertNotIn("LIKE", where)


# ---------------------------------------------------------------------------
# Test 5: Tag search uses LIKE fallback when fulltext NOT available
# ---------------------------------------------------------------------------

class TestTagSearchLikeFallback(unittest.TestCase):

    def setUp(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def tearDown(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def test_like_used_for_tag_when_fulltext_unavailable(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=False)

        where, params, _ = svc._build_article_filters(tag="política")

        self.assertIn("LIKE", where)

    def test_no_contains_in_tag_like_fallback(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=False)

        where, params, _ = svc._build_article_filters(tag="política")

        self.assertNotIn("CONTAINS", where)


# ---------------------------------------------------------------------------
# Test 6: _build_article_filters return signature is always (str, list, bool)
# ---------------------------------------------------------------------------

class TestBuildArticleFiltersReturnSignature(unittest.TestCase):

    def setUp(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def tearDown(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def _assert_signature(self, result):
        self.assertIsInstance(result, tuple, "Must return a tuple")
        self.assertEqual(len(result), 3, "Must be a 3-tuple")
        where, params, needs_join = result
        self.assertIsInstance(where, str, "where_clause must be str")
        self.assertIsInstance(params, list, "params must be list")
        self.assertIsInstance(needs_join, bool, "needs_scores_join must be bool")

    def test_no_filters(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=False)
        self._assert_signature(svc._build_article_filters())

    def test_search_only(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=True)
        self._assert_signature(svc._build_article_filters(search="test"))

    def test_tag_only(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=False)
        self._assert_signature(svc._build_article_filters(tag="política"))

    def test_classification_only(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=False)
        self._assert_signature(svc._build_article_filters(classification="A"))

    def test_category_only(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=False)
        self._assert_signature(svc._build_article_filters(category="esporte"))

    def test_period_only(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=False)
        self._assert_signature(svc._build_article_filters(period="today"))

    def test_all_filters(self):
        svc = _make_db_service()
        svc._has_fulltext_index = MagicMock(return_value=True)
        self._assert_signature(svc._build_article_filters(
            search="seleção",
            tag="futebol",
            classification="A",
            category="esporte",
            period="week",
        ))


# ---------------------------------------------------------------------------
# Test 7: cost_queries.py — JOIN line has no extra CAST, SELECT keeps display CAST
# ---------------------------------------------------------------------------

class TestCostQueriesJoin(unittest.TestCase):

    def test_join_uses_direct_equality_no_cast(self):
        """Line 333 must use l.user_id = u.id without wrapping either side in CAST."""
        cost_queries_path = os.path.join(
            os.path.dirname(__file__), "..", "services", "cost_queries.py"
        )
        with open(cost_queries_path, "r", encoding="utf-8") as f:
            source = f.read()

        # The fixed JOIN line
        self.assertIn(
            "LEFT JOIN users u ON l.user_id = u.id",
            source,
            "JOIN must use l.user_id = u.id (no CAST on either side)",
        )

    def test_select_still_has_display_cast(self):
        """The SELECT still uses CAST(l.user_id AS VARCHAR(36)) for the uid display column."""
        cost_queries_path = os.path.join(
            os.path.dirname(__file__), "..", "services", "cost_queries.py"
        )
        with open(cost_queries_path, "r", encoding="utf-8") as f:
            source = f.read()

        # The display CAST (inside ISNULL) must still be present in the SELECT list
        self.assertIn(
            "CAST(l.user_id AS VARCHAR(36))",
            source,
            "SELECT must still include CAST(l.user_id AS VARCHAR(36)) for display",
        )

    def test_no_cast_on_join_rhs(self):
        """Confirm there is no CAST wrapping u.id on the JOIN right-hand side."""
        cost_queries_path = os.path.join(
            os.path.dirname(__file__), "..", "services", "cost_queries.py"
        )
        with open(cost_queries_path, "r", encoding="utf-8") as f:
            source = f.read()

        # The old broken form that was removed
        self.assertNotIn(
            "ON CAST(l.user_id AS VARCHAR(36)) = u.id",
            source,
            "Old CAST-on-JOIN pattern must not be present",
        )


# ---------------------------------------------------------------------------
# Test 8: _facet_cache dict has no 'filter_key'
# ---------------------------------------------------------------------------

class TestFacetCacheKeys(unittest.TestCase):

    def test_no_filter_key_in_facet_cache(self):
        """_facet_cache must NOT contain a 'filter_key' entry."""
        # Import fresh to get the module-level dict
        import importlib
        import functions.articles_api as api_mod
        importlib.reload(api_mod)  # ensure we read the current source state

        self.assertNotIn(
            "filter_key",
            api_mod._facet_cache,
            "_facet_cache must not contain 'filter_key'",
        )

    def test_facet_cache_has_required_keys(self):
        """_facet_cache must have exactly: 'categories', 'tags', 'timestamp'."""
        import importlib
        import functions.articles_api as api_mod
        importlib.reload(api_mod)

        expected_keys = {"categories", "tags", "timestamp"}
        actual_keys = set(api_mod._facet_cache.keys())
        self.assertEqual(
            actual_keys,
            expected_keys,
            f"_facet_cache keys mismatch. Got: {actual_keys}",
        )


# ---------------------------------------------------------------------------
# Test 9: FACET_CACHE_TTL is 300
# ---------------------------------------------------------------------------

class TestFacetCacheTTL(unittest.TestCase):

    def test_facet_cache_ttl_is_300(self):
        """FACET_CACHE_TTL must be 300 seconds (5 minutes)."""
        import importlib
        import functions.articles_api as api_mod
        importlib.reload(api_mod)

        self.assertEqual(
            api_mod.FACET_CACHE_TTL,
            300,
            f"FACET_CACHE_TTL should be 300, got {api_mod.FACET_CACHE_TTL}",
        )


if __name__ == "__main__":
    unittest.main()
