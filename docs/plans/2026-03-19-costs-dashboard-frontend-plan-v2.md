# Costs Dashboard — Frontend Implementation Plan (v2)

**Date:** 2026-03-19
**Status:** Approved
**Version:** 2 (revised — incorporates review findings)
**Related:** [Backend Plan](2026-03-19-costs-dashboard-plan-v2.md) | [v1 Plan](2026-03-19-costs-dashboard-frontend-plan.md)

## Context

TMC admins need full cost traceability for all AI operations on the platform. Currently, the only cost-related UI is the kill switch on SistemaPage showing `estimatedSavings` and `avgHourlyCost`. The backend already logs every LLM call to `llm_usage_log` (migration 009) with token counts, cost USD, model, task_type, and latency — but there's **no user attribution**, **no Exa/embedding tracking**, **no cost API endpoints**, and **no dashboard UI**.

This plan covers the **frontend dashboard only** — what admins will see. Backend API endpoints and migrations are covered in the existing plan at `docs/plans/2026-03-19-costs-dashboard-plan-v2.md` and will be implemented separately.

**Approach:** Build the full frontend with mock data fallbacks so it can be wired to real APIs as backend endpoints become available.

---

## Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `tmc-redacao/src/services/costsApi.js` | API service — 6 endpoint wrappers using `fetchApi` |
| 2 | `tmc-redacao/src/pages/config/CustosPage.jsx` | Main page — orchestrates state, period selector, all sections |
| 3 | `tmc-redacao/src/components/custos/CostOverviewCards.jsx` | 4 top-row metric cards with deltas, sparklines, and mini provider bars |
| 4 | `tmc-redacao/src/components/custos/CostTrendsChart.jsx` | Dual-panel chart: total cost trend line + non-LLM detail chart |
| 5 | `tmc-redacao/src/components/custos/CostBreakdownTable.jsx` | Action cost map — horizontal bar + sortable table |
| 6 | `tmc-redacao/src/components/custos/CostByUserTable.jsx` | Per-user cost table with search and sort |
| 7 | `tmc-redacao/src/components/custos/CostBySourceTable.jsx` | Per-source cost table with efficiency indicators |
| 8 | `tmc-redacao/src/components/custos/WhatIfCalculator.jsx` | Interactive cost projection calculator |

## Files to Modify

| File | Change |
|------|--------|
| `tmc-redacao/src/App.jsx` | Line 21: add lazy import. Line 54: add title. Line 206: add route |
| `tmc-redacao/src/pages/ConfiguracoesPage.jsx` | Line 3: add `DollarSign` import. Line 25: add menu item |
| `tmc-redacao/vite.config.js` | Add `recharts` to manual chunks (line 64, inside `manualChunks`) |

---

## Step 1: Install recharts

```bash
cd tmc-redacao && npm install recharts
```

Add to `vite.config.js` manual chunks inside the existing `manualChunks` object at line 63-74:

```js
manualChunks: {
  vendor: ['react', 'react-dom', 'react-router-dom'],
  tiptap: [ /* existing */ ],
  'vendor-sanitize': ['dompurify'],
  'vendor-charts': ['recharts'],    // <-- ADD
},
```

Since CustosPage is lazy-loaded, recharts only downloads when an admin visits the page.

**Build verification note:** After implementation, check `npm run build` output to confirm that recharts + d3 sub-packages land in the `vendor-charts` chunk and do NOT appear in the main vendor chunk. If d3 sub-packages leak into vendor, explicitly add them: `'vendor-charts': ['recharts', 'd3-scale', 'd3-shape', 'd3-path', 'd3-array', 'd3-color', 'd3-format', 'd3-interpolate', 'd3-time', 'd3-time-format']`.

---

## Step 2: Create `costsApi.js`

**File:** `tmc-redacao/src/services/costsApi.js`

Follow exact pattern of `userApi.js` — thin wrappers around `fetchApi` from `api.js`.

```
getCostOverview(period)              → GET /api/costs/overview?period=30d
getCostTrends({granularity, start, end}) → GET /api/costs/trends?granularity=day&start_date=...&end_date=...
getCostBreakdown({start, end, groupBy})  → GET /api/costs/breakdown?group_by=action&start_date=...&end_date=...
getCostByUser({start, end})          → GET /api/costs/by-user?start_date=...&end_date=...
getCostBySource({start, end})        → GET /api/costs/by-source?start_date=...&end_date=...
getSourceEstimate()                  → GET /api/costs/source-estimate
```

All functions accept an optional `signal` parameter (AbortController signal) passed through to `fetchApi` for request cancellation.

No caching — cost data changes constantly and is admin-only (low traffic).

**Mock data strategy:** Use `import.meta.env.VITE_COSTS_USE_MOCK === 'true'` env var check at the top of the module. When enabled, functions return mock data immediately (no API call). This is explicit and will NOT mask routing bugs in production. Include a `// TODO: remove mock mode when backend is ready` comment.

```js
const USE_MOCK = import.meta.env.VITE_COSTS_USE_MOCK === 'true';

export async function getCostOverview(period, { signal } = {}) {
  if (USE_MOCK) return MOCK_OVERVIEW;
  return fetchApi(`/costs/overview?period=${period}`, { signal });
}
// ... same pattern for all 6 endpoints
```

---

## Step 3: Wire up route and navigation

### App.jsx (3 edits)

1. **After line 20** (after `const SistemaPage = lazy(...)`) — Add lazy import:
   ```jsx
   const CustosPage = lazy(() => import('./pages/config/CustosPage'));
   ```

2. **Before line 54** (before closing brace of `titles` object) — Add title mapping:
   ```js
   '/configuracoes/custos': 'Custos - Configurações',
   ```

3. **After line 205** (after the `sistema` route) — Add route inside `/configuracoes`:
   ```jsx
   <Route path="custos" element={<ProtectedRoute permission="manage_users"><CustosPage /></ProtectedRoute>} />
   ```

### ConfiguracoesPage.jsx (2 edits)

1. **Line 3** — Add `DollarSign` to lucide import:
   ```jsx
   import { Newspaper, Users, Power, DollarSign, Menu, X } from 'lucide-react';
   ```

2. **After line 24** (after the Sistema menu item, making it line 25) — Add menu item (admin-only):
   ```jsx
   ...(canManageUsers ? [{ path: '/configuracoes/custos', label: 'Custos', icon: DollarSign }] : []),
   ```

---

## Step 4: Create CustosPage.jsx (orchestrator)

**File:** `tmc-redacao/src/pages/config/CustosPage.jsx`

**Location note:** CustosPage goes in `pages/config/CustosPage.jsx` following the UsuariosPage/BuscadorPage convention. SistemaPage is at `pages/SistemaPage.jsx` (NOT in `pages/config/`) — do not follow its patterns for page location or styling.

**Container:** `<div className="max-w-6xl mx-auto space-y-6">` (wider than SistemaPage's `max-w-3xl` because charts and tables need horizontal space).

### Page Header + Period Selector + Metadata

```
[h1: "Custos"]  [subtitle: "Acompanhe os gastos com IA, busca e embeddings"]     [Atualizado em HH:MM]  [Exportar CSV]  [Period: Hoje | 7d | 30d | 90d | Ano]
```

**Page header:** `<h1 className="text-2xl font-bold text-dark-gray">Custos</h1>` and `<p className="text-sm text-medium-gray mt-1">...`.

**"Atualizado em" timestamp:** Show `Atualizado em ${lastFetchTime.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}` near the period selector. Updates whenever `fetchAllData` completes.

**"Exportar CSV" button:** `<button className="px-4 py-2 text-sm font-medium text-medium-gray hover:text-dark-gray border border-light-gray rounded-lg hover:bg-off-white transition-colors flex items-center gap-2 min-h-[44px]">` with `Download` icon. Exports overview + breakdown data as CSV.

**Period selector:** Use the actual `TabButton` component from `components/ui/TabButton.jsx`. Wrap in a `role="tablist"` container matching TrendsPage pattern (TrendsPage.jsx lines 81-96):

```jsx
import TabButton from '../../components/ui/TabButton';

<div className="flex flex-wrap gap-1 bg-off-white p-1 rounded-lg w-fit" role="tablist" aria-label="Período de custos">
  {PERIODS.map(p => (
    <TabButton
      key={p.value}
      active={period === p.value}
      onClick={() => handlePeriodChange(p.value)}
      ariaLabel={`Período: ${p.label}`}
    >
      {p.label}
    </TabButton>
  ))}
</div>
```

`PERIODS` constant: `[{ value: 'today', label: 'Hoje' }, { value: '7d', label: '7d' }, { value: '30d', label: '30d' }, { value: '90d', label: '90d' }, { value: 'year', label: 'Ano' }]`.

**Mobile wrapping:** Below `md:` breakpoint, show a `<select>` dropdown as an alternative:

```jsx
{/* Mobile: select dropdown */}
<select
  value={period}
  onChange={(e) => handlePeriodChange(e.target.value)}
  className="md:hidden px-3 py-2 border border-light-gray rounded-lg text-sm bg-white min-h-[44px]"
  aria-label="Período de custos"
>
  {PERIODS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
</select>

{/* Desktop: TabButtons */}
<div className="hidden md:flex flex-wrap gap-1 bg-off-white p-1 rounded-lg w-fit" role="tablist" aria-label="Período de custos">
  {/* ... TabButtons */}
</div>
```

### State Management

All state at page level — no context, no Zustand (matches UsuariosPage pattern):

```
period          — '30d' (default)
overview        — data for cards
trends          — data for chart
breakdown       — data for action table
byUser          — data for user table
bySource        — data for source table
sourceEstimate  — data for calculator
loadingStates   — { overview: bool, trends: bool, ... } per-section
errors          — { overview: string|null, ... } per-section
lastFetchTime   — Date|null for "Atualizado em" display
```

### Data Fetching with AbortController

`useEffect` on `period` change calls `fetchAllData(period)` which:
1. **Aborts stale requests:** Creates a new `AbortController`, cancels previous one via cleanup ref
2. Computes `startDate`/`endDate`/`granularity` from period string
3. Fires all 6 API calls with `Promise.allSettled` (parallel), passing `signal` to each
4. Updates each section's data + loading + error independently
5. Updates `lastFetchTime` on completion
6. Partial rendering: if one endpoint fails, others still render

**200ms debounce on period change:** Prevent rapid-fire requests if user clicks multiple periods quickly:

```jsx
const periodDebounceRef = useRef(null);

const handlePeriodChange = useCallback((newPeriod) => {
  setPeriod(newPeriod);
  clearTimeout(periodDebounceRef.current);
  periodDebounceRef.current = setTimeout(() => {
    fetchAllData(newPeriod);
  }, 200);
}, []);
```

**AbortController pattern:**

```jsx
const abortControllerRef = useRef(null);

const fetchAllData = useCallback(async (currentPeriod) => {
  // Cancel previous in-flight requests
  if (abortControllerRef.current) {
    abortControllerRef.current.abort();
  }
  const controller = new AbortController();
  abortControllerRef.current = controller;

  const { startDate, endDate, granularity } = periodToDateRange(currentPeriod);
  const signal = controller.signal;

  // ... fire Promise.allSettled with signal passed to each API call
  // On AbortError, silently ignore (new request superseded this one)
}, []);

// Cleanup on unmount
useEffect(() => {
  return () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    clearTimeout(periodDebounceRef.current);
  };
}, []);
```

### periodToDateRange helper

Inline pure function (~15 lines):
- `today` → start=midnight today, granularity=`hour`
- `7d` → -7 days, granularity=`day`
- `30d` → -30 days, granularity=`day`
- `90d` → -90 days, granularity=`week`
- `year` → Jan 1 current year, granularity=`month`

### Section Layout

```
[Period Selector + Atualizado em + Exportar CSV]
[Overview Cards — 4 cards in row, with sparklines]
[Cost Trends — dual-panel: total line + non-LLM detail]
[Cost by Action — horizontal bars + table]
[Cost by User — sortable table]
[Cost by Source — sortable table (own component)]
[What-If Calculator]
```

Each section is a white card (`bg-white rounded-xl border border-light-gray p-6`) with its own content-shaped loading skeleton and error retry.

### PropTypes

All components in this feature MUST include PropTypes (codebase convention — every component uses `prop-types`). Page-level components that receive no props still export `default` but all child components define full propTypes.

---

## Step 5: CostOverviewCards component

**File:** `tmc-redacao/src/components/custos/CostOverviewCards.jsx`

Grid: `grid grid-cols-2 lg:grid-cols-4 gap-4`

### 4 Cards (following codebase card pattern: `bg-white rounded-xl border border-light-gray p-6`):

| Card | Icon | Label | Value | Subtitle |
|------|------|-------|-------|----------|
| Custo Total | `DollarSign` (tmc-orange) | CUSTO TOTAL | `$48.23 USD` | Delta badge: `+12% vs período anterior` |
| Chamadas de IA | `Activity` (medium-gray) | CHAMADAS DE IA | `1.847` | `Sonnet: 312 · Haiku: 1.535` |
| Custo por Artigo | `FileText` (medium-gray) | CUSTO MÉDIO/ARTIGO | `$0.18` | `Baseado em 267 artigos gerados` |
| Projeção Mensal | `TrendingUp` (medium-gray) | PROJEÇÃO MENSAL | `$62.40` | `Baseado nos últimos 7 dias` |

### Sparklines in each card

Each card includes a **sparkline** (tiny line chart, ~30px height) showing the trend for that metric over the selected period. This uses the `trends` data already fetched by the parent — zero extra API cost. Render with Recharts `<LineChart>` in sparkline mode (no axes, no grid, no tooltip):

```jsx
<ResponsiveContainer width="100%" height={30}>
  <LineChart data={sparklineData}>
    <Line type="monotone" dataKey="value" stroke="#E87722" strokeWidth={1.5} dot={false} />
  </LineChart>
</ResponsiveContainer>
```

### Mini provider bar

Each card includes a **mini provider bar** (6px height, rounded, stacked horizontal bar):
- LLM = `#E87722` (tmc-orange)
- Exa = `#1A4D2E` (tmc-dark-green)
- Embeddings = `#2D5A3D` (tmc-light-green)

**Delta badge colors:**
- Cost increase: `bg-warning/10 text-warning` (amber — spending more)
- Cost decrease: `bg-success/10 text-success` (green — saving money)

**Loading:** Content-shaped skeleton cards matching actual card layout (following UsuariosPage lines 480-497 pattern):

```jsx
{[...Array(4)].map((_, i) => (
  <div key={i} className="bg-white rounded-xl border border-light-gray p-6 space-y-3">
    <div className="flex items-center gap-2">
      <Skeleton variant="circle" />
      <Skeleton variant="text" className="w-1/3" />
    </div>
    <Skeleton variant="title" className="w-1/2" />
    <Skeleton variant="text" className="w-2/3" />
    <Skeleton variant="default" className="h-1.5 w-full" />
  </div>
))}
```

**PropTypes:**

```jsx
import PropTypes from 'prop-types';

CostOverviewCards.propTypes = {
  data: PropTypes.shape({
    total_cost: PropTypes.number,
    delta_percent: PropTypes.number,
    total_calls: PropTypes.number,
    sonnet_calls: PropTypes.number,
    haiku_calls: PropTypes.number,
    avg_cost_per_article: PropTypes.number,
    articles_generated: PropTypes.number,
    projected_monthly: PropTypes.number,
    provider_split: PropTypes.shape({
      llm: PropTypes.number,
      exa: PropTypes.number,
      embeddings: PropTypes.number,
    }),
  }),
  trends: PropTypes.arrayOf(PropTypes.object),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};
```

---

## Step 6: CostTrendsChart component

**File:** `tmc-redacao/src/components/custos/CostTrendsChart.jsx`

### Problem: Stacked area chart is broken

LLM costs represent 97-99% of total spending. A stacked area chart would render Exa and Embeddings as invisible slivers. This defeats the purpose of the visualization.

### Solution: Dual-panel layout with view toggle

**Card header:** `Tendência de Custos` with a toggle: `[Todos | Sem LLM]`

The toggle uses `TabButton` from `components/ui/TabButton.jsx`:

```jsx
<div className="flex items-center justify-between mb-4">
  <h2 className="text-lg font-semibold text-dark-gray">Tendência de Custos</h2>
  <div className="flex gap-1 bg-off-white p-1 rounded-lg" role="tablist" aria-label="Modo de visualização">
    <TabButton active={chartMode === 'all'} onClick={() => setChartMode('all')}>
      Todos
    </TabButton>
    <TabButton active={chartMode === 'non-llm'} onClick={() => setChartMode('non-llm')}>
      Sem LLM
    </TabButton>
  </div>
</div>
```

**"Todos" mode** — Two charts stacked vertically:

1. **Main chart (h-[250px]):** Line chart showing total cost trend over time. Single line, `stroke="#E87722"`. This gives a clear trend without scale issues.

2. **Detail chart (h-[150px]):** Stacked area chart showing ONLY Exa + Embeddings at their own Y-axis scale. This makes non-LLM costs visible and comparable to each other.

```jsx
{/* Main: Total Cost Trend */}
<ResponsiveContainer width="100%" height={250}>
  <LineChart data={trends}>
    <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
    <XAxis dataKey="date" tickFormatter={formatDatePtBR} />
    <YAxis tickFormatter={v => `$${v.toFixed(2)}`} />
    <Tooltip content={<CustomTooltip />} />
    <Line type="monotone" dataKey="total" stroke="#E87722" strokeWidth={2} name="Custo Total" dot={false} />
  </LineChart>
</ResponsiveContainer>

<p className="text-xs text-medium-gray mt-4 mb-2 font-medium">Custos Exa + Embeddings (escala própria)</p>

{/* Detail: Non-LLM Costs at their own scale */}
<ResponsiveContainer width="100%" height={150}>
  <AreaChart data={trends}>
    <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
    <XAxis dataKey="date" tickFormatter={formatDatePtBR} />
    <YAxis tickFormatter={v => `$${v.toFixed(4)}`} />
    <Tooltip content={<CustomTooltip nonLlmOnly />} />
    <Area stackId="1" dataKey="embeddings" fill="#2D5A3D" stroke="#2D5A3D" fillOpacity={0.6} name="Embeddings" />
    <Area stackId="1" dataKey="exa" fill="#1A4D2E" stroke="#1A4D2E" fillOpacity={0.6} name="Exa (Pesquisa)" />
  </AreaChart>
</ResponsiveContainer>
```

**"Sem LLM" mode** — Only the Exa + Embeddings stacked area chart, at full height (300px). Useful for focusing on non-LLM cost patterns.

**Data shape:** `[{ date: '2026-03-01', total: 1.28, llm: 1.23, exa: 0.05, embeddings: 0.002 }, ...]`

**Custom tooltip:** Shows date + total cost + per-provider breakdown in USD.

**X-axis formatting:** `DD/MM` for daily, `Sem DD/MM` for weekly, `MMM` for monthly — all `pt-BR` locale.

**Empty state:** Use `EmptyState` component from `components/ui/EmptyState.jsx`:

```jsx
import EmptyState from '../ui/EmptyState';

<EmptyState
  icon={DollarSign}
  title="Nenhum dado de custo disponível"
  description="Não há dados de custo para o período selecionado."
/>
```

**Loading:** Content-shaped skeleton matching chart layout.

**PropTypes:**

```jsx
CostTrendsChart.propTypes = {
  data: PropTypes.arrayOf(PropTypes.shape({
    date: PropTypes.string.isRequired,
    total: PropTypes.number.isRequired,
    llm: PropTypes.number.isRequired,
    exa: PropTypes.number.isRequired,
    embeddings: PropTypes.number.isRequired,
  })),
  granularity: PropTypes.oneOf(['hour', 'day', 'week', 'month']),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};
```

---

## Step 7: CostBreakdownTable component

**File:** `tmc-redacao/src/components/custos/CostBreakdownTable.jsx`

Card header: `Custos por Ação`

### Action Name Map (Portuguese — with correct diacritics)

```js
const ACTION_LABELS = {
  generate_article:  { label: 'Gerar Artigo',           icon: Sparkles },
  edit_article:      { label: 'Editar Artigo',          icon: Edit2 },
  fact_check_scan:   { label: 'Fact-Check Scan',        icon: Shield },
  deep_verify:       { label: 'Verificação Profunda',   icon: SearchCheck },
  extract_topics:    { label: 'Extrair Tópicos',        icon: ListTree },
  merge_topics:      { label: 'Mesclar Tópicos',        icon: Merge },
  generate_tags:     { label: 'Gerar Tags',             icon: Tag },
  research:          { label: 'Pesquisar (Exa)',        icon: Globe },
  system_rss:        { label: 'Sistema: RSS',           icon: Rss },
  system_embedding:  { label: 'Sistema: Embeddings',    icon: Database },
  system_scoring:    { label: 'Sistema: Scoring',       icon: BarChart3 },
  system_clustering: { label: 'Sistema: Clustering',    icon: Network },
};
```

### Table Columns

| Ação | Chamadas | Custo Total | Custo Médio | % do Total |
|------|----------|-------------|-------------|------------|
| Icon + PT label | Formatted count | `$X.XX` | `$X.XXXX` | % with thin colored bar |

Sortable by any column (click header toggles asc/desc). Default sort: `Custo Total` descending.

### Accessibility (following UsuariosPage pattern)

```jsx
<table className="w-full" role="table" aria-label="Custos por ação">
  <thead className="bg-off-white border-b border-light-gray">
    <tr>
      <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">Ação</th>
      <th scope="col" className="...">Chamadas</th>
      {/* ... */}
    </tr>
  </thead>
```

Decorative icons: `aria-hidden="true"`.
Sorted column header: `aria-sort="ascending"` or `aria-sort="descending"`.

**Desktop:** Standard table (follows UsuariosPage pattern).
**Mobile:** Card layout per action (icon + label + cost + calls).

**Loading:** Content-shaped skeleton table with 8 rows.

**PropTypes:**

```jsx
CostBreakdownTable.propTypes = {
  data: PropTypes.arrayOf(PropTypes.shape({
    action: PropTypes.string.isRequired,
    call_count: PropTypes.number.isRequired,
    total_cost: PropTypes.number.isRequired,
    avg_cost: PropTypes.number.isRequired,
    pct_of_total: PropTypes.number.isRequired,
  })),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};
```

---

## Step 8: CostByUserTable component

**File:** `tmc-redacao/src/components/custos/CostByUserTable.jsx`

Card header: `Custos por Usuário` with search input (`Buscar por nome ou email...`).

### Table Columns

| Usuário | Artigos | Edições | Scans | Custo Total | Custo/Artigo |
|---------|---------|---------|-------|-------------|--------------|
| Avatar + name + email | Count | Count | Count | `$X.XX` (bold if highest) | `$X.XX` |

### Accessibility

```jsx
<table className="w-full" role="table" aria-label="Custos por usuário">
  <thead className="bg-off-white border-b border-light-gray">
    <tr>
      <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">Usuário</th>
      {/* ... */}
    </tr>
  </thead>
```

**Visual highlights:**
- Highest cost user gets left border: `border-l-4 border-tmc-orange`
- If cost/article > 2x average: `AlertTriangle` icon with `aria-hidden="true"` in `text-warning`
- System/timer row at bottom: "Sistema (Automático)" with `Cpu` icon

**Sort:** Internal state (`sortField`, `sortDirection`). Sorted array with `useMemo`.

**Desktop:** Full table. **Mobile:** Card per user.

**PropTypes:**

```jsx
CostByUserTable.propTypes = {
  data: PropTypes.arrayOf(PropTypes.shape({
    user_id: PropTypes.number,
    user_name: PropTypes.string.isRequired,
    user_email: PropTypes.string,
    articles_generated: PropTypes.number.isRequired,
    edits: PropTypes.number,
    scans: PropTypes.number,
    total_cost: PropTypes.number.isRequired,
    cost_per_article: PropTypes.number,
  })),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};
```

---

## Step 8b: CostBySourceTable component

**File:** `tmc-redacao/src/components/custos/CostBySourceTable.jsx`

Extracted as its own component (not inline in CustosPage) for maintainability.

Card header: `Custos por Fonte`

### Table Columns

| Fonte | Artigos Coletados | Custo Total | Custo/Artigo |
|-------|-------------------|-------------|--------------|
| Source name + category badge | Count | `$X.XX` | `$X.XX` |

Color dot per source: green (`text-success`) if cost/article < median, orange (`text-warning`) if 1.5-2x, red (`text-error`) if > 2x.

### Accessibility

```jsx
<table className="w-full" role="table" aria-label="Custos por fonte RSS">
  <thead className="bg-off-white border-b border-light-gray">
    <tr>
      <th scope="col" className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide">Fonte</th>
      {/* ... */}
    </tr>
  </thead>
```

**Desktop:** Full table. **Mobile:** Card per source.

**PropTypes:**

```jsx
CostBySourceTable.propTypes = {
  data: PropTypes.arrayOf(PropTypes.shape({
    source_id: PropTypes.number.isRequired,
    source_name: PropTypes.string.isRequired,
    category: PropTypes.string,
    articles_collected: PropTypes.number.isRequired,
    total_cost: PropTypes.number.isRequired,
    cost_per_article: PropTypes.number.isRequired,
  })),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};
```

---

## Step 9: WhatIfCalculator component

**File:** `tmc-redacao/src/components/custos/WhatIfCalculator.jsx`

Card with orange top border: `border-t-4 border-tmc-orange rounded-xl bg-white border border-light-gray p-6`

Self-contained — receives `sourceEstimate` data (avg costs per source) from parent, owns its own input state.

### UX: Number Input as PRIMARY, Textarea as Expandable Advanced

The admin doesn't always have specific RSS URLs. The **primary interface** is a simple number input for quick ballparks, with an expandable "Avançado" section for pasting URLs.

**Primary input:**

```jsx
<label className="block text-sm font-medium text-dark-gray mb-2">
  Quantidade de novas fontes
</label>
<input
  type="number"
  min="1"
  max="100"
  value={sourceCount}
  onChange={(e) => setSourceCount(Number(e.target.value))}
  className="w-32 px-3 py-2 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange min-h-[44px]"
  aria-label="Quantidade de novas fontes RSS"
/>
```

**Advanced section (expandable):**

```jsx
<button
  type="button"
  onClick={() => setShowAdvanced(!showAdvanced)}
  className="text-sm text-tmc-orange hover:underline flex items-center gap-1 min-h-[44px]"
>
  <ChevronDown className={`transition-transform ${showAdvanced ? 'rotate-180' : ''}`} size={16} aria-hidden="true" />
  Avançado: colar links RSS
</button>

{showAdvanced && (
  <div>
    <label className="block text-sm font-medium text-dark-gray mb-2">
      Cole os links RSS das novas fontes (um por linha)
    </label>
    <textarea
      value={urlText}
      onChange={handleUrlChange}
      placeholder={"https://rss.example.com/feed1\nhttps://rss.example.com/feed2"}
      className="w-full p-3 border border-light-gray rounded-lg text-sm min-h-[100px] focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
      aria-label="Links RSS das novas fontes, um por linha"
    />
    <p className="text-xs text-medium-gray mt-1">{parsedCount} fontes detectadas</p>
  </div>
)}
```

When URLs are pasted, `sourceCount` auto-updates to the number of non-empty lines. When number input changes and textarea has content, textarea clears.

### Auto-Calculated Projections (from platform averages)

The system uses `sourceEstimate` data from the API which provides:
- `avg_articles_per_source_per_day` — how many articles a typical RSS source collects daily
- `avg_cost_per_article_pipeline` — avg cost of classification + scoring + embedding per article
- `avg_cost_per_generated_article` — avg cost of generating an article (Exa + Sonnet + CoVe)
- `avg_articles_generated_per_source` — how many source articles become generated articles

### Output (real-time, recalculates as input changes)

```
Baseado nas médias atuais da plataforma:

Coleta e Processamento (por fonte/dia):
   ~20 artigos coletados/dia (média atual)
   Classificação + Scoring + Embedding: $0.03/dia por fonte

Geração estimada:
   ~2 artigos gerados por fonte/semana (média atual)
   Custo médio por artigo gerado: $0.18

CUSTO ADICIONAL ESTIMADO (5 fontes):
   Diário:  $0.15 + gerações sob demanda
   Mensal:  $4.50 + ~$14.40 em gerações
   Anual:   $54.00 + ~$172.80 em gerações
```

**Key insight shown:** Separate pipeline costs (automatic, predictable) from generation costs (on-demand, depends on user behavior). This helps the admin understand that adding sources is cheap — the cost comes from generating articles from them.

Total row highlighted: `bg-tmc-orange/5 border border-tmc-orange/20 rounded-lg p-4 text-lg font-bold`.

**Info callout:** `<div className="bg-tmc-orange/10 border border-tmc-orange/30 rounded-lg p-4 text-sm text-tmc-orange">` explaining: "Os custos de pipeline (coleta, classificação, scoring, embedding) são automáticos. Os custos de geração dependem de quantos artigos os redatores criam a partir dessas fontes."

**Mobile:** Number input and output stack naturally (single column).

**PropTypes:**

```jsx
WhatIfCalculator.propTypes = {
  sourceEstimate: PropTypes.shape({
    avg_articles_per_source_per_day: PropTypes.number,
    avg_cost_per_article_pipeline: PropTypes.number,
    avg_cost_per_generated_article: PropTypes.number,
    avg_articles_generated_per_source: PropTypes.number,
  }),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};
```

---

## Step 10: Build + Lint verification

```bash
cd tmc-redacao && npm run build && npm run lint
```

---

## Color Allocation

| Element | Color | Tailwind |
|---------|-------|----------|
| LLM (Anthropic) costs | `#E87722` | `bg-tmc-orange` |
| Exa costs | `#1A4D2E` | `bg-tmc-dark-green` |
| Embedding costs | `#2D5A3D` | `bg-tmc-light-green` |
| Cost increase (bad) | `#F59E0B` | `text-warning` |
| Cost decrease (good) | `#10B981` | `text-success` |
| Cost spike alert | `#EF4444` | `text-error` |
| Card background | `#FFFFFF` | `bg-white` |
| Page background | `#F5F5F5` | `bg-off-white` |
| Card border | `#E0E0E0` | `border-light-gray` |
| Primary text | `#333333` | `text-dark-gray` |
| Secondary text | `#666666` | `text-medium-gray` |

**Note:** No `tailwind.config.js` exists. The project uses Tailwind CSS v4 with `@theme` in `src/index.css`. All custom color tokens (`tmc-orange`, `dark-gray`, `medium-gray`, `light-gray`, `off-white`, `success`, `warning`, `error`) are defined there. Do NOT use raw Tailwind grays (`text-gray-500`, `border-gray-200`, etc.) — always use the project theme tokens.

---

## Tailwind Class Reference (codebase norms)

| Pattern | Correct Class | NOT This |
|---------|--------------|----------|
| Card container | `bg-white rounded-xl border border-light-gray p-6` | `p-4 border-gray-200` |
| Page title | `text-2xl font-bold text-dark-gray` | `text-gray-900` |
| Subtitle | `text-sm text-medium-gray mt-1` | `text-gray-500` |
| Table header | `bg-off-white border-b border-light-gray px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide` | `bg-gray-50 text-gray-600` |
| Section divider | `border-light-gray` | `border-gray-200` |
| Icon (decorative) | `text-medium-gray` + `aria-hidden="true"` | `text-gray-400` |

---

## Responsive Strategy

All sections use `md:` breakpoint (768px) as primary:

| Component | Mobile (<md) | Desktop (>=md) |
|-----------|-------------|----------------|
| Period Selector | `<select>` dropdown | TabButton row (`flex-wrap`) |
| Overview Cards | 2-col grid | 4-col grid |
| Trends Chart | height 200px main / 120px detail, rotated X labels | height 250px main / 150px detail, full labels |
| Action Table | Card layout per action | Full table |
| User Table | Card per user | Full sortable table |
| Source Table | Card per source | Full table |
| Calculator | Stacked (input above, output below) | Side-by-side |

All interactive elements: `min-h-[44px]` touch target (WCAG 2.5.5).

---

## Loading & Error Per Section

### Loading

Content-shaped skeletons that match actual card/chart/table layouts. Reference: UsuariosPage lines 480-497.

- **Cards:** 4 skeleton cards with circle + title + text + bar
- **Chart:** Skeleton rectangle at chart height with title and toggle placeholders
- **Tables:** Skeleton table header + 5-8 rows with circle + text columns
- **Calculator:** Skeleton input + output blocks

All skeletons use the `Skeleton` component from `components/ui/Skeleton.jsx`.

### Error

Per-section error card following UsuariosPage pattern (lines 499-515):

```jsx
<div className="bg-white rounded-xl border border-light-gray p-8">
  <div className="flex flex-col items-center justify-center py-8">
    <AlertCircle size={32} className="text-error mb-4" aria-hidden="true" />
    <p className="text-lg font-semibold text-dark-gray mb-2">Erro ao carregar dados</p>
    <p className="text-sm text-medium-gray mb-4">{error}</p>
    <button
      onClick={() => onRetry()}
      className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center gap-2 min-h-[44px]"
    >
      <RefreshCw size={16} aria-hidden="true" />
      Tentar novamente
    </button>
  </div>
</div>
```

`retrySection(key)` re-fetches only that section.

### Empty Data

Use `EmptyState` from `components/ui/EmptyState.jsx`:

```jsx
<EmptyState
  icon={DollarSign}
  title="Nenhum dado de custo disponível"
  description="Não há registros de custo para o período selecionado. Os dados aparecerão conforme as operações de IA forem executadas."
/>
```

### Status Feedback

Use `StatusMessage` from `components/ui/StatusMessage.jsx` for transient feedback (e.g., CSV export success):

```jsx
<StatusMessage
  type="success"
  message="CSV exportado com sucesso"
  isVisible={statusMessage.isVisible}
  onDismiss={() => setStatusMessage({ ...statusMessage, isVisible: false })}
/>
```

---

## Accessibility Checklist

Following UsuariosPage patterns throughout:

| Pattern | Implementation |
|---------|---------------|
| Table semantics | `role="table"` + `aria-label` on every `<table>` |
| Column headers | `scope="col"` on all `<th>` elements |
| Decorative icons | `aria-hidden="true"` on all Lucide icons that are decorative |
| Touch targets | `min-h-[44px]` on all buttons and interactive elements |
| Dynamic content | `role="status"` + `aria-live="polite"` on loading/empty/error states |
| Tab navigation | `role="tablist"` container + `TabButton` with `role="tab"` + `aria-selected` |
| Sort controls | `aria-sort="ascending"` / `"descending"` on sorted `<th>` |
| Search input | `aria-label="Buscar por nome ou email"` on filter inputs |

---

## Performance

1. **Lazy loading:** CustosPage loaded via `lazy()` — recharts chunk only downloads when admin visits
2. **Parallel fetch:** All 6 APIs fire simultaneously with `Promise.allSettled`
3. **AbortController:** Stale requests cancelled on period change (prevents wrong-period data rendering)
4. **200ms debounce:** Period selector debounced to prevent rapid-fire requests
5. **React.memo:** All child components wrapped in `React.memo()` to prevent unnecessary re-renders
6. **useMemo for sorts:** Sorted arrays computed with `useMemo` keyed on data + sort state
7. **Manual chunk:** recharts isolated to `vendor-charts` chunk in vite.config
8. **Sparklines from existing data:** Overview card sparklines use trends data already fetched — zero extra API cost

---

## Portuguese Diacritics Checklist

All user-facing strings MUST use correct PT-BR diacritics:

| Wrong | Correct |
|-------|---------|
| `Projecao Mensal` | `Projeção Mensal` |
| `Verificacao Profunda` | `Verificação Profunda` |
| `Tendencia de Custos` | `Tendência de Custos` |
| `Nenhum dado de custo disponivel` | `Nenhum dado de custo disponível` |
| `Configuracoes` | `Configurações` |
| `Custos por Acao` | `Custos por Ação` |
| `Custos por Usuario` | `Custos por Usuário` |
| `Extrair Topicos` | `Extrair Tópicos` |
| `Mesclar Topicos` | `Mesclar Tópicos` |

**Rule:** For `titles` map entries in App.jsx and for `aria-label` attributes, always use full accented Portuguese. For constant keys and URL paths, use ASCII-only.

---

## Verification

1. `npm run build` — no errors, recharts in `vendor-charts` chunk (verify build output)
2. `npm run lint` — no warnings
3. Navigate to `/configuracoes` — "Custos" menu item visible for admin users only
4. Click "Custos" — page loads with period selector defaulting to 30d
5. All 6 sections render (with mock data if `VITE_COSTS_USE_MOCK=true`)
6. Change period — all sections reload, previous requests aborted
7. Rapid period clicks — debounce prevents multiple simultaneous fetches
8. Toggle chart mode — "Todos" shows dual panel, "Sem LLM" shows Exa+Embeddings only
9. Mobile — sections stack correctly, tables become cards, period selector shows `<select>`
10. Error state — disconnect API → each section shows `AlertCircle` + "Tentar novamente" independently
11. Empty state — no cost data → shows `EmptyState` component with friendly message
12. All PropTypes validated — no console warnings
13. All interactive elements have `min-h-[44px]` touch targets
14. All tables have `role="table"` + `aria-label`, all `<th>` have `scope="col"`
15. All decorative icons have `aria-hidden="true"`
16. CSV export button works and shows success `StatusMessage`

---

## Changes from v1

1. **Mock data strategy** — changed from "return mock on 404" to explicit `VITE_COSTS_USE_MOCK` env var
2. **AbortController** — added request cancellation on period change
3. **200ms debounce** — added to period selector
4. **Chart redesign** — replaced stacked area with dual-panel (total line + non-LLM detail) + "Sem LLM" toggle
5. **CostBySourceTable** — extracted from inline JSX to its own component
6. **Period selector** — uses actual `TabButton` component + `<select>` fallback for mobile
7. **Content-shaped skeletons** — loading states match actual layouts
8. **Error pattern** — follows UsuariosPage pattern with `AlertCircle` + "Tentar novamente"
9. **Empty state** — uses existing `EmptyState` component
10. **Status feedback** — uses existing `StatusMessage` component
11. **Sparklines** — added to overview cards using existing trends data
12. **WhatIfCalculator UX** — number input as primary, expandable textarea for URLs
13. **PropTypes** — full definitions for every component
14. **Accessibility** — comprehensive checklist following UsuariosPage patterns
15. **Tailwind class reference** — prevents using raw Tailwind grays
16. **Portuguese diacritics checklist** — explicit table of correct strings
17. **"Atualizado em" timestamp** and **"Exportar CSV" button** added to page header
18. **Location note** — clarifies CustosPage goes in `pages/config/` (not `pages/`)
19. **Build verification note** — warns about d3 sub-package chunk leakage
20. **AbortController signal** — passed to every API function
