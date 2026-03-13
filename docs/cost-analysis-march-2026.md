# TMC Application - Cost Analysis (March 2026)

> Generated: 2026-03-11 | **Updated: 2026-03-11 (deep review by 5 specialized agents)**
> **Validated against production database** (611 LLM calls + 56 days of collection_logs)
> Exchange Rate: 1 USD = R$5.16 (March 2026)
> Provider: Anthropic Direct API or Google Vertex AI (Global) or Azure AI Foundry

---

## Executive Summary

| Metric | Value | Confidence |
|--------|-------|:----------:|
| **Cost per generated article (Sonnet)** | **$0.22** | MEASURED |
| **Fixed monthly (RSS pipeline + infra)** | **$229 / R$1,182** | Mixed |
| **Per generated article (marginal)** | **$0.24 / R$1.24** | MEASURED |
| **Monthly (300 gen, all scored, real-time)** | **$301 / R$1,553** | Mixed |
| **Fixed infrastructure** | **$22/month** | MEASURED |
| **Haiku scoring (61K articles/month)** | **$184/month** | ESTIMATED |
| **RSS articles collected/day** | **2,049** | MEASURED (collection_logs, 56 days) |

> **"MEASURED"** = derived from production database (611 successful LLM calls, 1,386 total; 56 days of collection_logs)
> **"ESTIMATED"** = Haiku 4.5 never ran in production (772/772 calls failed: DeploymentNotFound). Token counts estimated from source code analysis of prompt templates.

### Critical Issues in Production

| Issue | Impact |
|-------|--------|
| **Haiku 4.5 NOT DEPLOYED** on Azure AI Foundry | 772 failed calls (100%). No scoring, no classification running. |
| **Stale Haiku pricing in code** (`llm_service.py:1798`) | Uses $0.80/$4.00, should be $1.00/$5.00 (25% underreport) |
| **Collection volume was underestimated** | `collected_articles` showed 1,268/day (rolling 4-day window). `collection_logs` (56 active days) shows **2,049/day** — 61% higher. |

---

## 1. Model Pricing

### 1.1 Standard Pricing (Anthropic Direct API or Vertex AI Global)

| Model | Input / MTok | Output / MTok |
|-------|------------:|--------------:|
| **Claude Sonnet 4.5** | $3.00 | $15.00 |
| **Claude Haiku 4.5** | $1.00 | $5.00 |

### 1.2 Batch API Pricing

| Provider | Batch Discount | Effective Sonnet In | Effective Sonnet Out | Effective Haiku In | Effective Haiku Out |
|----------|:-:|---:|---:|---:|---:|
| **Anthropic Direct API** | **-50%** | $1.50 | $7.50 | $0.50 | $2.50 |
| Vertex AI (requires **regional** endpoint) | -50% + 10% premium = **-45%** | $1.65 | $8.25 | $0.55 | $2.75 |

> **IMPORTANT**: Vertex AI Batch API requires **regional endpoints**, which carry a +10% premium over global. The effective batch discount on Vertex AI is **45%** (not 50%). Anthropic Direct API gives the full 50% batch discount.
> **Recommendation: Use Anthropic Direct API for batch processing.**
> Sources: [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing), [Vertex AI Regional Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)

### 1.3 Prompt Caching (stacks with batch)

| Cache Type | Cost Multiplier | Notes |
|------------|:-:|---|
| Cache write (5-min TTL) | 1.25× input | First request pays write cost |
| Cache write (1-hour TTL) | 2.0× input | Higher write cost, longer cache |
| Cache read (hit) | **0.1×** input | 90% savings on cached tokens |

> Scoring system prompt (~900 tokens) repeats identically across all scoring calls. With caching: save ~90% on system prompt tokens for subsequent calls within TTL window.

---

## 2. Production Data (March 9-11, 2026 — 2.5 Days)

### 2.1 Successful LLM Calls (MEASURED)

| Task Type | Model | Calls | Avg Input | Avg Output | Total Cost |
|-----------|-------|------:|----------:|-----------:|-----------:|
| article_generation | Sonnet 4.5 | 245 | 11,084 | 1,754 | $14.60 |
| claim_extraction | Sonnet 4.5 | 235 | 4,609 | 1,616 | $8.95 |
| enrichment_extraction | Sonnet 4.5 | 113 | 1,700 | 228 | $0.96 |
| article_edit | Sonnet 4.5 | 6 | 4,456 | 1,842 | $0.25 |
| topic_extraction | Sonnet 4.5 | 7 | 1,171 | 654 | $0.09 |
| story_fusion | Sonnet 4.5 | 1 | 3,617 | 1,907 | $0.04 |
| cove_qa | Sonnet 4.5 | 2 | 974 | 336 | $0.02 |
| cove_verdict | Sonnet 4.5 | 2 | 622 | 175 | $0.01 |
| **TOTAL** | | **611** | | | **$24.91** |

> Math verification: 11,084 × $3/1M + 1,754 × $15/1M = $0.0333 + $0.0263 = **$0.0596/gen call** ✓
> Cross-check: $24.91 total / 113 unique articles = **$0.2204/article** (Sonnet only) ✓

### 2.2 Failed Calls

| Task Type | Model | Failures | Error |
|-----------|-------|------:|-------|
| classification | Haiku 4.5 | 522 | `DeploymentNotFound` |
| scoring | Haiku 4.5 | 250 | `DeploymentNotFound` |
| claim_extraction | Sonnet 4.5 | 2 | `RateLimitReached` |
| article_generation | Sonnet 4.5 | 1 | `RateLimitReached` |

### 2.3 Pipeline Ratios (MEASURED)

| Metric | Value | Derivation | Confidence |
|--------|------:|------------|:----------:|
| Unique articles processed | 113 | = enrichment_extraction calls (1 per article) | MEASURED |
| Generation calls per article | 2.17 | = 245 gen / 113 articles (quality loop retries) | MEASURED |
| Claim extractions per article | 2.08 | = 235 / 113 (1 per gen attempt) | MEASURED |
| CoVe trigger rate | 1.8% | = 2 / 113 | MEASURED |
| **RSS articles collected per day** | **2,049** | = **collection_logs** (114,764 articles ÷ 56 active days) | **MEASURED** |
| Articles per 15-min collection | ~34 | = 2,049 / (96 runs × 0.63 activity ratio) | MEASURED |
| Active RSS sources | 27 | from `sources` table | MEASURED |

> **Volume correction**: Previous estimate of 1,268/day came from `collected_articles` table which has a rolling 72h deletion window. The `collection_logs` table preserves historical data across 56 active days, showing **2,049/day** — **61% higher** than the rolling-window estimate. All downstream Haiku cost calculations use the corrected 2,049/day figure.

---

## 3. Cost Per Generated Article

### 3.1 Breakdown (MEASURED Sonnet + ESTIMATED Haiku)

| Step | Calls/article | Cost/call | Cost/article | Confidence |
|------|-----:|-----:|-----:|-----------:|
| Enrichment extraction (Sonnet) | 1.00 | $0.0085 | $0.0085 | MEASURED |
| Article generation (Sonnet) | 2.17 | $0.0596 | $0.1293 | MEASURED |
| Claim extraction (Sonnet) | 2.08 | $0.0381 | $0.0792 | MEASURED |
| CoVe QA + verdict (Sonnet) | 0.04 | $0.0063 | $0.0002 | MEASURED |
| Exa API searches | 2-13 | $0.0070 | $0.0140-$0.091 | ESTIMATED |
| Classification (Haiku) | 1.0 | $0.0003 | $0.0003 | ESTIMATED |
| Scoring (Haiku) | 1.0 | $0.0030 | $0.0030 | ESTIMATED |
| **TOTAL PER ARTICLE** | | | **$0.2345** | |

**Rounded: ~$0.22/article (Sonnet measured) + ~$0.02-$0.10 (Exa + Haiku estimated) = $0.24-$0.32/article**
**Typical (2 Exa calls): $0.24/article | Full verification (13 Exa calls): $0.32/article**

> Haiku scoring estimate: 5,000 chars content (scoring_service.py:372) ÷ 3.5 chars/tok = ~1,430 tokens + ~500 system prompt + ~70 template = **~2,000 input tokens**. Output: ~200 tokens. Cost: 2,000 × $1/MTok + 200 × $5/MTok = **$0.003**.
> **This is the only significant estimated number in per-article cost. ±30% variance = $0.002-$0.004.**

---

## 4. Infrastructure (MEASURED — Fixed Monthly)

| Service | Tier | Monthly |
|---------|------|--------:|
| Azure SQL Database | **S0** (10 DTU) | **$14.72** |
| Azure Functions | Consumption (free tier) | $0.00 |
| Azure Application Insights | Pay-as-you-go | ~$1.50 |
| Azure Key Vault | Standard | $0.03 |
| Azure DNS | 1 zone | $0.50 |
| Azure OpenAI (embeddings) | text-embedding-3-small | $0.61 |
| Frontend hosting | Vercel Free / Azure SWA | ~$2.50 |
| Domain (.com.br) | Registro.br | $0.65 |
| Network egress | Azure | ~$1.50 |
| **TOTAL** | | **~$22** |

> Azure SQL confirmed S0 via production DB query. DB size: 5.67 GB.

---

## 5. RSS Pipeline Cost (ESTIMATED — Haiku Never Ran)

**61,470 articles/month** (2,049/day × 30). Collection every 15 min, ~34 articles/run.

| Step | Model | Calls/month | Input tok | Output tok | Cost/call | Monthly |
|------|-------|----------:|------:|-------:|----------:|--------:|
| Batch classification | Haiku | ~61,470 | ~125 | ~40 | $0.0003 | $18 |
| Editorial scoring (all) | Haiku | ~61,470 | ~2,000 | ~200 | $0.0030 | $184 |
| Theme naming | Haiku | ~3,000 | ~800 | ~200 | $0.0018 | $5 |
| **TOTAL (all scored)** | | | | | | **$207** |

> **All Haiku numbers are estimates.** Scoring could range $130-240/month depending on actual token counts (±30%).
> Scoring processes up to 50 articles/run every 10 min (scoring_calculator.py:18).

### Scoring Volume Note

All 61,470 articles/month receive full LLM scoring to preserve editorial quality. The Batch API (-50%) is the primary cost reduction lever — no quality tradeoff.

> The scoring_calculator timer (every 10 min, max 50/run) serves as a backfill safety net for articles missed by inline scoring.
> Heuristic fallback exists at `scoring_service.py:219-279` and activates automatically if LLM is unavailable.

---

## 6. Monthly Cost Scenarios (300 Generated Articles)

### Monthly Cost (All Articles Scored, Real-Time)

| Cost Center | Calculation | USD |
|-------------|------------|----:|
| Sonnet generation pipeline | 300 × $0.22 | $66 |
| Sonnet on-demand extras | est. edits, topics, fusion | $18 |
| Exa Search API | 300 articles × ~7 calls avg × $0.007 | $10 |
| Haiku classification (all 61K) | 61K × $0.0003 | $18 |
| Haiku scoring (all 61K) | 61K × $0.003 | $184 |
| Haiku theme naming | 3K × $0.0018 | $5 |
| Infrastructure | fixed | $22 |
| **TOTAL (fixed)** | pipeline + infra | **$229** |
| **TOTAL (300 gen)** | fixed + 300 × $0.24 | **$301** |
| **TOTAL BRL (300 gen)** | × 5.16 | **R$1,553** |

> All LLM calls are real-time (synchronous). Batch API is not used because scoring, classification, and generation all require immediate responses — no article can be presented without a score.
> The fixed cost ($229/month) runs regardless of generation volume. Each generated article adds only ~$0.24 marginal cost.

---

## 7. Budget Summary for Client

### Monthly Operating Cost

| Component | USD | BRL |
|-----------|----:|----:|
| Fixed (RSS pipeline + infra) | $229 | R$1,182 |
| Variable (300 articles × $0.24) | $72 | R$372 |
| **TOTAL (300 articles/month)** | **$301** | **R$1,553** |

> **Marginal cost per article: $0.24 (R$1,24).** The fixed cost runs regardless of generation volume.

### Annual Projection (300 articles/month)

| Period | USD | BRL |
|--------|---:|---:|
| Monthly | $301 | R$1,553 |
| **Annual** | **$3,612** | **R$18,638** |

---

## Custo Mensal Estimado — Ferramenta TMC

> Referência: Março 2026 | Câmbio: USD 1 = R$ 5,16
> Dados validados contra banco de dados de produção (611 chamadas LLM + 56 dias de collection_logs)
> Cenário: 300 artigos gerados/mês | **61.000 artigos coletados/mês** (27 fontes RSS, 2.049/dia medidos)
> Valores apresentados em faixas para contemplar variação cambial, sazonalidade e margem operacional

### Resumo Executivo

```
╔══════════════════════════════════════════════════════════════════════════╗
║                   CUSTO MENSAL ESTIMADO — TMC                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║   Custo fixo (pipeline RSS + infra):                                   ║
║          R$ 1.180 — R$ 1.600 / mês     (USD 229 — 310)                ║
║                                                                        ║
║   Custo por artigo gerado:                                             ║
║          R$ 1,24 — R$ 1,70 / artigo    (USD 0,24 — 0,33)              ║
║                                                                        ║
║   Exemplo com 300 artigos/mês:                                         ║
║          R$ 1.550 — R$ 2.100 / mês     (USD 301 — 409)                ║
║                                                                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║   Projeção Anual (300 art/mês):  R$ 18.600 — R$ 25.200 / ano          ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Composição Mensal Detalhada

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  CUSTO FIXO (independe do volume de geração)                            │
│  ─────────────────────────────────────────────────────────────────────── │
│  ITEM DE CUSTO                              │  BRL (faixa estimada)     │
├─────────────────────────────────────────────┼───────────────────────────┤
│  IA — Pipeline RSS (Claude Haiku)           │                           │
│    Classificação (61K artigos/mês)          │   R$   90  —  R$  125    │
│    Scoring editorial completo (61K, IA)     │   R$  950  —  R$ 1.240   │
│    Nomeação de temas                        │   R$   25  —  R$   35    │
│                                             │                           │
│  Infraestrutura                             │                           │
│    Azure SQL Database (S0)                  │   R$   75  —  R$   80    │
│    Azure Functions + DNS + outros           │   R$   35  —  R$   50    │
│                                             │                           │
│  Subtotal fixo                              │ R$ 1.180  — R$ 1.530     │
│                                                                          │
│  CUSTO VARIÁVEL (por artigo gerado)                                     │
│  ─────────────────────────────────────────────────────────────────────── │
│  ITEM DE CUSTO                              │  BRL (por artigo)         │
├─────────────────────────────────────────────┼───────────────────────────┤
│  IA — Geração (Claude Sonnet)               │                           │
│    Geração + verificação anti-alucinação    │   R$ 1,14                │
│    Extras (edição, tópicos, fusão)          │   R$ 0,31 (média)        │
│  Pesquisa Web — Exa API                     │   R$ 0,07 — 0,47        │
│                                             │                           │
│  Subtotal por artigo                        │ R$ 1,24 — 1,70           │
│                                                                          │
│  EXEMPLO: 300 artigos/mês                                               │
│  ─────────────────────────────────────────────────────────────────────── │
├─────────────────────────────────────────────┼───────────────────────────┤
│  Fixo                                       │ R$ 1.180  — R$ 1.530     │
│  Variável (300 × R$ 1,24-1,70)             │ R$   370  —  R$  510     │
│                                             │                           │
│  TOTAL MENSAL (300 artigos)                 │ R$ 1.550  — R$ 2.100     │
│  TOTAL ANUAL                                │ R$18.600  — R$25.200     │
└─────────────────────────────────────────────┴───────────────────────────┘
```

### O Que Está Incluído

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ✓  Coleta automática de ~61.000 artigos/mês (27 fontes RSS)           │
│  ✓  Classificação editorial com IA (A/B/C) de todos os artigos         │
│  ✓  Scoring editorial completo com IA de todos os artigos              │
│  ✓  Agrupamento semântico em temas (clustering)                         │
│  ✓  Geração de até 300 artigos/mês com pipeline anti-alucinação        │
│     → Enriquecimento factual via pesquisa web (Exa)                    │
│     → Verificação de claims (extração + CoVe)                           │
│     → Quality loop (até 3 tentativas por artigo)                        │
│     → Safety gates (bloqueio automático de conteúdo de risco)          │
│  ✓  Banco de dados Azure SQL com 250 GB                                │
│  ✓  Execução serverless (Azure Functions)                               │
│  ✓  Hosting do frontend (React/Vite)                                    │
└──────────────────────────────────────────────────────────────────────────┘
```

### Escalabilidade — Custo por Volume de Geração

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ARTIGOS/MÊS   │  Mensal BRL (faixa)     │  Por artigo (média)         │
├─────────────────┼─────────────────────────┼─────────────────────────────┤
│  100            │  R$ 1.300 — R$ 1.700    │  R$ 13,00 — 17,00          │
│  300            │  R$ 1.550 — R$ 2.100    │  R$  5,20 —  7,00          │
│  500            │  R$ 1.800 — R$ 2.400    │  R$  3,60 —  4,80          │
│  1.000          │  R$ 2.420 — R$ 3.230    │  R$  2,42 —  3,23          │
└─────────────────┴─────────────────────────┴─────────────────────────────┘

  O custo fixo (~R$ 1.180) é diluído conforme o volume de geração aumenta.
  O custo marginal por artigo é apenas R$ 1,24 — 1,70.
```

### Comparativo de Custo

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  TMC (300 artigos/mês)             R$ 1.550 — 2.100/mês                │
│  ██████████████                                                          │
│                                                                          │
│  Freelancer (1 jornalista)         R$ 4.000 — 6.000/mês                │
│  ██████████████████████████████████████████                              │
│                                                                          │
│  Agência (300 artigos × R$80)      R$ 24.000/mês                       │
│  ████████████████████████████████████████████████████████████████████    │
│                                                                          │
│  Custo marginal por artigo gerado:                                      │
│    TMC:        R$ 1,24 — 1,70                                           │
│    Freelancer: R$ 13 — 20                                               │
│    Agência:    R$ 80 — 120                                              │
│                                                                          │
│  * TMC tem custo fixo de ~R$ 1.180/mês (pipeline de coleta + infra)    │
│    que independe do volume de artigos gerados                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Projeção Anual (300 artigos/mês)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PERÍODO                          │  BRL (faixa)                        │
├───────────────────────────────────┼─────────────────────────────────────┤
│  Mensal                           │   R$  1.550  —  R$  2.100          │
│  Anual                            │   R$ 18.600  —  R$ 25.200          │
└───────────────────────────────────┴─────────────────────────────────────┘
```

### Notas

1. **Faixas de custo**: O limite inferior representa o custo calculado. O limite superior inclui margem de ~35% para variação cambial, sazonalidade de volume, e eventuais diferenças nos tokens efetivos do modelo Haiku (que ainda não foi medido em produção).
2. **Câmbio**: Valores base calculados a R$ 5,16/USD (março 2026). A faixa superior absorve câmbio até ~R$ 5,70/USD.
3. **Volume corrigido**: 2.049 artigos/dia medidos via `collection_logs` (56 dias de dados). O valor anterior de 1.268/dia vinha da tabela `collected_articles` que tem janela rotativa de 72h — subestimava em 61%.
4. **Tempo real**: Todas as chamadas LLM são síncronas (tempo real). Batch API (desconto de 50%) não é utilizada porque nenhum artigo pode ser apresentado sem score, e a geração de artigos também requer resposta imediata.
5. **Scoring completo**: Todos os 61.000 artigos coletados/mês recebem scoring editorial completo via IA (Claude Haiku), sem filtragem prévia. Isso garante máxima qualidade na priorização editorial.
6. **Dados reais**: Custo por artigo Sonnet ($0.22) medido em 113 artigos de produção. Custos Haiku estimados a partir de análise do código-fonte (modelo não estava deployado no período de medição).

### Recommended Actions

| Priority | Action | Monthly Impact |
|----------|--------|--------:|
| **P0** | Deploy Haiku 4.5 (Azure AI Foundry, Vertex AI, or Anthropic Direct) | Unblocks scoring + classification |
| **P0** | ~~Fix stale Haiku pricing in `llm_service.py:1798`~~ | **DONE** ($0.80→$1.00, $4.00→$5.00) |
| **P2** | Enable prompt caching for scoring system prompt | **-$5** estimated |

---

## 8. Confidence Assessment

### What I MEASURED (production database, 1,386 LLM calls + 56 days collection_logs)

- Sonnet cost per generated article: **$0.22** (99% confidence)
- Token averages per LLM step: all 8 task types measured
- Quality loop retry rate: **2.17x** (95%)
- Daily RSS collection: **2,049/day** from collection_logs, 56 active days (99%)
- Cost distribution: P50=$0.0595, P75=$0.0633, P90=$0.0664 per gen call (tight)
- Azure SQL: **S0 = $14.72/month** (99%)
- Infrastructure total: **~$22/month** (95%)
- Haiku deployment: **100% broken** (772/772 DeploymentNotFound)
- All 611 successful call costs verified with 0 discrepancies

### What I ESTIMATED (Haiku never ran — ±30% variance)

- Haiku scoring tokens: **~2,000 input** (from scoring_service.py prompt analysis)
- Haiku scoring cost/month (all 61K articles): **$184** (could be $130-240)
- Haiku classification cost/month: **$18** (could be $13-24)
- Exa calls per article: **2-13** depending on verification depth ($0.014-$0.091/article)

### What I DON'T KNOW

- Generated articles/month target (used 300 as scenario)
- On-demand extras volume (edits, topics, fusion)
- Actual Haiku token counts (need to deploy and measure 1 day)

---

## 9. SQL Queries to Monitor Real Costs

### Monthly cost by task type
```sql
SELECT
    FORMAT(created_at, 'yyyy-MM') AS month,
    model, task_type,
    COUNT(*) AS calls,
    SUM(input_tokens) AS input_tok,
    SUM(output_tokens) AS output_tok,
    CAST(
        SUM(input_tokens) * CASE
            WHEN model LIKE '%sonnet%' THEN 3.00 / 1000000.0
            ELSE 1.00 / 1000000.0 END
        + SUM(output_tokens) * CASE
            WHEN model LIKE '%sonnet%' THEN 15.00 / 1000000.0
            ELSE 5.00 / 1000000.0 END
    AS DECIMAL(10,4)) AS corrected_cost_usd
FROM llm_usage_log
WHERE status = 'success'
GROUP BY FORMAT(created_at, 'yyyy-MM'), model, task_type
ORDER BY corrected_cost_usd DESC;
```

### Error monitoring
```sql
SELECT task_type, model, COUNT(*) AS failures,
       LEFT(error_message, 100) AS error_sample
FROM llm_usage_log
WHERE status = 'error'
  AND created_at >= DATEADD(day, -7, GETUTCDATE())
GROUP BY task_type, model, LEFT(error_message, 100)
ORDER BY failures DESC;
```

---

## Sources

- **Production Database**: `bi4ia-tmc.database.windows.net/tmc` — 1,386 LLM calls (March 9-11, 2026) + 56 days of collection_logs (114,764 articles)
- [Anthropic Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing) — Haiku $1/$5, Sonnet $3/$15, Batch -50%
- [Claude on Vertex AI](https://platform.claude.com/docs/en/build-with-claude/claude-on-vertex-ai) — Global = same price; Regional = +10%
- [Google Vertex AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) — Batch requires regional endpoints
- [Exa AI Pricing](https://exa.ai/pricing) — $7/1K requests bundled (search + contents), March 2026
- [Azure SQL Pricing](https://azure.microsoft.com/en-us/pricing/details/azure-sql-database/single/) — S0 = $14.72/month
- [Azure Functions Pricing](https://azure.microsoft.com/en-us/pricing/details/functions/) — Consumption = free tier

---

## Revision Log

| Date | Change | Impact |
|------|--------|--------|
| 2026-03-11 v1 | Initial analysis | — |
| 2026-03-11 v2 | Deep review by 5 specialized agents | +61% volume correction, Batch API pricing corrected, scoring optimization added |
| | **Volume**: 1,268/day → **2,049/day** (from collection_logs, 56 days) | All Haiku costs increased |
| | **Batch API**: Vertex AI regional +10% → recommend Anthropic Direct | Full -50% discount |
| | **Scoring**: Added heuristic pre-filter recommendation | -80% scoring cost |
| | **Exa**: Flat $4 → range $5-$15/month | Per-article range $0.014-$0.091 |
