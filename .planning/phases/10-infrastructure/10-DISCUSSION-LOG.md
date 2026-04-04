# Phase 10: Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 10-infrastructure
**Areas discussed:** Hosting plan choice, numpy replacement scope, Gemini service fate, Deployment approach

---

## Hosting Plan Choice

| Option | Description | Selected |
|--------|-------------|----------|
| Flex Consumption | 1 always-ready instance, ~$60-80/mo, zero cold starts | |
| Premium EP1 | ~$150/mo, zero cold starts, VNet integration | |
| Defer | Handle hosting plan migration later | ✓ |

**User's choice:** Defer to later — handle hosting plan separately
**Notes:** User wants to implement code-level optimizations first, evaluate hosting plan as a separate decision

---

## numpy Replacement Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Replace all | Remove numpy entirely, rewrite silhouette in pure Python | |
| Hot paths only | Replace cosine/normalize/EMA, lazy-import for silhouette | ✓ |
| Keep numpy | Only remove from module-level, no code changes | |

**User's choice:** Accepted specialist recommendation — hot paths only
**Notes:** Silhouette score uses heavy matrix ops (pairwise distances, broadcasting). Runs only in daily 3AM maintenance timer. Lazy import gives 90% cold start savings without complex rewrites.

---

## Gemini Service Fate

| Option | Description | Selected |
|--------|-------------|----------|
| Remove service + dep | Full cleanup of gemini_service.py and google-auth | |
| Remove dep, keep service | Remove google-auth, service stays dormant | ✓ |
| Keep both | Leave as-is | |

**User's choice:** Accepted specialist recommendation — remove dependency, keep service dormant
**Notes:** google-auth adds ~200ms import time. All imports are lazy (inside methods). Re-adding is a one-line requirements.txt change. Zero-risk removal.

---

## Deployment Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Single deploy | All changes at once | |
| Two-stage | Code changes first, plan migration second | ✓ |
| Three-stage | numpy, then nest_asyncio, then deps | |

**User's choice:** Accepted two-stage approach (specialist recommendation)
**Notes:** Stage 1 (code changes) deployed to current Consumption plan. Stage 2 (plan migration) deferred. Isolates variables for troubleshooting.

---

## Claude's Discretion

- Pure-Python implementation details (math.sqrt, list comprehensions, zip)
- ThreadPoolExecutor pattern for nest_asyncio replacement
- Lazy import placement inside silhouette functions

## Deferred Ideas

- INFRA-01 hosting plan migration — separate decision with cost implications
- INFRA-06 region verification — pair with hosting plan migration
- Full Gemini service removal — if Gemini is permanently abandoned
