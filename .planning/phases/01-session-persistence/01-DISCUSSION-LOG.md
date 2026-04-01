# Phase 1: Session Persistence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 01-session-persistence
**Areas discussed:** CORS verification, Retry strategy, Concurrent 401 handling, Cookie Domain
**Mode:** --auto (all areas auto-selected, recommended defaults chosen)

---

## CORS Verification Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Harden code + document Azure check | Add defensive fallback + human verifies Azure portal | ✓ |
| Code-only fix (add wildcard fallback) | Less secure, masks the real problem | |
| Skip (assume it's set) | Risky — if not set, nothing else works | |

**User's choice:** [auto] Harden code + document Azure check (recommended default)
**Notes:** Code already has startup warning at config.py:211. No additional code needed — Azure portal verification is the action item.

---

## Retry Strategy for Refresh-on-Mount

| Option | Description | Selected |
|--------|-------------|----------|
| 1 retry, 1s fixed delay | Simple, covers cold starts | ✓ |
| 3 retries, exponential backoff | Over-engineered for this use case | |
| No retry, faster fail | Current behavior — too aggressive | |

**User's choice:** [auto] 1 retry, 1s fixed delay (recommended default)
**Notes:** Matches plan specification. A single retry with 1s delay covers the most common failure mode (Azure Functions cold start).

---

## Concurrent 401 Handling Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix _onUnauthorized to fire once | Add _isRedirecting flag, minimal change | ✓ |
| Full failedQueue pattern | Complex, queues and replays all 401 requests | |
| Leave as-is | Multiple redirects are cosmetic but sloppy | |

**User's choice:** [auto] Fix _onUnauthorized to fire once (recommended default)
**Notes:** Singleton promise pattern already handles the hard part. Just need a guard flag on the redirect.

---

## Cookie Domain Directive

| Option | Description | Selected |
|--------|-------------|----------|
| Leave as-is (SameSite=None; Secure) | Correct for cross-site, no Domain needed | ✓ |
| Add explicit Domain= | Can't span different TLDs — would break things | |

**User's choice:** [auto] Leave as-is (recommended default)
**Notes:** Frontend (azurestaticapps.net) and API (azurewebsites.net) are different TLDs. SameSite=None; Secure is the correct cross-site approach. Task 1.4 becomes verification-only.

---

## Claude's Discretion

- Error message/indicator during retry window (loading spinner vs "reconnecting..." text)

## Deferred Ideas

None — discussion stayed within phase scope
