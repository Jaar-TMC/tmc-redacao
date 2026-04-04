# TMC - Ferramenta de Redacao

## What This Is

AI-powered newsroom tool that collects RSS feeds, scores articles editorially, clusters them into semantic themes, and generates journalistic articles with anti-hallucination safeguards. Built with Azure Functions (Python) backend, React frontend, and Azure SQL database.

## Core Value

Enable journalists to efficiently discover, filter, and generate news articles — speed and reliability are the core differentiators.

## Current Milestone: v2.0 Performance Optimization

**Goal:** Eliminate RedacaoPage performance bottlenecks across backend, frontend, database, and infrastructure to achieve sub-200ms page loads and sub-50ms filter responses.

**Target features:**
- Quick wins: CORS preflight caching, HTTP cache headers, content removal from list queries, memo fixes
- Database optimization: Covering indexes, urgency count caching, parallel facets, source_id filtering
- Frontend state: TanStack Query migration, SmartEmptyState fix, FiltersContext splitting
- Server-side caching: Redis cache-aside pattern between API and Azure SQL
- Keyset pagination: Cursor-based O(1) pagination replacing OFFSET
- Infrastructure: Flex/Premium plan, dependency cleanup, connection pool tuning

**Context:** 32 bottlenecks identified by 4 specialized agents across backend, frontend, infrastructure, and industry research. Full analysis at `docs/plans/2026-04-02-performance-optimization-plan.md`.

## Active Requirements

See REQUIREMENTS.md for milestone v2.0 requirements.

## Key Decisions

- **Denormalized scores** (migration 013): Scores copied into articles table for 60x faster filtering
- **Full-text search** (migration 021): FREETEXT replaces LIKE for search queries
- **Pre-aggregated tags** (migration 020): tag_aggregations table avoids OPENJSON per request
- **JWT auth**: Access token (60min) + refresh token (7d httpOnly cookie, SameSite=None)
- **Production safety mode**: Forces fact-checking, requires CORS origins and strong JWT secret

## Validated (shipped)

- v1.0 P0 Backlog Resolution
  - Phase 1: Session persistence (auth refresh on F5)
  - Phase 2: Search/filter performance (full-text index, FREETEXT queries, frontend debounce)
  - Phase 3: Text quality (anti-copy, competitor filter, safety gates)
  - Phase 4: Fact-check accuracy (temporal awareness, breaking news handling)

## Context

- **Backend**: Azure Functions (Python 3.11) on Consumption Plan
- **Frontend**: React 19, Vite 7, Tailwind CSS 4
- **Database**: Azure SQL Server with 14 tables, 22 migrations
- **Deployment**: Azure Static Web Apps (frontend) + Azure Functions (backend)
- **LLM**: Claude Sonnet 4.5 (generation) + Claude Haiku 4.5 (classification)

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-02*
