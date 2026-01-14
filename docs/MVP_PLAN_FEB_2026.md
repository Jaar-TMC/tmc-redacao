# TMC Redacao - MVP Plan for February 15th, 2026

## Executive Summary

**Goal:** Deliver a functional MVP of the journalistic writing tool by Feb 15th (33 days from today, Jan 13)

**Core Value Proposition:** AI-powered article generation from RSS feeds and pasted text, with SEO analysis and a simple editor.

**Deployment Target:** WordPress Admin Plugin (changed from Azure Static Web Apps)

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
| Connect FeedSelector to API | `FeedSelector.jsx` | 2026-01-13 | Loading/error states, real data fetch |
| Connect TextoBaseFeed to RSS API | `TextoBaseFeed.jsx` | 2026-01-13 | "Add more articles" with API loading/error states |
| Connect RevisarPage to generation API | `RevisarPage.jsx`, `CriarPostPage.jsx` | 2026-01-13 | Full generation flow: API call + context + editor display |
| Add Copy to Clipboard button | `CriarPostPage.jsx` | 2026-01-13 | Copy title + linha fina + content + tags to clipboard |

### In Progress
| Task | File(s) | Started | Notes |
|------|---------|---------|-------|
| Test in WordPress environment | N/A | 2026-01-13 | Install plugin in WP and test all flows |

### Pending - Core MVP
| Task | Priority | Estimated Hours |
|------|----------|-----------------|
| Deploy Azure Functions | HIGH | 2h | Requires Azure MFA login |

### WordPress Plugin Migration - Completed
| Task | File(s) | Date | Notes |
|------|---------|------|-------|
| Create WP plugin structure | `tmc-redacao-wp/` | 2026-01-13 | Main plugin, admin, assets classes |
| Create uninstall.php | `tmc-redacao-wp/uninstall.php` | 2026-01-13 | Cleanup on plugin delete |
| Add capability checks | `class-tmc-redacao-admin.php` | 2026-01-13 | current_user_can('edit_posts') |
| Add settings page | `views/settings-page.php` | 2026-01-13 | API URL configuration |
| Modify Vite config | `vite.config.js` | 2026-01-13 | WordPress build with single bundle |
| Add CSS scoping | `index.css` | 2026-01-13 | .tmc-app isolation, WP admin bar offset |
| Change to HashRouter | `App.jsx` | 2026-01-13 | HashRouter for WP, BrowserRouter for dev |
| Create WordPressContext | `WordPressContext.jsx` | 2026-01-13 | WP user data provider |
| Update api.js | `api.js` | 2026-01-13 | Dynamic base URL from WP config |
| Update Header.jsx | `Header.jsx` | 2026-01-13 | WP user name/avatar display |

### Azure Functions Deployment Instructions

**Prerequisites Met:**
- ✅ Azure Functions Core Tools v4.0.7317 installed
- ✅ Azure subscription "Microsoft Azure Sponsorship" connected
- ⚠️ Azure CLI needs MFA re-authentication

**Required Environment Variables (add to Azure App Settings):**
```
ANTHROPIC_API_KEY=<your-anthropic-api-key>
ANTHROPIC_MODEL=claude-sonnet-4-5-20241022
SQL_SERVER=bi4ia-tmc.database.windows.net
SQL_DATABASE=tmc
SQL_USERNAME=admjaar
SQL_PASSWORD=<configured>
```

**To Deploy:**
```bash
# 1. Re-authenticate with Azure (requires MFA)
az login --scope https://management.core.windows.net//.default

# 2. Create Function App (if not exists) or use existing
# az functionapp create --resource-group <rg-name> --name tmc-redacao-api --storage-account <storage> --runtime python --runtime-version 3.11 --functions-version 4

# 3. Add ANTHROPIC_API_KEY to App Settings
az functionapp config appsettings set --name <function-app-name> --resource-group <rg-name> --settings "ANTHROPIC_API_KEY=<your-key>"

# 4. Deploy
cd FeedRSS/tmc-rss-collector
func azure functionapp publish <function-app-name>
```

### Pending - WordPress Plugin Migration
| Task | Priority | Estimated Hours |
|------|----------|-----------------|
| Test in WordPress environment | HIGH | 8h |

**Note:** All other WordPress migration tasks completed on 2026-01-13. See "WordPress Plugin Migration - Completed" section above.

### How to Continue Development

If session is cleared, use this prompt:
```
Continue developing the TMC Redação MVP.
Read the plan file at: docs/MVP_PLAN_FEB_2026.md
Follow the Implementation Progress Tracker at the top.
Key files: api.js, featureFlags.js, llm_service.py, generation_api.py
WordPress plugin: tmc-redacao-wp/
Tag v0.0.0-mockup preserves the mockup.
Continue from where we left off.
```

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
| **WordPress Plugin Migration** | 0% | HIGH | CRITICAL |
| **Article Persistence** | 0% | MEDIUM | HIGH |
| **Copy/Export Content** | 0% | LOW | HIGH |

---

## WordPress Plugin Architecture

### Deployment Change
**Before:** React SPA → Azure Static Web Apps
**After:** React SPA → WordPress Admin Plugin → Azure Functions API (unchanged)

### Key Decisions
- **Location:** WordPress Admin Area only
- **Auth:** WordPress user authentication
- **Backend:** Keep Azure Functions (no PHP rewrite)
- **Strategy:** Minimal React changes, bundle for WordPress

### Plugin Structure
```
tmc-redacao-wp/
├── tmc-redacao.php                     # Main plugin file
├── uninstall.php                       # CRITICAL: Cleanup on uninstall
├── includes/
│   ├── class-tmc-redacao-admin.php     # Admin menu + settings page
│   └── class-tmc-redacao-assets.php    # Script/style enqueuing
├── assets/
│   ├── js/tmc-redacao.js               # Bundled React app
│   ├── css/tmc-redacao.css             # Scoped Tailwind CSS
│   └── images/logo-tmc.svg
├── views/
│   ├── admin-page.php                  # React container
│   └── settings-page.php               # API configuration
└── languages/
    └── tmc-redacao.pot                 # Translation template
```

### React App Changes Required
| File | Change |
|------|--------|
| `vite.config.js` | Add WordPress build mode |
| `package.json` | Add `build:wp` script |
| `src/main.jsx` | Support WP root element |
| `src/App.jsx` | BrowserRouter → HashRouter |
| `src/index.css` | CSS scoping under `.tmc-app` |
| `src/services/api.js` | Dynamic API base URL |
| `src/components/layout/Header.jsx` | Use WP user data |

### New Files to Create (React)
| File | Purpose |
|------|---------|
| `src/context/WordPressContext.jsx` | WP user context provider |

### WordPress Security Requirements

**Capability Checks (in PHP):**
```php
// Every admin page render must check:
if ( ! current_user_can( 'edit_posts' ) ) {
    wp_die( 'Access denied' );
}
```

**Nonce Verification:**
- Pass nonce via `wp_localize_script()`
- Verify with `wp_verify_nonce()` for any AJAX calls

**CSS Scoping (CRITICAL):**
```css
/* Use aggressive isolation to prevent WP admin conflicts */
.tmc-app {
    all: initial;  /* Reset ALL inherited styles */
}
/* Adjust for WP admin bar (32px desktop, 46px mobile) */
.tmc-app header { top: 32px; }
```

### WordPress Data Flow
```
WordPress Admin Page Loads
         ↓
current_user_can('edit_posts') check
         ↓
wp_enqueue_script('tmc-redacao-app')
         ↓
wp_localize_script('tmcRedacaoConfig', {
    user: { id, displayName, email, roles },
    apiBaseUrl: get_option('tmc_redacao_api_url'),
    nonce: wp_create_nonce('tmc_redacao_nonce'),
    restNonce: wp_create_nonce('wp_rest')
})
         ↓
React app reads window.tmcRedacaoConfig
         ↓
WordPressContext provides user data to components
         ↓
API calls go directly to Azure Functions
```

### Build Commands
```bash
# Development (standalone React)
npm run dev

# Build for WordPress
npm run build:wp

# Build for WordPress with watch
npm run build:wp:watch
```

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

#### 4. WordPress Plugin Migration ⭐ NEW
- **What:** Convert React SPA to WordPress admin plugin
- **Status:** Not started
- **Effort:** HIGH (32 hours)
- **Files to create:** See "WordPress Plugin Architecture" section

### TIER 2: QUICK WINS (High Value, Low Effort - Week 2)

#### 5. Tag/Hashtag Display & Selection
- **What:** Show article tags in UI, let users select which to keep
- **Status:** Data exists in mockData, UI missing
- **Effort:** LOW (3-4 hours)
- **Value:** HIGH - Better article targeting, SEO improvement
- **Files to modify:**
  - `TextoBaseFeed.jsx` - Add tag chips display on side of the tema dropdown
  - `CriarContext.jsx` - Add selectedTags state
  - `RevisarPage.jsx` - Show aggregated tags

#### 6. Copy to Clipboard
- **What:** One-click copy of generated article
- **Status:** Missing
- **Effort:** LOW (1-2 hours)
- **Files:** `CriarPostPage.jsx`

#### 7. Full-Text Editing Mode Fix
- **What:** Enable the textarea in full-text mode (currently `onChange={() => {}}`)
- **Effort:** LOW (1 hour)
- **File:** `TextoBaseFeed.jsx:391-396`

### TIER 3: NICE TO HAVE (If Time Permits - Week 3)

#### 8. Tags Recognition Display (Feed em Alta)
- **What:** Show trending tags from RSS
- **Status:** Data exists (mock data), UI missing
- **Effort:** MEDIUM (4-6 hours)
- **Value:** Helps users pick trending topics

#### 9. Article Persistence (LocalStorage)
- **What:** Auto-save drafts to browser
- **Effort:** MEDIUM (3-4 hours)
- **File:** `CriarContext.jsx`

#### 10. Export Options (Markdown/HTML)
- **What:** Download article in different formats
- **Effort:** MEDIUM (3-4 hours)

### CUT FROM MVP (Post-Launch)

| Feature | Reason |
|---------|--------|
| Video transcription | Complex, needs Speech-to-Text service |
| Google Trends integration | Backend not ready |
| User authentication | Handled by WordPress now |
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
- Configure CORS for WordPress domain
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

### Phase 2: WordPress Plugin (Week 1-2)

**Step 2.1: Create Plugin Structure**
- Create `tmc-redacao-wp/` folder with PHP files
- Main plugin file with activation hooks
- Admin menu registration
- Script/style enqueuing

**Step 2.2: Modify Vite Build**
- Update `vite.config.js` for WordPress output
- Add `build:wp` script to package.json
- Configure single bundle output

**Step 2.3: CSS Scoping**
- Wrap all styles under `.tmc-app` class
- Add WordPress admin reset styles

**Step 2.4: React Router Change**
- Change BrowserRouter to HashRouter in App.jsx
- Test all navigation paths

**Step 2.5: WordPress Integration**
- Create WordPressContext.jsx
- Update Header.jsx with WP user data
- Update api.js for dynamic base URL

### Phase 3: Frontend Integration (Week 2)

**Step 3.1: Connect RSS Feed to Backend**
- File: `tmc-redacao/src/pages/crear/variantes/TextoBaseFeed.jsx`
- Replace `mockArticles` with `api.getArticles()`
- Add loading/error states

**Step 3.2: Add Tag Display & Selection**
- File: `TextoBaseFeed.jsx`
- Display tags as chips below each article in sidebar
- Add checkboxes to select/deselect tags
- Aggregate selected tags across all articles

**Step 3.3: Update Context for Tags**
- File: `tmc-redacao/src/context/CriarContext.jsx`
- Add `selectedTags: Set()` to state
- Add `setSelectedTags()` action
- Include tags in `getDataForGeneration()`

**Step 3.4: Connect Generation to API**
- File: `tmc-redacao/src/pages/criar/RevisarPage.jsx`
- Replace mock `setTimeout` with real `api.generate()` call
- Pass selected topics + tags + configuration
- Handle response and navigate to editor

**Step 3.5: Fix Full-Text Editing**
- File: `TextoBaseFeed.jsx:391-396`
- Implement `onChange` handler for textarea

### Phase 4: Editor & Export (Week 2-3)

**Step 4.1: Add Copy to Clipboard**
- File: `tmc-redacao/src/pages/CriarPostPage.jsx`
- Add "Copy Article" button in toolbar
- Copy title + linha fina + content
- Show toast confirmation

**Step 4.2: Show Tags in Review**
- File: `tmc-redacao/src/pages/criar/RevisarPage.jsx`
- Display aggregated selected tags
- Allow last-minute tag editing

### Phase 5: Testing (Week 3-4)

**Step 5.1: WordPress Integration Testing**
- Set up local WordPress environment
- Test plugin activation
- Test all 15 pages via HashRouter
- Test API connectivity with CORS

**Step 5.2: Error Handling**
- API timeout handling
- Network error recovery
- Validation feedback

**Step 5.3: LocalStorage Persistence (Optional)**
- Auto-save draft to localStorage
- Recover on page reload

**Step 5.4: End-to-End Testing**
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
| **Deployment** | WordPress Admin Plugin |
| **Input Sources** | Both RSS and Pasted Text equally important |
| **Article Length** | Minimum 2000 characters (TMC standard for columnists) |
| **Personas** | Currently mock data - will be designed |
| **Tones** | Currently mock data - will be designed |
| **Auth** | WordPress user authentication |

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

### WORDPRESS PLUGIN MIGRATION

| Task | Description | Hours |
|------|-------------|-------|
| **WP.1** | Create WordPress plugin structure (PHP files) | 4h |
| **WP.2** | Create uninstall.php for cleanup | 1h |
| **WP.3** | Add capability checks + security | 1h |
| **WP.4** | Add settings page for API URL config | 2h |
| **WP.5** | Modify Vite config for WordPress build | 4h |
| **WP.6** | Add aggressive CSS scoping (all:initial) | 3h |
| **WP.7** | Adjust CSS for WP admin bar offset | 1h |
| **WP.8** | Change BrowserRouter to HashRouter | 2h |
| **WP.9** | Use unique root ID (#tmc-redacao-root) | 1h |
| **WP.10** | Create WordPressContext.jsx | 2h |
| **WP.11** | Update api.js for dynamic base URL | 1h |
| **WP.12** | Update Header.jsx for WP user | 1h |
| **WP.13** | Add nonce to wp_localize_script | 1h |
| **WP.14** | Test in WordPress environment | 8h |
| | **Subtotal WordPress** | **32h** |

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
| **WordPress** | Plugin Migration | 32h |
| **TIER 2** | Quick Wins (Tag Selection + Copy) | 7h |
| **TIER 3** | Nice to Have (Themes + LocalStorage + Export) | 10h |
| **Testing** | E2E Testing + Bug Fixes | 7h |
| | | |
| **TOTAL MVP (TIER 1+WP+TIER 2+Testing)** | Minimum viable product | **68h** |
| **TOTAL COMPLETE (All Tiers)** | Full feature set | **78h** |

### Timeline Mapping

- **68 hours** = ~8-9 days of focused development (8h/day)
- **78 hours** = ~10 days of focused development

With a Feb 15 deadline (33 days from Jan 13):
- **Conservative estimate:** 2-3 weeks for full implementation + testing
- **Buffer:** 1-2 weeks for iterations and unforeseen issues

---

## Key Files Summary

**Backend (to create):**
- `FeedRSS/tmc-rss-collector/services/llm_service.py`
- `FeedRSS/tmc-rss-collector/functions/generation_api.py`

**Frontend (to create):**
- `tmc-redacao/src/services/api.js`
- `tmc-redacao/src/context/WordPressContext.jsx`

**Frontend (to modify):**
- `tmc-redacao/vite.config.js`
- `tmc-redacao/package.json`
- `tmc-redacao/src/main.jsx`
- `tmc-redacao/src/App.jsx`
- `tmc-redacao/src/index.css`
- `tmc-redacao/src/services/api.js`
- `tmc-redacao/src/components/layout/Header.jsx`
- `tmc-redacao/src/pages/crear/variantes/TextoBaseFeed.jsx`
- `tmc-redacao/src/pages/criar/RevisarPage.jsx`
- `tmc-redacao/src/pages/CriarPostPage.jsx`
- `tmc-redacao/src/context/CriarContext.jsx`
- `tmc-redacao/src/components/cards/ArticleCard.jsx`
- `tmc-redacao/src/components/criar/FeedSelector.jsx`

**WordPress Plugin (to create):**
- `tmc-redacao-wp/tmc-redacao.php` - Main plugin file with activation hooks
- `tmc-redacao-wp/uninstall.php` - CRITICAL: Cleanup on uninstall
- `tmc-redacao-wp/includes/class-tmc-redacao-admin.php` - Admin menu + settings
- `tmc-redacao-wp/includes/class-tmc-redacao-assets.php` - Script/style enqueuing
- `tmc-redacao-wp/views/admin-page.php` - React container with unique ID
- `tmc-redacao-wp/views/settings-page.php` - API URL configuration

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
8. **Access the tool via WordPress Admin menu (TMC Redacao)**

This delivers the core value proposition: **AI-powered journalistic writing with SEO optimization, delivered as a WordPress plugin**.
