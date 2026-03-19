# Costs Dashboard — Implementation Plan (v2)

**Date:** 2026-03-19
**Status:** Approved
**Version:** 2 (revised — incorporates findings from 5 review teams)
**Related:** [Frontend Plan](2026-03-19-costs-dashboard-frontend-plan-v2.md) | [v1 Plan](2026-03-19-costs-dashboard-plan.md)

## Context

TMC admins need full visibility into platform costs. Currently, LLM calls are logged to `llm_usage_log` (migration 009) with token counts and USD costs, but there are critical gaps: **no user attribution** (no `user_id` column), **zero Exa API cost tracking**, **no embedding cost tracking**, **no cost API endpoints**, and **no dashboard UI**. The existing `SistemaPage` only shows a kill switch with basic savings estimate.

The goal is a comprehensive admin Costs page at `/configuracoes/custos` with: total costs by provider, cost per user, cost per source, cost per action, trends over time, and a "what-if" calculator for adding new RSS sources.

### Complete Cost Source Map (26 sources audited)

| Category | Sites | Currently Tracked | This Plan Covers |
|----------|:-----:|:-----------------:|:----------------:|
| LLM calls | 19 | 18 logged (no user_id) | All 19 |
| Exa API calls | 5 | 0 | All 5 |
| Embedding calls | 2 | 0 | All 2 |
| Google Fact Check | 1 | 0 | N/A (free API) |
| YouTube/Transcription | 2 | 0 | N/A (free) |

---

## Phase 0: Bug Fixes (Pre-requisite)

### Task 0.1 — Fix broken Gemini cost logging

**File:** `FeedRSS/tmc-rss-collector/services/gemini_service.py` (line 274)

The Gemini service calls `db.log_llm_usage()` which **does not exist** in `DatabaseService`. The correct method is `insert_llm_usage_log()`. The error is silently swallowed by `logger.debug`. If Gemini is ever activated, all cost logging would fail.

**Fix:** Change line 274 from:
```python
db.log_llm_usage(
    model=model,
    task_type=task_type or "gemini_call",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    cost_usd=total_cost,
    duration_ms=int(elapsed * 1000),
    correlation_id=correlation_id or None,
)
```
To:
```python
db.insert_llm_usage_log({
    'model': model,
    'task_type': task_type or 'gemini_call',
    'provider': 'google',
    'endpoint': 'gemini',
    'input_tokens': input_tokens,
    'output_tokens': output_tokens,
    'total_tokens': input_tokens + output_tokens,
    'input_cost_usd': input_tokens * cost_in,
    'output_cost_usd': output_tokens * cost_out,
    'total_cost_usd': total_cost,
    'latency_ms': int(elapsed * 1000),
    'status': 'success',
    'correlation_id': correlation_id or None,
})
```

---

## Phase 1: Database Migrations

### Task 1.1 — Migration 017: Extend `llm_usage_log` with user/action tracking

**File:** `FeedRSS/tmc-rss-collector/migrations/017_cost_tracking_extensions.sql`

Add columns to existing `llm_usage_log` table:
```sql
ALTER TABLE llm_usage_log ADD user_id UNIQUEIDENTIFIER NULL;
ALTER TABLE llm_usage_log ADD source_id UNIQUEIDENTIFIER NULL;
ALTER TABLE llm_usage_log ADD action_type VARCHAR(50) NULL;
ALTER TABLE llm_usage_log ADD cache_read_tokens INT NULL;
ALTER TABLE llm_usage_log ADD cache_creation_tokens INT NULL;
-- action_type values: 'generate_article', 'edit_article', 'fact_check_scan',
--   'deep_verify', 'extract_topics', 'merge_topics', 'generate_tags',
--   'research', 'system_rss', 'system_embedding', 'system_scoring',
--   'system_clustering', 'system_clustering_maintenance'
```

Add indexes:
- `IX_llm_usage_user (user_id, created_at DESC)`
- `IX_llm_usage_source (source_id, created_at DESC) WHERE source_id IS NOT NULL`
- `IX_llm_usage_action (action_type, created_at DESC)`
- `IX_llm_usage_hourly (created_at, action_type) INCLUDE (user_id, total_cost_usd, input_tokens, output_tokens)` — supports "today" view with `granularity=hour`

### Task 1.2 — Migration 018: Create `api_usage_log` + `daily_cost_summary` + `daily_cost_detail`

**File:** `FeedRSS/tmc-rss-collector/migrations/018_api_usage_and_daily_summary.sql`

**`api_usage_log`** — for non-LLM API costs (Exa, embeddings):
| Column | Type | Purpose |
|--------|------|---------|
| id | UNIQUEIDENTIFIER PK DEFAULT NEWID() | |
| correlation_id | VARCHAR(64) NULL | Links to generation_audit_trail |
| user_id | UNIQUEIDENTIFIER NULL | NULL for system/timer calls |
| source_id | UNIQUEIDENTIFIER NULL | For RSS pipeline attribution |
| action_type | VARCHAR(50) NULL | Same values as llm_usage_log |
| provider | VARCHAR(30) NOT NULL | 'exa', 'azure_openai_embedding' |
| operation | VARCHAR(50) NOT NULL | 'enrichment_search', 'claim_verification', 'factcheck_site_search', 'research_search', 'embedding_batch', 'embedding_single' |
| request_count | INT DEFAULT 1 | Number of API calls |
| input_units | INT NULL | Exa: num_results; Embeddings: token count |
| cost_usd | DECIMAL(10,6) NULL | Estimated cost |
| latency_ms | INT NULL | |
| status | VARCHAR(10) DEFAULT 'success' | |
| error_message | NVARCHAR(500) NULL | |
| metadata | NVARCHAR(MAX) NULL | JSON (query text, batch_size, etc.) |
| created_at | DATETIME2 DEFAULT GETUTCDATE() | |

Indexes:
- `IX_api_usage_created (created_at DESC)`
- `IX_api_usage_provider (provider, created_at DESC)`
- `IX_api_usage_action (action_type, created_at DESC)`

**`daily_cost_summary`** — pre-aggregated for fast dashboard overview/trends queries:
| Column | Type | Purpose |
|--------|------|---------|
| id | INT IDENTITY PK | |
| date | DATE NOT NULL | |
| provider | VARCHAR(30) NOT NULL | 'anthropic', 'exa', 'azure_openai_embedding' |
| action_type | VARCHAR(50) NOT NULL DEFAULT 'unknown' | |
| call_count | INT DEFAULT 0 | |
| total_input_tokens | BIGINT DEFAULT 0 | |
| total_output_tokens | BIGINT DEFAULT 0 | |
| total_cost_usd | DECIMAL(12,6) DEFAULT 0 | |
| avg_latency_ms | INT NULL | |

Unique index on `(date, provider, action_type)`.

**`daily_cost_detail`** — per-user/source breakdown for drill-down queries:
| Column | Type | Purpose |
|--------|------|---------|
| id | INT IDENTITY PK | |
| date | DATE NOT NULL | |
| provider | VARCHAR(30) NOT NULL | |
| model | VARCHAR(100) NULL | NULL for Exa |
| task_type | VARCHAR(50) NULL | |
| action_type | VARCHAR(50) NOT NULL DEFAULT 'unknown' | |
| user_id | UNIQUEIDENTIFIER NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000' | Sentinel for system |
| source_id | UNIQUEIDENTIFIER NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000' | Sentinel for no-source |
| call_count | INT DEFAULT 0 | |
| total_input_tokens | BIGINT DEFAULT 0 | |
| total_output_tokens | BIGINT DEFAULT 0 | |
| total_cost_usd | DECIMAL(12,6) DEFAULT 0 | |
| avg_latency_ms | INT NULL | |

Unique index on `(date, provider, model, task_type, action_type, user_id, source_id)`.

**Note on sentinel values:** Use `'00000000-0000-0000-0000-000000000000'` instead of NULL for `user_id` and `source_id` in both summary tables. Azure SQL treats NULLs as equal in unique indexes, which would prevent multiple system-level rows per day. The aggregation job must `ISNULL(user_id, '00000000-0000-0000-0000-000000000000')` when inserting.

### Task 1.3 — Historical data backfill script

**New file:** `FeedRSS/tmc-rss-collector/scripts/backfill_daily_costs.py`

One-time script that:
1. Reads all existing `llm_usage_log` rows (since migration 009, ~March 9)
2. Infers `action_type` from `task_type` using a mapping:
   - `article_generation` → `generate_article`
   - `article_edit` → `edit_article`
   - `topic_extraction` → `extract_topics`
   - `tag_generation` → `generate_tags`
   - `story_fusion` → `merge_topics`
   - `classification` → `system_rss`
   - `scoring` → `system_scoring`
   - `theme_naming` → `system_clustering`
   - `claim_extraction`, `source_comparison`, `cove_qa`, `cove_verdict`, `enrichment_extraction` → `generate_article`
   - `scan_claim_extraction`, `scan_claim_verdict` → `fact_check_scan`
   - `deep_verify_claims` → `deep_verify`
   - `event_extraction` → `system_rss`
   - `event_verification` → `system_clustering`
3. Aggregates into `daily_cost_summary` and `daily_cost_detail` with `user_id='00000000-...'` (no user data available for historical rows)
4. Logs total rows processed and date range covered

---

## Phase 2: Backend Instrumentation

### Task 2.1 — Create request context propagation

**New file:** `FeedRSS/tmc-rss-collector/services/request_context.py`

Uses Python `contextvars.ContextVar` to propagate `user_id`, `action_type`, and `source_id` from HTTP handlers down to `llm_service._call_api()` without changing 20+ function signatures across the large service files.

```python
from contextvars import ContextVar

current_user_id: ContextVar[str | None] = ContextVar('current_user_id', default=None)
current_action_type: ContextVar[str | None] = ContextVar('current_action_type', default=None)
current_source_id: ContextVar[str | None] = ContextVar('current_source_id', default=None)
current_correlation_id: ContextVar[str | None] = ContextVar('current_correlation_id', default=None)
```

**Why ContextVar:** Azure Functions v2 runs each HTTP request in its own async context. ContextVar is scoped per-task, doesn't leak between concurrent requests, and avoids touching signatures of `_call_api()`, `generate_article()`, etc. The `_log_data` dict is constructed BEFORE being passed to `run_in_executor` (line 2156), so ContextVar values are read safely in the main async context.

**Note on timer triggers:** Timer handlers receive `func.TimerRequest` (not `HttpRequest`), which has no `user` attribute. Set `current_user_id` to `None` and `current_action_type` to the appropriate `system_*` value.

### Task 2.2 — Set context in all handlers

**Complete handler mapping** (corrected from v1):

| Handler file | Function | action_type value |
|---|---|---|
| `functions/generation_api.py` (line 604) | `generate_article_handler` | `generate_article` |
| `functions/edit_api.py` (line 57) | `edit_article_handler` | `edit_article` |
| `functions/generation_api.py` (line 1471) | `extract_topics_handler` | `extract_topics` |
| `functions/generation_api.py` (line 1960) | `merge_topics_handler` | `merge_topics` |
| `functions/generation_api.py` (line 1516) | `generate_tags_handler` | `generate_tags` |
| `functions/fact_check_scan_api.py` (line 36) | `fact_check_scan_handler` | `fact_check_scan` |
| `functions/fact_check_scan_api.py` (line 167) | `deep_verify_handler` | `deep_verify` |
| `functions/research_api.py` (line 244) | `research_topic_handler` | `research` |
| `functions/rss_collector.py` (timer) | `rss_collector_handler` | `system_rss` |
| `functions/embedding_generator.py` (timer) | `embedding_generator_handler` | `system_embedding` |
| `functions/scoring_calculator.py` (timer) | `scoring_calculator_handler` | `system_scoring` |
| `functions/clustering_engine.py` (timer) | `clustering_engine_handler` | `system_clustering` |
| `functions/clustering_maintenance.py` (line 542, timer) | `clustering_maintenance_handler` | `system_clustering_maintenance` |

**v2 corrections from v1:**
- `edit_article` handler is in `functions/edit_api.py:57`, NOT `generation_api.py`
- Added `deep_verify_handler` at `fact_check_scan_api.py:167` (separate endpoint)
- Added `clustering_maintenance` timer (daily 3AM, `function_app.py:208`)
- Event extraction (`event_signature_service.py:145`) inherits `system_rss` from the RSS collector context
- Event verification (`llm_verification_service.py:240`) inherits `system_clustering` from the clustering engine context

User ID comes from `req.user['id']` — injected by `@require_auth` in `utils/auth.py:77`. Note: `req.user` is available but currently no handler in `generation_api.py` reads it. The ContextVar approach works because `@require_auth` sets `req.user` before the handler is called.

**Add correlation_id to handlers missing it:**
- `extract_topics_handler` — add `correlation_id = str(uuid.uuid4())[:8]`
- `generate_tags_handler` — add `correlation_id = str(uuid.uuid4())[:8]`
- `merge_topics_handler` — add `correlation_id = str(uuid.uuid4())[:8]`
- `edit_article_handler` — add `correlation_id = str(uuid.uuid4())[:8]`

Set `current_correlation_id` ContextVar so Exa calls can inherit it.

### Task 2.3 — Read context in LLM logging

**File:** `services/llm_service.py` (line 2141)

In `_call_api()`, when building `_log_data` dict, add:
```python
from services.request_context import current_user_id, current_action_type, current_source_id
_log_data['user_id'] = current_user_id.get()
_log_data['action_type'] = current_action_type.get()
_log_data['source_id'] = current_source_id.get()
```

Also capture cache token data (already available in the API response at lines 2122-2127):
```python
_log_data['cache_read_tokens'] = usage.get('cache_read_input_tokens', 0)
_log_data['cache_creation_tokens'] = usage.get('cache_creation_input_tokens', 0)
```

**File:** `services/database.py` (line 3163)

Update `insert_llm_usage_log()` INSERT statement to include `user_id`, `source_id`, `action_type`, `cache_read_tokens`, `cache_creation_tokens`.

### Task 2.4 — Add Exa cost logging

**All 5 Exa call sites** (corrected from v1 which had only 4):

| # | File | Function | Line | Operation | Caller |
|---|------|----------|------|-----------|--------|
| 1 | `services/fact_check_service.py` | `_search_exa()` | 671 | `enrichment_search` or `claim_verification` | Article generation |
| 2 | `services/article_safety_service.py` | `_search_exa_corroboration()` | 455 | `claim_corroboration` | Fact-check scan |
| 3 | `services/article_safety_service.py` | `_search_factcheck_sites()` | 556 | `factcheck_site_search` | Fact-check scan |
| 4 | `services/article_safety_service.py` | `_deep_verify_exa_search()` | 905 | `deep_verify_search` | Deep verify |
| 5 | `functions/research_api.py` | `_search_exa()` (standalone function) | 177 | `research_search` | Manual research |

**v2 correction:** Site #3 (`_search_factcheck_sites`) was completely missing from v1.

**Instrumentation approach for `_search_exa()` in `fact_check_service.py`:** Add an `operation` parameter so callers pass the operation name and logging happens once inside the method:

```python
async def _search_exa(self, query, num_results=5, operation='enrichment_search'):
    # ... existing code ...
    # After successful response:
    from services.request_context import current_user_id, current_action_type, current_correlation_id
    get_db().insert_api_usage_log({
        'correlation_id': current_correlation_id.get(),
        'user_id': current_user_id.get(),
        'action_type': current_action_type.get(),
        'provider': 'exa',
        'operation': operation,
        'request_count': 1,
        'input_units': num_results,
        'cost_usd': get_config().exa_cost_per_search,
        'latency_ms': elapsed,
        'status': 'success',
    })
```

Callers update:
- Line 555 (enrichment): `await self._search_exa(query, operation='enrichment_search')`
- Line 793 (claim verification): `await self._search_exa(query, operation='claim_verification')`

Same pattern for `article_safety_service.py` methods — add logging inside each method.

For `research_api.py._search_exa()` (standalone function at line 177): add logging after the `httpx` response, same pattern but without `self`.

**New env var:** `EXA_COST_PER_SEARCH` (default: `0.001` USD) — added to `config.py`. Note: this is an estimate. Should be periodically reconciled against actual Exa invoices.

### Task 2.5 — Add embedding cost logging

**Both embedding call sites** (v1 only covered batch):

| # | File | Function | Line | Operation |
|---|------|----------|------|-----------|
| 1 | `services/embedding_service.py` | `_call_embedding_api()` | 182 | `embedding_batch` |
| 2 | `services/embedding_service.py` | `generate_embedding()` | 94 | `embedding_single` |

For batch (line 223-228, inside `_call_embedding_api()`):
```python
usage = result.get("usage", {})
total_tokens = usage.get("total_tokens", 0)
get_db().insert_api_usage_log({
    'provider': 'azure_openai_embedding',
    'operation': 'embedding_batch',
    'input_units': total_tokens,
    'cost_usd': total_tokens * (get_config().embedding_cost_per_1m_tokens / 1_000_000),
    'action_type': current_action_type.get() or 'system_embedding',
})
```

**Note:** `_call_embedding_api()` returns only embeddings, not token counts. The cost logging MUST happen inside the method (at line 223-228), not outside it.

For single (line 94, inside `generate_embedding()`): same pattern with `operation='embedding_single'`.

**New env var:** `EMBEDDING_COST_PER_1M_TOKENS` (default: `0.02` USD) — matches Azure OpenAI text-embedding-3-small pricing.

### Task 2.6 — Create cost query service

**New file:** `FeedRSS/tmc-rss-collector/services/cost_queries.py`

Create a separate module instead of adding to `database.py` (already 3840 lines — flagged in CLAUDE.md gotchas). Imports `get_db()` and uses `db.get_connection()` for raw SQL. Follows the pattern of `services/scoring_service.py`.

Methods:

1. `insert_api_usage_log(log_data: dict)` — non-blocking INSERT via `run_in_executor`, same pattern as `insert_llm_usage_log` with `_trunc()` for string fields
2. `get_cost_overview(period: str)` — totals for today/7d/30d/90d/year, split by provider (LLM vs Exa vs Embeddings), with delta vs previous period
3. `get_cost_by_action(start_date, end_date)` — breakdown by action_type with call counts, total cost, avg cost, % of total
4. `get_cost_by_user(start_date, end_date)` — per user_id, JOINed with `users.name` and `users.email`, includes articles_generated/edits/scans counts
5. `get_cost_by_source(start_date, end_date)` — per source_id, JOINed with `sources.name` and `sources.category`
6. `get_cost_trends(granularity, start_date, end_date)` — time series with `{date, total, llm, exa, embeddings}` per period
7. `get_source_cost_estimate()` — avg cost per active source per day, avg articles per source, avg cost per generated article
8. `aggregate_daily_costs(date)` — MERGE/UPSERT raw logs into `daily_cost_summary` and `daily_cost_detail`

**Query routing:**
- `granularity=hour` (today): queries raw `llm_usage_log` + `api_usage_log` with `GROUP BY DATEPART(hour, created_at)`
- `granularity=day/week/month`: queries `daily_cost_summary` (fast, pre-aggregated)
- Per-user and per-source drill-downs: query `daily_cost_detail`

---

## Phase 3: Cost API Endpoints

### Task 3.1 — Create costs API handler

**New file:** `FeedRSS/tmc-rss-collector/functions/costs_api.py`

All endpoints use `@with_cors @require_admin` (NOT `@require_auth` + manual role check). The `@require_admin` decorator already exists at `utils/auth.py:82` and is used by `/api/stats`, `/api/metrics`, `/api/clustering-stats`.

**Response format:** Return data directly (no `{success: true, data: ...}` envelope). Errors use `{"error": "message"}` consistent with all existing endpoints.

#### Endpoint 1: `GET /api/costs/overview`

**Params:** `period` — one of `today`, `7d`, `30d`, `90d`, `year`

**Response:**
```json
{
  "total_cost": 48.23,
  "delta_percent": 12.5,
  "total_calls": 1847,
  "sonnet_calls": 312,
  "haiku_calls": 1535,
  "avg_cost_per_article": 0.18,
  "articles_generated": 267,
  "projected_monthly": 62.40,
  "provider_split": {
    "llm": 47.15,
    "exa": 0.98,
    "embeddings": 0.10
  },
  "period": "30d",
  "start_date": "2026-02-17",
  "end_date": "2026-03-19"
}
```

#### Endpoint 2: `GET /api/costs/trends`

**Params:** `granularity` — one of `hour`, `day`, `week`, `month`; `start_date`, `end_date`

**Response:**
```json
{
  "granularity": "day",
  "data": [
    { "date": "2026-03-01", "total": 1.28, "llm": 1.23, "exa": 0.05, "embeddings": 0.002 },
    { "date": "2026-03-02", "total": 1.45, "llm": 1.40, "exa": 0.04, "embeddings": 0.003 }
  ]
}
```

#### Endpoint 3: `GET /api/costs/breakdown`

**Params:** `start_date`, `end_date`, `group_by` — one of `action`, `task`, `model`

**Response:**
```json
{
  "items": [
    { "action": "generate_article", "call_count": 312, "total_cost": 35.50, "avg_cost": 0.1138, "pct_of_total": 73.6 },
    { "action": "fact_check_scan", "call_count": 45, "total_cost": 4.20, "avg_cost": 0.0933, "pct_of_total": 8.7 }
  ],
  "total_cost": 48.23
}
```

#### Endpoint 4: `GET /api/costs/by-user`

**Params:** `start_date`, `end_date`

**Response:**
```json
{
  "items": [
    {
      "user_id": 1,
      "user_name": "João Silva",
      "user_email": "joao@example.com",
      "articles_generated": 120,
      "edits": 45,
      "scans": 12,
      "total_cost": 25.30,
      "cost_per_article": 0.21
    }
  ],
  "system_cost": 12.50
}
```

Note: `system_cost` is the total for timer-triggered operations (no user attribution).

#### Endpoint 5: `GET /api/costs/by-source`

**Params:** `start_date`, `end_date`

**Response:**
```json
{
  "items": [
    {
      "source_id": 1,
      "source_name": "G1 Política",
      "category": "politica",
      "articles_collected": 450,
      "total_cost": 0.90,
      "cost_per_article": 0.002
    }
  ]
}
```

#### Endpoint 6: `GET /api/costs/source-estimate`

**Params:** none

**Response:**
```json
{
  "avg_articles_per_source_per_day": 20,
  "avg_cost_per_article_pipeline": 0.002,
  "avg_cost_per_generated_article": 0.18,
  "avg_articles_generated_per_source": 0.28,
  "active_sources": 15,
  "total_daily_pipeline_cost": 0.60
}
```

### Task 3.2 — Register routes in function_app.py

Add route registrations for all 6 endpoints following existing pattern:
```python
from functions.costs_api import (
    costs_overview_handler,
    costs_trends_handler,
    costs_breakdown_handler,
    costs_by_user_handler,
    costs_by_source_handler,
    costs_source_estimate_handler,
)
```

### Task 3.3 — Daily aggregation timer

New timer trigger in `function_app.py`: runs at **00:30 UTC** daily (not 00:05 — allows buffer for late log entries), calls `cost_queries.aggregate_daily_costs(yesterday)`.

```python
@app.timer_trigger(schedule="0 30 0 * * *", arg_name="timer", run_on_startup=False)
async def daily_cost_aggregation(timer: func.TimerRequest):
    from services.cost_queries import aggregate_daily_costs
    yesterday = (datetime.utcnow() - timedelta(days=1)).date()
    await aggregate_daily_costs(yesterday)
```

### Task 3.4 — Data retention cleanup (monthly)

New timer trigger: runs at 03:00 UTC on the 1st of each month. Deletes raw `llm_usage_log` and `api_usage_log` rows older than 90 days (after confirming they have been aggregated into `daily_cost_summary`/`daily_cost_detail`).

---

## Phase 4: Frontend Dashboard

Frontend implementation is covered in the separate plan: `docs/plans/2026-03-19-costs-dashboard-frontend-plan-v2.md`

Key decisions (for backend reference):
- Period selector sends: `today`, `7d`, `30d`, `90d`, `year`
- "Today" view uses `granularity=hour` (backend must query raw tables)
- Mock data via `VITE_COSTS_USE_MOCK=true` env var (not 404 detection)
- 6 parallel API calls with `Promise.allSettled`

---

## Cost Action Map (Reference — corrected estimates)

| User Action (Button) | API Call | AI Calls | Est. Cost |
|---|---|---|---|
| **Gerar Artigo** | POST /api/generate | 1 Exa enrichment + Sonnet generation + Sonnet claim extraction + up to 10 Exa claim verifications + Sonnet CoVe (x2) + up to 3 regen loops | $0.08-$0.30 |
| **Editar Artigo** | POST /api/edit-article | 1 Sonnet call | $0.02-$0.08 |
| **Fact-Check Scan** | POST /api/fact-check-scan | Haiku extraction + 3-10 Exa verifications + 1 Exa factcheck sites + Haiku verdict | $0.03-$0.15 |
| **Verificação Profunda** | POST /api/fact-check-deep-verify | Up to 15 Exa searches + Haiku classification | $0.02-$0.08 |
| **Pesquisar (Exa)** | POST /api/research | 1-5 Exa searches | $0.001-$0.005 |
| **Extrair Tópicos** | POST /api/extract-topics | 1 Sonnet call | $0.01-$0.03 |
| **Gerar Tags** | POST /api/generate-tags | 1 Sonnet call | $0.005-$0.02 |
| **Sistema: RSS** (every 15min) | Timer | Haiku classification + Haiku scoring + Sonnet event extraction per article | ~$0.002/article |
| **Sistema: Embeddings** (every 5min) | Timer | Azure OpenAI batch (50 articles) | ~$0.000015/article |
| **Sistema: Scoring** (every 10min) | Timer | Haiku scoring per unscored article | ~$0.001/article |
| **Sistema: Clustering** (every 30min) | Timer | Haiku theme naming per new theme + Sonnet event verification | ~$0.001/theme |
| **Sistema: Manutenção** (daily 3AM) | Timer | Haiku theme renaming for merged themes | ~$0.0003/theme |

**Notes on estimates:**
- Gerar Artigo range adjusted from v1's $0.05 to $0.08 (typical no-regen article is ~$0.10-$0.15)
- RSS cost doubled from v1's $0.001 to $0.002 (accounts for 2 Haiku calls + event extraction)
- Embedding cost corrected from v1's $0.0001 to $0.000015 (was overestimated 6x)
- All estimates assume prompt caching is active (which it is per `prompt_caching_enabled: True` in config). Without caching, LLM costs would be ~2-3x higher.
- Exa cost of $0.001/search is configurable via env var — reconcile against actual invoices periodically.

---

## Deployment Order

1. **Migration 017 + 018** — run `python scripts/run_migrations.py` (non-breaking: adds nullable columns and new tables)
2. **Backfill script** — run `python scripts/backfill_daily_costs.py` (one-time, populates historical data)
3. **Phase 0** — fix Gemini logging bug (deploy with Phase 2)
4. **Phase 2** — backend instrumentation (backward-compatible, writes to new columns)
5. **Phase 3** — cost API endpoints + aggregation timer
6. **Frontend** — last (auto-deploys on push to `main`, mock fallback ready)

---

## Verification

1. **Run migration 017 + 018** locally — verify tables/columns exist
2. **Run backfill script** — verify `daily_cost_summary` has historical data
3. **Generate an article** — check `llm_usage_log` has `user_id` and `action_type` populated
4. **Generate an article** — check `api_usage_log` has Exa search entries with correlation_id
5. **Run fact-check scan** — check `api_usage_log` has entries for corroboration AND factcheck sites
6. **Wait for embedding timer** — check `api_usage_log` has embedding entries
7. **Call each `/api/costs/*` endpoint** with curl — verify JSON matches response schemas above
8. **Test `granularity=hour`** for today's data — verify hourly buckets
9. **Open `/configuracoes/custos`** — verify all 6 sections render with real data
10. **Test what-if calculator** — verify calculation matches manual estimate

---

## Critical Files

| File | Changes |
|---|---|
| `FeedRSS/tmc-rss-collector/services/gemini_service.py` (line 274) | FIX - broken `log_llm_usage()` → `insert_llm_usage_log()` |
| `FeedRSS/tmc-rss-collector/migrations/017_cost_tracking_extensions.sql` | NEW - ALTER llm_usage_log + indexes |
| `FeedRSS/tmc-rss-collector/migrations/018_api_usage_and_daily_summary.sql` | NEW - CREATE api_usage_log + daily_cost_summary + daily_cost_detail |
| `FeedRSS/tmc-rss-collector/scripts/backfill_daily_costs.py` | NEW - one-time historical data backfill |
| `FeedRSS/tmc-rss-collector/services/request_context.py` | NEW - ContextVar for user_id/action_type/correlation_id propagation |
| `FeedRSS/tmc-rss-collector/services/cost_queries.py` | NEW - 8 cost query methods (separate from database.py) |
| `FeedRSS/tmc-rss-collector/services/llm_service.py` (line 2141) | EDIT - read ContextVar, add to log_data, capture cache tokens |
| `FeedRSS/tmc-rss-collector/services/database.py` (line 3163) | EDIT - extend INSERT with user_id, source_id, action_type, cache columns |
| `FeedRSS/tmc-rss-collector/services/fact_check_service.py` (line 671) | EDIT - add `operation` param to `_search_exa`, add cost logging |
| `FeedRSS/tmc-rss-collector/services/article_safety_service.py` (lines 455, 556, 905) | EDIT - add Exa cost logging in 3 methods |
| `FeedRSS/tmc-rss-collector/services/embedding_service.py` (lines 94, 223) | EDIT - add embedding cost logging (batch + single) |
| `FeedRSS/tmc-rss-collector/services/config.py` | EDIT - add EXA_COST_PER_SEARCH, EMBEDDING_COST_PER_1M_TOKENS |
| `FeedRSS/tmc-rss-collector/functions/costs_api.py` | NEW - 6 cost API endpoints |
| `FeedRSS/tmc-rss-collector/functions/generation_api.py` | EDIT - set request context at handler top |
| `FeedRSS/tmc-rss-collector/functions/edit_api.py` (line 57) | EDIT - set request context for edit_article |
| `FeedRSS/tmc-rss-collector/functions/fact_check_scan_api.py` (lines 36, 167) | EDIT - set context for scan + deep_verify |
| `FeedRSS/tmc-rss-collector/functions/research_api.py` (line 177) | EDIT - add Exa cost logging |
| `FeedRSS/tmc-rss-collector/functions/rss_collector.py` | EDIT - set request context for system_rss |
| `FeedRSS/tmc-rss-collector/functions/clustering_engine.py` | EDIT - set request context for system_clustering |
| `FeedRSS/tmc-rss-collector/functions/clustering_maintenance.py` | EDIT - set context for system_clustering_maintenance |
| `FeedRSS/tmc-rss-collector/function_app.py` | EDIT - register cost routes + aggregation timer + cleanup timer |

---

## Changes from v1

1. **Phase 0 added** — fix pre-existing Gemini logging bug (`db.log_llm_usage()` → `db.insert_llm_usage_log()`)
2. **Split daily_cost_summary** into `daily_cost_summary` (overview/trends) + `daily_cost_detail` (per-user/source drill-down)
3. **Sentinel values** for NULLs in unique indexes (Azure SQL NULL uniqueness issue)
4. **Historical data backfill** script added
5. **5th Exa call site** added: `article_safety_service._search_factcheck_sites()` at line 556
6. **Single embedding** tracking added: `embedding_service.generate_embedding()` at line 94
7. **Corrected file references**: `edit_article` → `edit_api.py`, `deep_verify` → `fact_check_scan_api.py:167`
8. **Added missing handlers**: `event_extraction`, `event_verification`, `clustering_maintenance`
9. **Hourly granularity** support for "today" view with covering index
10. **Cache token columns** added to `llm_usage_log` for cache efficiency monitoring
11. **`@require_admin`** instead of `@require_auth` + manual role check
12. **`cost_queries.py`** separate module instead of expanding `database.py`
13. **Explicit JSON response schemas** for all 6 API endpoints
14. **Period parameter** accepts `7d`/`30d`/`90d`/`today`/`year` (matching frontend)
15. **Aggregation timer** at 00:30 UTC (not 00:05) to avoid race conditions
16. **Data retention** cleanup job (90-day raw log purge)
17. **Correlation_id** added to 4 handlers that were missing it
18. **`correlation_id`** added to ContextVar for end-to-end cost tracing
19. **Cost estimates corrected**: RSS $0.002, embeddings $0.000015, Gerar Artigo $0.08-$0.30
20. **Google Fact Check API** documented as zero-cost dependency (excluded from tracking)
