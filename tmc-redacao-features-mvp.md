# TMC Redacao - Features para MVP

## Documento de Revisao de Features Frontend
### Features Mockadas que Precisam de Implementacao Real

---

## Sumario Executivo

Este documento lista TODAS as features do frontend TMC Redacao que estao atualmente em mockup e precisam ser implementadas com dados reais no MVP.

**Total de Features Identificadas:** 45+

**Categorias:**
- Coleta de Noticias: 8 features
- Google Trends: 6 features
- Feed e Artigos: 7 features
- Criacao com IA: 12 features
- Gerenciamento de Materias: 6 features
- Configuracoes: 3 features
- Autenticacao: 1 sistema completo
- Infraestrutura: 3 servicos background

---

# 1. SISTEMA DE COLETA E AGREGACAO DE NOTICIAS

## 1.1 Buscador de Noticias (RSS Feed)

**Arquivo:** `src/pages/config/BuscadorPage.jsx`

### O que esta mockado:
- Lista de fontes RSS com dados hardcoded em `mockSources` (G1, Folha, ESPN, TechCrunch, Valor Economico)
- Toggle ativo/inativo das fontes
- Frequencia de coleta (15min, 30min, 1h, 2h, 6h)
- Ultima coleta (timestamps simulados)
- Adicao, edicao e exclusao de fontes (apenas em memoria)
- Contador "156 materias coletadas hoje" (numero fixo)

### O que precisa ser implementado:

**API Backend:**
| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/sources` | POST | Criar nova fonte RSS |
| `/api/sources` | GET | Listar fontes |
| `/api/sources/:id` | PUT | Atualizar fonte |
| `/api/sources/:id` | DELETE | Deletar fonte |
| `/api/sources/:id/toggle` | PATCH | Ativar/desativar fonte |

**Servico de Coleta RSS (Background Job):**
- Parser de feeds RSS/Atom usando **rss-parser** (Node.js)
- Scheduler para respeitar frequencia configurada
- Validacao de URL do feed
- Extracao de favicon automatica
- Deteccao de categoria automatica
- Deduplicacao de artigos

**Banco de Dados:**
```sql
CREATE TABLE sources (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  name VARCHAR(255),
  url TEXT,
  favicon_url TEXT,
  active BOOLEAN DEFAULT true,
  frequency VARCHAR(10), -- '15min', '30min', '1h', '2h', '6h'
  category VARCHAR(100),
  last_fetch TIMESTAMP,
  created_at TIMESTAMP
);
```

---

# 2. INTEGRACAO COM GOOGLE TRENDS

## 2.1 Configuracao de Trends

**Arquivo:** `src/pages/config/TrendsPage.jsx`

### O que esta mockado:
- Lista de temas monitorados em `mockMonitoredTopics` (Tecnologia, IA, Eleicoes, Economia Brasil)
- Lista de termos excluidos em `mockExcludedTerms` (BBB, Reality Show, Celebridades)
- Contador de "tendencias encontradas" (numeros fixos)
- Selecao de regiao (BR, US, Global)
- Selecao de categorias de interesse

### O que precisa ser implementado:

**API Backend:**
| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/trends/topics` | POST | Adicionar tema para monitorar |
| `/api/trends/topics` | GET | Listar temas monitorados |
| `/api/trends/topics/:id` | DELETE | Remover tema |
| `/api/trends/exclusions` | POST | Adicionar termo excluido |
| `/api/trends/exclusions` | GET | Listar termos excluidos |
| `/api/trends/exclusions/:id` | DELETE | Remover termo excluido |
| `/api/trends/results` | GET | Buscar tendencias |

**Integracao Google Trends:**
- Usar **SerpAPI** ($50-250/mes) ou **DataForSEO** ($0.006/req)
- Coleta periodica a cada 1h via background job
- Aplicacao de filtros de exclusao
- Calculo de relevancia/score

## 2.2 TrendsSidebar - Visualizacao

**Arquivo:** `src/components/layout/TrendsSidebar.jsx`

### O que esta mockado:
- Google Trends em `mockGoogleTrends` (Eleicoes 2024, Black Friday, Copa do Brasil)
- Twitter Trending em `mockTwitterTrends` (#ForaBolsonaro, #Flamengo, #BBB24)
- Temas no Feed em `mockFeedThemes` (Dollar, Petrobras, Selic)
- Botao de pause/play (funcional apenas na UI)
- Timestamp "Atualizado ha 5 minutos" (fixo)

### O que precisa ser implementado:

**API Backend:**
| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/trends/google` | GET | Tendencias do Google atualizadas |
| `/api/trends/twitter` | GET | Trending topics do Twitter |
| `/api/trends/feed` | GET | Temas em alta no feed interno |

**Integracao Twitter API:**
- Twitter API v2 Basic ($100/mes) ou Bluesky AT Protocol (gratuito)
- Filtragem por localizacao (Brasil)
- Contagem de mencoes

**Real-time Updates:**
- WebSocket ou Server-Sent Events (SSE)
- Respeitar botao de pause/play
- Auto-refresh configuravel

---

# 3. FEED PRINCIPAL E ARTIGOS

## 3.1 RedacaoPage - Feed de Materias

**Arquivo:** `src/pages/RedacaoPage.jsx`

### O que esta mockado:
- Lista de artigos em `mockArticles` (8 artigos fixos)
- Filtros (categoria, origem, periodo, busca) - apenas filtram os mockados
- Botao "Carregar mais materias" (simula loading)
- Selecao de artigos (apenas estado local)

### O que precisa ser implementado:

**API Backend:**
| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/articles` | GET | Listar materias com paginacao |
| `/api/articles/stats` | GET | Estatisticas do dia |

**Query params para filtros:**
```
?page=1&limit=10&category=&source=&period=&search=
```

**Sistema de Busca:**
- Full-text search usando **Meilisearch** ($29/mes)
- Indexacao de titulo e conteudo
- Typo tolerance para portugues

## 3.2 ArticleCard - Cartao de Materia

**Arquivo:** `src/components/cards/ArticleCard.jsx`

### O que esta mockado:
- Checkbox de selecao (estado local)
- Tag de categoria (cores hardcoded)
- Preview do artigo
- Link externo

### O que precisa ser implementado:
- Extracao de imagem/thumbnail do RSS
- Score de relevancia calculado
- Estado de selecao persistente

---

# 4. CRIACAO DE CONTEUDO COM IA

## 4.1 CriarPostPage - Editor com IA

**Arquivo:** `src/pages/CriarPostPage.jsx`

### O que esta mockado:
- Editor de texto simples (textarea)
- Selecao de tom em `mockTones` (Formal, Informal, Tecnico, Persuasivo, Neutro)
- Selecao de persona em `mockPersonas` (Jornalista, Especialista, Colunista, Influencer)
- Botao de correcao ortografica (visual apenas)
- Botao de traducao (nao funcional)
- Botao de "Insights SEO" (nao funcional)
- Botao "Sugerir titulo" (nao funcional)
- Chat com assistente de IA (resposta simulada com timeout)
- Score SEO calculado localmente (wordCount / 5 + 30)
- Salvar como rascunho (simula com timeout)

### O que precisa ser implementado:

**APIs de IA (Claude 3.5 Haiku/Sonnet):**
| Endpoint | Metodo | Descricao | Modelo |
|----------|--------|-----------|--------|
| `/api/ai/chat` | POST | Chat contextual | Claude 3.5 Haiku |
| `/api/ai/suggest-title` | POST | Sugerir titulo | Claude 3.5 Haiku |
| `/api/ai/improve-paragraph` | POST | Melhorar texto | Claude 3.5 Sonnet |
| `/api/ai/translate` | POST | Traducao | Claude 3.5 Haiku |
| `/api/ai/seo-insights` | POST | Analise SEO | Claude 3.5 Haiku |
| `/api/ai/research` | POST | Pesquisar tema | Claude + Tavily |

**Prompts de IA necessarios:**

### Prompt: Chat Assistente
```
Voce e um assistente de redacao jornalistica brasileiro. Ajude o redator a:
- Sugerir angulos para a materia
- Melhorar a estrutura do texto
- Encontrar dados e estatisticas relevantes
- Responder duvidas sobre o tema

Tom: {tone}
Persona: {persona}
Contexto do artigo: {article_context}

Pergunta do usuario: {user_message}
```

### Prompt: Sugestao de Titulo
```
Com base no conteudo abaixo, sugira 5 titulos jornalisticos em portugues brasileiro.
Os titulos devem ser:
- Claros e objetivos
- Atrativos para cliques (sem ser clickbait)
- Entre 50-70 caracteres
- Usar verbos no presente quando possivel

Conteudo:
{content}

Retorne apenas os 5 titulos, um por linha.
```

### Prompt: Insights SEO
```
Analise o texto abaixo e forneca insights de SEO em portugues brasileiro:

1. Keywords principais identificadas (5-10)
2. Densidade de keywords (ideal: 1-2%)
3. Sugestoes de meta description (max 160 chars)
4. Estrutura de headings (H1, H2, H3)
5. Sugestoes de links internos
6. Score de legibilidade (Flesch-Kincaid adaptado para PT-BR)
7. Pontos de melhoria

Texto:
{content}

Retorne em formato JSON estruturado.
```

### Prompt: Correcao Ortografica
```
Corrija o texto abaixo mantendo o estilo e tom original.
Identifique:
- Erros de ortografia
- Erros de concordancia
- Erros de pontuacao
- Sugestoes de estilo

Texto:
{content}

Retorne o texto corrigido e uma lista de alteracoes feitas.
```

**Editor de Texto Rico:**
- Integrar **TipTap** ou **Lexical** (React)
- Formatacao (negrito, italico, listas, links, imagens)
- Undo/redo real
- Markdown support

**Correcao Ortografica:**
- Integrar **LanguageTool API** (gratuito ate 20 req/min)
- Highlight de erros inline

## 4.2 CriarInspiracaoPage - Criacao com Inspiracao

**Arquivos:**
- `src/pages/CriarInspiracaoPage/index.jsx`
- `src/pages/CriarInspiracaoPage/StepOne.jsx`
- `src/pages/CriarInspiracaoPage/StepTwo.jsx`
- `src/pages/CriarInspiracaoPage/StepThree.jsx`

### O que esta mockado:

**Step 1:**
- Selecao de artigos inspiradores
- Selecao de paragrafos de cada artigo
- Selecao de tom e persona

**Step 2:**
- Barra de progresso simulada
- Textos de loading mockados
- Timeout de 5 segundos

**Step 3:**
- Conteudo gerado mockado (texto fixo)
- Metricas mockadas (Palavras: 156, Originalidade: 87%, SEO: 72/100)
- Sugestoes de melhoria mockadas
- Keywords SEO mockadas

### O que precisa ser implementado:

**API de Geracao com IA:**
| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/ai/generate-inspired` | POST | Gerar conteudo baseado em artigos |

**Request Body:**
```json
{
  "articles": [
    {
      "id": "uuid",
      "title": "Titulo do artigo",
      "selectedParagraphs": [0, 1, 2],
      "content": "Conteudo completo..."
    }
  ],
  "tone": "formal",
  "persona": "jornalista",
  "settings": {
    "minWords": 300,
    "maxWords": 800,
    "includeStats": true
  }
}
```

### Prompt: Geracao Inspirada
```
Voce e um jornalista brasileiro experiente. Com base nos artigos de referencia abaixo, crie um NOVO artigo ORIGINAL sobre o mesmo tema.

IMPORTANTE:
- NAO copie trechos dos artigos originais
- Use as informacoes como base para criar conteudo novo
- Mantenha o tom {tone} e a perspectiva de {persona}
- Inclua dados e estatisticas quando relevante
- Estruture com introducao, desenvolvimento e conclusao
- Tamanho: {minWords}-{maxWords} palavras

ARTIGOS DE REFERENCIA:
{articles_content}

PARAGRAFOS SELECIONADOS COMO FOCO:
{selected_paragraphs}

Gere o artigo em portugues brasileiro, formatado em Markdown.
```

**Streaming Response (SSE):**
- Progresso em tempo real durante geracao
- Feedback visual para o usuario

**Analise de Originalidade:**
- Comparar com fontes usando embeddings (**pgvector**)
- Score de originalidade (% de texto novo)

**Banco de Dados:**
```sql
CREATE TABLE ai_generations (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  type VARCHAR(50), -- 'inspired', 'chat', 'suggestion'
  input_data JSONB,
  output_data JSONB,
  tone VARCHAR(50),
  persona VARCHAR(50),
  originality_score DECIMAL(5,2),
  seo_score INT,
  created_at TIMESTAMP
);
```

---

# 5. GERENCIAMENTO DE MATERIAS

## 5.1 MinhasMaterias - Listagem

**Arquivo:** `src/pages/MinhasMaterias.jsx`

### O que esta mockado:
- Lista de materias do usuario em `myArticles` (10 artigos fixos)
- Filtros (busca, status, categoria, data)
- Paginacao (6 itens por pagina)
- Botoes Ver, Editar, Excluir (apenas console.log)
- Modal de confirmacao de exclusao

### O que precisa ser implementado:

**API Backend:**
| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/my-articles` | GET | Listar materias do usuario |
| `/api/my-articles/:id` | GET | Detalhes de uma materia |
| `/api/my-articles/:id` | PUT | Atualizar materia |
| `/api/my-articles/:id` | DELETE | Deletar materia |
| `/api/my-articles/:id/metrics` | GET | Metricas da materia |

**Pagina de Edicao:**
- Rota `/editar/:id`
- Carregar rascunho existente no editor
- Manter historico de edicoes

**Sistema de Metricas:**
- Rastreamento de visualizacoes
- Tempo medio de leitura
- Integracao com **GA4 Data API** (gratuito)

---

# 6. CONFIGURACOES

## 6.1 Paginas Placeholder

**Arquivo:** `src/App.jsx`

### Rotas mockadas:
- `/configuracoes/perfil` - Placeholder
- `/configuracoes/integracoes` - Placeholder
- `/configuracoes/preferencias` - Placeholder

### O que precisa ser implementado:

**Perfil:**
- Editar nome, email, avatar
- Alterar senha
- Gerenciar notificacoes

**Integracoes:**
- Conectar contas (Twitter, LinkedIn)
- API keys (OpenAI, Google)
- Webhooks

**Preferencias:**
- Tema (claro/escuro)
- Auto-save interval
- Notificacoes

---

# 7. AUTENTICACAO

**Status:** Nao implementado

### O que precisa ser implementado:

**Paginas:**
- Login
- Registro
- Recuperacao de senha

**API Backend:**
| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/auth/register` | POST | Registro de usuario |
| `/api/auth/login` | POST | Login |
| `/api/auth/logout` | POST | Logout |
| `/api/auth/forgot-password` | POST | Solicitar reset |
| `/api/auth/reset-password` | POST | Resetar senha |
| `/api/auth/me` | GET | Usuario atual |

**Tecnologia Recomendada:**
- **Microsoft Entra ID** (SSO corporativo) ou
- **JWT** com refresh tokens

**React Context:**
```javascript
// AuthContext
const AuthContext = createContext({
  user: null,
  login: async () => {},
  logout: async () => {},
  isAuthenticated: false,
  isLoading: true
});
```

---

# 8. INFRAESTRUTURA BACKEND

## 8.1 API Backend

**Stack Recomendada:**
- **Azure Functions** (serverless) ou **Node.js Express**
- **PostgreSQL** (Azure Flexible Server) - $13/mes
- **Upstash Redis** (cache) - $0-10/mes
- **Azure Blob Storage** - $5/mes

## 8.2 Background Jobs

| Job | Frequencia | Descricao |
|-----|------------|-----------|
| RSS Collector | Configuravel (15min-6h) | Coleta de feeds RSS |
| Google Trends Monitor | 1h | Buscar tendencias |
| Twitter Trends | 30min | Buscar trending topics |
| Feed Themes Calculator | 1h | Calcular temas em alta no feed |
| Cleanup | 1x/dia | Remover dados antigos |

---

# 9. APIS EXTERNAS NECESSARIAS

## 9.1 IA Generativa

| Servico | Uso | Custo Estimado |
|---------|-----|----------------|
| **Claude 3.5 Haiku** | Chat, sugestoes, tags | $0.80-4/MTok |
| **Claude 3.5 Sonnet** | Geracao inspirada, analise | $3-15/MTok |
| **Tavily API** | Enriquecimento de contexto | Gratis ate 1k/mes |

## 9.2 Trends e Dados

| Servico | Uso | Custo Estimado |
|---------|-----|----------------|
| **SerpAPI** | Google Trends | $50-250/mes |
| **Bluesky AT Protocol** | Social trends | Gratuito |
| **OpenWeatherMap** | Dados de clima | Gratuito |
| **API-Football** | Resultados esportivos | Gratuito |

## 9.3 Outros

| Servico | Uso | Custo Estimado |
|---------|-----|----------------|
| **LanguageTool** | Correcao ortografica | Gratuito (20 req/min) |
| **Meilisearch** | Busca full-text | $29/mes |
| **GA4 Data API** | Metricas de visualizacao | Gratuito |

---

# 10. MODELO DE DADOS

```sql
-- Usuarios
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  avatar_url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Fontes RSS
CREATE TABLE sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  name VARCHAR(255) NOT NULL,
  url TEXT NOT NULL,
  favicon_url TEXT,
  active BOOLEAN DEFAULT true,
  frequency VARCHAR(10) DEFAULT '1h',
  category VARCHAR(100),
  last_fetch TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Materias coletadas
CREATE TABLE collected_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID REFERENCES sources(id),
  title TEXT NOT NULL,
  content TEXT,
  preview TEXT,
  url TEXT UNIQUE,
  image_url TEXT,
  category VARCHAR(100),
  tags TEXT[],
  published_at TIMESTAMP,
  collected_at TIMESTAMP DEFAULT NOW()
);

-- Materias do usuario
CREATE TABLE my_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  title TEXT NOT NULL,
  content TEXT,
  preview TEXT,
  status VARCHAR(20) DEFAULT 'draft',
  category VARCHAR(100),
  tags TEXT[],
  tone VARCHAR(50),
  persona VARCHAR(50),
  seo_score INT,
  views INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  published_at TIMESTAMP
);

-- Temas monitorados
CREATE TABLE monitored_topics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  topic VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Termos excluidos
CREATE TABLE excluded_terms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  term VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Resultados de trends
CREATE TABLE trends_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50), -- 'google', 'twitter', 'feed'
  topic VARCHAR(255) NOT NULL,
  value VARCHAR(50), -- volume ou mencoes
  trend VARCHAR(20), -- 'up', 'down', 'stable'
  region VARCHAR(10),
  category VARCHAR(100),
  fetched_at TIMESTAMP DEFAULT NOW()
);

-- Historico de geracoes IA
CREATE TABLE ai_generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  type VARCHAR(50) NOT NULL,
  input_data JSONB,
  output_data JSONB,
  tone VARCHAR(50),
  persona VARCHAR(50),
  tokens_used INT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indice para busca full-text
CREATE INDEX idx_collected_articles_search
ON collected_articles USING gin(to_tsvector('portuguese', title || ' ' || content));

-- Indice para busca por embedding (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE collected_articles ADD COLUMN embedding vector(1536);
CREATE INDEX idx_collected_articles_embedding
ON collected_articles USING hnsw (embedding vector_cosine_ops);
```

---

# 11. FASES DE IMPLEMENTACAO

## FASE 1 - Core (MVP Minimo)
**Prioridade:** Essencial

| Feature | Descricao | Estimativa |
|---------|-----------|------------|
| Autenticacao | Login, registro, JWT | 1 semana |
| Backend API | Setup basico Azure Functions | 1 semana |
| Database | PostgreSQL + schema | 3 dias |
| RSS Collector | Servico de coleta | 1 semana |
| Feed principal | API + filtros + paginacao | 1 semana |
| Salvar rascunho | CRUD de materias | 3 dias |

**Total Fase 1:** ~5 semanas

## FASE 2 - IA Basica
**Prioridade:** Alta

| Feature | Descricao | Estimativa |
|---------|-----------|------------|
| Chat assistente | Integracao Claude | 1 semana |
| Geracao inspirada | Steps 1-3 funcionais | 2 semanas |
| Sugerir titulo | Botao funcional | 2 dias |
| Correcao ortografica | LanguageTool | 3 dias |
| Editor rico | TipTap integration | 1 semana |

**Total Fase 2:** ~5 semanas

## FASE 3 - Trends e Analytics
**Prioridade:** Media

| Feature | Descricao | Estimativa |
|---------|-----------|------------|
| Google Trends | Coleta + config | 1 semana |
| TrendsSidebar | Dados reais | 3 dias |
| Bluesky Trends | Integracao | 3 dias |
| Metricas basicas | Views, tempo leitura | 3 dias |
| Minhas Materias | CRUD completo | 3 dias |

**Total Fase 3:** ~3 semanas

## FASE 4 - Polish
**Prioridade:** Baixa

| Feature | Descricao | Estimativa |
|---------|-----------|------------|
| SEO Analysis | Keywords, readability | 1 semana |
| Configuracoes | Perfil, integracoes | 1 semana |
| Notificacoes | Email, in-app | 3 dias |
| Tema escuro | Dark mode | 2 dias |

**Total Fase 4:** ~3 semanas

---

# 12. CUSTOS ESTIMADOS (MVP)

## Infraestrutura Mensal

| Servico | Custo |
|---------|-------|
| Azure PostgreSQL (B1ms) | $13 |
| Azure Functions | Gratis (1M exec) |
| Azure Blob Storage | $5 |
| Upstash Redis | $0-10 |
| **Subtotal Infra** | **~$28/mes** |

## APIs Externas Mensal

| Servico | Custo |
|---------|-------|
| Claude API (estimado) | $20-50 |
| SerpAPI (Developer) | $50 |
| Meilisearch Cloud | $29 |
| **Subtotal APIs** | **~$99-129/mes** |

## Total MVP

| Item | Custo |
|------|-------|
| Infraestrutura | ~$28/mes |
| APIs Externas | ~$99-129/mes |
| **TOTAL** | **~$127-157/mes** |

---

# 13. CHECKLIST DE IMPLEMENTACAO

## Fase 1 - Core
- [ ] Setup Azure Functions
- [ ] Setup PostgreSQL + schema
- [ ] Implementar autenticacao (registro, login, JWT)
- [ ] Implementar CRUD de fontes RSS
- [ ] Implementar RSS Collector (background job)
- [ ] Implementar API de artigos coletados
- [ ] Implementar filtros e paginacao
- [ ] Implementar CRUD de materias do usuario
- [ ] Conectar frontend com APIs

## Fase 2 - IA
- [ ] Setup Claude API
- [ ] Implementar chat assistente
- [ ] Implementar geracao inspirada (streaming)
- [ ] Implementar sugestao de titulo
- [ ] Integrar LanguageTool
- [ ] Integrar editor TipTap
- [ ] Criar todos os prompts de IA

## Fase 3 - Trends
- [ ] Setup SerpAPI
- [ ] Implementar coleta Google Trends
- [ ] Implementar Bluesky trends
- [ ] Implementar calculo de temas do feed
- [ ] Atualizar TrendsSidebar com dados reais
- [ ] Implementar metricas basicas

## Fase 4 - Polish
- [ ] Implementar analise SEO
- [ ] Criar paginas de configuracao
- [ ] Implementar notificacoes
- [ ] Implementar tema escuro
- [ ] Testes e2e
- [ ] Documentacao

---

*Documento gerado em: Dezembro 2025*
*Projeto: TMC Redacao - Features MVP*
