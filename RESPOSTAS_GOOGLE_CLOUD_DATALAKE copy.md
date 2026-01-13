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
3. **Transcrição de vídeos** do YouTube para extração de conteúdo
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

---

### 3. Quais funcionalidades de I.A vocês buscam/desejam para trabalhar com esses dados?

| Funcionalidade | Descrição
|----------------|-----------
| **Geração de Texto** | Criar matérias completas a partir de texto-base e configurações 
| **Sugestão de Títulos** | Gerar múltiplas opções de títulos otimizados para SEO 
| **Resumo Automático** | Condensar textos longos em resumos/leads 
| **Transcrição de Vídeo** | Speech-to-Text para vídeos de Redes Sociais 
| **Análise de Sentimento** | Classificar tom de notícias (positivo/negativo/neutro) 
| **Extração de Tags** | Identificar Tags e tópicos das matérias 
| **Extração de Entidades** | Identificar pessoas, organizações, locais mencionados 
| **Detecção de Tendências** | Identificar padrões emergentes nos dados coletados 
| **Tradução** | Traduzir matérias entre idiomas 
| **Correção Ortográfica** | Revisão automática de texto 
| **Clusterização de Notícias** | Agrupar matérias similares automaticamente

**Modelos Considerados:**
- Google Vertex AI (Gemini)
- OpenAI GPT-4
- Anthropic Claude
- Google Cloud Speech-to-Text

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

### 5. Quais ferramentas vocês utilizam atualmente no ecossistema de dados?

**Backend (A implementar):**
- Não possui backend estruturado atualmente

**Arquitetura Proposta:**
```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API GATEWAY (Cloud Run)                      │
└─────────────────────────────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Cloud SQL    │    │   BigQuery      │    │  Cloud Storage  │
│ (PostgreSQL)  │    │   (Data Lake)   │    │   (Arquivos)    │
│  - Usuários   │    │  - Histórico    │    │  - PDFs         │
│  - Artigos    │    │  - Analytics    │    │  - Imagens      │
│  - Config     │    │  - Tendências   │    │  - Transcrições │
└───────────────┘    └─────────────────┘    └─────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Vertex AI    │    │  Cloud Pub/Sub  │    │ Cloud Functions │
│  (Gemini)     │    │  (Eventos)      │    │  (Collectors)   │
│  - Geração    │    │  - Filas        │    │  - RSS Parser   │
│  - Resumos    │    │  - Webhooks     │    │  - Trends API   │
└───────────────┘    └─────────────────┘    └─────────────────┘
```

---

### 6. Vocês já possuem algum tipo de DW/DL estruturado atualmente?

**Não.** Atualmente não existe Data Warehouse ou Data Lake estruturado.

**Situação Atual:**
- Dados mockados no frontend (JSON estático)
- Nenhum banco de dados em produção
- Nenhum pipeline de dados

**Necessidade:**
- Data Lake para armazenar histórico de matérias coletadas
- Análise de tendências ao longo do tempo
- Treinamento/fine-tuning de modelos com dados próprios

---

### 7. Quais fontes e tipos de dados devemos considerar?

| Fonte | Tipo | Formato | Frequência |
|-------|------|---------|------------|
| **RSS Feeds** | API/XML | XML/JSON | 15min - 6h |
| **Google Trends** | API | JSON | 1h |
| **Twitter/X API** | API | JSON | 15min |
| **YouTube Data API** | API | JSON | On-demand |
| **YouTube Captions** | API | VTT/SRT | On-demand |
| **Links da Web** | Scraping | HTML | On-demand |
| **PDFs complementares** | Upload | PDF | On-demand |
| **Matérias geradas** | Interno | JSON/HTML | Real-time |
| **Configurações editoriais** | Interno | JSON | On-demand |

**Dados a Coletar de Cada Fonte RSS:**
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

**Recomendação para GCP:**

| Serviço | Uso | Justificativa |
|---------|-----|---------------|
| **Cloud SQL (PostgreSQL 15)** | Dados operacionais | Usuários, artigos, configurações, sessões |
| **BigQuery** | Data Lake/Analytics | Histórico de matérias, análise de tendências, ML |
| **Cloud Storage** | Arquivos | PDFs, imagens, transcrições, backups |
| **Firestore** | Cache/Real-time | Sessões, estado de UI, preferências |

**Alternativa Simplificada:**
- AlloyDB for PostgreSQL (performance + analytics)

---

### 9. Quantas e quais tabelas está sendo considerado?

**Banco Operacional (Cloud SQL - ~15 tabelas):**

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
google_trends_topics     -- Tópicos monitorados no Trends
excluded_terms           -- Termos excluídos do monitoramento

-- Configurações
personas                 -- Personas editoriais
tones                    -- Tons de escrita
categories               -- Categorias de conteúdo

-- Transcrição
transcriptions           -- Transcrições de vídeos
transcription_segments   -- Segmentos de transcrição
```

**Data Lake (BigQuery - ~8 tabelas):**

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

**Endpoints Necessários (a desenvolver):**

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

**APIs Externas Necessárias:**
- YouTube Data API v3
- Google Trends (via pytrends ou SerpAPI)
- Twitter/X API v2
- OpenAI API ou Vertex AI

---

### 11. Para arquivos: qual o formato e forma de obtenção?

| Tipo de Arquivo | Formato | Origem | Armazenamento |
|-----------------|---------|--------|---------------|
| PDFs complementares | PDF | Upload do usuário | Cloud Storage |
| Imagens de matérias | JPG/PNG/WebP | Upload/URL | Cloud Storage |
| Transcrições | JSON/VTT | Processamento | Cloud Storage + BigQuery |
| Backups de artigos | JSON | Sistema | Cloud Storage |
| Exports | DOCX/PDF/HTML | Geração | Cloud Storage (temporário) |

**Estrutura de Buckets Sugerida:**
```
gs://tmc-uploads/
  ├── pdfs/
  ├── images/
  └── temp/

gs://tmc-transcriptions/
  └── {video_id}/
      ├── raw.json
      ├── segments.json
      └── audio.mp3 (se necessário)

gs://tmc-backups/
  └── daily/
      └── {date}/
```

---

### 12. Quais são os destinos finais dos dados e qual a frequência?

| Dado | Destino | Frequência |
|------|---------|------------|
| Matérias coletadas (RSS) | BigQuery + Cloud SQL | 15min - 1h |
| Tendências Google | BigQuery | 1h |
| Tendências Twitter | BigQuery | 15min |
| Artigos criados | Cloud SQL + BigQuery | Real-time |
| Transcrições | Cloud Storage + BigQuery | On-demand |
| Logs de atividade | BigQuery | Real-time |
| Métricas de uso | BigQuery | Batch (daily) |

**Fluxo de Dados:**
```
Fontes Externas → Cloud Functions → Pub/Sub → Dataflow → BigQuery
                                           ↓
                                    Cloud SQL (operacional)
```

---

### 13. Qual a frequência de atualização dos dados na estrutura?

| Processo | Frequência | Tipo |
|----------|------------|------|
| Coleta RSS - Alta prioridade | 15 minutos | Scheduled |
| Coleta RSS - Normal | 30min - 1h | Scheduled |
| Coleta RSS - Baixa prioridade | 2h - 6h | Scheduled |
| Google Trends | 1 hora | Scheduled |
| Twitter Trends | 15 minutos | Scheduled |
| Transcrição de vídeo | On-demand | Event-driven |
| Geração de matéria | On-demand | Event-driven |
| Sync BigQuery | Near real-time | Streaming |
| Backup | Diário | Scheduled |
| Agregações analíticas | Hourly/Daily | Scheduled |

---

### 14. Existem premissas a serem consideradas?

**Premissas Técnicas:**
1. **Frontend React deve ser mantido** - já está implementado e funcional
2. **Integração com múltiplas APIs de IA** - não depender de um único provider
3. **Escalabilidade** - suportar múltiplas redações/clientes
4. **Multi-tenancy** - isolamento de dados por cliente/redação
5. **Baixa latência** - geração de matéria deve ser rápida (<30s)

**Premissas de Negócio:**
1. **Conformidade LGPD** - dados de usuários protegidos
2. **Direitos autorais** - rastreabilidade de fontes
3. **Auditoria** - log de todas as gerações de IA
4. **SLA** - 99.5% de disponibilidade

**Plataformas Externas:**
- Possível integração futura com CMSs (WordPress, Drupal)
- Exportação para redes sociais
- Webhooks para sistemas de publicação

---

### 15. Devemos considerar algum processo de ETL/transformação dos dados?

**Sim.** Processos ETL necessários:

| Processo | Origem | Transformação | Destino |
|----------|--------|---------------|---------|
| **RSS Ingestion** | Feeds XML | Parse + Limpeza + Enriquecimento | Cloud SQL + BigQuery |
| **Trend Analysis** | Google Trends | Normalização + Score | BigQuery |
| **Sentiment Analysis** | Textos coletados | NLP + Classificação | BigQuery |
| **Entity Extraction** | Textos coletados | NER + Normalização | BigQuery |
| **Aggregation** | Raw data | GROUP BY + Métricas | BigQuery (materialized views) |
| **Deduplication** | Artigos coletados | Similarity check | Cloud SQL |

**Pipeline Sugerido:**
```
Cloud Functions (Collectors)
       ↓
   Pub/Sub (Queue)
       ↓
Dataflow (ETL Processing)
       ↓
BigQuery (Data Lake) + Cloud SQL (Operational)
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

**Projeção para Produção (Ano 1):**

| Tipo de Dado | Volume Estimado/Mês | Volume Ano 1 |
|--------------|---------------------|--------------|
| Artigos coletados (RSS) | ~300.000 artigos | ~3.6M artigos |
| Texto dos artigos | ~150 MB | ~1.8 GB |
| Metadados | ~30 MB | ~360 MB |
| Tendências | ~50 MB | ~600 MB |
| Transcrições | ~100 MB | ~1.2 GB |
| Artigos gerados | ~20 MB | ~240 MB |
| Logs/Analytics | ~200 MB | ~2.4 GB |
| **TOTAL** | **~550 MB/mês** | **~6-10 GB** |

**Projeção Ano 3 (com crescimento):**
- Estimativa: 50-100 GB

---

### 17. Qual a região dos serviços deve ser considerada em GCP?

**Recomendação:** `southamerica-east1` (São Paulo, Brasil)

**Justificativa:**
- Menor latência para usuários brasileiros
- Conformidade com LGPD (dados no Brasil)
- Disponibilidade de todos os serviços necessários

**Serviços Multi-região (se necessário):**
- Cloud Storage: `southamerica-east1` (primário) + `us-central1` (backup)
- BigQuery: `southamerica-east1`

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

| Ano | Volume Estimado | Crescimento |
|-----|-----------------|-------------|
| Ano 1 | 6-10 GB | Base |
| Ano 2 | 20-30 GB | +200% |
| Ano 3 | 50-100 GB | +150% |
| Ano 4 | 100-200 GB | +100% |
| Ano 5 | 200-400 GB | +100% |

**Percentual Anual Médio:** 100-150% nos primeiros 3 anos, estabilizando em 50-100% após.

---

## RESUMO EXECUTIVO PARA PROPOSTA

### Stack Recomendada GCP

| Camada | Serviço GCP | Função |
|--------|-------------|--------|
| **Compute** | Cloud Run | Backend API (serverless) |
| **Database** | Cloud SQL (PostgreSQL 15) | Dados operacionais |
| **Data Lake** | BigQuery | Analytics e histórico |
| **Storage** | Cloud Storage | Arquivos e backups |
| **AI/ML** | Vertex AI (Gemini) | Geração de texto |
| **AI/ML** | Cloud Speech-to-Text | Transcrição |
| **ETL** | Dataflow | Processamento de dados |
| **Messaging** | Pub/Sub | Filas e eventos |
| **Scheduler** | Cloud Scheduler | Jobs agendados |
| **Functions** | Cloud Functions | Collectors/Triggers |
| **Auth** | Firebase Auth | Autenticação |
| **CDN** | Cloud CDN | Assets estáticos |
| **Monitoring** | Cloud Monitoring | Observabilidade |

### Estimativa de Custos (Ordem de Grandeza)

| Serviço | Estimativa Mensal |
|---------|-------------------|
| Cloud Run | $50-150 |
| Cloud SQL | $50-100 |
| BigQuery | $20-50 |
| Cloud Storage | $10-30 |
| Vertex AI | $100-500 (dependendo do uso) |
| Outros | $50-100 |
| **TOTAL** | **$280-930/mês** |

*Valores aproximados para fase inicial. Escala conforme uso.*

---

## CONTATO PARA DÚVIDAS

[Inserir informações de contato da equipe TMC]

---

**Documento preparado para:** Google Cloud Team
**Versão:** 1.0
**Data:** 23/12/2025
