# Plano UI/UX: Gerenciar Usuarios (Admin Only)

## Analise

### Entendimento
Tela de gerenciamento de usuarios dentro de Configuracoes, acessivel apenas por admins.
Backend ja existe com endpoints completos. Falta apenas o frontend.

### Localizacao
- Nova rota: `/configuracoes/usuarios`
- Novo item no sidebar de Configuracoes (visivel apenas para admins)
- Icone: `Users` (lucide-react)

### API Endpoints (ja existentes)
- `GET /api/auth/users?page=1&limit=20&search=&role=` → `{items, total, page, pages}`
- `POST /api/auth/users` → body: `{name, email, password, role}`
- `PUT /api/auth/users/{id}` → body: `{name, email, role, is_active}`
- `DELETE /api/auth/users/{id}` → desativa usuario
- `POST /api/auth/users/{id}/reset-password` → body: `{password}`

### User Format (frontend)
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "role": "admin|user",
  "avatar": "string|null",
  "isNewUser": true,
  "isActive": true,
  "lastLogin": "ISO datetime|null",
  "createdAt": "ISO datetime",
  "updatedAt": "ISO datetime"
}
```

---

## Especificacao Visual

### Layout Desktop
```
┌─────────────────────────────────────────────────────┐
│ Gerenciar Usuarios                [+ Novo Usuario]  │
├─────────────────────────────────────────────────────┤
│ [🔍 Buscar por nome ou email...] [Filtro: Todos ▼] │
├─────────────────────────────────────────────────────┤
│ Nome          │ Email        │ Papel  │ Status │ Acoes│
│───────────────┼──────────────┼────────┼────────┼──────│
│ Administrador │ admin@tmc... │ Admin  │ Ativo  │ ⚙ ▼ │
│ Joao Silva    │ joao@tmc...  │ User   │ Ativo  │ ⚙ ▼ │
│ Maria Santos  │ maria@tmc... │ User   │ Inativo│ ⚙ ▼ │
├─────────────────────────────────────────────────────┤
│ Mostrando 1-3 de 3          [< 1 >]                │
└─────────────────────────────────────────────────────┘
```

### Modal: Criar/Editar Usuario
```
┌─────────────────────────────────────┐
│ Novo Usuario               [X]     │
├─────────────────────────────────────┤
│ Nome *                              │
│ [____________________________]      │
│                                     │
│ Email *                             │
│ [____________________________]      │
│                                     │
│ Senha * (apenas criacao)            │
│ [____________________________]      │
│                                     │
│ Papel *                             │
│ [Redator ▼]                         │
│                                     │
├─────────────────────────────────────┤
│           [Cancelar]  [Salvar]      │
└─────────────────────────────────────┘
```

### Menu de Acoes (dropdown por usuario)
```
┌──────────────────┐
│ ✏️ Editar         │
│ 🔑 Resetar Senha  │
│ ───────────────  │
│ 🚫 Desativar     │
└──────────────────┘
```

---

## Implementacao

### Arquivos a criar/editar

1. **CRIAR** `tmc-redacao/src/pages/config/UsuariosPage.jsx` - Pagina principal
2. **CRIAR** `tmc-redacao/src/services/userApi.js` - API calls para usuarios
3. **EDITAR** `tmc-redacao/src/pages/ConfiguracoesPage.jsx` - Adicionar item "Usuarios" (admin only)
4. **EDITAR** `tmc-redacao/src/App.jsx` - Adicionar rota `/configuracoes/usuarios`

### Componentes a usar (ja existentes)
- `ConfirmDialog` - Confirmacao de desativacao
- `StatusMessage` - Feedback de sucesso/erro
- `Skeleton` - Loading state
- `EmptyState` - Estado vazio
- `Spinner` - Loading inline

### Permissao
- Sidebar item visivel apenas se `usePermissions().canManageUsers`
- Rota protegida com `<ProtectedRoute permission="manage_users">`
- `PERMISSIONS.MANAGE_USERS` ja existe, so admins tem
