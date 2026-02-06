# Plano UI/UX: Filtro de Urgencia por Hora (Freshness Filter)

## Analise: Filtro de Frescor/Urgencia Temporal

### Entendimento
O redator jornalistico precisa identificar rapidamente quais noticias sao **quentes** (acabaram de ser publicadas) vs. noticias que ja tem algumas horas. Em um ciclo de 24h de coleta, a "frescura" da noticia e um fator critico na decisao editorial - noticias de 30min atras tem urgencia completamente diferente de noticias de 12h atras.

### Contexto Atual
- **FilterBar** atual: Search, Tema, Tag, Origem (4 filtros)
- **FiltersContext**: ja possui campo `period: 'today'` (declarado mas NAO implementado)
- **ArticleCard**: ja exibe timestamp relativo (`ha 2h`, `ha 30min`, etc.)
- **API**: nao envia parametro de periodo atualmente
- **IntervalFilter** existe para videos (transcricao), mas nao para artigos do feed

---

## Proposta: Urgency Chips (Horizontal Pill Bar)

### Por que Chips e nao Dropdown?
1. **Visibilidade imediata** - o redator ve todas as opcoes sem clique extra
2. **Selecao rapida** - 1 clique vs. 2 (abrir dropdown + selecionar)
3. **Contexto visual** - cores e icones comunicam urgencia instantaneamente
4. **Padrao jornalistico** - redacoes usam classificacao visual de urgencia

### Clusters de Tempo Propostos

Baseado no workflow jornalistico real, onde urgencia decai exponencialmente:

| Cluster | Intervalo | Label | Icone | Cor | Justificativa |
|---------|-----------|-------|-------|-----|---------------|
| **AGORA** | 0-1h | `Agora` | Flame | Vermelho `#EF4444` | Breaking news, publicacao imediata |
| **RECENTE** | 1-3h | `Recente` | Zap | Laranja `#F59E0B` | Ainda quente, janela de oportunidade |
| **HOJE** | 3-8h | `Hoje` | Clock | Azul `#2563EB` | Noticias do dia, analise possivel |
| **MAIS CEDO** | 8-24h | `Mais cedo` | History | Cinza `#6B7280` | Materia de ontem/madrugada, ainda relevante |
| **TODAS** | 0-24h | `Todas` | - | Default | Sem filtro temporal (estado padrao) |

### Racional dos Clusters:
- **0-1h (Agora)**: A "golden hour" do jornalismo. A noticia acabou de sair. Redatores precisam agir RAPIDO. Textos de agencias, breaking news.
- **1-3h (Recente)**: Ainda ha tempo de cobrir com originalidade. Janela ideal para criacao de conteudo baseado em fontes multiplas.
- **3-8h (Hoje)**: Noticias da manha/tarde corrente. Ideal para analises mais aprofundadas e matérias de contexto.
- **8-24h (Mais cedo)**: Matérias que podem já ter sido cobertas pela concorrência, mas ainda servem para artigos de análise, opinião ou retrospectiva.

---

## Localizacao na Interface

### Posicao: Abaixo da FilterBar, acima do grid de artigos

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Busca________________________]  [Tema▼]  [Tag▼]  [Origem▼]        │  ← FilterBar existente
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🕐 Frescor:  [Todas]  [🔥 Agora]  [⚡ Recente]  [🕐 Hoje]  [📋 Mais cedo] │  ← NOVO: Urgency Chips
│                                                                     │
│  Mostrando 45 matérias • Última atualização há 5 min               │  ← Counter + refresh info
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Card 1  │  │  Card 2  │  │  Card 3  │  │  Card 4  │           │  ← Article Grid
│  │  🔥 2min │  │  ⚡ 1h30 │  │  🕐 5h   │  │  📋 12h  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
```

### Por que esta posicao?
1. **Hierarquia de filtros**: Filtros de conteudo (tema, tag, origem) ficam na barra principal. Filtro temporal fica em uma segunda linha porque e uma **dimensao diferente** de filtragem.
2. **Scan visual**: O olho desce naturalmente - filtros > urgencia > artigos.
3. **Nao poluir a FilterBar**: A FilterBar ja tem 4 elementos. Adicionar mais um dropdown quebraria o ritmo visual.

---

## Especificacao Visual Detalhada

### Urgency Chips Bar

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│  🕐  Frescor:   ┌─────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────┐  ┌──────────────┐  │
│                  │  Todas  │  │  🔥 Agora (12)│  │ ⚡ Recente(8)│  │ 🕐 Hoje(20)│  │📋 Mais cedo(5)│  │
│                  └─────────┘  └───────────────┘  └──────────────┘  └───────────┘  └──────────────┘  │
│                                                                                  │
│  45 matérias encontradas                                                         │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Chip Individual - Estados

```css
/* Default (nao selecionado) */
.chip-default {
  background: white;
  border: 1px solid #E5E7EB;    /* light-gray */
  color: #6B7280;               /* medium-gray */
  border-radius: 9999px;        /* full rounded */
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
}

/* Hover */
.chip-hover {
  border-color: var(--chip-color);
  color: var(--chip-color);
  background: var(--chip-color-10);  /* 10% opacity */
}

/* Active/Selected */
.chip-active {
  background: var(--chip-color);
  border-color: var(--chip-color);
  color: white;
  font-weight: 600;
  box-shadow: 0 2px 8px var(--chip-color-25);  /* glow sutil */
}
```

### Cores por Cluster

| Cluster | --chip-color | Hover BG | Active BG | Badge |
|---------|-------------|----------|-----------|-------|
| Todas | `#6B7280` | `#F3F4F6` | `#6B7280` | - |
| Agora | `#EF4444` | `#FEF2F2` | `#EF4444` | count vermelho |
| Recente | `#F59E0B` | `#FFFBEB` | `#F59E0B` | count laranja |
| Hoje | `#2563EB` | `#EFF6FF` | `#2563EB` | count azul |
| Mais cedo | `#6B7280` | `#F3F4F6` | `#6B7280` | count cinza |

### Animacao do Chip "Agora"
Quando ha matérias na ultima hora, o chip "Agora" deve ter um **pulse sutil** para chamar atencao:

```css
/* Apenas quando chip "Agora" nao esta selecionado E tem count > 0 */
@keyframes urgency-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
  50% { box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.15); }
}

.chip-agora-has-items:not(.active) {
  animation: urgency-pulse 2s ease-in-out infinite;
}
```

---

## Impacto no ArticleCard

### Badge de Urgencia no Card (Opcional, recomendado)

Adicionar um pequeno indicador visual de frescor no canto do card:

```
┌─────────────────────────────────────────┐
│ [🔥] ☐                    [TECNOLOGIA]  │  ← Icone de urgencia ao lado do checkbox
│                                          │
│ Título da matéria que pode               │
│ ocupar até duas linhas...                │
│                                          │
│ [🌐] G1 • há 15 min                     │
│ #tag1 #tag2 #tag3                        │
└──────────────────────────────────────────┘
```

Regras do badge:
- **0-1h**: 🔥 (flame icon, vermelho) - pequeno, 16x16px
- **1-3h**: ⚡ (zap icon, laranja) - pequeno, 16x16px
- **3-8h**: sem badge (neutral)
- **8-24h**: sem badge (neutral)

Apenas os dois clusters mais urgentes ganham badge visual no card, para nao poluir a interface.

---

## Fluxo de Interacao

### 1. Estado Inicial
- Chip "Todas" selecionado (estado padrao)
- Todos os artigos visiveis, sem filtro temporal
- Contagem de artigos por cluster calculada client-side usando `publishedAt`

### 2. Selecao de Cluster
```
Usuario clica em [🔥 Agora (12)]
  → Chip "Agora" fica ativo (fundo vermelho, texto branco)
  → Chip "Todas" fica inativo
  → Grid filtra para mostrar apenas artigos de 0-1h
  → Counter atualiza: "12 matérias encontradas"
  → Animacao suave (fade) nos cards que saem/entram
  → Paginacao resetada para pagina 1
```

### 3. Deselecao (volta a "Todas")
```
Usuario clica no chip ativo OU clica em "Todas"
  → Volta ao estado sem filtro temporal
  → Todos os artigos visiveis novamente
```

### 4. Combinacao com Outros Filtros
O filtro de urgencia e **combinavel** com os outros filtros:
```
Exemplo: [Tema: Tecnologia] + [🔥 Agora]
  → Mostra apenas artigos de Tecnologia publicados na ultima hora
  → Counter: "3 matérias encontradas"
```

### 5. Estado Vazio
```
Se cluster selecionado tem 0 artigos:
  → EmptyState: "Nenhuma matéria nas últimas X horas"
  → Sugestao: "Tente ampliar o intervalo de tempo"
```

---

## Abordagem Tecnica: Client-Side vs Server-Side

### Recomendacao: **Filtragem Client-Side** (fase 1)

**Por que?**
1. Os artigos ja tem `publishedAt` como campo Date no frontend
2. Sao apenas 24h de artigos (maximo ~200-300), ja carregados
3. A filtragem por data e uma simples comparacao de timestamps
4. Nao requer mudancas na API backend
5. Response time instantaneo (0ms vs ~200ms da API)

**Implementacao**:
- O filtro de urgencia filtra `articles[]` localmente no `RedacaoPage`
- As contagens por cluster sao calculadas usando `useMemo` sobre todos os artigos
- Quando combinado com outros filtros, a urgencia atua como filtro adicional sobre os resultados da API

**Fase 2 (futuro)**: Se necessario, adicionar parametro `hours_ago` na API para filtragem server-side com paginacao.

---

## Consideracoes de Responsividade

### Desktop (>1280px)
```
🕐 Frescor:  [Todas]  [🔥 Agora (12)]  [⚡ Recente (8)]  [🕐 Hoje (20)]  [📋 Mais cedo (5)]
```
Todos os chips visíveis em uma linha.

### Tablet (768-1280px)
```
🕐 Frescor:  [Todas]  [🔥 Agora (12)]  [⚡ Recente (8)]  [🕐 Hoje (20)]  [📋 Mais cedo (5)]
```
Mesma disposição, chips menores (padding reduzido, sem label "Frescor").

### Mobile (<768px)
```
[Todas] [🔥 12] [⚡ 8] [🕐 20] [📋 5]
```
- Labels abreviados (apenas icone + count)
- Scroll horizontal se necessario
- Chips menores

---

## Acessibilidade

- `role="radiogroup"` no container dos chips
- `role="radio"` + `aria-checked` em cada chip
- `aria-label` descritivo: "Filtrar por matérias publicadas na última hora (12 matérias)"
- Navegacao por teclado: Arrow Left/Right entre chips, Enter/Space para selecionar
- Contraste minimo 4.5:1 em todos os estados
- `aria-live="polite"` no counter para anunciar mudancas

---

## Componentes a Criar/Modificar

### Novos:
1. **`UrgencyChips.jsx`** - Componente dos chips de urgencia (novo)
2. **`useUrgencyFilter.js`** - Hook para logica de filtragem temporal (novo, opcional)

### Modificar:
3. **`FiltersContext.jsx`** - Adicionar campo `urgency` (null | 'now' | 'recent' | 'today' | 'earlier')
4. **`RedacaoPage.jsx`** - Integrar UrgencyChips + filtragem client-side no useMemo
5. **`ArticleCard.jsx`** - Adicionar badge de urgencia (opcional, fase 2)

### NAO modificar:
- `FilterBar.jsx` - Os chips ficam FORA da FilterBar, como componente separado
- `api.js` - Filtragem e client-side, sem mudanca na API

---

## Resumo das Decisoes de Design

| Decisao | Escolha | Alternativa descartada | Motivo |
|---------|---------|----------------------|--------|
| Formato | Chips horizontais | Dropdown/Select | Visibilidade imediata, 1 clique |
| Posicao | Abaixo da FilterBar | Dentro da FilterBar | Separacao de dimensoes de filtro |
| Clusters | 4 + "Todas" | 6 clusters de 4h | Jornalismo tem urgencia exponencial, nao linear |
| Filtragem | Client-side | Server-side | Performance, simplicidade, artigos ja carregados |
| Selecao | Single-select | Multi-select | Simplicidade, caso de uso claro |
| Contagem | Badge no chip | Sem contagem | Feedback quantitativo essencial |
| Badge no card | Apenas 0-1h e 1-3h | Todos os clusters | Evitar poluicao visual |
| Pulse | Apenas "Agora" | Nenhum | Chamar atencao para breaking news |
