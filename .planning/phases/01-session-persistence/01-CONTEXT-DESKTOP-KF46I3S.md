# Phase 1: Session Persistence - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix auth session persistence so users stay logged in after F5 page refresh. Currently, refreshing the page clears the access token (stored in JS memory) and the refresh-on-mount flow fails silently, redirecting to login.

**Root cause hierarchy (confirmed by code analysis):**
1. **PRIMARY**: If `CORS_ALLOWED_ORIGINS` is not set in Azure production, `ALLOWED_ORIGINS = []` → browser blocks all cross-site responses → cookies never stored/sent → refresh always fails
2. **SECONDARY**: `AuthContext.jsx:50` has no retry on refresh failure — a single transient error (cold start, 5s timeout) immediately clears auth state
3. **MINOR**: `api.js:154-156` fires `_onUnauthorized()` per-request during concurrent 401s (cosmetic — multiple redirects)

</domain>

<decisions>
## Implementation Decisions

### CORS Verification (Task 1.1)
- **D-01:** CORS_ALLOWED_ORIGINS must be verified in Azure portal — this is an operational task, not a code change. Human must check.
- **D-02:** The code already has a startup warning at `config.py:211-214` when CORS is unset in production mode. No additional code hardening needed.
- **D-03:** Verification method: hit `/api/health` from browser DevTools at production URL, check `Access-Control-Allow-Origin` response header.

### Retry Strategy (Task 1.2)
- **D-04:** 1 retry with 1-second delay before clearing auth state. No exponential backoff — single retry covers Azure cold starts.
- **D-05:** Add `console.error` logging on refresh failure (currently silent catch at `AuthContext.jsx:50`).
- **D-06:** `isLoading` state must remain `true` during retry (loading spinner visible). Only set `false` in `finally` after all attempts.

### Concurrent 401 Handling (Task 1.3)
- **D-07:** Keep existing singleton `_refreshPromise` pattern at `api.js:133-134` — it already prevents concurrent refresh calls.
- **D-08:** Add `_isRedirecting` flag to ensure `_onUnauthorized()` fires exactly once, not per-request.
- **D-09:** Do NOT implement a full `failedQueue` pattern — the current approach where each 401 waits on the shared promise and retries individually is sufficient.

### Cookie Domain (Task 1.4)
- **D-10:** Leave cookie settings as-is. `SameSite=None; Secure` at `auth_api.py:137-140` is correct for cross-site (azurestaticapps.net → azurewebsites.net). No `Domain=` attribute needed — can't span different TLDs.
- **D-11:** This task becomes a verification-only check, not a code change.

### Claude's Discretion
- Error message shown during retry (if any transient UI feedback is appropriate during the 1s retry window)
- Whether to add a brief "reconnecting..." indicator or keep the existing loading spinner

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Plan
- `docs/plans/2026-04-01-p0-implementation-plan.md` §Phase 1 — Full task breakdown, line numbers, verification checklist

### Backend Auth
- `FeedRSS/tmc-rss-collector/functions/auth_api.py:125-150` — Login handler, cookie creation, Set-Cookie header
- `FeedRSS/tmc-rss-collector/function_app.py:31-61` — CORS configuration, ALLOWED_ORIGINS resolution, with_cors decorator
- `FeedRSS/tmc-rss-collector/services/config.py:79,171,211-215` — CORS env var loading and production validation

### Frontend Auth
- `tmc-redacao/src/context/AuthContext.jsx:15-59` — AuthProvider, registerAuthHandlers, refresh-on-mount flow
- `tmc-redacao/src/services/auth.js:1-91` — Token storage (memory-only), authRefresh (5s timeout), authLogin
- `tmc-redacao/src/services/api.js:27-34,94-164` — fetchApi, singleton refresh promise, _onUnauthorized handler

### Prior Fixes (context)
- Commit `6777fb7` — Fixed CORS header mutation that dropped Set-Cookie (add_cors_headers now mutates in-place)
- Commit `75722f6` — Reduced refresh timeout from 30s to 5s for fail-fast behavior

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `registerAuthHandlers()` in `api.js:27-34` — already wires up getToken, onUnauthorized, refreshToken callbacks
- `_refreshPromise` singleton pattern in `api.js:133-134` — prevents concurrent refresh; just needs the unauthorized guard
- `authRefresh()` in `auth.js:47-59` — already has 5s AbortController timeout, `credentials: 'include'`

### Established Patterns
- Auth state: React Context (`AuthContext.jsx`), NOT Zustand/Redux
- Token storage: memory-only `_accessToken` variable in `auth.js:12` (security: no localStorage)
- Cookie: httpOnly refresh token set by backend, managed by browser
- Error handling: silent catch with state clear (needs to be made resilient)

### Integration Points
- `AuthContext.jsx:16-34` registers handlers with `api.js` on mount — any changes to refresh logic must maintain this registration
- `function_app.py:31-44` loads CORS at module level — changes apply to all handlers via `with_cors` decorator
- Cookie path `/api/auth` scopes refresh token to auth endpoints only

</code_context>

<specifics>
## Specific Ideas

- The CORS env var check (Task 1.1) MUST be done first — if CORS is broken, no code fix will help
- The retry in AuthContext (Task 1.2) should use a simple `setTimeout` + `await`, not a retry library
- The `_isRedirecting` flag (Task 1.3) should be a module-level boolean in `api.js`, reset on successful refresh

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-session-persistence*
*Context gathered: 2026-04-01*
