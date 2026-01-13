# TMC Redacao - MVP Plan for February 15th, 2026

## Executive Summary

**Goal:** Deliver a functional MVP of the journalistic writing tool by Feb 15th (33 days from today, Jan 13)

**Core Value Proposition:** AI-powered article generation from RSS feeds and pasted text, with SEO analysis and a simple editor.

---

## Implementation Progress Tracker

**Last Updated:** 2026-01-13

### Completed Tasks
| Task | File(s) | Date | Notes |
|------|---------|------|-------|
| Tag mockup version | Git tag `v0.0.0-mockup` | 2026-01-13 | Preserves full mockup state |
| Create feature flags | `src/config/featureFlags.js` | 2026-01-13 | Controls MVP/post-MVP visibility |
| Hide non-MVP features | `pages/criar/index.jsx`, `TrendsSidebar.jsx` | 2026-01-13 | Video, Google Trends, Twitter hidden |
| Create API service layer | `src/services/api.js` | 2026-01-13 | Frontend API wrapper with error handling |
| Create LLM service | `services/llm_service.py` | 2026-01-13 | Claude Sonnet 4.5 with personas/tones |
| Create generation API | `functions/generation_api.py` | 2026-01-13 | /generate, /extract-topics, /generate-tags |

### In Progress
| Task | File(s) | Started | Notes |
|------|---------|---------|-------|
| Connect TextoBaseFeed to RSS API | `TextoBaseFeed.jsx` | 2026-01-13 | Replace mock data with real API |

### Pending
| Task | Priority | Estimated Hours |
|------|----------|-----------------|
| Connect RevisarPage to generation API | CRITICAL | 3h |
| Add Copy to Clipboard button | HIGH | 1h |
| Deploy Azure Functions | HIGH | 2h |

---

## Current State Analysis

### What's Already Done (90%+ Complete)

| Feature | Status | Notes |
|---------|--------|-------|
| **Frontend UI/UX** | 95% | Polished, responsive, accessible |
| **4-Step Creation Flow** | 100% | Fonte -> Texto-Base -> Config -> Revisar |
| **SEO Analyzer** | 100% | Real-time scoring, Portuguese readability |
| **Tags Management** | 100% | Add/remove/AI generate (mock) |
| **Editor (Basic)** | 80% | Textarea works, formatting buttons decorative |
| **Minhas Materias** | 90% | Grid, filters, pagination, delete |
| **RSS Backend** | 95% | Azure Functions ready (Not Deployed), 27 sources configured |

### What Needs Work

| Feature | Status | Effort | Priority |
|---------|--------|--------|----------|
| **AI Generation Backend** | 0% | HIGH | CRITICAL |
| **RSS Frontend Integration and Theme and Tags Extraction** | 0% | MEDIUM | CRITICAL |
| **Article Persistence** | 0% | MEDIUM | HIGH |
| **Copy/Export Content** | 0% | LOW | HIGH |

---

## RSS Frontend Features - Deep Analysis

### UI Elements Mapping

| Concept | Data Field | UI Component | Status |
|---------|------------|--------------|--------|
| **Theme** | `article.category` | ArticleCard.jsx:74-79 (colored badge) | DISPLAYED BUT WITH MOCK DATA |
| **Tags/Hashtags** | `article.tags` | ArticleCard.jsx:137-147 (`#{tag}` chips) | DISPLAYED BUT WITH MOCK DATA |
| **Category filter** | `category` | FeedSelector.jsx:110-127 (dropdown) | WORKING BUT WITH MOCK DATA |

**Categories/Themes available IN MOCK DATA:** Política, Tecnologia, Ciência, Esportes, Economia, Entretenimento, Saúde, Educação WILL CHANGE BECAUSE IT IS USING MOCK DATA

### Currently WORKING (Ready for MVP)

| Feature | Status | Location | Notes |
|---------|--------|----------|-------|
| **Multi-article selection** | ✅ 100% | TextoBaseFeed.jsx | Users can select multiple RSS articles (MOCK DATA) |
| **Topic extraction** | ✅ 80% | TextoBaseFeed.jsx:24-40 | Basic sentence-based (3 types: fato, contexto, detalhe) (MOCK DATA) |
| **Topic selection** | ✅ 100% | TextoBaseFeed.jsx:128-159 | Select/deselect individual topics per article  (MOCK DATA)|
| **Topic editing** | ✅ 100% | TextoBaseFeed.jsx:140-145 | Inline editing with save/cancel (MOCK DATA) |
| **Theme/Category display** | ✅ 100% | ArticleCard.jsx:74-79 | Color-coded badge (blue=Política, purple=Tech, etc.) (MOCK DATA) |
| **Tags as hashtags** | ✅ 100% | ArticleCard.jsx:137-147 | Displayed as `#{tag}` chips  (MOCK DATA)|
| **FeedSelector modal** | ✅ 100% | FeedSelector.jsx | Filter by category, source, search (MOCK DATA) |
| **TopicCard component** | ✅ 100% | TopicCard.jsx | 8 topic types with color coding  (MOCK DATA) |

### MISSING: Tag Selection Functionality

**Issue:** Tags ARE displayed on ArticleCard (as hashtags), but:
1. **Not shown in FeedSelector** (simplified view)
2. **No selection checkboxes** for tags
3. **Tags not passed to generation**

**What to add (LOW effort, HIGH value):**

1. **Add tag selection checkboxes** to ArticleCard and FeedSelector
2. **Track selectedTags in CriarContext**
3. **Pass selected tags to AI generation** for SEO and content targeting
4. **Show aggregated tags in RevisarPage**

### Data Structures (mockData.js)

**Article Structure:**
```javascript
{
  id: 1,
  title: "Governo anuncia novo pacote...",
  source: "G1",
  category: "Política",                     // ← THEME (displayed as badge)
  tags: ["economia", "governo", "medidas"], // ← HASHTAGS (displayed but not selectable)
  publishedAt: Date,
  preview: "...",
  content: "..."
}
```

**Category Colors (ArticleCard.jsx:14-23):** WILL CHANGE BECAUSE IT IS USING MOCK DATA
```javascript
categoryColors = {
  'Política': 'bg-blue-500',
  'Economia': 'bg-emerald-500',
  'Esportes': 'bg-orange-500',
  'Tecnologia': 'bg-purple-500',
  'Entretenimento': 'bg-pink-500',
  'Saúde': 'bg-red-500',
  'Ciência': 'bg-cyan-500',
  'Educação': 'bg-yellow-500'
}
```

---

## MVP Feature Scope (Revised with RSS Analysis)

### TIER 1: MUST HAVE (Core MVP - Week 1-2)

#### 1. AI Article Generation Backend
- **What:** Create API endpoint to generate articles using Claude Sonnet 4.5
- **Input:** Selected topics + tags + configuration (persona, tone, lead, quotes)
- **Output:** Generated title + linha fina + article content (min 2000 chars)
- **Tech:** Azure Functions + Anthropic Claude
- **Files to create:**
  - `FeedRSS/tmc-rss-collector/functions/generation_api.py`
  - `FeedRSS/tmc-rss-collector/services/llm_service.py`

#### 2. RSS Feed Integration (Frontend ↔ Backend)
- **What:** Connect frontend to existing RSS backend API
- **Status:** Backend DONE, frontend needs wiring
- **Files to modify:**
  - `tmc-redacao/src/pages/crear/variantes/TextoBaseFeed.jsx`
  - Create `tmc-redacao/src/services/api.js` for API wrapper
- **Also includes:** Deploy Azure Functions to production

#### 3. AI from Pasted Text
- **What:** Same generation backend, different input source
- **Status:** Frontend UI complete, just needs API connection
- **Work:** Connect to same generation API as #1

### TIER 2: QUICK WINS (High Value, Low Effort - Week 2)

#### 4. Tag/Hashtag Display & Selection ⭐ NEW
- **What:** Show article tags in UI, let users select which to keep
- **Status:** Data exists in mockData, UI missing
- **Effort:** LOW (3-4 hours)
- **Value:** HIGH - Better article targeting, SEO improvement
- **Files to modify:**
  - `TextoBaseFeed.jsx` - Add tag chips display on side of the tema dropdown
  - `CriarContext.jsx` - Add selectedTags state
  - `RevisarPage.jsx` - Show aggregated tags

#### 5. Copy to Clipboard
- **What:** One-click copy of generated article
- **Status:** Missing
- **Effort:** LOW (1-2 hours)
- **Files:** `CriarPostPage.jsx`

#### 6. Full-Text Editing Mode Fix
- **What:** Enable the textarea in full-text mode (currently `onChange={() => {}}`)
- **Effort:** LOW (1 hour)
- **File:** `TextoBaseFeed.jsx:391-396`

### TIER 3: NICE TO HAVE (If Time Permits - Week 3)

#### 7. Tags Recognition Display (Feed em Alta)
- **What:** Show trending tags from RSS 
- **Status:** Data exists (mock data), UI missing
- **Effort:** MEDIUM (4-6 hours)
- **Value:** Helps users pick trending topics

#### 8. Article Persistence (LocalStorage)
- **What:** Auto-save drafts to browser
- **Effort:** MEDIUM (3-4 hours)
- **File:** `CriarContext.jsx`

#### 9. Export Options (Markdown/HTML)
- **What:** Download article in different formats
- **Effort:** MEDIUM (3-4 hours)

### CUT FROM MVP (Post-Launch)

| Feature | Reason |
|---------|--------|
| Video transcription | Complex, needs Speech-to-Text service |
| Google Trends integration | Backend not ready |
| User authentication | Out of scope for MVP |
| Rich text editor (TipTap/Slate) | Textarea sufficient for MVP |
| AI-powered topic extraction | Can use basic sentence extraction for now |
| Article merging UI | Complex UX, defer to v2 |
| Database persistence | Use localStorage for MVP |
| PDF export | Markdown/copy sufficient |

---

## Technical Implementation Plan (Detailed)

### Phase 1: Backend Foundation (Week 1)

**Step 1.1: Create API Service Layer (Frontend)**
- File: `tmc-redacao/src/services/api.js`
- Centralized API calls with error handling
- Base URL configuration via `VITE_API_BASE_URL`

**Step 1.2: Deploy RSS Backend to Azure**
```bash
cd FeedRSS/tmc-rss-collector
func azure functionapp publish <APP_NAME>
```
- Configure CORS for frontend domain
- Verify endpoints: `/api/health`, `/api/articles`, `/api/sources`

**Step 1.3: Create LLM Service**
- File: `FeedRSS/tmc-rss-collector/services/llm_service.py`
- Integration with Claude Sonnet 4.5
- Prompt templates for each persona/tone combination

**Step 1.4: Create Generation API Endpoint**
- File: `FeedRSS/tmc-rss-collector/functions/generation_api.py`
- `POST /api/generate`
- Input: `{ texto_base, tags, persona, tom, orientacao_lide, citacoes, contexto, creditos, tipo_materia }`
- Output: `{ titulo, linha_fina, conteudo, tags_sugeridas }`

### Phase 2: Frontend Integration (Week 1-2)

**Step 2.1: Connect RSS Feed to Backend**
- File: `tmc-redacao/src/pages/crear/variantes/TextoBaseFeed.jsx`
- Replace `mockArticles` with `api.getArticles()`
- Add loading/error states

**Step 2.2: Add Tag Display & Selection ⭐**
- File: `TextoBaseFeed.jsx`
- Display tags as chips below each article in sidebar
- Add checkboxes to select/deselect tags
- Aggregate selected tags across all articles

**Step 2.3: Update Context for Tags**
- File: `tmc-redacao/src/context/CriarContext.jsx`
- Add `selectedTags: Set()` to state
- Add `setSelectedTags()` action
- Include tags in `getDataForGeneration()`

**Step 2.4: Connect Generation to API**
- File: `tmc-redacao/src/pages/criar/RevisarPage.jsx`
- Replace mock `setTimeout` with real `api.generate()` call
- Pass selected topics + tags + configuration
- Handle response and navigate to editor

**Step 2.5: Fix Full-Text Editing**
- File: `TextoBaseFeed.jsx:391-396`
- Implement `onChange` handler for textarea

### Phase 3: Editor & Export (Week 2)

**Step 3.1: Add Copy to Clipboard**
- File: `tmc-redacao/src/pages/CriarPostPage.jsx`
- Add "Copy Article" button in toolbar
- Copy title + linha fina + content
- Show toast confirmation

**Step 3.2: Show Tags in Review**
- File: `tmc-redacao/src/pages/criar/RevisarPage.jsx`
- Display aggregated selected tags
- Allow last-minute tag editing

### Phase 4: Polish & Testing (Week 3-4)

**Step 4.1: Error Handling**
- API timeout handling
- Network error recovery
- Validation feedback

**Step 4.2: LocalStorage Persistence (Optional)**
- Auto-save draft to localStorage
- Recover on page reload

**Step 4.3: End-to-End Testing**
- Test full RSS → Generate → Edit → Copy flow
- Test Pasted Text → Generate → Edit → Copy flow

---

## AI Model Selection: Claude Sonnet 4.5

### Selected Model: **Claude Sonnet 4.5** (Anthropic)

Based on user preference for best possible quality:

| Aspect | Claude Sonnet 4.5 |
|--------|-------------------|
| **Portuguese Quality** | Excellent |
| **Instruction Following** | Superior |
| **Long-form Coherence** | Excellent (2000+ chars) |
| **Context Window** | 200K tokens |
| **Cost per article** | ~$0.025 |
| **Speed** | ~18-65s per generation |

### Why Claude Sonnet 4.5:

1. **Superior instruction following** - Critical for tone/persona adherence
2. **Excellent long-form coherence** - Maintains quality for TMC's 2000+ char requirement
3. **200K context window** - Rich context from multiple RSS articles
4. **Strong reasoning** - Better for analytical journalism
5. **Best Portuguese writing quality** among all models tested

### Environment Variables:
```
# Anthropic Claude (Selected)
ANTHROPIC_API_KEY=sk-ant-...

# Model to use
ANTHROPIC_MODEL=claude-sonnet-4-5-20241022
```

---

## Confirmed Requirements

| Requirement | Decision |
|-------------|----------|
| **AI Model** | Claude Sonnet 4.5 (Anthropic) |
| **Deployment** | RSS backend tested locally, needs Azure deployment |
| **Input Sources** | Both RSS and Pasted Text equally important |
| **Article Length** | Minimum 2000 characters (TMC standard for columnists) |
| **Personas** | Currently mock data - will be designed |
| **Tones** | Currently mock data - will be designed |

---

## Pending Design Decisions (To Be Planned Later)

### 1. System Prompt Design
- The personas and tones are currently mock data
- System prompt structure needs to be designed with real TMC requirements
- Will be planned in a separate session

### 2. RSS Tag & Theme Extraction Strategy
**Current state:** Tags and themes are manually defined in mock data

**Future state (to be planned):**
- RSS articles will have tags/themes stored in SQL database
- Need to decide extraction method:
  - **Option A:** AI-powered extraction (LLM analyzes each article)
  - **Option B:** Manual categorization
  - **Option C:** NLP keyword extraction
  - **Option D:** Source-provided tags (from RSS feed metadata)

**Questions to answer later:**
- What themes will we use? (Categories like Política, Economia, etc.)
- What tags will we use? (Keywords like "governo", "dólar", "inflação", etc.)
- Who decides the taxonomy? (Predefined list vs. dynamic)
- When is extraction done? (At RSS collection time or on-demand)

### 3. Integration Plan
- Tags and themes will be added to the SQL database during RSS integration
- `collected_articles` table may need new columns or a separate `article_tags` table

---

## Development Hours Estimate (Claude Code)

### TIER 1: MUST HAVE (Core MVP)

| Task | Description | Hours |
|------|-------------|-------|
| **1.1** | Create `api.js` service layer (frontend) | 2h |
| **1.2** | Create `llm_service.py` with Claude Sonnet 4.5 integration | 4h |
| **1.3** | Create `generation_api.py` endpoint | 3h |
| **1.4** | Prompt engineering (persona/tone templates) | 3h |
| **1.5** | Deploy Azure Functions to production | 2h |
| **1.6** | Connect TextoBaseFeed to RSS API | 3h |
| **1.7** | Connect RevisarPage to generation API | 3h |
| **1.8** | Error handling & loading states | 2h |
| | **Subtotal TIER 1** | **22h** |

### TIER 2: QUICK WINS

| Task | Description | Hours |
|------|-------------|-------|
| **2.1** | Add tag selection checkboxes to ArticleCard/FeedSelector | 3h |
| **2.2** | Update CriarContext with selectedTags state | 1h |
| **2.3** | Show aggregated tags in RevisarPage | 1h |
| **2.4** | Add Copy to Clipboard button | 1h |
| **2.5** | Fix full-text editing mode (onChange handler) | 1h |
| | **Subtotal TIER 2** | **7h** |

### TIER 3: NICE TO HAVE

| Task | Description | Hours |
|------|-------------|-------|
| **3.1** | Theme recognition display (mockFeedThemes) | 4h |
| **3.2** | LocalStorage persistence for drafts | 3h |
| **3.3** | Export options (Markdown/HTML download) | 3h |
| | **Subtotal TIER 3** | **10h** |

### TESTING & POLISH

| Task | Description | Hours |
|------|-------------|-------|
| **4.1** | End-to-end testing (RSS flow) | 2h |
| **4.2** | End-to-end testing (Pasted text flow) | 1h |
| **4.3** | Bug fixes and refinements | 4h |
| | **Subtotal Testing** | **7h** |

---

## Total Development Hours Summary

| Tier | Features | Hours |
|------|----------|-------|
| **TIER 1** | Core MVP (AI Generation + RSS Integration) | 22h |
| **TIER 2** | Quick Wins (Tag Selection + Copy) | 7h |
| **TIER 3** | Nice to Have (Themes + LocalStorage + Export) | 10h |
| **Testing** | E2E Testing + Bug Fixes | 7h |
| | | |
| **TOTAL MVP (TIER 1+2+Testing)** | Minimum viable product | **36h** |
| **TOTAL COMPLETE (All Tiers)** | Full feature set | **46h** |

### Timeline Mapping

- **36 hours** = ~4-5 days of focused development (8h/day)
- **46 hours** = ~6 days of focused development

With a Feb 15 deadline (33 days from Jan 13):
- **Conservative estimate:** 2 weeks for full implementation + testing
- **Buffer:** 2+ weeks for iterations and unforeseen issues

---

## Key Files Summary

**Backend (to create):**
- `FeedRSS/tmc-rss-collector/services/llm_service.py`
- `FeedRSS/tmc-rss-collector/functions/generation_api.py`

**Frontend (to create):**
- `tmc-redacao/src/services/api.js`

**Frontend (to modify):**
- `tmc-redacao/src/pages/crear/variantes/TextoBaseFeed.jsx`
- `tmc-redacao/src/pages/criar/RevisarPage.jsx`
- `tmc-redacao/src/pages/CriarPostPage.jsx`
- `tmc-redacao/src/context/CriarContext.jsx`
- `tmc-redacao/src/components/cards/ArticleCard.jsx`
- `tmc-redacao/src/components/criar/FeedSelector.jsx`

---

## MVP Success Criteria

A successful MVP will allow users to:

1. Browse real RSS feed articles from 27 Brazilian news sources
2. Select an article (or paste their own text) as the base for generation
3. Configure the article style (persona, tone, lead orientation)
4. Generate a complete journalistic article using AI
5. Edit the generated content in a simple editor
6. See real-time SEO analysis and scoring
7. Copy the final content to clipboard for publishing elsewhere

This delivers the core value proposition: **AI-powered journalistic writing with SEO optimization**.
