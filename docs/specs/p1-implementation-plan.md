# P1 High Priority Issues - Implementation Plan

> Generated 2026-03-13 by 4 specialized agents analyzing security, architecture, performance, and infrastructure.
> Goal: Fix all 4 P1 issues WITHOUT breaking the running application.

---

## Overview

| ID | Issue | Effort | Risk | Savings/Impact |
|----|-------|--------|------|----------------|
| P1-4 | Split `database.py` into domain repositories | 4-6h | Low (facade pattern) | Maintainability step-change |
| P1-5 | Enable Anthropic prompt caching | 1-2h | Low | ~$20-30/month + 100-200ms latency |
| P1-6 | Implement refresh token rotation | 2-3h | Medium | Security hardening |
| P1-7 | Add staging environment | 2-3h | Low | Deploy confidence |

**Recommended execution order**: P1-5 → P1-6 → P1-7 → P1-4

Rationale: P1-5 is the quickest win (1-2h, immediate cost savings). P1-6 is a targeted security fix. P1-7 creates staging infrastructure. P1-4 is the largest refactor and benefits from having staging + CI in place first.

---

## P1-4: Split `database.py` into Domain Repositories

### Problem

`database.py` is a 3,648-line God Object with 80+ methods touching every table. Impossible to test in isolation. Every feature adds to the monolith.

### Architecture

**New directory structure:**
```
services/
  database.py              # Keeps ConnectionPool + facade (~250 lines)
  repos/
    __init__.py             # Re-exports all repo classes
    base.py                 # BaseRepository base class
    article_repo.py         # 27 methods: articles, user_articles, tags, collection logs
    source_repo.py          # 9 methods: RSS source CRUD
    theme_repo.py           # 13 methods: themes + article-theme relations
    embedding_repo.py       # 5 methods: embedding storage
    scoring_repo.py         # 5 methods: article scores
    event_repo.py           # 8 methods: event signatures
    user_repo.py            # 12 methods: user CRUD
    auth_repo.py            # 4 methods: token blacklist, auth events
    audit_repo.py           # 4 methods: generation audit, LLM usage, fact-check scans
```

### Base Class Design

```python
# services/repos/base.py
class BaseRepository:
    """Base class for all domain repositories."""
    def __init__(self, db_service: 'DatabaseService'):
        self._db = db_service

    def get_connection(self):
        return self._db.get_connection()
```

### Backward Compatibility Strategy

**Zero-breakage migration via facade pattern:**

1. Extract methods into repo classes
2. `DatabaseService` retains ALL methods as one-line delegations
3. `get_db()` returns the same `DatabaseService` object — all callers unchanged
4. New code can optionally use `get_db().sources.get_all_sources()`

```python
class DatabaseService:
    def __init__(self):
        # ... existing connection setup ...
        self.articles = ArticleRepository(self)
        self.sources = SourceRepository(self)
        self.themes = ThemeRepository(self)
        self.embeddings = EmbeddingRepository(self)
        self.scoring = ScoringRepository(self)
        self.events = EventRepository(self)
        self.users = UserRepository(self)
        self.auth = AuthRepository(self)
        self.audit = AuditRepository(self)

    # Backward compat delegations
    def get_all_sources(self, *a, **kw):
        return self.sources.get_all_sources(*a, **kw)
    # ... one per method ...
```

### Method Inventory by Repository

#### `article_repo.py` — ArticleRepository (27 methods)

| Method | Line | Domain |
|--------|------|--------|
| `_build_article_filters` | 431 | Core query builder |
| `get_articles` | 513 | List articles with pagination |
| `get_articles_with_urgency` | 568 | List with urgency counts |
| `get_urgency_counts` | 681 | A/B/C urgency breakdown |
| `get_article_by_id` | 725 | Single article lookup |
| `check_existing_hashes` | 745 | Deduplication |
| `get_recent_titles` | 773 | Recent title lookup |
| `insert_articles` | 795 | Batch insert |
| `insert_articles_returning` | 808 | Insert with ID return |
| `delete_old_articles` | 880 | Cleanup |
| `delete_duplicate_articles_by_title` | 906 | Dedup cleanup |
| `_row_to_article` | 1331 | Row mapper |
| `get_trending_tags` | 980 | Tag analytics |
| `get_all_tags` | 1057 | Tag listing |
| `get_categories_filtered` | 1131 | Category listing |
| `get_all_tags_filtered` | 1166 | Filtered tag listing |
| `log_collection` | 951 | Collection run logging |
| `get_collection_stats` | 1267 | Collection statistics |
| `get_user_articles` | 1362 | User article listing |
| `get_user_article_by_id` | 1453 | Single user article |
| `create_user_article` | 1476 | Create user article |
| `update_user_article` | 1546 | Update user article |
| `delete_user_article` | 1638 | Soft delete user article |
| `_row_to_user_article` | 1667 | Row mapper |

#### `source_repo.py` — SourceRepository (9 methods)

| Method | Line |
|--------|------|
| `get_all_sources` | 219 |
| `get_active_sources` | 233 |
| `get_sources_to_fetch` | 248 |
| `get_source_by_id` | 280 |
| `create_source` | 294 |
| `update_source` | 322 |
| `delete_source` | 366 |
| `update_source_last_fetch` | 380 |
| `_row_to_source` | 1314 |

#### `theme_repo.py` — ThemeRepository (13 methods)

| Method | Line |
|--------|------|
| `create_theme` | 1935 |
| `get_theme` | 1994 |
| `get_theme_by_slug` | 2026 |
| `get_all_themes` | 2058 |
| `update_theme` | 2088 |
| `_row_to_theme` | 2157 |
| `add_article_to_theme` | 2186 |
| `get_articles_by_theme` | 2237 |
| `get_article_themes` | 2295 |
| `get_articles_without_theme` | 2333 |
| `get_articles_pending_clustering` | 2370 |
| `add_article_to_theme_with_match_type` | 3010 |
| `update_theme_event_data` | 2956 |

#### `embedding_repo.py` — EmbeddingRepository (5 methods)

| Method | Line |
|--------|------|
| `save_article_embedding` | 1701 |
| `save_article_embeddings_batch` | 1752 |
| `get_article_embedding` | 1828 |
| `get_articles_without_embedding` | 1867 |
| `mark_article_has_embedding` | 1905 |

#### `scoring_repo.py` — ScoringRepository (5 methods)

| Method | Line |
|--------|------|
| `save_article_score` | 2414 |
| `get_article_score` | 2488 |
| `get_articles_without_score` | 2525 |
| `mark_article_has_score` | 2566 |
| `get_theme_article_scores` | 2592 |

#### `event_repo.py` — EventRepository (8 methods)

| Method | Line |
|--------|------|
| `save_event_signature` | 2632 |
| `get_event_signature` | 2725 |
| `find_signatures_by_canonical_key` | 2757 |
| `find_themes_by_canonical_key` | 2803 |
| `get_articles_pending_signature` | 2847 |
| `update_event_signature_theme` | 2887 |
| `get_theme_signatures` | 2918 |
| `_row_to_event_signature` | 3060 |

#### `user_repo.py` — UserRepository (12 methods)

| Method | Line |
|--------|------|
| `_row_to_user` | 3340 |
| `_row_to_user_with_password` | 3357 |
| `get_user_by_email` | 3375 |
| `get_user_by_id` | 3388 |
| `get_users` | 3401 |
| `create_user` | 3443 |
| `update_user` | 3462 |
| `deactivate_user` | 3499 |
| `reset_user_password` | 3513 |
| `set_user_not_new` | 3527 |
| `record_failed_login` | 3543 |
| `record_successful_login` | 3566 |

#### `auth_repo.py` — AuthRepository (4 methods)

| Method | Line |
|--------|------|
| `blacklist_token` | 3581 |
| `is_token_blacklisted` | 3592 |
| `cleanup_expired_blacklist` | 3600 |
| `log_auth_event` | 3612 |

#### `audit_repo.py` — AuditRepository (4 methods)

| Method | Line |
|--------|------|
| `insert_generation_audit` | 3081 |
| `insert_llm_usage_log` | 3147 |
| `insert_fact_check_scan` | 3203 |
| `get_latest_scan` | 3265 |

### Caller Mapping

| Handler/Service File | DB Methods Called | Target Repos |
|---------------------|------------------|-------------|
| `articles_api.py` | `get_articles_with_urgency`, `get_article_by_id`, `get_categories_filtered`, `get_all_tags_filtered`, `get_all_tags`, `get_trending_tags` | `articles` |
| `sources_api.py` | `get_all_sources`, `get_source_by_id`, `create_source`, `update_source`, `delete_source` | `sources` |
| `auth_api.py` | `get_user_by_email`, `get_user_by_id`, `get_users`, `create_user`, `update_user`, `deactivate_user`, `reset_user_password`, `set_user_not_new`, `record_failed_login`, `record_successful_login`, `blacklist_token`, `is_token_blacklisted`, `log_auth_event` | `users` + `auth` |
| `user_articles_api.py` | `get_user_articles`, `get_user_article_by_id`, `create_user_article`, `update_user_article`, `delete_user_article` | `articles` |
| `rss_collector.py` | `test_connection`, `delete_old_articles`, `get_sources_to_fetch`, `insert_articles_returning`, `update_source_last_fetch`, `log_collection` | `sources` + `articles` |
| `embedding_generator.py` | `get_articles_without_embedding`, `save_article_embedding`, `save_article_embeddings_batch`, `mark_article_has_embedding` | `embeddings` |
| `generation_api.py` | `insert_generation_audit`, `get_articles_with_urgency` | `audit` + `articles` |
| `fact_check_scan_api.py` | `get_latest_scan`, `insert_fact_check_scan` | `audit` |
| `clustering_service.py` | `get_all_themes`, `create_theme`, `add_article_to_theme`, `get_theme`, `update_theme`, `get_theme_article_scores` | `themes` + `scoring` |
| `llm_service.py` | `insert_llm_usage_log` | `audit` |
| `utils/auth.py` | `is_token_blacklisted` | `auth` |

### Migration Order (One Repo at a Time)

| Step | Repo | Methods | Risk | Verification |
|------|------|---------|------|-------------|
| 0 | Create `repos/` dir + `base.py` | 0 | None | No callers affected |
| 1 | `source_repo.py` | 9 | **Lowest** | `GET/POST /api/sources`, RSS collector |
| 2 | `embedding_repo.py` | 5 | Low | Embedding timer trigger |
| 3 | `scoring_repo.py` | 5 | Low | Scoring timer, clustering |
| 4 | `auth_repo.py` | 4 | Low | Login/logout flow |
| 5 | `user_repo.py` | 12 | Medium | Full auth flow, user CRUD |
| 6 | `audit_repo.py` | 4 | Medium | Generation, LLM logging |
| 7 | `event_repo.py` | 8 | Medium | Clustering, event matching |
| 8 | `theme_repo.py` | 13 | Higher | Theme endpoints, clustering |
| 9 | `article_repo.py` | 27 | **Highest** | All article endpoints, RSS |
| 10 | Clean up `database.py` | — | None | Run full test suite |

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Import circular dependencies | HIGH | Models in `models/` never import from `services/` — verified |
| `self.db` refs in clustering/event services | MEDIUM | Facade delegation handles transparently |
| Raw SQL via `db.get_connection()` (10 call sites) | MEDIUM | `get_connection()` stays on DatabaseService |
| `generation_api.py` creates `DatabaseService()` directly | LOW | Facade works on any instance |

### Result

| Metric | Before | After |
|--------|--------|-------|
| `database.py` lines | 3,648 | ~250 |
| Number of files | 1 | 12 |
| Largest repo | N/A | `article_repo.py` (~600 lines) |
| Breaking changes | N/A | **Zero** |
| Callers needing update | N/A | **Zero** (Phase 1) |

---

## P1-5: Enable Anthropic Prompt Caching

### Problem

~4,000 tokens of identical system prompt sent on every LLM call. No prompt caching enabled. Wasted input tokens.

### LLM Call Inventory

| # | Task Type | System Prompt Size | Model | Cacheable? |
|---|-----------|-------------------|-------|-----------|
| 1 | `article_generation` | ~3,500-4,500 tokens | Sonnet | **YES — highest value** |
| 2 | `topic_extraction` | ~30 tokens | Sonnet | No (too short) |
| 3 | `tag_generation` | ~20 tokens | Sonnet | No (too short) |
| 4 | `story_fusion` | ~500 tokens | Sonnet | Maybe (near minimum) |
| 5 | `article_edit` | ~500-700 tokens | Sonnet | Maybe |
| 6 | `classification` | ~300 tokens | Haiku | No (below 2,048 min for Haiku) |
| 7 | `scoring` | ~500 tokens | Haiku | No (below 2,048 min for Haiku) |
| 8 | `theme_naming` | ~50 tokens | Haiku | No (too short) |
| 9 | `event_extraction` | ~200 tokens | Sonnet | No (too short) |
| 10 | `event_verification` | ~200 tokens | Sonnet | No (too short) |
| 11-15 | fact-check sub-tasks | ~20-1,200 tokens | Sonnet | #13 maybe (claim extraction) |
| 16-18 | article_safety scans | ~250-300 tokens | Sonnet | No (below 1,024 min for Sonnet) |

**Key insight:** Biggest savings come from call #1 (article generation) — ~4,000 tokens of system prompt sent identically on every generation call.

### Implementation

#### Step 1: Modify `_call_api` (llm_service.py:1954)

Add `cache_system: bool = False` parameter:

```python
async def _call_api(self, system, user_content, max_tokens=MAX_TOKENS,
                    correlation_id="", model="", task_type="",
                    cache_system=False):
    # ...
    if cache_system and not self.use_azure:
        if isinstance(system, str):
            system_payload = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        else:
            system_payload = system  # Already structured
    else:
        system_payload = system  # Plain string (Azure or no caching)
```

#### Step 2: Parse cache usage from response (llm_service.py:2087)

```python
usage = result.get("usage", {})
input_tokens = usage.get("input_tokens", 0)
output_tokens = usage.get("output_tokens", 0)
cache_creation_input_tokens = usage.get("cache_creation_input_tokens", 0)
cache_read_input_tokens = usage.get("cache_read_input_tokens", 0)
```

#### Step 3: Update cost calculation (llm_service.py:2092)

```python
cache_read_cost = cache_read_input_tokens * (input_rate * 0.1)
cache_creation_cost = cache_creation_input_tokens * (input_rate * 1.25)
input_cost = input_tokens * input_rate + cache_read_cost + cache_creation_cost
```

#### Step 4: Enable at call sites (priority order)

1. **Article generation** (`llm_service.py:2221`): `cache_system=True`
2. **Story fusion** (`llm_service.py:2486`): `cache_system=True`
3. **Article edit** (`llm_service.py:2606`): `cache_system=True`
4. **Claim extraction** (`fact_check_service.py:1510`): Requires prompt refactoring to split static rules from dynamic preamble

#### Step 5 (Advanced): Multi-block system prompt for article generation

```python
def _build_category_prompt_blocks(categoria, tom, tipo_materia, ...):
    # Block 1: Universal rules (static, ~3,000 tokens) — CACHED
    static_block = {
        "type": "text",
        "text": TMC_GENERAL_GUIDELINES + ANTI_FABRICACAO_UNIVERSAL + ...,
        "cache_control": {"type": "ephemeral"}
    }
    # Block 2: Category-specific (dynamic, ~500 tokens) — NOT cached
    dynamic_block = {
        "type": "text",
        "text": f"## CATEGORIA: {cat_info['name']}\n..."
    }
    return [static_block, dynamic_block]
```

### Provider Compatibility

| Provider | Caching Support | Notes |
|----------|----------------|-------|
| Anthropic Direct | **Full support** | GA since late 2024 |
| Azure AI Proxy | **No support** | Strips `cache_control` fields |
| Haiku (always via Anthropic) | Partial | 2,048-token minimum (most prompts too short) |

**Guard:** When `self.use_azure == True` and no `ANTHROPIC_API_KEY`, caching is unavailable — code degrades gracefully (sends plain string, no `cache_control`).

### Expected Savings

| Metric | Value |
|--------|-------|
| Per-generation savings (cache hit) | $0.0108 (90% on system prompt) |
| Monthly savings (~100 gen/day, 60% hit rate) | ~$20-30/month |
| Latency improvement | ~100-200ms faster TTFT |
| Break-even | 2 calls within 5-minute cache TTL |

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Azure AI proxy rejects structured `system` array | Medium | Guard with `self.use_azure` check |
| Haiku min threshold (2,048 tokens) | Medium | Only enable for Sonnet calls |
| Cache writes cost 25% more on first call | Low | Break-even at 2 calls within 5 min |
| Breaking existing test mocks | Low | `cache_system=False` default is backward-compatible |

### Files to Change

| File | Change |
|------|--------|
| `services/llm_service.py` | `_call_api` payload, cost calc, logging |
| `services/config.py` | Add `prompt_caching_enabled: bool = True` |
| `services/fact_check_service.py` | Optional: split claim_extraction prompt |

---

## P1-6: Implement Refresh Token Rotation

### Problem

When a refresh token is used, a new access token is issued but the SAME refresh token stays valid. If stolen, attacker has persistent access for 7-30 days.

### Current Auth Flow

1. Login → access token (60min, in JSON body) + refresh token (7d, httpOnly cookie)
2. Refresh → new access token only; **old refresh token stays valid**
3. Logout → blacklists both tokens, clears cookie

### New Rotation Flow

On every successful refresh:
1. **Blacklist** the old refresh token `jti` (with `replaced_at` timestamp)
2. **Issue** a new refresh token (new `jti`, same `token_family`)
3. **Set** new refresh token as cookie in response
4. Return new access token in JSON body

### Race Condition Strategy: 30-Second Grace Period

| Scenario | Detection | Action |
|----------|-----------|--------|
| Two tabs refresh within 30s | Blacklisted + `replaced_at` < 30s | Treat as benign race, re-issue tokens |
| Token reuse after 30s | Blacklisted + `replaced_at` > 30s | **Compromise detected** — revoke entire family |
| Logout | Blacklisted + no `replaced_at` | Normal rejection |

**Why not rely on frontend singleton?** `_refreshPromise` in `api.js` only deduplicates within a single tab. Two tabs = two independent JavaScript contexts.

### Database Migration: `015_refresh_token_rotation.sql`

```sql
-- Add token_family column
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('token_blacklist') AND name = 'token_family'
)
BEGIN
    ALTER TABLE token_blacklist ADD token_family VARCHAR(64) NULL;
    CREATE INDEX IX_token_blacklist_family ON token_blacklist (token_family);
END

-- Add replaced_at column (NULL = revoked by logout, not rotation)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('token_blacklist') AND name = 'replaced_at'
)
BEGIN
    ALTER TABLE token_blacklist ADD replaced_at DATETIME2 NULL;
END

-- Add replaced_by_jti column
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('token_blacklist') AND name = 'replaced_by_jti'
)
BEGIN
    ALTER TABLE token_blacklist ADD replaced_by_jti VARCHAR(64) NULL;
END
```

### Backend Code Changes

#### 1. `services/auth_service.py` — Add `token_family` to refresh tokens

```python
def create_refresh_token(user_id: str, remember_me: bool = False, token_family: str = None) -> str:
    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=days),
        "type": "refresh",
        "family": token_family or str(uuid.uuid4()),  # new family at login
    }
    return jwt.encode(payload, config.jwt_secret_key, algorithm="HS256")
```

#### 2. `services/database.py` — Add 4 new methods

```python
def blacklist_token_rotated(self, jti, user_id, expires_at, token_family, replaced_by_jti):
    """Blacklist a refresh token due to rotation."""

def get_blacklisted_token_info(self, jti) -> Optional[dict]:
    """Get blacklist entry details for reuse detection."""

def blacklist_token_family(self, token_family, user_id) -> int:
    """Blacklist ALL tokens in a family (compromise detected)."""

def is_family_revoked(self, token_family) -> bool:
    """Check if an entire token family has been revoked."""
```

#### 3. `functions/auth_api.py` — Rewrite `refresh_handler`

The new handler:
1. Reads refresh token from cookie
2. Decodes and validates JWT
3. **Reuse detection**: If token blacklisted, check grace period
   - Within 30s → benign race, re-issue
   - After 30s → **compromise**, revoke family, force re-login
4. **Family revocation check**: If family is revoked, reject
5. Issue new access token + new refresh token (with same `token_family`)
6. Blacklist old refresh token with `replaced_at` timestamp
7. Set new refresh token cookie

#### 4. `functions/auth_api.py` — Update `logout_handler`

Add family revocation on logout:
```python
if payload and payload.get("family"):
    db.blacklist_token_family(payload["family"], req.user["id"])
```

### Frontend Impact

**Zero frontend changes needed.**

- `auth.js` `authRefresh()` reads `data.access_token` from JSON — unchanged
- Browser automatically replaces cookie (same domain, same path, same name)
- `_refreshPromise` singleton continues deduplicating within-tab refreshes
- 401 → `_onUnauthorized` → clear state → re-login still works

### Deployment Order (Zero-Downtime)

1. **Run migration 015** — nullable columns, existing rows unaffected
2. **Deploy backend** — new `refresh_handler` backward-compatible (old tokens lack `family` claim, handled as `None`)
3. **No frontend deploy** needed
4. **Monitor** `auth_audit_log` for `token_reuse_detected` events

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Race condition causes logout | Medium | High (UX) | 30s grace period + frontend `_refreshPromise` dedup |
| Grace period too long | Low | Medium | 30s is short; attacker must use within 30s of legitimate refresh |
| Old tokens without `family` claim | Certain (transitional) | None | Code handles `None` gracefully — rotation works, family detection disabled |
| Blacklist table grows faster | Low | Low | `cleanup_expired_blacklist` already runs; rows expire with token |
| Cookie not replaced by browser | Very Low | High | Same domain/path/name — browser spec guarantees replacement |

### Files to Change

| File | Change |
|------|--------|
| `migrations/015_refresh_token_rotation.sql` | **New**: 3 columns on `token_blacklist` |
| `services/auth_service.py` | Add `token_family` param + `"family"` claim |
| `services/database.py` | Add 4 new methods for rotation-aware blacklisting |
| `functions/auth_api.py` | Rewrite `refresh_handler`, update `logout_handler` |

---

## P1-7: Add Staging Environment

### Problem

Changes go directly to production. For a newsroom tool with safety gates, this is risky.

### Recommended Architecture

| Component | Staging Solution | Cost |
|-----------|-----------------|------|
| **Backend** | Separate Function App (`tmc-redacao-api-staging`) on Consumption plan | ~$0-2/mo |
| **Frontend** | Azure SWA Preview Environments (already working) | Free |
| **Database** | Separate `tmc-staging` DB on same SQL Server, Basic tier (5 DTU) | ~$5/mo |
| **Total** | | **~$5-7/mo** |

**Why not deployment slots?** Current Consumption plan doesn't support slots. B1 upgrade costs $13/mo — wasteful for pre-revenue product.

### Azure Resources to Create

| Resource | Name | SKU |
|----------|------|-----|
| Function App | `tmc-redacao-api-staging` | Consumption (Y1) |
| SQL Database | `tmc-staging` (on existing SQL Server) | Basic (5 DTU) |
| Application Insights | Reuse existing | — |

### Environment Variable Configuration

**Staging Function App settings:**

| Setting | Staging Value |
|---------|---------------|
| `TMC_ENVIRONMENT` | `staging` |
| `PRODUCTION_SAFETY_MODE` | `true` |
| `SQL_DATABASE` | `tmc-staging` |
| `SQL_USERNAME` | `tmc_staging_user` |
| `SQL_PASSWORD` | (generate new) |
| `JWT_SECRET_KEY` | (generate new, 32+ chars) |
| `ANTHROPIC_API_KEY` | Same as prod |
| `AZURE_OPENAI_API_KEY` | Same as prod |
| `EXA_API_KEY` | Same as prod |
| `CORS_ALLOWED_ORIGINS` | `*` (staging-only, not public) |

**Disable timer triggers in staging:**

| Setting | Value |
|---------|-------|
| `AzureWebJobs.rss_collector.Disabled` | `true` |
| `AzureWebJobs.embedding_generator.Disabled` | `true` |
| `AzureWebJobs.scoring_calculator.Disabled` | `true` |
| `AzureWebJobs.clustering_engine.Disabled` | `true` |
| `AzureWebJobs.clustering_maintenance.Disabled` | `true` |

### Backend Code Change

Add `TMC_ENVIRONMENT` to `config.py`:

```python
# In AppConfig dataclass
environment: str = "production"  # "production" | "staging" | "development"

# In load_config()
environment=os.environ.get("TMC_ENVIRONMENT", "production"),
```

### CI/CD Workflow Changes

#### Backend (`backend-deploy.yml`) — Add `deploy-staging` job

```yaml
deploy-staging:
  name: Deploy to Staging
  needs: test
  if: github.event_name == 'pull_request'
  runs-on: ubuntu-latest
  environment: staging
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.11' }
    - run: pip install -r requirements.txt --target=".python_packages/lib/site-packages"
      working-directory: FeedRSS/tmc-rss-collector
    - uses: Azure/functions-action@v1
      with:
        app-name: 'tmc-redacao-api-staging'
        package: 'FeedRSS/tmc-rss-collector'
        publish-profile: ${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE_STAGING }}
    - name: Health check
      run: |
        sleep 30
        for i in 1 2 3; do
          STATUS=$(curl -s -o /dev/null -w '%{http_code}' "https://tmc-redacao-api-staging.azurewebsites.net/api/health")
          [ "$STATUS" = "200" ] && exit 0
          sleep 15
        done
        exit 1
```

#### Frontend (SWA workflow) — Conditional API URL for PR builds

```yaml
env:
  VITE_API_BASE_URL: ${{ github.event_name == 'pull_request' && 'https://tmc-redacao-api-staging.azurewebsites.net/api' || 'https://tmc-redacao-api-b7h3dyaxazfvdcez.eastus2-01.azurewebsites.net/api' }}
```

### Frontend CSP Change

Add staging backend URL to `connect-src` in `staticwebapp.config.json`:
```
connect-src: ... https://tmc-redacao-api-staging.azurewebsites.net ...
```

### Database Setup

1. Create `tmc-staging` DB on existing SQL Server
2. Create `tmc_staging_user` login with db_owner on `tmc-staging`
3. Run all 14 migrations: `python scripts/run_migrations.py` (with staging env vars)
4. Run `python scripts/seed_admin.py` for test admin user

### Testing Workflow

```
Developer creates PR
  → CI runs tests
  → Backend deploys to staging Function App
  → Frontend deploys to SWA preview (pointing at staging API)
  → Developer tests manually via preview URL
  → PR approved and merged to main
  → CI deploys to production (both frontend and backend)
```

### GitHub Setup Required

| Item | Action |
|------|--------|
| Secret: `AZURE_FUNCTIONAPP_PUBLISH_PROFILE_STAGING` | Download from Azure Portal for staging FA |
| Environment: `staging` | Create in GitHub Settings (no approval gates) |

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Timer triggers run in staging | High | Disable all 5 via `AzureWebJobs.*.Disabled=true` |
| LLM costs double if staging used heavily | Medium | Staging only used during active testing |
| CSP blocks staging API from preview frontend | Medium | Add staging URL to `connect-src` before first use |
| Staging DB accumulates stale data | Low | Drop/recreate monthly, or add cleanup script |

### Implementation Sequence

1. Create Azure resources (Function App + SQL DB) — 30 min
2. Configure staging app settings + disable timers — 15 min
3. Run migrations + seed staging DB — 10 min
4. Add `TMC_ENVIRONMENT` to `config.py` — 5 min
5. Update `staticwebapp.config.json` CSP — 5 min
6. Update `backend-deploy.yml` + add secret — 20 min
7. Update SWA workflow with conditional API URL — 10 min
8. Create GitHub `staging` environment — 5 min
9. Test end-to-end with a test PR — 30 min

**Total: ~2-3 hours**

---

## Implementation Timeline

| Week | Day | Task | Effort |
|------|-----|------|--------|
| 1 | Mon | **P1-5**: Prompt caching (Steps 1-4 in `_call_api`) | 1-2h |
| 1 | Mon | **P1-5**: Enable on article generation + story fusion | 30min |
| 1 | Tue | **P1-6**: Migration 015 + auth_service.py changes | 1h |
| 1 | Tue | **P1-6**: database.py new methods + refresh_handler rewrite | 2h |
| 1 | Wed | **P1-7**: Create Azure resources + configure staging | 1h |
| 1 | Wed | **P1-7**: CI/CD workflows + CSP + config.py | 1h |
| 1 | Wed | **P1-7**: End-to-end staging test | 30min |
| 2 | Mon-Tue | **P1-4**: Steps 0-4 (repos dir, source, embedding, scoring, auth) | 2-3h |
| 2 | Wed-Thu | **P1-4**: Steps 5-8 (user, audit, event, theme repos) | 2-3h |
| 2 | Fri | **P1-4**: Step 9 (article repo) + Step 10 (cleanup) | 2h |

**Total: ~14-18 hours across 2 weeks**

---

## Pre-Implementation Checklist

- [ ] Verify current tests pass: `cd FeedRSS/tmc-rss-collector && python -m pytest tests/ -v`
- [ ] Confirm Azure Functions publish profile is accessible
- [ ] Confirm `ANTHROPIC_API_KEY` is set (for prompt caching to work)
- [ ] Take baseline of current `GET /api/health` response
- [ ] Create branch: `git checkout -b feat/p1-production-hardening`
