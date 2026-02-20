# Plano de Migração Azure → Google Cloud Platform (TMC)

## Contexto
O app TMC (Ferramenta de Redação Jornalística) roda hoje 100% na Azure. O cliente quer migrar para GCP. Este documento detalha os serviços a contratar, passo a passo pelo Console, e checklist para a reunião.

---

## 1. MAPEAMENTO DE SERVIÇOS: AZURE → GCP

São os **mesmos serviços** que já usamos no Azure, só com nomes diferentes:

| Azure (Atual) | GCP (Novo) | Custo Estimado/mês |
|---|---|---|
| Azure Functions (Python) | **Cloud Run** | ~$45 |
| Azure SQL Server | **Cloud SQL PostgreSQL** | ~$130 |
| Azure Static Web Apps | **Firebase Hosting** | $0-5 |
| Azure AI Foundry (Claude) | **Vertex AI — `claude-sonnet-4-5`** | por uso |
| Azure OpenAI (embeddings) | **Vertex AI — `gemini-embedding-001`** | por uso |
| Application Insights | **Cloud Monitoring + Logging** (automático) | $0 (free tier) |
| Env vars do Function App | **Secret Manager** | $0 (free tier) |
| GitHub Actions | **GitHub Actions** (mantém igual) | $0 |

Único serviço novo: **Artifact Registry** (repositório Docker p/ Cloud Run) — grátis no free tier.

**Total estimado: ~$200-350/mês** (inclui APIs de IA)

---

## 2. REGIÃO: US-CENTRAL1 (IOWA)

Todos os recursos devem ser criados em **`us-central1` (Iowa)** — a região mais barata do GCP.

**Por que US Central e não São Paulo?** O TMC é uma ferramenta editorial interna, não um app consumer. As operações pesadas (geração de matéria, embeddings, fact-check) já levam segundos — 150ms extra de latência é irrelevante. A navegação entre páginas fica ~150ms mais lenta, mas imperceptível no uso real.

| Critério | US Central (Iowa) | São Paulo | Impacto real |
|---|---|---|---|
| Latência rede | ~150-200ms | ~5-15ms | Imperceptível (ops pesadas levam segundos) |
| Cloud SQL (2 vCPU) | ~$130/mês | ~$180/mês | **Economia $50/mês** |
| Cloud Run | ~$45/mês | ~$65/mês | **Economia $20/mês** |
| **Economia total** | **~$70/mês ($840/ano)** | - | - |

> Firebase Hosting distribui globalmente via CDN — o frontend não é afetado pela região.

---

## 3. O QUE CRIAR NO GCP — PELO CONSOLE

### Recursos a criar (5 principais):
1. **Cloud Run Service** — backend Python (substitui Azure Functions)
2. **Cloud SQL PostgreSQL** — banco de dados (substitui Azure SQL)
3. **Firebase Hosting** — frontend React (substitui Static Web Apps)
4. **Vertex AI** — Claude para geração + Gemini para embeddings
5. **Secret Manager** — API keys e connection strings (substitui env vars do Azure)

### APIs que precisam ser habilitadas:

Habilitadas em: **Console → APIs & Services → Enable APIs** (buscar pelo nome)

| API | Por quê |
|---|---|
| Cloud Run API | Backend |
| Cloud SQL Admin API | Banco de dados |
| Vertex AI API | LLM Claude + Gemini embeddings |
| Secret Manager API | Guardar API keys |
| Artifact Registry API | Guardar imagem Docker do backend |
| Firebase Hosting API | Frontend React |

> **Monitoring e Logging** já vêm habilitados automaticamente em todo projeto GCP.

---

## 4. PASSO A PASSO PELO CONSOLE (Reunião com o Cliente)

### ETAPA 1: Seu Acesso ao Ambiente

**O que pedir ao cliente ANTES da reunião:**
- Organization ID do GCP dele
- Que ele esteja logado como admin/owner

**Na reunião — cliente faz isso:**
1. Abrir **Console GCP** → **IAM & Admin** → **IAM**
2. Clicar **"Grant Access"**
3. Em "New principals": digitar seu email Google (ex: `enzo.oliveira@jaarconsult.com.br` ou Gmail pessoal)
4. Em "Role": selecionar **Owner** (temporário, para fazer o setup)
5. Clicar **Save**

**Melhor prática de acesso:**
- Use sua conta Google **já existente** (pessoal ou @jaarconsult)
- NÃO precisa criar conta no Google Workspace do cliente
- O cliente só te adiciona via IAM — simples e rápido
- Depois do setup, reduzir para roles específicas (seção 6)

---

### ETAPA 2: Criar Projeto Novo

1. No canto superior, clicar no **seletor de projeto** (dropdown)
2. Clicar **"New Project"**
3. Preencher:
   - **Project name**: `TMC Producao`
   - **Organization**: selecionar a organização do cliente
   - **Billing account**: selecionar o billing existente
   - **Location**: pode deixar na organização raiz ou criar folder
4. Clicar **Create**
5. Após criado, **selecionar o projeto** como ativo

---

### ETAPA 3: Habilitar APIs

1. Ir em **APIs & Services** → **Library**
2. Buscar e habilitar cada uma:
   - `Cloud Run API` → Enable
   - `Cloud SQL Admin API` → Enable
   - `Vertex AI API` → Enable
   - `Secret Manager API` → Enable
   - `Artifact Registry API` → Enable
3. Para Firebase:
   - Ir em **console.firebase.google.com**
   - Clicar **"Add project"** → selecionar `TMC Producao`
   - Habilitar Firebase Hosting

---

### ETAPA 4: Criar Cloud SQL PostgreSQL

1. Ir em **SQL** no menu lateral
2. Clicar **"Create Instance"**
3. Selecionar **PostgreSQL**
4. Configurar:
   - **Instance ID**: `tmc-db`-ia
   - **Password**: definir senha forte para o usuário `postgres`
   - **Database version**: PostgreSQL 15
   - **Region**: `us-central1 (Iowa)` — região mais barata
   - **Zonal availability**: "Multiple zones (HA)" para produção
5. Em **Machine configuration**:
   - **Machine type**: Shared core (`db-f1-micro` para início, ou `db-custom-2-7680` para produção)
   - **Storage**: 20GB SSD, com auto-increase
6. Em **Backups**:
   - Habilitar automated backups
   - Habilitar point-in-time recovery
7. Clicar **Create Instance** (demora ~5-10 min)
8. Após criado, ir em **Databases** → **Create Database** → nome: `tmc`
9. Ir em **Users** → **Add User Account** → username: `admjaar`, senha segura

---

### ETAPA 5: Configurar Secret Manager

1. Ir em **Security** → **Secret Manager**
2. Clicar **"Create Secret"** para cada um:

| Secret Name | Valor |
|---|---|
| `DATABASE_URL` | `postgresql://admjaar:SENHA@/tmc?host=/cloudsql/PROJECT:REGION:tmc-db` |
| `EXA_API_KEY` | a chave Exa atual |
| `CORS_ALLOWED_ORIGINS` | URLs do frontend |

> As chaves de LLM e embeddings não precisam mais de secret separado — Vertex AI usa as credenciais do GCP automaticamente (service account).

---

### ETAPA 6: Criar Artifact Registry

1. Ir em **Artifact Registry** no menu
2. Clicar **"Create Repository"**
3. Configurar:
   - **Name**: `tmc-ia-docker`
   - **Format**: Docker
   - **Location type**: Region
   - **Region**: `us-central1`
4. Clicar **Create**

---

### ETAPA 7: Vertex AI (Claude + Gemini Embeddings)

**7a. Habilitar Claude:**
1. Ir em **Vertex AI** → **Model Garden**
2. Buscar **"Claude"**
3. Clicar no modelo → **aceitar termos** da Anthropic → **Enable**
4. Verificar que está habilitado

**Modelos Claude disponíveis no Vertex AI:**

| Modelo | ID | Recomendação |
|---|---|---|
| Claude Opus 4.6 | `claude-opus-4-6` | Mais inteligente, mais caro |
| Claude Sonnet 4.5 | `claude-sonnet-4-5@20250929` | **Usar este** (já usamos hoje) |
| Claude Sonnet 4 | `claude-sonnet-4@20250514` | Alternativa mais barata |
| Claude Haiku 4.5 | `claude-haiku-4-5` | Mais rápido e barato |

**7b. Embeddings (já incluído no Vertex AI):**

| Modelo | Dimensões | Uso |
|---|---|---|
| **`gemini-embedding-001`** | até 3072 (configurável) | **Usar este** — #1 no MTEB, multilingual |
| `text-embedding-005` | até 768 | Alternativa (inglês/código) |
| `text-multilingual-embedding-002` | até 768 | Alternativa (multilingual) |

**Sobre o Vertex AI:**
- Claude e embeddings são acessados via API usando credenciais GCP (service account)
- NÃO precisa de API key separada — o service account do Cloud Run já tem acesso
- Billing vai direto na fatura do GCP

**Nota sobre `gemini-embedding-001`:**
- #1 no ranking MTEB Multilingual — superior ao `text-embedding-3-small` da OpenAI
- Suporta Matryoshka (dimensões reduzíveis): 3072 (default), 1536, 768, etc.
- Recomendo usar 768 para economizar storage (suficiente para clustering/similaridade)
- Suporta 100+ idiomas incluindo PT-BR
- **Precisará re-embedar todos os artigos existentes** após migração

---

### ETAPA 8: Firebase Hosting (fazer depois, na hora do deploy do frontend)

1. Ir em **console.firebase.google.com**
2. Selecionar projeto `TMC Producao`
3. Menu lateral → **Hosting** → **Get Started**
4. O deploy em si faz pelo CLI do Firebase na hora de implementar

---

### ETAPA 9: Criar Service Account para o Backend

1. Ir em **IAM & Admin** → **Service Accounts**
2. Clicar **"Create Service Account"**
3. Configurar:
   - **Name**: `tmc-backend`
   - **ID**: `tmc-backend-sa`
   - **Description**: "Service account for TMC backend on Cloud Run"
4. Clicar **Create and Continue**
5. Adicionar roles:
   - `Cloud SQL Client` — acesso ao banco
   - `Secret Manager Secret Accessor` — ler secrets
   - `Vertex AI User` — usar Claude e embeddings
   - `Logging Writer` — escrever logs
   - `Monitoring Metric Writer` — escrever métricas
6. Clicar **Done**

---

## 5. MUDANÇAS DE CÓDIGO NECESSÁRIAS (Após reunião)

### Backend (maior impacto):
1. **Azure Functions → Cloud Run**: Refatorar de function triggers para FastAPI
2. **pymssql → psycopg2**: Trocar driver de banco e ajustar queries T-SQL → PostgreSQL
3. **Azure AI SDK → Vertex AI SDK**: Para Claude e Gemini embeddings
4. **Criar Dockerfile**: Cloud Run roda containers
5. **Config/Environment**: Migrar de `local.settings.json` para Secret Manager + env vars

### Frontend (menor impacto):
1. **Trocar `VITE_API_BASE_URL`**: De Azure Function App URL → Cloud Run URL
2. **Deploy**: De Azure Static Web Apps → Firebase Hosting
3. **CI/CD**: Ajustar GitHub Actions workflow (ou usar Cloud Build)

### Database:
1. **Migrar schema**: SQL Server → PostgreSQL (Google DMS pode ajudar)
2. **Migrar dados**: Export/Import
3. **Re-embedar artigos**: Com `gemini-embedding-001`

---

## 6. IAM — ROLES PARA APÓS O SETUP

Após terminar o setup inicial, pedir ao cliente para reduzir de Owner para roles específicas:

| Role | Para quê |
|---|---|
| `Cloud Run Developer` | Deploy/update backend |
| `Cloud SQL Client` | Conectar ao banco |
| `Secret Manager Admin` | Gerenciar secrets |
| `Logging Viewer` | Ver logs |
| `Monitoring Editor` | Criar alertas |
| `Firebase Hosting Admin` | Deploy frontend |
| `Artifact Registry Writer` | Push Docker images |
| `Vertex AI User` | Usar IA |

---

## 7. CHECKLIST PARA A REUNIÃO

### Antes da reunião:
- [ ] Ter conta Google pronta (email que vai usar)
- [ ] Pedir Organization ID ao cliente
- [ ] Pedir que o admin esteja presente

### Na reunião — fazer junto com cliente:
- [ ] 1. Cliente te adiciona como Owner no IAM
- [ ] 2. Criar projeto `TMC Producao`
- [ ] 3. Vincular billing account ao projeto
- [ ] 4. Habilitar APIs (Cloud Run, Cloud SQL, Vertex AI, Secret Manager, Artifact Registry)
- [ ] 5. Criar instância Cloud SQL PostgreSQL (US Central)
- [ ] 6. Criar database `tmc` e usuário `admjaar`
- [ ] 7. Criar Artifact Registry `tmc-docker`
- [ ] 8. Habilitar Vertex AI + aceitar termos Claude
- [ ] 9. Criar Service Account `tmc-backend-sa` com roles
- [ ] 10. Criar secrets no Secret Manager

### Após a reunião (desenvolvimento):
- [ ] Migrar backend Azure Functions → Cloud Run + FastAPI + Docker
- [ ] Migrar banco SQL Server → PostgreSQL
- [ ] Integrar Vertex AI (Claude + Gemini Embeddings)
- [ ] Re-embedar artigos existentes
- [ ] Ajustar frontend URL e deploy Firebase
- [ ] Configurar CI/CD
- [ ] Testes end-to-end
- [ ] Configurar alertas no Cloud Monitoring

---

## 8. ESTIMATIVA DE CUSTO MENSAL

| Serviço | Custo/mês |
|---|---|
| Cloud Run (backend) | ~$45 |
| Cloud SQL PostgreSQL (HA) | ~$130 |
| Firebase Hosting (frontend) | $0-5 |
| Vertex AI Claude (LLM) | $3-20 (por uso) |
| Vertex AI Gemini Embeddings | $1-5 (por uso) |
| Exa API (fact-check) | $10-50 (externo) |
| Secret Manager | $0 (free tier) |
| Monitoring/Logging | $0 (free tier) |
| Artifact Registry | $0-2 |
| **TOTAL** | **~$200-350/mês** |

---

## 9. ARQUITETURA GCP FINAL

```
┌─────────────────────────────────────────────┐
│       Firebase Hosting (React SPA)          │
│     tmc-producao.web.app                    │
└──────────────┬──────────────────────────────┘
               │ HTTPS
               ▼
┌─────────────────────────────────────────────┐
│   Cloud Run — tmc-backend                   │
│   (FastAPI + Python)                        │
│   Region: us-central1 (Iowa)                │
│                                             │
│   ├─ RSS Collector                          │
│   ├─ Clustering Engine                      │
│   ├─ Article Generation (Vertex AI Claude)  │
│   ├─ Fact-Check (Exa API)                   │
│   ├─ Embeddings (Vertex AI Gemini)          │
│   └─ Health / Monitoring                    │
└──────┬──────────────────┬───────────────────┘
       │                  │
       ▼                  ▼
┌──────────────┐  ┌─────────────────────────────┐
│ Cloud SQL    │  │ Vertex AI                   │
│ PostgreSQL   │  │ ├─ claude-sonnet-4-5        │
│ (HA, Iowa)   │  │ └─ gemini-embedding-001     │
│              │  │                             │
└──────────────┘  └─────────────────────────────┘

Suporte:
├─ Secret Manager (credentials)
├─ Cloud Monitoring (métricas/alertas) — automático
├─ Cloud Logging (logs) — automático
├─ Artifact Registry (Docker images)
└─ GitHub Actions (CI/CD — mantém)
```
