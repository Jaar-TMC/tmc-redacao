# TMC - Ferramenta de Redacao

AI-powered newsroom tool that collects RSS feeds, scores articles editorially, clusters them into semantic themes, and generates journalistic articles with anti-hallucination safeguards.

## Project Structure

```
.
├── FeedRSS/tmc-rss-collector/   # Python backend (Azure Functions)
│   ├── function_app.py          # Entry point - routes all HTTP/Timer triggers
│   ├── functions/               # 14 handler modules (HTTP + Timer triggers)
│   ├── services/                # 18 service modules (core business logic)
│   ├── models/                  # 9 Pydantic models
│   ├── utils/                   # Auth decorators
│   ├── migrations/              # 13 SQL migration files
│   ├── scripts/                 # Audit, migration, seed scripts
│   └── monitoring/              # KQL queries, alerting rules, runbooks
├── tmc-redacao/                 # React frontend (Vite + Tailwind)
│   ├── src/
│   │   ├── pages/               # 19 page components (lazy-loaded)
│   │   ├── components/          # auth/, cards/, criar/, editor/, layout/, onboarding/, ui/
│   │   ├── context/             # 8 React Context providers
│   │   ├── services/            # api.js, auth.js, apiCache.js, userApi.js
│   │   ├── hooks/               # 8 custom hooks
│   │   ├── utils/               # Formatters, transformers, SEO, markdown
│   │   └── constants/           # editorial.js, permissions.js, seoConstants.js
│   └── staticwebapp.config.json # Azure SWA routing + security headers
├── gcp-setup/                   # Alternative GCP deployment scripts
└── docs/                        # Architecture docs, specs, project plans
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite 7, Tailwind CSS 4, React Router 7, TipTap 3 (rich text), Lucide React (icons) |
| **Backend** | Python 3.11, Azure Functions v2 (13 HTTP triggers, 5 timer triggers) |
| **Database** | Azure SQL Server (pymssql), 13 migrations |
| **LLM** | Claude Sonnet 4.5 (generation, fact-check), Claude Haiku 4.5 (classification, scoring) via Azure AI proxy |
| **Embeddings** | Azure OpenAI text-embedding-3-small (1536 dims) |
| **Search** | Exa AI (pre-generation factual enrichment) |
| **Auth** | JWT (access 60min + refresh 7d httpOnly cookie) |

## Deployment

### Frontend (Azure Static Web Apps)
- **URL**: https://purple-river-09235a310.3.azurestaticapps.net/
- **Deploy**: Automatic via GitHub Actions on push to `main`
- **Workflow**: `.github/workflows/azure-static-web-apps-purple-river-09235a310.yml`
- **Build**: `cd tmc-redacao && npm run build` (outputs to `dist/`)
- **DO NOT deploy to Vercel** - only Azure SWA

### Backend (Azure Functions)
- **URL**: https://tmc-redacao-api-b7h3dyaxazfvdcez.eastus2-01.azurewebsites.net/
- **Deploy**: Manual via CLI
  ```bash
  cd FeedRSS/tmc-rss-collector
  func azure functionapp publish tmc-redacao-api --python
  ```
- **Azure subscription**: Microsoft Azure Sponsorship
- **Account**: enzo.oliveira@jaarconsult.com.br
- **Runtime**: Python 3.11, Extension Bundle v4

### Git Setup
- **origin**: https://github.com/enzocarvalhotech/tmc-redacao.git (personal)
- **upstream**: https://github.com/Jaar-TMC/tmc-redacao.git (organization)
- **Branch strategy**: Single `main` branch, push triggers CI/CD
- **Commits**: Conventional commits (`feat:`, `fix:`, `perf:`, `refactor:`, `chore:`, `docs:`, `test:`)

## Data Pipeline

### Collection (every 15min)
```
RSS Feeds → parse → deduplicate → filter <300 chars → enrich images → AI classify → insert DB → score (A/B/C) → embed → cluster into themes
```

### Article Generation (on-demand)
```
User selects sources → extract topics → configure (category, tone, type)
→ validate (MIN_SOURCE_CHARS=300) → Exa enrichment → LLM generation
→ temporal decontamination → claim verification (10 claims)
→ CoVe for fabricated claims → quality loop (up to 3 regen)
→ safety gates → assign publication status
```

## Backend Architecture

### Timer Triggers (Scheduled)
| Function | Schedule | Purpose |
|----------|----------|---------|
| `rss_collector` | Every 15 min | Fetch RSS, dedup, filter short, AI enrich, insert, score inline |
| `embedding_generator` | Every 5 min | Generate embeddings for unprocessed articles (batch 50) |
| `scoring_calculator` | Every 10 min | Backfill A/B/C scores for unscored articles |
| `clustering_engine` | Every 30 min | Group articles into semantic themes (cosine sim >= 0.50) |
| `clustering_maintenance` | Daily 3AM | Merge similar themes, remove orphans, recalculate scores |

### Key Services
| Service | Size | Purpose |
|---------|------|---------|
| `database.py` | 131 KB | ConnectionPool, all CRUD, SQL queries, soft deletes |
| `llm_service.py` | 117 KB | Claude API calls, category prompts, JSON repair, retry logic |
| `fact_check_service.py` | 110 KB | Anti-hallucination: enrichment, claim extraction, CoVe, confidence |
| `clustering_service.py` | 57 KB | Semantic clustering, centroid EMA, theme merging |
| `scoring_service.py` | 32 KB | A/B/C editorial scoring (4 signals: inesperado, impacto, busca_agora, conversa) |
| `youtube_service.py` | 36 KB | YouTube caption extraction via InnerTube API |
| `config.py` | 9 KB | Singleton AppConfig (frozen dataclass), all env var loading |
| `auth_service.py` | 3 KB | JWT encode/decode, token blacklist |
| `rate_limiter.py` | 3 KB | Token bucket (generate: 0.5 req/sec, burst=3) |

### API Endpoints (HTTP Triggers)
- **Articles**: `GET /api/articles`, `GET /api/articles/{id}`, `GET /api/categories`, `GET /api/trending-tags`, `GET /api/tags`
- **Sources**: `GET|POST /api/sources`, `GET|PUT|DELETE /api/sources/{id}`, `POST /api/sources/{id}/collect`
- **Generation**: `POST /api/generate`, `/api/extract-topics`, `/api/generate-tags`, `/api/merge-topics`, `/api/edit-article`
- **Auth**: `POST /api/login`, `/api/refresh`, `/api/logout`, `GET /api/me`
- **Users**: `GET|POST /api/users`, `GET|PUT|DELETE /api/users/{id}`, `POST /api/users/{id}/reset-password`
- **User Articles**: `GET|POST /api/user-articles`, `GET|PUT|DELETE /api/user-articles/{id}`
- **Themes**: `GET /api/semantic-themes`, `GET /api/semantic-themes/{id}`
- **Transcription**: `POST /api/transcribe`
- **Admin**: `GET /api/health` (no auth), `GET /api/stats`, `GET /api/metrics`

## Frontend Architecture

### Routes
| Path | Page | Auth |
|------|------|------|
| `/login` | LoginPage | Public |
| `/` | RedacaoPage (main feed) | Required |
| `/criar` | SelecionarFontePage | Required |
| `/criar/texto-base` | TextoBasePage | Required |
| `/criar/configurar` | ConfigurarPage | Required |
| `/criar/revisar` | RevisarPage | Required |
| `/criar/editor` | CriarPostPage | Required |
| `/transcricao` | TranscricaoPage | Required |
| `/minhas-materias` | MinhasMaterias | Required |
| `/editar/:articleId` | CriarPostPage | Required |
| `/configuracoes` | ConfiguracoesPage | Required |
| `/configuracoes/buscador` | BuscadorPage | Required |
| `/configuracoes/usuarios` | UsuariosPage | `manage_users` permission |

### State Management
8 React Context providers: `AuthProvider`, `ArticlesProvider`, `FiltersProvider`, `UIProvider`, `CriarProvider`, `ArticlesCacheProvider`, `OnboardingProvider`, `WordPressProvider`

### Build Targets
1. **Standard** (`npm run build`): Code-split, lazy-loaded pages, manual chunks for TipTap/DOMPurify
2. **WordPress** (`npm run build:wp`): Single bundle, fixed filenames (`js/tmc-redacao.js`)

## Safety Gates & Thresholds

### Content Length Gates
| Threshold | Value | Effect |
|-----------|-------|--------|
| `RSS_MIN_CONTENT_CHARS` | 300 | Article filtered at collection (not saved) |
| `MIN_SOURCE_CHARS` | 300 | Hard reject at generation |
| `NOTA_ONLY_THRESHOLD` | 500 | Force "nota" brief format |
| `SHORT_SOURCE_THRESHOLD` | 800 | Downgrade to "servico" category |

### Publication Safety
| Gate | Threshold | Action |
|------|-----------|--------|
| Confidence floor | < 0.65 | HARD BLOCK |
| Grounded claims | < 70% | HARD BLOCK |
| Expansion ratio | > 8.0x | HARD BLOCK |
| High risk level | Any | HARD BLOCK (production) |
| Quality loop exhaustion | 3 attempts | Block if critical criteria fail |

### Scoring System (0-100 points)
| Signal | Values | Max Points |
|--------|--------|------------|
| inesperado (unexpected) | yes=25, partial=12, no=0 | 25 |
| impacto (impact) | high=30, medium=15, low=0 | 30 |
| busca_agora (trending) | yes=25, maybe=12, no=0 | 25 |
| conversa (discussion) | yes=20, maybe=10, no=0 | 20 |
| **Classification** | A >= 75, B >= 35, C < 35 | **100** |

### Clustering
- Similarity threshold: 0.50 (cosine distance)
- Centroid EMA alpha: 0.15
- Theme merge threshold: 0.90
- Max articles per clustering run: 100

## Model Routing

| Task | Model | Cost Tier |
|------|-------|-----------|
| Article generation | claude-sonnet-4-5 | High |
| Fact checking | claude-sonnet-4-5 | High |
| Article editing | claude-sonnet-4-5 | High |
| Topic merging | claude-sonnet-4-5 | High |
| Enrichment extraction | claude-sonnet-4-5 | High |
| Classification | claude-haiku-4-5 | Low |
| Scoring | claude-haiku-4-5 | Low |
| Theme naming | claude-haiku-4-5 | Low |
| Event extraction | claude-sonnet-4-5 | High |
| Event verification | claude-sonnet-4-5 | High |
| Embeddings | text-embedding-3-small | Low |

## Database Tables (Azure SQL Server)

| Table | Purpose |
|-------|---------|
| `sources` | RSS feed sources (url, name, category, frequency, active) |
| `collected_articles` | Main articles table + denormalized scores (migration 013) |
| `article_scores` | Detailed editorial scores (4 signals: inesperado, impacto, busca_agora, conversa) |
| `article_embeddings` | 1536-dim vectors for semantic clustering |
| `themes` | Semantic article clusters (centroid vector, classification, status) |
| `article_themes` | Theme-article N:N mapping with similarity_score and is_primary |
| `users` | Auth users (email, password_hash, role, lockout) |
| `user_articles` | User-generated articles (draft/published, soft-delete via deleted_at) |
| `collection_logs` | RSS collection run logs (articles_found, articles_new, duration_ms) |
| `token_blacklist` | Revoked JWT tokens |
| `auth_audit_log` | Login event tracking (user_id, event_type, ip_address) |
| `llm_usage_log` | LLM cost tracking (model, task_type, input/output tokens) |
| `generation_audit_trail` | Generation history (params, confidence, risk, review flags) |
| `event_signatures` | Event entity extraction (people, orgs, locations, action) |

## Environment Variables

### Required (Backend)
```
SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD
JWT_SECRET_KEY (min 32 chars in production)
ANTHROPIC_API_KEY or AZURE_AI_API_KEY (one required)
AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT
```

### Optional (Backend)
```
EXA_API_KEY                        # Enables enrichment (disabled without)
CORS_ALLOWED_ORIGINS               # Comma-separated allowed origins
PRODUCTION_SAFETY_MODE=true        # Forces fact-check, requires JWT secret
AI_ENRICHMENT_ENABLED=true         # AI classification during collection
CLUSTERING_ENABLED=true            # Semantic clustering
QUALITY_LOOP_ENABLED=true          # Regen loop for low-quality articles
RSS_MIN_CONTENT_CHARS=300          # Filter short articles at collection
```

### Frontend
```
VITE_API_BASE_URL=http://localhost:7071/api   # Backend API URL
```

## Code Conventions

### Backend (Python)
- Files: `snake_case.py`
- Classes: `PascalCase` (DatabaseService, AppConfig)
- Functions: `snake_case` (generate_article_handler)
- Constants: `SCREAMING_SNAKE_CASE` (MIN_SOURCE_CHARS)
- Models: `PascalCase` Pydantic (Article, UserCreate)
- All handlers: `async def` with `@with_cors @require_auth` decorators
- Error handling: tenacity retries (3x exponential backoff) for API calls
- Logging: `logger.info` for milestones, `logger.error` for failures
- Singleton services: `get_db()`, `get_config()`, `get_scoring_service()`

### Frontend (React/JSX)
- Components: `PascalCase.jsx` (ArticleCard.jsx)
- Pages: `PascalCase.jsx` (RedacaoPage.jsx)
- Hooks: `camelCase.js` with `use` prefix (useForm.js)
- Services: `camelCase.js` (api.js, apiCache.js)
- Utils: `camelCase.js` (formatters.js)
- Constants: `camelCase.js` (editorial.js)
- All components: Functional with hooks, PropTypes for validation
- State: React Context API (no Zustand/Redux)
- Imports: `import { useAuth } from '../context'`
- Icons: Lucide React (`import { Sparkles } from 'lucide-react'`)
- Theme colors (Tailwind v4 custom properties in `src/index.css`):
  - Primary: `--color-tmc-orange: #E87722`
  - Dark green: `#1A4D2E`, Light green: `#2D5A3D`
  - Background: `--color-off-white: #F5F5F5`
  - Status: success `#10B981`, warning `#F59E0B`, error `#EF4444`, live-red `#E53935`

### Git
- Conventional commits: `feat:`, `fix:`, `perf:`, `refactor:`, `chore:`, `docs:`, `test:`
- Atomic commits: one logical change per commit
- No pre-commit hooks configured

## Development

### Frontend
```bash
cd tmc-redacao
npm install
npm run dev          # http://localhost:5173
npm run build        # Production build → dist/
npm run lint         # ESLint check
npm run build:wp     # WordPress single-bundle build
```

### Backend
```bash
cd FeedRSS/tmc-rss-collector
pip install -r requirements.txt
func start                        # Local Azure Functions (http://localhost:7071)
```

### Database Migrations
```bash
cd FeedRSS/tmc-rss-collector
python scripts/run_migrations.py  # Run all pending migrations
python scripts/seed_admin.py      # Create initial admin user
```

### Testing
```bash
cd FeedRSS/tmc-rss-collector
pytest tests/                                    # Unit tests
python scripts/test_10_articles_audit.py         # 10-article generation audit
python scripts/full_pipeline_audit.py            # Full pipeline audit
```

## Gotchas

- `database.py` is ~130KB and `llm_service.py` is ~117KB — never rewrite these wholesale. Use targeted edits.
- `fact_check_service.py` is ~110KB — same rule, surgical edits only.
- The main articles table is called `collected_articles`, not `articles`.
- Scores are denormalized into `collected_articles` (migration 013) — when modifying scoring, update both `article_scores` AND the denormalized columns.
- Backend `.gitignore` excludes `scripts/` and `*.md` — these files won't appear in git status but exist on disk.
- `function_app.py` (1177 lines) registers ALL routes — a single handler file can map to multiple HTTP endpoints.

## Key Architectural Decisions

1. **Denormalized scores** (migration 013): Scores copied into `articles` table for 60x faster filtering (eliminates JOIN on every list query)
2. **Short article filter**: Articles < 300 chars rejected at RSS collection to save AI tokens on classification, scoring, embedding
3. **Stale-while-revalidate**: Frontend shows cached data immediately, refreshes in background
4. **TTL cache + request dedup**: `apiCache.js` prevents duplicate API calls with configurable TTL per resource
5. **Connection pooling with idle checks**: Skip health pings if connection used < 60s ago
6. **Rate limiting**: Token bucket on generation endpoints (0.5 req/sec, burst 3)
7. **Production safety mode**: Forces fact-checking, requires CORS origins and strong JWT secret
8. **Soft deletes**: Users, sources, and user articles use `is_deleted` flag (never hard-delete)

## Monitoring

- **Application Insights**: Enabled in `host.json`
- **KQL dashboards**: `monitoring/kql_queries.md`
- **Alerting rules**: `monitoring/alerting_rules.md`
- **Rollback runbook**: `monitoring/rollback_runbook.md`
- **LLM cost tracking**: `llm_usage_log` table tracks every API call (model, tokens, cost_usd)
- **Generation audit**: `generation_audit_trail` table logs confidence, risk level, review flags

## Documentation

Architecture docs, specs, and project plans are in `docs/` (including `specs/` and `plans/` subdirectories).
