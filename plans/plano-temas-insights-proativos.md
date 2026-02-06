# Plano: Experiência Proativa de Temas com Insights de IA

## Resumo Executivo

Criar uma experiência onde o **sistema guia proativamente o redator**, indicando exatamente o que fazer para criar uma excelente matéria. A interface terá:

1. **Lista compacta de temas na SIDEBAR ESQUERDA** - Decisão rápida de qual tema trabalhar
2. **Modal de Insights** - Ao clicar em tema urgente, mostra ângulos, matérias e guia de ação

### Decisões do Usuário
- **Geração de IA:** Híbrida (pré-processa A, sob demanda B/C)
- **Posição da Lista:** Sidebar esquerda (substitui/complementa TrendsSidebar)

---

## ESCOPO DESTA IMPLEMENTAÇÃO

### FASE 1 - FRONTEND (Esta Implementação)
- Todos os componentes visuais com **mock data**
- Lista compacta de temas
- Modal de insights completo
- Estados de loading, error, empty
- Responsividade e acessibilidade
- Hook preparado para integração futura

### FASE 2 - BACKEND (Planejamento Futuro)
Itens que precisarão ser planejados depois:
- [ ] Endpoint `/api/semantic-themes/{id}/insights`
- [ ] Serviço de geração de insights com IA (Claude/OpenAI)
- [ ] Estratégia híbrida de cache (pré-processado A, sob demanda B/C)
- [ ] Timer para pré-processamento de temas classe A
- [ ] Tabela `theme_insights` no banco de dados
- [ ] Prompt engineering para geração de ângulos e insights
- [ ] Rate limiting e custo de API IA

---

## 1. Lista Compacta de Temas (Sidebar Esquerda)

> **Localização:** Substitui/integra com `TrendsSidebar.jsx` existente na sidebar esquerda da RedacaoPage

### Layout ASCII

```
┌─────────────────────────────────────────────────┐
│  EM ALTA                       [↻] [⏸]         │
├─────────────────────────────────────────────────┤
│  [A] 82  Lula faz pronunciam...    URGENTE     │
│  [A] 78  Dólar bate recorde...     URGENTE     │
│  [A] 75  STF decide sobre...       URGENTE     │
├─────────────────────────────────────────────────┤
│  [B] 65  Flamengo vence final...               │
│  [B] 52  Reforma tributária...                 │
│  [B] 45  Clima extremo no Sul                  │
├─────────────────────────────────────────────────┤
│  [C] 35  Feira do livro SP...      MONIT.      │
│  [C] 28  Novo filme brasileiro                 │
└─────────────────────────────────────────────────┘
│   A: 3  │  B: 3  │  C: 2  │  Total: 8          │
└─────────────────────────────────────────────────┘
```

### Estrutura do Item Compacto

```jsx
<li className="compact-theme-item flex items-center gap-3 py-2.5 px-3 hover:bg-gray-50 cursor-pointer">
  {/* Badge classificação */}
  <span className="classification-badge w-6 h-6 rounded-full bg-green-500 text-white text-xs font-bold flex items-center justify-center">
    {classification}
  </span>

  {/* Score */}
  <span className="score w-8 text-sm font-bold tabular-nums text-tmc-orange">
    {score}
  </span>

  {/* Nome truncado */}
  <span className="name flex-1 text-sm text-dark-gray truncate">
    {theme.name}
  </span>

  {/* Badge urgência (condicional) */}
  {score >= 75 && (
    <span className="urgency-badge text-[10px] font-bold bg-tmc-orange text-white px-2 py-0.5 rounded animate-pulse">
      URGENTE
    </span>
  )}
</li>
```

### Interações

| Ação | Comportamento |
|------|---------------|
| Hover | Tooltip com preview de insights |
| Click | Abre ThemeInsightsModal |
| Duplo-click | Seleciona tema e filtra artigos |
| Enter/Space | Abre modal (acessibilidade) |

---

## 2. Modal de Insights do Tema (ThemeInsightsModal)

### Layout ASCII Completo

```
┌══════════════════════════════════════════════════════════════════════════════┐
│                                                                        [X]   │
├══════════════════════════════════════════════════════════════════════════════┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  [A] URGENTE   Score: 82/100                             EMERGENTE    │  │
│  │  "Lula faz pronunciamento sobre economia"                              │  │
│  │  15 matérias  •  8 nas últimas 24h  •  ↑ trending                     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ POR QUE ESTE TEMA É IMPORTANTE AGORA? ────────────────────────────────┐  │
│  │                                                                        │  │
│  │  O presidente fez um pronunciamento inesperado sobre medidas           │  │
│  │  econômicas em horário nobre. Todas as grandes emissoras               │  │
│  │  interromperam programação.                                            │  │
│  │                                                                        │  │
│  │  JANELA DE OPORTUNIDADE: Próximas 4-6 horas                            │  │
│  │  Antes dos jornais impressos fecharem suas edições de amanhã.          │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ ÂNGULOS SUGERIDOS ───────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │ * ÂNGULO RECOMENDADO                                             │  │  │
│  │  │                                                                   │  │  │
│  │  │   O impacto no bolso do brasileiro                               │  │  │
│  │  │   Como as medidas afetam o dia-a-dia da população               │  │  │
│  │  │   Dificuldade: Fácil  •  Alto engajamento esperado              │  │  │
│  │  │                                              [Usar este ângulo]  │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  ┌────────────────────┐  ┌────────────────────┐                      │  │
│  │  │ Reação do mercado  │  │ Contexto político  │                      │  │
│  │  │ Dólar, bolsa...    │  │ Por que agora...   │                      │  │
│  │  │ Média              │  │ Difícil            │                      │  │
│  │  └────────────────────┘  └────────────────────┘                      │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ TOP 3 MATÉRIAS DO TEMA ──────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  [favicon] #1 - G1                                                    │  │
│  │  "Lula anuncia pacote de medidas econômicas"                          │  │
│  │  Score: 92  •  Há 2h  •  Útil para: fatos principais                  │  │
│  │  [ ] Usar como fonte                                                  │  │
│  │                                                                        │  │
│  │  [favicon] #2 - Folha                                                 │  │
│  │  "Análise: O que muda na economia com novo pacote"                    │  │
│  │  Score: 85  •  Há 3h  •  Útil para: contexto                          │  │
│  │  [ ] Usar como fonte                                                  │  │
│  │                                                                        │  │
│  │  [favicon] #3 - Estadão                                               │  │
│  │  "Mercado reage com volatilidade após anúncio"                        │  │
│  │  Score: 78  •  Há 1h  •  Útil para: reações                           │  │
│  │  [ ] Usar como fonte                                                  │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─ O QUE VOCÊ DEVE FAZER ───────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  [ ] 1. Leia as 3 matérias selecionadas acima                         │  │
│  │  [ ] 2. Identifique citações dos principais envolvidos                │  │
│  │  [ ] 3. Escolha um ângulo diferenciado                                │  │
│  │  [ ] 4. Adicione contexto local (se aplicável)                        │  │
│  │                                                                        │  │
│  │  DICA: O ângulo "impacto no bolso" tem maior potencial de             │  │
│  │  engajamento baseado em temas similares anteriores.                   │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
├══════════════════════════════════════════════════════════════════════════════┤
│  [Ver todas as matérias]              [ CRIAR MATÉRIA COM ESTE TEMA ]        │
└══════════════════════════════════════════════════════════════════════════════┘
```

---

## 3. Estrutura de Componentes

### Novos Componentes a Criar

```
tmc-redacao/src/components/
├── themes/
│   ├── ThemeInsightsModal/
│   │   ├── index.jsx                    # Container com focus trap
│   │   ├── ThemeHeader.jsx              # Seção header (classificação, score)
│   │   ├── AIInsightsSection.jsx        # "Por que é importante agora?"
│   │   ├── SuggestedAngles.jsx          # Grid de ângulos sugeridos
│   │   ├── AngleCard.jsx                # Card individual de ângulo
│   │   ├── TopArticlesSection.jsx       # Top 3 matérias
│   │   ├── ArticlePreviewCard.jsx       # Preview de artigo com checkbox
│   │   └── ActionGuideSection.jsx       # Checklist "O que você deve fazer"
│   │
│   ├── CompactThemeList.jsx             # Lista compacta (substitui TrendsSidebar)
│   └── CompactThemeItem.jsx             # Item individual compacto
│
└── hooks/
    └── useThemeInsights.js              # Hook para buscar insights via API
```

### Reutilização de Componentes Existentes

| Componente | Arquivo | Reutilização |
|------------|---------|--------------|
| Focus trap pattern | `ConfirmDialog.jsx:17-68` | Copiar lógica de focus trap |
| UrgencyBadge | `ThemeCard.jsx:89-104` | Usar diretamente no header |
| ScoreDisplay | `ThemeCard.jsx:114-146` | Usar diretamente no header |
| URGENCY_LEVELS config | `ThemeCard.jsx:13-47` | Importar constantes |
| getFaviconUrl | `ThemeCard.jsx:76-80` | Usar para ícones de fonte |

---

## 4. Mock Data para Frontend

> **Nota:** O backend será planejado na Fase 2. Por ora, usamos mock data realista.

### Hook useThemeInsights com Mock

```javascript
// src/hooks/useThemeInsights.js

const MOCK_INSIGHTS = {
  // Simulação de delay de API
  delay: 800,

  // Dados mock realistas
  data: {
    insights: {
      whyImportant: "O presidente fez um pronunciamento inesperado sobre medidas econômicas...",
      context: "Todas as grandes emissoras interromperam programação...",
      timingWindow: {
        urgency: "high",
        hoursRemaining: 6,
        reason: "Antes dos jornais impressos fecharem suas edições"
      }
    },
    suggestedAngles: [
      {
        id: "angle-1",
        title: "O impacto no bolso do brasileiro",
        description: "Como as medidas afetam o dia-a-dia da população",
        difficulty: "easy",
        isRecommended: true,
        reasoning: "Maior alcance e engajamento esperado"
      },
      // ... mais ângulos
    ],
    actionChecklist: [
      { id: 1, text: "Leia as 3 matérias selecionadas", priority: "high" },
      { id: 2, text: "Identifique citações principais", priority: "medium" },
      // ...
    ],
    proTip: "O ângulo 'impacto no bolso' tem maior potencial de engajamento..."
  }
};
```

### Contrato de API (para Fase 2)

```javascript
{
  // Dados do tema (já existentes)
  theme: {
    id, name, slug, classification, score,
    articleCount, recentArticleCount, trend, isEmergent
  },

  // NOVOS: Insights gerados por IA
  insights: {
    whyImportant: "Texto explicando a importância...",
    context: "O que está acontecendo agora...",
    timingWindow: {
      urgency: "high" | "medium" | "low",
      hoursRemaining: 6,
      reason: "Antes dos jornais impressos fecharem..."
    }
  },

  // NOVOS: Ângulos sugeridos
  suggestedAngles: [
    {
      id: "angle-1",
      title: "O impacto no bolso do brasileiro",
      description: "Como as medidas afetam o dia-a-dia...",
      difficulty: "easy" | "medium" | "hard",
      isRecommended: true,
      reasoning: "Maior alcance e engajamento esperado..."
    }
  ],

  // Top artigos (já existente, enriquecido)
  topArticles: [
    {
      ...articleData,
      relevanceNote: "Útil para: fatos principais",
      highlightedQuotes: ["citação 1", "citação 2"]
    }
  ],

  // NOVO: Checklist de ações
  actionChecklist: [
    { id: 1, text: "Leia as 3 matérias selecionadas", priority: "high" },
    { id: 2, text: "Identifique citações dos principais envolvidos", priority: "medium" },
    { id: 3, text: "Escolha um ângulo diferenciado", priority: "high" },
    { id: 4, text: "Adicione contexto local (se aplicável)", priority: "low" }
  ],

  // NOVO: Dica contextual
  proTip: "O ângulo 'impacto no bolso' tem maior potencial de engajamento..."
}
```

### Função Frontend (preparada para integração futura)

```javascript
// src/hooks/useThemeInsights.js

export function useThemeInsights(themeId) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!themeId) return;

    setLoading(true);

    // MOCK: Simula delay de API
    // TODO Fase 2: Substituir por chamada real
    setTimeout(() => {
      setData(generateMockInsights(themeId));
      setLoading(false);
    }, 800);
  }, [themeId]);

  return { data, loading, error, refetch };
}
```

---

## 5. Estados do Modal

### Loading State

```
┌────────────────────────────────────────────────┐
│  [Skeleton header]                             │
│  [Skeleton badge] [Skeleton text...........]   │
├────────────────────────────────────────────────┤
│  Gerando insights com IA...                    │
│  [████████████░░░░░░░░░] 60%                   │
├────────────────────────────────────────────────┤
│  [Skeleton card 1]                             │
│  [Skeleton card 2]                             │
│  [Skeleton card 3]                             │
└────────────────────────────────────────────────┘
```

### Error State

```
┌────────────────────────────────────────────────┐
│  Não foi possível carregar insights            │
│                                                │
│  O tema ainda está disponível. Você pode:      │
│  • [Ver todas as matérias] manualmente         │
│  • [Tentar novamente] recarregar               │
└────────────────────────────────────────────────┘
```

---

## 6. Fluxo de Interação

```
┌─────────────────┐
│  RedacaoPage    │
│  (Lista Temas)  │
└────────┬────────┘
         │ Click em tema urgente
         ▼
┌─────────────────┐     Fetch API
│ ThemeInsights   │ ────────────────► /api/themes/{id}/insights
│    Modal        │ ◄────────────────
└────────┬────────┘     JSON Response
         │
    ┌────┴────┐
    ▼         ▼
[Seleciona  [Ver todas
 ângulo]    matérias]
    │         │
    ▼         ▼
┌─────────────────┐
│ Seleciona       │
│ artigos/fontes  │
└────────┬────────┘
         │ Click "Criar Matéria"
         ▼
┌─────────────────┐
│  CriarPage      │  (fluxo existente)
│  (texto-base)   │
└─────────────────┘
```

---

## 7. Arquivos a Criar/Modificar (Frontend)

### Novos Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `components/themes/ThemeInsightsModal/index.jsx` | Container principal do modal |
| `components/themes/ThemeInsightsModal/ThemeHeader.jsx` | Header com classificação e score |
| `components/themes/ThemeInsightsModal/AIInsightsSection.jsx` | Seção "Por que é importante" |
| `components/themes/ThemeInsightsModal/SuggestedAngles.jsx` | Grid de ângulos sugeridos |
| `components/themes/ThemeInsightsModal/AngleCard.jsx` | Card individual de ângulo |
| `components/themes/ThemeInsightsModal/TopArticlesSection.jsx` | Top 3 matérias |
| `components/themes/ThemeInsightsModal/ArticlePreviewCard.jsx` | Preview de artigo |
| `components/themes/ThemeInsightsModal/ActionGuideSection.jsx` | Checklist de ações |
| `components/themes/CompactThemeList.jsx` | Lista compacta na sidebar |
| `components/themes/CompactThemeItem.jsx` | Item individual da lista |
| `hooks/useThemeInsights.js` | Hook com mock data |
| `data/mockInsights.js` | Dados mock realistas |

### Arquivos a Modificar

| Arquivo | Modificação |
|---------|-------------|
| `components/themes/index.js` | Exportar novos componentes |
| `pages/RedacaoPage.jsx` | Integrar modal e lista compacta |
| `index.css` | Adicionar animações do modal |

---

## BACKEND - Planejamento Futuro (Fase 2)

> Estes itens serão planejados em detalhe após validação do frontend.

### Itens a Planejar

| Item | Descrição |
|------|-----------|
| Endpoint `/api/semantic-themes/{id}/insights` | Retorna insights do tema |
| `ai_insights_service.py` | Serviço de geração com Claude/OpenAI |
| Estratégia de cache híbrida | Pré-processa A, sob demanda B/C |
| Timer de pré-processamento | Job a cada 30min para classe A |
| Tabela `theme_insights` | Schema do banco de dados |
| Prompt engineering | Otimização do prompt para IA |
| Rate limiting | Controle de custo de API |
| Fallback | Comportamento quando IA falha |

---

## 8. Prompt para Geração de Insights (Claude/OpenAI)

```
Você é um editor-chefe de um grande veículo de notícias brasileiro.
Analise o tema jornalístico abaixo e forneça orientações para o redator.

TEMA: {theme.name}
CLASSIFICAÇÃO: {theme.classification} (A=urgente, B=relevante, C=monitorar)
SCORE: {theme.score}/100
ARTIGOS RELACIONADOS:
{top_articles_summary}

Forneça em formato JSON:
1. "whyImportant": Por que este tema é importante agora? (2-3 frases)
2. "context": O que está acontecendo? (contexto editorial)
3. "timingWindow": Janela de oportunidade para publicar
4. "suggestedAngles": 3 ângulos editoriais diferentes, com:
   - title: Título curto do ângulo
   - description: O que abordar
   - difficulty: easy/medium/hard
   - isRecommended: true para o melhor ângulo
5. "proTip": Uma dica prática para o redator

Responda em português do Brasil, tom profissional mas acessível.
```

---

## 9. Responsividade

### Desktop (>1024px)
- Modal: max-width 900px, centered
- Ângulos em grid 3 colunas
- Layout conforme ASCII

### Tablet (768px-1024px)
- Modal: 90% width
- Ângulos em grid 2 colunas
- Seções mantidas

### Mobile (<768px)
- Modal: fullscreen (100vh)
- Seções colapsáveis (accordion)
- Ângulos em scroll horizontal
- CTA fixo no bottom

---

## 10. Verificação

### Como Testar

1. **Lista Compacta**
   - Verificar que todos os temas aparecem com classe/score/nome/badge
   - Hover mostra tooltip
   - Click abre modal

2. **Modal de Insights**
   - Abrir modal de tema classe A (urgente)
   - Verificar loading state enquanto busca insights
   - Verificar todas as 5 seções renderizadas
   - Testar seleção de ângulo
   - Testar checkbox de artigos
   - Clicar "Criar Matéria" e verificar navegação

3. **Estados de Erro**
   - Simular falha de API
   - Verificar que modal mostra fallback gracioso
   - Verificar botão "Tentar novamente"

4. **Acessibilidade**
   - Navegar modal com Tab
   - Fechar com Escape
   - Verificar aria-labels
   - Testar com leitor de tela

5. **Mobile**
   - Testar em viewport 375px
   - Verificar scroll e seções colapsáveis
   - Verificar CTA fixo

---

## 11. Ordem de Implementação (Frontend com Mock)

### Etapa 1 - Fundação (Estrutura)
1. Criar estrutura de pastas `ThemeInsightsModal/`
2. Criar arquivo `data/mockInsights.js` com dados realistas
3. Criar hook `useThemeInsights.js` com mock data
4. Criar container `ThemeInsightsModal/index.jsx` com focus trap

### Etapa 2 - Componentes do Modal
1. `ThemeHeader.jsx` - Reutilizar UrgencyBadge/ScoreDisplay
2. `AIInsightsSection.jsx` - "Por que é importante agora?"
3. `SuggestedAngles.jsx` + `AngleCard.jsx` - Grid de ângulos
4. `TopArticlesSection.jsx` + `ArticlePreviewCard.jsx` - Top 3 matérias
5. `ActionGuideSection.jsx` - Checklist interativo

### Etapa 3 - Lista Compacta
1. `CompactThemeItem.jsx` - Item individual
2. `CompactThemeList.jsx` - Container da lista
3. Integrar na sidebar esquerda (RedacaoPage)

### Etapa 4 - Integração e Estados
1. Conectar click da lista com abertura do modal
2. Implementar loading state com skeleton
3. Implementar error state com retry
4. Implementar empty state

### Etapa 5 - Polish
1. Animações CSS (entrada modal, hover cards)
2. Responsividade (mobile fullscreen, accordion)
3. Acessibilidade (focus trap, aria-labels, keyboard)
4. Testes manuais do fluxo completo

---

## Arquivos Críticos para Referência

- `tmc-redacao/src/components/ui/ConfirmDialog.jsx` - Pattern de modal com focus trap
- `tmc-redacao/src/components/themes/ThemeCard.jsx` - Componentes UrgencyBadge, ScoreDisplay para reutilizar
- `tmc-redacao/src/components/layout/TrendsSidebar.jsx` - Sidebar atual a integrar/substituir
- `tmc-redacao/src/index.css` - Adicionar animações do modal

---

## Mock Data Completo

```javascript
// src/data/mockInsights.js

export const MOCK_INSIGHTS_BY_THEME = {
  // Tema exemplo: Economia
  "theme-economia-001": {
    insights: {
      whyImportant: "O presidente fez um pronunciamento inesperado sobre medidas econômicas em horário nobre. Todas as grandes emissoras interromperam programação para transmitir ao vivo.",
      context: "O anúncio vem em momento de alta do dólar e preocupações com inflação. Economistas já começam a analisar os impactos das medidas propostas.",
      timingWindow: {
        urgency: "high",
        hoursRemaining: 6,
        reason: "Antes dos jornais impressos fecharem suas edições de amanhã"
      }
    },
    suggestedAngles: [
      {
        id: "angle-1",
        title: "O impacto no bolso do brasileiro",
        description: "Como as medidas afetam o dia-a-dia da população. Foque em preços, salários e custo de vida.",
        difficulty: "easy",
        isRecommended: true,
        reasoning: "Maior alcance e engajamento esperado baseado em temas similares"
      },
      {
        id: "angle-2",
        title: "Reação do mercado financeiro",
        description: "Dólar, bolsa e o que esperar para amanhã. Inclua análise de especialistas.",
        difficulty: "medium",
        isRecommended: false,
        reasoning: "Público mais especializado, bom para SEO de longo prazo"
      },
      {
        id: "angle-3",
        title: "O contexto político por trás",
        description: "Por que Lula escolheu este momento para o anúncio. Relação com Congresso e eleições.",
        difficulty: "hard",
        isRecommended: false,
        reasoning: "Requer fontes políticas, ideal para análise aprofundada"
      }
    ],
    topArticles: [
      {
        id: "art-001",
        title: "Lula anuncia pacote de medidas econômicas em pronunciamento",
        source: "G1",
        sourceIcon: "https://www.google.com/s2/favicons?domain=g1.globo.com&sz=32",
        score: 92,
        publishedAt: "2024-01-15T20:30:00Z",
        relevanceNote: "Útil para: fatos principais e citações diretas",
        preview: "O presidente Luiz Inácio Lula da Silva anunciou nesta terça-feira um pacote de medidas econômicas..."
      },
      {
        id: "art-002",
        title: "Análise: O que muda na economia com o novo pacote",
        source: "Folha de S.Paulo",
        sourceIcon: "https://www.google.com/s2/favicons?domain=folha.uol.com.br&sz=32",
        score: 85,
        publishedAt: "2024-01-15T21:15:00Z",
        relevanceNote: "Útil para: contexto econômico e análise",
        preview: "Economistas ouvidos pela Folha avaliam que as medidas terão impacto..."
      },
      {
        id: "art-003",
        title: "Mercado reage com volatilidade após anúncio de Lula",
        source: "Estadão",
        sourceIcon: "https://www.google.com/s2/favicons?domain=estadao.com.br&sz=32",
        score: 78,
        publishedAt: "2024-01-15T21:45:00Z",
        relevanceNote: "Útil para: reações e dados de mercado",
        preview: "O dólar fechou em alta de 1,2% após o pronunciamento presidencial..."
      }
    ],
    actionChecklist: [
      { id: 1, text: "Leia as 3 matérias selecionadas acima", priority: "high" },
      { id: 2, text: "Identifique citações dos principais envolvidos", priority: "medium" },
      { id: 3, text: "Escolha um ângulo diferenciado da concorrência", priority: "high" },
      { id: 4, text: "Adicione contexto local se aplicável", priority: "low" }
    ],
    proTip: "O ângulo 'impacto no bolso' tem maior potencial de engajamento baseado em temas econômicos similares dos últimos 30 dias."
  }
};

// Função para gerar mock baseado em tema
export function generateMockInsights(theme) {
  // Retorna mock específico ou gera um genérico baseado no tema
  return MOCK_INSIGHTS_BY_THEME[theme.id] || generateGenericMock(theme);
}
```
