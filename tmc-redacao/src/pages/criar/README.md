# Etapa 1 - Seleção de Fonte

## Visão Geral

Esta é a implementação completa da **Etapa 1** do novo fluxo de criação de matéria, conforme especificado em `Planning/UI-UX-REWORK-CRIAR-MATERIA.md`.

## Estrutura de Arquivos

```
src/
├── pages/
│   └── criar/
│       ├── index.jsx          # Página principal (Etapa 1)
│       └── README.md           # Esta documentação
│
└── components/
    └── criar/
        ├── SourceCard.jsx      # Card de seleção de fonte
        ├── UrlInputModal.jsx   # Modal para YouTube e Link da Web
        ├── TemaSelector.jsx    # Seletor inline de temas
        ├── FeedSelector.jsx    # Seletor inline de matérias
        └── index.js            # Barrel exports
```

## Componentes Implementados

### 1. SourceCard
Card de seleção de fonte com estados visuais:
- Default: borda light-gray, fundo white
- Hover: borda tmc-orange, shadow-md, scale 1.02
- Selected: borda tmc-orange 2px, fundo orange-50

**Props:**
- `icon` (string): Emoji do ícone
- `title` (string): Título do card
- `description` (string): Descrição curta
- `selected` (boolean): Estado selecionado
- `disabled` (boolean): Estado desabilitado
- `onClick` (function): Handler de clique

### 2. UrlInputModal
Modal para input de URL (YouTube ou Link da Web) com:
- Input de URL com botão de colar
- Validação básica de URL
- Preview após validação
- Estados de loading e erro

**Props:**
- `isOpen` (boolean): Controla visibilidade
- `onClose` (function): Handler de fechar
- `type` ('youtube' | 'web'): Tipo de URL
- `onSubmit` (function): Handler de submit

### 3. TemaSelector
Seletor inline de temas em alta com:
- Abas: Feed em Alta, Google Trends, Twitter
- Busca de temas
- Seleção única de tema
- Dados do mockData.js

**Props:**
- `onClose` (function): Handler de fechar
- `onSelect` (function): Handler de seleção

### 4. FeedSelector
Seletor inline de matérias do feed com:
- Busca de matérias
- Filtros por categoria e data
- Seleção múltipla com checkbox
- Dados do mockData.js

**Props:**
- `onClose` (function): Handler de fechar
- `onSelect` (function): Handler de seleção

## Fluxo de Interação

### Transcrição de Vídeo
1. Usuário clica no card "Transcrição de Vídeo"
2. Abre modal de URL (tipo: youtube)
3. Usuário cola URL e clica em "Validar URL"
4. Mostra preview do vídeo
5. Clica em "Transcrever"
6. **TODO**: Navegar para `/criar/texto-base` com dados

### Tema em Alta
1. Usuário clica no card "Tema em Alta"
2. Expande seletor inline com abas
3. Usuário busca e seleciona um tema
4. Clica em "Continuar com tema"
5. **TODO**: Navegar para `/criar/texto-base` com dados

### Matérias do Feed
1. Usuário clica no card "Matérias do Feed"
2. Expande seletor inline com filtros
3. Usuário seleciona uma ou mais matérias
4. Clica em "Continuar com seleção"
5. **TODO**: Navegar para `/criar/texto-base` com dados

### Link da Web
1. Usuário clica no card "Link da Web"
2. Abre modal de URL (tipo: web)
3. Usuário cola URL e clica em "Validar URL"
4. Mostra preview da página
5. Clica em "Extrair Conteúdo"
6. **TODO**: Navegar para `/criar/texto-base` com dados

## Rotas Configuradas

- `/criar` - Etapa 1: Seleção de Fonte (implementada)
- `/criar/texto-base` - Etapa 2: Texto-Base (placeholder)
- `/criar/configurar` - Etapa 3: Configurações (placeholder)
- `/criar/editor` - Etapa 4: Editor (já existente)

## Stepper

O stepper mostra visualmente as 4 etapas:
1. **Fonte** (atual) - Círculo preenchido laranja
2. **Texto-Base** (pendente) - Círculo vazio
3. **Configurar** (pendente) - Círculo vazio
4. **Editor** (pendente) - Círculo vazio

## Responsividade

- **Desktop (>768px)**: Grid 2x2 de cards
- **Mobile (<768px)**: Grid 1 coluna

## Acessibilidade

- Navegação por teclado completa
- ARIA labels apropriados
- Contraste WCAG 2.1 AA
- Focus indicators visíveis

## Próximos Passos

1. **Integração com Backend**
   - Implementar validação real de URLs
   - Buscar preview de vídeos/páginas via API
   - Transcrição de vídeos
   - Extração de conteúdo web

2. **Navegação entre Etapas**
   - Passar dados selecionados via `state` do React Router
   - Implementar Etapa 2 (Texto-Base)
   - Implementar Etapa 3 (Configurações)

3. **Melhorias de UX**
   - Adicionar loading states mais detalhados
   - Implementar error boundaries
   - Adicionar animações de transição

## Uso

```jsx
import CriarMateria from './pages/criar';

// No App.jsx ou router
<Route path="/criar" element={<CriarMateria />} />
```

## Testes

Para testar localmente:

1. Acesse `/criar` na aplicação
2. Teste cada fonte:
   - Clique em "Transcrição de Vídeo" e teste o modal
   - Clique em "Tema em Alta" e teste o seletor
   - Clique em "Matérias do Feed" e teste a seleção múltipla
   - Clique em "Link da Web" e teste o modal web

## Dependências

- React Router (navegação)
- Tailwind CSS (estilos)
- lucide-react (ícones)
- PropTypes (validação de props)

## Observações

- Os alerts são temporários para demonstração
- Em produção, devem ser substituídos por navegação real
- A validação de URL é básica e deve ser melhorada
- Os previews são mockados e devem buscar dados reais
