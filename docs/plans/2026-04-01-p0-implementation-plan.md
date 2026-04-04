# P0 Implementation Plan — April 2026 (Merged + Agentic Playbook)

> Synthesized from 8 parallel research agents across 2 terminals: codebase exploration (text quality, performance, auth) + Exa SOTA research (anti-hallucination, search perf, session auth, agentic orchestration patterns).

---

## Execution Order (Dependency-Optimized)

```
Phase 1: Session Persistence ──> Phase 2: Search/Filter Performance ──> Phase 3: Text Quality ──> Phase 4: Fact-Check Accuracy
   (1 session)                      (2-3 sessions)                        (2-3 sessions)            (2 sessions)
```

**Why this order:**
1. **Session** first — every other fix is untestable if users get logged out on refresh
2. **Performance** second — users need working search/filters to evaluate quality fixes
3. **Text Quality** third — generation pipeline must be stable before modifying downstream verification
4. **Fact-Check** last — depends on generation pipeline changes from Phase 3

**Total: 7-9 SDD sessions (~3 days focused solo dev)**

---

## Agentic Execution Playbook

### Core Workflow: SDD + GSD Hybrid

Each phase follows the proven 5-step loop validated by both SDD methodology and 2026 Exa research:

```
/specify ──> /plan ──> /breakdown ──> Parallel Subagent Implementation ──> Review Gate ──> Ship
  (human)    (opus)     (opus)        (sonnet subagents × N)                (opus + human)
```

**Model allocation:**
- Main orchestrator session: **Opus** (planning, review synthesis, quality judgment)
- Implementation subagents: **Sonnet** (fast, cheap, great at focused coding tasks)
- Quick tasks (migrations, config): **Haiku** via `/gsd:fast` (no overhead)

### Subagent Team Structure Per Phase

Each phase spawns a specialized team following the **implement → review → test** triangle:

```
                    ┌──────────────┐
                    │  Orchestrator │  (this session - Opus)
                    │  /gsd:execute │
                    └──────┬───────┘
                           │ dispatches
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Coder    │ │ Coder    │ │ Coder    │   (parallel Sonnet agents)
        │ Agent A  │ │ Agent B  │ │ Agent C  │   (each handles 1 task)
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │             │             │
             └──────┬──────┴──────┬──────┘
                    ▼             ▼
              ┌──────────┐ ┌──────────┐
              │ Reviewer │ │ Tester   │   (sequential after all coders finish)
              │ Agent    │ │ Agent    │
              └──────────┘ └──────────┘
                    │             │
                    ▼             ▼
              ┌──────────────────────┐
              │  Human Review (diff) │   (you approve/iterate)
              └──────────────────────┘
```

### Skills & Slash Commands Per Step

| Step | Skill/Command | Purpose |
|------|---------------|---------|
| **Specify** | Manual / `/gsd:discuss-phase` | Gather phase context, clarify requirements |
| **Plan** | `/gsd:plan-phase` | Create PLAN.md with task breakdown, deps, verification criteria |
| **Breakdown** | `/gsd:plan-phase` (built-in) | Atomic ~15min tasks with clear entry/exit criteria |
| **Implement** | `superpowers:dispatching-parallel-agents` | Fan-out independent tasks to parallel Sonnet subagents |
| **Review** | `superpowers:requesting-code-review` | AI code review of all changes against the plan |
| **Test** | `superpowers:test-driven-development` | TDD for new functions; audit scripts for pipeline changes |
| **Verify** | `superpowers:verification-before-completion` | Run build+lint+tests, confirm output before claiming done |
| **Debug** | `superpowers:systematic-debugging` | If any step fails, structured root cause analysis |
| **Ship** | `/gsd:ship` | Create PR, run review, prepare for merge |

### Invocation Quality Protocol

Every subagent dispatch MUST include (per Exa research — #1 cause of subagent failure is vague invocations):

```
1. SPECIFIC FILES with line numbers (not "fix the auth")
2. CURRENT BEHAVIOR description (what happens now)
3. DESIRED BEHAVIOR description (what should happen)
4. SUCCESS CRITERIA (how to verify the fix works)
5. CONSTRAINTS (don't touch X, preserve Y, max N lines changed)
```

### Three Verification Gates (Non-Negotiable)

Every phase passes through all 3 gates before shipping:

| Gate | What | Who | Blocks On |
|------|------|-----|-----------|
| **Gate 1: Automated** | `npm run lint` + `npm run build` (frontend), `pytest tests/` (backend) | CI/scripts | Any failure |
| **Gate 2: AI Review** | Reviewer subagent checks diff against plan + CLAUDE.md conventions | Sonnet agent | Deviations from spec, missed edge cases, security issues |
| **Gate 3: Human Review** | You review `git diff`, approve or iterate | Human | Business logic, UX judgment |

---

## Phase 1: Session Persistence (P0-Sessao)

### Root Cause (confirmed by codebase exploration)
- Access token stored in **JS memory** (`_accessToken` variable in `auth.js`) — lost on page refresh
- `AuthContext.jsx:39` calls `tryRefresh()` on mount, which works IF cookies are sent
- **Critical**: `CORS_ALLOWED_ORIGINS` env var may be empty in production → browser blocks credentials → cookie not sent → refresh fails → redirect to login
- Commit `6777fb7` fixed CORS header mutation dropping `Set-Cookie`, but origin list still needs verification
- Cookie set with `Path=/api/auth; SameSite=None; Secure` but no explicit `Domain=`

### Agentic Execution

**Workflow**: `/gsd:fast` — Single session, no subagents needed (4 small focused tasks)

**Skills sequence**:
1. `superpowers:systematic-debugging` → Diagnose exact failure point (is CORS_ALLOWED_ORIGINS set? Does cookie transmit?)
2. `superpowers:test-driven-development` → Write test for refresh-on-mount flow before fixing
3. `superpowers:verification-before-completion` → Verify with browser DevTools

**No parallel agents** — tasks are sequential (1.1 → 1.2 → 1.3 → 1.4) because each depends on the previous.

### Implementation Tasks

#### Task 1.1: Verify and fix CORS_ALLOWED_ORIGINS in Azure
- **Where**: Azure Function App Settings (production environment)
- **Action**: Ensure `CORS_ALLOWED_ORIGINS=https://purple-river-09235a310.3.azurestaticapps.net` is set
- **Verify**: `config.py:171` — `os.environ.get("CORS_ALLOWED_ORIGINS", "")` returns non-empty

#### Task 1.2: Harden the refresh-on-mount flow
- **File**: `tmc-redacao/src/context/AuthContext.jsx` (lines 37-59)
- **Action**: 
  - Add retry (1 retry, 1s delay) before clearing auth state
  - Add console.error logging for refresh failures
  - Ensure loading spinner shows while `tryRefresh()` is in-flight

#### Task 1.3: Add request queue for concurrent 401 handling
- **File**: `tmc-redacao/src/services/api.js` (lines 94-122)
- **Action**: Implement `isRefreshing` flag + `failedQueue` pattern:
  ```
  401 → if already refreshing → queue request → replay on success
       → if not refreshing → start refresh → queue subsequent 401s
       → on refresh failure → redirect to login ONCE (not per request)
  ```

#### Task 1.4: Verify cookie Domain directive
- **File**: `FeedRSS/tmc-rss-collector/functions/auth_api.py` (lines 137-141)
- **Action**: Add explicit `Domain` attribute if frontend/API are on different subdomains
- **Current**: `Path=/api/auth; Max-Age={max_age}` — no Domain specified

### Verification Checklist
- [ ] Clear all cookies, login fresh
- [ ] DevTools > Application > Cookies → verify `refresh_token` exists
- [ ] F5 refresh → `/api/auth/refresh` request includes Cookie header
- [ ] No redirect to login after refresh
- [ ] Open 3 tabs simultaneously → no race condition logout

---

## Phase 2: Search/Filter Performance (P0-Performance)

### Root Causes (confirmed)

| Problem | Root Cause | File:Line |
|---------|-----------|-----------|
| Compound word search freezes | `LIKE '%term%'` on 3 unindexed columns (5 LIKE conditions per search, full table scan) | `database.py:495-517` |
| Score filter slow | Missing composite index for "All scores" view without classification | `migrations/013:25-28` |
| Costs page slow | 11 sequential SQL queries within 6 functions + missing `created_at` indexes + `CAST()` on JOIN kills index | `cost_queries.py:127-182,333` |
| General filters degraded | Facet cache invalidates on every keystroke (keyed on all 6 filter params) + unindexed LIKE on tags | `articles_api.py:105-110`, `database.py:1210-1276` |

### Agentic Execution

**Workflow**: `/gsd:plan-phase` → `/gsd:execute-phase` (2-3 sessions)

**Skills sequence**:
1. `/gsd:discuss-phase` → Confirm scope, identify any blockers
2. `superpowers:dispatching-parallel-agents` → Fan-out 3 independent tracks
3. `superpowers:requesting-code-review` → AI review of all changes
4. `superpowers:verification-before-completion` → Run performance benchmarks

**Parallel subagent dispatch** (3 independent tracks):

```
Track A (DBA Agent - Backend):              Track B (Query Agent - Backend):           Track C (Frontend Agent):
  Task 2.1: Full-text index migration         Task 2.2: Replace LIKE with FREETEXT       Task 2.6: AbortController + debounce
  Task 2.3: Cost/score index migration        Task 2.4: Fix CAST on JOIN                 (FilterBar.jsx, api.js)
  (new SQL migration files)                   Task 2.5: Decouple facet cache
                                              (database.py, cost_queries.py,
                                               articles_api.py)
```

**After all 3 tracks complete → sequential**:
- Reviewer Agent: cross-check migrations + queries + frontend for consistency
- Tester Agent: run performance benchmarks (`SET STATISTICS IO ON`, time API calls)

### Implementation Tasks

#### Task 2.1: Create Azure SQL Full-Text Index (Portuguese)
- **File**: New `migrations/014_fulltext_search.sql`
- **SQL**:
  ```sql
  CREATE FULLTEXT CATALOG ArticleCatalog AS DEFAULT;
  CREATE FULLTEXT INDEX ON collected_articles (title LANGUAGE 1046, preview LANGUAGE 1046, tags LANGUAGE 1046)
  KEY INDEX PK_collected_articles;
  ```
  - Language 1046 = Brazilian Portuguese (native word breaker handles compound words)
  - Run during low-traffic window (3AM UTC)

#### Task 2.2: Replace LIKE queries with FREETEXT
- **File**: `services/database.py` (lines 495-517)
- **Action**: Replace 5 LIKE conditions with single FREETEXT predicate:
  ```python
  # OLD: 5 LIKE '%term%' conditions (full table scan)
  # NEW: Single FREETEXT predicate (full-text index seek)
  conditions.append("FREETEXT((a.title, a.preview, a.tags), %s)")
  params.append(search)
  ```

#### Task 2.3: Add missing performance indexes
- **File**: New `migrations/015_cost_performance_indexes.sql`
- **SQL**:
  ```sql
  -- Cost page date filtering
  CREATE NONCLUSTERED INDEX IX_llm_usage_created 
  ON llm_usage_log(created_at) 
  INCLUDE(model, task_type, input_tokens, output_tokens, cost_usd, user_id);
  
  -- Score filter without classification  
  CREATE NONCLUSTERED INDEX IX_articles_score_only 
  ON collected_articles(total_score DESC, published_at DESC) 
  WHERE is_deleted = 0 AND total_score IS NOT NULL;
  ```

#### Task 2.4: Fix CAST on JOIN in cost_by_user
- **File**: `services/cost_queries.py` (line 333)
- **Action**: Remove `CAST()` on both sides — ensure column types match natively

#### Task 2.5: Decouple facet cache from search query
- **File**: `functions/articles_api.py` (lines 102-168)
- **Action**: Cache facets independently with 5-min TTL, regardless of search/filter params

#### Task 2.6: Frontend search optimization
- **Files**: `FilterBar.jsx`, `api.js`
- **Action**:
  - Add `AbortController` to cancel in-flight search requests on new input
  - Increase search debounce to 500ms (currently 300ms)
  - Add request deduplication for identical in-flight queries

### Verification Checklist
- [ ] "selecao brasileira" returns results in <2s (was timing out)
- [ ] Score filter A/B/C/All responds in <1s
- [ ] Costs page loads in <3s (was 5-6s+)
- [ ] Typing in search doesn't freeze UI
- [ ] `SET STATISTICS IO ON` confirms index seeks, not table scans

---

## Phase 3: Text Quality (P0-Qualidade)

### Root Causes (confirmed)

| Problem | Root Cause | File:Line |
|---------|-----------|-----------|
| Text copies original | NO post-generation similarity check; raw source text injected directly into prompt | `llm_service.py:1718-1725` |
| Competitor mentions | ZERO filtering logic anywhere in entire pipeline | `llm_service.py` (absent) |
| Fabricated data | Claim extraction fails silently (0 claims → passes with confidence 0.35); unverifiable claims not auto-removed; quality loop lacks "text_copy" criterion | `fact_check_service.py:1239-1241`, `generation_api.py:414-545` |

### Agentic Execution

**Workflow**: `/gsd:plan-phase` → `/gsd:execute-phase` (2-3 sessions)

**Skills sequence**:
1. `/gsd:discuss-phase` → Align on extraction prompt design, competitor list, n-gram thresholds
2. `superpowers:test-driven-development` → Write 10-article audit test BEFORE implementing
3. `superpowers:dispatching-parallel-agents` → Fan-out 2 independent tracks
4. `superpowers:requesting-code-review` → AI review of prompt changes + new functions
5. `superpowers:verification-before-completion` → Run 10-article audit, compare before/after

**Parallel subagent dispatch** (2 tracks):

```
Track A (Pipeline Agent - llm_service.py):      Track B (Safety Agent - fact_check + generation_api):
  Task 3.1: Extract-then-generate step            Task 3.2: N-gram overlap detection function
  Task 3.3: Competitor brand filtering             Task 3.4: Fix silent claim extraction failure
  Task 3.5: Anti-copy few-shot examples            (fact_check_service.py, generation_api.py)
  (llm_service.py, config.py)
```

**Critical: llm_service.py is 117KB and fact_check_service.py is 110KB — surgical edits only, NEVER rewrite wholesale.**

**After both tracks complete → sequential**:
- Reviewer Agent: verify prompt coherence (no contradictory instructions), check n-gram thresholds are reasonable
- Tester Agent: run `scripts/test_10_articles_audit.py` with new quality gates, compute n-gram overlap stats

### Implementation Tasks

#### Task 3.1: Add extract-then-generate pipeline step
- **File**: `services/llm_service.py` (around line 1718)
- **Action**: Before building user prompt, extract facts from source:
  1. Call Claude Haiku to extract ONLY factual claims/entities from source (cheap + fast)
  2. Build generation prompt from extracted facts, NOT raw source text
  3. Instruction: "Escreva baseado APENAS nos fatos verificados. NAO copie frases do material."
- **Why**: Removing raw source text eliminates ~80% of verbatim copying (Exa research: abstractive rewriting pipelines)
- **Cost**: ~$0.001 extra per article (Haiku extraction)

#### Task 3.2: Add post-generation n-gram overlap detection
- **File**: `services/llm_service.py` or `services/fact_check_service.py`
- **Action**: New function `check_originality(generated, source)`:
  - Compute 4-gram overlap between generated article and source text
  - Threshold: >15% overlap → flag as "high_copy"
  - Add "text_copy" criterion to quality loop in `generation_api.py:414-545`
  - Regenerate with stronger anti-copy instructions if threshold exceeded
- **Implementation**: Pure Python string processing, no external API needed
  ```python
  def check_originality(generated: str, source: str, n: int = 4, threshold: float = 0.15) -> dict:
      gen_ngrams = set(zip(*[generated.split()[i:] for i in range(n)]))
      src_ngrams = set(zip(*[source.split()[i:] for i in range(n)]))
      overlap = gen_ngrams & src_ngrams
      ratio = len(overlap) / max(len(gen_ngrams), 1)
      return {"overlap_ratio": ratio, "is_copy": ratio > threshold, "overlapping_phrases": len(overlap)}
  ```

#### Task 3.3: Add competitor brand filtering
- **File**: `services/llm_service.py` (system prompt ~line 1387) + `services/config.py`
- **Action**:
  - Add `COMPETITOR_BRANDS` env var (comma-separated list, editorial-maintained)
  - Prompt instruction: "NAO mencione estes veiculos pelo nome: [lista]. Use 'segundo apuracao'."
  - Post-generation scan: find competitor names in output, replace with generic references

#### Task 3.4: Fix silent claim extraction failure
- **File**: `services/fact_check_service.py` (lines 1239-1241)
- **Action**: When claim extraction returns 0 claims:
  - Retry extraction once with simplified prompt
  - If still 0: mark article as `needs_manual_review` (not auto-pass with 0.35 confidence)
  - Log warning with article ID

#### Task 3.5: Add anti-copy few-shot examples to generation prompt
- **File**: `services/llm_service.py` (prompt constants ~line 149)
- **Action**: New `ANTI_COPIA` constant with:
  - 2 examples of BAD output (copied passages) labeled "INACEITAVEL"
  - 2 examples of GOOD output (fully rewritten) labeled "CORRETO"
  - Hard rule: "Nunca use mais de 3 palavras consecutivas do material fonte"

### Verification Checklist
- [ ] Generate 10 test articles → all have <15% 4-gram overlap with sources
- [ ] Zero competitor brand names in generated output
- [ ] Quality loop triggers regen on high text similarity
- [ ] Claim extraction failure → article flagged for review, not auto-published
- [ ] Run `scripts/test_10_articles_audit.py` with new quality gates
- [ ] Compare before/after metrics (overlap ratio, competitor mentions, claim coverage)

---

## Phase 4: Fact-Check Accuracy (P0-FactCheck)

### Root Causes (confirmed)

| Problem | Root Cause | File:Line |
|---------|-----------|-----------|
| Doesn't recognize new info | Exa search uses global date range, no per-article temporal context | `fact_check_service.py:784-788` |
| | Claim classification is atemporal — no "recent vs background" distinction | `fact_check_service.py:1468-1577` |
| | CoVe has no temporal checks | `fact_check_service.py:2242-2343` |
| | Enrichment treats ALL Exa results equally | `fact_check_service.py:500-621` |

### Agentic Execution

**Workflow**: `/gsd:plan-phase` → `/gsd:execute-phase` (2 sessions)

**Skills sequence**:
1. `/gsd:discuss-phase` → Align on temporal thresholds (48h/7d), confidence adjustments
2. `superpowers:test-driven-development` → Write pipeline audit test with mix of old/new sources BEFORE implementing
3. `superpowers:dispatching-parallel-agents` → Fan-out 2 independent tracks
4. `superpowers:requesting-code-review` → AI review of temporal logic changes
5. `superpowers:verification-before-completion` → Full pipeline audit

**Parallel subagent dispatch** (2 tracks):

```
Track A (Temporal Agent - enrichment):           Track B (Verification Agent - claim pipeline):
  Task 4.1: Temporal classification for claims     Task 4.3: Internal cross-reference via embeddings
  Task 4.2: Date-scoped Exa queries               Task 4.4: Temporal awareness in CoVe
  (fact_check_service.py: enrichment section)      Task 4.5: Softer confidence for recent_unverifiable
                                                   (fact_check_service.py: verification section)
```

**Critical: fact_check_service.py is 110KB — surgical edits only. Both tracks edit the SAME file in different sections, so merge carefully.**

**After both tracks complete → sequential**:
- Reviewer Agent: verify no section conflicts in fact_check_service.py, check temporal thresholds are reasonable
- Tester Agent: run `scripts/full_pipeline_audit.py` with mix of breaking news + old sources

### Implementation Tasks

#### Task 4.1: Add temporal classification to claims
- **File**: `services/fact_check_service.py` (lines 1468-1577)
- **Action**: Extend claim extraction prompt with temporal field:
  ```
  Para cada claim, adicione "temporalidade":
  - "breaking": informacao nova das ultimas 48 horas
  - "recente": informacao dos ultimos 7 dias
  - "historico": contexto geral/antigo
  ```
- **Rollout**: Start logging-only (no behavior change), analyze distribution, then enable

#### Task 4.2: Date-scoped Exa enrichment queries
- **File**: `services/fact_check_service.py` (lines 710-721)
- **Action**:
  - Pass article's `published_at` to enrichment step
  - "breaking" claims: search only last 48h
  - "recent" claims: search last 7 days
  - "historical" claims: standard date range
  - Add recency boost: prioritize results closest to article date

#### Task 4.3: Internal cross-reference via existing embeddings
- **File**: `services/fact_check_service.py` (new method)
- **Action**: Before Exa search, query `article_embeddings` for semantically similar collected articles:
  - Embed the claim text
  - Query with cosine similarity > 0.7
  - If 3+ independent sources report same claim → boost grounding confidence
  - **Cost**: FREE (no API cost, uses existing embedding infrastructure)

#### Task 4.4: Add temporal awareness to CoVe
- **File**: `services/fact_check_service.py` (lines 2242-2343)
- **Action**: Add temporal question to CoVe Q&A:
  ```
  Pergunta adicional: "Quando este evento foi reportado? 
  A informacao e atual (ultimas 48h) ou contexto historico?"
  ```

#### Task 4.5: Soften confidence for "recent_unverifiable" claims
- **File**: `services/fact_check_service.py` (lines 2349-2497)
- **Action**: New verdict type `recent_unverifiable`:
  - Confidence weight: 0.7 (vs 0.35 for standard unverifiable)
  - Only applies when: source <48h old AND claim has supporting internal cross-reference
  - Prevents hard-blocking articles about genuinely breaking news

### Verification Checklist
- [ ] Generate article from breaking news source (<24h) → no false blocks
- [ ] Generate article from week-old source → standard verification applies
- [ ] Internal cross-reference finds matching articles in embeddings table
- [ ] CoVe correctly identifies breaking vs historical claims
- [ ] Full pipeline audit with mix of new and old sources

---

## Agentic Session Playbook (Copy-Paste for Each Phase)

### Session Start Protocol

```
1. Read this plan (the current phase section)
2. Read the specific files listed (exact line numbers)
3. git log --oneline -20 (check for recent changes)
4. Run baseline: pytest tests/ (backend) + npm run lint (frontend)
5. /gsd:discuss-phase --auto (gather context, skip interactive questions)
```

### Implementation Protocol (Per Task)

```
For each task in the phase:

1. READ the target file at the exact lines specified
2. WRITE a test that captures the desired behavior (TDD)
3. IMPLEMENT the change (surgical edit, not rewrite)
4. RUN lint + build to verify no breakage
5. COMMIT atomically: feat:/fix: with clear "why" message
```

### Review Protocol (After All Tasks)

```
1. git diff main...HEAD (full phase diff)
2. Spawn Reviewer Agent:
   - "Review this diff against Phase N of docs/plans/2026-04-01-p0-implementation-plan.md.
     Check: (a) all tasks completed, (b) no CLAUDE.md convention violations,
     (c) no security issues, (d) surgical edits only on large files"
3. Fix any issues found
4. Human reviews git diff, approves or iterates
```

### Test Protocol (After Review)

```
Phase 1 (Auth):     Manual browser test (DevTools → Network → Cookie inspection)
Phase 2 (Perf):     SET STATISTICS IO ON + time API responses + frontend Lighthouse
Phase 3 (Quality):  scripts/test_10_articles_audit.py + n-gram overlap report
Phase 4 (FactCheck): scripts/full_pipeline_audit.py with old/new source mix
```

### Quick Reference: Key Files Per Phase

| Phase | Primary Files | Read Lines | Agent Team Size |
|-------|--------------|------------|-----------------|
| 1 (Auth) | `auth_api.py`, `AuthContext.jsx`, `api.js` | 137-141, 37-59, 94-122 | 1 (sequential) |
| 2 (Perf) | `database.py`, `cost_queries.py`, `FilterBar.jsx` | 495-517, 127-182, 86-102 | 3 parallel tracks |
| 3 (Quality) | `llm_service.py`, `generation_api.py` | 1718-1745, 414-545 | 2 parallel tracks |
| 4 (FactCheck) | `fact_check_service.py` | 710-721, 784-788, 1468-1577, 2242-2343 | 2 parallel tracks (same file, different sections) |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Full-text index creation locks table | Run migration at 3AM UTC; use ONLINE=ON if supported |
| Extract-then-generate adds latency | Use Haiku for extraction (~$0.001/article), keep Sonnet for generation |
| Temporal claim classification incorrect | Start logging-only, analyze distribution over 24h, then enable enforcement |
| Competitor blocklist maintenance | Store in env var, not hardcoded; editorial team updates without deploy |
| Auth fix breaks existing sessions | Deploy during low traffic; existing refresh tokens remain valid |
| Both Phase 4 tracks edit same file | Use git worktrees or careful section isolation; reviewer checks for conflicts |
| Large file edits (117KB/110KB/131KB) | NEVER rewrite wholesale — surgical edits at specific lines only |

---

## Anti-Patterns to Avoid (From Exa Research)

| Anti-Pattern | Why It Fails | Do Instead |
|-------------|-------------|-----------|
| "Fix the auth" (vague subagent prompt) | Subagent explores randomly, wastes tokens | Specify exact file:line, current behavior, desired behavior |
| Rewriting large files wholesale | Creates merge conflicts, introduces regressions | Surgical Edit tool at specific line ranges |
| Running all 4 phases in one session | Context pollution after ~50k tokens | `/compact` between phases, new session for each phase |
| Skipping the review agent | Multi-agent without review produces WORSE code than single agent | Always run reviewer after implementation |
| Amending commits on failures | Destroys previous work if pre-commit hook fails | Always create NEW commits |
| Testing after all phases done | Late-found bugs cascade across phases | Test each phase independently before moving to next |

---

## Success Metrics

| P0 Issue | Current State | Target State | Measurement |
|----------|--------------|-------------|-------------|
| Session persistence | Logout on F5 | Stays logged in | Manual browser test |
| Compound word search | Timeout/freeze | <2s response | API response time |
| Score filter | 5-10s | <1s | API response time |
| Costs page | 5-6s+ | <3s | Page load time |
| Text copying | Verbatim passages in output | <15% 4-gram overlap | `check_originality()` |
| Competitor mentions | Present in output | Zero mentions | Post-generation scan |
| Fabricated data | Silent pass on 0 claims | Flagged for review | Audit log check |
| New info fact-check | False blocks on breaking news | Temporal-aware verification | Pipeline audit |

---

*Generated: 2026-04-01*  
*Research: 8 parallel agents across 2 terminals (5 codebase explorers + 3 Exa SOTA researchers)*  
*Methodology: SDD + GSD hybrid with 3-gate verification (automated → AI review → human review)*
