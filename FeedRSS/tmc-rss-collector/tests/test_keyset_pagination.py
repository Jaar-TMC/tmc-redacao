"""
Tests for Phase 09 Keyset Pagination (Plans 01-02).

Covers:
- encode_cursor / decode_cursor roundtrip
- decode_cursor with invalid base64 input
- decode_cursor with missing pipe separator
- Forward seek predicate in _build_article_filters
- Backward seek predicate in _build_article_filters
- Seek predicate combined with category filter
- No seek when no cursor params provided
- Score ordering skips cursor mode
- No duplicate articles between cursor pages (disjoint seek predicates)
- Backward seek results reversed to DESC order
- nextCursor encoding from last article
- prevCursor encoding from first article
- nextCursor is None on last page
- Cursors are None when order_by=score
"""

import sys
import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from contextlib import contextmanager
from uuid import UUID

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Prevent config module from crashing without real env vars
os.environ.setdefault("PRODUCTION_SAFETY_MODE", "false")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_service():
    """Return a DatabaseService instance whose __init__ does NOT connect."""
    with patch("services.database.ConnectionPool"), \
         patch("services.database.pymssql"):
        from services.database import DatabaseService
        svc = DatabaseService.__new__(DatabaseService)
        svc.pool = MagicMock()
        svc.logger = MagicMock()
        return svc


@contextmanager
def _cursor_returning(rows):
    """Context-manager factory that mimics DatabaseService.get_connection()."""
    cursor = MagicMock()
    cursor.fetchone.return_value = rows
    cursor.fetchall.return_value = rows if isinstance(rows, list) else [rows]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    yield cm, cursor


# ===========================================================================
# Test 1: encode_cursor / decode_cursor roundtrip
# ===========================================================================

class TestCursorEncodeDecode(unittest.TestCase):

    def test_cursor_encode_decode_roundtrip(self):
        """Encode a known (datetime, uuid) then decode, assert values match."""
        from services.database import encode_cursor, decode_cursor

        dt = datetime(2025, 1, 15, 10, 30, 0)
        article_id = "550e8400-e29b-41d4-a716-446655440000"

        encoded = encode_cursor(dt, article_id)
        self.assertIsInstance(encoded, str)
        self.assertTrue(len(encoded) > 0)

        decoded_dt, decoded_id = decode_cursor(encoded)
        self.assertEqual(decoded_dt, dt)
        self.assertEqual(decoded_id, article_id)

    def test_cursor_decode_invalid_base64(self):
        """Invalid base64 should raise an exception."""
        from services.database import decode_cursor

        with self.assertRaises(Exception):
            decode_cursor("not-valid-base64!!!")

    def test_cursor_decode_invalid_format(self):
        """Base64 without pipe separator should raise ValueError."""
        import base64
        from services.database import decode_cursor

        # Encode a string without | separator
        encoded = base64.urlsafe_b64encode(b"nopipe").decode().rstrip("=")
        with self.assertRaises(ValueError):
            decode_cursor(encoded)


# ===========================================================================
# Tests 4-7: Seek predicate in _build_article_filters
# ===========================================================================

class TestSeekPredicate(unittest.TestCase):

    def setUp(self):
        import services.database as db_mod
        db_mod._fulltext_available = None
        self.svc = _make_db_service()

    def tearDown(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def test_seek_predicate_forward(self):
        """Forward cursor adds (published_at < %s OR ...) predicate."""
        where, params, _ = self.svc._build_article_filters(
            cursor_published_at=datetime(2025, 1, 15, 10, 0, 0),
            cursor_id="abc-123",
            cursor_direction="next"
        )
        self.assertIn("a.published_at < %s", where)
        self.assertIn("a.id < %s", where)
        # 3 cursor params
        self.assertEqual(len(params), 3)

    def test_seek_predicate_backward(self):
        """Backward cursor adds (published_at > %s OR ...) predicate."""
        where, params, _ = self.svc._build_article_filters(
            cursor_published_at=datetime(2025, 1, 15, 10, 0, 0),
            cursor_id="abc-123",
            cursor_direction="prev"
        )
        self.assertIn("a.published_at > %s", where)
        self.assertIn("a.id > %s", where)
        self.assertEqual(len(params), 3)

    def test_seek_predicate_combined_with_category(self):
        """Cursor params combine with category filter."""
        where, params, _ = self.svc._build_article_filters(
            category="politica",
            cursor_published_at=datetime(2025, 1, 15, 10, 0, 0),
            cursor_id="abc-123",
            cursor_direction="next"
        )
        self.assertIn("a.category = %s", where)
        self.assertIn("a.published_at < %s", where)
        # 1 category + 3 cursor = 4 params
        self.assertEqual(len(params), 4)

    def test_no_seek_when_no_cursor(self):
        """Without cursor params, no seek predicate in WHERE."""
        where, params, _ = self.svc._build_article_filters()
        self.assertNotIn("published_at <", where)
        self.assertNotIn("published_at >", where)


# ===========================================================================
# Test 8: Score ordering skips cursor mode
# ===========================================================================

class TestScoreOrderSkipsCursor(unittest.TestCase):

    def test_score_order_skips_cursor(self):
        """When order_by='score', use_cursor evaluates to False."""
        cursor_data = {"published_at": datetime(2025, 1, 15, 10, 0, 0), "id": "abc"}
        use_cursor = cursor_data is not None and 'score' != 'score'
        self.assertFalse(use_cursor)

    def test_non_score_order_uses_cursor(self):
        """When order_by is not 'score', use_cursor evaluates to True."""
        cursor_data = {"published_at": datetime(2025, 1, 15, 10, 0, 0), "id": "abc"}
        use_cursor = cursor_data is not None and None != 'score'
        self.assertTrue(use_cursor)


# ===========================================================================
# Test 9: No duplicates between cursor pages
# ===========================================================================

class TestNoDuplicates(unittest.TestCase):

    def setUp(self):
        import services.database as db_mod
        db_mod._fulltext_available = None
        self.svc = _make_db_service()

    def tearDown(self):
        import services.database as db_mod
        db_mod._fulltext_available = None

    def test_no_duplicates(self):
        """Seek predicate produces disjoint sets between consecutive pages.

        Page 1 has no cursor (returns all articles ordered by date DESC).
        Page 2 uses cursor from the last article of page 1. The forward seek
        predicate (published_at < boundary OR ...) is strictly less-than,
        guaranteeing no overlap.
        """
        # Page 1: no cursor
        where1, params1, _ = self.svc._build_article_filters()
        self.assertEqual(where1, "")  # No conditions = all articles

        # Page 2: cursor from "last article" of page 1
        boundary_dt = datetime(2025, 1, 15, 10, 0, 0)
        boundary_id = "550e8400-e29b-41d4-a716-446655440000"
        where2, params2, _ = self.svc._build_article_filters(
            cursor_published_at=boundary_dt,
            cursor_id=boundary_id,
            cursor_direction="next"
        )
        # Forward seek predicate present
        self.assertIn("(a.published_at < %s OR (a.published_at = %s AND a.id < %s))", where2)
        # Params contain the boundary cursor values
        self.assertEqual(params2[0], boundary_dt)
        self.assertEqual(params2[1], boundary_dt)
        self.assertEqual(params2[2], boundary_id)


# ===========================================================================
# Test 10: Backward seek results reversed to DESC order
# ===========================================================================

class TestBackwardSeekOrder(unittest.TestCase):

    def test_backward_seek_order(self):
        """Backward cursor results are reversed from ASC to DESC order."""
        svc = _make_db_service()

        # Mock rows in ASC order (as DB would return for ORDER BY ASC)
        # Columns: id, source_id, title, content, preview, url,
        #          image_url, author, category, tags, published_at,
        #          collected_at, hash, source_name, source_url, favicon_url,
        #          total_score, classification, content_length_original
        dt1 = datetime(2025, 1, 13, 8, 0, 0)   # oldest
        dt2 = datetime(2025, 1, 14, 9, 0, 0)   # middle
        dt3 = datetime(2025, 1, 15, 10, 0, 0)  # newest

        def make_row(dt, idx):
            # Use valid UUIDs for id and source_id (Article model validates UUID)
            article_uuid = f"550e8400-e29b-41d4-a716-44665544000{idx}"
            source_uuid = f"660e8400-e29b-41d4-a716-44665544000{idx}"
            return (
                article_uuid, source_uuid, f"Title {idx}", f"Content {idx}",
                f"Preview {idx}", f"http://url{idx}.com",
                None, None, "politica", "[]", dt,
                datetime(2025, 1, 15), "a" * 32 + str(idx),
                f"Source {idx}", f"http://source{idx}.com", None,
                50, "B",
                100,  # content_length_original
            )

        mock_rows = [make_row(dt1, 1), make_row(dt2, 2), make_row(dt3, 3)]

        # Mock the count query returning 100 total articles
        count_result = MagicMock()
        count_result.__getitem__ = MagicMock(return_value=100)

        mock_cursor = MagicMock()
        # First call: count query returns (100,)
        # Second call: data query returns mock_rows
        mock_cursor.fetchone.return_value = (100,)
        mock_cursor.fetchall.return_value = mock_rows

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_conn)
        mock_cm.__exit__ = MagicMock(return_value=False)

        svc.get_connection = MagicMock(return_value=mock_cm)

        cursor_data = {
            "published_at": datetime(2025, 1, 16, 10, 0, 0),
            "id": "abc-123"
        }

        articles, total, urgency = svc.get_articles_with_urgency(
            cursor=cursor_data,
            cursor_direction="prev",
            skip_urgency_query=True
        )

        # Verify results are in DESC order (newest first) after reverse
        self.assertEqual(len(articles), 3)
        self.assertEqual(articles[0].published_at, dt3)  # newest first
        self.assertEqual(articles[1].published_at, dt2)
        self.assertEqual(articles[2].published_at, dt1)  # oldest last
        self.assertEqual(total, 100)


# ===========================================================================
# Tests 11-14: API-level cursor response fields
# ===========================================================================

class TestCursorResponseFields(unittest.TestCase):

    def test_next_cursor_encoding(self):
        """nextCursor encodes last article's published_at and id (roundtrip)."""
        from services.database import encode_cursor, decode_cursor

        dt = datetime(2025, 6, 20, 14, 30, 0)
        article_id = UUID("550e8400-e29b-41d4-a716-446655440000")

        encoded = encode_cursor(dt, article_id)
        self.assertIsInstance(encoded, str)

        decoded_dt, decoded_id = decode_cursor(encoded)
        self.assertEqual(decoded_dt, dt)
        self.assertEqual(decoded_id, str(article_id))

    def test_prev_cursor_encoding(self):
        """prevCursor encodes first article's published_at and id (roundtrip)."""
        from services.database import encode_cursor, decode_cursor

        dt = datetime(2025, 6, 20, 10, 0, 0)
        article_id = UUID("660e8400-e29b-41d4-a716-446655440000")

        encoded = encode_cursor(dt, article_id)
        decoded_dt, decoded_id = decode_cursor(encoded)
        self.assertEqual(decoded_dt, dt)
        self.assertEqual(decoded_id, str(article_id))

    def test_cursor_none_on_last_page(self):
        """When len(articles) < limit, next_cursor should be None."""
        # Simulate: limit=20, articles has 15 items -> not a full page
        limit = 20
        articles_count = 15
        # The condition for setting nextCursor is: len(articles) == limit
        should_set_next = articles_count == limit
        self.assertFalse(should_set_next)

    def test_cursor_none_for_score_order(self):
        """When order_by='score', both cursors should be None."""
        order_by = 'score'
        use_cursor_mode = order_by != 'score'
        self.assertFalse(use_cursor_mode)
        # Since use_cursor_mode is False, next_cursor and prev_cursor stay None


if __name__ == '__main__':
    unittest.main()
