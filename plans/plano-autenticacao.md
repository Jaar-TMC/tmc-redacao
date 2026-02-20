# Plano: Sistema de Autenticacao e Controle de Acesso - TMC Redacao

## Resumo

Implementar sistema completo de autenticacao: backend (JWT, users table, auth middleware) + frontend (login, permissoes, route protection) + onboarding integrado. Sem registro publico — admin cria contas. Sem integracao WordPress — standalone only.

---

## 1. Requisitos

| Funcionalidade | Usuario | Admin |
|----------------|---------|-------|
| Feed de materias | ✓ | ✓ |
| Criar materias | ✓ | ✓ |
| Minhas Materias (scoped por user) | ✓ | ✓ |
| Configuracoes (Buscador, Trends) | ✗ | ✓ |
| Modo Avancado (ver prompts) | ✗ | ✓ |
| Gerenciar usuarios | ✗ | ✓ |
| Onboarding progressivo | ✓ | ✓ |

**Decisoes de design:**
- Nao havera auto-registro. Admins criam contas para usuarios.
- Nao havera integracao com WordPress auth. App funciona standalone.
- Nao havera "Esqueceu a senha?". Admin reseta senhas manualmente.
- Backend construido ANTES do frontend.

---

## 2. Arquitetura de Seguranca

### 2.1 Estrategia de Tokens (JWT)

| Parametro | Valor |
|-----------|-------|
| Tipo | JWT (JSON Web Token) |
| Algoritmo | HS256 |
| Access token TTL | 60 minutos |
| Refresh token TTL | 7 dias (30 dias com "Lembrar de mim") |
| Armazenamento (access) | Memory (variavel JS) |
| Armazenamento (refresh) | `httpOnly` cookie com `SameSite=Lax; Secure` |
| Secret | Env var `JWT_SECRET_KEY` (validado no startup via `config.py`) |

**Estrutura do JWT (payload):**
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "role": "admin",
  "name": "User Name",
  "jti": "random-uuid",
  "iat": 1708387200,
  "exp": 1708390800
}
```

### 2.2 Seguranca de Senhas

- Hashing: **bcrypt** com cost factor 12
- Minimo: 10 caracteres, sem maximo
- Rate limiting no login: max 5 tentativas por email por 15 minutos (reutilizar `RateLimiter` existente)
- Lockout: conta bloqueada por 15 min apos 5 tentativas consecutivas falhadas
- Campos na tabela: `failed_login_attempts`, `locked_until`

### 2.3 CSRF Protection

JWT no header `Authorization: Bearer` (nao em cookie) para requests autenticados = CSRF inherentemente protegido (headers customizados requerem CORS preflight). Refresh token em `httpOnly` cookie com `SameSite=Lax`.

### 2.4 Protecao de Rotas (Backend)

Todos os endpoints protegidos no backend com decorators. Frontend protection e complementar, nao substituto.

**Matriz de autorizacao:**
| Endpoint | Auth Level |
|----------|-----------|
| `GET /api/health` | Publico |
| `GET /api/articles` | Publico (feed de leitura) |
| `GET /api/categories`, `/tags`, `/trending-tags` | Publico |
| `POST /api/generate`, `/extract-topics`, `/generate-tags`, `/merge-topics`, `/edit-article` | Autenticado |
| `GET/POST/PUT/DELETE /api/user-articles` | Autenticado (scoped por user_id) |
| `POST/PUT/DELETE /api/sources/*` | Admin |
| `POST /api/clustering/maintenance` | Admin |
| `GET/POST/PUT/DELETE /api/auth/users` | Admin |

---

## 3. Database Schema

### 3.1 Migration `005_auth_users.sql`

```sql
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'users')
BEGIN
    CREATE TABLE users (
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        name NVARCHAR(255) NOT NULL,
        email NVARCHAR(255) NOT NULL,
        password_hash NVARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'user',
        avatar NVARCHAR(500) NULL,
        is_new_user BIT NOT NULL DEFAULT 1,
        is_active BIT NOT NULL DEFAULT 1,
        last_login DATETIME2 NULL,
        failed_login_attempts INT NOT NULL DEFAULT 0,
        locked_until DATETIME2 NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

        CONSTRAINT UQ_users_email UNIQUE (email),
        CONSTRAINT CK_users_role CHECK (role IN ('admin', 'user'))
    );

    CREATE INDEX IX_users_email ON users (email) WHERE is_active = 1;
    CREATE INDEX IX_users_role ON users (role) WHERE is_active = 1;
END
```

### 3.2 Migration `006_token_blacklist.sql`

```sql
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'token_blacklist')
BEGIN
    CREATE TABLE token_blacklist (
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        token_jti VARCHAR(64) NOT NULL,
        user_id UNIQUEIDENTIFIER NOT NULL,
        expires_at DATETIME2 NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),

        CONSTRAINT FK_token_blacklist_user
            FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE UNIQUE INDEX IX_token_blacklist_jti ON token_blacklist (token_jti);
    CREATE INDEX IX_token_blacklist_expires ON token_blacklist (expires_at);
END
```

### 3.3 Migration `007_user_articles_add_user_id.sql`

```sql
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('user_articles') AND name = 'user_id'
)
BEGIN
    ALTER TABLE user_articles ADD user_id UNIQUEIDENTIFIER NULL;

    CREATE INDEX IX_user_articles_user ON user_articles (user_id);
END
```

### 3.4 Migration `008_auth_audit_log.sql`

```sql
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'auth_audit_log')
BEGIN
    CREATE TABLE auth_audit_log (
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        user_id UNIQUEIDENTIFIER NULL,
        email NVARCHAR(255) NULL,
        action VARCHAR(50) NOT NULL,
        ip_address VARCHAR(45) NULL,
        user_agent NVARCHAR(500) NULL,
        metadata NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );

    CREATE INDEX IX_auth_audit_user ON auth_audit_log (user_id, created_at DESC);
    CREATE INDEX IX_auth_audit_action ON auth_audit_log (action, created_at DESC);
END
```

---

## 4. Backend: Novos Arquivos e Servicos

### 4.1 Pydantic Models — `models/user.py`

```python
class UserLogin(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"  # 'admin' | 'user'

class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None

class User(BaseModel):
    id: str
    name: str
    email: str
    role: str
    avatar: str | None
    is_new_user: bool
    is_active: bool
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime
```

### 4.2 Auth Service — `services/auth_service.py`

Responsabilidades:
- `hash_password(password)` — bcrypt hash
- `verify_password(password, hash)` — bcrypt verify
- `create_access_token(user)` — JWT com exp de 60min
- `create_refresh_token(user)` — JWT com exp de 7/30 dias
- `decode_token(token)` — Validar e decodificar JWT
- `is_token_blacklisted(jti)` — Verificar blacklist
- `blacklist_token(jti, user_id, expires_at)` — Adicionar ao blacklist
- `check_account_lockout(user)` — Verificar se conta esta bloqueada
- `record_login_attempt(user_id, success)` — Atualizar contagem de falhas
- `cleanup_expired_blacklist()` — Limpar tokens expirados

### 4.3 Auth Decorators — `utils/auth.py`

```python
def require_auth(handler):
    """Valida JWT do header Authorization. Injeta req.user."""

def require_admin(handler):
    """Valida JWT + role='admin'. Retorna 403 se nao admin."""
```

Usa o mesmo padrao do `@with_cors` existente. Stackavel:
```python
@app.route(route="sources", methods=["POST", "OPTIONS"])
@with_cors
@require_admin
async def create_source(req): ...
```

### 4.4 Auth API Handlers — `functions/auth_api.py`

Segue o padrao existente de `functions/user_articles_api.py`.

### 4.5 Seed Admin Script — `scripts/seed_admin.py`

Script para criar o primeiro usuario admin. Le `ADMIN_EMAIL` e `ADMIN_PASSWORD` de env vars ou `local.settings.json`.

### 4.6 Config Updates — `services/config.py`

Novos campos no `AppConfig`:
```python
jwt_secret_key: str = ""
jwt_access_token_minutes: int = 60
jwt_refresh_token_days: int = 7
```

Validacao no startup: fail fast se `JWT_SECRET_KEY` vazio em production.

### 4.7 Dependencies — `requirements.txt`

Adicionar:
```
PyJWT>=2.8.0
bcrypt>=4.1.0
```

---

## 5. Backend: API Endpoints

### Auth Core

#### POST /api/auth/login
```javascript
// Request
{ email: string, password: string, remember_me: boolean }

// Response 200
{
  access_token: string,
  expires_in: 3600,
  user: { id, name, email, role, avatar, is_new_user }
}
// Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax; Secure; Path=/api/auth

// Response 401: { error: "Email ou senha incorretos" }
// Response 423: { error: "Conta bloqueada. Tente em X minutos.", locked_until: "..." }
// Response 429: { error: "Muitas tentativas. Aguarde." }
```

#### POST /api/auth/refresh
```javascript
// Cookie: refresh_token=...
// Response 200
{ access_token: string, expires_in: 3600 }

// Response 401: { error: "Refresh token invalido ou expirado" }
```

#### GET /api/auth/me
```javascript
// Headers: Authorization: Bearer {access_token}
// Response 200
{ user: { id, name, email, role, avatar, is_new_user } }
```

#### POST /api/auth/logout
```javascript
// Headers: Authorization: Bearer {access_token}
// Cookie: refresh_token=...
// Response 200: { success: true }
// Server: blacklist o JTI do access token, invalida refresh token
// Set-Cookie: refresh_token=; Max-Age=0
```

#### PATCH /api/auth/me
```javascript
// Headers: Authorization: Bearer {access_token}
// Request: { is_new_user: false }  // Dismiss WelcomeModal
// Response 200: { user: { ... } }
```

### User Management (Admin Only)

#### GET /api/auth/users
```javascript
// Query: ?page=1&limit=20&search=&role=
// Response: { items: [User], total, page, pages }
```

#### POST /api/auth/users
```javascript
// Request: { name, email, password, role }
// Response 201: { user: { ... } }
// Response 409: { error: "Email ja cadastrado" }
```

#### PUT /api/auth/users/{id}
```javascript
// Request: { name?, email?, role?, is_active? }
// Response 200: { user: { ... } }
```

#### DELETE /api/auth/users/{id}
```javascript
// Soft delete (is_active = false)
// Response 200: { success: true }
```

#### POST /api/auth/users/{id}/reset-password
```javascript
// Admin reseta senha de outro usuario
// Request: { new_password: string }
// Response 200: { success: true }
```

---

## 6. Frontend: Componentes a Criar

### 6.1 Contexto de Autenticacao — `src/context/AuthContext.jsx`

```javascript
{
  user: {
    id: string,
    name: string,
    email: string,
    role: 'admin' | 'user',
    avatar: string | null,
    isNewUser: boolean
  } | null,
  isAuthenticated: boolean,
  isLoading: boolean,        // true enquanto verifica token no startup
  error: string | null,

  // Metodos
  login(email, password, rememberMe): Promise<void>,
  logout(): void,
  refreshToken(): Promise<void>,
  dismissWelcome(): Promise<void>,  // PATCH /api/auth/me { is_new_user: false }
}
```

**Notas de implementacao:**
- Access token em memoria (variavel de modulo), NAO em localStorage
- Refresh via `httpOnly` cookie (automatico pelo browser)
- No mount: tenta `POST /api/auth/refresh` silenciosamente
- Se refresh falhar: `isAuthenticated = false`, sem redirect (user vera login)
- `isLoading = true` ate resolver o refresh inicial

### 6.2 Tela de Login

**Layout Desktop:**
```
┌────────────────────────┬────────────────────────┐
│                        │                        │
│    [Logo TMC]          │   Bem-vindo de volta!  │
│                        │   Entre para continuar │
│    Ferramenta de       │                        │
│    Redacao             │   Email*               │
│    Jornalistica        │   ┌──────────────────┐ │
│                        │   │ seu@email.com    │ │
│    ┌──────────────┐    │   └──────────────────┘ │
│    │ [Ilustracao] │    │                        │
│    └──────────────┘    │   Senha*               │
│                        │   ┌──────────────────┐ │
│    "Transforme         │   │ ************ [👁] │ │
│     informacao         │   └──────────────────┘ │
│     em impacto"        │                        │
│                        │   [x] Lembrar de mim   │
│   bg-tmc-dark-green    │                        │
│                        │   ┌──────────────────┐ │
│                        │   │     ENTRAR       │ │
│                        │   └──────────────────┘ │
│                        │                        │
└────────────────────────┴────────────────────────┘
```

**SEM "Esqueceu a senha?" (admin reseta manualmente)**
**SEM "Cadastre-se" (admin cria contas)**

**Layout Mobile (< lg breakpoint):**
- Coluna unica, branding panel oculto
- Logo + tagline acima do form (menor, centralizado)
- Inputs full-width, `min-h-[44px]` para touch targets
- Botao ENTRAR full-width

**Estados de erro na UI:**
| Estado | UI |
|--------|-----|
| Campo vazio | Borda vermelha + mensagem abaixo do campo |
| Credenciais incorretas | Banner vermelho acima do form: "Email ou senha incorretos" |
| Conta bloqueada | Banner amarelo: "Conta bloqueada. Tente em X minutos." |
| Rate limited | Banner amarelo: "Muitas tentativas. Aguarde." |
| Erro de rede | Banner vermelho: "Erro de conexao. Tente novamente." |
| Loading | Botao mostra Spinner + disabled + `aria-busy="true"` |

**Acessibilidade:**
- Erros em `aria-live="polite"` para screen readers
- Todos os inputs com `aria-invalid` quando com erro
- Focus trap no form

**Usar hooks existentes:**
- `useForm` para gerenciamento de estado e validacao do formulario
- `useLocalStorage` para persistir email quando "Lembrar de mim" ativo

### 6.3 Sistema de Permissoes — `src/constants/permissions.js`

```javascript
export const PERMISSIONS = {
  VIEW_FEED: 'view_feed',
  CREATE_ARTICLE: 'create_article',
  VIEW_MY_ARTICLES: 'view_my_articles',
  ACCESS_SETTINGS: 'access_settings',
  VIEW_ADVANCED_MODE: 'view_advanced_mode',
  MANAGE_USERS: 'manage_users',
};

export const ROLE_PERMISSIONS = {
  admin: Object.values(PERMISSIONS),
  user: ['view_feed', 'create_article', 'view_my_articles']
};
```

### 6.4 Hook usePermissions — `src/hooks/usePermissions.js`

```javascript
{
  user,
  role,                    // 'admin' | 'user'
  isAdmin,                 // boolean
  hasPermission(perm),     // (string) => boolean
  canAccessSettings,       // boolean (atalho)
  canViewAdvancedMode,     // boolean (atalho)
  canManageUsers,          // boolean (atalho)
}
```

### 6.5 Componentes de Controle

**ProtectedRoute.jsx:**
```jsx
// Logica:
// if (isLoading) return <AuthLoadingScreen />   ← previne flash do login
// if (!isAuthenticated) return <Navigate to="/login" />
// if (permission && !hasPermission) return <AccessDenied />
// return children

<ProtectedRoute permission="access_settings">
  <ConfiguracoesPage />
</ProtectedRoute>
```

**RequirePermission.jsx:**
```jsx
// Nao renderiza se sem permissao
<RequirePermission permission="view_advanced_mode">
  <button>Modo Avancado</button>
</RequirePermission>
```

**AccessDenied.jsx:**
```
┌─────────────────────────────────┐
│        [ShieldX icon]           │
│                                 │
│      Acesso Restrito            │
│                                 │
│  Voce nao tem permissao para    │
│  acessar esta pagina. Entre em  │
│  contato com o administrador.   │
│                                 │
│  ┌───────────────────────────┐  │
│  │  Voltar para a Redacao    │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

**AuthLoadingScreen:** Usa `<Spinner size="lg" />` existente com branding TMC. Exibido enquanto `isLoading = true` no AuthContext.

### 6.6 WelcomeModal — `src/components/onboarding/WelcomeModal.jsx`

```
┌─────────────────────────────────────┐
│ ┌─────────────────────────────────┐ │
│ │  [Rocket]  Bem-vindo, Joao!     │ │
│ │            TMC Redacao          │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Preparamos um tour guiado para      │
│ voce conhecer a ferramenta.         │
│ Leva apenas 2 minutos!              │
│                                     │
│ ┌───────────┐  ┌─────────────────┐  │
│ │   Pular   │  │  Comecar tour → │  │
│ └───────────┘  └─────────────────┘  │
└─────────────────────────────────────┘
```

**z-index:** 10000 (acima do tour overlay 9998)
**Body scroll:** `overflow: hidden` enquanto visivel

**Ao dispensar (Pular ou Comecar):**
1. Chama `dismissWelcome()` do AuthContext → `PATCH /api/auth/me { is_new_user: false }`
2. Desbloqueia o sistema de onboarding (remove gate)
3. Se "Comecar tour": chama `startTour(TOUR_IDS.HOME)` diretamente

---

## 7. Onboarding: Integracao com Auth

### 7.1 Conflito a Resolver: Double-Prompt

O WelcomeModal (do `isNewUser`) e o HOME tour auto-trigger (do localStorage) disparam simultaneamente para novos usuarios. Solucao:

**Mecanismo de gating no OnboardingProvider:**
- Novo state: `gated: boolean` (default: false)
- Novo metodo: `setGated(boolean)`
- `shouldShowTour()` retorna `false` quando `gated = true`

**WelcomeModal controla o gate:**
- On mount: `setGated(true)` → bloqueia tours
- On dismiss: `setGated(false)` → libera tours

### 7.2 Sequencia de Primeiro Acesso

```
Login (isNewUser: true) → Redirect /
    ↓
WelcomeModal aparece (gate ON, tours bloqueados)
    ↓
  "Pular"          →  gate OFF, tours auto-trigger normalmente
  "Comecar tour"   →  gate OFF, startTour(HOME) imediatamente
    ↓
HOME tour completa → usuario navega normalmente
    ↓
Primeiro acesso /criar → CRIAR tour auto-trigger
    ↓
Primeiro acesso /configuracoes (admin) → CONFIG tour auto-trigger
```

### 7.3 localStorage Scoped por Usuario

Key muda de `tmc-onboarding-v1` para `tmc-onboarding-v1-{userId}`.
OnboardingProvider recebe userId do AuthContext. Ao mudar userId (login/logout), re-le localStorage.

### 7.4 Lifecycle do `isNewUser`

1. Admin cria usuario → `is_new_user = true` no banco
2. Usuario faz login → response inclui `is_new_user: true`
3. WelcomeModal dispensado → `PATCH /api/auth/me { is_new_user: false }`
4. Proximos logins → `is_new_user: false`, sem WelcomeModal
5. Tours governados por localStorage independentemente

### 7.5 Novo Tour: CONFIG (Admin Only)

```javascript
TOUR_IDS.CONFIG = 'config'

tourSteps[CONFIG] = [
  {
    target: '[data-tour="config-sidebar"]',
    title: 'Menu de Configuracoes',
    content: 'Navegue entre as diferentes configuracoes do sistema.',
    position: 'right'
  },
  {
    target: '[data-tour="config-buscador"]',
    title: 'Buscador de Noticias',
    content: 'Configure as fontes de noticias e feeds RSS monitorados.',
    position: 'bottom'
  },
  {
    target: '[data-tour="config-trends"]',
    title: 'Google Trends',
    content: 'Configure os temas para monitoramento de tendencias.',
    position: 'bottom'
  }
]
```

Tour auto-trigger em ConfiguracoesPage apenas para admins (a pagina ja esta protegida por ProtectedRoute).

Help menu no Header: mostrar opcao CONFIG tour apenas quando `isAdmin`.

---

## 8. Modificacoes em Arquivos Existentes

### 8.1 `services/api.js` (CRITICO)

- Injetar `Authorization: Bearer {token}` em `fetchApi()` usando token de modulo
- Exportar `setAuthToken(token)` / `clearAuthToken()` para AuthContext chamar
- Tratar response 401 globalmente: limpar token → redirect `/login`

### 8.2 `App.jsx`

Reestruturar para separar rotas publicas e protegidas:
```jsx
<ErrorBoundary>
  <Router>
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/*" element={<AuthenticatedApp />} />
      </Routes>
    </AuthProvider>
  </Router>
</ErrorBoundary>
```

`AuthenticatedApp` contem toda a chain de providers existente + ProtectedRoute.

**Remover WordPressProvider** (sem integracao WP).

### 8.3 `Header.jsx`

- Trocar `useWordPress()` por `useAuth()` e `usePermissions()`
- Filtrar navItems: esconder "Configuracoes" se `!canAccessSettings`
- Aplicar filtro no mobile menu tambem
- Adicionar botao de logout (desktop: dropdown no avatar, mobile: bottom do menu)
- Help menu: mostrar CONFIG tour apenas quando `isAdmin`

### 8.4 `ConfigurarPage.jsx` (fluxo criacao)

- Esconder botao "Modo Avancado" com `<RequirePermission permission="view_advanced_mode">`

### 8.5 `ConfiguracoesPage.jsx` (pagina settings)

- Adicionar `data-tour="config-sidebar"`, `data-tour="config-buscador"`, `data-tour="config-trends"`
- Adicionar auto-trigger CONFIG tour para admins

### 8.6 `OnboardingProvider.jsx`

- Adicionar mecanismo de `gated` state
- Scoped localStorage key com userId
- Exportar `setGated()` method

### 8.7 `tourSteps.js`

- Adicionar `TOUR_IDS.CONFIG`
- Adicionar steps do CONFIG tour

### 8.8 `context/index.js`

- Exportar `AuthProvider`, `useAuth`
- Remover exports de `WordPressProvider`, `useWordPress`

### 8.9 `hooks/index.js`

- Exportar `usePermissions`

### 8.10 `function_app.py`

- Registrar rotas de auth (`/auth/login`, `/auth/refresh`, `/auth/me`, `/auth/logout`, `/auth/users`)
- Aplicar `@require_auth` e `@require_admin` nos endpoints existentes conforme matriz
- Adicionar rate limit bucket `auth-login` no RateLimiter

### 8.11 `services/database.py`

- Adicionar metodos CRUD para users
- Adicionar metodos para token_blacklist
- Adicionar metodos para auth_audit_log
- Modificar user_articles queries para scoped por `user_id`

### 8.12 `services/config.py`

- Adicionar `jwt_secret_key`, `jwt_access_token_minutes`, `jwt_refresh_token_days`
- Validacao startup: fail fast se `JWT_SECRET_KEY` vazio em production

---

## 9. Estrutura de Arquivos

### Backend (novos)

```
FeedRSS/tmc-rss-collector/
├── migrations/
│   ├── 005_auth_users.sql
│   ├── 006_token_blacklist.sql
│   ├── 007_user_articles_add_user_id.sql
│   └── 008_auth_audit_log.sql
├── models/
│   └── user.py                           # NOVO
├── utils/
│   └── auth.py                           # NOVO (decorators)
├── services/
│   ├── auth_service.py                   # NOVO
│   ├── config.py                         # MODIFICAR
│   ├── database.py                       # MODIFICAR
│   └── rate_limiter.py                   # MODIFICAR
├── functions/
│   └── auth_api.py                       # NOVO
├── scripts/
│   └── seed_admin.py                     # NOVO
├── function_app.py                       # MODIFICAR
└── requirements.txt                      # MODIFICAR
```

### Frontend (novos)

```
tmc-redacao/src/
├── components/
│   ├── auth/                              # NOVO
│   │   ├── index.js
│   │   ├── AuthLayout.jsx
│   │   ├── LoginForm.jsx
│   │   ├── ProtectedRoute.jsx
│   │   ├── RequirePermission.jsx
│   │   ├── AccessDenied.jsx
│   │   └── AuthLoadingScreen.jsx
│   ├── layout/
│   │   └── Header.jsx                    # MODIFICAR
│   └── onboarding/
│       ├── OnboardingProvider.jsx         # MODIFICAR
│       ├── WelcomeModal.jsx              # NOVO
│       └── tourSteps.js                  # MODIFICAR
├── constants/
│   └── permissions.js                    # NOVO
├── context/
│   ├── AuthContext.jsx                   # NOVO
│   └── index.js                          # MODIFICAR
├── hooks/
│   ├── usePermissions.js                 # NOVO
│   └── index.js                          # MODIFICAR
├── pages/
│   ├── auth/
│   │   └── LoginPage.jsx                # NOVO
│   └── ConfiguracoesPage.jsx             # MODIFICAR
├── services/
│   ├── auth.js                           # NOVO
│   └── api.js                            # MODIFICAR
└── App.jsx                               # MODIFICAR
```

---

## 10. Sequencia de Implementacao

### Fase 0: Backend Foundation

| # | Tarefa | Arquivo |
|---|--------|---------|
| 1 | Migration 005 — users table | `migrations/005_auth_users.sql` |
| 2 | Migration 006 — token blacklist | `migrations/006_token_blacklist.sql` |
| 3 | Migration 007 — user_articles add user_id | `migrations/007_user_articles_add_user_id.sql` |
| 4 | Migration 008 — auth audit log | `migrations/008_auth_audit_log.sql` |
| 5 | Pydantic models | `models/user.py` |
| 6 | Auth service (hash, JWT, blacklist) | `services/auth_service.py` |
| 7 | Auth decorators | `utils/auth.py` |
| 8 | Config updates (JWT_SECRET_KEY) | `services/config.py` |
| 9 | requirements.txt (PyJWT, bcrypt) | `requirements.txt` |

### Fase 1: Backend Auth Endpoints

| # | Tarefa | Arquivo |
|---|--------|---------|
| 10 | POST /auth/login (com rate limit) | `functions/auth_api.py` |
| 11 | POST /auth/refresh | `functions/auth_api.py` |
| 12 | GET /auth/me | `functions/auth_api.py` |
| 13 | PATCH /auth/me | `functions/auth_api.py` |
| 14 | POST /auth/logout | `functions/auth_api.py` |
| 15 | Registrar rotas em function_app.py | `function_app.py` |
| 16 | Seed admin script | `scripts/seed_admin.py` |
| 17 | DB methods para users + blacklist | `services/database.py` |

### Fase 2: Backend Protection

| # | Tarefa | Arquivo |
|---|--------|---------|
| 18 | Aplicar @require_auth em endpoints existentes | `function_app.py` |
| 19 | Aplicar @require_admin em sources + clustering | `function_app.py` |
| 20 | Scope user_articles por user_id | `functions/user_articles_api.py` + `services/database.py` |
| 21 | Auth audit logging | `services/database.py` |

### Fase 3: Backend User Management

| # | Tarefa | Arquivo |
|---|--------|---------|
| 22 | GET /auth/users (admin list) | `functions/auth_api.py` |
| 23 | POST /auth/users (admin create) | `functions/auth_api.py` |
| 24 | PUT /auth/users/{id} | `functions/auth_api.py` |
| 25 | DELETE /auth/users/{id} | `functions/auth_api.py` |
| 26 | POST /auth/users/{id}/reset-password | `functions/auth_api.py` |

### Fase 4: Frontend Auth Core

| # | Tarefa | Arquivo |
|---|--------|---------|
| 27 | AuthContext (com refresh silencioso) | `src/context/AuthContext.jsx` |
| 28 | Auth service (API calls) | `src/services/auth.js` |
| 29 | api.js — injetar Bearer + tratar 401 | `src/services/api.js` |
| 30 | Permissions constants | `src/constants/permissions.js` |
| 31 | usePermissions hook | `src/hooks/usePermissions.js` |

### Fase 5: Frontend Auth UI

| # | Tarefa | Arquivo |
|---|--------|---------|
| 32 | AuthLayout (split layout desktop/mobile) | `src/components/auth/AuthLayout.jsx` |
| 33 | LoginForm (usar useForm existente) | `src/components/auth/LoginForm.jsx` |
| 34 | LoginPage | `src/pages/auth/LoginPage.jsx` |
| 35 | ProtectedRoute (com AuthLoadingScreen) | `src/components/auth/ProtectedRoute.jsx` |
| 36 | RequirePermission | `src/components/auth/RequirePermission.jsx` |
| 37 | AccessDenied | `src/components/auth/AccessDenied.jsx` |
| 38 | AuthLoadingScreen | `src/components/auth/AuthLoadingScreen.jsx` |

### Fase 6: Frontend Integracao

| # | Tarefa | Arquivo |
|---|--------|---------|
| 39 | Reestruturar App.jsx (remover WP, add auth) | `src/App.jsx` |
| 40 | Header.jsx — filtrar nav + logout + mobile | `src/components/layout/Header.jsx` |
| 41 | ConfigurarPage — RequirePermission Modo Avancado | `src/pages/criar/ConfigurarPage.jsx` |
| 42 | Barrel exports (context/index, hooks/index) | `src/context/index.js`, `src/hooks/index.js` |

### Fase 7: Onboarding

| # | Tarefa | Arquivo |
|---|--------|---------|
| 43 | OnboardingProvider — gating + userId scope | `src/components/onboarding/OnboardingProvider.jsx` |
| 44 | tourSteps.js — add CONFIG tour | `src/components/onboarding/tourSteps.js` |
| 45 | WelcomeModal | `src/components/onboarding/WelcomeModal.jsx` |
| 46 | ConfiguracoesPage — data-tour attrs + auto-trigger | `src/pages/ConfiguracoesPage.jsx` |

---

## 11. Verificacao

### Backend Tests
- [ ] Login com credenciais corretas retorna JWT + user
- [ ] Login com credenciais incorretas retorna 401
- [ ] Login com conta bloqueada retorna 423
- [ ] Rate limit funciona (5 tentativas/15min)
- [ ] GET /auth/me com token valido retorna user
- [ ] GET /auth/me com token expirado retorna 401
- [ ] POST /auth/refresh com refresh token valido retorna novo access token
- [ ] POST /auth/logout blacklista o token
- [ ] @require_auth bloqueia requests sem token
- [ ] @require_admin bloqueia usuarios normais
- [ ] user_articles scoped por user_id
- [ ] Admin CRUD de usuarios funciona
- [ ] Seed admin script cria primeiro admin

### Frontend Tests
- [ ] Tela de login aparece para nao autenticados
- [ ] Validacao de campos (vazio, formato email)
- [ ] Erros inline e banner para cada tipo de erro
- [ ] Loading state no botao durante login
- [ ] Sucesso redireciona para /
- [ ] AuthLoadingScreen durante verificacao de token (sem flash)
- [ ] "Lembrar de mim" controla persistencia
- [ ] Logout limpa token e redireciona para /login

### Permissoes
- [ ] Usuario NAO ve "Configuracoes" no menu (desktop E mobile)
- [ ] Usuario NAO ve "Modo Avancado"
- [ ] /configuracoes mostra AccessDenied para usuario
- [ ] Admin ve tudo
- [ ] Admin pode gerenciar usuarios

### Onboarding
- [ ] isNewUser: WelcomeModal aparece SEM tour simultaneo
- [ ] "Comecar tour" inicia HOME tour apos fechar modal
- [ ] "Pular" fecha modal, tours disparam normalmente por pagina
- [ ] isNewUser vira false no server apos dispensar modal
- [ ] Tours nao repetem apos completado
- [ ] CONFIG tour aparece para admins em /configuracoes
- [ ] Help menu mostra CONFIG tour apenas para admins

---

## 12. Arquivos Criticos (Resumo)

| # | Arquivo | Acao | Fase |
|---|---------|------|------|
| 1 | `migrations/005-008` | Criar (4 arquivos) | 0 |
| 2 | `models/user.py` | Criar | 0 |
| 3 | `services/auth_service.py` | Criar | 0 |
| 4 | `utils/auth.py` | Criar | 0 |
| 5 | `services/config.py` | Modificar | 0 |
| 6 | `requirements.txt` | Modificar | 0 |
| 7 | `functions/auth_api.py` | Criar | 1-3 |
| 8 | `function_app.py` | Modificar | 1-2 |
| 9 | `services/database.py` | Modificar | 1-2 |
| 10 | `scripts/seed_admin.py` | Criar | 1 |
| 11 | `src/context/AuthContext.jsx` | Criar | 4 |
| 12 | `src/services/auth.js` | Criar | 4 |
| 13 | `src/services/api.js` | Modificar | 4 |
| 14 | `src/constants/permissions.js` | Criar | 4 |
| 15 | `src/hooks/usePermissions.js` | Criar | 4 |
| 16 | `src/components/auth/*` | Criar (7 arquivos) | 5 |
| 17 | `src/pages/auth/LoginPage.jsx` | Criar | 5 |
| 18 | `src/App.jsx` | Modificar | 6 |
| 19 | `src/components/layout/Header.jsx` | Modificar | 6 |
| 20 | `src/pages/criar/ConfigurarPage.jsx` | Modificar | 6 |
| 21 | `src/components/onboarding/*` | Criar/Modificar | 7 |
| 22 | `src/pages/ConfiguracoesPage.jsx` | Modificar | 7 |
