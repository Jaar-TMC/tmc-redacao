# Bugs - Página de Transcrição

> **Data:** 15/12/2025
> **Status:** ✅ CORRIGIDOS
> **Reportado por:** Usuário
> **Data Correção:** 16/12/2025

---

## Resumo

| Prioridade | Total de Bugs | Corrigidos |
|------------|---------------|------------|
| Alta | 2 | 2 ✅ |
| Média | 1 | 1 ✅ |
| **Total** | **3** | **3** ✅ |

---

## Alta Prioridade

### BUG-001: Header com etapas escondido atrás do menu do app ✅ CORRIGIDO
- **Página:** `/transcricao`
- **Componente:** `TranscricaoPage.jsx`
- **Problema:** O header que mostra as etapas (1 - Adicionar Vídeo, 2 - Transcrevendo, 3 - Selecionar Trechos) está sendo renderizado embaixo do menu principal do app, ficando invisível/inacessível.
- **Causa Provável:** Conflito de `z-index` ou falta de `top` offset no header sticky da página de transcrição. O Header principal do app tem `z-index` maior ou o header da transcrição não considera a altura do Header principal.
- **Impacto:** Usuário não consegue visualizar em qual etapa do fluxo está.
- **Solução:** Adicionado `top-16` ao header sticky e `pt-16` ao container principal.

**Checklist:**
- [x] Identificar altura do Header principal (64px = top-16)
- [x] Ajustar `top` do header sticky da transcrição para compensar altura do Header
- [x] Verificar `z-index` para garantir visibilidade correta
- [x] Testar em diferentes tamanhos de tela

---

### BUG-002: Navegação bloqueada na página de transcrição ✅ CORRIGIDO
- **Página:** `/transcricao`
- **Componente:** `TranscricaoPage.jsx` / Router
- **Problema:** Quando o usuário está na página de transcrição:
  - Clicar no menu "Redação" não navega de volta
  - Clicar no botão "Criar do Zero" não funciona
  - Nenhum link de navegação funciona
  - Só consegue continuar se seguir o fluxo de transcrição (colocar vídeo do YouTube)
- **Causa Real:** Loop infinito de re-renders causado por `useEffect` com dependências instáveis (`selection` e `resetSteps` que são objetos recriados a cada render). Erro no console: "Maximum update depth exceeded".
- **Impacto:** Crítico - Usuário fica "preso" na página de transcrição.
- **Solução:**
  1. Removido o `useEffect` de "Reset ao mudar URL" que tinha dependências instáveis
  2. Atualizado o `useEffect` de keyboard shortcuts para ignorar elementos `a`, `button` e `[role="button"]`

**Checklist:**
- [x] Debugar por que cliques no Header/menu não funcionam (loop infinito)
- [x] Verificar se `e.preventDefault()` ou `e.stopPropagation()` estão sendo chamados incorretamente
- [x] Remover useEffect problemático que causava loop infinito
- [x] Corrigir a causa raiz (dependências instáveis no useEffect)
- [x] Testar navegação em todas as etapas

---

## Média Prioridade

### BUG-003: ConfigPanel inconsistente com página de criação de matéria ✅ CORRIGIDO
- **Página:** `/transcricao` (Etapa 3)
- **Componente:** `src/pages/transcricao/components/ConfigPanel.jsx`
- **Problema:** O painel de configuração (Tom da Matéria, Persona do Redator, Tipo de Matéria, etc.) na página de transcrição tem visual/estilo diferente do painel equivalente na página de criação de matéria com base em artigos selecionados.
- **Impacto:** Inconsistência visual na aplicação, quebra o design system.
- **Solução:** Redesenhado o ConfigPanel para usar cards clicáveis com bordas coloridas ao invés de selects, mantendo consistência com outras páginas. Adicionado campo de Keywords SEO.

**Checklist:**
- [x] Identificar componente de referência (design correto)
- [x] Listar diferenças visuais entre os dois
- [x] Padronizar estilos do ConfigPanel da transcrição
- [x] Testar consistência visual

---

## Arquivos a Investigar

| Arquivo | Bugs Relacionados |
|---------|-------------------|
| `src/pages/transcricao/TranscricaoPage.jsx` | BUG-001, BUG-002 |
| `src/pages/transcricao/components/ConfigPanel.jsx` | BUG-003 |
| `src/components/layout/Header.jsx` | BUG-001, BUG-002 |
| `src/pages/CriarPostPage.jsx` | BUG-003 (referência) |
| `src/pages/CriarInspiracaoPage.jsx` | BUG-003 (referência) |

---

## Próximos Passos

1. **BUG-002** deve ser investigado primeiro pois bloqueia uso da aplicação
2. **BUG-001** deve ser corrigido em seguida para restaurar visibilidade das etapas
3. **BUG-003** pode ser tratado após os bugs críticos

---

## Validação ✅ COMPLETA

Após correções:
- [x] Testar navegação completa (entrar e sair da página de transcrição)
- [x] Testar visibilidade do header de etapas em todas as resoluções
- [x] Comparar visualmente ConfigPanel com outras páginas
- [x] Testar fluxo completo de transcrição

### Testes Realizados (16/12/2025):
1. ✅ Página de transcrição carrega sem erros no console
2. ✅ Step indicator (etapas 1-2-3) visível acima do conteúdo
3. ✅ Click no menu "Redação" navega corretamente
4. ✅ Click no dropdown "Criar" abre o menu
5. ✅ Click em "Do Zero" navega para a página de criação
6. ✅ ConfigPanel redesenhado com cards clicáveis
