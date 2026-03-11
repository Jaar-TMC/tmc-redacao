# Spec: Criar por Prompt (Create from Topic Research)

**Status:** Draft
**Author:** Claude (agentic spec generation)
**Date:** 2026-03-11
**Priority:** High

## 1. Vision

Allow journalists to generate high-quality articles by describing a **topic** instead of selecting pre-collected RSS sources. The system uses Exa AI to research the topic in real-time, presents verified sources to the user for review/selection, then feeds those sources into the existing generation pipeline with full anti-hallucination safeguards.

**User story:** "As a journalist, I want to type 'conflito Irã e EUA esta semana' and have the system research fresh sources, let me review them, then generate a verified article — so I can cover breaking topics not yet in my RSS feeds."

## 2. How It Differs from Existing "Criar do Zero"

| Aspect | Criar do Zero (existing) | Criar por Prompt (new) |
|--------|-------------------------|----------------------|
| Source | User pastes text manually | Exa researches web in real-time |
| Input | Raw text (textarea) | Topic description (prompt) |
| Source validation | User responsible for quality | System fetches + user curates |
| texto_base | Whatever user pasted | Synthesized from selected Exa results |
| Enrichment | Normal Phase 1 (supplementary) | Research IS the source material |
| Min chars gate | Applies to pasted text | Applies to assembled Exa material |

**Key principle:** We don't skip the source step — we **automate** it. The user still sees and approves sources before generation, maintaining "humans above the loop."

## 3. User Flow

```
┌──────────────────────────────────────────────────────────────────┐
│ Step 0: SelecionarFontePage                                      │
│ User clicks new card: "Criar por Prompt" (🔍 Research icon)      │
│ setFonte('prompt', {})                                           │
└────────────────────────┬─────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────────┐
│ Step 1: TextoBasePage → TextoBasePrompt (NEW variant)            │
│                                                                   │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ A) Prompt Input                                              │  │
│ │ - Textarea: "Descreva o tema que deseja pesquisar..."        │  │
│ │ - Min 30 chars, max 500 chars                                │  │
│ │ - Optional: date range picker (default: last 7 days)         │  │
│ │ - Optional: category hint dropdown (politica, economia, etc) │  │
│ │ - Button: "Pesquisar Fontes" → calls POST /api/research      │  │
│ └─────────────────────────────────────────────────────────────┘  │
│                         │                                         │
│                         ▼                                         │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ B) Source Review (after Exa search)                          │  │
│ │ - List of Exa results as selectable cards:                   │  │
│ │   [✓] "Irã anuncia..." - Reuters (11/03/2026) [280 words]   │  │
│ │   [✓] "EUA respondem..." - AP News (11/03/2026) [350 words]  │  │
│ │   [ ] "Análise: tensões..." - BBC (10/03/2026) [420 words]   │  │
│ │   [✓] "ONU convoca..." - G1 (11/03/2026) [190 words]        │  │
│ │ - Total selected: 3 sources, ~820 words                      │  │
│ │ - Minimum: 1 source selected                                 │  │
│ │ - "Pesquisar novamente" button (refine query)                │  │
│ │ - Button: "Continuar com X fontes selecionadas"              │  │
│ └─────────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ texto_base = assembled from selected sources
                         │ titulo_fonte = user's original prompt
                         │ source_type = "prompt"
                         │
┌────────────────────────▼─────────────────────────────────────────┐
│ Step 2: ConfigurarPage (UNCHANGED)                                │
│ - Category, tone, tipo_materia, etc.                              │
│ - Same UI, same options                                           │
└────────────────────────┬─────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────────┐
│ Step 3: RevisarPage (MINOR CHANGES)                               │
│ - Shows "Fonte: Pesquisa por prompt" badge                        │
│ - Shows source URLs from research                                 │
│ - Shows assembled texto_base preview                              │
│ - Same generation progress UI                                     │
└────────────────────────┬─────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────────┐
│ Step 4: CriarPostPage / Editor (UNCHANGED)                        │
│ - Same editor with verification data                              │
│ - source_urls displayed for attribution                           │
└──────────────────────────────────────────────────────────────────┘
```

## 4. Backend Architecture

### 4.1 New Endpoint: `POST /api/research`

**Purpose:** Executes Exa web search based on a topic prompt and returns structured source candidates for the user to review.

**Request:**
```python
class ResearchRequest(BaseModel):
    prompt: str                          # Topic description (30-500 chars)
    categoria: Optional[str] = None      # Hint for search refinement
    date_range_days: int = 7             # How far back to search (1-60)
    max_results: int = 10                # Max sources to return (5-15)
    language: str = "pt"                 # Preferred language
```

**Response:**
```python
class ResearchResponse(BaseModel):
    sources: list[ResearchSource]        # Ordered by relevance
    search_queries: list[str]            # Queries executed (for transparency)
    total_chars: int                     # Total chars across all sources
    search_duration_ms: int              # Performance metric

class ResearchSource(BaseModel):
    id: str                              # UUID for selection tracking
    title: str                           # Article title from Exa
    url: str                             # Source URL
    domain: str                          # Extracted domain (e.g. "reuters.com")
    published_date: Optional[str]        # ISO date if available
    snippet: str                         # First 300 chars for preview
    full_text: str                       # Full extracted text (up to 4000 chars)
    char_count: int                      # Length of full_text
    word_count: int                      # Approximate word count
    relevance_score: float               # 0-1 Exa relevance
    is_gov_source: bool                  # True if .gov.br domain
```

**Implementation logic:**

```python
@app.route(route="research", methods=["POST", "OPTIONS"])
@with_cors
@require_auth
async def research_topic_handler(req: func.HttpRequest) -> func.HttpResponse:
    # 1. Parse & validate ResearchRequest
    # 2. Build 3-5 search queries from prompt:
    #    - Query 1: prompt verbatim (neural search handles semantics)
    #    - Query 2: prompt + year (e.g., "conflito Irã EUA 2026")
    #    - Query 3: key entities extracted via simple NER/regex
    #    - Query 4: categoria-specific angle (if provided)
    #    - Query 5: prompt in English (for international sources)
    # 3. Execute parallel Exa searches (reuse _search_exa from fact_check_service)
    # 4. Deduplicate by URL + domain (reuse existing dedup logic)
    # 5. Filter quality (>50 chars, not index/tag pages)
    # 6. Sort by: recency × relevance_score
    # 7. Return top max_results
```

**Reused components from `fact_check_service.py`:**
- `_search_exa(query, num_results, max_text)` — Direct Exa API calls
- URL quality filtering (blocks /topicos/, /tag/, blogspot, etc.)
- Domain extraction logic
- Gov source whitelist (.gov.br domains)

**New logic needed:**
- Multi-query generation from topic prompt
- Result ranking by recency × relevance
- Response formatting with preview snippets

### 4.2 Modified Generation Flow

**No new generation endpoint.** The existing `POST /api/generate` is extended with a `source_type` field.

**GenerateRequest additions:**
```python
class GenerateRequest(BaseModel):
    # ... existing fields ...
    source_type: str = "manual"          # NEW: "manual" | "feed" | "prompt"
    research_source_urls: list = []      # NEW: URLs from research step
    research_prompt: Optional[str] = None # NEW: Original topic prompt
```

**Changes to `generate_article_handler()`:**

```python
# Phase 1.1: Source validation (MODIFIED)
source_char_count = len(request_data.texto_base.strip())

if request_data.source_type == "prompt":
    # For prompt-based: texto_base is assembled from Exa results
    # The user already reviewed and selected sources
    # Apply softer gates since material is pre-verified web content

    if source_char_count < MIN_SOURCE_CHARS:
        # Same hard reject — Exa should have provided enough
        return create_error_response(...)

    # Skip nota/servico downgrade for prompt-based:
    # Exa material is inherently richer than short RSS snippets
    # The user consciously selected enough sources
    # BUT still enforce if truly short (<500)
    if source_char_count < NOTA_ONLY_THRESHOLD:
        request_data.tipo_materia = "nota"
        nota_forced = True
    # No SHORT_SOURCE_THRESHOLD downgrade for prompt-based

    # Force enrichment ON (Exa research IS the enrichment)
    request_data.skip_enrichment = False

    # Use research_prompt as titulo_fonte for Phase 1 enrichment
    if not request_data.titulo_fonte and request_data.research_prompt:
        request_data.titulo_fonte = request_data.research_prompt

else:
    # Existing logic unchanged
    ...
```

**Expansion ratio adjustment (in `_evaluate_safety_gates`):**
```python
# For prompt-based: enrichment IS the source, so use verified_chars
# as effective source length (not raw texto_base which may be synthetic)
if source_type == "prompt" and enrichment and enrichment.verified_chars > 0:
    effective_source_len = max(enrichment.verified_chars, source_len)
```

**Audit trail:**
```python
# Log source_type in generation_audit_trail
audit_data["source_type"] = request_data.source_type
audit_data["research_prompt"] = request_data.research_prompt
audit_data["research_source_urls"] = request_data.research_source_urls
```

### 4.3 Safety Gate Adjustments for `source_type == "prompt"`

| Gate | Current | Prompt-Based | Rationale |
|------|---------|-------------|-----------|
| MIN_SOURCE_CHARS | 300 | 300 (keep) | Exa should provide enough material |
| NOTA_ONLY_THRESHOLD | 500 | 500 (keep) | If Exa returned thin results, force nota |
| SHORT_SOURCE_THRESHOLD | 800 | **Skip** | Exa sources are curated web content, not raw RSS |
| Confidence floor | 0.65 | 0.65 (keep) | Non-negotiable for any source type |
| Grounded claims floor | 0.70 | 0.70 (keep) | Non-negotiable |
| Expansion ratio | 8x | 8x (keep) | But use `verified_chars` as denominator |
| Fabrication hard block | ≥2 | ≥2 (keep) | Non-negotiable |
| Novel entity ratio (quality loop) | 0.75 | **0.85** | Research naturally introduces entities not in source |
| CoVe scope | Top 5 claims | **All fabricated** | Prompt-based needs thorough verification |

### 4.4 Rate Limiting

New endpoint rate limit:
```python
# research endpoint: 1 req/sec, burst 3
# (Exa calls are expensive, prevent abuse)
RATE_LIMITS["research"] = {"rate": 1.0, "burst": 3}
```

## 5. Frontend Architecture

### 5.1 New Source Card in SelecionarFontePage

**File:** `tmc-redacao/src/pages/criar/index.jsx`

Add new card between existing options:
```jsx
<SourceCard
  icon={<Search size={28} />}
  title="CRIAR POR PROMPT"
  description="Pesquise um tema na web e gere a matéria com fontes verificadas"
  selected={selectedSource === 'prompt'}
  onClick={() => handleSourceClick('prompt')}
  badge="Novo"  // Optional "New" badge
/>
```

**Context update:** `setFonte('prompt', {})`

### 5.2 New TextoBase Variant: TextoBasePrompt

**File:** `tmc-redacao/src/pages/criar/variantes/TextoBasePrompt.jsx`

**State:**
```jsx
const [prompt, setPrompt] = useState('')
const [dateRange, setDateRange] = useState(7)
const [isSearching, setIsSearching] = useState(false)
const [sources, setSources] = useState([])
const [selectedIds, setSelectedIds] = useState(new Set())
const [searchQueries, setSearchQueries] = useState([])
const [error, setError] = useState(null)
const [hasSearched, setHasSearched] = useState(false)
```

**Layout — Phase A (Prompt Input):**
```
┌─────────────────────────────────────────────────┐
│ 🔍 Descreva o tema que deseja pesquisar         │
│ ┌─────────────────────────────────────────────┐ │
│ │ Conflito entre Irã e Estados Unidos com     │ │
│ │ informações atualizadas da semana de        │ │
│ │ 11/03/2026...                               │ │
│ └─────────────────────────────────────────────┘ │
│ 142 caracteres                                  │
│                                                  │
│ Período: [Últimos 7 dias ▾]   (1-60 dias)      │
│                                                  │
│ [ 🔍 Pesquisar Fontes ]                         │
└─────────────────────────────────────────────────┘
```

**Layout — Phase B (Source Review):**
```
┌─────────────────────────────────────────────────┐
│ Fontes encontradas (8 resultados)               │
│ Pesquisa: "conflito irã eua 2026"               │
│                                                  │
│ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐ │
│ │ [✓] Irã anuncia retaliação após sanções     │ │
│ │     reuters.com · 11/03/2026 · 350 palavras│ │
│ │     "O governo iraniano anunciou nesta       │ │
│ │     terça-feira medidas de retaliação..."    │ │
│ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘ │
│ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐ │
│ │ [✓] EUA reforçam presença militar no Golfo  │ │
│ │     apnews.com · 11/03/2026 · 420 palavras │ │
│ │     "O Pentágono confirmou o envio..."      │ │
│ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘ │
│ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐ │
│ │ [ ] Análise: O que está por trás das tensõe │ │
│ │     bbc.com · 10/03/2026 · 580 palavras    │ │
│ │     "Os recentes movimentos diplomáticos..."│ │
│ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘ │
│                                                  │
│ Selecionadas: 2 fontes · ~770 palavras          │
│ ⚠️ Mínimo: 300 caracteres de material           │
│                                                  │
│ [🔄 Pesquisar novamente]                         │
│ [Continuar com 2 fontes →]                       │
└─────────────────────────────────────────────────┘
```

**On "Continuar" click:**
```js
// Assemble texto_base from selected sources
const assembledText = selectedSources
  .map(s => `[Fonte: ${s.domain} - ${s.published_date || 'sem data'}]\n${s.full_text}`)
  .join('\n\n---\n\n')

onDataChange({
  selectedTopics: ['pesquisa-prompt'],
  topicTexts: { 'pesquisa-prompt': assembledText },
  wordCount: totalWords,
  // Extra metadata for RevisarPage
  _promptMeta: {
    source_type: 'prompt',
    research_prompt: prompt,
    research_source_urls: selectedSources.map(s => s.url),
    source_count: selectedSources.length,
  }
})
```

### 5.3 TextoBasePage Router Update

**File:** `tmc-redacao/src/pages/criar/TextoBasePage.jsx`

Add new case in the variant router:
```jsx
// Existing
if (fonte.tipo === 'zero') return <TextoBaseZero ... />
if (fonte.tipo === 'feed') return <TextoBaseFeed ... />

// NEW
if (fonte.tipo === 'prompt') return <TextoBasePrompt ... />
```

### 5.4 CriarContext Additions

**File:** `tmc-redacao/src/context/CriarContext.jsx`

Add to `variantSelections`:
```js
variantSelections: {
  // ... existing fields ...
  promptMeta: null  // { source_type, research_prompt, research_source_urls }
}
```

Update `getTextoBaseParaGeracao()` to pass metadata through.

### 5.5 RevisarPage Changes

**File:** `tmc-redacao/src/pages/criar/RevisarPage.jsx`

Minor additions:
```jsx
// Show prompt source badge
{fonte.tipo === 'prompt' && (
  <div className="flex items-center gap-2 text-sm text-tmc-orange">
    <Search size={14} />
    <span>Fonte: Pesquisa por prompt ({promptMeta.source_count} fontes)</span>
  </div>
)}

// Pass source_type in API payload
const payload = {
  ...existingPayload,
  source_type: promptMeta?.source_type || 'manual',
  research_prompt: promptMeta?.research_prompt,
  research_source_urls: promptMeta?.research_source_urls || [],
}
```

### 5.6 API Service Addition

**File:** `tmc-redacao/src/services/api.js`

```js
export async function researchTopic({ prompt, dateRangeDays = 7, maxResults = 10, categoria = null }) {
  const response = await fetch(`${API_BASE_URL}/research`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      prompt,
      date_range_days: dateRangeDays,
      max_results: maxResults,
      categoria,
    }),
  })
  if (!response.ok) throw new Error(await response.text())
  return response.json()
}
```

## 6. Quality Assurance Strategy

### 6.1 Why This Produces Quality Articles

1. **Exa neural search** returns semantically relevant, full-text web content — not just snippets
2. **User curation step** ensures only relevant sources enter the pipeline (humans above the loop)
3. **Assembled texto_base** from multiple sources provides rich, multi-angle material
4. **Phase 1 enrichment** runs on TOP of the assembled sources (double research layer)
5. **Same verification pipeline** — claim extraction, CoVe, confidence scoring, safety gates
6. **Quality loop** — up to 3 regeneration attempts if fabrication or low confidence detected
7. **Expansion ratio guard** — prevents hallucinated padding even with enrichment

### 6.2 Quality Comparison: RSS vs Prompt

| Dimension | RSS Sources | Prompt Sources |
|-----------|-------------|----------------|
| Source reliability | Pre-curated feeds | Exa search (filtered by quality) |
| Source freshness | 15-min collection cycle | Real-time search |
| Topic coverage | Limited to subscribed feeds | Any topic on the web |
| Multi-perspective | Only if multiple feeds cover topic | Exa returns diverse sources |
| Hallucination risk | Low (rich source text) | Medium (depends on Exa quality) |
| Fact-check effectiveness | High (claims traceable to source) | High (same pipeline applies) |

### 6.3 Minimum Quality Bar

For an article to pass with `source_type == "prompt"`:
- Assembled texto_base ≥ 300 chars (from Exa selections)
- Confidence ≥ 0.65 after verification
- Grounded claims ≥ 70%
- Expansion ratio ≤ 8x (using verified_chars as denominator)
- 0 or 1 fabricated claims (≥2 = hard block)
- Quality loop passes OR article goes to human review

## 7. Implementation Plan

### Phase 1: Backend — Research Endpoint (1 task)
1. Create `functions/research_api.py` with `POST /api/research`
2. Build multi-query generation from topic prompt
3. Reuse `_search_exa()` from fact_check_service
4. Add rate limiting for research endpoint
5. Register route in `function_app.py`

### Phase 2: Backend — Generation Modifications (1 task)
1. Add `source_type`, `research_source_urls`, `research_prompt` to GenerateRequest
2. Adjust Phase 1.1 source validation for `source_type == "prompt"`
3. Adjust expansion ratio logic for prompt-based sources
4. Adjust novel entity threshold in quality loop for prompt-based
5. Expand CoVe scope to all fabricated claims when prompt-based
6. Add source_type to audit trail

### Phase 3: Frontend — Prompt Variant (1 task)
1. Create `TextoBasePrompt.jsx` with prompt input + source review UI
2. Add `researchTopic()` to api.js
3. Add source card in SelecionarFontePage
4. Add `'prompt'` case in TextoBasePage router
5. Pass promptMeta through CriarContext

### Phase 4: Frontend — Integration (1 task)
1. Update RevisarPage to show prompt source badge
2. Pass source_type + metadata in generate payload
3. Update ConfigurarPage to skip SHORT_SOURCE downgrade hint for prompt
4. Test full flow end-to-end

### Phase 5: Testing (1 task)
1. Test research endpoint with various prompts (broad, narrow, Portuguese, English)
2. Test generation with prompt-sourced texto_base
3. Verify safety gates work correctly
4. Test edge cases: Exa down, thin results, no results
5. Test quality loop with prompt-based articles

## 8. Files to Create/Modify

### New Files
| File | Purpose |
|------|---------|
| `FeedRSS/tmc-rss-collector/functions/research_api.py` | Research endpoint handler |
| `tmc-redacao/src/pages/criar/variantes/TextoBasePrompt.jsx` | Prompt input + source review UI |

### Modified Files
| File | Change |
|------|--------|
| `FeedRSS/tmc-rss-collector/function_app.py` | Register `/api/research` route |
| `FeedRSS/tmc-rss-collector/functions/generation_api.py` | Add source_type field, adjust gates |
| `FeedRSS/tmc-rss-collector/services/rate_limiter.py` | Add research endpoint rate limit |
| `tmc-redacao/src/pages/criar/index.jsx` | Add "Criar por Prompt" source card |
| `tmc-redacao/src/pages/criar/TextoBasePage.jsx` | Add 'prompt' variant routing |
| `tmc-redacao/src/pages/criar/RevisarPage.jsx` | Show prompt badge, pass source_type |
| `tmc-redacao/src/context/CriarContext.jsx` | Add promptMeta to variantSelections |
| `tmc-redacao/src/services/api.js` | Add researchTopic() function |

## 9. Edge Cases

| Scenario | Handling |
|----------|----------|
| Exa returns 0 results | Show "Nenhuma fonte encontrada. Tente outro tema ou amplie o período." |
| Exa returns only thin results (<50 chars each) | Filter out, show remaining. If all filtered, show empty state. |
| Exa is down (circuit breaker open) | Show error: "Serviço de pesquisa indisponível. Tente novamente em 1 minuto." |
| User selects 1 source with <300 chars | Show warning. Block "Continuar" if total chars < 300. |
| Prompt is too vague ("notícias") | Exa handles it (neural search), but results may be unfocused. Let user refine. |
| User navigates back and re-searches | Preserve previous selections in CriarContext, clear on new search. |
| Generated article blocked by safety gates | Same as current: show block reason, suggest editing texto_base or trying different sources. |
| Duplicate sources from Exa | Deduplicate by URL before showing to user. |

## 10. Cost Analysis

### Per Research Request
| Operation | Cost |
|-----------|------|
| Exa search (3-5 queries × 10 results) | ~$0.03-0.05 (Exa pricing) |
| Total per research | ~$0.03-0.05 |

### Per Article Generation (prompt-based)
| Operation | Model | Est. Cost |
|-----------|-------|-----------|
| Phase 1: Enrichment (additional Exa) | Exa + claude-sonnet-4-5 | ~$0.08 |
| Phase 2: Generation | claude-sonnet-4-5 | ~$0.05 |
| Phase 3: Verification + CoVe | claude-sonnet-4-5 | ~$0.10 |
| Quality loop (if needed, 1-2 regens) | claude-sonnet-4-5 | ~$0.10 |
| **Total per prompt-based article** | | **~$0.33-0.38** |
| **Total per RSS-based article** (baseline) | | **~$0.25-0.30** |

**Delta:** ~$0.08-0.13 more per article (research step + slightly more verification). Acceptable for the value provided.

## 11. Success Criteria

1. User can generate an article from a topic prompt in ≤3 minutes (including source review)
2. Generated articles pass safety gates at ≥80% rate (comparable to RSS-based)
3. Confidence scores average ≥0.70 for prompt-based articles
4. Users can research topics not covered by their RSS feeds
5. Full audit trail captures source_type, research queries, and selected URLs
