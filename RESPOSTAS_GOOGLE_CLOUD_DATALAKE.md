# Respostas para Google Cloud - Projeto Data Lake TMC
**Data:** 23/12/2025
**Projeto:** Ferramenta de Redação Jornalística TMC

---

## I. PROCESSO E ARQUITETURA DE DADOS

### 1. Qual é o caso de uso que podemos considerar no desenvolvimento?

**Caso de Uso Principal:** Plataforma de criação de conteúdo jornalístico assistida por IA

O TMC é uma ferramenta para redações jornalísticas que:
1. **Coleta automatizada de notícias** de múltiplas fontes (RSS feeds de concorrentes)
2. **Identificação de temas quentes** através de análise de tendências em tempo real (RSS feeds, Google Trends, Twitter/X)
3. **Transcrição de vídeos** de redes sociais para extração de conteúdo
4. **Geração de matérias** utilizando IA generativa com base em:
   - Textos-base de referência
   - Configurações editoriais (tom, persona, estilo)
   - Materiais complementares (links, PDFs, vídeos)
5. **Otimização SEO** com análise de legibilidade, palavras-chave e checklist
6. **Gestão editorial** com workflow de rascunhos e publicações

---

### 2. Quais são os objetivos e quem serão os usuários finais?

**Objetivos:**
- Aumentar a produtividade de redações jornalísticas
- Reduzir tempo de produção de matérias de horas para minutos
- Garantir consistência editorial através de personas e tons configuráveis
- Identificar pautas relevantes automaticamente através de análise de tendências
- Melhorar SEO das publicações

**Usuários Finais:**
| Perfil | Uso Principal |
|--------|---------------|
| **Jornalistas/Redatores** | Criar matérias a partir de fontes diversas |
| **Editores** | Revisar, aprovar e publicar conteúdo |
| **Produtores de Conteúdo** | Transcrever vídeos e gerar textos |
| **Gestores de Redação** | Monitorar tendências e definir pautas |

**Consumo das Informações:**
- Interface web responsiva (desktop/mobile)
- Dashboards de tendências em tempo real
- Exportação para CMSs de publicação
- APIs para integração com sistemas editoriais existentes

---

### 3. Quais funcionalidades de I.A vocês buscam/desejam para trabalhar com esses dados?

| Funcionalidade | Descrição |
|----------------|-----------|
| **Geração de Texto** | Criar matérias completas a partir de texto-base e configurações |
| **Sugestão de Títulos** | Gerar múltiplas opções de títulos otimizados para SEO |
| **Resumo Automático** | Condensar textos longos em resumos/leads |
| **Transcrição de Vídeo** | Speech-to-Text para vídeos de redes sociais |
| **Análise de Sentimento** | Classificar tom de notícias (positivo/negativo/neutro) |
| **Extração de Tags** | Identificar tags e tópicos das matérias |
| **Extração de Entidades** | Identificar pessoas, organizações, locais mencionados |
| **Detecção de Tendências** | Identificar padrões emergentes nos dados coletados |
| **Tradução** | Traduzir matérias entre idiomas |
| **Correção Ortográfica** | Revisão automática de texto |
| **Clusterização de Notícias** | Agrupar matérias similares automaticamente |

---

### 4. Como atualmente vocês trabalham o processo de análise de insights e matérias?

**Situação Atual:** Processo manual e fragmentado

O processo atual envolve:
1. Jornalistas acessam manualmente sites concorrentes
2. Monitoram Google Trends e Twitter manualmente
3. Copiam textos de referência para documentos
4. Escrevem matérias do zero ou reescrevem manualmente
5. Revisão manual de SEO

**Dores Identificadas:**
- Alto tempo gasto em coleta manual de informações
- Dificuldade em identificar tendências rapidamente
- Falta de padronização no processo editorial
- Retrabalho na otimização de SEO

---

### 5. Quais ferramentas vocês utilizam atualmente no ecossistema de dados? Possuem arquitetura desenhada?

**Situação Atual:**
- Frontend web implementado (React)
- Não possui backend estruturado
- Não possui banco de dados em produção
- Dados mockados no frontend

**Necessidades de Arquitetura:**
```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Web App)                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                             │
└─────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Banco de   │    │    Data Lake    │    │  Armazenamento  │
│    Dados      │    │   (Analytics)   │    │   de Arquivos   │
│  Operacional  │    │                 │    │                 │
│  - Usuários   │    │  - Histórico    │    │  - PDFs         │
│  - Artigos    │    │  - Analytics    │    │  - Imagens      │
│  - Config     │    │  - Tendências   │    │  - Transcrições │
└───────────────┘    └─────────────────┘    └─────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Modelo de   │    │   Sistema de    │    │   Coletores     │
│      IA       │    │   Mensageria    │    │   de Dados      │
│               │    │                 │    │                 │
│  - Geração    │    │  - Filas        │    │  - RSS Parser   │
│  - Resumos    │    │  - Eventos      │    │  - Trends API   │
│  - Transcrição│    │  - Webhooks     │    │  - Twitter API  │
└───────────────┘    └─────────────────┘    └─────────────────┘
```

---

### 6. Vocês já possuem algum tipo de DW/DL estruturado atualmente?

**Não.** Atualmente não existe Data Warehouse ou Data Lake estruturado.

**Necessidade:**
- Data Lake para armazenar histórico de matérias coletadas
- Análise de tendências ao longo do tempo
- Possibilidade futura de treinamento/fine-tuning de modelos com dados próprios

---

### 7. Quais fontes e tipos de dados devemos considerar?

| Fonte | Tipo | Formato | Frequência | Retenção |
|-------|------|---------|------------|----------|
| **RSS Feeds** | API/XML | XML/JSON | 15min - 6h | 24 horas* |
| **Google Trends** | API | JSON | 1h | Permanente |
| **Twitter/X API** | API | JSON | 15min | Permanente |
| **YouTube Data API** | API | JSON | On-demand | Permanente |
| **YouTube Captions** | API | VTT/SRT | On-demand | Permanente |
| **Links da Web** | Scraping | HTML | On-demand | Permanente |
| **PDFs complementares** | Upload | PDF | On-demand | Permanente |
| **Matérias geradas** | Interno | JSON/HTML | Real-time | Permanente |
| **Configurações editoriais** | Interno | JSON | On-demand | Permanente |

> **\*Política de Retenção RSS:** Matérias coletadas de feeds RSS são armazenadas apenas por 24 horas. Após esse período, são automaticamente descartadas. Apenas matérias que o usuário selecionar como base para criação de conteúdo são preservadas permanentemente.

**Estrutura de dados de cada artigo coletado:**
```json
{
  "title": "string",
  "description": "string",
  "content": "string (full text)",
  "url": "string",
  "source": "string",
  "category": "string",
  "publishedAt": "datetime",
  "author": "string",
  "tags": ["string"],
  "sentiment": "positive|negative|neutral",
  "entities": ["string"]
}
```

---

### 8. Para banco de dados: qual o banco e versão?

**Situação Atual:** Não possui banco de dados implementado.

**Necessidades identificadas:**

| Tipo de Banco | Uso |
|---------------|-----|
| **Banco Relacional** | Dados operacionais (usuários, artigos, configurações) |
| **Data Lake/Warehouse** | Histórico de matérias, análise de tendências, analytics |
| **Armazenamento de Objetos** | Arquivos (PDFs, imagens, transcrições, backups) |
| **Cache/Real-time** | Sessões, estado de UI, preferências |

---

### 9. Quantas e quais tabelas está sendo considerado?

**Banco Operacional (~15 tabelas):**

```sql
-- Core
users                    -- Usuários do sistema
user_roles               -- Papéis (admin, editor, redator)
user_preferences         -- Preferências de UI

-- Artigos
articles                 -- Matérias criadas pelos usuários
article_versions         -- Histórico de versões
article_tags             -- Tags das matérias
article_sources          -- Fontes utilizadas em cada matéria

-- Fontes
rss_sources              -- Configuração de feeds RSS
collected_articles       -- Matérias coletadas dos feeds
trends_topics            -- Tópicos monitorados
excluded_terms           -- Termos excluídos do monitoramento

-- Configurações
personas                 -- Personas editoriais
tones                    -- Tons de escrita
categories               -- Categorias de conteúdo

-- Transcrição
transcriptions           -- Transcrições de vídeos
transcription_segments   -- Segmentos de transcrição
```

**Data Lake (~8 tabelas):**

```sql
-- Analytics
raw_collected_articles   -- Todas as matérias coletadas (histórico completo)
trends_history           -- Histórico de tendências ao longo do tempo
user_activity            -- Logs de atividade dos usuários
generation_logs          -- Logs de geração de IA

-- ML/Training
training_examples        -- Exemplos para fine-tuning
sentiment_analysis       -- Resultados de análise de sentimento
entity_extractions       -- Entidades extraídas
topic_clusters           -- Clusters de tópicos
```

---

### 10. Para API: já possui todos os endpoints necessários para coleta dos dados?

**Não.** O backend ainda não foi implementado.

**Endpoints necessários (a desenvolver):**

```
# Autenticação
POST   /api/auth/login
POST   /api/auth/register
POST   /api/auth/refresh

# Artigos do Usuário
GET    /api/articles
POST   /api/articles
GET    /api/articles/:id
PUT    /api/articles/:id
DELETE /api/articles/:id
POST   /api/articles/:id/publish

# Geração com IA
POST   /api/generate/article
POST   /api/generate/title
POST   /api/generate/summary

# Fontes RSS
GET    /api/sources
POST   /api/sources
PUT    /api/sources/:id
DELETE /api/sources/:id
GET    /api/sources/:id/articles

# Tendências
GET    /api/trends/google
GET    /api/trends/twitter
GET    /api/trends/feed

# Transcrição
POST   /api/transcriptions
GET    /api/transcriptions/:id
GET    /api/videos/:videoId/metadata

# Configurações
GET    /api/config/personas
GET    /api/config/tones
GET    /api/config/categories
```

**APIs Externas que serão consumidas:**
- YouTube Data API
- Google Trends API
- Twitter/X API
- API de modelo de IA generativa
---

### 11. Para arquivos: qual o formato e forma de obtenção?

| Tipo de Arquivo | Formato | Origem |
|-----------------|---------|--------|
| PDFs complementares | PDF | Upload do usuário |
| Imagens de matérias | JPG/PNG/WebP | Upload/URL |
| Transcrições | JSON/VTT | Processamento |
| Backups de artigos | JSON | Sistema |
| Exports | DOCX/PDF/HTML | Geração |

---

### 12. Quais são os destinos finais dos dados e qual a frequência?

| Dado | Destino | Frequência | Retenção |
|------|---------|------------|----------|
| Matérias coletadas (RSS) | Banco Operacional (temporário) | 15min - 1h | 24 horas |
| Tendências Google | Data Lake | 1h | Permanente |
| Tendências Twitter | Data Lake | 15min | Permanente |
| Artigos criados | Banco Operacional + Data Lake | Real-time | Permanente |
| Transcrições | Armazenamento + Data Lake | On-demand | Permanente |
| Logs de atividade | Data Lake | Real-time | Permanente |
| Métricas de uso | Data Lake | Batch (daily) | Permanente |

> **Nota:** Matérias de RSS são armazenadas temporariamente por 24h apenas para exibição no feed. Somente matérias selecionadas pelo usuário como base para geração são preservadas permanentemente.

**Fluxo de Dados:**
```
Fontes Externas → Coletores → Fila de Mensagens → ETL → Data Lake
                                                    ↓
                                          Banco Operacional
```

---

### 13. Qual a frequência de atualização dos dados na estrutura?

| Processo | Frequência | Tipo |
|----------|------------|------|
| Coleta RSS - Alta prioridade | 15 minutos | Agendado |
| Coleta RSS - Normal | 30min - 1h | Agendado |
| Coleta RSS - Baixa prioridade | 2h - 6h | Agendado |
| **Limpeza RSS (24h)** | Contínuo ou 1h | Agendado |
| Google Trends | 1 hora | Agendado |
| Twitter Trends | 15 minutos | Agendado |
| Transcrição de vídeo | On-demand | Evento |
| Geração de matéria | On-demand | Evento |
| Sync com Data Lake | Near real-time | Streaming |
| Backup | Diário | Agendado |
| Agregações analíticas | Hourly/Daily | Agendado |

---

### 14. Existem premissas a serem consideradas?

**Premissas Técnicas:**
1. **Frontend React deve ser mantido** - já está implementado e funcional
2. **Integração com múltiplas APIs de IA** - flexibilidade para trocar providers
3. **Escalabilidade** - suportar múltiplas redações/clientes
4. **Multi-tenancy** - isolamento de dados por cliente/redação
5. **Baixa latência** - geração de matéria deve ser rápida (<30s)

**Premissas de Negócio:**
1. **Conformidade LGPD** - dados de usuários protegidos
2. **Direitos autorais** - rastreabilidade de fontes utilizadas
3. **Auditoria** - log de todas as gerações de IA
4. **SLA** - 99.5% de disponibilidade
5. **Retenção de RSS** - matérias coletadas de feeds RSS são mantidas apenas por 24 horas; após esse período são automaticamente descartadas

**Integrações Futuras:**
- Possível integração com CMSs (WordPress, Drupal)
- Exportação para redes sociais
- Webhooks para sistemas de publicação externos

---

### 15. Devemos considerar algum processo de ETL/transformação dos dados?

**Sim.** Processos ETL necessários:

| Processo | Origem | Transformação | Destino |
|----------|--------|---------------|---------|
| **RSS Ingestion** | Feeds XML | Parse + Limpeza + Enriquecimento | Banco Operacional (24h) |
| **RSS Cleanup** | Banco Operacional | Expiração após 24h | Descarte automático |
| **Trend Analysis** | APIs de Trends | Normalização + Score | Data Lake |
| **Sentiment Analysis** | Textos coletados | NLP + Classificação | Data Lake |
| **Entity Extraction** | Textos coletados | NER + Normalização | Data Lake |
| **Aggregation** | Raw data | GROUP BY + Métricas | Views materializadas |
| **Deduplication** | Artigos coletados | Similarity check | Banco Operacional |

**Pipeline sugerido:**
```
Coletores (Functions)
       ↓
   Fila de Mensagens
       ↓
Processamento ETL
       ↓
Data Lake + Banco Operacional
```

**Transformações Principais:**
1. **Limpeza de HTML** - remover tags, scripts, estilos
2. **Normalização de datas** - converter para UTC
3. **Extração de entidades** - pessoas, organizações, locais
4. **Análise de sentimento** - positivo/negativo/neutro
5. **Deduplicação** - identificar matérias repetidas
6. **Categorização** - classificar por tema automaticamente

---

## II. VOLUMETRIA E CONSUMO DE DADOS

### 16. Qual o volume de dados total hoje?

**Situação Atual:** Apenas dados mockados (~500KB)

---

## VOLUMETRIA ESTIMADA

### Premissas do Cenário Base

| Parâmetro | Valor Estimado |
|-----------|----------------|
| Usuários ativos/mês | ~100 |
| Matérias geradas/mês | ~3.500 |
| Fontes RSS monitoradas | ~75 |
| Transcrições de vídeo/mês | ~1.000 |
| Tópicos de tendências monitorados | ~50 (coleta 4x/dia) |
| Trending topics Twitter | ~30 (coleta 6x/dia) |
| Imagens por matéria | ~1.5 (média) |
| PDFs complementares/mês | ~1.000 |

> **Política de retenção:** RSS (24h) e PDFs (30 dias) são temporários - usados apenas na produção da matéria.

---

### TABELA RESUMO - VOLUMETRIA ESTIMADA

| Tipo de Dado | Volume/mês | Volume/ano | Linhas/mês | Linhas/ano |
|--------------|------------|------------|------------|------------|
| **Armazenamento permanente** | | | | |
| Imagens de matérias | 2.6 GB | 31 GB | 5.250 | 63.000 |
| Matérias criadas + versões | 157 MB | 1.9 GB | 14.000 | 168.000 |
| Transcrições de vídeo | 35 MB | 420 MB | 1.000 | 12.000 |
| Tendências (Google + Twitter) | 33 MB | 400 MB | 11.400 | 137.000 |
| Logs de geração IA | 9 MB | 110 MB | 17.500 | 210.000 |
| **Subtotal permanente** | **~2.8 GB** | **~34 GB** | **~49.000** | **~590.000** |
| | | | | |
| **Armazenamento temporário** | | | | |
| PDFs complementares (30 dias) | 2 GB | 2 GB* | 1.000* | 1.000* |
| RSS (cache 24h) | 31 MB | 31 MB* | 6.000* | 6.000* |
| **Subtotal temporário** | **~2 GB** | **~2 GB** | **~7.000*** | **~7.000*** |
| | | | | |
| **TOTAL ARMAZENAMENTO** | **~4.8 GB** | **~36 GB** | **~49.000** | **~590.000** |

> *Dados temporários não acumulam - valores representam o máximo em qualquer momento.

### CONSUMO DE SERVIÇOS

| Serviço | Consumo/mês | Consumo/ano | Observação |
|---------|-------------|-------------|------------|
| IA Generativa (tokens) | 192M | 2.3B | ~55K tokens/matéria |
| Speech-to-Text (minutos) | 10.000 | 120.000 | Transcrição de vídeos |
| Invocações serverless | 15.000 | 180.000 | Coletores RSS/Trends |
| Mensagens em filas | 100.000 | 1.2M | Processamento assíncrono |

**Detalhamento do consumo de IA por matéria (~55.000 tokens):**
- Geração principal (título, linha fina, corpo, tags, SEO): ~21.000
- Chat do assistente (~12 interações): ~14.400
- Funcionalidades do editor (reescritas, melhorias, formatação): ~15.000
- Processamento de materiais (PDFs, links, transcrições): ~4.500

### Projeção de Crescimento (5 anos)

| Ano | Armazenamento | Linhas/registros | Tokens IA | Speech-to-Text | Usuários |
|-----|---------------|------------------|-----------|----------------|----------|
| Ano 1 | ~36 GB | ~590K | ~2.3B | ~120.000 min | ~100 |
| Ano 2 | ~54 GB | ~885K | ~3.0B | ~150.000 min | ~150 |
| Ano 3 | ~73 GB | ~1.2M | ~3.6B | ~180.000 min | ~200 |
| Ano 4 | ~95 GB | ~1.5M | ~4.3B | ~210.000 min | ~260 |
| Ano 5 | ~120 GB | ~1.9M | ~5.0B | ~240.000 min | ~325 |

> **Nota:** Projeção conservadora. PDFs e RSS são temporários e não acumulam.

---

## METODOLOGIA DE CÁLCULO (Detalhamento)

Esta seção detalha como cada estimativa foi calculada, permitindo validação e ajuste conforme premissas mudem.

---

### 1. VOLUMETRIA DE COLETA RSS

**Estrutura de dados por artigo coletado:**
```json
{
  "title": "~100 caracteres",
  "description": "~500 caracteres",
  "content": "~4.000 caracteres (texto completo)",
  "url": "~150 caracteres",
  "source": "~50 caracteres",
  "category": "~30 caracteres",
  "publishedAt": "24 caracteres (ISO)",
  "author": "~50 caracteres",
  "tags": "~100 caracteres (array)",
  "metadata": "~200 caracteres"
}
// Total médio: ~5.2 KB por artigo
```

**Cálculo de volume diário:**
- Portais de notícia publicam **~50-200 artigos/dia** cada
- RSS típico retorna **últimos 20-50 artigos** por request
- Frequência média de coleta: **1 hora** (24 requests/dia por fonte)

**Volume estimado (cenário médio - 75 fontes RSS):**

| Métrica | Valor |
|---------|-------|
| Artigos coletados/dia | ~6.000 |
| Volume máximo (24h) | ~31 MB |
| Invocações de coleta/mês | ~54.000 |

> **Nota:** Com política de retenção de 24h, o volume de RSS é **FIXO** (não acumulativo). Representa custo máximo de armazenamento temporário.

---

### 2. VOLUMETRIA DE TENDÊNCIAS

#### 2.1 Google Trends

**Dados coletados por tópico:**
```json
{
  "topic": "string",
  "interest_over_time": [168 pontos/semana],
  "related_queries": [25 queries × 2 campos],
  "related_topics": [25 topics × 3 campos],
  "geo_data": [27 estados BR],
  "timestamp": "datetime"
}
// Total médio: ~3 KB por tópico por coleta
```

**Volume estimado (cenário médio - 50 tópicos):**

| Métrica | Valor |
|---------|-------|
| Volume/mês | ~108 MB |
| Volume/ano | ~1.3 GB |

#### 2.2 Twitter/X Trends

**Dados coletados por hashtag:**
```json
{
  "hashtag": "string",
  "tweet_volume": "number",
  "sample_tweets": [20 tweets × 1KB],
  "engagement_metrics": "object",
  "timestamp": "datetime"
}
// Total médio: ~25 KB por hashtag por coleta
```

**Volume estimado (cenário médio - 25 hashtags):**

| Métrica | Valor |
|---------|-------|
| Volume/mês | ~1.8 GB |
| Volume/ano | ~21.6 GB |

#### 2.3 Resumo Tendências (Histórico Permanente - Cenário Médio)

| Fonte | Volume/mês | Volume/ano |
|-------|------------|------------|
| Google Trends | ~108 MB | ~1.3 GB |
| Twitter/X | ~1.8 GB | ~21.6 GB |
| **Total** | **~1.9 GB** | **~22.8 GB** |

---

### 3. VOLUMETRIA DE TRANSCRIÇÕES (Speech-to-Text)

**Premissas de transcrição:**
- Duração média de vídeo: **10 minutos**
- Palavras por minuto (fala): **~150 palavras**
- Caracteres por palavra: **~6 caracteres**
- Texto gerado por vídeo: **10 min × 150 palavras × 6 chars = ~9 KB**

**Estrutura de dados por transcrição:**
```json
{
  "video_id": "string",
  "video_metadata": {
    "title": "~100 chars",
    "channel": "~50 chars",
    "duration": "number",
    "thumbnail": "url"
  },
  "full_transcript": "~9.000 caracteres",
  "segments": [
    {
      "start": "number",
      "end": "number",
      "text": "~150 chars",
      "confidence": "number"
    }
  ],  // ~100 segmentos × 200 bytes = 20 KB
  "language": "string",
  "created_at": "datetime"
}
// Total médio: ~35 KB por transcrição
```

**Consumo estimado (cenário médio):**

| Métrica | Valor |
|---------|-------|
| Transcrições/mês | ~500 |
| Minutos de áudio/mês | ~5.000 min |
| Armazenamento/mês | ~17.5 MB |
| Armazenamento/ano | ~210 MB |

> **Nota:** O custo de Speech-to-Text varia conforme o provedor. Consultar tabela de preços do provedor selecionado.

---

### 4. VOLUMETRIA DE GERAÇÃO DE IA

**Consumo estimado de tokens por matéria (cenário médio):**

| Operação | Input | Output |
|----------|-------|--------|
| Geração da matéria completa | ~7.500 | ~2.700 |
| Operações auxiliares (títulos, resumos, SEO) | ~7.500 | ~2.500 |
| **Total por matéria** | **~15.000** | **~5.200** |

**Consumo mensal (cenário médio - 3.500 matérias/mês):**

| Métrica | Valor |
|---------|-------|
| Input tokens/mês | ~52.5M |
| Output tokens/mês | ~18.2M |
| **Total tokens/mês** | **~71M** |
| Logs de geração | ~9 MB/mês |

> **Nota:** O custo de IA generativa varia conforme o provedor e modelo escolhido. Recomenda-se consultar tabelas de preço atualizadas do provedor selecionado.

---

### 5. VOLUMETRIA DE MATÉRIAS CRIADAS (Permanente)

**Estrutura de dados por matéria:**
```json
{
  "id": "uuid",
  "title": "~100 caracteres",
  "subtitle": "~200 caracteres",
  "content": "~15.000 caracteres (HTML)",
  "content_plain": "~12.000 caracteres",
  "summary": "~500 caracteres",
  "author_id": "uuid",
  "category_id": "uuid",
  "tags": ["~10 tags × 20 chars"],
  "seo_metadata": {
    "meta_title": "~60 chars",
    "meta_description": "~160 chars",
    "keywords": "~200 chars",
    "readability_score": "number",
    "seo_score": "number"
  },
  "sources": [
    {"url": "string", "title": "string", "type": "string"}
  ],
  "status": "draft|published",
  "created_at": "datetime",
  "updated_at": "datetime",
  "published_at": "datetime",
  "version": "number"
}
// Total médio: ~30 KB por matéria
```

**Versionamento (histórico de edições):**
- Média de 3 versões por matéria
- Cada versão armazena diff: ~5 KB

**Volume estimado (cenário médio - 3.500 matérias/mês):**

| Métrica | Valor |
|---------|-------|
| Volume/mês | ~157.5 MB |
| Volume/ano | ~1.89 GB |

---

### 6. VOLUMETRIA DE LOGS E ANALYTICS

**Tipos de logs coletados:**

| Tipo de Log | Tamanho médio | Eventos/usuário/dia |
|-------------|---------------|---------------------|
| Page views | 200 bytes | 50 |
| Clicks/Interações | 150 bytes | 100 |
| Geração de IA | 500 bytes | 5 |
| Erros | 1 KB | 2 |
| Performance | 300 bytes | 20 |

**Volume estimado (cenário médio - 100 usuários ativos):**

| Métrica | Valor |
|---------|-------|
| Eventos/dia | ~17.700 |
| Volume/mês | ~159 MB |
| Volume/ano | ~1.9 GB |

---

### 7. VOLUMETRIA DE ARQUIVOS

**Tipos de arquivos:**
| Tipo | Tamanho médio | Frequência | Retenção |
|------|---------------|------------|----------|
| PDFs complementares | 2 MB | 10/mês/usuário | Permanente |
| Imagens de matérias | 500 KB | 3/matéria | Permanente |
| Exports (DOCX/PDF) | 100 KB | 1/matéria | 30 dias |
| Backups | Variável | Diário | 30 dias |

**Volume estimado (cenário médio):**

| Métrica | Valor |
|---------|-------|
| PDFs/mês | ~1.000 (2 GB) |
| Imagens/mês | ~10.500 (5.25 GB) |
| Volume/mês | ~7.25 GB |
| Volume/ano | ~87 GB |

---

*Ver tabela resumo de volumetria estimada no início da Seção II.*

---

### 17. Qual a região dos serviços deve ser considerada?

**Recomendação:** São Paulo, Brasil

**Justificativa:**
- Menor latência para usuários brasileiros
- Conformidade com LGPD (dados no Brasil)

**Multi-região (se necessário):**
- Região primária: Brasil
- Backup: EUA (para redundância)

---

### 18. O volume de dados tende a crescer? Em qual percentual anual estimado?

**Sim, o volume tende a crescer.**

**Fatores de Crescimento:**
1. Aumento de fontes RSS monitoradas
2. Mais usuários/redações na plataforma
3. Histórico acumulativo de tendências
4. Mais transcrições de vídeo
5. Logs e analytics

**Projeção de Crescimento:**

| Ano | Volume Estimado | Crescimento | Observação |
|-----|-----------------|-------------|------------|
| Ano 1 | 4-5 GB | Base | RSS não acumula (24h) |
| Ano 2 | 10-15 GB | +150% | Mais usuários e transcrições |
| Ano 3 | 20-40 GB | +100% | Histórico de tendências |
| Ano 4 | 40-80 GB | +100% | Crescimento linear |
| Ano 5 | 80-150 GB | +100% | Crescimento linear |

**Percentual Anual Médio:** 100-150% nos primeiros 3 anos, estabilizando em 50-100% após.

> **Impacto da Política de 24h:** A retenção temporária de RSS reduz significativamente o volume total, pois não há acúmulo histórico de matérias coletadas.

---

## RESUMO DAS NECESSIDADES

### Componentes de Infraestrutura Necessários

| Camada | Necessidade |
|--------|-------------|
| **Compute** | Backend API (serverless ou containers) |
| **Database** | Banco relacional para dados operacionais |
| **Data Lake** | Armazenamento analítico para histórico e ML |
| **Storage** | Armazenamento de objetos para arquivos |
| **AI/ML** | Modelo de IA generativa para geração de texto |
| **AI/ML** | Serviço de Speech-to-Text para transcrição |
| **ETL** | Ferramenta de processamento de dados |
| **Messaging** | Sistema de filas e eventos |
| **Scheduler** | Agendador de jobs |
| **Functions** | Funções serverless para coletores |
| **Auth** | Serviço de autenticação |
| **CDN** | Distribuição de assets estáticos |
| **Monitoring** | Observabilidade e logs |

---

## CONTATO PARA DÚVIDAS

enzo.oliveira@jaarconsult.com.br e luana.araujo@tmc.com.br

---


