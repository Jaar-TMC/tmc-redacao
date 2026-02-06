# Plano: Sistema de Autenticacao e Controle de Acesso - TMC Redacao

## Resumo

Implementar tela de login (sem registro - admin cria contas), sistema de controle de acesso com 2 niveis (usuario/admin), e integrar com onboarding existente.

---

## 1. Requisitos

| Funcionalidade | Usuario | Admin |
|----------------|---------|-------|
| Feed de materias | ✓ | ✓ |
| Criar materias | ✓ | ✓ |
| Minhas Materias | ✓ | ✓ |
| Configuracoes (Buscador, Trends) | ✗ | ✓ |
| Modo Avancado (ver prompts) | ✗ | ✓ |
| **Criar contas de usuarios** | ✗ | ✓ |
| Onboarding progressivo | ✓ | ✓ |

**Importante:** Nao havera auto-registro. Admins criam contas para usuarios.

---

## 2. Sistema de Onboarding (JA EXISTE)

O onboarding ja esta implementado em `src/components/onboarding/`:

```
OnboardingProvider.jsx  - Gerencia estado dos tours
tourSteps.js           - 3 tours: HOME, CRIAR, EDITOR
useOnboarding.js       - Hook para acessar contexto
OnboardingTour.jsx     - Renderiza o tour visual
OnboardingStep.jsx     - Componente de cada step
OnboardingBeacon.jsx   - Indicador visual
OnboardingOverlay.jsx  - Overlay escuro
```

**Funcionalidades existentes:**
- `shouldShowTour(tourId)` - Verifica se deve mostrar (primeira vez)
- `startTour(tourId)` - Inicia um tour
- `skipTour()` / `completeTour()` - Finaliza tour
- Persistencia em localStorage (`tmc-onboarding-v1`)
- Auto-trigger em RedacaoPage e CriarPage

**O que precisamos fazer:**
- Integrar com AuthContext para detectar `isNewUser`
- Adicionar WelcomeModal para primeiro acesso
- Adicionar tour CONFIG para admins

---

## 3. Fluxo de Autenticacao

```
Usuario acessa app
        │
        ▼
┌───────────────────┐
│  AuthProvider     │
│  verifica token   │
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
 Token       Sem token
 valido
    │           │
    ▼           ▼
 Carregar    Redirecionar
 usuario     para /login
    │
    ▼
 Dashboard
 (RedacaoPage)
    │
    ▼
 Se isNewUser:
 WelcomeModal → Tour HOME
```

---

## 4. Componentes a Criar

### 4.1 Contexto de Autenticacao

**Arquivo:** `src/context/AuthContext.jsx`
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
  isLoading: boolean,
  error: string | null,

  // Metodos
  login(email, password): Promise<void>,
  logout(): void,
  checkAuthStatus(): Promise<void>
}
```

### 4.2 Tela de Login (SEM registro)

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
│                        │   Esqueceu a senha?    │
│                        │                        │
└────────────────────────┴────────────────────────┘
```

**Nota:** Sem link "Cadastre-se" - apenas login.

### 4.3 Sistema de Permissoes

**Arquivo:** `src/constants/permissions.js`
```javascript
export const PERMISSIONS = {
  VIEW_FEED: 'view_feed',
  CREATE_ARTICLE: 'create_article',
  ACCESS_SETTINGS: 'access_settings',      // Admin only
  VIEW_ADVANCED_MODE: 'view_advanced_mode', // Admin only
  MANAGE_USERS: 'manage_users',            // Admin only
};

export const ROLE_PERMISSIONS = {
  admin: Object.values(PERMISSIONS),
  user: ['view_feed', 'create_article', 'view_my_articles']
};
```

### 4.4 Hook usePermissions

**Arquivo:** `src/hooks/usePermissions.js`
```javascript
// Retorna
{
  user,
  role,                    // 'admin' | 'user'
  isAdmin,                 // boolean
  hasPermission(perm),     // (string) => boolean
  canAccessSettings,       // boolean (atalho)
  canViewAdvancedMode,     // boolean (atalho)
}
```

### 4.5 Componentes de Controle

**ProtectedRoute.jsx** - Protege rotas
```jsx
// Redireciona para /login se nao autenticado
// Mostra AccessDenied se sem permissao
<ProtectedRoute permission="access_settings">
  <ConfiguracoesPage />
</ProtectedRoute>
```

**RequirePermission.jsx** - Esconde elementos
```jsx
// Nao renderiza se sem permissao
<RequirePermission permission="view_advanced_mode">
  <button>Modo Avancado</button>
</RequirePermission>
```

### 4.6 WelcomeModal (novo)

**Arquivo:** `src/components/onboarding/WelcomeModal.jsx`

Exibido apenas para usuarios com `isNewUser: true` no primeiro acesso:

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

---

## 5. Modificacoes em Arquivos Existentes

### 5.1 Header.jsx
- Filtrar menu baseado em permissoes
- Esconder "Configuracoes" para usuarios

### 5.2 ConfigurarPage.jsx
- Esconder botao "Modo Avancado" para usuarios
- Usar `<RequirePermission>`

### 5.3 App.jsx
- Adicionar `AuthProvider`
- Adicionar rota `/login`
- Proteger rotas com `ProtectedRoute`

### 5.4 OnboardingProvider.jsx (pequena modificacao)
- Receber `isNewUser` do AuthContext
- Integrar WelcomeModal trigger

---

## 6. Estrutura de Arquivos

```
src/
├── components/
│   ├── auth/                       # NOVO
│   │   ├── index.js
│   │   ├── AuthLayout.jsx
│   │   ├── LoginForm.jsx
│   │   ├── AuthInput.jsx
│   │   ├── ProtectedRoute.jsx
│   │   ├── RequirePermission.jsx
│   │   └── AccessDenied.jsx
│   ├── layout/
│   │   └── Header.jsx              # MODIFICAR
│   └── onboarding/
│       ├── OnboardingProvider.jsx  # MODIFICAR (integrar Auth)
│       ├── WelcomeModal.jsx        # NOVO
│       └── tourSteps.js            # MODIFICAR (add CONFIG)
├── constants/
│   └── permissions.js              # NOVO
├── context/
│   └── AuthContext.jsx             # NOVO
├── hooks/
│   └── usePermissions.js           # NOVO
├── pages/
│   └── auth/
│       └── LoginPage.jsx           # NOVO
├── services/
│   └── auth.js                     # NOVO
└── App.jsx                         # MODIFICAR
```

---

## 7. Sequencia de Implementacao

### Fase 1: Autenticacao (Alta prioridade)
1. `src/context/AuthContext.jsx`
2. `src/services/auth.js`
3. `src/constants/permissions.js`
4. `src/hooks/usePermissions.js`

### Fase 2: Componentes Auth
5. `src/components/auth/AuthInput.jsx`
6. `src/components/auth/AuthLayout.jsx`
7. `src/components/auth/LoginForm.jsx`
8. `src/pages/auth/LoginPage.jsx`
9. `src/components/auth/ProtectedRoute.jsx`
10. `src/components/auth/RequirePermission.jsx`
11. `src/components/auth/AccessDenied.jsx`

### Fase 3: Integracao
12. Modificar `App.jsx` - AuthProvider + rotas
13. Modificar `Header.jsx` - filtrar menu
14. Modificar `ConfigurarPage.jsx` - esconder Modo Avancado

### Fase 4: Onboarding
15. Criar `WelcomeModal.jsx`
16. Modificar `OnboardingProvider.jsx` - integrar Auth
17. Modificar `tourSteps.js` - adicionar CONFIG

---

## 8. API Backend (Endpoints)

### POST /api/auth/login
```javascript
// Request
{ email: string, password: string }

// Response
{
  token: string,
  user: { id, name, email, role, avatar, isNewUser }
}
```

### GET /api/auth/me
```javascript
// Headers: Authorization: Bearer {token}
// Response: { user: { ... } }
```

### POST /api/auth/logout
```javascript
// Response: { success: true }
```

---

## 9. Verificacao

### Testes
1. **Login**
   - [ ] Tela de login aparece para nao autenticados
   - [ ] Validacao de campos
   - [ ] Erro com credenciais incorretas
   - [ ] Sucesso redireciona para /

2. **Usuario (role: user)**
   - [ ] NAO ve "Configuracoes" no menu
   - [ ] NAO ve "Modo Avancado"
   - [ ] /configuracoes mostra AccessDenied

3. **Admin (role: admin)**
   - [ ] Ve "Configuracoes" no menu
   - [ ] Ve "Modo Avancado"
   - [ ] Acessa /configuracoes

4. **Onboarding**
   - [ ] isNewUser: WelcomeModal aparece
   - [ ] Tours funcionam normalmente
   - [ ] Nao repete apos completado

---

## 10. Arquivos Criticos

| # | Arquivo | Acao |
|---|---------|------|
| 1 | `src/context/AuthContext.jsx` | Criar |
| 2 | `src/services/auth.js` | Criar |
| 3 | `src/constants/permissions.js` | Criar |
| 4 | `src/hooks/usePermissions.js` | Criar |
| 5 | `src/components/auth/*` | Criar (7 arquivos) |
| 6 | `src/pages/auth/LoginPage.jsx` | Criar |
| 7 | `src/App.jsx` | Modificar |
| 8 | `src/components/layout/Header.jsx` | Modificar |
| 9 | `src/pages/criar/ConfigurarPage.jsx` | Modificar |
| 10 | `src/components/onboarding/WelcomeModal.jsx` | Criar |
| 11 | `src/components/onboarding/OnboardingProvider.jsx` | Modificar |
