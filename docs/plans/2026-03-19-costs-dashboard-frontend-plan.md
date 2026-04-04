# Costs Dashboard — Frontend Implementation Plan

**Date:** 2026-03-19
**Status:** Review
**Related:** [Backend Plan](2026-03-19-costs-dashboard-plan.md)

## Context

TMC admins need full cost traceability for all AI operations on the platform. Currently, the only cost-related UI is the kill switch on SistemaPage showing `estimatedSavings` and `avgHourlyCost`. The backend already logs every LLM call to `llm_usage_log` (migration 009) with token counts, cost USD, model, task_type, and latency — but there's **no user attribution**, **no Exa/embedding tracking**, **no cost API endpoints**, and **no dashboard UI**.

This plan covers the **frontend dashboard only** — what admins will see. Backend API endpoints and migrations are covered in the existing plan at `docs/plans/2026-03-19-costs-dashboard-plan.md` and will be implemented separately.

**Approach:** Build the full frontend with mock data fallbacks so it can be wired to real APIs as backend endpoints become available.

---

## Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `tmc-redacao/src/services/costsApi.js` | API service — 6 endpoint wrappers using `fetchApi` |
| 2 | `tmc-redacao/src/pages/config/CustosPage.jsx` | Main page — orchestrates state, period selector, all sections |
| 3 | `tmc-redacao/src/components/custos/CostOverviewCards.jsx` | 4 top-row metric cards with deltas and mini provider bars |
| 4 | `tmc-redacao/src/components/custos/CostTrendsChart.jsx` | Recharts stacked area chart (LLM/Exa/Embeddings over time) |
| 5 | `tmc-redacao/src/components/custos/CostBreakdownTable.jsx` | Action cost map — horizontal bar + sortable table |
| 6 | `tmc-redacao/src/components/custos/CostByUserTable.jsx` | Per-user cost table with search and sort |
| 7 | `tmc-redacao/src/components/custos/WhatIfCalculator.jsx` | Interactive cost projection calculator |

## Files to Modify

| File | Change |
|------|--------|
| `tmc-redacao/src/App.jsx` | Line ~20: add lazy import. Line ~53: add title. Line ~205: add route |
| `tmc-redacao/src/pages/ConfiguracoesPage.jsx` | Line 3: add `DollarSign` import. Line 24: add menu item |
| `tmc-redacao/vite.config.js` | Add `recharts` to manual chunks for code-splitting |

---

## Step 1: Install recharts

```bash
cd tmc-redacao && npm install recharts
```

Add to `vite.config.js` manual chunks: `'vendor-charts': ['recharts']` so it doesn't bloat the main vendor bundle. Since CustosPage is lazy-loaded, recharts only downloads when an admin visits the page.

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

No caching — cost data changes constantly and is admin-only (low traffic).

**Mock data:** Each function should return mock data if the API returns 404 (endpoint not yet built), so the frontend can be developed and demoed independently. Include a `// TODO: remove mock fallback when backend is ready` comment.

---

## Step 3: Wire up route and navigation

### App.jsx (3 edits)

1. **Line ~20** — Add lazy import:
   ```jsx
   const CustosPage = lazy(() => import('./pages/config/CustosPage'));
   ```

2. **Line ~53** — Add title mapping:
   ```js
   '/configuracoes/custos': 'Custos - Configuracoes',
   ```

3. **Line ~205** — Add route inside `/configuracoes`:
   ```jsx
   <Route path="custos" element={<ProtectedRoute permission="manage_users"><CustosPage /></ProtectedRoute>} />
   ```

### ConfiguracoesPage.jsx (2 edits)

1. **Line 3** — Add `DollarSign` to lucide import:
   ```jsx
   import { Newspaper, Users, Power, DollarSign, Menu, X } from 'lucide-react';
   ```

2. **Line 24** — Add menu item (admin-only, after Sistema):
   ```jsx
   ...(canManageUsers ? [{ path: '/configuracoes/custos', label: 'Custos', icon: DollarSign }] : []),
   ```

---

## Step 4: Create CustosPage.jsx (orchestrator)

**File:** `tmc-redacao/src/pages/config/CustosPage.jsx`

**Container:** `<div className="max-w-6xl mx-auto space-y-6">` (wider than SistemaPage's `max-w-3xl` because charts and tables need horizontal space).

### Page Header + Period Selector

```
[h1: "Custos"]  [subtitle: "Acompanhe os gastos com IA, busca e embeddings"]     [Period: Hoje | 7d | 30d | 90d | Ano]
```

Period selector: row of buttons styled like TabButton. Default: `30d`. Changing period triggers `fetchAllData(period)`.

### State Management

All state at page level — no context, no Zustand (matches SistemaPage/UsuariosPage pattern):

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
```

### Data Fetching

`useEffect` on `period` change calls `fetchAllData(period)` which:
1. Computes `startDate`/`endDate`/`granularity` from period string
2. Fires all 6 API calls with `Promise.allSettled` (parallel)
3. Updates each section's data + loading + error independently
4. Partial rendering: if one endpoint fails, others still render

### periodToDateRange helper

Inline pure function (~15 lines):
- `today` → start=midnight today, granularity=`hour`
- `7d` → -7 days, granularity=`day`
- `30d` → -30 days, granularity=`day`
- `90d` → -90 days, granularity=`week`
- `year` → Jan 1 current year, granularity=`month`

### Section Layout

```
[Period Selector]
[Overview Cards — 4 cards in row]
[Cost Trends Chart — stacked area]
[Cost by Action — horizontal bars + table]
[Cost by User — sortable table]
[Cost by Source — sortable table]
[What-If Calculator]
```

Each section is a white card (`bg-white rounded-xl border border-light-gray p-6`) with its own loading skeleton and error retry.

---

## Step 5: CostOverviewCards component

**File:** `tmc-redacao/src/components/custos/CostOverviewCards.jsx`

Grid: `grid grid-cols-2 lg:grid-cols-4 gap-4`

### 4 Cards (following SistemaPage card pattern):

| Card | Icon | Label | Value | Subtitle |
|------|------|-------|-------|----------|
| Custo Total | `DollarSign` (tmc-orange) | CUSTO TOTAL | `$48.23 USD` | Delta badge: `+12% vs periodo anterior` |
| Chamadas de IA | `Activity` (gray-400) | CHAMADAS DE IA | `1.847` | `Sonnet: 312 · Haiku: 1.535` |
| Custo por Artigo | `FileText` (gray-400) | CUSTO MEDIO/ARTIGO | `$0.18` | `Baseado em 267 artigos gerados` |
| Projecao Mensal | `TrendingUp` (gray-400) | PROJECAO MENSAL | `$62.40` | `Baseado nos ultimos 7 dias` |

Each card includes a **mini provider bar** (6px height, rounded, stacked horizontal bar):
- LLM = `#E87722` (tmc-orange)
- Exa = `#1A4D2E` (dark-green)
- Embeddings = `#2D5A3D` (light-green)

**Delta badge colors:**
- Cost increase: `bg-warning/10 text-warning` (amber — spending more)
- Cost decrease: `bg-success/10 text-success` (green — saving money)

**Loading:** 4 skeleton cards with `Skeleton variant="title"` + `Skeleton variant="text"`.

---

## Step 6: CostTrendsChart component

**File:** `tmc-redacao/src/components/custos/CostTrendsChart.jsx`

Card header: `Tendencia de Custos` with optional granularity sub-toggle.

### Recharts Configuration

```jsx
<ResponsiveContainer width="100%" height={300}> // mobile: 200
  <AreaChart data={trends}>
    <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
    <XAxis dataKey="date" tickFormatter={formatDatePtBR} />
    <YAxis tickFormatter={v => `$${v.toFixed(2)}`} />
    <Tooltip content={<CustomTooltip />} />
    <Legend />
    <Area stackId="1" dataKey="embeddings" fill="#2D5A3D" stroke="#2D5A3D" name="Embeddings" />
    <Area stackId="1" dataKey="exa" fill="#1A4D2E" stroke="#1A4D2E" name="Exa (Pesquisa)" />
    <Area stackId="1" dataKey="llm" fill="#E87722" stroke="#E87722" name="LLM (Anthropic)" />
  </AreaChart>
</ResponsiveContainer>
```

**Data shape:** `[{ date: '2026-03-01', llm: 1.23, exa: 0.05, embeddings: 0.002 }, ...]`

**Custom tooltip:** Shows date + total cost + per-provider breakdown in USD.

**X-axis formatting:** `DD/MM` for daily, `Sem DD/MM` for weekly, `MMM` for monthly — all `pt-BR` locale.

**Empty state:** Centered text "Nenhum dado de custo disponivel para este periodo." with grayed DollarSign icon.

**Loading:** Skeleton rectangle at chart height (`h-[300px]`).

---

## Step 7: CostBreakdownTable component

**File:** `tmc-redacao/src/components/custos/CostBreakdownTable.jsx`

Card header: `Custos por Acao`

### Action Name Map (Portuguese)

```js
const ACTION_LABELS = {
  generate_article:  { label: 'Gerar Artigo',           icon: Sparkles },
  edit_article:      { label: 'Editar Artigo',          icon: Edit2 },
  fact_check_scan:   { label: 'Fact-Check Scan',        icon: Shield },
  deep_verify:       { label: 'Verificacao Profunda',   icon: SearchCheck },
  extract_topics:    { label: 'Extrair Topicos',        icon: ListTree },
  merge_topics:      { label: 'Mesclar Topicos',        icon: Merge },
  generate_tags:     { label: 'Gerar Tags',             icon: Tag },
  research:          { label: 'Pesquisar (Exa)',        icon: Globe },
  system_rss:        { label: 'Sistema: RSS',           icon: Rss },
  system_embedding:  { label: 'Sistema: Embeddings',    icon: Database },
  system_scoring:    { label: 'Sistema: Scoring',       icon: BarChart3 },
  system_clustering: { label: 'Sistema: Clustering',    icon: Network },
};
```

### Table Columns

| Acao | Chamadas | Custo Total | Custo Medio | % do Total |
|------|----------|-------------|-------------|------------|
| Icon + PT label | Formatted count | `$X.XX` | `$X.XXXX` | % with thin colored bar |

Sortable by any column (click header toggles asc/desc). Default sort: `Custo Total` descending.

**Desktop:** Standard table (follows UsuariosPage pattern).
**Mobile:** Card layout per action (icon + label + cost + calls).

**Loading:** Skeleton table with 8 rows.

---

## Step 8: CostByUserTable component

**File:** `tmc-redacao/src/components/custos/CostByUserTable.jsx`

Card header: `Custos por Usuario` with search input (`Buscar por nome ou email...`).

### Table Columns

| Usuario | Artigos | Edicoes | Scans | Custo Total | Custo/Artigo |
|---------|---------|---------|-------|-------------|--------------|
| Avatar + name + email | Count | Count | Count | `$X.XX` (bold if highest) | `$X.XX` |

**Visual highlights:**
- Highest cost user gets left border: `border-l-4 border-tmc-orange`
- If cost/article > 2x average: `AlertTriangle` icon in `text-warning`
- System/timer row at bottom: "Sistema (Automatico)" with `Cpu` icon

**Sort:** Internal state (`sortField`, `sortDirection`). Sorted array with `useMemo`.

**Desktop:** Full table. **Mobile:** Card per user.

### Per-Source Table (inline in CustosPage)

Same table pattern for RSS sources:

| Fonte | Artigos Coletados | Custo Total | Custo/Artigo |
|-------|-------------------|-------------|--------------|
| Source name + category badge | Count | `$X.XX` | `$X.XX` |

Color dot per source: green if cost/article < median, orange 1.5-2x, red > 2x. This is ~40 lines of JSX inline in CustosPage — no separate component needed unless it grows.

---

## Step 9: WhatIfCalculator component

**File:** `tmc-redacao/src/components/custos/WhatIfCalculator.jsx`

Card with orange top border: `border-t-4 border-tmc-orange rounded-xl`

Self-contained — receives `sourceEstimate` data (avg costs per source) from parent, owns its own input state.

### UX: Simple Input — Just RSS Links

The admin doesn't know technical details like "articles per source per day". They just want to paste RSS URLs and see cost projections. The system calculates everything automatically using **existing platform averages**.

### Input

A single `<textarea>` where the admin pastes RSS feed URLs (one per line):

```
Label: "Cole os links RSS das novas fontes (um por linha)"
Placeholder: "https://rss.example.com/feed1\nhttps://rss.example.com/feed2"
```

Below the textarea: a counter showing `X fontes detectadas` (parsed by counting non-empty lines).

Alternatively, a simple number input: `Quantidade de novas fontes: [5]` for admins who don't have specific URLs yet but want a ballpark.

### Auto-Calculated Projections (from platform averages)

The system uses `sourceEstimate` data from the API which provides:
- `avg_articles_per_source_per_day` — how many articles a typical RSS source collects daily
- `avg_cost_per_article_pipeline` — avg cost of classification + scoring + embedding per article
- `avg_cost_per_generated_article` — avg cost of generating an article (Exa + Sonnet + CoVe)
- `avg_articles_generated_per_source` — how many source articles become generated articles

### Output (real-time, recalculates as URLs are added/removed)

```
Baseado nas medias atuais da plataforma:

Coleta e Processamento (por fonte/dia):
   ~20 artigos coletados/dia (media atual)
   Classificacao + Scoring + Embedding: $0.03/dia por fonte

Geracao estimada:
   ~2 artigos gerados por fonte/semana (media atual)
   Custo medio por artigo gerado: $0.18

CUSTO ADICIONAL ESTIMADO (5 fontes):
   Diario:  $0.15 + geracoes sob demanda
   Mensal:  $4.50 + ~$14.40 em geracoes
   Anual:   $54.00 + ~$172.80 em geracoes
```

**Key insight shown:** Separate pipeline costs (automatic, predictable) from generation costs (on-demand, depends on user behavior). This helps the admin understand that adding sources is cheap — the cost comes from generating articles from them.

Total row highlighted: `bg-tmc-orange/5 border border-tmc-orange/20 rounded-lg p-4 text-lg font-bold`.

**Info callout:** A small `bg-blue-50 border-blue-200` box explaining: "Os custos de pipeline (coleta, classificacao, scoring, embedding) sao automaticos. Os custos de geracao dependem de quantos artigos os redatores criam a partir dessas fontes."

**Mobile:** Textarea stacks above output (natural form layout).

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

---

## Responsive Strategy

All sections use `md:` breakpoint (768px) as primary:

| Component | Mobile (<md) | Desktop (>=md) |
|-----------|-------------|----------------|
| Overview Cards | 2-col grid | 4-col grid |
| Trends Chart | height 200px, rotated X labels | height 300px, full labels |
| Action Table | Card layout per action | Full table |
| User Table | Card per user | Full sortable table |
| Source Table | Card per source | Full table |
| Calculator | Stacked (inputs above, output below) | Side-by-side |

---

## Loading & Error Per Section

**Loading:** Each section independently shows a Skeleton matching its shape. Cards -> skeleton cards. Chart -> skeleton rectangle. Tables -> skeleton rows.

**Error:** Per-section error card (AlertCircle + message + "Tentar novamente" button). `retrySection(key)` re-fetches only that section.

**Empty data:** EmptyState with DollarSign icon: "Nenhum dado de custo encontrado para este periodo."

---

## Performance

1. **Lazy loading:** CustosPage loaded via `lazy()` — recharts chunk only downloads when admin visits
2. **Parallel fetch:** All 6 APIs fire simultaneously with `Promise.allSettled`
3. **React.memo:** All child components wrapped in `React.memo()` to prevent unnecessary re-renders
4. **useMemo for sorts:** Sorted arrays computed with `useMemo` keyed on data + sort state
5. **Manual chunk:** recharts isolated to `vendor-charts` chunk in vite.config

---

## Verification

1. `npm run build` — no errors, recharts in separate chunk
2. `npm run lint` — no warnings
3. Navigate to `/configuracoes` — "Custos" menu item visible for admin users only
4. Click "Custos" — page loads with period selector defaulting to 30d
5. All 6 sections render (with mock data if backend not ready)
6. Change period — all sections reload
7. Mobile — sections stack correctly, tables become cards
8. Error state — disconnect API -> each section shows retry button independently
9. Empty state — no cost data -> shows friendly empty message
