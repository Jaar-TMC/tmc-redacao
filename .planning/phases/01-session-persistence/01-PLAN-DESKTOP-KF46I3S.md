---
phase: 1
name: Session Persistence
wave: 1
depends_on: []
files_modified:
  - tmc-redacao/src/context/AuthContext.jsx
  - tmc-redacao/src/services/api.js
autonomous: true
requirements_addressed: [P0-Sessao]
---

# Phase 1: Session Persistence — Plan

## Objective
Fix auth session persistence so users stay logged in after F5 page refresh. Two code changes + two human verification tasks.

## Wave 1 (Sequential — each task depends on the previous)

### Task 1.1: Verify CORS_ALLOWED_ORIGINS in Azure (HUMAN TASK)

<action>
**Operational task — not a code change.**

1. Open Azure Portal → Function App → tmc-redacao-api → Configuration → Application Settings
2. Verify `CORS_ALLOWED_ORIGINS` contains: `https://purple-river-09235a310.3.azurestaticapps.net`
3. If missing: add it and restart the Function App
4. Verify via browser: open production URL, DevTools > Network, hit `/api/health`, check response header `Access-Control-Allow-Origin` matches the frontend origin

**Why this matters:** Without this env var, `function_app.py:37-39` sets `ALLOWED_ORIGINS = []` in production mode, which means ALL cross-site requests silently fail — cookies are never sent, refresh never works.
</action>

<read_first>
- FeedRSS/tmc-rss-collector/function_app.py (lines 31-44 — CORS resolution logic)
- FeedRSS/tmc-rss-collector/services/config.py (line 211 — production validation warning)
</read_first>

<acceptance_criteria>
- `/api/health` response contains `Access-Control-Allow-Origin: https://purple-river-09235a310.3.azurestaticapps.net`
- `Access-Control-Allow-Credentials: true` present in response
- Browser DevTools > Application > Cookies shows `refresh_token` cookie after login
</acceptance_criteria>

---

### Task 1.2: Add retry to refresh-on-mount flow

<action>
**File:** `tmc-redacao/src/context/AuthContext.jsx` (lines 38-59)

**Current behavior:** Single `authRefresh()` call — any failure (cold start timeout, transient network error) immediately clears auth state and redirects to login.

**Desired behavior:** Retry once with 1-second delay before clearing auth state. Log failures for debugging.

**Implementation:**

Replace the `tryRefresh` function (lines 39-58) with:

```javascript
const tryRefresh = async () => {
  const MAX_RETRIES = 1;
  const RETRY_DELAY_MS = 1000;
  
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const data = await authRefresh();
      if (data?.access_token) {
        setAuthToken(data.access_token);
        const userData = await authGetMe();
        setUser(userData);
        return; // Success — exit
      }
    } catch (err) {
      console.error(`[Auth] Refresh attempt ${attempt + 1} failed:`, err.message || err);
      if (attempt < MAX_RETRIES) {
        await new Promise(r => setTimeout(r, RETRY_DELAY_MS));
        continue;
      }
    }
  }
  // All retries exhausted — clear auth state
  clearAuthToken();
  setUser(null);
};
```

**Constraints:**
- Do NOT change the `useEffect` wrapper or its dependency array
- `isLoading` remains `true` until `finally` block (loading spinner visible during retry)
- Keep `finally { setIsLoading(false); }` AFTER the retry loop
</action>

<read_first>
- tmc-redacao/src/context/AuthContext.jsx (full file — understand registration flow and state management)
- tmc-redacao/src/services/auth.js (authRefresh function — understand the 5s timeout)
</read_first>

<acceptance_criteria>
- AuthContext.jsx contains `MAX_RETRIES = 1`
- AuthContext.jsx contains `RETRY_DELAY_MS = 1000`
- AuthContext.jsx contains `console.error('[Auth] Refresh attempt'`
- AuthContext.jsx contains `await new Promise(r => setTimeout(r, RETRY_DELAY_MS))`
- `setIsLoading(false)` is called in `finally` block AFTER retry loop
- `npm run lint` passes on AuthContext.jsx (no new errors)
- `npm run build` succeeds
</acceptance_criteria>

---

### Task 1.3: Fix _onUnauthorized to fire exactly once

<action>
**File:** `tmc-redacao/src/services/api.js` (lines 129-156)

**Current behavior:** When multiple concurrent requests get 401, each one that falls through to `_onUnauthorized()` at line 154 triggers a separate redirect to login. This causes multiple navigation events and potential race conditions.

**Desired behavior:** `_onUnauthorized()` fires exactly once. Subsequent 401s within the same "batch" are suppressed.

**Implementation:**

Add a module-level flag near line 30 (after the existing `_refreshPromise` declaration):

```javascript
let _isRedirecting = false;
```

Replace the `_onUnauthorized` call at line 154-156 with:

```javascript
if (_onUnauthorized && !_isRedirecting) {
  _isRedirecting = true;
  _onUnauthorized();
}
```

Add reset in registerAuthHandlers (when a new onUnauthorized handler is registered), so the flag resets on fresh login:

In the `registerAuthHandlers` function, add after the handler assignments:
```javascript
_isRedirecting = false;
```

**Constraints:**
- Do NOT modify the singleton `_refreshPromise` pattern — it already works correctly
- Do NOT add a `failedQueue` pattern — the current per-request retry-after-refresh is sufficient
- Keep the flag at module level (not function-scoped)
</action>

<read_first>
- tmc-redacao/src/services/api.js (lines 27-34 — registerAuthHandlers, lines 94-164 — fetchApi with 401 handling)
</read_first>

<acceptance_criteria>
- api.js contains `let _isRedirecting = false`
- api.js contains `if (_onUnauthorized && !_isRedirecting)`
- api.js contains `_isRedirecting = true` before `_onUnauthorized()` call
- `registerAuthHandlers` resets `_isRedirecting = false`
- `npm run lint` passes on api.js (no new errors)
- `npm run build` succeeds
</acceptance_criteria>

---

### Task 1.4: Verify Cookie Domain Directive (VERIFICATION ONLY)

<action>
**No code change needed.**

`auth_api.py:137-140` sets cookies with `SameSite=None; Secure; Path=/api/auth`. 
Frontend (azurestaticapps.net) and API (azurewebsites.net) are different TLDs — `Domain=` attribute cannot span them.
`SameSite=None; Secure` is the correct cross-site approach.

**Verification:** After Tasks 1.1-1.3 are deployed:
1. Login at production URL
2. DevTools > Application > Cookies → verify `refresh_token` exists with correct attributes
3. F5 refresh → Network tab shows `/api/auth/refresh` with Cookie header included
4. No redirect to login
</action>

<read_first>
- FeedRSS/tmc-rss-collector/functions/auth_api.py (lines 133-141 — cookie creation)
</read_first>

<acceptance_criteria>
- `refresh_token` cookie visible in DevTools after login
- Cookie has `HttpOnly`, `Secure`, `SameSite=None`, `Path=/api/auth`
- F5 refresh sends cookie in `/api/auth/refresh` request
- User stays logged in after refresh
</acceptance_criteria>

---

## must_haves (Goal-backward verification)

1. User stays logged in after F5 refresh (the entire point of Phase 1)
2. Refresh retry covers Azure cold start transient failures
3. Multiple concurrent 401s produce single redirect, not N redirects
4. No regressions: existing login, logout, and token refresh continue to work

## Verification Protocol

- **Gate 1 (Automated):** `npm run lint` + `npm run build` pass
- **Gate 2 (AI Review):** Reviewer checks diff against this plan
- **Gate 3 (Human):** Manual browser test at production URL (login → F5 → verify session persists)
