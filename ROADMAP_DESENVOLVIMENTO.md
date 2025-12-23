# Roadmap de Desenvolvimento - TMC

**Data:** 23/12/2025
**Versão:** 1.0
**Foco:** Funcionalidades Core (sem autenticação/usuários)

---

## Resumo Executivo

| Prioridade | Módulo | Horas Total |
|------------|--------|-------------|
| P1 | Coletor RSS | 32h |
| P2 | Tendências (Trends) | 24h |
| P3 | Transcrição de Vídeos | 28h |
| P4 | Geração de Matérias (IA) | 40h |
| P5 | Editor e SEO | 40h |
| P6 | Gestão de Matérias | 16h |
| **TOTAL** | | **164h** |

---

## Detalhamento por Módulo

### P1 - COLETOR RSS (32h)

| ID | Task | Descrição | Horas | Dependência |
|----|------|-----------|-------|-------------|
| 1.1 | Parser RSS/Atom | Biblioteca para parse de feeds XML (RSS 2.0, Atom) | 4h | - |
| 1.2 | Modelo de dados | Tabelas: rss_sources, collected_articles | 3h | - |
| 1.3 | CRUD Fontes RSS | API: criar, listar, editar, deletar fontes | 4h | 1.2 |
| 1.4 | Validador de URL | Validar se URL é feed válido antes de salvar | 2h | 1.1 |
| 1.5 | Job de Coleta | Worker agendado para coletar feeds (frequência configurável) | 6h | 1.1, 1.2 |
| 1.6 | Deduplicação | Evitar artigos duplicados (hash de URL + título) | 3h | 1.5 |
| 1.7 | Limpeza 24h | Job para remover artigos > 24 horas | 2h | 1.2 |
| 1.8 | API Feed | GET /api/feed - listar artigos coletados com filtros | 4h | 1.2 |
| 1.9 | Integração Frontend | Conectar BuscadorPage e RedacaoPage com APIs reais | 4h | 1.3, 1.8 |

---

### P2 - TENDÊNCIAS / TRENDS (24h)

| ID | Task | Descrição | Horas | Dependência |
|----|------|-----------|-------|-------------|
| 2.1 | Modelo de dados | Tabelas: trends_topics, excluded_terms, trends_cache | 2h | - |
| 2.2 | Integração Google Trends | Coletar tendências do Google Trends API | 6h | - |
| 2.3 | Integração Twitter/X | Coletar trending topics da API do Twitter | 6h | - |
| 2.4 | Temas Quentes RSS | Extrair temas mais frequentes dos artigos coletados | 4h | P1 |
| 2.5 | CRUD Monitoramento | API: adicionar/remover tópicos monitorados e excluídos | 3h | 2.1 |
| 2.6 | Integração Frontend | Conectar TrendsPage e TrendsSidebar com APIs reais | 3h | 2.2, 2.3, 2.4, 2.5 |

---

### P3 - TRANSCRIÇÃO DE VÍDEOS (28h)

| ID | Task | Descrição | Horas | Dependência |
|----|------|-----------|-------|-------------|
| 3.1 | YouTube Metadata | Obter título, thumbnail, duração via YouTube Data API | 4h | - |
| 3.2 | Download de Áudio | Extrair áudio do vídeo YouTube (yt-dlp ou similar) | 4h | - |
| 3.3 | Speech-to-Text | Integrar serviço de transcrição (Whisper ou Cloud STT) | 8h | 3.2 |
| 3.4 | Segmentação | Dividir transcrição em segmentos com timestamps | 4h | 3.3 |
| 3.5 | Modelo de dados | Tabelas: transcriptions, transcription_segments | 2h | - |
| 3.6 | API Transcrição | POST /api/video/transcribe (async com status) | 4h | 3.3, 3.4, 3.5 |
| 3.7 | Integração Frontend | Conectar TranscricaoPage e TextoBaseVideo | 2h | 3.1, 3.6 |

---

### P4 - GERAÇÃO DE MATÉRIAS COM IA (40h)

| ID | Task | Descrição | Horas | Dependência |
|----|------|-----------|-------|-------------|
| 4.1 | Integração LLM | Configurar cliente para API de modelo de IA | 4h | - |
| 4.2 | Prompt Engineering | Criar prompts otimizados para geração de matérias | 8h | 4.1 |
| 4.3 | Personas e Tons | Modelo de dados e lógica para aplicar estilos | 4h | 4.2 |
| 4.4 | Gerador de Títulos | Endpoint para sugerir títulos | 3h | 4.1, 4.2 |
| 4.5 | Gerador de Resumo | Endpoint para resumir textos | 3h | 4.1 |
| 4.6 | Extrator de Tópicos | Extrair pontos principais de texto-base | 4h | 4.1 |
| 4.7 | Geração Completa | POST /api/articles/generate (principal) | 8h | 4.1, 4.2, 4.3 |
| 4.8 | Processamento Async | WebSocket/SSE para progresso em tempo real | 4h | 4.7 |
| 4.9 | Integração Frontend | Conectar RevisarPage e fluxo de geração | 2h | 4.7, 4.8 |

---

### P5 - EDITOR E SEO (24h)

| ID | Task | Descrição | Horas | Dependência |
|----|------|-----------|-------|-------------|
| 5.1 | Analisador SEO | Calcular score baseado em regras (título, keywords, etc) | 6h | - |
| 5.2 | Contador de Legibilidade | Implementar Flesch-Kincaid ou similar para PT-BR | 4h | - |
| 5.3 | Extrator de Keywords | Identificar palavras-chave do texto | 3h | - |
| 5.4 | API SEO | GET /api/seo/analyze | 3h | 5.1, 5.2, 5.3 |
| 5.5 | Upload de Imagens | Endpoint para upload e CDN | 4h | - |
| 5.6 | Corretor Ortográfico | Integrar serviço de correção | 2h | - |
| 5.7 | Integração Frontend | Conectar SEOAnalyzerPanel com API real | 2h | 5.4 |

---

### P6 - GESTÃO DE MATÉRIAS (16h)

| ID | Task | Descrição | Horas | Dependência |
|----|------|-----------|-------|-------------|
| 6.1 | Modelo de dados | Tabelas: articles, article_versions, article_tags | 3h | - |
| 6.2 | CRUD Artigos | Criar, ler, atualizar, deletar matérias | 4h | 6.1 |
| 6.3 | Rascunhos | Salvar automaticamente como draft | 2h | 6.2 |
| 6.4 | Publicação | Alterar status para publicado | 2h | 6.2 |
| 6.5 | Versionamento | Manter histórico de versões | 3h | 6.1, 6.2 |
| 6.6 | Integração Frontend | Conectar MinhasMateriasPage e CriarPostPage | 2h | 6.2, 6.3, 6.4 |

---

## Ordem de Execução Recomendada

```
SPRINT 1 (Semana 1-2): P1 - Coletor RSS
├── Setup inicial do backend
├── Banco de dados
└── RSS funcionando end-to-end

SPRINT 2 (Semana 3): P2 - Tendências
├── Google Trends
├── Twitter (se API disponível)
└── Temas quentes do RSS

SPRINT 3 (Semana 4): P3 - Transcrição
├── YouTube integration
└── Speech-to-Text

SPRINT 4 (Semana 5-6): P4 - Geração IA
├── Integração LLM
├── Prompts e personas
└── Geração completa

SPRINT 5 (Semana 7): P5 + P6 - Editor e Gestão
├── SEO analyzer
├── CRUD de matérias
└── Publicação
```

---

## Dependências Técnicas

| Componente | Tecnologia Sugerida | Observação |
|------------|---------------------|------------|
| Backend API | Node.js/Python | A definir |
| Banco Operacional | PostgreSQL | Relacional |
| Cache | Redis | Sessões e cache |
| Filas | Bull/RabbitMQ | Jobs assíncronos |
| Armazenamento | S3-compatible | PDFs, imagens |
| LLM | Claude/GPT | Geração de texto |
| STT | Whisper/Cloud STT | Transcrição |

---

## Riscos e Considerações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Limites de API (Trends/Twitter) | Alto | Implementar cache agressivo |
| Custo de transcrição | Médio | Limitar duração de vídeos |
| Latência de geração IA | Médio | Streaming + feedback de progresso |
| Volume de RSS | Baixo | Política de 24h já definida |

---

## Métricas de Sucesso (MVP)

- [ ] Coletor RSS funcionando com 5+ fontes
- [ ] Tendências atualizando a cada hora
- [ ] Transcrição de vídeos até 15 min
- [ ] Geração de matéria em < 30 segundos
- [ ] Score SEO calculado em tempo real
- [ ] Salvar e recuperar matérias

---

**Total Estimado: 164 horas de desenvolvimento**

*Nota: Estimativas não incluem testes automatizados, documentação, deploy e DevOps.*
