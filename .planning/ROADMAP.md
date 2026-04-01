# P0 Backlog Resolution - Roadmap

> 9 critical bugs across 4 phases, executed in dependency order.
> Source: `docs/plans/2026-04-01-p0-implementation-plan.md`

## Milestone: P0 April 2026

### Phase 1: Session Persistence
- **Goal:** Fix auth so users stay logged in after F5 refresh
- **Status:** COMPLETE (commits 020b028, 8ae94c8, c7d2d84)
- **Bugs:** P0-Sessao (session lost on page refresh)
- Canonical refs: `docs/plans/2026-04-01-p0-implementation-plan.md` section Phase 1

### Phase 2: Search/Filter Performance
- **Goal:** Fix LIKE query freezes, add missing indexes, optimize costs page, fix facet cache thrashing
- **Status:** PLANNED
- **Bugs:** P0-Performance (compound search freezes, score filter slow, costs page slow, general filter degradation)
- **Tracks:** 3 parallel (DBA migrations, query optimization, frontend abort/debounce)
- **Plans:** 3 plans (all Wave 1 — parallel)

Plans:
- [ ] 02-PLAN-A-dba-migrations.md — SQL migrations for full-text index (021) + performance indexes (022)
- [ ] 02-PLAN-B-query-optimization.md — Replace LIKE with FREETEXT, fix CAST on JOIN, decouple facet cache
- [ ] 02-PLAN-C-frontend-search.md — Increase search debounce from 300ms to 500ms

- Canonical refs: `docs/plans/2026-04-01-p0-implementation-plan.md` section Phase 2, `docs/backlog-prioritizado-abril-2026.md`

### Phase 3: Text Quality
- **Goal:** Fix text copying from sources, add competitor filtering, fix silent hallucination pass
- **Status:** NOT STARTED
- **Bugs:** P0-Qualidade (copied text, competitor mentions, fabricated data passes silently)
- Canonical refs: `docs/plans/2026-04-01-p0-implementation-plan.md` section Phase 3

### Phase 4: Fact-Check Accuracy
- **Goal:** Add temporal awareness to fact-checking, stop blocking breaking news as unverifiable
- **Status:** NOT STARTED
- **Bugs:** P0-FactCheck (no temporal awareness, blocks breaking news)
- Canonical refs: `docs/plans/2026-04-01-p0-implementation-plan.md` section Phase 4
