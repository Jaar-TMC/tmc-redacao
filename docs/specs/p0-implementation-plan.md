# P0 Critical Issues - Implementation Plan

> Generated 2026-03-13 from deep codebase analysis by 3 specialized agents + manual review.
> Updated with critical agent findings (stale test mocks, auth middleware blocking, CI concurrency).
> Goal: Fix all 3 P0 issues WITHOUT breaking the running application.

---

## CRITICAL FINDINGS FROM AGENT ANALYSIS

### BUG FOUND — Existing Safety Gate Tests Are Broken (P0-2)
`test_generation_api.py:129` uses `@patch("functions.generation_api.PRODUCTION_SAFETY_MODE", True)` but this module-level constant **no longer exists**. The function now reads from `_get_production_safety_mode()` → `get_config().production_safety_mode`. This means the "production mode" test is **silently running in legacy mode** — it passes but tests the wrong behavior. Must fix before writing new tests.

### HIDDEN BLOCKER — Auth Middleware Blocks Event Loop (P0-1)
`utils/auth.py:get_current_user()` is a **synchronous function** that calls `db.is_token_blacklisted(jti)` on **every single authenticated request**. This blocks the event loop before the handler even runs. This must be addressed as part of P0-1 or the async DB work is incomplete.

### CI RACE CONDITION — Need Concurrency Control (P0-3)
If two pushes to `main` with `FeedRSS/` changes happen quickly, two deploy workflows race. Must add `concurrency` group with `cancel-in-progress: true`.

---

## P0-1: Wrap Synchronous DB Calls with `asyncio.to_thread()`

### Problem Analysis

All 17 handler files use `async def` but call `get_db().*` synchronously. pymssql is 100% blocking — every DB call blocks the Azure Functions event loop. Under concurrent HTTP load, requests serialize.

**Current pattern** (every handler):
```python
async def list_articles_handler(req):
    db = get_db()
    articles, total, urgency = db.get_articles_with_urgency(...)  # BLOCKS event loop
```

**Existing async usage** (already partially done in 3 places):
- `generation_api.py:1882` — `await asyncio.to_thread(db.insert_generation_audit, ...)`
- `generation_api.py:1911` — `await asyncio.to_thread(results, count, _ = ...)`
- `youtube_service.py:464` — `await asyncio.to_thread(...)`
- `embedding_service.py:337,388` — `loop.run_in_executor(None, ...)`
- `fact_check_service.py:1193,1197` — `asyncio.to_thread(...)`
- `llm_service.py:2032,2065,2127` — `run_in_executor(None, ...)` for fire-and-forget logging

### Thread Safety Analysis

**pymssql connections**: NOT thread-safe. Each thread must use its own connection.

**ConnectionPool**: Already thread-safe (uses `threading.Lock` + `queue.Queue`). The `get_connection()` / `return_connection()` cycle is safe across threads because:
- `queue.Queue` is thread-safe
- `_lock` protects `_current_size` counter
- Each `get_connection()` returns a unique connection object

**DatabaseService singleton**: `get_db()` uses `threading.Lock` for creation. The singleton itself is safe. Methods call `self.pool.get_connection()` which hands out separate connections per call.

**Conclusion**: `asyncio.to_thread(db.method, args)` is safe because each call to `db.method` internally does `pool.get_connection()` which gives it a dedicated connection.

### Implementation Strategy

**Approach**: Create a thin async wrapper utility. Apply incrementally per handler file.

#### Step 1: Create `utils/async_db.py`

```python
"""
Async wrapper for synchronous DatabaseService calls.

pymssql is blocking; this module wraps DB calls with asyncio.to_thread()
so async handlers don't block the Azure Functions event loop.

Thread safety: ConnectionPool.get_connection() returns a dedicated connection
per call, so concurrent threads never share a connection object.
"""

import asyncio
from functools import wraps
from typing import TypeVar, Callable, Any

T = TypeVar('T')


async def run_db(func: Callable[..., T], *args, **kwargs) -> T:
    """Run a synchronous DB function in a thread pool.

    Usage:
        articles, total = await run_db(db.get_articles, page=1, limit=20)
    """
    return await asyncio.to_thread(func, *args, **kwargs)
```

#### Step 1.5: Fix Auth Middleware (CRITICAL — blocks EVERY request)

`utils/auth.py:get_current_user()` is synchronous and calls `db.is_token_blacklisted(jti)` on every authenticated request. The `require_auth` decorator wrapper is already `async def`, so we can make `get_current_user` async:

**Current** (`utils/auth.py:20-55`):
```python
def get_current_user(req: func.HttpRequest) -> Optional[dict]:  # sync!
    # ...
    db = get_db()
    if db.is_token_blacklisted(jti):  # BLOCKS event loop on EVERY request
        return None
```

**After**:
```python
async def get_current_user(req: func.HttpRequest) -> Optional[dict]:
    # ...
    db = get_db()
    if await asyncio.to_thread(db.is_token_blacklisted, jti):
        return None
```

**Cascade changes**:
- `require_auth` wrapper (line 66): `user = get_current_user(req)` → `user = await get_current_user(req)`
- `require_admin` wrapper: same change
- `function_app.py`: ~9 inline calls to `get_current_user(req)` must become `await get_current_user(req)` (all already inside `async def` handlers, so this is safe)

**Do this BEFORE migrating any handler files** — it's the single highest-frequency blocking call.

#### Step 2: Migrate Handlers (Order by Risk — Low Risk First)

| Priority | File | Handlers | DB Calls | Risk |
|----------|------|----------|----------|------|
| 1 | `health.py` | 2 | 4 | Lowest (read-only, no auth) |
| 2 | `articles_api.py` | 5 | 5 | Low (read-only) |
| 3 | `themes_api.py` | 3 | 4 | Low (read-only) |
| 4 | `sources_api.py` | 6 | 6 | Medium (CRUD) |
| 5 | `user_articles_api.py` | 5 | 5 | Medium (CRUD) |
| 6 | `auth_api.py` | 10 | 10 | Medium (auth-sensitive) |
| 7 | `generation_api.py` | 5 | ~8 | High (already partially migrated, complex) |
| 8 | `fact_check_scan_api.py` | 2 | ~3 | Medium |
| 9 | `edit_api.py` | 1 | ~2 | Medium |
| 10 | `research_api.py` | 1 | ~1 | Low |
| 11 | `transcription_api.py` | 1 | ~1 | Low |

**Timer Triggers** (separate batch — different concurrency model):

| File | Handler | Notes |
|------|---------|-------|
| `rss_collector.py` | 1 timer + 1 helper | Heavy — many DB calls in loop |
| `embedding_generator.py` | 1 timer | Already uses run_in_executor for some ops |
| `scoring_calculator.py` | 1 timer | Calls scoring_service which has own async |
| `clustering_engine.py` | 1 timer | Uses clustering_service |
| `clustering_maintenance.py` | 1 timer + 1 manual | Complex maintenance ops |

#### Step 3: Migration Pattern Per Handler

**Before:**
```python
async def list_articles_handler(req):
    db = get_db()
    articles, total, urgency = db.get_articles_with_urgency(page=page, limit=limit)
```

**After:**
```python
from utils.async_db import run_db

async def list_articles_handler(req):
    db = get_db()
    articles, total, urgency = await run_db(
        db.get_articles_with_urgency, page=page, limit=limit
    )
```

#### Step 3.5: Handle Raw SQL Context Managers (themes_api.py)

`themes_api.py` and `clustering_maintenance.py` use `with db.get_connection() as conn:` with multiple cursor operations. These can't be wrapped line-by-line. Instead, extract the entire block into a synchronous helper function:

```python
# Before (in list_themes_handler):
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(stats_query)
    stats_rows = cursor.fetchall()
    # ... more cursor operations ...

# After:
def _fetch_themes_data(db, params, offset, limit):
    """Synchronous helper — all raw SQL stays here."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        # ... all cursor operations ...
    return items, stats, total

items, stats, total = await run_db(_fetch_themes_data, db, params, offset, limit)
```

#### Step 4: Connection Pool Sizing

Current: `max_size=10` (default in ConnectionPool.__init__)

With `asyncio.to_thread()`, concurrent requests will actually run DB queries in parallel. Need to ensure pool can handle it.

**Recommendation**: Increase to `max_size=20` to match Azure Functions `maxConcurrentRequests: 50` (not all requests hit DB).

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Pool exhaustion under burst load | Increase pool size to 20; add warning log when pool is >80% used |
| Exception handling changes | `asyncio.to_thread` propagates exceptions normally — no change needed |
| Timer triggers running in thread context | Timer triggers already run in the event loop; wrapping their DB calls is the same pattern as HTTP handlers |
| `nest_asyncio` usage in 4 services | These are in service-level code that calls `asyncio.run()` from sync context. `asyncio.to_thread()` in handlers is a separate concern — no conflict |
| Rollback difficulty | Each file is independent — can revert one file at a time by removing `await run_db()` wrapper |

### Testing Plan

1. After migrating `health.py`: Hit `GET /api/health` — verify response unchanged
2. After migrating `articles_api.py`: Hit `GET /api/articles` — verify pagination, filters, facets
3. Load test with 10 concurrent requests to confirm parallelism works
4. Monitor Connection Pool stats in Application Insights

### Estimated Effort: 3-4 hours

---

## P0-2: Unit Tests for Safety Gates & Scoring Logic

### Code Analysis

#### `evaluate_safety_gates()` — Location: `generation_api.py:237-411`

**Signature:**
```python
def evaluate_safety_gates(
    verification_data: dict,
    content_length: int,
    effective_source_len: int,
    prior_human_review: bool = False,
    prior_review_reasons: list = None,
) -> SafetyDecision
```

**Returns:** `SafetyDecision(publish_blocked, block_reasons, human_review_required, review_reasons)`

**Pure function**: Yes — no DB calls, no side effects. Only dependency: `get_config()` for thresholds.

**Branching Conditions Cataloged (18 total):**

| # | Condition | Type | Mode |
|---|-----------|------|------|
| 1 | `risk_level == "critical"` | HARD BLOCK | Both |
| 2 | `PRODUCTION_SAFETY_MODE and risk_level == "high"` | HARD BLOCK | Production |
| 3 | `confidence_score < confidence_floor and is_verified` | HARD BLOCK | Both (floor differs: 0.50 prod, 0.40 legacy) |
| 4 | `confidence_score < publish_confidence_floor` (prod + verified) | HARD BLOCK | Production |
| 5 | `grounded_ratio < publish_grounded_floor` (prod + verified) | HARD BLOCK | Production |
| 6 | `fabricated_claims >= 2` (production) | HARD BLOCK | Production |
| 7 | `fabricated_claims == 1 and confidence < 0.50` (production) | HARD BLOCK | Production |
| 8 | `fabricated_claims >= 3` (legacy) | HARD BLOCK | Legacy |
| 9 | `fabricated_claims == 2 and confidence < 0.40` (legacy) | HARD BLOCK | Legacy |
| 10 | `unverifiable >= 3 and unverifiable/total > 0.40` | HARD BLOCK | Both |
| 11 | `effective_expansion > expansion_hard_limit` (8.0 prod, 15 legacy) | HARD BLOCK | Both |
| 12 | `fabricated_claims == 1 and confidence >= 0.50` (prod, not blocked) | SOFT REVIEW | Production |
| 13 | `fabricated_claims == 2 and confidence >= 0.40` (legacy, not blocked) | SOFT REVIEW | Legacy |
| 14 | `unverifiable >= 2 and unverifiable/total > 0.30` | SOFT REVIEW | Both |
| 15 | `novel_entities >= 4 and novel_ratio > 0.60 and confidence < 0.80` | SOFT REVIEW | Both |
| 16 | `10 < effective_expansion <= 15` (legacy) | SOFT REVIEW | Legacy |
| 17 | `risk_level == "high" and not blocked` (legacy) | SOFT REVIEW | Legacy |
| 18 | Prior review carry-forward | CARRY | Both |

**Special computation:**
- `effective_grounded = grounded_claims + (context_claims * 0.8)`
- `grounded_ratio = effective_grounded / total_claims` (0.0 if total=0)
- `effective_expansion = content_length / effective_source_len` (fallback to expansion_ratio if source=0)

#### `evaluate_quality_criteria()` — Location: `generation_api.py:414-547`

**Signature:**
```python
def evaluate_quality_criteria(
    verification_data: dict,
    readability_data: dict,
    categoria: str = "",
    tipo_materia: str = "",
) -> dict  # {all_passed: bool, failures: list}
```

**Pure function**: Yes.

**7 criteria:** fabrication, readability (Flesch), confidence, novel entities, unverifiable claims, risk level (prod only), bold count (removed).

#### `ScoringService._calculate_scores()` — Location: `scoring_service.py:316-347`

**Pure method** (no DB, no LLM):
```python
def _calculate_scores(self, signals: Dict[str, str]) -> Tuple[Dict[str, int], int, str]
```

**Scoring maps:**
- inesperado: yes=25, partial=12, no=0
- impacto: high=30, medium=15, low=0
- busca_agora: yes=25, maybe=12, no=0
- conversa: yes=20, maybe=10, no=0
- Classification: A >= 75, B >= 35, C < 35

#### `_heuristic_score_article()` — Location: `scoring_service.py:213-259`

**Pure function**: Yes. Keyword-based fallback scoring.

### Existing Test Infrastructure

- **conftest.py**: Already has `_reset_config_singleton`, `sample_verification_data`, `mock_llm_service` fixtures
- **Existing tests**: `test_fact_check_improvements.py`, `test_quality_loop.py`, `test_generation_api.py`, `test_llm_service.py`
- **Framework**: pytest (in requirements? — not listed but used in conftest)

### Test File Structure

```
tests/
├── conftest.py                          # Existing — add new fixtures
├── test_safety_gates.py                 # NEW — 35+ test cases
├── test_quality_criteria.py             # NEW — 20+ test cases
├── test_scoring.py                      # NEW — 25+ test cases
├── test_fact_check_improvements.py      # Existing
├── test_quality_loop.py                 # Existing
├── test_generation_api.py              # Existing
└── test_llm_service.py                 # Existing
```

### Test Cases: `test_safety_gates.py`

#### Fixtures Needed (add to conftest.py)

```python
@pytest.fixture
def base_verification_data():
    """Minimal passing verification data."""
    return {
        "confidence_score": 0.85,
        "risk_level": "low",
        "fabricated_claims": 0,
        "unverifiable_claims": 0,
        "total_claims": 10,
        "grounded_claims": 8,
        "context_claims": 2,
        "expansion_ratio": 2.0,
        "is_verified": True,
        "entity_comparison": {
            "source_entities": ["A", "B", "C"],
            "output_entities": ["A", "B", "C", "D"],
            "common_entities": ["A", "B", "C"],
            "novel_entities": ["D"],
        },
    }

@pytest.fixture
def production_mode(monkeypatch):
    """Enable production safety mode."""
    monkeypatch.setenv("PRODUCTION_SAFETY_MODE", "true")

@pytest.fixture
def legacy_mode(monkeypatch):
    """Disable production safety mode."""
    monkeypatch.setenv("PRODUCTION_SAFETY_MODE", "false")
```

#### Test Case Matrix

```python
# === HARD BLOCKS ===

class TestSafetyGatesHardBlocks:
    # Risk level blocks
    def test_critical_risk_blocks(self, base_verification_data)
    def test_high_risk_blocks_in_production(self, base_verification_data, production_mode)
    def test_high_risk_does_NOT_block_in_legacy(self, base_verification_data, legacy_mode)

    # Confidence blocks
    def test_confidence_below_050_blocks_in_production(self, production_mode)
    def test_confidence_below_040_blocks_in_legacy(self, legacy_mode)
    def test_confidence_at_050_does_NOT_block_production(self, production_mode)
    def test_confidence_at_040_does_NOT_block_legacy(self, legacy_mode)
    def test_confidence_block_only_when_is_verified(self)  # is_verified=False → no block

    # Publication floor blocks (production only)
    def test_confidence_below_publish_floor_065_blocks(self, production_mode)
    def test_confidence_at_065_does_NOT_block(self, production_mode)
    def test_grounded_below_070_blocks(self, production_mode)
    def test_grounded_at_070_does_NOT_block(self, production_mode)
    def test_context_claims_count_as_partial_grounded(self, production_mode)

    # Fabrication blocks
    def test_2_fabricated_blocks_production(self, production_mode)
    def test_1_fabricated_low_confidence_blocks_production(self, production_mode)
    def test_1_fabricated_high_confidence_does_NOT_block_production(self, production_mode)
    def test_3_fabricated_blocks_legacy(self, legacy_mode)
    def test_2_fabricated_low_confidence_blocks_legacy(self, legacy_mode)
    def test_2_fabricated_high_confidence_does_NOT_block_legacy(self, legacy_mode)

    # Unverifiable blocks
    def test_3_unverifiable_over_40pct_blocks(self)
    def test_3_unverifiable_under_40pct_does_NOT_block(self)
    def test_2_unverifiable_does_NOT_block(self)

    # Expansion blocks
    def test_expansion_over_8x_blocks_production(self, production_mode)
    def test_expansion_at_8x_does_NOT_block_production(self, production_mode)
    def test_expansion_over_15x_blocks_legacy(self, legacy_mode)
    def test_expansion_uses_effective_source_len(self)
    def test_expansion_fallback_when_source_len_zero(self)

# === SOFT REVIEW GATES ===

class TestSafetyGatesSoftReview:
    def test_1_fabricated_high_confidence_triggers_review_production(self, production_mode)
    def test_2_fabricated_high_confidence_triggers_review_legacy(self, legacy_mode)
    def test_unverifiable_2_over_30pct_triggers_review(self)
    def test_novel_entities_4_plus_high_ratio_triggers_review(self)
    def test_novel_entities_skipped_when_confidence_high(self)  # confidence >= 0.80
    def test_expansion_10_15_triggers_review_legacy(self, legacy_mode)
    def test_high_risk_triggers_review_legacy_not_blocked(self, legacy_mode)

# === EDGE CASES ===

class TestSafetyGatesEdgeCases:
    def test_empty_verification_data_defaults(self)
    def test_zero_total_claims_no_division_error(self)
    def test_prior_review_carried_forward(self)
    def test_prior_review_reasons_carried_forward(self)
    def test_multiple_block_reasons_accumulated(self)
    def test_no_blocks_no_reviews_clean_pass(self)
    def test_block_prevents_soft_review_for_same_fabrication(self)
```

### Test Cases: `test_scoring.py`

```python
class TestCalculateScores:
    # Individual signals
    @pytest.mark.parametrize("value,expected", [("yes", 25), ("partial", 12), ("no", 0)])
    def test_inesperado_scoring(self, value, expected)

    @pytest.mark.parametrize("value,expected", [("high", 30), ("medium", 15), ("low", 0)])
    def test_impacto_scoring(self, value, expected)

    @pytest.mark.parametrize("value,expected", [("yes", 25), ("maybe", 12), ("no", 0)])
    def test_busca_agora_scoring(self, value, expected)

    @pytest.mark.parametrize("value,expected", [("yes", 20), ("maybe", 10), ("no", 0)])
    def test_conversa_scoring(self, value, expected)

    # Classification boundaries
    def test_max_score_is_100_class_A(self)  # all max → 25+30+25+20=100
    def test_min_score_is_0_class_C(self)    # all min → 0
    def test_score_75_is_class_A(self)       # boundary
    def test_score_74_is_class_B(self)       # boundary
    def test_score_35_is_class_B(self)       # boundary
    def test_score_34_is_class_C(self)       # boundary

    # Edge cases
    def test_missing_signal_defaults_to_zero(self)
    def test_invalid_signal_value_defaults_to_zero(self)
    def test_all_partial_maybe_scores(self)  # 12+15+12+10=49 → B

class TestHeuristicScoring:
    def test_high_value_keywords_boost_scores(self)
    def test_no_keywords_gives_low_scores(self)
    def test_relevance_boost_from_major_entities(self)
    def test_multiple_categories_detected(self)
```

### Test Cases: `test_quality_criteria.py`

```python
class TestQualityCriteria:
    def test_all_pass_clean_article(self)
    def test_fabrication_fails_with_1_fabricated(self)
    def test_readability_fails_below_flesch_threshold(self)
    def test_readability_threshold_relaxed_for_analise(self)
    def test_readability_threshold_relaxed_for_economia(self)
    def test_confidence_fails_below_065_when_verified(self)
    def test_confidence_passes_when_not_verified(self)
    def test_novel_entities_fails_5_plus_high_ratio(self)
    def test_unverifiable_fails_3_plus_high_ratio(self)
    def test_risk_level_fails_high_production(self, production_mode)
    def test_risk_level_ignored_legacy(self, legacy_mode)
    def test_multiple_failures_accumulated(self)
    def test_corrective_instructions_built_from_failures(self)
```

### Implementation Order

1. **Fix broken test** in `test_generation_api.py:129` — remove `@patch("functions.generation_api.PRODUCTION_SAFETY_MODE", True)` and use `production_mode` fixture instead (the patched constant no longer exists — test silently runs in legacy mode)
2. **Add fixtures** to `conftest.py`:
   - `production_mode` fixture using `patch.dict(os.environ, {"PRODUCTION_SAFETY_MODE": "true", "JWT_SECRET_KEY": "a" * 32})` (JWT secret required in prod mode)
   - `make_verification_data(**overrides)` factory function
3. **Create `test_safety_gates.py`** — ~50 test cases, start with hard block tests (most critical)
4. **Create `test_scoring.py`** — `_calculate_scores` tests (simple, fast), ~25 test cases
5. **Create `test_quality_criteria.py`** — quality loop criteria, ~20 test cases
6. **Run full suite**: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/ -v`

**Important**: The `production_mode` fixture must also reset the config singleton since JWT_SECRET_KEY validation happens at config load time:
```python
@pytest.fixture
def production_mode():
    with patch.dict(os.environ, {
        "PRODUCTION_SAFETY_MODE": "true",
        "JWT_SECRET_KEY": "a" * 32,
    }):
        import services.config as cfg_mod
        cfg_mod._config = None  # Force reload with new env
        yield
        cfg_mod._config = None
```

### Dependencies to Add

```
# requirements-dev.txt (or add to requirements.txt)
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

### Estimated Effort: 4-6 hours

---

## P0-3: Backend CI/CD via GitHub Actions

### Current State

- **Frontend CI/CD**: Already automated via `.github/workflows/azure-static-web-apps-purple-river-09235a310.yml`
- **Backend deploy**: Manual `func azure functionapp publish tmc-redacao-api --python`
- **Existing test infra**: `tests/` directory with 6 test files + conftest.py
- **No pytest in requirements.txt** — needs to be added or handled in CI
- **host.json**: Standard Azure Functions v2 config with Extension Bundle v4

### Workflow Design

#### File: `.github/workflows/backend-deploy.yml`

```yaml
name: Backend CI/CD

on:
  push:
    branches: [main]
    paths:
      - 'FeedRSS/**'
      - '.github/workflows/backend-deploy.yml'
  pull_request:
    branches: [main]
    paths:
      - 'FeedRSS/**'
  workflow_dispatch:  # Manual trigger for emergencies

concurrency:
  group: backend-deploy
  cancel-in-progress: true

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: FeedRSS/tmc-rss-collector
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: FeedRSS/tmc-rss-collector/requirements.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio

      - name: Run tests
        env:
          PRODUCTION_SAFETY_MODE: "false"
          SQL_SERVER: "dummy"
          SQL_DATABASE: "dummy"
          SQL_USERNAME: "dummy"
          SQL_PASSWORD: "dummy"
        run: python -m pytest tests/ -v --tb=short

  deploy:
    name: Deploy to Azure Functions
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: production  # Requires manual approval
    defaults:
      run:
        working-directory: FeedRSS/tmc-rss-collector
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Deploy to Azure Functions
        uses: Azure/functions-action@v1
        with:
          app-name: 'tmc-redacao-api'
          package: 'FeedRSS/tmc-rss-collector'
          publish-profile: ${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE }}
          scm-do-build-during-deployment: true

      - name: Health check (3 retries, cold start tolerance)
        run: |
          sleep 30
          HEALTH_URL="https://tmc-redacao-api-b7h3dyaxazfvdcez.eastus2-01.azurewebsites.net/api/health"
          for i in 1 2 3; do
            STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL")
            if [ "$STATUS" = "200" ]; then
              echo "Health check passed (attempt $i)"
              curl -s "$HEALTH_URL" | python -m json.tool
              exit 0
            fi
            echo "Attempt $i: HTTP $STATUS, retrying in 15s..."
            sleep 15
          done
          echo "DEPLOY WARNING: Health check failed after 3 attempts"
          exit 1
```

### Secrets Required

| Secret | How to Get | Where |
|--------|-----------|-------|
| `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` | Azure Portal → tmc-redacao-api → Get Publish Profile → Download XML | GitHub repo Settings → Secrets |

### Environment Protection

1. Go to GitHub repo → Settings → Environments
2. Create `production` environment
3. Add **Required reviewers** (enzo.oliveira@jaarconsult.com.br)
4. Add **Wait timer**: 0 minutes (manual approval is enough)

### Rollback Strategy

**Option A — Revert commit** (simplest):
```bash
git revert HEAD
git push origin main
# CI/CD auto-deploys the reverted version
```

**Option B — Azure Portal**:
- Azure Portal → tmc-redacao-api → Deployment Center → Redeploy previous version

**Option C — Manual CLI** (emergency bypass):
```bash
git checkout <last-good-commit>
cd FeedRSS/tmc-rss-collector
func azure functionapp publish tmc-redacao-api --python
git checkout main
```

### First Deploy Checklist

1. [ ] Download publish profile from Azure Portal
2. [ ] Add `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` secret to GitHub
3. [ ] Create `production` environment with required reviewer
4. [ ] Push workflow file on a branch first → test the `test` job on PR
5. [ ] Merge to main → approve deploy → verify health check passes
6. [ ] Keep manual deploy command documented as emergency fallback

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| First automated deploy breaks production | Low | Health check + manual approval gate |
| Tests fail on CI but pass locally (env differences) | Medium | Set dummy env vars, PRODUCTION_SAFETY_MODE=false |
| Publish profile expires | Low | Azure auto-rotates; update secret if deploy fails |
| Path filter misses relevant files | Low | `FeedRSS/**` catches everything in backend dir |

### Estimated Effort: 3-4 hours

---

## Implementation Order (Recommended)

### Phase 1: Tests First (P0-2) — Days 1-2
Why first: Tests create a safety net for the other changes. Once tests exist, we can verify P0-1 doesn't break safety gates.

### Phase 2: CI/CD (P0-3) — Day 2
Why second: Once tests exist, the CI/CD pipeline can run them. This creates automated validation for future changes.

### Phase 3: Async DB (P0-1) — Days 3-4
Why last: This is the riskiest change (touches every handler). Having tests + CI/CD in place means we can verify correctness automatically and roll back if needed.

### Total Estimated Effort: 10-14 hours across 4 days

---

## Pre-Implementation Checklist

- [ ] Verify current tests pass: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/ -v`
- [ ] Ensure `pytest` and `pytest-asyncio` are installed locally
- [ ] Confirm Azure Functions publish profile is accessible
- [ ] Take note of current `GET /api/health` response as baseline
- [ ] Create a git branch: `git checkout -b feat/p0-production-hardening`
