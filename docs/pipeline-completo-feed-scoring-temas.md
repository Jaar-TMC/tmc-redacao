# Pipeline Completo: Feed RSS, Scoring e Temas Semânticos

> Documentação técnica completa do fluxo de dados desde a coleta RSS até a geração de matérias com verificação anti-alucinação.
> Versão: v7.1 | Data: 2026-02-12

---

## Índice

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Coleta RSS — O Início do Pipeline](#2-coleta-rss--o-início-do-pipeline)
3. [Parsing e Extração de Dados](#3-parsing-e-extração-de-dados)
4. [Deduplicação Multi-Camada](#4-deduplicação-multi-camada)
5. [Enriquecimento de Artigos](#5-enriquecimento-de-artigos)
6. [Scoring Editorial (Classificação A/B/C)](#6-scoring-editorial-classificação-abc)
7. [Geração de Embeddings](#7-geração-de-embeddings)
8. [Clustering Semântico — Formação de Temas](#8-clustering-semântico--formação-de-temas)
9. [Event Signatures — Clustering por Eventos](#9-event-signatures--clustering-por-eventos)
10. [Score do Tema (Composite Score)](#10-score-do-tema-composite-score)
11. [Manutenção de Temas](#11-manutenção-de-temas)
12. [Geração de Matérias via LLM](#12-geração-de-matérias-via-llm)
13. [Pipeline Anti-Alucinação (Fact-Check)](#13-pipeline-anti-alucinação-fact-check)
14. [Safety Gates — Publicação](#14-safety-gates--publicação)
15. [Schema do Banco de Dados](#15-schema-do-banco-de-dados)
16. [Endpoints da API](#16-endpoints-da-api)
17. [Configuração Completa](#17-configuração-completa)

---

## 1. Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AZURE FUNCTIONS (Python)                            │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ RSS Collector │  │  Embedding   │  │   Scoring    │  │  Clustering   │  │
│  │  (15 min)    │  │  Generator   │  │  Calculator  │  │   Engine      │  │
│  │              │  │  (5 min)     │  │  (10 min)    │  │  (30 min)     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         │                 │                  │                  │           │
│  ┌──────▼─────────────────▼──────────────────▼──────────────────▼────────┐  │
│  │                     SERVICES LAYER                                    │  │
│  │  rss_parser │ database │ embedding │ scoring │ clustering │ llm      │  │
│  │  dedup      │ config   │ ai_enrich │ metrics │ event_sig  │ factchk  │  │
│  └──────────────────────────┬────────────────────────────────────────────┘  │
│                             │                                               │
│  ┌──────────────────────────▼────────────────────────────────────────────┐  │
│  │                      AZURE SQL DATABASE                               │  │
│  │  sources │ collected_articles │ article_scores │ article_embeddings   │  │
│  │  themes  │ article_themes     │ event_signatures │ collection_logs    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Timer Triggers (Agendamento)

| Trigger | Frequência | Função |
|---------|-----------|--------|
| `rss_collector` | A cada 15 min | Busca feeds RSS, deduplica, enriquece, insere artigos |
| `embedding_generator` | A cada 5 min | Gera embeddings (OpenAI) para artigos sem vetor |
| `scoring_calculator` | A cada 10 min | Classifica artigos em A/B/C via Claude AI |
| `clustering_engine` | A cada 30 min | Agrupa artigos em temas semânticos |
| `clustering_maintenance` | Diário às 3h UTC | Merge temas, limpeza, recalcula scores |

### Fluxo de Dados (Ciclo de Vida do Artigo)

```
Feed RSS → Parse → Dedup → Enrich → Insert (DB)
                                        │
                    ┌───────────────────┤
                    ▼                   ▼
              Embedding (5min)    Scoring (10min)
                    │                   │
                    ▼                   ▼
              Clustering (30min)  article_scores
                    │                   │
                    ▼                   │
                themes ◄────────────────┘
                    │         (theme score = f(article scores))
                    ▼
           Frontend (React)
                    │
                    ▼
           Geração de Matéria → Fact-Check → Safety Gates → Publicação
```

---

## 2. Coleta RSS — O Início do Pipeline

### 2.1 Fontes RSS Configuradas

O sistema monitora **27 fontes RSS** de 13 publishers brasileiros:

| Publisher | Feeds | Frequência | Categorias |
|-----------|-------|------------|------------|
| G1 (Globo) | 7 | 30min | Geral, Política, Economia, Tecnologia, Mundo, Ciência/Saúde, SP |
| GloboEsporte | 1 | 30min | Futebol |
| Folha de S.Paulo | 5 | 1h | Principal, Política, Mercado, Mundo, Esporte |
| Estadão | 3 | 1h | Principal, Política, Economia |
| CNN Brasil | 1 | 1h | Geral |
| R7 | 1 | 1h | Geral |
| Agência Brasil | 1 | 2h | Geral |
| Senado Notícias | 1 | 2h | Política |
| Câmara Notícias | 1 | 2h | Política |
| InfoMoney | 1 | 1h | Economia |
| Valor Econômico | 1 | 1h | Economia |
| TecMundo | 1 | 1h | Tecnologia |
| BBC Brasil | 1 | 1h | Internacional |
| DW Brasil | 1 | 2h | Internacional |
| UOL | 1 | 1h | Geral |

Cada fonte é um registro na tabela `sources`:

```sql
INSERT INTO sources (name, url, favicon_url, category, frequency, active)
VALUES ('G1 - Principal', 'https://g1.globo.com/rss/g1/',
        'https://g1.globo.com/favicon.ico', 'Geral', '30min', 1)
```

### 2.2 Controle de Frequência

Cada fonte tem uma frequência configurável. O `should_fetch()` verifica se já passou tempo suficiente:

```python
intervals = {
    '15min': timedelta(minutes=15),
    '30min': timedelta(minutes=30),
    '1h':    timedelta(hours=1),
    '2h':    timedelta(hours=2),
    '6h':    timedelta(hours=6),
}

def should_fetch(self, now):
    if self.last_fetch is None:
        return True  # Primeira coleta
    elapsed = now - self.last_fetch
    return elapsed >= intervals.get(self.frequency, timedelta(hours=1))
```

### 2.3 Fluxo do RSS Collector (a cada 15 min)

```
rss_collector_handler()
│
├── 1. Testar conexão com banco
├── 2. Limpar artigos antigos (> 24h)
├── 3. Remover títulos duplicados
├── 4. Buscar fontes ativas que devem ser coletadas
│
└── 5. Para CADA FONTE (paralelo, max 10 simultâneas):
    ├── 5.1 Fetch + Parse do feed RSS
    ├── 5.2 Deduplica contra banco
    ├── 5.3 Enriquece imagens (máx 5 artigos sem imagem)
    ├── 5.4 Enriquece com AI (categorias + tags) se habilitado
    ├── 5.5 Insere artigos no banco
    ├── 5.6 Atualiza last_fetch da fonte
    └── 5.7 Loga resultado da coleta
```

---

## 3. Parsing e Extração de Dados

### 3.1 RSS Parser (`services/rss_parser.py`)

O parser usa a lib `feedparser` e extrai os seguintes campos de cada entry:

| Campo | Prioridade de Extração | Obrigatório |
|-------|----------------------|-------------|
| `title` | `entry.title` | Sim (min 1 char) |
| `url` | `entry.link` | Sim |
| `content` | `entry.content[0].value` → `entry.summary` → `entry.description` | Não |
| `preview` | Truncamento do content (máx 500 chars) | Não |
| `published_at` | `published_parsed` → `updated_parsed` → `datetime.utcnow()` | Não |
| `author` | `entry.author` → `author_detail.name` → `dc:creator` | Não |
| `category` | `entry.tags` → `entry.category` → `source.category` | Não |
| `tags` | `entry.tags` (até 10) | Não |
| `image_url` | `media:content` → `media:thumbnail` → `enclosures` → `<img src>` | Não |
| `hash` | `SHA256(url\|title)` lowercase | Auto-gerado |

### 3.2 Hash de Deduplicação

```python
def _generate_hash(url: str, title: str) -> str:
    content = f"{url}|{title}".lower().strip()
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

O hash é a chave primária de deduplicação — se o mesmo artigo aparecer com URL ou título idêntico, é descartado.

### 3.3 Extração de Imagem (Prioridade)

```
1. RSS <media:content> (medium='image' ou type='image/*')
2. RSS <media:thumbnail>
3. RSS <enclosures> (type='image/*')
4. Atom <image href>
5. Regex <img src> no content/summary
```

**Filtros de qualidade**: Rejeita URLs contendo `placeholder`, `default`, `avatar`, `icon`, `logo`, `1x1`, `spacer`, `blank`, `pixel`.

### 3.4 Limpeza de Texto

- Normalização Unicode (NFC)
- Remoção de caracteres de controle
- Unescape de entidades HTML
- Remoção de tags HTML
- Normalização de espaços em branco

---

## 4. Deduplicação Multi-Camada

A deduplicação opera em **3 camadas** para evitar artigos repetidos:

### Camada 1: Hash Exato (SHA256)

```python
# Gera hash para todos os artigos
hashes = [article.hash for article in articles]
# Consulta batch no banco
existing_hashes = db.check_existing_hashes(hashes)
# Filtra artigos com hash já existente
unique = [a for a in articles if a.hash not in existing_hashes]
```

### Camada 2: Similaridade de Título (Jaccard ≥ 0.85)

```python
def is_similar_title(title1: str, title2: str, threshold=0.85) -> bool:
    t1, t2 = normalize(title1), normalize(title2)

    # Containment check
    if t1 in t2 or t2 in t1:
        return True

    # Jaccard similarity
    words1, words2 = set(t1.split()), set(t2.split())
    similarity = len(words1 & words2) / len(words1 | words2)
    return similarity >= threshold
```

Compara contra títulos das últimas 24h no banco.

### Camada 3: Dedup em Lote (Mesmo Feed)

Dentro do mesmo batch de artigos de um feed, remove duplicatas internas.

### Limpeza Periódica (SQL)

```sql
-- Executada a cada coleta (rss_collector_handler)
-- Mantém o mais antigo de cada grupo de títulos idênticos
WITH Duplicates AS (
    SELECT id, title,
           ROW_NUMBER() OVER (
               PARTITION BY LOWER(LTRIM(RTRIM(title)))
               ORDER BY collected_at ASC
           ) as rn
    FROM collected_articles
)
DELETE FROM collected_articles
WHERE id IN (SELECT id FROM Duplicates WHERE rn > 1)
```

---

## 5. Enriquecimento de Artigos

### 5.1 Enriquecimento de Imagem (`services/enrichment.py`)

Para artigos sem imagem (máx 5 por fonte, para não atrasar a coleta):

```
1. Fetch da página do artigo via httpx (timeout 10s)
2. Parse com BeautifulSoup
3. Extração por prioridade:
   a. <meta property="og:image"> (Open Graph)
   b. <meta name="twitter:image"> (Twitter Cards)
   c. <meta name="twitter:image:src">
   d. Primeira <img> dentro de <article>/<main>
4. Validação contra padrões de placeholder
5. Conversão para URL absoluta se necessário
```

### 5.2 Enriquecimento AI — Categorias e Tags (`services/ai_enrichment.py`)

Quando habilitado (`AI_ENRICHMENT_ENABLED=true`), usa Claude para classificar artigos em categorias e gerar tags SEO.

**Configuração:**
- Batch size: 5 artigos por chamada
- Máx por fonte: 20 artigos
- Timeout: 60 segundos

**System Prompt completo:**

```
Você é um especialista em classificação de conteúdo jornalístico e SEO.

Sua tarefa é analisar artigos de notícias e:
1. Classificar cada artigo em UMA categoria válida
2. Gerar 5-8 tags SEO relevantes para cada artigo

## CATEGORIAS VÁLIDAS
Use EXATAMENTE uma destas categorias (sem acentos):
- Politica, Economia, Esportes, Tecnologia, Saude, Cultura,
  Entretenimento, Internacional, Brasil, Ciencia, Educacao,
  Meio Ambiente, Seguranca, Celebridades

## REGRAS PARA TAGS
- Tags em português, sem acentos, minúsculas
- Termos pesquisáveis e relevantes para SEO
- Incluir: tema principal, entidades (pessoas, empresas, lugares), contexto
- Separar palavras compostas com hífen (ex: "meio-ambiente", "copa-do-mundo")

## FORMATO DE RESPOSTA
Responda APENAS com JSON válido no formato:
{
  "classifications": [
    {"id": "0", "category": "Categoria", "tags": ["tag1", "tag2", ...]},
    {"id": "1", "category": "Categoria", "tags": ["tag1", "tag2", ...]}
  ]
}
```

**User Prompt (por batch):**

```
Classifique os seguintes artigos:

---
ARTIGO 0:
Título: {title}
Conteúdo: {content[:500]}
Categoria original: {category ou 'N/A'}
---
ARTIGO 1:
...
---

Responda com o JSON de classificações.
```

---

## 6. Scoring Editorial (Classificação A/B/C)

### 6.1 Visão Geral

O sistema de scoring avalia cada artigo com base em **4 sinais editoriais** para determinar sua prioridade jornalística. Executa a cada 10 minutos, processando até 50 artigos por execução.

### 6.2 Os 4 Sinais Editoriais

| Sinal | Pergunta | Valores | Pontos |
|-------|----------|---------|--------|
| **Inesperado** | A notícia é surpreendente? | `yes` / `partial` / `no` | 25 / 12 / 0 |
| **Impacto** | Afeta a vida do leitor? | `high` / `medium` / `low` | 30 / 15 / 0 |
| **Busca Agora** | O leitor vai buscar mais? | `yes` / `maybe` / `no` | 25 / 12 / 0 |
| **Conversa** | O leitor vai comentar? | `yes` / `no` | 20 / 0 |

**Score total = soma dos 4 sinais = 0 a 100 pontos**

### 6.3 Classificação

```
┌──────────────────────────────────────────────────────────────┐
│  Score ≥ 75  →  Classe A  (verde #22c55e)                   │
│              "Alta prioridade — material de capa"             │
├──────────────────────────────────────────────────────────────┤
│  Score 40-74 →  Classe B  (amarelo #eab308)                 │
│              "Média prioridade — bom conteúdo"               │
├──────────────────────────────────────────────────────────────┤
│  Score < 40  →  Classe C  (vermelho #ef4444)                │
│              "Baixa prioridade — conteúdo complementar"      │
└──────────────────────────────────────────────────────────────┘
```

### 6.4 Exemplos de Pontuação

**Exemplo A (Score 100 — Classe A):**
- Inesperado: `yes` (25) — Renúncia inesperada de ministro
- Impacto: `high` (30) — Afeta política econômica
- Busca Agora: `yes` (25) — Trending topic
- Conversa: `yes` (20) — Debate nas redes
- **Total: 100**

**Exemplo B (Score 52 — Classe B):**
- Inesperado: `partial` (12) — Aumento maior que esperado
- Impacto: `medium` (15) — Relevante mas não urgente
- Busca Agora: `yes` (25) — Leitor vai buscar detalhes
- Conversa: `no` (0) — Sem polêmica
- **Total: 52**

**Exemplo C (Score 12 — Classe C):**
- Inesperado: `no` (0) — Evento agendado
- Impacto: `low` (0) — Sem impacto prático
- Busca Agora: `maybe` (12) — Pode interessar
- Conversa: `no` (0) — Factual neutro
- **Total: 12**

### 6.5 Método Primário: Análise via Claude AI

**System Prompt completo (usado na chamada LLM):**

```
Voce e um editor experiente de jornalismo brasileiro, especializado em
avaliar a relevancia editorial de noticias de qualquer categoria (politica,
economia, esportes, cultura, tecnologia, saude, etc).

Sua tarefa e analisar artigos e classificar seu potencial editorial usando
4 sinais de relevancia jornalistica.

## OS 4 SINAIS DE RELEVANCIA

### 1. INESPERADO (Fato surpreendente?)
Avalia se a noticia traz algo que o leitor NAO esperava ver hoje.
- **yes**: Fato completamente inesperado, surpreendente, fora do comum
  - Exemplos: Renuncia de ministro, falencia de banco, morte de celebridade,
    descoberta cientifica, golpe de estado
- **partial**: Fato parcialmente inesperado, com elementos de surpresa
  - Exemplos: Aumento de juros maior que esperado, resultado eleitoral
    apertado, declaracao polemica de autoridade
- **no**: Fato esperado, rotineiro, previsivel
  - Exemplos: Reuniao agendada, balanco trimestral, previsao do tempo,
    evento cultural anunciado

### 2. IMPACTO (Afeta a vida do leitor?)
Avalia o impacto pratico na vida do cidadao/leitor.
- **high**: Impacto alto e direto na vida das pessoas
  - Exemplos: Aumento de precos, mudanca em impostos, surto de doenca,
    corte de empregos, nova lei aprovada
- **medium**: Impacto moderado - relevante mas nao urgente
  - Exemplos: Mudanca em politica publica, lancamento de produto,
    resultado de pesquisa, acordo comercial
- **low**: Impacto baixo - informacao interessante mas sem consequencia pratica
  - Exemplos: Curiosidade historica, evento cultural local, estatistica
    sem contexto, entrevista protocolar

### 3. BUSCA AGORA (Leitor vai buscar?)
Avalia se o leitor vai ativamente buscar mais informacoes sobre este assunto.
- **yes**: Leitor vai procurar imediatamente - noticia urgente/trending
  - Exemplos: Acidente grave, escandalo politico, vazamento de dados,
    morte de famoso, resultado de eleicao
- **maybe**: Leitor pode se interessar em saber mais
  - Exemplos: Nova tecnologia, especulacao de mercado, boato sobre
    celebridade, tendencia de comportamento
- **no**: Leitor provavelmente nao vai buscar ativamente
  - Exemplos: Rotina administrativa, comunicado oficial padrao, evento
    comum, fato sem novidade

### 4. CONVERSA (Leitor vai comentar?)
Avalia se a noticia vai gerar discussao nas redes sociais, com amigos, familia.
- **yes**: Noticia para conversar - vai gerar debates e discussoes
  - Exemplos: Polemica politica, declaracao controversa, crime chocante,
    resultado surpreendente, tema divisivo
- **no**: Noticia que nao gera conversa - leia e siga em frente
  - Exemplos: Informacao factual sem polemica, rotina, comunicado tecnico,
    estatistica neutra

## FORMATO DE RESPOSTA

Responda APENAS com JSON valido no seguinte formato:
{
  "sinal_inesperado": "yes|partial|no",
  "sinal_impacto": "high|medium|low",
  "sinal_busca_agora": "yes|maybe|no",
  "sinal_conversa": "yes|no",
  "justificativa": "Breve explicacao das classificacoes (max 200 caracteres)"
}

IMPORTANTE:
- Use APENAS os valores especificados para cada sinal
- NAO inclua comentarios ou texto fora do JSON
- A justificativa deve ser concisa e em portugues
- Considere o CONTEXTO BRASILEIRO e a relevancia para o publico geral
```

**User Prompt:**

```
Analise o seguinte artigo e classifique usando os 4 sinais de relevancia editorial:

## TITULO
{title}

## CONTEUDO
{content[:3000]}

---

Classifique este artigo nos 4 sinais (inesperado, impacto, busca_agora, conversa)
e retorne APENAS o JSON.
```

**Parâmetros LLM:** max_tokens=1024, content truncado a 3000 chars.

### 6.6 Método Fallback: Heurística por Keywords

Quando o LLM não está disponível, o sistema usa matching de keywords:

**Keywords por sinal:**

```python
# INESPERADO (25 keywords)
'surpresa', 'surpreendente', 'inesperado', 'bomba', 'exclusivo', 'urgente',
'breaking', 'inedito', 'chocante', 'revela', 'descobre', 'bombastico',
'renuncia', 'demissao', 'demitido', 'afastado', 'cassado', 'preso',
'falencia', 'quebra', 'golpe', 'impeachment', 'escandalo',
'surto', 'pandemia', 'descoberta', 'cura', 'vacina', 'alerta',
'eliminacao', 'rebaixamento', 'titulo'

# IMPACTO (24 keywords)
'inflacao', 'juros', 'selic', 'dolar', 'desemprego', 'salario', 'preco',
'aumento', 'reducao', 'imposto', 'tributo', 'gasolina', 'energia',
'lei', 'votacao', 'aprovado', 'reforma', 'direito', 'proibido',
'medicamento', 'tratamento', 'doenca', 'morte', 'vitimas',
'violencia', 'crime', 'acidente', 'tragedia',
'campeao', 'titulo', 'rebaixado', 'classificado'

# BUSCA AGORA (18 keywords)
'ao vivo', 'tempo real', 'resultado', 'como', 'quando', 'onde',
'cotacao', 'bolsa', 'mercado', 'investimento',
'eleicao', 'candidato', 'pesquisa', 'apuracao',
'lancamento', 'novo', 'atualizacao', 'vazamento',
'gol', 'placar', 'jogo', 'contratacao'

# CONVERSA (18 keywords)
'polemica', 'polemico', 'controverso', 'discussao', 'debate',
'critica', 'criticou', 'ataca', 'responde', 'rebate',
'corrupcao', 'fraude', 'mentira', 'fake', 'acusacao',
'racismo', 'preconceito', 'assedio', 'discriminacao', 'injustica',
'viral', 'treta', 'briga', 'conflito', 'provocacao'
```

**Lógica de decisão:**

```python
# Inesperado
≥ 2 matches → 'yes' (25 pts)
≥ 1 match  → 'partial' (12 pts)
0 matches  → 'no' (0 pts)

# Impacto (com relevance_boost)
≥ 2 matches OU (≥1 match + relevance_boost) → 'high' (30 pts)
≥ 1 match → 'medium' (15 pts)
0 matches → 'low' (0 pts)

# Busca Agora (com relevance_boost)
≥ 2 matches OU (≥1 match + relevance_boost) → 'yes' (25 pts)
≥ 1 match → 'maybe' (12 pts)
0 matches → 'no' (0 pts)

# Conversa (com relevance_boost)
≥ 2 matches OU (≥1 match + relevance_boost) → 'yes' (20 pts)
0 ou 1 match → 'no' (0 pts)
```

**Relevance Boost** — ativado se qualquer um destes 44 termos aparecer no texto:

```python
# Política
'governo', 'presidente', 'lula', 'bolsonaro', 'congresso', 'senado', 'stf',
'ministro', 'prefeitura', 'governador'

# Economia
'banco central', 'petrobras', 'vale', 'ibovespa', 'caixa', 'itau', 'bradesco'

# Esportes (16 termos — times grandes + competições)
'flamengo', 'corinthians', 'palmeiras', 'sao paulo', 'santos', 'gremio',
'internacional', 'cruzeiro', 'atletico', 'fluminense', 'botafogo', 'vasco',
'selecao', 'brasileirao', 'libertadores', 'copa do brasil'

# Tecnologia
'google', 'apple', 'microsoft', 'meta', 'amazon', 'openai', 'nvidia'

# Saúde
'sus', 'anvisa', 'ministerio da saude'

# Cultura
'globo', 'netflix', 'spotify'
```

### 6.7 Fluxo de Execução Completo

```
scoring_calculator_handler() [cada 10 min]
│
├── 1. Verifica conexão com banco
├── 2. get_scoring_service().process_pending_articles(limit=50)
│   │
│   ├── 2.1 _get_pending_articles(50)
│   │   └── SELECT articles WHERE NOT IN article_scores (LEFT JOIN)
│   │
│   ├── 2.2 score_articles_batch(articles, batch_delay=0.5s)
│   │   │
│   │   └── Para cada artigo:
│   │       ├── Tenta: _analyze_with_llm(title, content[:3000])
│   │       │   ├── Chama Claude com system + user prompt
│   │       │   ├── Extrai JSON da resposta
│   │       │   └── Valida campos obrigatórios
│   │       │
│   │       ├── Fallback: _heuristic_score_article(title, content)
│   │       │   └── Conta keywords → determina sinais
│   │       │
│   │       └── _calculate_scores(signals)
│   │           └── Converte sinais → pontos → total → classificação
│   │
│   └── 2.3 _save_scores(scores)
│       └── INSERT INTO article_scores (batch)
│
├── 3. _update_affected_theme_scores(db)
│   └── UPDATE themes SET avg_score, classification... (SQL batch)
│
└── 4. Log: distribuição A/B/C da última hora
```

### 6.8 Persistência no Banco

```sql
INSERT INTO article_scores
(article_id, sinal_inesperado, sinal_impacto, sinal_busca_agora, sinal_conversa,
 score_inesperado, score_impacto, score_busca_agora, score_conversa,
 total_score, classification, scored_by, reasoning, scored_at)
VALUES (...)
```

O `scored_by` indica o método: `'ai'` (Claude) ou `'manual'` (heurística fallback).

---

## 7. Geração de Embeddings

### 7.1 Configuração

| Parâmetro | Valor |
|-----------|-------|
| Modelo | `text-embedding-3-small` (OpenAI via Azure) |
| Dimensões | 1536 |
| Batch size | 50 textos por chamada API |
| Max texto | 8000 caracteres (título + conteúdo) |
| Timeout | 120 segundos |
| Frequência | A cada 5 minutos |

### 7.2 Preparação do Texto

```python
def _prepare_text(title, content) -> str:
    text = f"{title}\n{content or ''}"
    return text[:8000].strip()
```

### 7.3 Fluxo

```
embedding_generator_handler() [cada 5 min]
│
├── 1. Busca artigos sem embedding (limit 50)
│   └── WHERE has_embedding = 0
│
├── 2. Prepara texto (título + conteúdo, max 8000 chars)
│
├── 3. Gera embeddings em batch via Azure OpenAI
│   └── POST /openai/deployments/text-embedding-3-small/embeddings
│
├── 4. Salva vetores na tabela article_embeddings
│   └── JSON array de 1536 floats
│
└── 5. Marca artigo com has_embedding = 1
```

### 7.4 Armazenamento

```sql
CREATE TABLE article_embeddings (
    article_id UNIQUEIDENTIFIER PRIMARY KEY,
    embedding NVARCHAR(MAX),          -- JSON: [0.0123, -0.0456, ...]
    model_version VARCHAR(50),        -- "text-embedding-3-small"
    created_at DATETIME DEFAULT GETUTCDATE()
)
```

---

## 8. Clustering Semântico — Formação de Temas

### 8.1 Visão Geral

O sistema agrupa artigos em **temas semânticos** usando dois métodos complementares:

1. **Event-Based Clustering** — Matching por assinatura de evento (WHO/WHERE/WHAT/WHEN)
2. **Semantic Clustering** — Matching por similaridade de embedding (cosine similarity)

### 8.2 Constantes de Configuração

```python
CLUSTERING_SIMILARITY_THRESHOLD = 0.50   # Min cosine similarity para entrar em tema
CLUSTERING_EMA_ALPHA = 0.15              # Peso do novo embedding no centroide (EMA)
CLUSTERING_MERGE_THRESHOLD = 0.90        # Min similarity para merge de temas
CLUSTERING_BATCH_SIZE = 100              # Max artigos por execução
TEMPORAL_BOOST_HOURS = 48                # Janela temporal de boost
TEMPORAL_BOOST_AMOUNT = 0.05             # +5% de similarity boost
EMBEDDING_DIMENSION = 1536               # Dimensões do vetor
```

### 8.3 Algoritmo Principal (`process_pending_articles`)

```
clustering_engine_handler() [cada 30 min]
│
├── 1. Verificar se clustering está habilitado
├── 2. Carregar cache de temas ativos (com centroides)
├── 3. Buscar artigos pendentes (tem embedding, sem tema, limit=100)
│
└── 4. Para CADA artigo:
    │
    ├── ETAPA 1: Extrair Event Signature (se habilitado)
    │   └── LLM extrai: people, orgs, locations, action, canonical_key
    │
    ├── ETAPA 2: Tentar Event-Based Matching (se habilitado)
    │   ├── Stage 1: Canonical Key exato (confiança 0.98)
    │   ├── Stage 2: Entity Overlap ≥ 0.70 (confiança 0.70-0.90)
    │   ├── Stage 3: Embedding similarity ≥ 0.55 (fallback)
    │   └── Stage 4: LLM Verification (borderline 0.50-0.70)
    │
    ├── ETAPA 3: Fallback — Embedding Similarity
    │   └── find_best_theme(): cosine similarity ≥ 0.50
    │
    └── ETAPA 4: Resultado
        ├── Match encontrado → add_article_to_theme() + atualizar centroide
        └── Sem match → create_theme() com artigo como seed
```

### 8.4 Cosine Similarity

```python
def cosine_similarity(vec1, vec2) -> float:
    """
    Fórmula: dot(a,b) / (norm(a) * norm(b))
    Retorna: [0.0, 1.0]
    Vetores zero retornam 0.0
    """
    a, b = np.array(vec1), np.array(vec2)
    dot_product = np.dot(a, b)
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot_product / (norm_a * norm_b)))
```

### 8.5 Find Best Theme (Matching por Embedding)

```python
def find_best_theme(embedding, exclude_theme_ids, article_published_at):
    """
    1. Itera todos os temas ativos no cache
    2. Calcula cosine similarity com centroide de cada tema
    3. Aplica temporal boost (+5%) se artigo < 48h do último artigo do tema
    4. Retorna tema com maior similarity se ≥ 0.50
    """
    best_theme_id = None
    best_similarity = 0.0

    for theme in active_themes:
        sim = cosine_similarity(embedding, theme.centroid)

        # Temporal boost
        if article is within 48h of theme.last_updated_at:
            sim = min(1.0, sim + 0.05)

        if sim > best_similarity and sim >= 0.50:
            best_similarity = sim
            best_theme_id = theme.id

    return (best_theme_id, best_similarity) if best_theme_id else None
```

### 8.6 Atualização do Centroide (EMA)

Quando um artigo entra em um tema, o centroide é atualizado via **Exponential Moving Average**:

```
novo_centroide = α × novo_embedding + (1 - α) × centroide_atual

onde α = 0.15 (CLUSTERING_EMA_ALPHA)
```

**Por que EMA?**
- Reduz drift semântico ao longo do tempo
- α=0.15 significa: novo artigo influencia o centroide em 15%
- Artigos anteriores retêm 85% da influência
- Mais estável que calcular a média de todos os embeddings

```python
def update_theme_centroid(theme_id, new_embedding):
    old_centroid = get_centroid(theme_id)

    if old_centroid is None:
        new_centroid = new_embedding  # Primeiro artigo = centroide inicial
    else:
        alpha = 0.15
        new_centroid = alpha * new_embedding + (1 - alpha) * old_centroid

    new_centroid = normalize_to_unit_vector(new_centroid)
    save_centroid(theme_id, new_centroid)
```

### 8.7 Criação de Tema

Quando nenhum tema existente tem similarity ≥ 0.50, um novo tema é criado:

```python
def create_theme(article, embedding, name=None):
    # 1. Gera nome temporário a partir do título
    name = generate_temp_name(article.title)  # max 120 chars

    # 2. Gera slug URL-friendly
    slug = generate_slug(name)  # "politica-brasileira"

    # 3. Normaliza embedding para vetor unitário
    centroid = normalize_vector(embedding)

    # 4. Insere no banco
    theme = db.create_theme(name, slug, centroid, article_count=1)

    # 5. Registra artigo como seed
    db.add_article_to_theme(article.id, theme.id, similarity=1.0, is_seed=True)

    return theme
```

**Regras de nomeação temporária:**
- Título ≤ 120 chars → usa título completo
- Título > 120 chars → tenta cortar na fronteira de sentença (se ≥ 40 chars)
- Fallback → corta em delimitadores (`:`, `-`, `|`) se primeira parte ≥ 50 chars
- Último recurso → trunca na fronteira de palavra + "..."

---

## 9. Event Signatures — Clustering por Eventos

### 9.1 Extração de Assinatura (`services/event_signature_service.py`)

O sistema extrai uma "impressão digital" do evento descrito no artigo:

```json
{
  "people": ["João Silva", "Maria Santos"],
  "organizations": ["STF", "Petrobras"],
  "locations": ["Brasília", "São Paulo"],
  "event_action": "detido",
  "unique_details": ["operação policial", "R$ 5 milhões"],
  "event_date": "2026-02-10",
  "canonical_key": "joao-silva|stf|detido|brasilia|2026-02",
  "confidence": 0.85
}
```

**Prompt LLM para extração:**

```
System: You are a journalist event extraction expert.
Extract the specific event signature (WHO, WHERE, WHAT, WHEN).
Important:
- Extract PROPER NAMES, not generic descriptions
- Specific organizations (ICE, STF, Petrobras)
- Main action verb (detido, morreu, announced)
- List UNIQUE details identifying THIS specific event

User:
Analyze article:
TITULO: {title}
PREVIEW/CONTEUDO: {content}

Respond with JSON:
{
  "people": [],
  "organizations": [],
  "locations": [],
  "event_action": "verb",
  "unique_details": [],
  "event_date": "YYYY-MM-DD or null",
  "confidence": 0.95
}
```

**Fallback heurístico** (quando LLM indisponível):
- Regex para nomes capitalizados
- Acrônimos (2-6 letras maiúsculas)
- Padrões de localização (em/no/na + palavra capitalizada)
- Keywords de ação (detido, preso, morreu, anunciou, venceu, perdeu)
- Confiança baixa: 0.40

### 9.2 Canonical Key

Formato: `{person}|{org}|{action}|{location}|{month-year}`

Exemplos:
- `"empresario-brasileiro|ice|detido|eua|2026-02"`
- `"flamengo|null|venceu|maracana|2026-02"`
- `"lula|stf|absolvido|brasilia|2026-02"`

### 9.3 Event Matching Multi-Estágio (`services/event_matching_service.py`)

```
┌──────────────────────────────────────────────────────────┐
│ STAGE 1: Canonical Key Exato                              │
│ Confiança: 0.98                                           │
│ Se canonical_key == theme.canonical_event_key → MATCH     │
├──────────────────────────────────────────────────────────┤
│ STAGE 2: Entity Overlap                                   │
│ Calcula similaridade de entidades (com sinônimos)         │
│ ≥ 0.70 → MATCH (confiança 0.70-0.90)                    │
│   + sanity check embedding ≥ 0.50                        │
│ 0.50-0.70 → Precisa verificação LLM                      │
├──────────────────────────────────────────────────────────┤
│ STAGE 3: Embedding Similarity (Fallback)                  │
│ Cosine similarity com centroide do tema                   │
│ ≥ 0.55 → MATCH (confiança 0.55-0.70)                    │
├──────────────────────────────────────────────────────────┤
│ STAGE 4: LLM Verification (Borderline)                    │
│ Para entity overlap 0.50-0.70                             │
│ LLM compara: "Mesmo evento específico?"                   │
│ Se sim → MATCH (confiança 0.85)                          │
└──────────────────────────────────────────────────────────┘
```

### 9.4 Matching Inteligente de Entidades

O sistema suporta:

**Matching exato** (após normalização):
- "São Paulo" = "sao paulo"

**Sinônimos**:
```python
ENTITY_SYNONYMS = {
    'eua': 'estados unidos', 'usa': 'estados unidos',
    'policia federal': 'pf', 'supremo tribunal federal': 'stf',
    'sp': 'sao paulo', 'rj': 'rio de janeiro', 'df': 'brasilia',
    # ... 20+ mapeamentos
}
```

**Substring matching**:
- "Lula" ⊂ "Luiz Inacio Lula da Silva" → match

**Ações similares**:
```python
{detido, preso, aprisionado}     # mesma ação
{morreu, morto, faleceu, obito}   # mesma ação
{anunciou, declarou, anuncia}     # mesma ação
{venceu, ganhou, conquistou}      # mesma ação
```

Se `signature.action == theme.action` → +0.15 na similaridade de entidades.

---

## 10. Score do Tema (Composite Score)

### 10.1 Fórmula COMPOSITE

O score de um tema é calculado combinando os scores dos artigos que o compõem:

```
theme_score = max_score × 0.70 + avg_score × 0.30 + volume_bonus

onde:
  max_score     = maior total_score entre os artigos do tema
  avg_score     = média dos total_score de todos os artigos
  volume_bonus  = min(20, (article_count - 1) × 5)
```

### 10.2 Pesos

| Componente | Peso | Justificativa |
|-----------|------|--------------|
| Max Score | 70% | O artigo mais relevante define a importância do tema |
| Avg Score | 30% | Qualidade média dos artigos no tema |
| Volume Bonus | +5 pts/artigo, max 20 | Temas com mais cobertura são mais relevantes |

### 10.3 Exemplos

**Tema com 3 artigos [70, 60, 50]:**
```
max = 70, avg = 60, volume_bonus = min(20, 2×5) = 10
score = 70×0.7 + 60×0.3 + 10 = 49 + 18 + 10 = 77 → Classe A
```

**Tema com 1 artigo [85]:**
```
max = 85, avg = 85, volume_bonus = min(20, 0×5) = 0
score = 85×0.7 + 85×0.3 + 0 = 59.5 + 25.5 = 85 → Classe A
```

**Tema com 5 artigos [45, 30, 25, 20, 15]:**
```
max = 45, avg = 27, volume_bonus = min(20, 4×5) = 20
score = 45×0.7 + 27×0.3 + 20 = 31.5 + 8.1 + 20 = 59.6 → Classe B
```

### 10.4 Classificação do Tema

Usa os mesmos thresholds dos artigos, mas aplicados ao `avg_score`:

```sql
UPDATE themes SET classification = CASE
    WHEN avg_score >= 75 THEN 'A'
    WHEN avg_score >= 40 THEN 'B'
    ELSE 'C'
END
```

### 10.5 Atualização de Scores (SQL)

Executada a cada ciclo do scoring_calculator e na manutenção diária:

```sql
UPDATE t
SET
    t.avg_score = scores.avg_score,
    t.max_score = scores.max_score,
    t.min_score = scores.min_score,
    t.classification = CASE
        WHEN scores.avg_score >= 75 THEN 'A'
        WHEN scores.avg_score >= 40 THEN 'B'
        ELSE 'C'
    END,
    t.last_updated_at = GETUTCDATE()
FROM themes t
INNER JOIN (
    SELECT
        at.theme_id,
        AVG(CAST(s.total_score AS FLOAT)) as avg_score,
        MAX(s.total_score) as max_score,
        MIN(s.total_score) as min_score
    FROM article_themes at
    INNER JOIN article_scores s ON at.article_id = s.article_id
    GROUP BY at.theme_id
) scores ON t.id = scores.theme_id
WHERE t.status = 'active'
```

### 10.6 Metadados Adicionais do Tema (API)

A API do tema também expõe:

| Campo | Descrição | Cálculo |
|-------|-----------|---------|
| `recentArticleCount` | Artigos adicionados nas últimas 24h | COUNT WHERE assigned_at ≥ -24h |
| `trend` | Tendência | `>30% recentes` → up, `<10% recentes + >5 total` → down, senão stable |
| `isEmergent` | Tema emergente | Criado <48h + ≥3 artigos + >50% são recentes |
| `representativeTags` | Top 5 tags | Tags mais frequentes dos artigos (OPENJSON) |
| `scoreBreakdown` | Média por sinal | AVG de cada score individual |

---

## 11. Manutenção de Temas

### 11.1 Tarefas Diárias (3h UTC)

```
clustering_maintenance_handler()
│
├── 1. merge_similar_themes()
│   ├── Carrega todos os temas ativos com centroides
│   ├── Calcula similaridade par-a-par (O(n²))
│   ├── Para pares com similarity ≥ 0.90:
│   │   ├── Tema maior = target, menor = source
│   │   ├── Move artigos do source → target
│   │   ├── Ajusta similarity scores (* merge_similarity)
│   │   ├── Desativa source (status='merged')
│   │   └── Atualiza article_count do target
│   └── Retorna número de merges
│
├── 2. cleanup_orphan_themes()
│   ├── Encontra temas com article_count=0 ou sem artigos
│   ├── Desativa (status='inactive')
│   └── Retorna número de temas desativados
│
├── 3. recalculate_all_scores()
│   ├── Para cada tema ativo: calculate_theme_score()
│   └── Atualiza banco com novo score
│
└── 4. generate_quality_metrics()
    ├── Total temas ativos/inativos
    ├── Distribuição de artigos (avg, min, max, std dev)
    ├── Distribuição de scores (avg, min, max)
    ├── Contagem A/B/C
    └── Artigos pendentes
```

### 11.2 Qualidade do Clustering (Silhouette Score)

```python
silhouette(i) = (b(i) - a(i)) / max(a(i), b(i))

onde:
  a(i) = distância média intra-cluster (dentro do mesmo tema)
  b(i) = menor distância média inter-cluster (para o tema mais próximo)

Range: [-1, +1]
  +1 = cluster bem definido
   0 = clusters sobrepostos
  -1 = artigo no cluster errado
```

### 11.3 Níveis de Qualidade

| Score | Nível | Interpretação |
|-------|-------|--------------|
| silhouette ≥ 0.5, coverage ≥ 0.9, avg_articles ≥ 5 | excellent | Clustering otimo |
| silhouette ≥ 0.3, coverage ≥ 0.7, avg_articles ≥ 3 | good | Funcionando bem |
| silhouette ≥ 0.1, coverage ≥ 0.5, avg_articles ≥ 2 | fair | Pode melhorar |
| abaixo | poor | Precisa ajustar parâmetros |

---

## 12. Geração de Matérias via LLM

### 12.1 Categorias Editoriais

O sistema gera matérias com tom e estilo específicos por categoria:

| Categoria | Estilo | Tom |
|-----------|--------|-----|
| Esportes | CazéTV-style | Emocional, gírias, humor |
| Entretenimento | The News + Pop | Leve, criativo, trocadilhos |
| Política | Sóbrio/Didático | Direto, explica termos técnicos |
| Economia | Traduz para cotidiano | Exemplos concretos (salário, aluguel) |
| Geral | Conversacional | "Você provavelmente já..." |

### 12.2 Tipos de Matéria

| Tipo | Estrutura | Parágrafos |
|------|-----------|-----------|
| Destaque | lide → nutgraf → desenvolvimento → contexto → desdobramentos | 5-10 |
| Coluna | gancho → tese → argumentos → contra-argumento → conclusão | 6-12 |
| Serviço | contexto → o que muda → passo a passo → FAQ | 5-8 |
| Análise | fato gerador → contexto → análise → cenários → perspectivas | 8-15 |
| Reportagem | cena/lide → contexto → desenvolvimento → vozes → fechamento | 10-20 |
| Nota | lide → contexto breve → fonte/créditos | 2-4 |

### 12.3 Comprimento Dinâmico

O tamanho mínimo da matéria depende do tamanho da fonte:

| Chars da Fonte | Tipo | Min chars | Max chars |
|---------------|------|-----------|-----------|
| 0-150 | nota curta | 200 | 400 |
| 150-500 | matéria curta | 600 | 1200 |
| 500-1500 | matéria média | 1200 | 2500 |
| 1500-3000 | matéria longa | 1800 | 3500 |
| 3000+ | matéria completa | 2000 | 4000 |

### 12.4 Regras Anti-Fabricação (FIDELIDADE FACTUAL)

As regras mais críticas do sistema:

```
REGRAS OBRIGATÓRIAS:
1. USE APENAS informações presentes no TEXTO-BASE e CONTEXTO VERIFICADO
2. NÃO invente nomes, números, estatísticas, datas ou citações
3. NÃO use conhecimento de treinamento mesmo que "lembre"
4. PROIBIDO: completar placares, resultados, valores monetários
5. PROIBIDO: adicionar contexto histórico não presente nas fontes
6. PROIBIDO: misturar eventos diferentes

PADRÕES PROIBIDOS:
- Especificidade temporal: NÃO invente "nesta quinta-feira", horários, datas
- Asserções negativas: NÃO diga "X não se pronunciou" — OMITA
- Preenchimento editorial: NÃO invente "um dos dias de maior movimento"
- Inferência causal: NÃO crie relações causa-efeito não explícitas
- Expansão de citações: NÃO parafraseie citações adicionando significado

REGRA DE OURO: Se um dado específico NÃO aparece literalmente nas fontes,
NÃO o inclua.
```

### 12.5 SEO e Legibilidade

**Título:** 7-10 palavras, 50-60 caracteres
**Linha fina:** 20-25 palavras, 150-160 caracteres
**Primeiro parágrafo:** 40-60 palavras (WHAT, WHO, WHEN, WHERE)

**Flesch-PT ≥ 60 (obrigatório):**
- Sentenças: 12-15 palavras (max absoluto: 20)
- Vocabulário simples (1-3 sílabas)
- Voz ativa
- Parágrafos de 2-3 sentenças

**Atribuição (E-E-A-T):**
- 3+ atribuições nomeadas por matéria
- 2+ verbos de reporte (disse, afirmou, declarou)
- 2+ dados verificáveis

---

## 13. Pipeline Anti-Alucinação (Fact-Check)

### 13.1 As 4 Fases

```
┌──────────────────────────────────────────────────────────────┐
│ FASE 1: ENRIQUECIMENTO PRÉ-GERAÇÃO (Exa Search)            │
│ - Busca web por artigos similares                            │
│ - Extração de fatos verificados                              │
│ - Cross-contamination guard                                  │
├──────────────────────────────────────────────────────────────┤
│ FASE 2: GERAÇÃO (LLM com prompts endurecidos)              │
│ - System prompt com fidelidade factual                       │
│ - User prompt com contexto verificado                        │
│ - Temporal decontamination (pós-geração)                     │
├──────────────────────────────────────────────────────────────┤
│ FASE 3: VERIFICAÇÃO PÓS-GERAÇÃO                            │
│ 3A. Extração de claims + grounding (LLM)                    │
│ 3B. Comparação de entidades (regex)                         │
│ 3C. Verificação de citações (string matching)               │
│ 3D. CoVe — Chain-of-Verification (2 chamadas LLM)          │
│ 3E. Confidence scoring (6 componentes ponderados)           │
├──────────────────────────────────────────────────────────────┤
│ FASE 4: SAFETY GATES                                        │
│ - Blocks duros (publicação bloqueada)                       │
│ - Revisão humana (soft gates)                               │
│ - Readability check                                          │
└──────────────────────────────────────────────────────────────┘
```

### 13.2 Fase 1: Enriquecimento via Exa

```python
# Busca web
exa_search(query=titulo_fonte, max_results=5, days=7)

# Modo agressivo (fonte < 500 chars):
# - 3 queries em vez de 2
# - Até 10 resultados
# - 4000 chars por resultado (vs 2000)
# - 15 fatos extraídos (vs 8)
# - Limite de contexto: 6000 chars (vs 3000)
```

**Cross-Contamination Guard:**
- Fatos extraídos devem compartilhar ≥1 nome próprio com o texto-fonte
- Evita que dados de eventos SIMILARES mas DIFERENTES contaminem o artigo

**Gov Whitelist:** Domínios `.gov.br`, `.leg.br`, `.jus.br` são fontes de alta autoridade.

### 13.3 Fase 3A: Extração e Classificação de Claims

O LLM analisa o artigo gerado vs fonte e classifica cada claim:

| Verdict | Significado | Impacto no Score |
|---------|------------|-----------------|
| `grounded` | Informação presente na fonte/contexto | Positivo |
| `context` | Contexto factual correto que enriquece | Positivo (conta como factual) |
| `opinion` | Análise subjetiva, previsões | Neutro (não conta) |
| `unverifiable` | Impossível confirmar com material disponível | Neutro |
| `fabricated` | INCORRETO, DESCONEXO ou CONTRADIZ fontes | Muito negativo |
| `inaccurate` | Distorcido (números errados, nomes trocados) | Negativo |

**Regra editorial:** Fabricações factualmente corretas são ACEITÁVEIS se coerentes com o tema. Só bloqueia fabricações INCORRETAS ou DESCONEXAS.

### 13.4 Fase 3D: CoVe (Chain-of-Verification)

Para claims marcados como `fabricated`, aplica verificação em 2 etapas:

**Etapa 1 — Geração de Q&A (768 tokens):**
```
System: "Verificador factual. Gere perguntas e responda com base no material."

Prompt:
  AFIRMAÇÃO: [claim text]
  TEXTO-FONTE: [source truncado a 4000 chars]
  [CONTEXTO VERIFICADO se disponível]

  Gere 3 perguntas de verificação e responda cada uma.
```

**Etapa 2 — Reclassificação (512 tokens):**
```
System: "Classificador factual. Re-classifique com base nas Q&A."

Prompt:
  AFIRMAÇÃO SUSPEITA: [claim text]
  PERGUNTAS E RESPOSTAS:
  P1: ... R1: ...
  P2: ... R2: ...
  P3: ... R3: ...

  Reclassifique: grounded|context|opinion|unverifiable|fabricated
```

**Bônus de confiança por reclassificação:**
- evidence_strength "strong": +0.08
- evidence_strength "moderate": +0.05
- evidence_strength "weak": +0.02

### 13.5 Confidence Score — 6 Componentes

```
confidence = 0.45 × claim_score
           + 0.15 × entity_score
           + 0.10 × expansion_score
           + 0.10 × quote_score
           + 0.10 × sufficiency_score
           + 0.10 × similarity_score
```

| Componente | Peso | Cálculo |
|-----------|------|---------|
| **Claim Grounding** | 0.45 | grounded_ratio - fabrication_penalty |
| **Entity Overlap** | 0.15 | Jaccard(common_entities, all_entities) |
| **Expansion Ratio** | 0.10 | Baseado em output_length / source_length |
| **Quote Verification** | 0.10 | verified_quotes / total_quotes (0.5 se sem citações) |
| **Material Sufficiency** | 0.10 | sufficient=1.0, marginal=0.5, insufficient=0.2 |
| **Claim-Source Similarity** | 0.10 | TF-IDF cosine similarity (sem API) |

**Fabrication Penalty (não-linear):**

| Fabricações | Penalidade |
|------------|-----------|
| 0 | 0.00 |
| 1 | 0.30 |
| 2 | 0.55 |
| 3+ | 0.80 |

**Expansion Ratio Score:**

| Ratio (output/source) | Score |
|----------------------|-------|
| ≤ 3x | 1.0 |
| 3-5x | 0.8 |
| 5-10x | 0.5 |
| 10-25x | 0.2 |
| > 25x | 0.0 |

**Ajustes pós-cálculo:**
- Expansion >10x → confidence capped a 0.50
- ≥3 entidades novas e >50% do output → confidence capped a 0.55
- CoVe reclassificou → +bonus baseado em evidence_strength

### 13.6 Risk Level

| Confiança | Nível Base |
|-----------|-----------|
| ≥ 0.80 | low |
| ≥ 0.50 | medium |
| ≥ 0.30 | high |
| < 0.30 | critical |

**Overrides automáticos:**
- 3+ fabricações → CRITICAL
- 2 fabricações + confidence <0.35 → CRITICAL
- 2 fabricações → HIGH
- Expansion >25x → HIGH
- Expansion >15x → LOW→MEDIUM
- <50% citações verificadas → HIGH
- ≥3 entidades novas >50% → HIGH
- ≥3 unverifiable >40% → HIGH

---

## 14. Safety Gates — Publicação

### 14.1 Hard Blocks (publish_blocked = true)

| Condição | Descrição |
|----------|-----------|
| Risk level = CRITICAL | Risco inaceitável |
| Confidence < 0.50 | Abaixo do piso de confiança (produção) |
| ≥ 2 fabricações | Múltiplas fabricações |
| 1 fabricação + confidence < 0.50 | Fabricação com confiança baixa |
| ≥ 3 unverifiable + >40% total | Excesso de claims não-verificáveis |
| Expansion > 15x | Expansão extrema |

### 14.2 Soft Gates (requires_human_review = true)

| Condição | Descrição |
|----------|-----------|
| 1 fabricação + confidence ≥ 0.50 | Fabricação isolada mas confiança OK |
| ≥ 2 unverifiable + >30% total | Vários claims não-verificáveis |
| ≥ 4 entidades novas + >60% output | Muitas entidades não da fonte |
| 10x < expansion ≤ 15x | Expansão alta |
| Risk level = HIGH (não bloqueado) | Risco alto mas não crítico |
| Flesch < 42 | Legibilidade abaixo do threshold PT-BR |

### 14.3 Detecção de Tópicos Sensíveis

| Tópico | Safeguard |
|--------|-----------|
| `menor_de_idade` | Não divulgar nome, não detalhar violência |
| `suicidio` | Não descrever método, incluir CVV: 188 |
| `violencia_sexual` | Não descrever detalhes, foco na vítima como sobrevivente |

---

## 15. Schema do Banco de Dados

### 15.1 Tabelas Principais

```sql
-- Fontes RSS
CREATE TABLE sources (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name NVARCHAR(255) NOT NULL,
    url NVARCHAR(2048) NOT NULL,
    favicon_url NVARCHAR(2048),
    category NVARCHAR(50),
    frequency NVARCHAR(10) DEFAULT '1h',     -- '15min','30min','1h','2h','6h'
    active BIT DEFAULT 1,
    last_fetch DATETIME,
    last_error NVARCHAR(MAX),
    articles_count INT DEFAULT 0,
    created_at DATETIME DEFAULT GETUTCDATE(),
    updated_at DATETIME DEFAULT GETUTCDATE()
);

-- Artigos coletados
CREATE TABLE collected_articles (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    source_id UNIQUEIDENTIFIER REFERENCES sources(id),
    title NVARCHAR(1000) NOT NULL,
    content NVARCHAR(MAX),
    preview NVARCHAR(500),
    url NVARCHAR(2048) NOT NULL,
    image_url NVARCHAR(2048),
    author NVARCHAR(255),
    category NVARCHAR(50),
    tags NVARCHAR(MAX),                       -- JSON: ["tag1", "tag2"]
    published_at DATETIME,
    collected_at DATETIME DEFAULT GETUTCDATE(),
    hash NVARCHAR(64) UNIQUE,                 -- SHA256
    has_score BIT DEFAULT 0,
    has_embedding BIT DEFAULT 0,
    primary_theme_id UNIQUEIDENTIFIER
);

-- Scores editoriais
CREATE TABLE article_scores (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    article_id UNIQUEIDENTIFIER UNIQUE REFERENCES collected_articles(id) ON DELETE CASCADE,
    sinal_inesperado NVARCHAR(10),            -- yes/partial/no
    sinal_impacto NVARCHAR(10),               -- high/medium/low
    sinal_busca_agora NVARCHAR(10),           -- yes/maybe/no
    sinal_conversa NVARCHAR(10),              -- yes/no
    score_inesperado INT CHECK (score_inesperado IN (0, 12, 25)),
    score_impacto INT CHECK (score_impacto IN (0, 15, 30)),
    score_busca_agora INT CHECK (score_busca_agora IN (0, 12, 25)),
    score_conversa INT CHECK (score_conversa IN (0, 20)),
    total_score INT CHECK (total_score BETWEEN 0 AND 100),
    classification CHAR(1) CHECK (classification IN ('A', 'B', 'C')),
    scored_by NVARCHAR(50),                   -- 'ai' ou 'manual'
    reasoning NVARCHAR(MAX),
    scored_at DATETIME2
);

-- Embeddings
CREATE TABLE article_embeddings (
    article_id UNIQUEIDENTIFIER PRIMARY KEY REFERENCES collected_articles(id),
    embedding NVARCHAR(MAX),                  -- JSON: [float × 1536]
    model_version VARCHAR(50),                -- "text-embedding-3-small"
    created_at DATETIME DEFAULT GETUTCDATE()
);

-- Temas semânticos
CREATE TABLE themes (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name NVARCHAR(255) NOT NULL,
    slug NVARCHAR(255) UNIQUE NOT NULL,
    centroid NVARCHAR(MAX),                   -- JSON: [float × 1536]
    article_count INT DEFAULT 0,
    avg_score FLOAT DEFAULT 0.0,
    min_score FLOAT DEFAULT 0.0,
    max_score FLOAT DEFAULT 0.0,
    classification NVARCHAR(10),              -- A/B/C ou JSON metadata
    status NVARCHAR(20) DEFAULT 'active',     -- active/inactive/merged/expired
    canonical_event_key NVARCHAR(500),
    primary_entities NVARCHAR(MAX),           -- JSON: {people, orgs, locs, action}
    seed_article_id UNIQUEIDENTIFIER,
    first_seen_at DATETIME DEFAULT GETUTCDATE(),
    last_updated_at DATETIME DEFAULT GETUTCDATE(),
    expires_at DATETIME NULL
);

-- Relação artigo ↔ tema
CREATE TABLE article_themes (
    article_id UNIQUEIDENTIFIER REFERENCES collected_articles(id),
    theme_id UNIQUEIDENTIFIER REFERENCES themes(id),
    similarity_score FLOAT,                   -- 0-1 cosine similarity
    match_type NVARCHAR(20),                  -- exact/entity/verified/embedding/seed
    is_seed BIT DEFAULT 0,
    assigned_at DATETIME DEFAULT GETUTCDATE(),
    PRIMARY KEY (article_id, theme_id)
);

-- Assinaturas de evento
CREATE TABLE event_signatures (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    article_id UNIQUEIDENTIFIER UNIQUE REFERENCES collected_articles(id),
    theme_id UNIQUEIDENTIFIER REFERENCES themes(id),
    people NVARCHAR(MAX),                     -- JSON array
    organizations NVARCHAR(MAX),              -- JSON array
    locations NVARCHAR(MAX),                  -- JSON array
    event_action NVARCHAR(100),
    unique_details NVARCHAR(MAX),             -- JSON array
    canonical_key NVARCHAR(500),
    event_date DATE,
    confidence FLOAT,
    extracted_at DATETIME DEFAULT GETUTCDATE()
);

-- Logs de coleta
CREATE TABLE collection_logs (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    source_id UNIQUEIDENTIFIER,
    started_at DATETIME,
    finished_at DATETIME,
    status NVARCHAR(20),                      -- success/error
    articles_found INT,
    articles_new INT,
    articles_duplicate INT,
    error_message NVARCHAR(MAX),
    duration_ms INT
);
```

### 15.2 Índices Relevantes

```sql
CREATE INDEX IX_article_scores_classification ON article_scores(classification);
CREATE INDEX IX_article_scores_total ON article_scores(total_score DESC);
CREATE INDEX IX_collected_articles_has_score ON collected_articles(has_score) WHERE has_score = 0;
CREATE INDEX IX_collected_articles_has_embedding ON collected_articles(has_embedding) WHERE has_embedding = 0;
CREATE INDEX IX_themes_status ON themes(status);
CREATE INDEX IX_article_themes_theme ON article_themes(theme_id);
CREATE INDEX IX_event_signatures_canonical ON event_signatures(canonical_key);
```

---

## 16. Endpoints da API

### 16.1 Artigos e Feed

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/articles` | Lista artigos com filtros, paginação, urgência |
| GET | `/api/articles/{id}` | Detalhes de um artigo |
| GET | `/api/categories` | Categorias com contagem |
| GET | `/api/trending-tags` | Tags trending com contagem |
| GET | `/api/tags` | Todas as tags com busca |

**Filtros de `/api/articles`:**
- `category`: filtro exato
- `source_id`: nome da fonte
- `period`: 'today', 'week', 'month', ou N horas
- `search`: LIKE em título/conteúdo/tags
- `tag`: busca na array JSON de tags

**Urgência (retornada com cada consulta):**
- `now`: artigos < 1 hora
- `recent`: artigos < 3 horas
- `today`: artigos < 8 horas
- `all`: total (24h)

### 16.2 Temas Semânticos

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/semantic-themes` | Lista temas com filtros e stats |
| GET | `/api/semantic-themes/{id}` | Detalhes do tema com artigos |
| GET | `/api/clustering-stats` | Métricas de qualidade do clustering |

**Filtros de `/api/semantic-themes`:**
- `classification`: A, B ou C
- `status`: active, inactive
- `sort`: score, articles, recent
- `limit`, `page`: paginação

### 16.3 Fontes RSS

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/sources` | Lista todas as fontes |
| GET | `/api/sources/{id}` | Detalhes da fonte |
| POST | `/api/sources` | Cria nova fonte |
| PUT | `/api/sources/{id}` | Atualiza fonte |
| DELETE | `/api/sources/{id}` | Desativa fonte (soft delete) |
| POST | `/api/sources/{id}/collect` | Coleta manual |

### 16.4 Geração e IA

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/generate` | Gera matéria via LLM |
| POST | `/api/extract-topics` | Extrai tópicos de texto |
| POST | `/api/generate-tags` | Gera tags |
| POST | `/api/merge-topics` | Merge de tópicos |
| POST | `/api/edit-article` | Edita matéria com IA |

### 16.5 Saúde e Monitoramento

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/health` | Health check (v7.0.0) |
| GET | `/api/stats` | Estatísticas de coleta |
| GET | `/api/metrics` | Métricas in-process do pipeline |

---

## 17. Configuração Completa

### 17.1 Thresholds de Scoring

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `THRESHOLD_A` | 75 | Score mínimo para Classe A |
| `THRESHOLD_B` | 40 | Score mínimo para Classe B |
| `SCORING_MAX_TOKENS` | 1024 | Max tokens da resposta LLM |
| `MAX_ARTICLES_PER_RUN` | 50 | Artigos por ciclo de scoring |
| Content truncation | 3000 chars | Truncamento do conteúdo para análise |
| Batch delay | 0.5s | Delay entre chamadas LLM (rate limiting) |

### 17.2 Thresholds de Clustering

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `CLUSTERING_SIMILARITY_THRESHOLD` | 0.50 | Min cosine similarity para tema |
| `CLUSTERING_EMA_ALPHA` | 0.15 | Peso do novo embedding no centroide |
| `CLUSTERING_MERGE_THRESHOLD` | 0.90 | Min similarity para merge |
| `CLUSTERING_BATCH_SIZE` | 100 | Max artigos por ciclo |
| `TEMPORAL_BOOST_HOURS` | 48 | Janela de temporal boost |
| `TEMPORAL_BOOST_AMOUNT` | 0.05 | +5% similarity boost |
| `EMBEDDING_DIMENSION` | 1536 | Dimensões do vetor |

### 17.3 Thresholds de Event Matching

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `EXACT_MATCH_CONFIDENCE` | 0.98 | Confiança para canonical key exato |
| `ENTITY_MATCH_HIGH_THRESHOLD` | 0.70 | Entity overlap alto (confia) |
| `ENTITY_MATCH_LOW_THRESHOLD` | 0.50 | Entity overlap médio (verifica) |
| `EMBEDDING_SIMILARITY_THRESHOLD` | 0.55 | Min embedding para standalone match |
| `EMBEDDING_SANITY_CHECK_THRESHOLD` | 0.50 | Min embedding para validar entity match |

### 17.4 Score do Tema (Composite)

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `SCORE_MAX_WEIGHT` | 0.70 | Peso do max score |
| `SCORE_AVG_WEIGHT` | 0.30 | Peso do avg score |
| `VOLUME_BONUS_MAX` | 20 | Bônus máximo por volume |
| `VOLUME_BONUS_PER_ARTICLE` | 5 | +5 pts por artigo adicional |

### 17.5 Confidence Score (Fact-Check v7)

| Componente | Peso | Descrição |
|-----------|------|-----------|
| Claim Grounding | 0.45 | Claims fundamentados nas fontes |
| Entity Overlap | 0.15 | Entidades em comum (fonte vs output) |
| Expansion Ratio | 0.10 | Razão output/source |
| Quote Verification | 0.10 | Citações verificadas |
| Material Sufficiency | 0.10 | Suficiência do material fonte |
| Claim-Source Similarity | 0.10 | TF-IDF similarity |

### 17.6 Safety Gates (Produção v7.1)

| Gate | Threshold | Ação |
|------|-----------|------|
| Confidence floor | < 0.50 | BLOCK |
| Fabricated claims | ≥ 2 | BLOCK |
| Fabricated + low confidence | 1 + < 0.50 | BLOCK |
| Unverifiable excess | ≥ 3 + >40% | BLOCK |
| Extreme expansion | > 15x | BLOCK |
| Novel entities | ≥ 4 + >60% | REVIEW |
| High expansion | 10-15x | REVIEW |
| Low Flesch | < 42 | REVIEW |

### 17.7 Embedding

| Parâmetro | Valor |
|-----------|-------|
| Modelo | `text-embedding-3-small` (Azure OpenAI) |
| Dimensões | 1536 |
| Batch size | 50 |
| Max texto | 8000 chars |
| Timeout | 120s |

### 17.8 RSS Collection

| Parâmetro | Valor |
|-----------|-------|
| `RSS_FETCH_TIMEOUT` | 30s |
| `RSS_MAX_CONCURRENT` | 10 |
| `RSS_MAX_ARTICLES_PER_FEED` | 100 |
| Dedup hash | SHA256(url\|title) |
| Dedup similarity | Jaccard ≥ 0.85 |
| Artigos mantidos | 24 horas |

---

## Diagrama de Fluxo Completo

```
                    ┌─────────────┐
                    │  27 Feeds   │
                    │    RSS      │
                    └──────┬──────┘
                           │ a cada 15 min
                           ▼
                    ┌──────────────┐
                    │  RSS Parser  │ feedparser + httpx
                    │  + Dedup     │ SHA256 + Jaccard ≥ 0.85
                    │  + Enrich    │ OG images + AI tags
                    └──────┬───────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   collected_articles    │ ← Azure SQL
              │   (~artigos / 24h)     │
              └────┬──────┬──────┬─────┘
                   │      │      │
          ┌────────┘      │      └────────┐
          ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ Embedding  │  │  Scoring   │  │ (artigos   │
   │ Generator  │  │ Calculator │  │  na API)   │
   │  (5 min)   │  │  (10 min)  │  └────────────┘
   │ OpenAI 1536│  │ Claude A/B/C│
   └─────┬──────┘  └──────┬─────┘
         │                │
         ▼                ▼
   ┌────────────┐  ┌────────────┐
   │ article_   │  │ article_   │
   │ embeddings │  │ scores     │
   └─────┬──────┘  └──────┬─────┘
         │                │
         └───────┬────────┘
                 │
                 ▼
          ┌────────────┐
          │ Clustering │ a cada 30 min
          │   Engine   │ similarity ≥ 0.50
          │            │ event matching
          └──────┬─────┘
                 │
                 ▼
          ┌────────────┐     ┌──────────────┐
          │   themes    │────▶│ theme score  │
          │ article_    │     │ = max×0.7    │
          │  themes     │     │ + avg×0.3    │
          └──────┬──────┘     │ + vol bonus  │
                 │            └──────────────┘
                 │
                 ▼
          ┌────────────┐
          │  Frontend  │ React
          │  (redação) │
          └──────┬─────┘
                 │ seleciona tema + artigos
                 ▼
          ┌────────────┐
          │  /generate │ POST
          └──────┬─────┘
                 │
     ┌───────────┤
     ▼           ▼
┌─────────┐ ┌──────────┐
│ Exa     │ │ LLM Gen  │
│ Enrich  │ │ (Claude) │
│ (Fase 1)│ │ (Fase 2) │
└────┬────┘ └────┬─────┘
     │           │
     └─────┬─────┘
           ▼
     ┌───────────┐
     │ Fact-Check│ (Fase 3)
     │ Claims    │ 6 componentes
     │ Entities  │ confidence
     │ Quotes    │ score
     │ CoVe      │
     └─────┬─────┘
           │
           ▼
     ┌───────────┐
     │  Safety   │ (Fase 4)
     │  Gates    │ block / review / publish
     └─────┬─────┘
           │
           ▼
     ┌───────────┐
     │ Resultado │ título + conteúdo + verificação + schema.org
     └───────────┘
```

---

*Documentação gerada em 2026-02-12. Baseada no código-fonte v7.1 do TMC Ferramenta.*
