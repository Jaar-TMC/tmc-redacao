# Production Hardening To-Do

> Generated 2026-03-13 from multi-agent code review (5 specialized agents analyzed security, architecture, performance, frontend, and backend code quality).

## Status Legend

- [ ] Not started
- [x] Completed (2026-03-12 fix sprint)

---

## Completed (2026-03-12)

- [x] **P0 Security**: Remove stack trace leakage from `with_cors` error handler (`function_app.py`)
- [x] **P0 Security**: Sanitize traceback exposure in `transcribe-diag` endpoint
- [x] **P1 Security**: Generate random JWT secret in dev mode when `JWT_SECRET_KEY` is empty (`config.py`)
- [x] **P1 Security**: Harden DOMPurify config in `ArticleViewModal.jsx` (restrictive ALLOWED_TAGS/ATTR)
- [x] **P1 Performance**: Connection pool timestamp-based health check skip (60s window, `database.py`)
- [x] **P1 Code Quality**: Consolidate `os.environ` reads to `get_config()` across 4 files (17 env vars)
- [x] **P1 Code Quality**: Deduplicate rate limiter boilerplate (9 blocks to 1 helper in `function_app.py`)
- [x] **P2 Code Quality**: Create shared `utils/responses.py` (eliminate duplicate error/success helpers)
- [x] **P2 Performance**: Add `loading="lazy"` and `decoding="async"` to content images
- [x] **P2 Performance**: Add vendor chunk for React/ReactDOM/Router in `vite.config.js`
- [x] **P2 Code Quality**: Fix deprecated `.substr()` calls in hooks
- [x] **P2 Frontend**: Explicit `useMemo` dependencies in `CriarContext.jsx`

---

## P0 -- Critical (do before next feature)

### 1. Wrap synchronous DB calls with `asyncio.to_thread()`
- **Why**: `database.py` is 100% synchronous pymssql. All async handlers block the event loop during DB queries. Under concurrent load, requests queue serially.
- **Impact**: 3-5x throughput improvement under concurrent HTTP load
- **Effort**: 2-4 hours
- **Files**: Create a wrapper utility, apply to all handler-level DB calls in `functions/` directory
- **Approach**:
  ```python
  # In each async handler:
  articles, total = await asyncio.to_thread(db.get_articles, page=page, limit=limit)
  ```

### 2. Unit tests for `evaluate_safety_gates()` and scoring logic
- **Why**: The function that decides whether fabricated news gets published has ZERO test coverage. It has 15+ branching conditions. A single regression could publish hallucinated content or block all articles.
- **Impact**: Safety net for the most critical code path
- **Effort**: 4-6 hours
- **Files**: Create `tests/test_safety_gates.py`, `tests/test_scoring.py`
- **What to test**: All hard block conditions (confidence < 0.65, grounded < 70%, expansion > 8x, high risk), soft review gates, production vs legacy mode, quality loop criteria

### 3. Backend CI/CD via GitHub Actions
- **Why**: Backend deployment is manual `func azure functionapp publish`. No rollback path, no pre-deploy validation, no automated testing.
- **Impact**: Deploy safety, rollback capability
- **Effort**: 4-6 hours
- **Files**: `.github/workflows/backend-deploy.yml`
- **Approach**: Trigger on push to `main` when `FeedRSS/` files change. Run `pytest`, then deploy. Add manual approval gate for production.

---

## P1 -- High Priority (do within 2 weeks)

### 4. Split `database.py` into domain repositories
- **Why**: 3,621-line God Object with 80+ methods touching every table. Impossible to test in isolation. Every feature adds to the monolith.
- **Impact**: Maintainability step-change, enables unit testing
- **Effort**: 8-12 hours
- **Approach**: Split into `repositories/article_repo.py`, `repositories/source_repo.py`, `repositories/user_repo.py`, `repositories/theme_repo.py`, `repositories/auth_repo.py`. Keep `ConnectionPool` and `DatabaseService` as the base. Each repository gets injected with a connection pool reference.

### 5. Enable Anthropic prompt caching
- **Why**: ~4,000 tokens of identical system prompt sent on every LLM call (editorial guidelines, anti-fabrication rules). Anthropic API supports automatic caching.
- **Impact**: ~30-40% reduction in input token costs
- **Effort**: 1-2 hours
- **Files**: `services/llm_service.py` -- add cache control headers to system prompt blocks
- **Approach**: Use `cache_control: {"type": "ephemeral"}` on the system message content blocks

### 6. Implement refresh token rotation
- **Why**: When a refresh token is used, a new access token is issued but the same refresh token stays valid. If stolen, attacker has persistent access for 7-30 days.
- **Impact**: Security hardening
- **Effort**: 2-3 hours
- **Files**: `functions/auth_api.py` (refresh_handler), `services/auth_service.py`
- **Approach**: On successful refresh, issue new refresh token cookie and blacklist the old one

### 7. Add staging environment
- **Why**: Changes go directly to production. For a newsroom tool with safety gates, this is risky.
- **Impact**: Deploy confidence, testing isolation
- **Effort**: 4-6 hours
- **Approach**: Create Azure Functions staging slot or a separate `tmc-redacao-api-staging` function app. Add `STAGING` env flag.

---

## P2 -- Medium Priority (do within 1 month)

### 8. Split `CriarPostPage.jsx` into sub-components
- **Why**: 1,795-line god component with 30 useState calls. Impossible to test, every change risks side effects.
- **Impact**: Frontend maintainability
- **Effort**: 6-8 hours
- **Target components**: `EditorPanel`, `ChatSidebar`, `SEOSidebar`, `VersionHistorySidebar`, `SavePublishBar`, `VerificationSection`

### 9. Extract LLM prompts into `prompts/` directory
- **Why**: ~1,500 lines of prompt strings in `llm_service.py`. Editorial staff cannot review prompts without reading Python code.
- **Impact**: Prompt editability, code clarity
- **Effort**: 3-4 hours
- **Approach**: Create `prompts/` package with `.py` or `.txt` files per prompt category. Import in `llm_service.py`.

### 10. Add dead letter queue for pipeline failures
- **Why**: If embedding generation fails for an article, it retries every 5 minutes indefinitely. A poisoned article burns API credits forever.
- **Impact**: Cost protection, operational reliability
- **Effort**: 3-4 hours
- **Approach**: Add `retry_count` and `last_error` columns to `collected_articles`. Skip articles with `retry_count > 5`. Alert on poisoned articles.

### 11. Consolidate remaining duplicate `create_error_response` definitions
- **Why**: `edit_api.py`, `transcription_api.py`, `research_api.py` still define their own copies.
- **Impact**: Code quality consistency
- **Effort**: 1 hour
- **Files**: Import from `utils.responses` in all 3 files, remove local definitions

### 12. Add timer trigger overlap protection
- **Why**: Embedding trigger runs every 5 minutes. If Azure OpenAI is slow, next trigger processes same articles concurrently.
- **Impact**: Prevent duplicate embeddings, wasted API calls
- **Effort**: 2-3 hours
- **Approach**: Add `processing_started_at` column or use Azure Functions singleton lock (`host.json` singleton configuration)

### 13. Sanitize remaining `transcribe-diag` error messages
- **Why**: 6 `except` blocks still embed `f"FAIL: {e}"` in responses. Admin-only but inconsistent with security hardening.
- **Impact**: Consistency
- **Effort**: 30 minutes

---

## P3 -- Nice to Have (backlog)

### 14. Split `CriarContext` into focused contexts
- `FonteContext`, `TextoBaseContext`, `ConfiguracoesContext`
- Requires splitting the single `useState` into multiple calls for real re-render savings

### 15. Add custom exception hierarchy
- `DatabaseError`, `LLMError`, `FactCheckError` instead of bare `except Exception`
- Enables callers to make informed error-handling decisions

### 16. Consolidate dual frontend caching layers
- `apiCache.js` and `ArticlesCacheContext` both implement TTL caching independently
- Pick one, remove the other

### 17. Replace `nest_asyncio` hack
- Used in 4 services as a band-aid for async/sync boundary design
- Azure Functions v2 Python supports async handlers natively

### 18. Add per-IP rate limiting
- Current rate limiter is global (one bucket per endpoint, not per user)
- Consider Azure API Management or Redis-backed buckets

### 19. Migrate vector storage from Azure SQL JSON to vector database
- Current: embeddings stored as JSON strings, cosine similarity computed in Python
- Works at hundreds of articles, won't scale past ~50K
- Options: Azure AI Search, pgvector, Qdrant

### 20. Add Infrastructure-as-Code
- Azure resources are presumably portal-created
- Bicep or Terraform templates for reproducible environments

---

## Metrics to Track

| Metric | Current | Target | How to Measure |
|--------|---------|--------|---------------|
| Test coverage (safety gates) | 0% | 100% | pytest --cov |
| Backend deploy time | ~2 min manual | <5 min automated | GitHub Actions duration |
| Connection pool health check overhead | ~5-15ms/query (optimized) | 0ms for active connections | Application Insights |
| LLM input token waste | ~4,000 tokens/call (no caching) | ~400 tokens/call (cached) | `llm_usage_log` table |
| Concurrent request throughput | ~1 req at a time (sync blocking) | 5-10 concurrent | Load test with k6 |
