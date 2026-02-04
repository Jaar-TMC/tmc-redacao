# Plano: Sistema de Temas Semânticos com Classificação Editorial A/B/C

## Resumo Executivo

Transformar o sistema atual de "temas quentes" (baseado em contagem de tags) para um sistema inteligente com:
1. **Agrupamento semântico** usando embeddings para clusterizar matérias em temas coesos
2. **Classificação editorial A/B/C** baseada em 4 sinais (inesperado, impacto, busca_agora, conversa)
3. **Scores** para matérias individuais E para temas agregados

---

## Fase 1: Schema de Banco de Dados

### 1.1 Novas Tabelas no Azure SQL

**Decisão: Usar tipo VECTOR nativo do Azure SQL** (disponível desde Jun 2025)

```sql
-- Tabela: article_embeddings (armazena embeddings 1536 dimensões)
CREATE TABLE article_embeddings (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    article_id UNIQUEIDENTIFIER NOT NULL UNIQUE,
    embedding VECTOR(1536) NOT NULL,
    model_version NVARCHAR(50) DEFAULT 'text-embedding-3-small',
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (article_id) REFERENCES collected_articles(id) ON DELETE CASCADE
);

-- Tabela: themes (clusters semânticos)
CREATE TABLE themes (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name NVARCHAR(255) NOT NULL,
    slug NVARCHAR(255) NOT NULL UNIQUE,
    centroid VECTOR(1536) NULL,
    article_count INT DEFAULT 0,
    avg_score DECIMAL(5,2) DEFAULT 0,
    classification CHAR(1) NULL, -- A, B, C
    status NVARCHAR(20) DEFAULT 'active',
    first_seen_at DATETIME2 DEFAULT GETUTCDATE(),
    last_updated_at DATETIME2 DEFAULT GETUTCDATE()
);

-- Tabela: article_themes (relação N:N artigo-tema)
CREATE TABLE article_themes (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    article_id UNIQUEIDENTIFIER NOT NULL,
    theme_id UNIQUEIDENTIFIER NOT NULL,
    similarity_score DECIMAL(5,4) NOT NULL,
    is_seed BIT DEFAULT 0,
    assigned_at DATETIME2 DEFAULT GETUTCDATE(),
    UNIQUE (article_id, theme_id)
);

-- Tabela: article_scores (scoring editorial)
CREATE TABLE article_scores (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    article_id UNIQUEIDENTIFIER NOT NULL UNIQUE,
    sinal_inesperado NVARCHAR(10) DEFAULT 'no',    -- yes/partial/no
    sinal_impacto NVARCHAR(10) DEFAULT 'low',       -- high/medium/low
    sinal_busca_agora NVARCHAR(10) DEFAULT 'no',    -- yes/maybe/no
    sinal_conversa NVARCHAR(10) DEFAULT 'no',       -- yes/no
    score_inesperado INT DEFAULT 0,
    score_impacto INT DEFAULT 0,
    score_busca_agora INT DEFAULT 0,
    score_conversa INT DEFAULT 0,
    total_score INT DEFAULT 0,
    classification CHAR(1) DEFAULT 'C',
    scored_by NVARCHAR(50) DEFAULT 'ai',
    scored_at DATETIME2 DEFAULT GETUTCDATE()
);
```

### 1.2 Alterações na Tabela Existente

```sql
ALTER TABLE collected_articles ADD
    has_embedding BIT DEFAULT 0,
    has_score BIT DEFAULT 0,
    primary_theme_id UNIQUEIDENTIFIER NULL;
```

---

## Fase 2: Serviços Backend (Azure Functions)

### 2.1 Novos Arquivos a Criar

```
FeedRSS/tmc-rss-collector/
├── services/
│   ├── embedding_service.py    # NOVO - Gera embeddings via OpenAI
│   ├── scoring_service.py      # NOVO - Calcula scores A/B/C via Claude
│   └── clustering_service.py   # NOVO - Agrupa artigos em temas
├── functions/
│   ├── embedding_generator.py  # NOVO - Timer trigger 5min
│   ├── scoring_calculator.py   # NOVO - Timer trigger 10min
│   ├── clustering_engine.py    # NOVO - Timer trigger 30min
│   └── themes_api.py           # NOVO - HTTP endpoints
└── models/
    ├── theme.py                # NOVO - Pydantic model
    └── article_score.py        # NOVO - Pydantic model
```

### 2.2 EmbeddingService

- **Modelo**: `text-embedding-3-small` (OpenAI/Azure OpenAI)
- **Custo**: ~$0.02/1M tokens (~$0.10/mês para 300 artigos/dia)
- **Batch**: 50 artigos por chamada
- **Trigger**: Timer a cada 5 minutos

### 2.3 ScoringService

**Sistema de Scoring (conforme especificação do usuário):**

| Sinal | Valores | Pontos |
|-------|---------|--------|
| inesperado | yes/partial/no | 25/12/0 |
| impacto | high/medium/low | 30/15/0 |
| busca_agora | yes/maybe/no | 25/12/0 |
| conversa | yes/no | 20/0 |

**Classificação:**
- Score >= 75 → **A** (Alta relevância)
- Score 40-74 → **B** (Média relevância)
- Score < 40 → **C** (Baixa relevância)

**Implementação:**
1. **LLM (Claude)**: Analisa título + conteúdo e classifica os 4 sinais
2. **Fallback heurístico**: Keywords + volume + categoria quando LLM indisponível

### 2.4 ClusteringService

**Algoritmo:**
1. Para cada artigo novo com embedding:
   - Calcular similaridade cosseno com centroides de temas existentes
   - Se similaridade >= 0.75: adicionar ao tema existente
   - Se similaridade < 0.75: criar novo tema (artigo como seed)
2. Atualizar centroide do tema (média exponencial)
3. Recalcular score agregado do tema

**Score de Tema (estratégia COMPOSITE):**
```python
score = max_score * 0.7 + avg_score * 0.3 + volume_bonus
# volume_bonus = min(20, (article_count - 1) * 5)
```

---

## Fase 3: Novos Endpoints da API

### 3.1 GET /api/semantic-themes

```json
// Response
{
  "items": [
    {
      "id": "uuid",
      "name": "Seleção Brasileira",
      "slug": "selecao-brasileira",
      "classification": "A",
      "score": 85,
      "articleCount": 47,
      "recentArticleCount": 18,
      "trend": "rising",
      "isEmergent": true,
      "representativeTags": ["selecao-brasileira", "cbf", "neymar"]
    }
  ],
  "stats": { "totalA": 5, "totalB": 12, "totalC": 13 }
}
```

### 3.2 GET /api/semantic-themes/{id}

Retorna detalhes do tema + lista de artigos + timeline de evolução.

### 3.3 GET /api/articles?theme={themeId}

Filtrar artigos por tema semântico (adicionar suporte ao endpoint existente).

---

## Fase 4: Mudanças no Frontend

### 4.1 FiltersContext.jsx

Adicionar:
```javascript
const [filters, setFilters] = useState({
  // ... existentes
  theme: null,        // ID do tema semântico
  themeData: null,    // Dados completos do tema selecionado
});

const selectTheme = (theme) => { ... };
const clearTheme = () => { ... };
```

### 4.2 TrendsSidebar.jsx

**Nova estrutura visual:**
- Agrupar temas por classificação (A primeiro, depois B, depois C)
- Cada grupo é colapsável (A expandido por default)
- Indicadores visuais:
  - **A**: Badge verde, fundo verde-claro
  - **B**: Badge amarelo, fundo amarelo-claro
  - **C**: Badge cinza, fundo cinza-claro
- Badge "EMERGENTE" para temas com crescimento >50% em 2h
- Exibir: nome, score, contagem de artigos, trend

### 4.3 api.js

Adicionar funções:
- `getSemanticThemes(params)`
- `getSemanticThemeDetail(themeId)`

---

## Fase 5: Fluxo de Processamento

```
RSS Collector (15min)
    │
    ▼
INSERT collected_articles (has_embedding=0, has_score=0)
    │
    ├──────────────────────┬──────────────────────┐
    ▼                      ▼                      ▼
Embedding Generator    Scoring Calculator    Clustering Engine
(5min timer)           (10min timer)         (30min timer)
    │                      │                      │
    ▼                      ▼                      ▼
article_embeddings    article_scores         themes + article_themes
    │                      │                      │
    └──────────────────────┴──────────────────────┘
                           │
                           ▼
                    GET /api/semantic-themes
                           │
                           ▼
                    TrendsSidebar (frontend)
```

---

## Arquivos Críticos a Modificar

### Backend
1. `FeedRSS/tmc-rss-collector/function_app.py` - Registrar novos triggers
2. `FeedRSS/tmc-rss-collector/services/database.py` - CRUD para novas tabelas
3. `FeedRSS/tmc-rss-collector/services/ai_enrichment.py` - Integrar scoring

### Frontend
4. `tmc-redacao/src/components/layout/TrendsSidebar.jsx` - Nova UI A/B/C
5. `tmc-redacao/src/context/FiltersContext.jsx` - Estado de tema
6. `tmc-redacao/src/services/api.js` - Novos endpoints

### SQL
7. Script de migração para criar novas tabelas

---

## Estimativa de Custos Mensais

| Componente | Custo |
|------------|-------|
| OpenAI Embeddings (text-embedding-3-small) | ~$0.10 |
| Claude Scoring (Sonnet) | ~$45 |
| Azure SQL (storage adicional) | Incluso |
| **Total adicional** | **~$50/mês** |

---

## Verificação (Como Testar)

1. **Criar tabelas**: Executar script SQL de migração
2. **Testar embedding**: Coletar artigos e verificar se embeddings são gerados
3. **Testar scoring**: Verificar se scores A/B/C aparecem nos artigos
4. **Testar clustering**: Verificar se artigos são agrupados em temas
5. **Testar API**: `GET /api/semantic-themes` deve retornar temas agrupados
6. **Testar frontend**: TrendsSidebar deve mostrar temas com badges A/B/C
7. **Testar filtro**: Clicar em tema deve filtrar artigos corretamente

---

## Ordem de Implementação Sugerida

1. **Semana 1**: Schema SQL + models Pydantic
2. **Semana 2**: EmbeddingService + ScoringService
3. **Semana 3**: ClusteringService + API endpoints
4. **Semana 4**: Frontend (TrendsSidebar + FiltersContext)
5. **Semana 5**: Testes e ajustes de calibração
