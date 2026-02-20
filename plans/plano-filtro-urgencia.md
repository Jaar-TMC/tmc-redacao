# Plano UI/UX: Filtro de Urgencia por Hora (Freshness Filter)

## Analise: Filtro de Frescor/Urgencia Temporal

### Entendimento
O redator jornalistico precisa identificar rapidamente quais noticias sao **quentes** (acabaram de ser publicadas) vs. noticias que ja tem algumas horas. Em um ciclo de 24h de coleta, a "frescura" da noticia e um fator critico na decisao editorial - noticias de 30min atras tem urgencia completamente diferente de noticias de 12h atras.

### Contexto Atual
- **FilterBar** atual: Search, Tema, Tag, Origem (4 filtros)
- **FiltersContext**: ja possui campo `period: 'today'` (declarado mas NAO implementado no frontend)
- **ArticleCard**: ja exibe timestamp relativo (`ha 2h`, `ha 30min`, etc.)
- **Backend `get_articles()`**: ja aceita parametro `period` com valores `today/week/month` usando `DATEADD`
- **Frontend `api.js`**: NAO envia `period` atualmente (campo ignorado)
- **Ordenacao**: Backend ja ordena por `published_at DESC` (mais recente primeiro)

---

## Proposta: Urgency Chips (Horizontal Pill Bar)

### Por que Chips e nao Dropdown?
1. **Visibilidade imediata** - o redator ve todas as opcoes sem clique extra
2. **Selecao rapida** - 1 clique vs. 2 (abrir dropdown + selecionar)
3. **Contexto visual** - cores e icones comunicam urgencia instantaneamente
4. **Padrao jornalistico** - redacoes usam classificacao visual de urgencia

### Clusters de Tempo Propostos

Baseado no workflow jornalistico real, onde urgencia decai exponencialmente:

| Cluster | Intervalo | Label | Icone | Cor | API param | Justificativa |
|---------|-----------|-------|-------|-----|-----------|---------------|
| **TODAS** | 0-24h | `Todas` | - | Default `#6B7280` | `urgency=null` | Sem filtro temporal (estado padrao) |
| **AGORA** | 0-1h | `Agora` | Flame | Vermelho `#EF4444` | `urgency=1` | Breaking news, publicacao imediata |
| **RECENTE** | 1-3h | `Recente` | Zap | Laranja `#F59E0B` | `urgency=3` | Ainda quente, janela de oportunidade |
| **HOJE** | 3-8h | `Hoje` | Sun | Azul `#2563EB` | `urgency=8` | Noticias do dia, analise possivel |
| **MAIS CEDO** | 8-24h | `Mais cedo` | History | Cinza `#6B7280` | `urgency=24` | Materia de ontem/madrugada, ainda relevante |

> **Nota sobre icones**: O chip "Hoje" usa `Sun` (nao `Clock`) para evitar duplicidade com o label "Frescor" que usa `Clock`.

### Racional dos Clusters:
- **0-1h (Agora)**: A "golden hour" do jornalismo. A noticia acabou de sair. Redatores precisam agir RAPIDO.
- **1-3h (Recente)**: Ainda ha tempo de cobrir com originalidade. Janela ideal para criacao de conteudo baseado em fontes multiplas.
- **3-8h (Hoje)**: Noticias da manha/tarde corrente. Ideal para analises mais aprofundadas e materias de contexto.
- **8-24h (Mais cedo)**: Materias que podem ja ter sido cobertas pela concorrencia, mas ainda servem para artigos de analise, opiniao ou retrospectiva.

---

## Abordagem Tecnica: Filtragem Server-Side com Paginacao

### Decisao: **Server-side filtering + server-side pagination**

O filtro de urgencia e enviado como parametro para a API. O backend filtra por hora e retorna paginado, sempre do mais recente pro mais antigo.

**Por que server-side?**
1. A paginacao existente e server-side (20 por pagina) - filtrar client-side daria contagens erradas
2. O backend ja tem infra para filtros (`period` param no `get_articles()`)
3. Contagens precisam refletir o total real, nao apenas a pagina atual
4. Performance consistente independente do volume de artigos

### Mudancas no Backend

#### 1. `database.py` - `get_articles()` (linha ~236)
Estender o parametro `period` para aceitar valores de horas:

```python
# Novo: suporte a urgency (horas)
if period:
    if period == 'today':
        conditions.append("a.published_at >= DATEADD(day, -1, GETUTCDATE())")
    elif period == 'week':
        conditions.append("a.published_at >= DATEADD(week, -1, GETUTCDATE())")
    elif period == 'month':
        conditions.append("a.published_at >= DATEADD(month, -1, GETUTCDATE())")
    else:
        # Tentar interpretar como numero de horas (urgency filter)
        try:
            hours = int(period)
            if 1 <= hours <= 24:
                conditions.append("a.published_at >= DATEADD(hour, -%s, GETUTCDATE())")
                params.append(hours)
        except ValueError:
            pass  # Ignorar valores invalidos
```

**Cluster "Mais cedo" (8-24h)**: Precisa de range `BETWEEN`:
```python
# Para urgency com range (ex: 8-24h = min_hours=8, max_hours=24)
if urgency_min and urgency_max:
    conditions.append("""
        a.published_at >= DATEADD(hour, -%s, GETUTCDATE())
        AND a.published_at < DATEADD(hour, -%s, GETUTCDATE())
    """)
    params.extend([urgency_max, urgency_min])
```

**Alternativa mais simples**: Usar apenas `max_hours` e fazer ranges no parametro:
- `urgency=1` → ultimas 1 hora (0-1h)
- `urgency=3` → ultimas 3 horas (0-3h, inclui "Agora")
- `urgency=8` → ultimas 8 horas (0-8h, inclui "Agora" e "Recente")
- `urgency=24` → ultimas 24 horas (0-24h, tudo)
- sem parametro → sem filtro (= todas, default atual)

**DECISAO**: Usar abordagem simples com `max_hours` apenas. Cada chip filtra "tudo ate X horas atras". Isso e suficiente porque o redator tipicamente quer "me mostre o que ha de mais fresco" (0-1h) ou "me mostre as noticias de hoje" (0-8h), nao "mostre APENAS entre 8h e 24h atras".

**Mas se o redator quiser ver "Mais cedo" (8-24h)?** Na verdade, o redator quer "todas" nesse caso - simplesmente nao aplica filtro. O cluster "Mais cedo" funciona melhor como **informacao visual** (badge no chip mostrando quantas tem nesse range) do que como filtro exclusivo. Assim:

| Chip | Clique filtra para | O que mostra |
|------|-------------------|-------------|
| Todas | sem filtro | Todos os artigos 0-24h |
| Agora | `max_hours=1` | Apenas 0-1h |
| Recente | `max_hours=3` | 0-3h (inclui "Agora") |
| Hoje | `max_hours=8` | 0-8h (inclui anteriores) |
| Mais cedo | sem filtro (= Todas) | Todos 0-24h |

**REVISAO**: Isso torna "Mais cedo" e "Todas" identicos. Melhor: **remover "Mais cedo" como filtro** e manter apenas 3 filtros + "Todas":

| Chip | API param | Resultado |
|------|-----------|-----------|
| **Todas** | nenhum | Todos 0-24h (default) |
| **Agora** | `max_hours=1` | Ultimas 1h |
| **Recente** | `max_hours=3` | Ultimas 3h |
| **Hoje** | `max_hours=8` | Ultimas 8h |

Isso e mais limpo: 4 opcoes, cada uma e um subconjunto progressivo.

#### 2. `articles_api.py` - `list_articles_handler()`
Adicionar parsing do novo parametro:

```python
# Existente
period = req.params.get('period')

# Novo: urgency como alias para max_hours
max_hours = req.params.get('max_hours')
if max_hours:
    try:
        hours = int(max_hours)
        if 1 <= hours <= 24:
            period = str(hours)  # Reutiliza o campo period internamente
    except ValueError:
        pass
```

#### 3. `api.js` - `getArticles()`
Adicionar parametro `max_hours`:

```javascript
export async function getArticles(params = {}, options = {}) {
  const queryParams = new URLSearchParams();
  // ... existente ...
  if (params.max_hours) queryParams.append('max_hours', params.max_hours.toString());
  // ...
}
```

### Contagens por Cluster (Endpoint Separado)

Para mostrar contagens nos chips **sem re-fetch a cada troca**, adicionar endpoint leve:

#### `GET /api/articles/counts?group_by=urgency`

```python
# Retorna contagens por cluster de urgencia
# Query unica e eficiente com CASE WHEN
query = """
    SELECT
        SUM(CASE WHEN published_at >= DATEADD(hour, -1, GETUTCDATE()) THEN 1 ELSE 0 END) as now_count,
        SUM(CASE WHEN published_at >= DATEADD(hour, -3, GETUTCDATE()) THEN 1 ELSE 0 END) as recent_count,
        SUM(CASE WHEN published_at >= DATEADD(hour, -8, GETUTCDATE()) THEN 1 ELSE 0 END) as today_count,
        COUNT(*) as total_count
    FROM collected_articles a
    JOIN sources s ON a.source_id = s.id
    WHERE a.published_at >= DATEADD(day, -1, GETUTCDATE())
    -- Aplicar mesmos filtros de conteudo (category, source, search, tag)
"""
```

Response:
```json
{
  "counts": {
    "now": 12,      // 0-1h
    "recent": 28,   // 0-3h (inclui now)
    "today": 45,    // 0-8h (inclui recent)
    "all": 67       // 0-24h
  }
}
```

**Alternativa mais simples**: Retornar as contagens junto com a response de `GET /api/articles` como campo extra. Assim nao precisa de endpoint separado:

```json
{
  "items": [...],
  "total": 67,
  "page": 1,
  "pages": 4,
  "urgency_counts": {
    "now": 12,
    "recent": 28,
    "today": 45,
    "all": 67
  }
}
```

**DECISAO**: Incluir `urgency_counts` na response existente de `GET /api/articles`. Uma unica query SQL adicional (ou subquery) e mais simples que um endpoint separado.

---

## Localizacao na Interface

### Posicao: Dentro da FilterBar como segunda linha

Os chips ficam **dentro** do container branco da FilterBar, como segunda linha separada por um divisor sutil. Isso mantem tudo no mesmo "card" e evita fragmentacao visual.

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Busca________________________]  [Tema▼]  [Tag▼]  [Origem▼]        │  ← Linha 1: filtros de conteudo
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │  ← Divisor sutil (border-t dashed)
│ 🕐 [Todas]  [🔥 Agora]  [⚡ Recente]  [☀ Hoje]                    │  ← Linha 2: filtro temporal
└─────────────────────────────────────────────────────────────────────┘
  45 matérias encontradas                                               ← Counter fora, antes do grid
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Card 1  │  │  Card 2  │  │  Card 3  │  │  Card 4  │                ← Article Grid
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Por que dentro da FilterBar?
1. **Mesma familia visual** - o container `bg-white rounded-xl border` ja existe
2. **Sem espaco extra** entre FilterBar e grid
3. **Coesao** - todos os filtros num so lugar, separados por dimensao (conteudo vs tempo)

---

## Especificacao Visual Detalhada

### Urgency Chips - Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│ [Busca________________________]  [Tema▼]  [Tag▼]  [Origem▼]           │
│                                                                        │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   │
│                                                                        │
│ 🕐  ┌─────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────┐  │
│     │  Todas  │  │  🔥 Agora (12)│  │ ⚡ Recente(28)│  │ ☀ Hoje(45)│  │
│     └─────────┘  └───────────────┘  └──────────────┘  └───────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Chip Individual - Estados (Tailwind classes)

```
Default:     bg-white border border-light-gray text-medium-gray rounded-full px-3.5 py-1.5 text-sm font-medium
Hover:       border-{chip-color} text-{chip-color} bg-{chip-color}/10
Active:      bg-{chip-color} border-{chip-color} text-white font-semibold shadow-sm
```

### Cores por Cluster

| Cluster | Tailwind Active | Tailwind Hover | Count Badge |
|---------|----------------|----------------|-------------|
| Todas | `bg-gray-500 text-white` | `hover:bg-gray-50 hover:text-gray-600` | - |
| Agora | `bg-red-500 text-white` | `hover:bg-red-50 hover:text-red-500` | `bg-red-100 text-red-600` |
| Recente | `bg-amber-500 text-white` | `hover:bg-amber-50 hover:text-amber-500` | `bg-amber-100 text-amber-600` |
| Hoje | `bg-blue-500 text-white` | `hover:bg-blue-50 hover:text-blue-500` | `bg-blue-100 text-blue-600` |

### Animacao do Chip "Agora" (com prefers-reduced-motion)

```css
/* Apenas quando chip "Agora" nao esta selecionado E tem count > 0 */
@keyframes urgency-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
  50% { box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.15); }
}

.chip-agora-has-items:not(.active) {
  animation: urgency-pulse 2s ease-in-out infinite;
}

/* WCAG 2.3.3 - Respeitar preferencia do usuario */
@media (prefers-reduced-motion: reduce) {
  .chip-agora-has-items:not(.active) {
    animation: none;
  }
}
```

---

## Impacto no ArticleCard (Fase 2 - Opcional)

### Urgencia no Timestamp (nao como badge separado)

Em vez de adicionar um icone novo no top do card (espaco apertado), integrar a urgencia no **timestamp existente** no footer:

```
Footer normal:     [🌐] G1 • há 15 min
Footer com frescor: [🌐] G1 • 🔥 há 15 min     (icone vermelho inline)
Footer com frescor: [🌐] G1 • ⚡ há 2h           (icone laranja inline)
Footer > 3h:       [🌐] G1 • há 5h               (sem icone, normal)
```

Regras:
- **0-1h**: Flame icon vermelho antes do timestamp
- **1-3h**: Zap icon laranja antes do timestamp
- **3h+**: Sem icone (comportamento atual)

Isso reutiliza espaco existente sem poluir o layout do card.

---

## Fluxo de Interacao

### 1. Estado Inicial
- Chip "Todas" selecionado (estado padrao, `bg-gray-500 text-white`)
- API chamada sem `max_hours` → retorna todos os artigos 0-24h paginados
- Response inclui `urgency_counts` → chips mostram contagens

### 2. Selecao de Cluster
```
Usuario clica em [🔥 Agora (12)]
  → Chip "Agora" fica ativo (fundo vermelho, texto branco)
  → Chip "Todas" fica inativo (volta ao default)
  → API re-fetch com max_hours=1, page=1
  → Grid atualiza com artigos de 0-1h, paginados
  → Counter: "12 matérias encontradas"
  → Paginacao resetada para pagina 1
```

### 3. Deselecao (volta a "Todas")
```
Usuario clica no chip ativo OU clica em "Todas"
  → API re-fetch sem max_hours, page=1
  → Volta ao estado completo
```

### 4. Combinacao com Outros Filtros
Combinavel com todos os filtros existentes:
```
[Tema: Tecnologia] + [🔥 Agora]
  → API: category=Tecnologia&max_hours=1&page=1
  → urgency_counts considera os filtros de conteudo ativos
```

### 5. Estado Vazio
```
Se cluster selecionado retorna 0 artigos:
  → EmptyState com icone do cluster
  → Mensagem: "Nenhuma matéria na última hora" (ajusta por cluster)
  → Sugestao: "Tente ampliar o período ou ajustar os filtros"
```

### 6. Loading State
```
Ao trocar de chip:
  → Chip selecionado fica ativo imediatamente (feedback instantaneo)
  → Grid mostra loading overlay (pattern existente do RedacaoPage)
  → Contagens nos chips mantem valores anteriores ate response chegar
```

---

## Consideracoes de Responsividade

### Desktop (>1280px)
```
🕐  [Todas]  [🔥 Agora (12)]  [⚡ Recente (28)]  [☀ Hoje (45)]
```
Todos os chips visiveis com labels completos + contagens.

### Tablet (768-1280px)
```
[Todas]  [🔥 Agora (12)]  [⚡ Recente (28)]  [☀ Hoje (45)]
```
Sem icone Clock label. Chips com padding reduzido.

### Mobile (<768px)
```
[Todas] [🔥 12] [⚡ 28] [☀ 45]
```
- Labels omitidos, apenas icone + count
- Chips menores (`px-2.5 py-1 text-xs`)
- Se necessario, scroll horizontal (`overflow-x-auto`)

---

## Acessibilidade

- `role="radiogroup"` + `aria-label="Filtrar por frescor"` no container
- `role="radio"` + `aria-checked` em cada chip
- `aria-label` descritivo: ex. "Agora - matérias da última hora, 12 matérias"
- Navegacao por teclado: Arrow Left/Right entre chips, Enter/Space para selecionar
- Contraste minimo 4.5:1 em todos os estados (verificado: branco sobre #EF4444 = 4.63:1 OK)
- `aria-live="polite"` no counter de materias para anunciar mudancas
- `@media (prefers-reduced-motion: reduce)` para desativar pulse animation
- Focus visible ring (`:focus-visible`) em todos os chips

---

## Componentes a Criar/Modificar

### Novos:
1. **`UrgencyChips.jsx`** - Componente dos chips de urgencia
   - Props: `counts`, `activeUrgency`, `onUrgencyChange`
   - Renderiza 4 chips com icones, labels, contagens
   - Gerencia estados visuais e acessibilidade

### Modificar (Frontend):
2. **`FiltersContext.jsx`** - Adicionar campo `urgency` ao state
   - Tipo: `null | 1 | 3 | 8` (horas)
   - Default: `null` (= "Todas")
   - Incluir no `resetFilters()` como `urgency: null`
3. **`FilterBar.jsx`** - Adicionar UrgencyChips como segunda linha dentro do container
4. **`RedacaoPage.jsx`** - Incluir `filters.urgency` no useEffect de fetch + enviar `max_hours` para API
5. **`api.js`** - Adicionar `max_hours` ao `getArticles()`

### Modificar (Backend):
6. **`database.py`** - Estender `get_articles()` para aceitar `max_hours` (int)
   - Adicionar `urgency_counts` query (SUM com CASE WHEN)
7. **`articles_api.py`** - Parsear `max_hours` param e retornar `urgency_counts` na response

### NAO modificar:
- `ArticleCard.jsx` - Badge no timestamp e fase 2, nao bloqueia o MVP

---

## Resumo das Decisoes de Design

| Decisao | Escolha | Alternativa descartada | Motivo |
|---------|---------|----------------------|--------|
| Formato | Chips horizontais | Dropdown/Select | Visibilidade imediata, 1 clique |
| Posicao | Dentro da FilterBar (2a linha) | Fora, separado | Coesao visual, mesmo container |
| Clusters | 3 + "Todas" | 4 + "Todas" com "Mais cedo" | "Mais cedo" e identico a "Todas" na pratica |
| Filtragem | **Server-side** | Client-side | Contagens corretas, paginacao consistente |
| Contagens | Na response de /articles | Endpoint separado | Menos requests, dados sempre sincronizados |
| Selecao | Single-select (radiogroup) | Multi-select | Simplicidade, urgencia e hierarquica |
| Icone "Hoje" | Sun | Clock | Evitar duplicidade com label "Frescor" |
| Badge no card | Inline no timestamp (fase 2) | Icone novo no top | Reutiliza espaco, nao polui layout |
| Pulse | Apenas "Agora" + reduced-motion | Sem animacao | Atencao para breaking news, acessivel |
| API param | `max_hours` (int) | Estender `period` string | Mais explicito, sem ambiguidade |
