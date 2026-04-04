# Costs Dashboard — Implementation Plan

**Date:** 2026-03-19
**Status:** Review

## Context

TMC admins need full visibility into platform costs. Currently, LLM calls are logged to `llm_usage_log` (migration 009) with token counts and USD costs, but there are critical gaps: **no user attribution** (no `user_id` column), **zero Exa API cost tracking**, **no embedding cost tracking**, **no cost API endpoints**, and **no dashboard UI**. The existing `SistemaPage` only shows a kill switch with basic savings estimate.

The goal is a comprehensive admin Costs page at `/configuracoes/custos` with: total costs by provider, cost per user, cost per source, cost per action, trends over time, and a "what-if" calculator for adding new RSS sources.

---

## Phase 1: Database Migrations (Backend)

### Task 1.1 — Migration 017: Extend `llm_usage_log` with user/action tracking

**File:** `FeedRSS/tmc-rss-collector/migrations/017_cost_tracking_extensions.sql`

Add columns to existing `llm_usage_log` table:
```sql
ALTER TABLE llm_usage_log ADD user_id UNIQUEIDENTIFIER NULL;
ALTER TABLE llm_usage_log ADD source_id UNIQUEIDENTIFIER NULL;
ALTER TABLE llm_usage_log ADD action_type VARCHAR(50) NULL;
-- action_type values: 'generate_article', 'edit_article', 'fact_check_scan',
--   'deep_verify', 'extract_topics', 'merge_topics', 'generate_tags',
--   'research', 'system_rss', 'system_embedding', 'system_scoring', 'system_clustering'
```

Add indexes:
- `IX_llm_usage_user (user_id, created_at DESC)`
- `IX_llm_usage_source (source_id, created_at DESC) WHERE source_id IS NOT NULL`
- `IX_llm_usage_action (action_type, created_at DESC)`

### Task 1.2 — Migration 018: Create `api_usage_log` + `daily_cost_summary`

**File:** `FeedRSS/tmc-rss-collector/migrations/018_api_usage_and_daily_summary.sql`

**`api_usage_log`** — for non-LLM API costs (Exa, embeddings):
| Column | Type | Purpose |
|--------|------|---------|
| id | UNIQUEIDENTIFIER PK | |
| correlation_id | VARCHAR(64) NULL | Links to generation_audit_trail |
| user_id | UNIQUEIDENTIFIER NULL | NULL for system/timer calls |
| source_id | UNIQUEIDENTIFIER NULL | For RSS pipeline attribution |
| action_type | VARCHAR(50) NULL | Same values as llm_usage_log |
| provider | VARCHAR(30) NOT NULL | 'exa', 'azure_openai_embedding' |
| operation | VARCHAR(50) NOT NULL | 'enrichment_search', 'claim_verification', 'research_search', 'embedding_batch' |
| request_count | INT DEFAULT 1 | Number of API calls |
| input_units | INT NULL | Exa: num_results; Embeddings: token count |
| cost_usd | DECIMAL(10,6) NULL | Estimated cost |
| latency_ms | INT NULL | |
| status | VARCHAR(10) DEFAULT 'success' | |
| error_message | NVARCHAR(500) NULL | |
| metadata | NVARCHAR(MAX) NULL | JSON (query text, batch_size, etc.) |
| created_at | DATETIME2 DEFAULT GETUTCDATE() | |

**`daily_cost_summary`** — pre-aggregated for fast dashboard queries:
| Column | Type | Purpose |
|--------|------|---------|
| id | INT IDENTITY PK | |
| date | DATE NOT NULL | |
| provider | VARCHAR(30) NOT NULL | 'anthropic', 'exa', 'azure_openai_embedding' |
| model | VARCHAR(100) NULL | NULL for Exa |
| task_type | VARCHAR(50) NULL | |
| action_type | VARCHAR(50) NULL | |
| user_id | UNIQUEIDENTIFIER NULL | NULL = system aggregate |
| source_id | UNIQUEIDENTIFIER NULL | |
| call_count | INT DEFAULT 0 | |
| total_input_tokens | BIGINT DEFAULT 0 | |
| total_output_tokens | BIGINT DEFAULT 0 | |
| total_cost_usd | DECIMAL(12,6) DEFAULT 0 | |
| avg_latency_ms | INT NULL | |

Unique index on `(date, provider, model, task_type, action_type, user_id, source_id)`.

---

## Phase 2: Backend Instrumentation

### Task 2.1 — Create request context propagation

**New file:** `FeedRSS/tmc-rss-collector/services/request_context.py`

Uses Python `contextvars.ContextVar` to propagate `user_id` and `action_type` from HTTP handlers down to `llm_service._call_api()` without changing 20+ function signatures across the 3 large service files.

```python
from contextvars import ContextVar
current_user_id: ContextVar[str | None] = ContextVar('current_user_id', default=None)
current_action_type: ContextVar[str | None] = ContextVar('current_action_type', default=None)
current_source_id: ContextVar[str | None] = ContextVar('current_source_id', default=None)
```

**Why ContextVar:** Azure Functions runs each request in its own async context. ContextVar is scoped per-task, doesn't leak between concurrent requests, and avoids touching signatures of `call_api()`, `generate_article()`, `classify_article()`, etc.

### Task 2.2 — Set context in all HTTP handlers

For each user-facing handler, add at the top:
| Handler file | action_type value |
|---|---|
| `functions/generation_api.py` (generate) | `generate_article` |
| `functions/generation_api.py` (edit) | `edit_article` |
| `functions/generation_api.py` (extract-topics) | `extract_topics` |
| `functions/generation_api.py` (merge-topics) | `merge_topics` |
| `functions/generation_api.py` (generate-tags) | `generate_tags` |
| `functions/fact_check_scan_api.py` | `fact_check_scan` |
| `functions/research_api.py` | `research` |
| `functions/rss_collector.py` (timer) | `system_rss` |
| `functions/embedding_generator.py` (timer) | `system_embedding` |
| `functions/scoring_calculator.py` (timer) | `system_scoring` |
| `functions/clustering_engine.py` (timer) | `system_clustering` |

User ID comes from `getattr(req, 'user', {}).get('id')` — already injected by `@require_auth`.

### Task 2.3 — Read context in LLM logging

**File:** `services/llm_service.py` (~line 2141)

In `_call_api()`, when building `_log_data` dict, add:
```python
from services.request_context import current_user_id, current_action_type, current_source_id
_log_data['user_id'] = current_user_id.get()
_log_data['action_type'] = current_action_type.get()
_log_data['source_id'] = current_source_id.get()
```

**File:** `services/database.py` (~line 3163)

Update `insert_llm_usage_log()` INSERT statement to include `user_id`, `source_id`, `action_type`.

### Task 2.4 — Add Exa cost logging

**Files to instrument:**
1. `services/fact_check_service.py._search_exa()` (~line 671) — enrichment search
2. `services/article_safety_service.py._search_exa_corroboration()` (~line 455) — claim verification
3. `services/article_safety_service.py._deep_verify_exa_search()` (~line 905) — deep verify
4. `functions/research_api.py._search_exa()` (~line 177) — manual research

After each successful Exa HTTP call, insert into `api_usage_log`:
```python
db.insert_api_usage_log({
    'correlation_id': ...,
    'user_id': current_user_id.get(),
    'provider': 'exa',
    'operation': 'enrichment_search',  # or 'claim_verification', 'research_search'
    'request_count': 1,
    'input_units': num_results,
    'cost_usd': config.exa_cost_per_search,  # new env var, default 0.001
    'latency_ms': elapsed,
    'status': 'success',
})
```

**New env var:** `EXA_COST_PER_SEARCH` (default: `0.001` USD) — added to `config.py`

### Task 2.5 — Add embedding cost logging

**File:** `services/embedding_service.py` (~line 223)

After the Azure OpenAI call returns with `usage.total_tokens`, insert into `api_usage_log`:
```python
db.insert_api_usage_log({
    'provider': 'azure_openai_embedding',
    'operation': 'embedding_batch',
    'input_units': total_tokens,
    'cost_usd': total_tokens * (0.02 / 1_000_000),  # text-embedding-3-small pricing
    'action_type': 'system_embedding',
})
```

**New env var:** `EMBEDDING_COST_PER_1M_TOKENS` (default: `0.02` USD)

### Task 2.6 — New database methods

**File:** `services/database.py` — add these methods:

1. `insert_api_usage_log(log_data: dict)` — non-blocking INSERT, same pattern as `insert_llm_usage_log`
2. `get_cost_overview(period)` — totals for today/week/month/year, split by provider (LLM vs Exa vs Embeddings)
3. `get_cost_by_action(start_date, end_date)` — breakdown by action_type
4. `get_cost_by_user(start_date, end_date)` — per user_id, JOINed with users.name
5. `get_cost_by_source(start_date, end_date)` — per source_id, JOINed with sources.name
6. `get_cost_trends(granularity, start_date, end_date)` — daily/weekly/monthly time series
7. `get_source_cost_estimate()` — avg cost per active source per day (for what-if)
8. `aggregate_daily_costs(date)` — roll up raw logs into `daily_cost_summary`

Queries use `daily_cost_summary` for historical periods, real-time tables for today.

---

## Phase 3: Cost API Endpoints

### Task 3.1 — Create costs API handler

**New file:** `FeedRSS/tmc-rss-collector/functions/costs_api.py`

| Endpoint | Method | Params | Returns |
|---|---|---|---|
| `/api/costs/overview` | GET | `period` (today/week/month/year) | Totals by provider, deltas vs previous period |
| `/api/costs/breakdown` | GET | `start_date`, `end_date`, `group_by` (action/task/model) | Breakdown with call counts and costs |
| `/api/costs/by-user` | GET | `start_date`, `end_date` | Per-user: name, articles generated, total cost, avg per article |
| `/api/costs/by-source` | GET | `start_date`, `end_date` | Per-source: name, articles, classification+scoring+embedding cost |
| `/api/costs/trends` | GET | `granularity` (day/week/month), `start_date`, `end_date` | Time series for chart |
| `/api/costs/source-estimate` | GET | — | Avg cost per source/day, projections |

All endpoints require admin auth (`@with_cors @require_auth` + role check).

### Task 3.2 — Register routes in function_app.py

Add route registrations for all 6 endpoints. Follow existing pattern.

### Task 3.3 — Daily aggregation timer

New timer trigger in `function_app.py`: runs at 00:05 UTC daily, calls `db.aggregate_daily_costs(yesterday)`.

---

## Phase 4: Frontend Dashboard

### Task 4.1 — Add recharts dependency

```bash
cd tmc-redacao && npm install recharts
```

Recharts adds ~40KB gzipped. The project already uses TipTap (~120KB), so acceptable.

### Task 4.2 — Create costs API service

**New file:** `tmc-redacao/src/services/costsApi.js`

Functions: `getCostOverview()`, `getCostBreakdown()`, `getCostByUser()`, `getCostBySource()`, `getCostTrends()`, `getSourceEstimate()`. Uses existing `apiRequest()` from `api.js`.

### Task 4.3 — Create CustosPage component

**New file:** `tmc-redacao/src/pages/config/CustosPage.jsx`

6 sections:

1. **Overview Cards** (top row) — Total cost today / this month / this year / avg daily. Each card shows LLM%, Exa%, Embedding% mini bar.

2. **Cost Trends Chart** — Stacked area chart (recharts) with LLM/Exa/Embedding layers. Period selector: 7d/30d/90d/1y.

3. **Action Cost Map** — Table mapping each user action to its cost. Portuguese labels:
   | Action | Label |
   |---|---|
   | generate_article | Gerar Artigo |
   | edit_article | Editar Artigo |
   | fact_check_scan | Fact-Check Scan |
   | deep_verify | Verificacao Profunda |
   | extract_topics | Extrair Topicos |
   | merge_topics | Mesclar Topicos |
   | generate_tags | Gerar Tags |
   | research | Pesquisar (Exa) |
   | system_rss | Sistema: RSS |
   | system_embedding | Sistema: Embeddings |
   | system_scoring | Sistema: Scoring |
   | system_clustering | Sistema: Clustering |

4. **Per-User Cost Table** — Sortable: name, email, total cost, articles generated, top action, avg cost/article.

5. **Per-Source Cost Table** — Sortable: source name, articles collected, total cost (classification + scoring + embedding), cost per article.

6. **What-If Calculator** — Input: number of new sources. Output: estimated daily/monthly/yearly cost increase. Formula: `avg_cost_per_source_per_day * new_sources * period_days`.

**State management:** Simple `useState` + `useEffect` with direct API calls (same pattern as `SistemaPage`). No new context needed — this page is admin-only and doesn't share state.

### Task 4.4 — Wire up route and navigation

**`App.jsx`** (~line 20): Add lazy import:
```jsx
const CustosPage = lazy(() => import('./pages/config/CustosPage'));
```

**`App.jsx`** (~line 53): Add title:
```js
'/configuracoes/custos': 'Custos - Configuracoes',
```

**`App.jsx`** (~line 205): Add route inside `/configuracoes`:
```jsx
<Route path="custos" element={<ProtectedRoute permission="manage_users"><CustosPage /></ProtectedRoute>} />
```

**`ConfiguracoesPage.jsx`** (~line 3): Add DollarSign import:
```jsx
import { Newspaper, Users, Power, DollarSign, Menu, X } from 'lucide-react';
```

**`ConfiguracoesPage.jsx`** (~line 24): Add menu item:
```jsx
...(canManageUsers ? [{ path: '/configuracoes/custos', label: 'Custos', icon: DollarSign }] : []),
```

---

## Cost Action Map (Reference)

| User Action (Button) | API Call | AI Calls | Est. Cost |
|---|---|---|---|
| **Gerar Artigo** | POST /api/generate | 1 Exa enrichment + Sonnet generation + Sonnet claim extraction + up to 10 Exa claim verifications + Sonnet CoVe (x2) + up to 3 regen loops | $0.05-$0.30 |
| **Editar Artigo** | POST /api/edit-article | 1 Sonnet call | $0.02-$0.08 |
| **Fact-Check Scan** | POST /api/fact-check-scan | Sonnet extraction + 3-10 Exa verifications + Sonnet verdict | $0.03-$0.15 |
| **Pesquisar (Exa)** | POST /api/research | 1-5 Exa searches | $0.001-$0.005 |
| **Extrair Topicos** | POST /api/extract-topics | 1 Sonnet call | $0.01-$0.03 |
| **Gerar Tags** | POST /api/generate-tags | 1 Sonnet call | $0.005-$0.02 |
| **Sistema: RSS** (every 15min) | Timer | Haiku classification + Haiku scoring per article | ~$0.001/article |
| **Sistema: Embeddings** (every 5min) | Timer | Azure OpenAI batch (50 articles) | ~$0.0001/article |
| **Sistema: Clustering** (every 30min) | Timer | Haiku theme naming per new theme | ~$0.0003/theme |

---

## Verification

1. **Run migration 017 + 018** locally - verify tables/columns exist
2. **Generate an article** - check `llm_usage_log` has `user_id` and `action_type` populated
3. **Generate an article** - check `api_usage_log` has Exa search entries
4. **Wait for embedding timer** - check `api_usage_log` has embedding entries
5. **Call each `/api/costs/*` endpoint** with Postman/curl - verify JSON responses
6. **Open `/configuracoes/custos`** - verify all 6 sections render with real data
7. **Test what-if calculator** - verify calculation matches manual estimate
8. **Build + lint**: `cd tmc-redacao && npm run build && npm run lint`
9. **Backend**: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/` (if tests exist)

---

## Critical Files

| File | Changes |
|---|---|
| `FeedRSS/tmc-rss-collector/migrations/017_cost_tracking_extensions.sql` | NEW - ALTER llm_usage_log |
| `FeedRSS/tmc-rss-collector/migrations/018_api_usage_and_daily_summary.sql` | NEW - CREATE api_usage_log + daily_cost_summary |
| `FeedRSS/tmc-rss-collector/services/request_context.py` | NEW - ContextVar for user_id/action_type propagation |
| `FeedRSS/tmc-rss-collector/services/llm_service.py` (~line 2141) | EDIT - read ContextVar, add to log_data |
| `FeedRSS/tmc-rss-collector/services/database.py` (~line 3163, 3779) | EDIT - extend INSERT, add 8 new query methods |
| `FeedRSS/tmc-rss-collector/services/fact_check_service.py` (~line 720) | EDIT - add Exa cost logging after _search_exa |
| `FeedRSS/tmc-rss-collector/services/embedding_service.py` (~line 223) | EDIT - add embedding cost logging |
| `FeedRSS/tmc-rss-collector/services/config.py` | EDIT - add EXA_COST_PER_SEARCH, EMBEDDING_COST_PER_1M_TOKENS |
| `FeedRSS/tmc-rss-collector/functions/costs_api.py` | NEW - 6 cost API endpoints |
| `FeedRSS/tmc-rss-collector/functions/generation_api.py` | EDIT - set request context at handler top |
| `FeedRSS/tmc-rss-collector/functions/rss_collector.py` | EDIT - set request context for system_rss |
| `FeedRSS/tmc-rss-collector/function_app.py` | EDIT - register cost routes + daily aggregation timer |
| `tmc-redacao/src/pages/config/CustosPage.jsx` | NEW - full costs dashboard |
| `tmc-redacao/src/services/costsApi.js` | NEW - API helpers |
| `tmc-redacao/src/App.jsx` (~lines 20, 53, 205) | EDIT - lazy import, title, route |
| `tmc-redacao/src/pages/ConfiguracoesPage.jsx` (~line 3, 24) | EDIT - DollarSign icon, menu item |
