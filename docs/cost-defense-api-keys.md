# Defesa de Custos — APIs da Ferramenta TMC

> Março 2026 | Câmbio: USD 1 = R$ 5,16
> Baseado em dados de produção (611 chamadas LLM medidas + 56 dias de coleta)
> Cenário base: **1.000 artigos gerados/mês**
> Referência completa: [`cost-analysis-march-2026.md`](./cost-analysis-march-2026.md)

---

## 1. Visão Geral

A Ferramenta TMC utiliza duas APIs externas essenciais:

| API | Provedor | Função na TMC |
|-----|----------|---------------|
| **Anthropic Claude API** | Anthropic (via Azure AI Foundry) | Geração de artigos, fact-checking, classificação, scoring editorial |
| **Exa Search API** | Exa AI | Enriquecimento factual pré-geração (pesquisa web verificada) |

Ambas são **insubstituíveis** no pipeline atual. Sem elas, a ferramenta não gera artigos nem garante qualidade editorial.

---

## 2. Anthropic Claude API

### O que faz

| Modelo | Tarefas | Criticidade |
|--------|---------|:-----------:|
| **Claude Sonnet 4.5/4.6** | Geração de artigos, verificação de claims, enriquecimento, edição | Essencial |
| **Claude Haiku 4.5** | Classificação A/B/C, scoring editorial, nomeação de temas | Essencial |

> Nota: Claude Sonnet 4.6 está disponível com **mesmo preço** ($3/$15 per MTok) e qualidade superior. Migração sem impacto de custo.

### Custo estimado em produção

| Métrica | Valor | Base |
|---------|-------|------|
| Custo por artigo gerado (Sonnet) | **$0.22 / R$ 1,14** | 113 artigos medidos |
| Pipeline RSS — classificação + scoring (Haiku) | **$207/mês / R$ 1.068** | 61K artigos/mês estimado |
| Infraestrutura Azure (SQL, Functions, etc.) | **$22/mês / R$ 114** | Medido |

### Composição por artigo gerado

```
Enriquecimento factual (Sonnet)    $0.009   ██
Geração do texto (Sonnet)          $0.129   ██████████████████████
Verificação de claims (Sonnet)     $0.079   █████████████
CoVe — verificação cruzada         $0.001   ▏
Classificação (Haiku)              $0.000   ▏
Scoring (Haiku)                    $0.003   ▏
                                   ───────
TOTAL Anthropic por artigo         $0.22    (R$ 1,14)
```

### Por que não pode ser cortado

1. **Sem Sonnet** → não há geração de artigos, não há verificação anti-alucinação, não há fact-checking
2. **Sem Haiku** → não há classificação editorial (A/B/C), não há scoring de relevância, artigos chegam sem priorização
3. **O pipeline anti-alucinação** (claim extraction + CoVe + safety gates) é o diferencial competitivo da TMC — sem ele, o produto perde credibilidade editorial
4. **Custo por artigo (R$ 1,14)** é **10-100x mais barato** que alternativas humanas:

```
TMC (IA):         R$  1,14 / artigo
Freelancer:       R$ 13-20 / artigo
Agência:          R$ 80-120 / artigo
```

### Projeção mensal (1.000 artigos)

| Componente | USD | BRL |
|------------|----:|----:|
| Sonnet (geração + verificação) | $220 | R$ 1.135 |
| Sonnet (extras: edição, tópicos, fusão)* | $60 | R$ 310 |
| Haiku (classificação 61K artigos) | $18 | R$ 93 |
| Haiku (scoring 61K artigos) | $184 | R$ 950 |
| Haiku (temas) | $5 | R$ 26 |
| **Total Anthropic** | **$487** | **R$ 2.513** |

> *Extras incluem reserva orçamentária para edições, extração de tópicos e fusão de fontes. Valor projetado com margem conservadora para absorver variação de uso.

---

## 3. Exa Search API

### O que faz

Exa é a camada de **enriquecimento factual** — busca fontes verificadas na web antes da geração do artigo para:

- Fornecer contexto factual atualizado ao LLM
- Reduzir alucinações (o LLM tem fatos reais para referenciar)
- Alimentar o pipeline de verificação de claims (CoVe)

### Pricing ([exa.ai/pricing](https://exa.ai/pricing))

| Operação | Custo |
|----------|------:|
| Search + Contents (até 10 resultados) | **$0.007/busca** ($7/1K requests) |
| Resultados adicionais (>10) | $0.001/página adicional |
| Exa Deep (pesquisa avançada) | $0.012/request |

### Uso no TMC

Cada artigo gerado faz **2-13 buscas Exa** dependendo da profundidade de verificação:

| Cenário | Buscas/artigo | Custo/artigo | Custo 1.000 art/mês |
|---------|:---:|---:|---:|
| Típico (2 buscas) | 2 | $0.014 / R$ 0,07 | $14 / R$ 72 |
| Médio (7 buscas) | 7 | $0.049 / R$ 0,25 | $49 / R$ 253 |
| Verificação completa (13 buscas) | 13 | $0.091 / R$ 0,47 | $91 / R$ 470 |

> Preço por busca: $0.007 (search + contents bundled, até 10 resultados). Fonte: [exa.ai/pricing](https://exa.ai/pricing)

### Por que não pode ser cortado

1. **Sem Exa** → o LLM gera artigos baseado apenas no texto-fonte RSS, sem contexto factual atualizado
2. **Aumento de alucinações** → sem enriquecimento, o pipeline de fact-checking tem menos material para verificar claims, resultando em mais artigos bloqueados ou com risco alto
3. **Custo marginal** → Exa representa apenas **~9%** do custo total mensal ($49 de $558), ou **R$ 0,25/artigo** no cenário médio
4. **ROI direto** → cada R$ 0,25 gasto em Exa evita potencialmente um artigo inteiro sendo bloqueado pelo safety gate (R$ 1,14 desperdiçados em geração Sonnet)

### Projeção mensal

| Volume | Custo Exa (médio, 7 buscas/art) |
|--------|------------------:|
| 300 artigos/mês | $14.70 / R$ 76 |
| **1.000 artigos/mês** | **$49 / R$ 253** |
| 2.000 artigos/mês | $98 / R$ 506 |

> Fontes: [Exa Pricing](https://exa.ai/pricing) | [Exa Pricing Update](https://exa.ai/docs/changelog/pricing-update)

---

## 4. Custo Total Consolidado

### Cenário base: 1.000 artigos/mês

| API | Mensal USD | Mensal BRL | % do Total |
|-----|---:|---:|:---:|
| **Anthropic Claude** | $487 | R$ 2.513 | **87%** |
| **Exa Search** | $49 | R$ 253 | **9%** |
| **Infraestrutura Azure** | $22 | R$ 114 | **4%** |
| | | | |
| **TOTAL** | **$558** | **R$ 2.879** | **100%** |

> Margem de segurança (+35%): até **R$ 3.890/mês** considerando variação cambial e sazonalidade.

### Custo anual

| Período | USD | BRL |
|---------|----:|----:|
| Mensal | $558 | R$ 2.879 |
| Anual | $6.696 | R$ 34.551 |
| Anual (com margem 35%) | $9.040 | R$ 46.646 |

---

## 5. Comparativo de Mercado

```
CUSTO MENSAL (1.000 artigos com verificação editorial):

TMC (IA completa):     R$  2.880 — 3.890
                       ████████████

3 Jornalistas CLT:     R$ 12.000 — 18.000   (produção equivalente, sem verificação auto)
                       ████████████████████████████████████████████████

Agência terceirizada:  R$ 80.000             (1.000 × R$ 80/artigo)
                       ██████████████████████████████████████████████████████████████████████████████████████
```

**A TMC entrega 1.000 artigos verificados por mês pelo custo de ~24% de 3 jornalistas CLT, ou ~4% de uma agência.**

---

## 6. Custo por Artigo (com diluição do fixo)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ARTIGOS/MÊS   │  Mensal BRL (faixa)     │  Por artigo (custo total)   │
├─────────────────┼─────────────────────────┼─────────────────────────────┤
│  300            │  R$ 1.691 — R$ 2.283    │  R$  5,64 —  7,61          │
│  500            │  R$ 2.030 — R$ 2.741    │  R$  4,06 —  5,48          │
│  ▶ 1.000       │  R$ 2.880 — R$ 3.890    │  R$  2,88 —  3,89          │
│  2.000          │  R$ 4.577 — R$ 6.179    │  R$  2,29 —  3,09          │
└─────────────────┴─────────────────────────┴─────────────────────────────┘

  Fórmula: Fixo $229 (Haiku pipeline $207 + infra $22)
         + N × $0.329/artigo ($0.22 Sonnet + $0.049 Exa + $0.06 extras)
  O custo fixo (~R$ 1.182) é diluído conforme o volume aumenta.
  A 1.000 artigos, o custo total por artigo cai para R$ 2,88.
```

---

## 7. Resumo Executivo

| | Anthropic Claude | Exa Search |
|---|---|---|
| **Custo mensal (1.000 art)** | R$ 2.513 (87%) | R$ 253 (9%) |
| **Função** | Geração, verificação, classificação | Enriquecimento factual |
| **Substituível?** | Não | Não (sem alternativa equivalente) |
| **Se cortado** | Ferramenta para de funcionar | Qualidade cai, alucinações aumentam |
| **ROI** | 10-100x mais barato que humano | Evita desperdício de geração |

### Investimento vs. Retorno

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║   Investimento mensal total:    R$ 2.880 — R$ 3.890                   ║
║   Artigos entregues:            1.000 / mês                            ║
║   Custo por artigo:             R$ 2,88 — R$ 3,89                     ║
║                                                                        ║
║   Equivalente humano:           R$ 80.000 / mês (agência)             ║
║   Economia:                     R$ 76.000 — 77.000 / mês (96-97%)    ║
║                                                                        ║
║   Investimento anual:           R$ 34.551 — R$ 46.646                 ║
║   Economia anual vs agência:    R$ 913.000 — 925.000                  ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**Recomendação: manter ambas as APIs. O custo combinado (R$ 2.879/mês) para 1.000 artigos verificados por mês é altamente competitivo e essencial para o funcionamento do produto.**

---

*Baseado em dados de produção medidos entre 9-11 de março de 2026 (611 chamadas LLM bem-sucedidas, 113 artigos gerados, 56 dias de logs de coleta RSS). Análise completa em [`cost-analysis-march-2026.md`](./cost-analysis-march-2026.md).*

---

### Fontes de Preço (verificadas em março 2026)

- [Anthropic Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — Sonnet $3/$15, Haiku $1/$5 per MTok
- [Exa AI Pricing](https://exa.ai/pricing) — $7/1K requests (search + contents bundled)
- [Exa Pricing Update](https://exa.ai/docs/changelog/pricing-update) — Pricing changelog
- [Azure SQL Database Pricing](https://azure.microsoft.com/en-us/pricing/details/azure-sql-database/single/) — S0 = $14.72/month
