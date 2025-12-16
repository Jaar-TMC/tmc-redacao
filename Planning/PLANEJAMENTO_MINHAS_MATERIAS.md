# Planejamento UI/UX - Página "Minhas Matérias"
## Portal TMC - Sistema de Redação

---

## 1. Visão Geral da Página

### 1.1 Propósito
A página "Minhas Matérias" é o painel pessoal do redator onde ele pode visualizar, gerenciar e editar todas as suas matérias criadas na ferramenta, sejam elas publicadas ou ainda em rascunho.

### 1.2 Público-Alvo
- Redatores do portal TMC
- Editores que precisam revisar suas próprias matérias
- Usuários que precisam acompanhar o status de suas publicações

### 1.3 Objetivos de UX
- **Eficiência**: Permitir acesso rápido às matérias através de filtros poderosos
- **Clareza**: Visualização clara do status de cada matéria (Publicada/Rascunho)
- **Controle**: Facilitar ações de edição, visualização e exclusão
- **Organização**: Estrutura lógica que reflita o fluxo de trabalho do redator

### 1.4 Métricas de Sucesso
- Tempo para encontrar uma matéria específica < 10 segundos
- Taxa de uso dos filtros > 60%
- Satisfação do usuário (NPS) > 8/10
- Acessibilidade WCAG 2.1 Nível AA

---

## 2. Estrutura e Layout

### 2.1 Wireframe ASCII - Desktop (1440px+)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ HEADER (bg: #1A4D2E - 64px height)                                          │
│  [Logo TMC]  [Redação] [Minhas Matérias*] [Configurações]    [Criar] [👤]  │
└──────────────────────────────────────────────────────────────────────────────┘
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ BREADCRUMB (16px top margin)                                       │    │
│  │ Início > Minhas Matérias                                           │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ PAGE HEADER (32px padding)                                         │    │
│  │  ┌──────────────────────────────────────────────┬────────────────┐ │    │
│  │  │ H1: Minhas Matérias                          │  [+ Nova Matéria]│ │    │
│  │  │ 24 matérias encontradas                      │                │ │    │
│  │  └──────────────────────────────────────────────┴────────────────┘ │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ FILTER BAR (24px padding, border-radius: 12px)                    │    │
│  │ ┌──────────────────────────────────────────────────────────────┐  │    │
│  │ │ [🔍] Buscar por título, conteúdo ou tags...                  │  │    │
│  │ └──────────────────────────────────────────────────────────────┘  │    │
│  │                                                                    │    │
│  │ [Status ▼] [Tema ▼] [Data ▼] [Redator ▼]     [Limpar Filtros]   │    │
│  │                                                                    │    │
│  │ Active Filters: [×Rascunho] [×Política] [×Últimos 7 dias]        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ TABS (Optional view mode)                                          │    │
│  │  [📋 Lista] [📱 Cards]                                            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ CONTENT AREA - GRID VIEW (gap: 24px)                              │    │
│  │                                                                    │    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                │    │
│  │  │ ARTICLE CARD        │  │ ARTICLE CARD        │                │    │
│  │  │ [RASCUNHO Badge]    │  │ [PUBLICADA Badge]   │                │    │
│  │  │ ───────────────     │  │ ───────────────     │                │    │
│  │  │ Título da Matéria   │  │ Título da Matéria   │                │    │
│  │  │ Preview do texto... │  │ Preview do texto... │                │    │
│  │  │                     │  │                     │                │    │
│  │  │ 📅 12/12/2024       │  │ 📅 10/12/2024       │                │    │
│  │  │ 🏷️ Política         │  │ 🏷️ Economia        │                │    │
│  │  │                     │  │                     │                │    │
│  │  │ [👁️ Ver] [✏️ Editar] │  │ [👁️ Ver] [✏️ Editar] │                │    │
│  │  │ [🗑️ Excluir]        │  │ [📊 Métricas]      │                │    │
│  │  └─────────────────────┘  └─────────────────────┘                │    │
│  │                                                                    │    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐                │    │
│  │  │ ARTICLE CARD        │  │ ARTICLE CARD        │                │    │
│  │  │ ...                 │  │ ...                 │                │    │
│  │  └─────────────────────┘  └─────────────────────┘                │    │
│  │                                                                    │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ PAGINATION                                                         │    │
│  │  [◀ Anterior] [1] [2] [3] ... [10] [Próximo ▶]                   │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Wireframe ASCII - Mobile (< 768px)

```
┌─────────────────────────────┐
│ HEADER (56px)               │
│ [☰] TMC      [+ Criar] [👤] │
├─────────────────────────────┤
│                             │
│ Minhas Matérias             │
│ 24 encontradas              │
│                             │
│ ┌─────────────────────────┐ │
│ │ [🔍] Buscar...          │ │
│ └─────────────────────────┘ │
│                             │
│ [Filtros ▼]  [Ordenar ▼]   │
│                             │
│ ┌─────────────────────────┐ │
│ │ ■ RASCUNHO              │ │
│ │ Título da Matéria       │ │
│ │ Preview breve...        │ │
│ │ 📅 12/12 | 🏷️ Política  │ │
│ │ [Ver] [Editar] [•••]    │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ ● PUBLICADA             │ │
│ │ Outra Matéria           │ │
│ │ Preview...              │ │
│ │ 📅 10/12 | 🏷️ Economia  │ │
│ │ [Ver] [Editar] [•••]    │ │
│ └─────────────────────────┘ │
│                             │
│ [Carregar mais...]          │
│                             │
└─────────────────────────────┘
```

### 2.3 Grid System

#### Desktop (1440px+)
- Container: `max-width: 1440px`, `padding: 0 48px`
- Columns: 2 colunas de cards (grid-template-columns: repeat(2, 1fr))
- Gap: 24px horizontal e vertical
- Breakpoint para 3 colunas em telas XL (1920px+)

#### Tablet (768px - 1023px)
- Container: `padding: 0 32px`
- Columns: 2 colunas
- Gap: 16px

#### Mobile (< 768px)
- Container: `padding: 0 16px`
- Columns: 1 coluna (stack vertical)
- Gap: 16px

---

## 3. Componentes de UI - Especificações Detalhadas

### 3.1 Page Header

#### Estrutura
```
┌────────────────────────────────────────────────┐
│  H1: Minhas Matérias           [+ Nova Matéria]│
│  Subtitle: 24 matérias encontradas             │
└────────────────────────────────────────────────┘
```

#### Especificações
- **Background**: `#FFFFFF`
- **Border**: `1px solid #E0E0E0`
- **Border-radius**: `12px`
- **Padding**: `32px`
- **Margin-bottom**: `24px`

**Título (H1)**
- Font: Arial/Helvetica, Bold
- Size: `28px` (desktop), `24px` (mobile)
- Color: `#333333`
- Line-height: `1.2`
- Margin-bottom: `8px`

**Subtitle**
- Font: Arial/Helvetica, Regular
- Size: `14px`
- Color: `#666666`
- Line-height: `1.5`

**Botão "Nova Matéria"**
- Background: `#E87722` (TMC Orange)
- Color: `#FFFFFF`
- Padding: `12px 24px`
- Border-radius: `8px`
- Font-size: `14px`, Font-weight: `600`
- Icon: PenLine (18px)
- Hover: `background: #D66A1E` (darken 5%)
- Focus: `outline: 2px solid #E87722`, `outline-offset: 2px`

### 3.2 Filter Bar Component

#### Estrutura Visual
```
┌──────────────────────────────────────────────────────┐
│ FILTER BAR                                           │
│ ┌──────────────────────────────────────────────────┐ │
│ │ [🔍] Buscar por título, conteúdo ou tags...      │ │
│ └──────────────────────────────────────────────────┘ │
│                                                      │
│ ┌─────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐ │
│ │Status ▼ │ │Tema ▼  │ │Data ▼  │ │Limpar Filtros│ │
│ └─────────┘ └────────┘ └────────┘ └──────────────┘ │
│                                                      │
│ Filtros ativos: [×Rascunho] [×Política]            │
└──────────────────────────────────────────────────────┘
```

#### Especificações do Container
- **Background**: `#FFFFFF`
- **Border**: `1px solid #E0E0E0`
- **Border-radius**: `12px`
- **Padding**: `24px`
- **Margin-bottom**: `24px`
- **Box-shadow**: `0 1px 3px rgba(0,0,0,0.05)`

#### Search Input
- **Width**: `100%` (full-width)
- **Height**: `44px`
- **Padding**: `12px 16px 12px 44px` (espaço para ícone)
- **Border**: `1px solid #E0E0E0`
- **Border-radius**: `8px`
- **Font-size**: `14px`
- **Color**: `#333333`
- **Placeholder color**: `#999999`
- **Icon**: Search (20px), positioned absolute left 12px
- **Focus state**:
  - Border: `1px solid #E87722`
  - Box-shadow: `0 0 0 3px rgba(232, 119, 34, 0.1)`

#### Filter Buttons (Dropdowns)

**Estado Normal**
- Background: Transparent
- Border: `1px solid #E0E0E0`
- Color: `#333333`
- Padding: `10px 16px`
- Border-radius: `8px`
- Font-size: `14px`, Font-weight: `500`
- Icon: ChevronDown (16px), color `#666666`
- Gap entre texto e ícone: `8px`

**Estado Hover**
- Background: `#F5F5F5`
- Border: `1px solid #E0E0E0`

**Estado Active (filtro aplicado)**
- Background: `#E87722`
- Border: `1px solid #E87722`
- Color: `#FFFFFF`
- Icon color: `#FFFFFF`

**Estado Focus**
- Outline: `2px solid #E87722`
- Outline-offset: `2px`

#### Dropdown Menu

**Container**
- Background: `#FFFFFF`
- Border: `1px solid #E0E0E0`
- Border-radius: `8px`
- Box-shadow: `0 4px 12px rgba(0,0,0,0.1)`
- Padding: `8px 0`
- Min-width: `200px`
- Position: `absolute`, `top: calc(100% + 8px)`
- Z-index: `50`

**Menu Items**
- Padding: `10px 16px`
- Font-size: `14px`
- Color: `#333333`
- Hover background: `#F5F5F5`
- Active item: Color `#E87722`, Font-weight `600`

**Divider**
- Height: `1px`
- Background: `#E0E0E0`
- Margin: `8px 0`

#### Active Filters Pills

**Pill Container**
- Display: `flex`, `flex-wrap: wrap`
- Gap: `8px`
- Margin-top: `16px`
- Padding-top: `16px`
- Border-top: `1px solid #E0E0E0`

**Individual Pill**
- Background: `#FFF5EE` (TMC Orange tint 5%)
- Border: `1px solid #E87722`
- Border-radius: `16px`
- Padding: `6px 12px 6px 16px`
- Font-size: `13px`
- Color: `#E87722`
- Display: `inline-flex`
- Align-items: `center`
- Gap: `8px`

**Close Icon (×)**
- Size: `16px`
- Color: `#E87722`
- Cursor: `pointer`
- Hover: Color `#D66A1E`, Background `rgba(232, 119, 34, 0.1)`, Border-radius `50%`

**Clear All Button**
- Background: Transparent
- Border: None
- Color: `#666666`
- Font-size: `13px`
- Text-decoration: `underline`
- Cursor: `pointer`
- Hover: Color `#E87722`

### 3.3 Article Card Component

#### Card Container
```
┌─────────────────────────────────────────┐
│ [BADGE]                     [Status •]  │
│                                         │
│ Título da Matéria Aqui                 │
│ ────────────────────────────           │
│                                         │
│ Preview do conteúdo da matéria que     │
│ será exibido em até 2 linhas...        │
│                                         │
│ 📅 12/12/2024  🏷️ Política             │
│ ✍️ João Silva  👁️ 1.2k visualizações   │
│                                         │
│ ┌──────┐ ┌────────┐ ┌────────────────┐ │
│ │ Ver  │ │ Editar │ │ Outras ações ▼ │ │
│ └──────┘ └────────┘ └────────────────┘ │
└─────────────────────────────────────────┘
```

#### Especificações do Container
- **Background**: `#FFFFFF`
- **Border**: `1px solid #E0E0E0`
- **Border-radius**: `12px`
- **Padding**: `24px`
- **Transition**: `all 0.2s ease`
- **Cursor**: `default`

**Hover State**
- Border: `1px solid #E87722`
- Box-shadow: `0 4px 12px rgba(232, 119, 34, 0.15)`
- Transform: `translateY(-2px)`

**Focus State** (quando card é focável via keyboard)
- Outline: `2px solid #E87722`
- Outline-offset: `2px`

#### Status Badge (Top Right)

**Badge Rascunho**
- Background: `#FFF5EE` (Orange tint)
- Border: `1px solid #E87722`
- Color: `#E87722`
- Padding: `6px 12px`
- Border-radius: `6px`
- Font-size: `12px`
- Font-weight: `600`
- Text-transform: `uppercase`
- Letter-spacing: `0.5px`
- Display: `inline-flex`
- Align-items: `center`
- Gap: `6px`
- Icon: FileEdit (14px)

**Badge Publicada**
- Background: `#E8F5E9` (Green tint)
- Border: `1px solid #10B981`
- Color: `#10B981`
- Icon: CheckCircle (14px)
- (Outras propriedades idênticas ao Rascunho)

#### Title
- Font: Arial/Helvetica, Bold
- Size: `18px` (desktop), `16px` (mobile)
- Color: `#333333`
- Line-height: `1.3`
- Margin-bottom: `12px`
- Max-lines: `2` (line-clamp)
- Overflow: `ellipsis`

**Hover State**
- Color: `#E87722`
- Cursor: `pointer`

#### Preview Text
- Font: Arial/Helvetica, Regular
- Size: `14px`
- Color: `#666666`
- Line-height: `1.5`
- Margin-bottom: `16px`
- Max-lines: `2` (line-clamp)
- Overflow: `ellipsis`

#### Metadata Row

**Container**
- Display: `flex`
- Flex-wrap: `wrap`
- Gap: `16px`
- Margin-bottom: `16px`
- Padding-bottom: `16px`
- Border-bottom: `1px solid #E0E0E0`
- Font-size: `13px`
- Color: `#666666`

**Metadata Item**
- Display: `inline-flex`
- Align-items: `center`
- Gap: `6px`

**Icons**
- Size: `16px`
- Color: `#999999`
- Aria-hidden: `true`

**Data/Hora**
- Icon: Calendar
- Format: `DD/MM/YYYY` ou `HH:MM - DD/MM` (se hoje)

**Tema/Categoria**
- Icon: Tag
- Color do texto: Cor da categoria (ex: Política = `#3B82F6`)
- Font-weight: `500`

**Redator**
- Icon: User
- Exibe apenas se filtro de redator não estiver ativo

**Visualizações** (apenas para Publicadas)
- Icon: Eye
- Format: `1.2k`, `340`, etc.

#### Action Buttons Row

**Container**
- Display: `flex`
- Gap: `8px`
- Margin-top: `16px`

**Button Base Style**
- Height: `36px`
- Padding: `0 16px`
- Border-radius: `6px`
- Font-size: `13px`
- Font-weight: `500`
- Display: `inline-flex`
- Align-items: `center`
- Gap: `6px`
- Transition: `all 0.15s ease`
- Cursor: `pointer`

**Primary Button (Ver, Editar)**
- Background: `#E87722`
- Color: `#FFFFFF`
- Border: None
- Hover: Background `#D66A1E`
- Focus: Outline `2px solid #E87722`, Outline-offset `2px`

**Secondary Button (Excluir - apenas Rascunho)**
- Background: `#FFFFFF`
- Color: `#E53935` (Live Red)
- Border: `1px solid #E53935`
- Hover: Background `#FFF5F5`, Border `1px solid #C62828`
- Focus: Outline `2px solid #E53935`, Outline-offset `2px`

**Tertiary Button (Mais ações ▼)**
- Background: `#F5F5F5`
- Color: `#666666`
- Border: `1px solid #E0E0E0`
- Hover: Background `#E0E0E0`
- Focus: Outline `2px solid #E87722`, Outline-offset `2px`

**Button Icons**
- Size: `16px`
- Vertical-align: `middle`

#### Category Color System

Cores para badges de categoria (mesma do ArticleCard existente):

```javascript
{
  'Política': '#3B82F6',      // Blue
  'Economia': '#10B981',      // Emerald/Green
  'Esportes': '#E87722',      // TMC Orange
  'Tecnologia': '#8B5CF6',    // Purple
  'Entretenimento': '#EC4899', // Pink
  'Saúde': '#E53935',         // Red
  'Ciência': '#06B6D4',       // Cyan
  'Educação': '#F59E0B'       // Yellow
}
```

### 3.4 Empty State Component

Quando não há matérias ou nenhum resultado é encontrado.

#### Estrutura
```
┌────────────────────────────────────┐
│                                    │
│            [📄 Icon]               │
│                                    │
│     Nenhuma matéria encontrada     │
│                                    │
│  Você ainda não criou nenhuma      │
│  matéria ou os filtros aplicados   │
│  não retornaram resultados.        │
│                                    │
│       [+ Criar Matéria]            │
│       [Limpar Filtros]             │
│                                    │
└────────────────────────────────────┘
```

#### Especificações
- **Container padding**: `64px 32px`
- **Text-align**: `center`
- **Max-width**: `480px`
- **Margin**: `0 auto`

**Icon**
- Size: `64px`
- Color: `#E0E0E0`
- Margin-bottom: `24px`

**Title**
- Font-size: `20px`
- Font-weight: `600`
- Color: `#333333`
- Margin-bottom: `12px`

**Description**
- Font-size: `14px`
- Color: `#666666`
- Line-height: `1.5`
- Margin-bottom: `32px`

**Buttons**
- Seguem especificação dos botões primário e secundário

### 3.5 Pagination Component

#### Estrutura
```
┌────────────────────────────────────────────────────┐
│  [◀ Anterior]  [1] [2] [3] ... [10]  [Próximo ▶]  │
│                                                    │
│  Mostrando 1-20 de 234 matérias                   │
└────────────────────────────────────────────────────┘
```

#### Especificações

**Container**
- Display: `flex`
- Justify-content: `center`
- Align-items: `center`
- Gap: `8px`
- Padding: `32px 0`
- Flex-direction: `column` (mobile), `row` (desktop)

**Page Number Button**
- Width: `40px`
- Height: `40px`
- Border-radius: `8px`
- Font-size: `14px`
- Font-weight: `500`
- Background: `#FFFFFF`
- Border: `1px solid #E0E0E0`
- Color: `#666666`
- Cursor: `pointer`

**Active Page**
- Background: `#E87722`
- Border: `1px solid #E87722`
- Color: `#FFFFFF`
- Font-weight: `600`

**Hover State**
- Background: `#F5F5F5`
- Border: `1px solid #E87722`

**Previous/Next Buttons**
- Padding: `10px 16px`
- Border-radius: `8px`
- Font-size: `14px`
- Font-weight: `500`
- Background: `#FFFFFF`
- Border: `1px solid #E0E0E0`
- Color: `#666666`
- Display: `inline-flex`
- Align-items: `center`
- Gap: `8px`

**Disabled State**
- Opacity: `0.5`
- Cursor: `not-allowed`
- Pointer-events: `none`

**Info Text**
- Font-size: `13px`
- Color: `#666666`
- Margin-top: `12px`

---

## 4. Sistema de Filtros - Funcionamento e Interação

### 4.1 Filtros Disponíveis

#### 1. Busca por Texto (Search)
**Comportamento:**
- Busca em tempo real (debounce de 300ms)
- Campos pesquisados: título, preview/conteúdo, tags
- Case-insensitive
- Suporta múltiplas palavras (AND lógico)
- Destaca resultados encontrados (opcional)

**UX:**
- Ícone de lupa à esquerda
- Placeholder: "Buscar por título, conteúdo ou tags..."
- Clear button (×) aparece quando há texto
- Loading indicator durante busca
- Exibe "X resultados encontrados" abaixo do input

#### 2. Status
**Opções:**
- Todos (padrão)
- Rascunho
- Publicada

**Comportamento:**
- Seleção única (radio)
- Aplica filtro imediatamente ao selecionar
- Badge visual quando filtro ativo

#### 3. Tema/Categoria
**Opções:**
- Todos (padrão)
- Política
- Economia
- Esportes
- Tecnologia
- Entretenimento
- Saúde
- Ciência
- Educação

**Comportamento:**
- Seleção única
- Mostra contador de matérias por tema
- Dropdown com scroll se necessário
- Badge colorido quando ativo (cor da categoria)

#### 4. Data
**Opções:**
- Últimas 24 horas
- Últimos 7 dias
- Últimos 30 dias
- Últimos 3 meses
- Este ano
- Personalizado (date range picker)

**Comportamento:**
- Seleção única
- "Personalizado" abre date picker
- Date picker com calendário visual
- Range selection (de - até)

#### 5. Redator
**Opções:**
- Todos
- Lista de redatores (do mais recente ao mais antigo)

**Comportamento:**
- Seleção única
- Mostra avatar + nome
- Busca interna no dropdown
- Sticky "Meus artigos" no topo

### 4.2 Lógica de Combinação

**Operadores:**
- Entre diferentes filtros: **AND** (todos devem ser satisfeitos)
- Busca por texto: **OR** entre palavras-chave

**Exemplo:**
```
Status: Rascunho
Tema: Política
Data: Últimos 7 dias
Busca: "eleições"

Resultado: Matérias que são Rascunho AND Política AND criadas nos últimos 7 dias AND contém "eleições"
```

### 4.3 Estados do Sistema de Filtros

#### Estado Inicial (Sem Filtros)
- Exibe todas as matérias do redator
- Ordenação padrão: Mais recentes primeiro
- Todos os dropdowns no estado neutro

#### Estado com Filtros Ativos
- Dropdowns ativos mudam para TMC Orange
- Pills exibem filtros aplicados
- Contador atualiza ("X matérias encontradas")
- Botão "Limpar Filtros" fica visível

#### Estado de Loading
- Skeleton loading nos cards
- Filtros permanecem interativos
- Spinner sutil no canto superior direito

#### Estado Vazio (Sem Resultados)
- Empty state exibe mensagem contextual
- Sugere remover filtros
- Oferece botão "Limpar Filtros"

### 4.4 Persistência de Filtros

**LocalStorage:**
- Salva última configuração de filtros
- Restaura ao retornar à página
- Expira após 7 dias
- Key: `tmc_minhas_materias_filters`

**URL Parameters:**
- Reflete filtros ativos na URL
- Permite compartilhar links filtrados
- Formato: `?status=rascunho&tema=politica&data=7d`

### 4.5 Interações do Dropdown

**Abrir:**
- Click no botão
- Enter ou Space quando focado
- Seta para baixo quando focado

**Navegar:**
- Setas ↑↓ para mover entre opções
- Home/End para primeira/última opção
- Type-ahead: digitar letra seleciona próximo item com essa inicial

**Selecionar:**
- Click na opção
- Enter quando opção focada
- Fecha dropdown automaticamente

**Fechar:**
- Click fora do dropdown
- Esc key
- Selecionar uma opção
- Click no mesmo botão novamente

---

## 5. Estados dos Cards/Itens

### 5.1 Card States

#### Default (Repouso)
- Border: `1px solid #E0E0E0`
- Background: `#FFFFFF`
- Shadow: None
- Transform: None

#### Hover
- Border: `1px solid #E87722`
- Background: `#FFFFFF`
- Shadow: `0 4px 12px rgba(232, 119, 34, 0.15)`
- Transform: `translateY(-2px)`
- Transition: `all 0.2s ease`
- Cursor: `default`

#### Focus (Keyboard Navigation)
- Outline: `2px solid #E87722`
- Outline-offset: `2px`
- Z-index: `10` (para sobrepor cards adjacentes)

#### Active (Sendo clicado)
- Transform: `translateY(0)`
- Shadow: `0 2px 6px rgba(232, 119, 34, 0.1)`

#### Loading
- Opacity: `0.6`
- Pointer-events: `none`
- Cursor: `wait`
- Skeleton animation nos textos

### 5.2 Button States (dentro dos cards)

#### Ver (Primary)

**Default**
- Background: `#E87722`
- Color: `#FFFFFF`
- Border: None

**Hover**
- Background: `#D66A1E`
- Transform: `scale(1.02)`

**Focus**
- Outline: `2px solid #E87722`
- Outline-offset: `2px`

**Active**
- Background: `#C25E1A`
- Transform: `scale(0.98)`

**Disabled**
- Background: `#E0E0E0`
- Color: `#999999`
- Cursor: `not-allowed`
- Opacity: `0.6`

#### Editar (Primary)

Segue mesmas especificações do botão "Ver"

#### Excluir (Danger/Secondary)

**Default**
- Background: `#FFFFFF`
- Color: `#E53935`
- Border: `1px solid #E53935`

**Hover**
- Background: `#FFF5F5`
- Border: `1px solid #C62828`
- Color: `#C62828`

**Focus**
- Outline: `2px solid #E53935`
- Outline-offset: `2px`

**Active**
- Background: `#FFEBEE`
- Border: `1px solid #B71C1C`

#### Menu Dropdown (•••)

**Default**
- Background: `#F5F5F5`
- Color: `#666666`
- Border: `1px solid #E0E0E0`

**Hover**
- Background: `#E0E0E0`
- Border: `1px solid #D0D0D0`

**Open (Dropdown ativo)**
- Background: `#E0E0E0`
- Color: `#333333`
- Border: `1px solid #E87722`

### 5.3 Badge States

#### Rascunho Badge

**Default**
- Background: `#FFF5EE`
- Border: `1px solid #E87722`
- Color: `#E87722`

**Animação (opcional para "mudou recentemente")**
- Pulse animation suave
- Duração: 2s
- Iteration: infinite

#### Publicada Badge

**Default**
- Background: `#E8F5E9`
- Border: `1px solid #10B981`
- Color: `#10B981`

**Com indicador "Novo"** (publicado nas últimas 24h)
- Adiciona dot verde `#10B981` pulsando
- Size: 6px
- Position: Top-right do badge

---

## 6. Indicadores de Status (Badges)

### 6.1 Badge: Rascunho

#### Especificações Completas
```css
.badge-rascunho {
  background: #FFF5EE; /* TMC Orange tint 5% */
  border: 1px solid #E87722;
  color: #E87722;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  position: absolute;
  top: 16px;
  right: 16px;
}
```

**Icon:** FileEdit (Lucide React) - 14px
**Label:** "RASCUNHO"

**Acessibilidade:**
- aria-label="Status: Rascunho"
- role="status"

### 6.2 Badge: Publicada

#### Especificações Completas
```css
.badge-publicada {
  background: #E8F5E9; /* Success green tint */
  border: 1px solid #10B981;
  color: #10B981;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  position: absolute;
  top: 16px;
  right: 16px;
}
```

**Icon:** CheckCircle (Lucide React) - 14px
**Label:** "PUBLICADA"

**Acessibilidade:**
- aria-label="Status: Publicada"
- role="status"

### 6.3 Badge: Em Revisão (Estado futuro)

Preparado para expansão futura do sistema.

```css
.badge-em-revisao {
  background: #FFF8E6; /* Warning yellow tint */
  border: 1px solid #F59E0B;
  color: #F59E0B;
  /* ... outras propriedades iguais */
}
```

**Icon:** Clock (Lucide React) - 14px
**Label:** "EM REVISÃO"

### 6.4 Badges de Categoria (Tags)

Pequenas tags coloridas para categorias.

#### Especificações
```css
.category-tag {
  background: transparent;
  border: 1px solid currentColor;
  color: var(--category-color);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
```

**Cores por categoria:**
- Política: `#3B82F6`
- Economia: `#10B981`
- Esportes: `#E87722`
- Tecnologia: `#8B5CF6`
- Entretenimento: `#EC4899`
- Saúde: `#E53935`
- Ciência: `#06B6D4`
- Educação: `#F59E0B`

### 6.5 Badge: Novo (Indicador temporal)

Para matérias publicadas/editadas nas últimas 24h.

```css
.badge-novo {
  background: #E53935;
  color: #FFFFFF;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-left: 8px;
}
```

**Label:** "NOVO"
**Posição:** Ao lado do título ou do status badge

---

## 7. Responsividade - Adaptação Mobile/Tablet

### 7.1 Breakpoints

```css
/* Mobile Small */
@media (max-width: 374px) { /* ... */ }

/* Mobile */
@media (max-width: 767px) { /* ... */ }

/* Tablet Portrait */
@media (min-width: 768px) and (max-width: 1023px) { /* ... */ }

/* Tablet Landscape / Desktop Small */
@media (min-width: 1024px) and (max-width: 1439px) { /* ... */ }

/* Desktop */
@media (min-width: 1440px) { /* ... */ }

/* Desktop XL */
@media (min-width: 1920px) { /* ... */ }
```

### 7.2 Mobile (< 768px)

#### Layout Changes

**Header**
- Height: `56px` (reduzido de 64px)
- Hamburger menu no lugar de nav items
- "Nova Matéria" button só com ícone

**Page Header**
- Padding: `16px` (reduzido de 32px)
- Title font-size: `24px` (reduzido de 28px)
- Subtitle font-size: `13px`
- "Nova Matéria" button: Full width, position bottom

**Filter Bar**
- Stack vertical
- Search input: Full width
- Filtros: Collapse em 1 botão "Filtros" que abre modal
- Active filters pills: Horizontal scroll

**Cards Grid**
- 1 coluna (stack vertical)
- Gap: `16px`
- Padding: `16px`

**Article Card**
- Padding: `16px` (reduzido de 24px)
- Title font-size: `16px` (reduzido de 18px)
- Preview: 2 linhas max (igual)
- Metadata: Stack vertical se necessário
- Buttons: Stack vertical, full width

**Pagination**
- Mostra apenas 3 números de página
- "..." para indicar mais páginas
- Previous/Next com ícone apenas (sem texto)

#### Mobile Filter Modal

Quando o botão "Filtros" é clicado, abre modal fullscreen:

```
┌─────────────────────────────┐
│ ← Filtros           [Aplicar]│
├─────────────────────────────┤
│                             │
│ Buscar                      │
│ ┌─────────────────────────┐ │
│ │ [🔍] Buscar...          │ │
│ └─────────────────────────┘ │
│                             │
│ Status                      │
│ ○ Todos                     │
│ ○ Rascunho                  │
│ ○ Publicada                 │
│                             │
│ Tema                        │
│ [Selecionar tema ▼]         │
│                             │
│ Data                        │
│ [Selecionar período ▼]      │
│                             │
│ Redator                     │
│ [Selecionar redator ▼]      │
│                             │
│ ┌─────────────────────────┐ │
│ │    [Limpar Filtros]     │ │
│ │    [Aplicar Filtros]    │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

**Especificações Modal:**
- Background: `#FFFFFF`
- Z-index: `100`
- Animation: Slide up from bottom
- Header: Fixed, `#F5F5F5` background
- Footer: Fixed, `#FFFFFF` background, shadow
- Body: Scrollable

### 7.3 Tablet (768px - 1023px)

#### Layout Changes

**Container**
- Padding: `0 32px`

**Cards Grid**
- 2 colunas (mantém)
- Gap: `16px`

**Filter Bar**
- Mantém layout horizontal
- Reduz padding para `16px`
- Reduz tamanho de fonte para `13px`

**Article Card**
- Padding: `20px`
- Font-sizes ligeiramente reduzidos

**Pagination**
- Mostra até 5 números de página

### 7.4 Desktop XL (1920px+)

#### Layout Changes

**Container**
- Max-width: `1600px`

**Cards Grid**
- 3 colunas (grid-template-columns: repeat(3, 1fr))
- Gap: `24px`

**Filter Bar**
- Mais espaçoso
- Dropdowns maiores

---

## 8. Micro-interações e Feedback Visual

### 8.1 Loading States

#### Skeleton Loading (Cards)

Enquanto matérias carregam:

```css
.skeleton {
  background: linear-gradient(
    90deg,
    #F5F5F5 0%,
    #E0E0E0 50%,
    #F5F5F5 100%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
  border-radius: 4px;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

**Elementos com skeleton:**
- Badge status (rectangle 80x24px)
- Title (rectangle full-width, height 20px)
- Preview (2 rectangles, 100% width, height 14px each)
- Metadata (4 small rectangles, 60px width)
- Buttons (3 rectangles, heights 36px)

#### Spinner (Global Loading)

Para operações que afetam toda a lista:

```html
<div class="spinner-overlay">
  <div class="spinner"></div>
</div>
```

**Especificações:**
- Position: Fixed, center
- Background overlay: `rgba(0,0,0,0.3)`
- Spinner: 40px, TMC Orange
- Animation: Rotate 360deg, 0.8s linear infinite
- Backdrop-filter: `blur(2px)`

### 8.2 Transitions

#### Card Hover Effect

```css
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
```

**Propriedades animadas:**
- transform
- box-shadow
- border-color

#### Button Interactions

```css
transition: all 0.15s ease;
```

**Propriedades animadas:**
- background-color
- color
- transform
- border-color

#### Dropdown Open/Close

```css
/* Opening */
animation: dropdown-open 0.2s ease-out;

@keyframes dropdown-open {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Closing */
animation: dropdown-close 0.15s ease-in;

@keyframes dropdown-close {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-8px);
  }
}
```

### 8.3 Success Feedback

#### Toast Notification

Aparece no top-right após ações bem-sucedidas:

```
┌─────────────────────────────────┐
│ ✓ Matéria excluída com sucesso │
└─────────────────────────────────┘
```

**Especificações:**
- Position: Fixed, `top: 80px`, `right: 24px`
- Background: `#10B981`
- Color: `#FFFFFF`
- Padding: `12px 20px`
- Border-radius: `8px`
- Box-shadow: `0 4px 12px rgba(16, 185, 129, 0.3)`
- Animation: Slide in from right, fade out after 3s
- Z-index: `1000`

**Tipos:**
- Success: Green `#10B981`
- Error: Red `#E53935`
- Warning: Orange `#F59E0B`
- Info: Blue `#3B82F6`

#### Card Action Feedback

**Delete Confirmation:**
- Modal overlay aparece
- Fade in animation
- Backdrop blur

```
┌─────────────────────────────────┐
│         Excluir Matéria?        │
│                                 │
│ Esta ação não pode ser          │
│ desfeita. Tem certeza que       │
│ deseja excluir este rascunho?   │
│                                 │
│  [Cancelar]    [Excluir]        │
└─────────────────────────────────┘
```

**Especificações Modal:**
- Max-width: `400px`
- Background: `#FFFFFF`
- Border-radius: `12px`
- Padding: `32px`
- Box-shadow: `0 20px 40px rgba(0,0,0,0.2)`
- Overlay: `rgba(0,0,0,0.5)`

### 8.4 Empty State Animations

#### Icon Animation

```css
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.empty-state-icon {
  animation: float 3s ease-in-out infinite;
}
```

### 8.5 Filter Pills Animation

#### Add Filter

```css
@keyframes pill-add {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
```

#### Remove Filter

```css
@keyframes pill-remove {
  from {
    opacity: 1;
    transform: scale(1);
  }
  to {
    opacity: 0;
    transform: scale(0.8);
  }
}
```

### 8.6 Scroll Behaviors

#### Smooth Scroll to Top

Botão aparece após scroll > 300px:

```css
.scroll-to-top {
  position: fixed;
  bottom: 32px;
  right: 32px;
  width: 48px;
  height: 48px;
  background: #E87722;
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(232, 119, 34, 0.3);
  transition: all 0.3s ease;
  z-index: 50;
}

.scroll-to-top:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(232, 119, 34, 0.4);
}
```

**Icon:** ArrowUp (Lucide) - 24px
**Behavior:** Smooth scroll com `behavior: 'smooth'`

#### Infinite Scroll (Opcional)

Se optar por infinite scroll ao invés de pagination:

```javascript
// Observer para último card
const observer = new IntersectionObserver(
  (entries) => {
    if (entries[0].isIntersecting) {
      loadMore();
    }
  },
  { threshold: 0.5 }
);
```

**Loading indicator:**
- Spinner no final da lista
- "Carregando mais matérias..."
- Fade in animation

---

## 9. Acessibilidade (WCAG 2.1 Nível AA)

### 9.1 Perceivable (Perceptível)

#### 1.1 Text Alternatives

**Imagens e Ícones:**
- Todos os ícones têm `aria-hidden="true"`
- Texto descritivo sempre acompanha ícones funcionais
- Ícones decorativos são ignorados por screen readers

```html
<!-- Correto -->
<button aria-label="Editar matéria: Título da matéria">
  <PencilIcon aria-hidden="true" />
  <span>Editar</span>
</button>
```

**Favicons de fontes:**
```html
<img src="favicon.png" alt="" aria-hidden="true" />
<span className="sr-only">Fonte: G1</span>
```

#### 1.2 Time-based Media

Não aplicável - não há mídia baseada em tempo nesta página.

#### 1.3 Adaptable

**Semantic HTML:**
```html
<header role="banner">
<nav role="navigation" aria-label="Navegação principal">
<main role="main">
<article> para cada card
<form role="search"> para filtros
```

**Heading Hierarchy:**
```
H1: "Minhas Matérias" (apenas 1 por página)
H2: Subtítulos de seções (se houver)
H3: Títulos dos cards de matérias
```

**ARIA Labels:**
- Todos os controles de filtro têm labels descritivos
- Dropdowns têm `aria-expanded`, `aria-haspopup`
- Cards têm `aria-label` completo
- Form inputs têm labels associados

#### 1.4 Distinguishable

**Contrast Ratios (WCAG AA):**

Textos normais (mínimo 4.5:1):
- `#333333` on `#FFFFFF`: 12.63:1 ✓
- `#666666` on `#FFFFFF`: 5.74:1 ✓
- `#E87722` on `#FFFFFF`: 3.34:1 ✗ (usar apenas para large text)

Textos grandes/Bold (mínimo 3:1):
- `#E87722` on `#FFFFFF`: 3.34:1 ✓
- `#FFFFFF` on `#E87722`: 3.34:1 ✓
- `#FFFFFF` on `#1A4D2E`: 8.59:1 ✓

Componentes de UI (mínimo 3:1):
- Borders `#E0E0E0` on `#FFFFFF`: 1.25:1 ✗
  - **Solução:** Usar `#D0D0D0` (2.1:1) ou `#C0C0C0` (3.1:1)
- Focus outline `#E87722`: 3.34:1 ✓ (quando usado em bg branco)

**Ajustes necessários:**
- Borders: Alterar de `#E0E0E0` para `#CCCCCC` (4.54:1)
- Placeholder text: `#999999` (2.85:1) - OK para placeholder
- Disabled states: Garantir contraste mínimo mesmo em estado desabilitado

**Color Usage:**
- Nunca usar APENAS cor para comunicar informação
- Badges têm ícone + texto + cor
- Links têm underline ou outro indicador visual
- Status é indicado por ícone + cor + texto

**Resize Text (200%):**
- Layout responsivo suporta zoom até 200%
- Sem quebras de layout
- Todos os textos permanecem legíveis
- Sem overlapping de elementos

**Reflow:**
- Layout adapta para 320px de largura
- Sem scroll horizontal
- Mobile-first approach

### 9.2 Operable (Operável)

#### 2.1 Keyboard Accessible

**Keyboard Navigation:**

Ordem de tabulação lógica:
1. Skip to main content link (oculto visualmente)
2. Logo
3. Nav items
4. Create button
5. User menu
6. Search input
7. Filter dropdowns (esquerda → direita)
8. Active filter pills (com botão × focável)
9. Cards (ordem: top → bottom, left → right)
10. Buttons dentro dos cards
11. Pagination

**Keyboard Shortcuts:**

| Tecla | Ação |
|-------|------|
| Tab | Próximo elemento focável |
| Shift+Tab | Elemento focável anterior |
| Enter | Ativar botão/link, abrir dropdown |
| Space | Ativar botão, selecionar checkbox |
| Esc | Fechar dropdown/modal |
| ↑↓ | Navegar em dropdown aberto |
| Home/End | Primeira/última opção em dropdown |

**Focus Management:**
- Ao abrir modal: Focus vai para primeiro elemento interativo
- Ao fechar modal: Focus retorna para elemento que abriu
- Ao remover filter pill: Focus vai para próximo pill ou botão "Filtros"
- Trap focus dentro de modais

**No Keyboard Trap:**
- Todos os modals podem ser fechados com Esc
- Dropdowns podem ser fechados com Esc
- Focus nunca fica preso em nenhum componente

#### 2.2 Enough Time

**Timing Adjustable:**
- Não há timeouts na aplicação
- Search debounce é transparente ao usuário
- Não há sessões que expiram
- Usuário controla ritmo de interação

**Pause, Stop, Hide:**
- Se implementar auto-refresh: Botão de pause visível
- Animações respeitam `prefers-reduced-motion`
- Skeleton animations podem ser pausadas

#### 2.3 Seizures and Physical Reactions

**Three Flashes:**
- Nenhum conteúdo pisca mais de 3 vezes por segundo
- Animações suaves, sem flashes
- Pulse animations são sutis (opacity 0.8 → 1.0)

#### 2.4 Navigable

**Bypass Blocks:**
```html
<a href="#main-content" class="skip-link">
  Pular para conteúdo principal
</a>
```

Estilo do skip-link:
```css
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: #E87722;
  color: #FFFFFF;
  padding: 8px 16px;
  text-decoration: none;
  z-index: 100;
}

.skip-link:focus {
  top: 0;
}
```

**Page Titled:**
```html
<title>Minhas Matérias - TMC Redação</title>
```

**Focus Order:**
- Segue ordem visual (left to right, top to bottom)
- Nenhum tabindex positivo
- Apenas tabindex="0" ou "-1" quando necessário

**Link Purpose:**
- Todos os links têm texto descritivo
- "Ler mais" → "Ler matéria completa: [Título]"
- "Editar" → "Editar matéria: [Título]"
- Contexto sempre fornecido via aria-label

**Multiple Ways:**
- Busca por texto
- Filtros por categoria/status/data
- Breadcrumb navigation
- Direct URL access

**Headings and Labels:**
- Heading hierarchy lógica
- Labels descritivos para todos os inputs
- Fieldsets para grupos relacionados

**Focus Visible:**
```css
*:focus-visible {
  outline: 2px solid #E87722;
  outline-offset: 2px;
}
```

### 9.3 Understandable (Compreensível)

#### 3.1 Readable

**Language:**
```html
<html lang="pt-BR">
```

**Unusual Words:**
- Termos técnicos são explicados em tooltips
- Abreviações expandidas em aria-label

#### 3.2 Predictable

**On Focus:**
- Nenhum elemento muda contexto apenas ao receber focus
- Dropdowns só abrem com click/Enter

**On Input:**
- Formulários não são submetidos automaticamente
- Mudanças de filtro são explícitas
- Loading states indicam processamento

**Consistent Navigation:**
- Header idêntico em todas as páginas
- Filtros seguem mesmo padrão da página Redação
- Botões de ação sempre na mesma posição

**Consistent Identification:**
- Ícones usados consistentemente
- Cores de badge sempre as mesmas
- Terminologia consistente

#### 3.3 Input Assistance

**Error Identification:**
```html
<div role="alert" aria-live="polite">
  Nenhuma matéria encontrada. Tente ajustar os filtros.
</div>
```

**Labels or Instructions:**
- Placeholder text descritivo
- Helper text quando necessário
- Format hints para date inputs

**Error Suggestion:**
- Mensagens de erro construtivas
- Sugestões de correção
- "Tente remover alguns filtros"

**Error Prevention:**
- Confirmation dialog para delete
- "Tem certeza?" antes de ações destrutivas
- Preview antes de publicar (em outras telas)

### 9.4 Robust (Robusto)

#### 4.1 Compatible

**Valid HTML:**
- Markup semântico correto
- Elementos aninhados corretamente
- IDs únicos

**Name, Role, Value:**
- Todos os componentes têm name/aria-label
- Roles ARIA apropriados
- Estados comunicados (checked, expanded, selected)
- Valores atualizados dinamicamente anunciados

**Status Messages:**
```html
<!-- Loading -->
<div role="status" aria-live="polite" aria-atomic="true">
  Carregando matérias...
</div>

<!-- Results -->
<div role="status" aria-live="polite">
  24 matérias encontradas
</div>

<!-- Success -->
<div role="alert" aria-live="assertive">
  Matéria excluída com sucesso
</div>
```

### 9.5 ARIA Patterns Utilizados

#### Dropdown Menu (Filter Buttons)
```html
<button
  aria-haspopup="listbox"
  aria-expanded="false"
  aria-controls="status-dropdown"
>
  Status
</button>

<ul
  id="status-dropdown"
  role="listbox"
  aria-label="Opções de status"
>
  <li role="option" aria-selected="false">Todos</li>
  <li role="option" aria-selected="true">Rascunho</li>
  <li role="option" aria-selected="false">Publicada</li>
</ul>
```

#### Search Input
```html
<div role="search">
  <label for="search-input" class="sr-only">
    Buscar matérias por título, conteúdo ou tags
  </label>
  <input
    id="search-input"
    type="search"
    aria-label="Buscar matérias"
    aria-describedby="search-hint"
  />
  <p id="search-hint" class="sr-only">
    Digite e aguarde para ver resultados
  </p>
</div>
```

#### Article Cards
```html
<article
  aria-labelledby="article-title-123"
  aria-describedby="article-preview-123"
>
  <div role="status" aria-label="Status: Rascunho">
    <span aria-hidden="true">■</span> RASCUNHO
  </div>

  <h3 id="article-title-123">Título da Matéria</h3>
  <p id="article-preview-123">Preview do conteúdo...</p>

  <div role="group" aria-label="Ações da matéria">
    <button aria-label="Visualizar matéria: Título da Matéria">
      Ver
    </button>
    <button aria-label="Editar matéria: Título da Matéria">
      Editar
    </button>
  </div>
</article>
```

#### Modal (Delete Confirmation)
```html
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="modal-title"
  aria-describedby="modal-description"
>
  <h2 id="modal-title">Excluir Matéria?</h2>
  <p id="modal-description">
    Esta ação não pode ser desfeita...
  </p>

  <button aria-label="Cancelar exclusão">Cancelar</button>
  <button aria-label="Confirmar exclusão">Excluir</button>
</div>
```

### 9.6 Screen Reader Testing

**Testes obrigatórios com:**
- NVDA (Windows)
- JAWS (Windows)
- VoiceOver (macOS/iOS)
- TalkBack (Android)

**Fluxos a testar:**
1. Navegação pelo header e menu
2. Uso dos filtros
3. Navegação pelos cards
4. Leitura de informações do card
5. Acionamento de ações (Ver, Editar, Excluir)
6. Confirmação de exclusão
7. Feedback de sucesso/erro
8. Paginação

---

## 10. Especificações Técnicas de Componentes

### 10.1 Componente: FilterBar

#### Props
```typescript
interface FilterBarProps {
  onFilterChange: (filters: Filters) => void;
  initialFilters?: Filters;
  loading?: boolean;
  resultsCount?: number;
}

interface Filters {
  searchQuery: string;
  status: 'all' | 'draft' | 'published';
  category: string | null;
  dateRange: DateRange | null;
  author: string | null;
}

interface DateRange {
  from: Date;
  to: Date;
}
```

#### Estado Interno
```typescript
const [filters, setFilters] = useState<Filters>(initialFilters);
const [openDropdown, setOpenDropdown] = useState<string | null>(null);
const [searchDebounce, setSearchDebounce] = useState<NodeJS.Timeout>();
```

#### Métodos Principais
```typescript
handleSearchChange(value: string): void
handleFilterSelect(type: string, value: any): void
handleClearFilters(): void
handleClearSingleFilter(type: string): void
```

#### Dependências
- React, useState, useEffect, useCallback
- Lucide React (ícones)
- date-fns (manipulação de datas)

### 10.2 Componente: ArticleCard

#### Props
```typescript
interface ArticleCardProps {
  article: Article;
  onView: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete?: (id: string) => void;
  showAuthor?: boolean;
}

interface Article {
  id: string;
  title: string;
  preview: string;
  content: string;
  status: 'draft' | 'published';
  category: string;
  tags: string[];
  author: {
    id: string;
    name: string;
    avatar?: string;
  };
  createdAt: Date;
  updatedAt: Date;
  publishedAt?: Date;
  views?: number;
  metadata?: {
    readTime?: number;
    wordCount?: number;
  };
}
```

#### Estado Interno
```typescript
const [showMenu, setShowMenu] = useState(false);
const [isDeleting, setIsDeleting] = useState(false);
```

#### Métodos Principais
```typescript
handleView(): void
handleEdit(): void
handleDelete(): void
handleMenuToggle(): void
formatDate(date: Date): string
formatViews(views: number): string
```

#### Dependências
- React
- Lucide React (ícones)
- date-fns (formatRelativeTime)

### 10.3 Componente: StatusBadge

#### Props
```typescript
interface StatusBadgeProps {
  status: 'draft' | 'published' | 'in-review';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}
```

#### Renderização
```typescript
const BADGE_CONFIG = {
  draft: {
    label: 'RASCUNHO',
    color: '#E87722',
    bgColor: '#FFF5EE',
    icon: FileEdit
  },
  published: {
    label: 'PUBLICADA',
    color: '#10B981',
    bgColor: '#E8F5E9',
    icon: CheckCircle
  },
  'in-review': {
    label: 'EM REVISÃO',
    color: '#F59E0B',
    bgColor: '#FFF8E6',
    icon: Clock
  }
};
```

### 10.4 Componente: Pagination

#### Props
```typescript
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  showInfo?: boolean;
}
```

#### Estado Interno
```typescript
const [visiblePages, setVisiblePages] = useState<number[]>([]);
```

#### Métodos Principais
```typescript
calculateVisiblePages(): number[]
handlePageChange(page: number): void
handlePrevious(): void
handleNext(): void
```

#### Lógica de Páginas Visíveis
```typescript
// Exemplo: currentPage = 5, totalPages = 20
// Desktop: [1, ..., 4, 5, 6, ..., 20]
// Mobile: [4, 5, 6]

function calculateVisiblePages() {
  const isMobile = window.innerWidth < 768;
  const maxVisible = isMobile ? 3 : 7;

  // ... lógica de cálculo
}
```

### 10.5 Componente: EmptyState

#### Props
```typescript
interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ComponentType;
  primaryAction?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
}
```

#### Variações
```typescript
// Sem matérias
<EmptyState
  title="Nenhuma matéria criada"
  description="Comece criando sua primeira matéria..."
  icon={FileText}
  primaryAction={{
    label: "Criar Matéria",
    onClick: () => navigate('/criar')
  }}
/>

// Sem resultados de busca
<EmptyState
  title="Nenhum resultado encontrado"
  description="Tente ajustar os filtros ou buscar por outros termos"
  icon={Search}
  secondaryAction={{
    label: "Limpar Filtros",
    onClick: clearFilters
  }}
/>
```

### 10.6 Componente: ConfirmDialog

#### Props
```typescript
interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'info';
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
  loading?: boolean;
}
```

#### Estado Interno
```typescript
const [isConfirming, setIsConfirming] = useState(false);
```

#### Métodos Principais
```typescript
async handleConfirm(): Promise<void>
handleCancel(): void
handleKeyDown(e: KeyboardEvent): void // Esc to close
```

### 10.7 Componente: Toast

#### Props
```typescript
interface ToastProps {
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
  onClose?: () => void;
}
```

#### Uso via Context
```typescript
const { showToast } = useToast();

// Exemplo
showToast({
  message: 'Matéria excluída com sucesso',
  type: 'success',
  duration: 3000
});
```

### 10.8 Hooks Personalizados

#### useFilters
```typescript
function useFilters(initialFilters?: Filters) {
  const [filters, setFilters] = useState<Filters>(initialFilters);

  const updateFilter = useCallback((key: keyof Filters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  });

  const clearFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  });

  const activeFiltersCount = useMemo(() => {
    // Conta quantos filtros estão ativos
  }, [filters]);

  return { filters, updateFilter, clearFilters, activeFiltersCount };
}
```

#### useArticles
```typescript
function useArticles(filters: Filters) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [pagination, setPagination] = useState<Pagination>({
    currentPage: 1,
    totalPages: 1,
    totalItems: 0,
    itemsPerPage: 20
  });

  useEffect(() => {
    fetchArticles(filters);
  }, [filters]);

  const fetchArticles = async (filters: Filters) => {
    // ... fetch logic
  };

  const deleteArticle = async (id: string) => {
    // ... delete logic
  };

  return {
    articles,
    loading,
    error,
    pagination,
    deleteArticle,
    refetch: () => fetchArticles(filters)
  };
}
```

#### useDebounce
```typescript
function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}
```

---

## 11. Fluxos de Usuário

### 11.1 Fluxo: Buscar Matéria

1. Usuário acessa página "Minhas Matérias"
2. Vê lista completa de matérias
3. Digita termo na busca (ex: "eleições")
4. Sistema debounce 300ms
5. Loading indicator aparece
6. Resultados filtrados aparecem
7. Contador atualiza "X matérias encontradas"
8. Pills de filtros ativos aparecem

**Tempo esperado:** < 2 segundos

### 11.2 Fluxo: Aplicar Múltiplos Filtros

1. Usuário clica em "Status"
2. Dropdown abre
3. Seleciona "Rascunho"
4. Dropdown fecha
5. Botão Status fica laranja
6. Pill "×Rascunho" aparece
7. Lista atualiza
8. Usuário clica em "Tema"
9. Seleciona "Política"
10. Pill "×Política" aparece
11. Lista atualiza com ambos filtros

**Tempo esperado:** < 1 segundo por filtro

### 11.3 Fluxo: Editar Matéria

1. Usuário encontra matéria (via busca ou scroll)
2. Hover no card (feedback visual)
3. Clica em "Editar"
4. Sistema valida permissões
5. Navega para página de edição
6. Carrega dados da matéria
7. Exibe editor preenchido

**Tempo esperado:** < 3 segundos

### 11.4 Fluxo: Excluir Rascunho

1. Usuário localiza rascunho
2. Clica em "Excluir"
3. Modal de confirmação abre
4. Foco vai para botão "Cancelar"
5. Usuário lê mensagem
6. Clica em "Excluir"
7. Modal fecha
8. Loading indicator no card
9. Card fade out
10. Toast de sucesso aparece
11. Lista reajusta layout
12. Contador atualiza

**Tempo esperado:** < 2 segundos após confirmação

### 11.5 Fluxo: Visualizar Métricas (Matéria Publicada)

1. Usuário localiza matéria publicada
2. Vê contador de visualizações no card
3. Clica em "Métricas" (ou "•••" → "Ver métricas")
4. Modal/página de métricas abre
5. Exibe:
   - Visualizações totais
   - Gráfico de visualizações ao longo do tempo
   - Origem do tráfego
   - Tempo médio de leitura
   - Taxa de conclusão

**Tempo esperado:** < 2 segundos

---

## 12. Cenários de Erro

### 12.1 Erro de Conexão

**Sintoma:** API não responde

**Feedback:**
```
┌─────────────────────────────────────┐
│ ⚠️ Erro de Conexão                  │
│                                     │
│ Não foi possível carregar suas     │
│ matérias. Verifique sua conexão.   │
│                                     │
│        [Tentar Novamente]           │
└─────────────────────────────────────┘
```

**Ações:**
- Exibe mensagem de erro
- Mantém últimos dados em cache (se houver)
- Botão "Tentar Novamente"
- Retry automático após 5s (até 3 vezes)

### 12.2 Nenhuma Matéria Encontrada

**Sintoma:** Usuário não tem matérias ou filtros muito restritivos

**Feedback:**
- Empty state com ícone de documento
- Mensagem contextual
- Sugestões de ação (criar matéria ou limpar filtros)

### 12.3 Erro ao Excluir

**Sintoma:** DELETE request falha

**Feedback:**
```
Toast vermelho:
"✗ Não foi possível excluir a matéria. Tente novamente."
```

**Ações:**
- Toast de erro
- Card volta ao estado normal
- Log erro no console
- Permite retry

### 12.4 Sessão Expirada

**Sintoma:** Token de autenticação inválido

**Feedback:**
- Modal informando sessão expirada
- Redireciona para login
- Preserva filtros/estado na URL
- Retorna ao mesmo estado após re-login

### 12.5 Permissão Negada

**Sintoma:** Usuário tenta editar matéria que não é sua

**Feedback:**
```
Toast laranja:
"⚠️ Você não tem permissão para editar esta matéria."
```

**Ações:**
- Impede ação
- Exibe toast
- Botões "Editar" ficam disabled se não for o autor

---

## 13. Performance e Otimizações

### 13.1 Lazy Loading

**Imagens:**
```html
<img
  src={article.thumbnail}
  loading="lazy"
  decoding="async"
  alt={article.title}
/>
```

**Componentes:**
```javascript
const ConfirmDialog = lazy(() => import('./ConfirmDialog'));
const MetricsModal = lazy(() => import('./MetricsModal'));
```

### 13.2 Virtualization (Listas Longas)

Se usuário tiver > 100 matérias, usar react-window:

```javascript
import { FixedSizeGrid } from 'react-window';

<FixedSizeGrid
  columnCount={2}
  columnWidth={350}
  height={800}
  rowCount={Math.ceil(articles.length / 2)}
  rowHeight={280}
  width={720}
>
  {({ columnIndex, rowIndex, style }) => (
    <div style={style}>
      <ArticleCard article={articles[rowIndex * 2 + columnIndex]} />
    </div>
  )}
</FixedSizeGrid>
```

### 13.3 Caching

**LocalStorage:**
- Cache de filtros (expire 7 dias)
- Cache de última visualização (scroll position)

**React Query / SWR:**
- Cache de artigos (stale time: 5min)
- Refetch em background
- Optimistic updates em delete

### 13.4 Debounce e Throttle

**Search Input:**
- Debounce 300ms

**Scroll Events:**
- Throttle 100ms para scroll-to-top button

**Resize Events:**
- Throttle 200ms para responsive adjustments

### 13.5 Code Splitting

```javascript
// Route-based splitting
const MinhasMaterias = lazy(() => import('./pages/MinhasMaterias'));
const RedacaoPage = lazy(() => import('./pages/RedacaoPage'));

// Component-based splitting
const ArticleEditor = lazy(() => import('./components/ArticleEditor'));
```

### 13.6 Metrics

**Core Web Vitals Targets:**
- LCP (Largest Contentful Paint): < 2.5s
- FID (First Input Delay): < 100ms
- CLS (Cumulative Layout Shift): < 0.1

**Specific Metrics:**
- Time to Interactive: < 3s
- First Contentful Paint: < 1.5s
- Speed Index: < 3s

---

## 14. Testes

### 14.1 Testes Unitários

**Componentes a testar:**
- FilterBar
- ArticleCard
- StatusBadge
- Pagination
- EmptyState
- ConfirmDialog

**Exemplo:**
```javascript
describe('ArticleCard', () => {
  it('renders draft badge for draft articles', () => {
    const article = { ...mockArticle, status: 'draft' };
    render(<ArticleCard article={article} />);
    expect(screen.getByText('RASCUNHO')).toBeInTheDocument();
  });

  it('calls onDelete when delete button is clicked', () => {
    const onDelete = jest.fn();
    render(<ArticleCard article={mockArticle} onDelete={onDelete} />);
    fireEvent.click(screen.getByText('Excluir'));
    fireEvent.click(screen.getByText('Confirmar'));
    expect(onDelete).toHaveBeenCalledWith(mockArticle.id);
  });
});
```

### 14.2 Testes de Integração

**Fluxos a testar:**
1. Filtrar por status → verificar resultados
2. Buscar texto → verificar resultados
3. Combinar múltiplos filtros
4. Excluir rascunho → verificar remoção da lista
5. Navegar entre páginas → verificar conteúdo

### 14.3 Testes de Acessibilidade

**Ferramentas:**
- axe-core
- jest-axe
- NVDA/JAWS manual testing

**Exemplo:**
```javascript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

it('should not have accessibility violations', async () => {
  const { container } = render(<MinhasMaterias />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### 14.4 Testes E2E

**Ferramentas:** Playwright, Cypress

**Cenários:**
```javascript
test('complete filtering flow', async ({ page }) => {
  await page.goto('/minhas-materias');

  // Aplicar filtro de status
  await page.click('button:has-text("Status")');
  await page.click('text=Rascunho');

  // Verificar badge ativo
  await expect(page.locator('.filter-pill')).toContainText('Rascunho');

  // Verificar apenas rascunhos na lista
  const badges = await page.locator('.status-badge').allTextContents();
  expect(badges.every(badge => badge === 'RASCUNHO')).toBe(true);
});
```

### 14.5 Testes de Performance

**Lighthouse CI:**
- Rodar em cada PR
- Targets: Performance > 90, Accessibility > 95

**Bundle Size:**
- Monitorar com bundlephobia
- Alert se bundle crescer > 10%

---

## 15. Documentação para Desenvolvedores

### 15.1 Estrutura de Arquivos

```
src/
├── pages/
│   └── MinhasMaterias/
│       ├── index.jsx
│       ├── MinhasMaterias.module.css
│       └── __tests__/
│           └── MinhasMaterias.test.jsx
├── components/
│   ├── FilterBar/
│   │   ├── FilterBar.jsx
│   │   ├── FilterBar.module.css
│   │   └── __tests__/
│   ├── ArticleCard/
│   │   ├── ArticleCard.jsx
│   │   ├── ArticleCard.module.css
│   │   └── __tests__/
│   ├── StatusBadge/
│   ├── Pagination/
│   ├── EmptyState/
│   └── ConfirmDialog/
├── hooks/
│   ├── useFilters.js
│   ├── useArticles.js
│   └── useDebounce.js
├── context/
│   └── ToastContext.jsx
├── utils/
│   ├── formatters.js
│   └── validators.js
└── types/
    └── article.ts
```

### 15.2 Convenções de Código

**Naming:**
- Componentes: PascalCase
- Hooks: camelCase com prefixo "use"
- Utils: camelCase
- Constants: UPPER_SNAKE_CASE

**CSS:**
- CSS Modules ou Tailwind
- Classes BEM se usar CSS puro
- Variáveis CSS para cores/espaçamentos

**Props:**
- Sempre tipar com PropTypes ou TypeScript
- Desestruturar props
- Valores padrão explícitos

### 15.3 Git Workflow

**Branches:**
- `main` - produção
- `develop` - desenvolvimento
- `feature/minhas-materias-filtros`
- `fix/article-card-layout`

**Commits:**
```
feat(minhas-materias): add filter by status
fix(article-card): correct hover animation
docs(ui-ux): update component specs
test(filter-bar): add unit tests
```

### 15.4 Deployment

**Build:**
```bash
npm run build
```

**Otimizações de Build:**
- Minificação
- Tree shaking
- Code splitting
- Image optimization (next/image ou similar)

**Environment Variables:**
```env
REACT_APP_API_URL=https://api.tmc.com.br
REACT_APP_ENV=production
```

---

## 16. Checklist de Implementação

### Fase 1: Setup e Estrutura
- [ ] Criar estrutura de pastas
- [ ] Configurar routing para `/minhas-materias`
- [ ] Criar componente base da página
- [ ] Configurar contextos necessários (Toast, Filters)

### Fase 2: Componentes Base
- [ ] FilterBar component
  - [ ] Search input
  - [ ] Dropdown de Status
  - [ ] Dropdown de Tema
  - [ ] Dropdown de Data
  - [ ] Dropdown de Redator
  - [ ] Active filter pills
  - [ ] Clear filters button
- [ ] ArticleCard component
  - [ ] Layout básico
  - [ ] Status badge
  - [ ] Metadata display
  - [ ] Action buttons
  - [ ] Hover states
- [ ] StatusBadge component
- [ ] Pagination component
- [ ] EmptyState component
- [ ] ConfirmDialog component

### Fase 3: Funcionalidades
- [ ] Integração com API
  - [ ] GET /articles (com filtros)
  - [ ] DELETE /articles/:id
- [ ] Sistema de filtros
  - [ ] Lógica de combinação (AND)
  - [ ] Debounce na busca
  - [ ] URL parameters
  - [ ] LocalStorage persistence
- [ ] Ações dos cards
  - [ ] Ver matéria
  - [ ] Editar matéria
  - [ ] Excluir rascunho
  - [ ] Ver métricas (publicadas)
- [ ] Paginação
  - [ ] Client-side ou server-side
  - [ ] Navegação
  - [ ] Info display

### Fase 4: Estados e Feedback
- [ ] Loading states
  - [ ] Skeleton loading
  - [ ] Spinner global
- [ ] Error states
  - [ ] Connection error
  - [ ] Empty states
  - [ ] Permission errors
- [ ] Success feedback
  - [ ] Toast notifications
  - [ ] Animations

### Fase 5: Responsividade
- [ ] Mobile layout (< 768px)
  - [ ] Mobile filter modal
  - [ ] Card adaptations
  - [ ] Button stacking
- [ ] Tablet layout (768-1023px)
- [ ] Desktop layout (1440px+)
- [ ] XL Desktop layout (1920px+)

### Fase 6: Acessibilidade
- [ ] Semantic HTML
- [ ] ARIA labels e roles
- [ ] Keyboard navigation
  - [ ] Tab order
  - [ ] Enter/Space activation
  - [ ] Esc to close
- [ ] Focus management
- [ ] Skip links
- [ ] Screen reader testing
- [ ] Color contrast validation

### Fase 7: Performance
- [ ] Lazy loading de imagens
- [ ] Code splitting
- [ ] Debounce/throttle
- [ ] Virtualization (se necessário)
- [ ] Caching (React Query/SWR)
- [ ] Lighthouse audit (> 90 performance)

### Fase 8: Testes
- [ ] Unit tests (componentes)
- [ ] Integration tests (fluxos)
- [ ] Accessibility tests (axe-core)
- [ ] E2E tests (Playwright/Cypress)
- [ ] Visual regression tests
- [ ] Performance tests

### Fase 9: Documentação
- [ ] Componentes documentados (Storybook)
- [ ] README atualizado
- [ ] API documentation
- [ ] User guide

### Fase 10: Review e Deploy
- [ ] Code review
- [ ] QA testing
- [ ] Staging deployment
- [ ] Production deployment
- [ ] Monitoring setup

---

## 17. Dependências Recomendadas

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "lucide-react": "^0.300.0",
    "date-fns": "^2.30.0",
    "@tanstack/react-query": "^5.14.0",
    "clsx": "^2.0.0"
  },
  "devDependencies": {
    "@testing-library/react": "^14.1.0",
    "@testing-library/jest-dom": "^6.1.0",
    "@axe-core/react": "^4.8.0",
    "jest-axe": "^8.0.0",
    "playwright": "^1.40.0",
    "eslint": "^8.55.0",
    "eslint-plugin-jsx-a11y": "^6.8.0"
  }
}
```

---

## 18. Notas Finais

Este documento de planejamento UI/UX foi criado seguindo as melhores práticas de design de interfaces e acessibilidade. Todos os componentes foram especificados com atenção aos detalhes visuais, funcionais e técnicos.

**Principais destaques:**
- Seguimento rigoroso do Brand Guide TMC
- Compliance com WCAG 2.1 Nível AA
- Design responsivo mobile-first
- Performance otimizada
- Experiência de usuário fluida e intuitiva

**Próximos passos:**
1. Review deste documento com stakeholders
2. Aprovação final do design
3. Início da implementação seguindo checklist
4. Testes iterativos de usabilidade
5. Deploy e monitoramento

---

**Documento criado em:** 07/12/2024
**Versão:** 1.0
**Autor:** Claude (Anthropic AI)
**Projeto:** Portal TMC - Sistema de Redação
