---
phase: 02-search-filter-performance
plan: C
type: execute
wave: 1
depends_on: []
files_modified:
  - tmc-redacao/src/components/ui/FilterBar.jsx
autonomous: true
requirements: [D-17, D-18, D-19]

must_haves:
  truths:
    - "Search debounce waits 500ms before dispatching filter update (was 300ms)"
    - "AbortController still correctly cancels in-flight requests on new filter changes"
    - "No additional request deduplication needed (apiCache.js already handles it)"
  artifacts:
    - path: "tmc-redacao/src/components/ui/FilterBar.jsx"
      provides: "500ms search debounce"
      contains: "500"
  key_links:
    - from: "FilterBar.jsx debounce timer"
      to: "RedacaoPage.jsx fetch debounce"
      via: "FilterBar dispatches updateFilter after 500ms, RedacaoPage coalesces with 150ms fetch debounce"
      pattern: "}, 500"
---

<objective>
Increase the search input debounce from 300ms to 500ms in FilterBar.jsx to reduce the frequency of API calls triggered by typing.

Purpose: Combined with RedacaoPage's existing 150ms fetch debounce, the effective delay becomes ~650ms, which dramatically reduces unnecessary search requests while remaining responsive. The AbortController (D-17) and apiCache dedup (D-19) already exist and work correctly — this plan only changes the debounce value.

Output: Single-line edit to FilterBar.jsx.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-search-filter-performance/02-CONTEXT.md

<interfaces>
<!-- FilterBar.jsx search debounce — lines 86-102 -->
From tmc-redacao/src/components/ui/FilterBar.jsx:86-102:
```jsx
// Handle search input change with debounce
const handleSearchChange = useCallback((e) => {
  const value = e.target.value;
  isUserTypingRef.current = true;
  setSearchTerm(value);

  // Clear existing timer
  if (debounceTimerRef.current) {
    clearTimeout(debounceTimerRef.current);
  }

  // Set new debounce timer
  debounceTimerRef.current = setTimeout(() => {
    updateFilter('searchQuery', value);
    isUserTypingRef.current = false;
  }, 300);   // <--- THIS LINE CHANGES TO 500
}, [updateFilter]);
```

<!-- RedacaoPage.jsx fetch debounce — line 161 (NOT changing) -->
From tmc-redacao/src/pages/RedacaoPage.jsx:76-81:
```jsx
const abortControllerRef = useRef(null);    // line 77 — AbortController (per D-17: already exists)
const fetchDebounceRef = useRef(null);      // line 81 — 150ms fetch coalescing (keep as-is per D-18)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Increase FilterBar search debounce from 300ms to 500ms</name>
  <files>tmc-redacao/src/components/ui/FilterBar.jsx</files>

  <read_first>
    - tmc-redacao/src/components/ui/FilterBar.jsx:82-106 (full debounce handler context including the useCallback and the debounce timer)
    - tmc-redacao/src/pages/RedacaoPage.jsx:76-82 (verify AbortController and fetchDebounce refs exist — per D-17)
    - tmc-redacao/src/pages/RedacaoPage.jsx:155-170 (verify AbortController correctly cancels on filter changes — per D-17)
    - .planning/phases/02-search-filter-performance/02-CONTEXT.md (decisions D-17, D-18, D-19)
  </read_first>

  <action>
    SINGLE LINE EDIT at FilterBar.jsx line 101 (per D-18).

    **Current code (line 101):**
    ```jsx
    }, 300);
    ```

    **Replace with:**
    ```jsx
    }, 500);
    ```

    That is the ONLY change in this plan.

    Per D-17: Verify (read-only, no edit needed) that AbortController in RedacaoPage.jsx:77,157 correctly:
    1. Creates a new AbortController before each fetch
    2. Calls `.abort()` on the previous controller when filters change
    3. Passes the `signal` to the fetch call
    If any of these are missing, note it in the SUMMARY but do NOT fix it in this plan (it would be a separate task).

    Per D-18: Do NOT change the 150ms fetch debounce in RedacaoPage.jsx:161. The combined effective debounce is 500ms (FilterBar) + 150ms (fetch) = 650ms total, which is acceptable.

    Per D-19: Do NOT add any request deduplication — apiCache.js already handles this.

    **CRITICAL CONSTRAINTS:**
    - Change ONLY the number `300` to `500` on line 101
    - Do NOT modify any other code in FilterBar.jsx
    - Do NOT modify RedacaoPage.jsx
    - Do NOT modify apiCache.js or api.js
    - Do NOT add AbortController to FilterBar (it already exists in RedacaoPage)
  </action>

  <verify>
    <automated>grep -n "}, 500)" "tmc-redacao/src/components/ui/FilterBar.jsx" | head -5</automated>
    <automated>! grep -n "debounceTimerRef.*300\|setTimeout.*}, 300)" "tmc-redacao/src/components/ui/FilterBar.jsx"</automated>
    <automated>cd tmc-redacao && npm run lint 2>&1 | tail -5</automated>
  </verify>

  <acceptance_criteria>
    - FilterBar.jsx line ~101 contains `}, 500)` (was `}, 300)`)
    - FilterBar.jsx does NOT contain `}, 300)` anywhere in the debounce handler
    - FilterBar.jsx still contains `useCallback` wrapping `handleSearchChange`
    - FilterBar.jsx still contains `clearTimeout(debounceTimerRef.current)` (timer cleanup preserved)
    - FilterBar.jsx still contains `updateFilter('searchQuery', value)` inside the setTimeout
    - No other files were modified
    - `cd tmc-redacao && npx eslint src/components/ui/FilterBar.jsx --no-error-on-unmatched-pattern` passes (or npm run lint covers it)
  </acceptance_criteria>

  <done>FilterBar search debounce increased from 300ms to 500ms. Combined with RedacaoPage's 150ms fetch debounce, total effective delay is ~650ms. AbortController verified present in RedacaoPage. No additional dedup needed (apiCache.js handles it).</done>
</task>

</tasks>

<verification>
After task completes:
1. `grep "500" tmc-redacao/src/components/ui/FilterBar.jsx` shows the 500ms debounce
2. `grep "300" tmc-redacao/src/components/ui/FilterBar.jsx` does NOT show 300ms in the setTimeout (may still appear elsewhere for unrelated values — verify context)
3. `cd tmc-redacao && npm run build` succeeds (no build breakage)
4. `cd tmc-redacao && npm run lint` passes (no lint errors)
</verification>

<success_criteria>
- FilterBar.jsx debounce is 500ms (per D-18)
- Build and lint pass
- No other files modified
- AbortController in RedacaoPage verified present (per D-17)
</success_criteria>

<output>
After completion, create `.planning/phases/02-search-filter-performance/02-C-SUMMARY.md`
</output>
