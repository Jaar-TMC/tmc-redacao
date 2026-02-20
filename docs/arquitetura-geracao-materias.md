# Arquitetura de Geração de Matérias - TMC

## Diagrama da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                             │
│                                                                     │
│  RevisarPage.jsx ──► api.js (POST /api/generate) ──► CriarContext  │
│  [GERAR MATÉRIA]       timeout: 90s                   [resultado]   │
│                                                            │        │
│                                                            ▼        │
│                                                    CriarPostPage    │
│                                                  + VerificationBanner│
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP POST
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   BACKEND (Azure Functions)                          │
│                                                                     │
│  function_app.py ──► generation_api.py (ORQUESTRADOR)               │
│  route: /generate      │                                            │
│  @with_cors             │                                           │
│                         ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           PIPELINE DE 3 FASES                               │    │
│  │                                                             │    │
│  │  ┌───────────────────────────────────────────────────────┐  │    │
│  │  │  FASE 1: ENRIQUECIMENTO (fact_check_service.py)       │  │    │
│  │  │  ┌──────────┐  ┌──────────┐  ┌───────────────────┐   │  │    │
│  │  │  │ Build    │  │ Exa API  │  │ Extract Key Facts │   │  │    │
│  │  │  │ Queries  │─►│ Search   │─►│ (LLM call)        │   │  │    │
│  │  │  │ (título, │  │ (2-3x    │  │                   │   │  │    │
│  │  │  │  tags,   │  │ parallel)│  │ JSON + fallback   │   │  │    │
│  │  │  │  texto)  │  │          │  │ bullet parser     │   │  │    │
│  │  │  └──────────┘  └──────────┘  └───────────────────┘   │  │    │
│  │  │                      │                                │  │    │
│  │  │  Filtros: _is_quality_url() + _BAD_URL_PATTERNS       │  │    │
│  │  │  Output: context_text, key_facts[], verified_chars     │  │    │
│  │  │  ⚠ NÃO-BLOQUEANTE: falha = warning, pipeline continua │  │    │
│  │  └───────────────────────────────────────────────────────┘  │    │
│  │                         │                                   │    │
│  │                         ▼                                   │    │
│  │  ┌───────────────────────────────────────────────────────┐  │    │
│  │  │  FASE 2: GERAÇÃO (llm_service.py)                     │  │    │
│  │  │                                                       │  │    │
│  │  │  ┌─────────────────────┐  ┌────────────────────────┐  │  │    │
│  │  │  │  SYSTEM PROMPT      │  │  USER PROMPT           │  │  │    │
│  │  │  │  ┌───────────────┐  │  │  ┌──────────────────┐  │  │  │    │
│  │  │  │  │ Categoria     │  │  │  │ TEXTO-BASE       │  │  │  │    │
│  │  │  │  │ Editorial     │  │  │  │ (fonte original)  │  │  │  │    │
│  │  │  │  │ (voz+regras)  │  │  │  ├──────────────────┤  │  │  │    │
│  │  │  │  ├───────────────┤  │  │  │ CONTEXTO         │  │  │  │    │
│  │  │  │  │ FIDELIDADE_*  │  │  │  │ VERIFICADO       │  │  │  │    │
│  │  │  │  │ (CURTA/MEDIA/ │  │  │  │ (enrichment)     │  │  │  │    │
│  │  │  │  │  FACTUAL)     │  │  │  ├──────────────────┤  │  │  │    │
│  │  │  │  ├───────────────┤  │  │  │ FATOS-CHAVE      │  │  │  │    │
│  │  │  │  │ ANTI_FABR.    │  │  │  │ VERIFICADOS      │  │  │  │    │
│  │  │  │  │ UNIVERSAL     │  │  │  ├──────────────────┤  │  │  │    │
│  │  │  │  │ + PADROES     │  │  │  │ Opções do user   │  │  │  │    │
│  │  │  │  ├───────────────┤  │  │  │ (lide, citações, │  │  │  │    │
│  │  │  │  │ Formatação    │  │  │  │  contexto, tags)  │  │  │  │    │
│  │  │  │  │ + JSON spec   │  │  │  ├──────────────────┤  │  │  │    │
│  │  │  │  └───────────────┘  │  │  │ INSTRUCOES FINAIS│  │  │  │    │
│  │  │  └─────────────────────┘  │  │ + dynamic length │  │  │  │    │
│  │  │                           │  └──────────────────┘  │  │  │    │
│  │  │            │              └────────────────────────┘  │  │    │
│  │  │            ▼                         │                │  │    │
│  │  │     ┌──────────────────────────────────┐              │  │    │
│  │  │     │   Claude Sonnet 4.5 (4096 tok)   │              │  │    │
│  │  │     └──────────────────────────────────┘              │  │    │
│  │  │                    │                                   │  │    │
│  │  │  Output: {titulo, linha_fina, conteudo, tags_sugeridas}│  │    │
│  │  │  ⚠ BLOQUEANTE: falha = erro retornado ao frontend     │  │    │
│  │  └───────────────────────────────────────────────────────┘  │    │
│  │                         │                                   │    │
│  │              ┌──────────┴──────────┐                        │    │
│  │              ▼                     ▼                        │    │
│  │  ┌──────────────────┐  ┌────────────────────────────────┐  │    │
│  │  │ SUFFICIENCY CHECK│  │ FASE 3: VERIFICAÇÃO            │  │    │
│  │  │ content<2000 AND │  │ (fact_check_service.py)        │  │    │
│  │  │ source<1500?     │  │                                │  │    │
│  │  │     │            │  │  3 checks em PARALELO:         │  │    │
│  │  │     ▼            │  │  ┌────────────────────────┐    │  │    │
│  │  │ DB: artigos      │  │  │ 1. Claims (LLM call)   │    │  │    │
│  │  │ similares        │  │  │ grounded/fabricated/    │    │  │    │
│  │  │ (por tags/cat)   │  │  │ editorial/unverifiable  │    │  │    │
│  │  └──────────────────┘  │  ├────────────────────────┤    │  │    │
│  │                        │  │ 2. Entities (regex)     │    │  │    │
│  │                        │  │ Jaccard overlap         │    │  │    │
│  │                        │  │ novel entity detection  │    │  │    │
│  │                        │  ├────────────────────────┤    │  │    │
│  │                        │  │ 3. Quotes (string match)│    │  │    │
│  │                        │  │ 50% word / 60% substr   │    │  │    │
│  │                        │  └────────────────────────┘    │  │    │
│  │                        │           │                    │  │    │
│  │                        │           ▼                    │  │    │
│  │                        │  ┌────────────────────────┐    │  │    │
│  │                        │  │ CONFIDENCE SCORING     │    │  │    │
│  │                        │  │ Claims:     50%        │    │  │    │
│  │                        │  │ Entities:   25%        │    │  │    │
│  │                        │  │ Expansion:  10%        │    │  │    │
│  │                        │  │ Quotes:      5%        │    │  │    │
│  │                        │  │ Sufficiency: 10%       │    │  │    │
│  │                        │  └────────────────────────┘    │  │    │
│  │                        │           │                    │  │    │
│  │                        │           ▼                    │  │    │
│  │                        │  Risk: low/medium/high/critical│  │    │
│  │                        │  ⚠ NÃO-BLOQUEANTE             │  │    │
│  │                        └────────────────────────────────┘  │    │
│  │                                    │                       │    │
│  │                                    ▼                       │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │  SAFETY GATES                                       │   │    │
│  │  │                                                     │   │    │
│  │  │  HARD BLOCK (publish_blocked=true):                 │   │    │
│  │  │   - risk = critical                                 │   │    │
│  │  │   - confidence < 0.4                                │   │    │
│  │  │   - fabricated >= 3                                 │   │    │
│  │  │   - fabricated == 2 AND confidence < 0.40           │   │    │
│  │  │   - unverifiable >= 3 AND ratio > 40%              │   │    │
│  │  │   - expansion > 15x                                │   │    │
│  │  │                                                     │   │    │
│  │  │  SOFT GATE (human_review_required=true):            │   │    │
│  │  │   - fabricated == 2 AND confidence >= 0.40          │   │    │
│  │  │   - unverifiable >= 2 AND ratio > 30%              │   │    │
│  │  │   - novel_entities >= 3 AND ratio > 50%            │   │    │
│  │  │   - 10 < expansion <= 15                           │   │    │
│  │  │   - risk = high (not already blocked)              │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  RESPOSTA JSON:                                                     │
│  {titulo, linha_fina, conteudo, tags_sugeridas,                     │
│   verification, publish_blocked, block_reason,                      │
│   human_review_required, review_reasons, material_sufficiency}      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Fluxo Frontend → Backend

1. O usuário monta a matéria em **RevisarPage.jsx**, selecionando texto-base, categoria, tom, tags, etc.
2. Ao clicar "GERAR MATÉRIA", `api.js` faz um `POST /api/generate` com timeout de 90s
3. O `function_app.py` roteia para `generation_api.py`, que orquestra as 3 fases

### Parâmetros da Request

| Campo | Tipo | Default | Descrição |
|---|---|---|---|
| `texto_base` | str (min 20) | obrigatório | Texto fonte |
| `persona` | str | "imparcial" | Persona legada |
| `tom` | str | "formal" | Tom de escrita |
| `tipo_materia` | str | "destaque" | Tipo da matéria |
| `categoria` | str? | None | Categoria editorial |
| `modo_opinativo` | bool | False | Modo opinião |
| `titulo_fonte` | str? | None | Título da fonte (usado no enrichment) |
| `skip_verification` | bool | False | Pular Fase 3 |
| `skip_enrichment` | bool | False | Pular Fase 1 |
| `orientacao_lide` | str? | None | Orientação de lide |
| `citacoes` | list? | None | Citações |
| `contexto` | str? | None | Contexto adicional |
| `creditos` | str? | None | Créditos da fonte |
| `tags` | list? | None | Tags SEO |

---

## Fase 1 - Enriquecimento (Exa Search)

**Serviço**: `fact_check_service.py → enrich_context()`
**Condição**: `FACT_CHECK_ENABLED` AND `ENRICHMENT_ENABLED` AND NOT `skip_enrichment`

### Fluxo

1. **Construir queries** (`_build_search_queries()`): Prioridade: `titulo_fonte` > 1ª frase do texto > tags combinadas > nomes próprios. Retorna até 3 queries.
2. **Buscas paralelas na Exa API**: Search neural, categoria news, autoprompt enabled, com highlights.
3. **Filtro de URLs** (`_is_quality_url()` + `_BAD_URL_PATTERNS`): Remove portais, .gov.br, dev docs, blogspot, indexes. Rejeita resultados com < 150 chars.
4. **Extração de fatos-chave** (`_extract_key_facts()`): LLM call com texto combinado. Fallback de parsing bullet/numbered lists quando JSON falha.
5. **Critério de sucesso**: `len(key_facts) > 0 OR len(context_text) > 200`

### Modo Agressivo (fonte < 500 chars)

- 3 queries (ao invés de 2)
- Até 10 resultados (ao invés de 5)
- 4000 chars/resultado
- 15 key facts
- 6000 char context limit

### Output

```python
EnrichmentContext {
    context_text: str,      # Texto bruto dos resultados Exa
    key_facts: list[str],   # Fatos-chave extraídos via LLM
    source_urls: list[str], # URLs das fontes
    search_queries: list,   # Queries usadas
    success: bool,
    verified_chars: int,    # source_len + len(context_text)
}
```

### Variáveis de Ambiente

| Variável | Default | Descrição |
|---|---|---|
| `FACT_CHECK_ENABLED` | true | Switch master |
| `FACT_CHECK_ENRICHMENT_ENABLED` | true | Switch da Fase 1 |
| `EXA_API_KEY` | - | Obrigatório para enrichment |
| `EXA_MAX_RESULTS` | 5 | Resultados por query |
| `EXA_SEARCH_DAYS` | 7 | Janela de busca em dias |
| `EXA_TIMEOUT` | 15 | Timeout em segundos |

---

## Fase 2 - Geração (Claude Sonnet 4.5)

**Serviço**: `llm_service.py → generate_article()`
**Modelo**: Claude Sonnet 4.5 (`claude-sonnet-4-5`), 4096 tokens max
**Infra**: Azure AI Services endpoint (preferencial) ou API Anthropic direta

### Construção do System Prompt

Dois caminhos possíveis:

**Caminho A - Sistema de Categorias** (preferencial, quando `categoria` é fornecida):
`get_system_prompt()` → `_build_category_prompt()`

**Caminho B - Sistema de Personas** (legado, fallback):
`get_system_prompt()` constrói direto de `PERSONAS[persona]`

Ambos incluem:
- `ANTI_FABRICACAO_UNIVERSAL` (5 regras core anti-fabricação)
- `ANTI_FABRICACAO_PADROES` (8 padrões específicos proibidos)
- Variante FIDELIDADE (selecionada pelo tamanho do material)
- Regras de formatação + spec JSON de resposta

### Seleção de FIDELIDADE

```python
effective_material = max(source_len, verified_chars) if verified_chars > 0 else source_len

if effective_material < 200:
    FIDELIDADE_CURTA      # 3-5 frases, fidelidade absoluta
elif effective_material < 500:
    FIDELIDADE_MEDIA      # 5-8 parágrafos, omitir lacunas
else:
    FIDELIDADE_FACTUAL    # Regras completas, tamanho padrão
```

O `effective_material` usa o MAIOR entre tamanho bruto da fonte e `verified_chars` (fonte + enrichment), permitindo que fontes curtas enriquecidas produzam matérias completas.

### Tamanho Dinâmico (SOURCE_LENGTH_TIERS)

| Fonte (chars) | Min Output | Max Output | Classificação |
|---|---|---|---|
| < 150 | 200 | 400 | nota curta |
| 150-500 | 400 | 1000 | matéria curta |
| 500-1500 | 800 | 2000 | matéria média |
| 1500-3000 | 1500 | 3500 | matéria longa |
| 3000+ | 2000 | 4000 | matéria completa |

Cap de expansão: `max_output = min(max_output, max(effective_len * 3, min_output))`

### Categorias Editoriais

| Categoria | Referência de Estilo | Opinião? | Tom Default |
|---|---|---|---|
| `esportes` | CazeTV | Sim | informal |
| `entretenimento` | The News + Pop | Não | informal |
| `politica` | Sóbrio/Didático | Sim | sóbrio |
| `economia` | Cotidiano cidadão | Sim | didático |
| `geral` | Conversacional | Não | conversacional |

Cada categoria tem: `system_prompt_base`, `allows_opinion`, `default_tone`, `available_tones`, `dos`, `donts`, e regras anti-fabricação específicas.

### Construção do User Prompt (`build_user_prompt()`)

Seções na ordem:
1. `TEXTO-BASE PARA REESCRITA` - texto fonte
2. `CONTEXTO VERIFICADO` - contexto do enrichment (se disponível), com aviso sobre cross-attribution
3. `FATOS-CHAVE VERIFICADOS` - key facts do enrichment (se disponível)
4. `ORIENTACAO PARA O LIDE` (se fornecido)
5. `CITACOES PARA INCLUIR` (se fornecido)
6. `CONTEXTO ADICIONAL` (se fornecido)
7. `CREDITOS DA FONTE` (se fornecido)
8. `TAGS/PALAVRAS-CHAVE` (se fornecido)
9. `INSTRUCOES FINAIS` - range de tamanho dinâmico + 5 regras finais

### Anti-Fabricação

**`ANTI_FABRICACAO_UNIVERSAL`** (5 regras core, injetado em TODAS as categorias):
- Regras gerais contra fabricação de informações

**`ANTI_FABRICACAO_PADROES`** (8 padrões específicos proibidos):
1. Não inventar detalhes temporais (dias da semana, horários)
2. Não fazer asserções negativas ("X não se pronunciou")
3. Não usar filler editorial como fato
4. Não generalizar comportamentos ("tem usado/feito")
5. Não preencher com conhecimento do training data
6. Não atribuir dados cruzados do enrichment
7. Não fazer inferências causais fora da fonte
8. Não expandir citações

### Output

```json
{
    "titulo": "Título da matéria",
    "linha_fina": "Subtítulo/lead",
    "conteudo": "Conteúdo HTML da matéria",
    "tags_sugeridas": ["tag1", "tag2"]
}
```

---

## Sufficiency Check (entre Fase 2 e Fase 3)

**Condição**: `content_len < 2000 AND source_len < 1500`

Busca artigos similares no banco de dados via `_find_similar_articles()`:
- Consulta por tags (até 3 primeiras) e categoria
- Retorna até 5 artigos com `{id, title, source, preview, content_length, published_at}`
- Adicionado ao response como `material_sufficiency` com sugestões de merge

---

## Fase 3 - Verificação

**Serviço**: `fact_check_service.py → verify_article()`
**Condição**: `FACT_CHECK_ENABLED` AND `VERIFICATION_ENABLED` AND NOT `skip_verification`

### 3 Checks em Paralelo (`asyncio.gather`)

#### 1. Claim Extraction & Grounding (LLM call)

- `_extract_and_verify_claims()` - Uma única chamada LLM que extrai e classifica
- Até 10 claims extraídos (`MAX_CLAIMS`)
- Classificações:
  - **grounded**: Presente na fonte/enrichment
  - **fabricated**: Incorreto, desconexo ou distorcido (NÃO contexto editorial correto)
  - **editorial**: Opiniões, background contextual correto, inferências lógicas, conhecimento público — EXCLUÍDOS do scoring de accuracy
  - **unverifiable**: Não confirmável com o material disponível
  - **inaccurate**: Fatos distorcidos (números errados, nomes trocados)

#### 2. Entity Comparison (regex puro)

- `_compare_entities()` - Sem chamada de API
- Extrai: nomes capitalizados multi-palavra, siglas (2-6 chars maiúsculas), valores monetários (R$...), percentuais, datas
- Filtra stopwords do português (44 palavras)
- Calcula Jaccard overlap entre entidades da fonte e do output
- Identifica entidades novas (novel entities)

#### 3. Quote Verification (string matching)

- `_verify_quotes()` - Sem chamada de API
- Extrai citações do artigo gerado via regex (aspas duplas, smart quotes, aspas simples, mín. 10 chars)
- Verifica contra texto fonte + citações fornecidas pelo usuário
- Critério: 50% word overlap OU 60% substring match

### Confidence Scoring

```
confidence = 0.50 × claim_score
           + 0.25 × entity_overlap_score
           + 0.10 × expansion_score
           + 0.05 × quote_verification_rate
           + 0.10 × sufficiency_score
```

| Componente | Cálculo |
|---|---|
| `claim_score` | `grounded_ratio - (fabricated_ratio × 0.5)`, excluindo claims editoriais. Sem claims factuais = 0.5 |
| `entity_overlap` | Jaccard similarity das entidades |
| `expansion_score` | `≤3x → 1.0, ≤5x → 0.8, ≤10x → 0.5, ≤25x → 0.2, >25x → 0.0` |
| `quote_rate` | `verified_quotes / total_quotes` |
| `sufficiency` | `≥500 chars → 1.0, 150-500 → 0.5, <150 → 0.2` |

**Guards** (cap de confidence):
- Expansion > 10x: cap em 0.5
- Novel entities ≥ 3 AND > 50% do output: cap em 0.55

### Risk Level

Base pela confidence: `≥0.8: low, ≥0.5: medium, ≥0.3: high, <0.3: critical`

**Override escalations**:
- 3+ fabricated → critical
- 2 fabricated + confidence < 0.35 → critical
- 2 fabricated + base low/medium → high
- 1 fabricated + confidence < 0.30 → high
- Expansion > 25x → no mínimo high
- Unverified quotes > 50% → no mínimo high
- Novel entities > 50% → no mínimo high
- Unverifiable ≥ 3 AND > 40% → no mínimo high
- Expansion > 15x → no mínimo medium

---

## Safety Gates

### Hard Blocks (publish_blocked=true, UI vermelho)

| Condição | Descrição |
|---|---|
| `risk_level == "critical"` | Risco crítico |
| `confidence < 0.4` | Confiança muito baixa (com dados verificados) |
| `fabricated >= 3` | 3+ claims fabricados |
| `fabricated == 2 AND confidence < 0.40` | 2 fabricados com baixa confiança |
| `unverifiable >= 3 AND ratio > 40%` | Muitas claims não verificáveis |
| `expansion > 15x` | Expansão excessiva (usa verified_chars quando disponível) |

### Soft Gates (human_review_required=true, UI âmbar)

| Condição | Descrição |
|---|---|
| `fabricated == 2 AND confidence >= 0.40` | 2 fabricados mas confiança razoável |
| `unverifiable >= 2 AND ratio > 30%` | Claims não verificáveis moderados |
| `novel_entities >= 3 AND ratio > 50%` | Muitas entidades novas |
| `10 < expansion <= 15` | Expansão alta mas não extrema |
| `risk_level == "high"` | Risco alto (não já bloqueado) |

---

## Resposta da API

```json
{
    "titulo": "Título gerado",
    "linha_fina": "Subtítulo/lead",
    "conteudo": "HTML da matéria",
    "tags_sugeridas": ["tag1", "tag2"],
    "verification": {
        "is_verified": true,
        "confidence_score": 0.72,
        "risk_level": "medium",
        "claims": [...],
        "entity_comparison": {...},
        "quote_verification": {...},
        "expansion_ratio": 3.5,
        "requires_human_review": false
    },
    "publish_blocked": false,
    "block_reason": null,
    "human_review_required": false,
    "review_reasons": [],
    "material_sufficiency": null
}
```

---

## Frontend Pós-Geração

1. **CriarContext** armazena resultado completo (incluindo verification) em `sessionStorage`
2. **CriarPostPage** exibe editor com conteúdo gerado
3. **VerificationBanner** mostra status (atualmente **escondido** via commit `dde19fb`):
   - Verde: `confidence >= 0.7 AND risk = low/medium`
   - Âmbar: risk high ou revisão parcial
   - Vermelho: `publishBlocked OR risk = critical OR confidence < 0.4`

---

## Política Editorial

- Fabricações factualmente corretas são **ACEITÁVEIS** se tiverem coesão com o tema
- Contexto editorial (background de fontes, análise razoável, inferências lógicas) enriquece a matéria
- Só bloquear fabricações **INCORRETAS** ou **DESCONEXAS** do tema

---

## Arquivos-Chave

| Arquivo | Papel |
|---|---|
| `functions/generation_api.py` | Orquestrador das 3 fases + safety gates |
| `services/llm_service.py` | Construção de prompts + chamada ao Claude |
| `services/fact_check_service.py` | Enriquecimento (Exa) + verificação factual |
| `services/database.py` | Busca de artigos similares (sufficiency check) |
| `tmc-redacao/src/services/api.js` | Chamada HTTP do frontend |
| `tmc-redacao/src/pages/criar/RevisarPage.jsx` | Página que dispara a geração |
| `tmc-redacao/src/context/CriarContext.jsx` | Estado da geração (resultado + verification) |
| `tmc-redacao/src/components/ui/VerificationBanner.jsx` | Banner de status de verificação |

---

## Variáveis de Ambiente

| Variável | Default | Descrição |
|---|---|---|
| `FACT_CHECK_ENABLED` | true | Master switch do pipeline |
| `FACT_CHECK_ENRICHMENT_ENABLED` | true | Fase 1 |
| `FACT_CHECK_VERIFICATION_ENABLED` | true | Fase 3 |
| `EXA_API_KEY` | - | API key para Exa search |
| `EXA_MAX_RESULTS` | 5 | Resultados por query |
| `EXA_SEARCH_DAYS` | 7 | Janela de busca |
| `EXA_TIMEOUT` | 15 | Timeout Exa (segundos) |
| `ANTHROPIC_MODEL` | claude-sonnet-4-5 | Modelo para geração |
| `AZURE_AI_ENDPOINT` | - | Endpoint Azure AI Services |
| `AZURE_AI_API_KEY` | - | API key Azure |
| `ANTHROPIC_API_KEY` | - | API key Anthropic (fallback) |
