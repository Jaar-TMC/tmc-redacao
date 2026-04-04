---
phase: 9
slug: keyset-pagination
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing in `FeedRSS/tmc-rss-collector/tests/`) |
| **Config file** | none — pytest auto-discovers |
| **Quick run command** | `cd FeedRSS/tmc-rss-collector && pytest tests/test_keyset_pagination.py -x` |
| **Full suite command** | `cd FeedRSS/tmc-rss-collector && pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd FeedRSS/tmc-rss-collector && pytest tests/test_keyset_pagination.py -x`
- **After every plan wave:** Run `cd FeedRSS/tmc-rss-collector && pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-A-01 | A | 1 | PAG-01 | unit | `pytest tests/test_keyset_pagination.py::test_cursor_decode -x` | ❌ W0 | ⬜ pending |
| 09-A-02 | A | 1 | PAG-01 | unit | `pytest tests/test_keyset_pagination.py::test_invalid_cursor_fallback -x` | ❌ W0 | ⬜ pending |
| 09-A-03 | A | 1 | PAG-02 | unit | `pytest tests/test_keyset_pagination.py::test_seek_predicate_added -x` | ❌ W0 | ⬜ pending |
| 09-A-04 | A | 1 | PAG-02 | unit | `pytest tests/test_keyset_pagination.py::test_no_offset_in_cursor_mode -x` | ❌ W0 | ⬜ pending |
| 09-A-05 | A | 1 | PAG-02 | integration | `pytest tests/test_keyset_pagination.py::test_no_duplicates -x` | ❌ W0 | ⬜ pending |
| 09-A-06 | A | 1 | PAG-03 | unit | `pytest tests/test_keyset_pagination.py::test_score_order_offset_fallback -x` | ❌ W0 | ⬜ pending |
| 09-B-01 | B | 1 | PAG-04 | unit | `pytest tests/test_keyset_pagination.py::test_next_cursor_encoding -x` | ❌ W0 | ⬜ pending |
| 09-B-02 | B | 1 | PAG-04 | unit | `pytest tests/test_keyset_pagination.py::test_prev_cursor_encoding -x` | ❌ W0 | ⬜ pending |
| 09-B-03 | B | 1 | PAG-04 | unit | `pytest tests/test_keyset_pagination.py::test_backward_seek_order -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `FeedRSS/tmc-rss-collector/tests/test_keyset_pagination.py` — stubs for PAG-01 through PAG-04 (entire test file is new)

*Existing infrastructure covers all other needs: conftest.py, pytest discovery, existing test files for other phases — all reusable. No new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Page 50 loads in <10ms (same as page 1) | PAG-02 | Requires live DB with real data volume | Deploy to staging, navigate to page 50 with cursor, measure response time in browser DevTools Network tab |
| No visible UX change to pagination buttons | PAG-04 | Visual verification | Verify Pagination component renders same page number buttons; cursor usage is invisible to user |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
