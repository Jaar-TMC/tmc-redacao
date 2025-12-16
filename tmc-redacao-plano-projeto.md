# TMC Redação - Plano Mestre do Projeto

## Documento de Planejamento e Especificação Técnica

---

## 1. Visão Geral do Projeto

### 1.1 Objetivo
O TMC Redação é uma plataforma de criação de conteúdo jornalístico assistida por IA, desenvolvida para operações de rádio, TV e digital. A ferramenta centraliza a coleta de notícias, geração de conteúdo com inteligência artificial e distribuição multiplataforma.

### 1.2 Stack Base do Projeto
| Camada | Tecnologia |
|--------|------------|
| Frontend | React 19 + Vite + Tailwind CSS 4 |
| Backend | Azure Functions (Node.js) |
| Banco de Dados | PostgreSQL + pgvector |
| Cache | Upstash Redis |
| Hosting | Azure Static Web Apps |
| CI/CD | GitHub Actions |
| Autenticação | Microsoft Entra ID + JWT |

### 1.3 Estrutura do Documento

Este documento está dividido em duas seções principais:

1. **MVP (Must-Have)** - Features obrigatórias para o lançamento inicial
2. **Ideias Futuras** - Funcionalidades de expansão pós-MVP

Cada feature contém:
- Descrição funcional
- Como funciona (perspectiva do usuário)
- Implementação técnica (ferramentas específicas)
- Modelo de dados
- Endpoints de API

---

# PARTE 1: MVP (MUST-HAVE)

## Funcionalidades obrigatórias para o produto mínimo viável

---

## MVP-01: Sistema de Autenticação

### Descrição
Sistema completo de autenticação e autorização de usuários com suporte a login corporativo.

### Como Funciona
O usuário acessa a plataforma e faz login com email/senha ou através do SSO corporativo da Microsoft. O sistema valida as credenciais, gera um token de acesso e mantém a sessão ativa. Usuários podem recuperar senha via email.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| SSO Corporativo | **Microsoft Entra ID** |
| Tokens de Sessão | **JWT** com refresh tokens |
| Hash de Senhas | **bcrypt** |
| Envio de Email | **Azure Communication Services** |

### Modelo de Dados
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),
  avatar_url TEXT,
  role VARCHAR(50) DEFAULT 'editor',
  entra_id VARCHAR(255), -- ID do Microsoft Entra
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  token_hash VARCHAR(255) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/auth/register` | POST | Registro de novo usuário |
| `/api/auth/login` | POST | Login com email/senha |
| `/api/auth/login/entra` | POST | Login via Microsoft Entra |
| `/api/auth/logout` | POST | Encerrar sessão |
| `/api/auth/refresh` | POST | Renovar token de acesso |
| `/api/auth/forgot-password` | POST | Solicitar reset de senha |
| `/api/auth/reset-password` | POST | Redefinir senha |
| `/api/auth/me` | GET | Dados do usuário logado |

---

## MVP-02: Gerenciamento de Fontes RSS

### Descrição
Sistema para cadastrar, gerenciar e coletar automaticamente notícias de fontes RSS/Atom.

### Como Funciona
O usuário cadastra URLs de feeds RSS de portais de notícias (G1, Folha, ESPN, etc.), define a frequência de coleta (15min a 6h) e ativa/desativa fontes. O sistema coleta automaticamente as notícias em background, extrai o favicon do site, categoriza o conteúdo e remove duplicatas.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Parser de RSS/Atom | **rss-parser** (Node.js) |
| Scheduler de Jobs | **Azure Functions Timer Trigger** |
| Extração de Favicon | **Google Favicon API** ou scraping |
| Validação de URL | **validator.js** |
| Deduplicação | Hash MD5 do título + URL |

### Modelo de Dados
```sql
CREATE TABLE sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  name VARCHAR(255) NOT NULL,
  url TEXT NOT NULL,
  favicon_url TEXT,
  active BOOLEAN DEFAULT true,
  frequency VARCHAR(10) DEFAULT '1h', -- '15min', '30min', '1h', '2h', '6h'
  category VARCHAR(100),
  last_fetch TIMESTAMP,
  last_error TEXT,
  articles_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/sources` | GET | Listar fontes do usuário |
| `/api/sources` | POST | Criar nova fonte RSS |
| `/api/sources/:id` | GET | Detalhes de uma fonte |
| `/api/sources/:id` | PUT | Atualizar fonte |
| `/api/sources/:id` | DELETE | Remover fonte |
| `/api/sources/:id/toggle` | PATCH | Ativar/desativar fonte |
| `/api/sources/:id/fetch` | POST | Forçar coleta imediata |
| `/api/sources/validate` | POST | Validar URL de feed |

---

## MVP-03: Feed Principal de Notícias

### Descrição
Listagem centralizada de todas as notícias coletadas com filtros, busca e paginação.

### Como Funciona
O usuário acessa o feed e visualiza todas as notícias coletadas das fontes ativas. Pode filtrar por categoria, fonte, período e buscar por palavras-chave. O sistema exibe cards com título, preview, imagem, fonte e data. O usuário seleciona artigos para usar como inspiração na criação de conteúdo.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Busca Full-text | **Meilisearch** |
| Paginação | Cursor-based pagination |
| Cache de Resultados | **Upstash Redis** |
| Extração de Imagem | Parser do feed + Open Graph fallback |

### Modelo de Dados
```sql
CREATE TABLE collected_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  content TEXT,
  preview TEXT,
  url TEXT UNIQUE NOT NULL,
  image_url TEXT,
  author VARCHAR(255),
  category VARCHAR(100),
  tags TEXT[],
  published_at TIMESTAMP,
  collected_at TIMESTAMP DEFAULT NOW(),
  hash VARCHAR(64) UNIQUE -- MD5 para deduplicação
);

CREATE INDEX idx_articles_published ON collected_articles(published_at DESC);
CREATE INDEX idx_articles_category ON collected_articles(category);
CREATE INDEX idx_articles_source ON collected_articles(source_id);
```

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/articles` | GET | Listar artigos com filtros |
| `/api/articles/:id` | GET | Detalhes de um artigo |
| `/api/articles/stats` | GET | Estatísticas (total hoje, por categoria) |
| `/api/articles/search` | GET | Busca full-text |

**Query Params:**
```
?page=1&limit=20&category=&source_id=&period=24h&search=&sort=published_at
```

---

## MVP-04: Criação de Matéria com Assistente IA

### Descrição
Editor de texto com assistente de IA integrado para auxiliar na criação de conteúdo jornalístico.

### Como Funciona
O usuário abre o editor, seleciona tom (Formal, Informal, Técnico) e persona (Jornalista, Especialista, Colunista). Enquanto escreve, pode conversar com o assistente de IA para tirar dúvidas, pedir sugestões de ângulo, solicitar dados sobre o tema. O assistente responde contextualmente baseado no conteúdo sendo escrito.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| LLM Principal | **Claude 3.5 Haiku** |
| Editor de Texto Rico | **TipTap** (React) |
| Streaming de Respostas | **Server-Sent Events (SSE)** |
| Enriquecimento de Contexto | **Tavily API** |

### Prompt: Chat Assistente
```
Você é um assistente de redação jornalística brasileiro experiente.
Seu papel é ajudar o redator a criar conteúdo de qualidade.

CONTEXTO:
- Tom: {tone}
- Persona: {persona}
- Conteúdo atual do artigo: {article_content}

VOCÊ PODE:
- Sugerir ângulos para a matéria
- Melhorar a estrutura do texto
- Encontrar dados e estatísticas relevantes
- Responder dúvidas sobre o tema
- Sugerir fontes de pesquisa

Pergunta do usuário: {user_message}

Responda de forma concisa e útil em português brasileiro.
```

### Modelo de Dados
```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID REFERENCES my_articles(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL, -- 'user' ou 'assistant'
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/ai/chat` | POST | Enviar mensagem ao assistente (SSE) |
| `/api/ai/chat/history/:articleId` | GET | Histórico de mensagens |

---

## MVP-05: Geração de Conteúdo Inspirado

### Descrição
Fluxo de 3 etapas para gerar artigos originais baseados em matérias de referência.

### Como Funciona
**Etapa 1:** O usuário seleciona 1-5 artigos do feed como inspiração e marca os parágrafos mais relevantes de cada um. Escolhe tom e persona desejados.

**Etapa 2:** O sistema processa os artigos selecionados, analisa os parágrafos marcados e gera um novo artigo original. O progresso é exibido em tempo real.

**Etapa 3:** O usuário recebe o artigo gerado com métricas de originalidade, contagem de palavras e sugestões de melhoria. Pode editar, regenerar ou salvar.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| LLM para Geração | **Claude 3.5 Sonnet** |
| Streaming de Progresso | **Server-Sent Events (SSE)** |
| Cálculo de Originalidade | **pgvector** (similaridade coseno) |
| Embeddings | **OpenAI text-embedding-3-small** |

### Prompt: Geração Inspirada
```
Você é um jornalista brasileiro experiente. Com base nos artigos de referência abaixo, crie um NOVO artigo ORIGINAL sobre o mesmo tema.

REGRAS OBRIGATÓRIAS:
- NÃO copie trechos dos artigos originais
- Use as informações como BASE para criar conteúdo NOVO
- Mantenha o tom {tone} e a perspectiva de {persona}
- Inclua dados e estatísticas quando relevante
- Estruture com introdução, desenvolvimento e conclusão
- Tamanho: {minWords}-{maxWords} palavras

ARTIGOS DE REFERÊNCIA:
{articles_content}

PARÁGRAFOS SELECIONADOS COMO FOCO:
{selected_paragraphs}

Gere o artigo em português brasileiro, formatado em Markdown.
```

### Modelo de Dados
```sql
CREATE TABLE ai_generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  type VARCHAR(50) NOT NULL, -- 'inspired', 'from_title', 'improvement'
  input_articles UUID[], -- IDs dos artigos de referência
  selected_paragraphs JSONB, -- {article_id: [0, 1, 2]}
  tone VARCHAR(50),
  persona VARCHAR(50),
  output_content TEXT,
  originality_score DECIMAL(5,2),
  word_count INT,
  tokens_used INT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/ai/generate-inspired` | POST | Iniciar geração (SSE) |
| `/api/ai/generations/:id` | GET | Status/resultado da geração |

---

## MVP-06: Sugestão de Títulos

### Descrição
Geração automática de múltiplas opções de títulos otimizados para o conteúdo.

### Como Funciona
O usuário clica em "Sugerir Títulos" e o sistema analisa o conteúdo do artigo, gerando 5 opções de títulos jornalísticos. Cada título é otimizado para clareza, atratividade e SEO. O usuário escolhe um ou usa como inspiração.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| LLM | **Claude 3.5 Haiku** |
| Análise de Comprimento | Validação 50-70 caracteres |

### Prompt: Sugestão de Títulos
```
Com base no conteúdo jornalístico abaixo, sugira 5 títulos em português brasileiro.

CRITÉRIOS:
- Claros e objetivos
- Atrativos para cliques (sem ser clickbait)
- Entre 50-70 caracteres cada
- Usar verbos no presente quando possível
- Variados em estilo (informativo, questionador, impactante)

CONTEÚDO:
{content}

Retorne APENAS os 5 títulos, um por linha, numerados.
```

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/ai/suggest-titles` | POST | Gerar sugestões de títulos |

---

## MVP-07: Correção Ortográfica

### Descrição
Verificação e correção automática de erros ortográficos, gramaticais e de estilo.

### Como Funciona
O usuário clica no botão de correção e o sistema analisa o texto, destacando erros encontrados. Cada erro mostra o tipo (ortografia, gramática, pontuação) e a sugestão de correção. O usuário pode aceitar correções individualmente ou todas de uma vez.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Corretor Principal | **LanguageTool API** (gratuito até 20 req/min) |
| Highlight de Erros | **TipTap** decorations |
| Fallback | **Claude 3.5 Haiku** |

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/ai/check-spelling` | POST | Verificar texto |

**Response:**
```json
{
  "corrections": [
    {
      "offset": 45,
      "length": 8,
      "message": "Possível erro de concordância",
      "type": "grammar",
      "suggestions": ["correto", "correta"]
    }
  ]
}
```

---

## MVP-08: Gerenciamento de Matérias do Usuário

### Descrição
CRUD completo para as matérias criadas pelo usuário com filtros e organização.

### Como Funciona
O usuário acessa "Minhas Matérias" e visualiza todos os seus rascunhos e publicações. Pode filtrar por status (rascunho, publicado), categoria, data e buscar por título. Cada matéria pode ser editada, duplicada ou excluída. O sistema mantém histórico de versões.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Versionamento | Tabela de histórico com diff |
| Busca | **Meilisearch** |
| Auto-save | Debounce de 3 segundos |

### Modelo de Dados
```sql
CREATE TABLE my_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  title TEXT NOT NULL,
  content TEXT,
  preview TEXT,
  status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'published', 'archived'
  category VARCHAR(100),
  tags TEXT[],
  tone VARCHAR(50),
  persona VARCHAR(50),
  seo_score INT,
  word_count INT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  published_at TIMESTAMP
);

CREATE TABLE article_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID REFERENCES my_articles(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  version_number INT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/my-articles` | GET | Listar matérias do usuário |
| `/api/my-articles` | POST | Criar nova matéria |
| `/api/my-articles/:id` | GET | Detalhes de uma matéria |
| `/api/my-articles/:id` | PUT | Atualizar matéria |
| `/api/my-articles/:id` | DELETE | Excluir matéria |
| `/api/my-articles/:id/duplicate` | POST | Duplicar matéria |
| `/api/my-articles/:id/versions` | GET | Histórico de versões |

---

## MVP-09: Configuração de Google Trends

### Descrição
Sistema para configurar monitoramento de tendências do Google com filtros personalizados.

### Como Funciona
O usuário define temas de interesse para monitorar (ex: "Tecnologia", "Economia Brasil") e termos para excluir (ex: "BBB", "Reality Show"). O sistema coleta tendências do Google periodicamente, aplicando os filtros configurados, e exibe apenas o que é relevante para a redação.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Coleta de Trends | **SerpAPI** ou **DataForSEO** |
| Scheduler | **Azure Functions Timer Trigger** (1h) |
| Cache | **Upstash Redis** (TTL 1h) |

### Modelo de Dados
```sql
CREATE TABLE monitored_topics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  topic VARCHAR(255) NOT NULL,
  category VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE excluded_terms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  term VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE trends_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50) NOT NULL, -- 'google', 'bluesky', 'feed'
  topic VARCHAR(255) NOT NULL,
  volume VARCHAR(50),
  trend VARCHAR(20), -- 'up', 'down', 'stable'
  region VARCHAR(10) DEFAULT 'BR',
  category VARCHAR(100),
  fetched_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trends_fetched ON trends_results(fetched_at DESC);
```

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/trends/topics` | GET | Listar temas monitorados |
| `/api/trends/topics` | POST | Adicionar tema |
| `/api/trends/topics/:id` | DELETE | Remover tema |
| `/api/trends/exclusions` | GET | Listar termos excluídos |
| `/api/trends/exclusions` | POST | Adicionar exclusão |
| `/api/trends/exclusions/:id` | DELETE | Remover exclusão |

---

## MVP-10: Sidebar de Tendências em Tempo Real

### Descrição
Painel lateral exibindo tendências atualizadas do Google, redes sociais e feed interno.

### Como Funciona
O usuário visualiza três seções de tendências atualizadas:
1. **Google Trends** - Termos mais buscados no Brasil
2. **Social Trends** - Trending topics do Bluesky/Twitter
3. **Temas no Feed** - Assuntos em alta nas fontes cadastradas

Pode pausar/retomar atualizações e clicar em um trend para buscar matérias relacionadas.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Atualização Real-time | **Server-Sent Events (SSE)** |
| Social Trends | **Bluesky AT Protocol** (gratuito) |
| Temas do Feed | Agregação por tags + frequência |

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/trends/google` | GET | Trends do Google |
| `/api/trends/social` | GET | Trends de redes sociais |
| `/api/trends/feed` | GET | Temas em alta no feed |
| `/api/trends/stream` | GET | Stream SSE de atualizações |

---

## MVP-11: Configurações de Perfil

### Descrição
Página para gerenciar dados pessoais, preferências e notificações do usuário.

### Como Funciona
O usuário acessa as configurações e pode editar nome, email, foto de perfil. Define preferências como tema (claro/escuro), intervalo de auto-save, e quais notificações deseja receber (email, push, in-app).

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Upload de Avatar | **Azure Blob Storage** |
| Tema | CSS Variables + localStorage |
| Notificações Push | **Firebase Cloud Messaging** |

### Modelo de Dados
```sql
CREATE TABLE user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID UNIQUE REFERENCES users(id),
  theme VARCHAR(20) DEFAULT 'light',
  auto_save_interval INT DEFAULT 30, -- segundos
  notifications_email BOOLEAN DEFAULT true,
  notifications_push BOOLEAN DEFAULT true,
  notifications_breaking BOOLEAN DEFAULT true,
  language VARCHAR(10) DEFAULT 'pt-BR',
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Endpoints de API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/users/profile` | GET | Dados do perfil |
| `/api/users/profile` | PUT | Atualizar perfil |
| `/api/users/profile/avatar` | POST | Upload de avatar |
| `/api/users/preferences` | GET | Preferências |
| `/api/users/preferences` | PUT | Atualizar preferências |

---

# PARTE 2: IDEIAS FUTURAS

## Funcionalidades de expansão pós-MVP ordenadas por valor/complexidade

---

## IDEIA-01: Criação a partir de Título

**Prioridade:** Alta | **Complexidade:** Baixa

### Descrição
Gerar matéria completa apenas com base em um título fornecido pelo redator.

### Como Funciona
O usuário digita apenas o título da matéria e o sistema faz o resto. A IA busca contexto atualizado na web, pesquisa dados relevantes e gera a matéria completa automaticamente. O usuário recebe o rascunho pronto para editar e publicar, com o conteúdo sendo exibido em tempo real via streaming.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| LLM | **Claude 3.5 Haiku** (80% casos) / **Sonnet** (complexos) |
| Enriquecimento Web | **Tavily API** |
| Streaming | **Server-Sent Events (SSE)** |

---

## IDEIA-02: Resumo Automático para Redes Sociais

**Prioridade:** Alta | **Complexidade:** Baixa

### Descrição
Gerar automaticamente versões da matéria otimizadas para cada rede social.

### Como Funciona
Após criar sua matéria, o usuário clica em "Resumir para Redes Sociais" e a IA cria posts otimizados para cada plataforma: tweet (280 chars), legenda Instagram, post Facebook, LinkedIn. O sistema pode publicar automaticamente nas contas conectadas, respeitando os limites de cada rede.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| LLM | **Claude 3.5 Haiku** |
| Facebook/Instagram | **Meta Graph API** |
| Twitter/X | **Twitter API v2** |
| LinkedIn | **LinkedIn Marketing API** |
| Bluesky | **AT Protocol** |

---

## IDEIA-03: Gerador de Headlines A/B

**Prioridade:** Alta | **Complexidade:** Baixa

### Descrição
IA gera múltiplas variações de títulos para testar qual performa melhor.

### Como Funciona
A IA gera múltiplas opções de títulos para sua matéria. O sistema publica todas simultaneamente usando testes A/B e rastreia qual headline ganha mais cliques em tempo real. Os dados de desempenho aparecem no painel do usuário.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| LLM | **Claude 3.5 Haiku** |
| Testes A/B | **GrowthBook** |
| Analytics | **GA4 Measurement Protocol** |

---

## IDEIA-04: Tageamento Automático

**Prioridade:** Alta | **Complexidade:** Baixa

### Descrição
Extração automática de palavras-chave para categorização e SEO.

### Como Funciona
O usuário escreve a matéria e a IA extrai palavras-chave automaticamente. O sistema indexa e categoriza o conteúdo, criando tags otimizadas para buscabilidade. Isso melhora o SEO e facilita as pessoas encontrarem a matéria por tema.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Extração de Tags | **Claude 3.5 Haiku** |
| Indexação/Busca | **Meilisearch** |

---

## IDEIA-05: Roteiro para Locução

**Prioridade:** Alta | **Complexidade:** Baixa

### Descrição
Converter matéria escrita em roteiro otimizado para leitura em rádio/TV.

### Como Funciona
A IA converte a matéria em roteiro profissional para rádio ou TV. O sistema insere marcações de pausa, entonação e calcula o tempo de leitura preciso. O usuário baixa o roteiro já formatado no padrão de teleprompter e pode ouvir uma prévia em áudio.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Conversão para Roteiro | **Claude 3.5 Haiku** |
| Preview TTS | **Azure Cognitive Services Speech** |
| Formato | **SSML** (Speech Synthesis Markup) |

---

## IDEIA-06: Detector de Breaking News

**Prioridade:** Muito Alta | **Complexidade:** Média

### Descrição
Monitorar feeds e redes sociais para alertar sobre notícias urgentes.

### Como Funciona
O sistema monitora 24/7 feeds RSS e APIs de redes sociais, enviando alertas instantâneos quando notícias importantes surgem. O usuário recebe notificações em tempo real nos seus dispositivos, podendo agir rapidamente em breaking news.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Parser RSS | **rss-parser** (Node.js) |
| Social Monitoring | **Bluesky AT Protocol** |
| Alertas Real-time | **Server-Sent Events (SSE)** |
| Push Notifications | **Firebase Cloud Messaging (FCM)** |

---

## IDEIA-07: Verificador de Fatos em Tempo Real

**Prioridade:** Muito Alta | **Complexidade:** Média

### Descrição
Integrar com bases de fact-checking para alertar sobre informações já desmentidas.

### Como Funciona
Enquanto o usuário escreve, o sistema compara automaticamente as informações com verificações de agências como Lupa e Aos Fatos. Se mencionar algo já desmentido, recebe um alerta destacado protegendo a credibilidade da reportagem.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Base de Verificações | Coleta RSS: Lupa, Aos Fatos, Comprova |
| Busca Semântica | **pgvector** (PostgreSQL) |
| Embeddings | **OpenAI text-embedding-3-small** |

---

## IDEIA-08: Apuração Jornalística (Google PinPoint)

**Prioridade:** Muito Alta | **Complexidade:** Média

### Descrição
Análise de documentos e relatórios para verificação contra matérias criadas.

### Como Funciona
O usuário anexa PDFs de documentos e relatórios ao sistema, que extrai automaticamente informações relevantes (datas, números, nomes). Os dados são indexados para buscas semânticas, permitindo comparar com matérias já criadas e validar dados.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| PDF Parsing | **pdf.js** (Mozilla) |
| OCR/Extração | **Azure AI Document Intelligence** |
| Armazenamento | **Azure Blob Storage** |
| Busca Semântica | **pgvector** |

---

## IDEIA-09: Matérias Automáticas sem Revisão

**Prioridade:** Alta | **Complexidade:** Média

### Descrição
Publicar automaticamente conteúdo factual: previsão do tempo, resultados esportivos, cotações.

### Como Funciona
O sistema gera automaticamente matérias sobre temas factuais consultando APIs de dados (tempo, placar de jogos, cotações) e estrutura o conteúdo de forma jornalística. Usa diferentes "vozes" de redatores na rotação para evitar texto robótico.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Dados de Clima | **OpenWeatherMap API** |
| Dados Esportivos | **API-Football** (RapidAPI) |
| Dados Financeiros | **Alpha Vantage** |
| Geração de Texto | **Claude 3.5 Haiku** |

---

## IDEIA-10: News Consumer Insights

**Prioridade:** Alta | **Complexidade:** Média

### Descrição
Integração com analytics para entender perfil do consumidor de notícias.

### Como Funciona
O usuário acessa um dashboard que mostra quem está lendo suas matérias, com métricas de engajamento e análises de audiência. Descobre quais tipos de conteúdo funcionam melhor, horários de pico e perfil demográfico dos leitores.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Dados de Analytics | **GA4 Data API** |
| Visualização | **Recharts** ou **Apache ECharts** |
| Dashboard Externo | **Looker Studio** (embed) |

---

## IDEIA-11: Calendário Editorial Inteligente

**Prioridade:** Alta | **Complexidade:** Média

### Descrição
Sugerir pautas baseado em efemérides, eventos e tendências sazonais.

### Como Funciona
O sistema apresenta um calendário visual com eventos e datas importantes. A IA analisa efemérides e sugere automaticamente pautas por semana. O usuário arrasta e solta as sugestões diretamente no calendário, com sincronização opcional com Google Calendar.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| UI de Calendário | **FullCalendar.js** (React) |
| Dados de Eventos | **IBGE API** |
| Sugestão de Pautas | **Claude 3.5 Haiku** |
| Sincronização | **Google Calendar API** |

---

## IDEIA-12: Sugestão de Fontes e Especialistas

**Prioridade:** Alta | **Complexidade:** Média

### Descrição
Base de dados de especialistas com busca semântica para matching pauta-fonte.

### Como Funciona
O usuário digita o tema da pauta e o sistema busca na base de dados de especialistas usando busca semântica. Recebe uma lista de especialistas relevantes com informações de contato, área de atuação e histórico de participações.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Busca Vetorial | **pgvector** (PostgreSQL) |
| Embeddings | **OpenAI text-embedding-3-small** |
| Dados de Pesquisadores | **Plataforma Lattes** (CNPq) |

---

## IDEIA-13: Clipping Inteligente de Concorrentes

**Prioridade:** Alta | **Complexidade:** Média

### Descrição
Monitorar portais concorrentes para identificar gaps de cobertura.

### Como Funciona
O sistema monitora automaticamente os principais portais concorrentes 24/7, identificando histórias que os concorrentes cobriram mas o usuário ainda não. Alerta em tempo real sobre possíveis "furos" perdidos.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Web Scraping | **Playwright** |
| Alternativa Legal | **NewsAPI.org** |
| Comparação | Embeddings + similaridade |

---

## IDEIA-14: Detector de Plágio e Similaridade

**Prioridade:** Alta | **Complexidade:** Média

### Descrição
Verificar similaridade antes de publicar para evitar plágio.

### Como Funciona
Antes de publicar, o usuário clica no verificador que usa um sistema em três níveis: compara contra matérias próprias, depois contra clippings de concorrentes, e finalmente contra a web. Recebe resultado com níveis de risco para corrigir antes da publicação.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Comparação Interna | **pgvector** |
| Near-Duplicate | **MinHash** (5-grams) |
| Busca Web | **Google Custom Search API** |

---

## IDEIA-15: Google Trends - Correlação de Temas

**Prioridade:** Muito Alta | **Complexidade:** Média-Alta

### Descrição
Usar dados do Trends dentro das matérias, encontrar correlações entre temas.

### Como Funciona
O usuário seleciona um tema e a ferramenta mostra automaticamente temas relacionados em alta. O sistema coleta dados do Google Trends em tempo real, gera embeddings e calcula correlações semânticas. Os resultados são cacheados para otimizar performance.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Coleta de Trends | **SerpAPI** ou **DataForSEO** |
| Embeddings | **OpenAI text-embedding-3-small** |
| Correlação | Similaridade coseno |
| Cache | **Upstash Redis** |

---

## IDEIA-16: Integração CMS Única

**Prioridade:** Muito Alta | **Complexidade:** Média-Alta

### Descrição
Publicação direta no CMS existente (WordPress) sem copiar/colar.

### Como Funciona
A matéria pronta sai direto do editor para o WordPress sem copiar/colar. A integração usa API GraphQL para comunicação, autenticação SSO para segurança corporativa e webhooks para sincronizar alterações em tempo real entre os sistemas.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| API WordPress | **WPGraphQL** |
| Autenticação | **Microsoft Entra ID** (SSO) + **JWT** |
| Sincronização | **WP Webhooks** |

---

## IDEIA-17: Transcrição ao Vivo de Rádio/TV

**Prioridade:** Muito Alta | **Complexidade:** Alta

### Descrição
Transcrever programas em tempo real, criar artigos de cortes.

### Como Funciona
O usuário aponta a ferramenta para um programa de rádio ou TV e ela converte o áudio em texto automaticamente em tempo real. Qualquer trecho pode virar artigo com alguns cliques, com a transcrição sincronizada ao vídeo.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Speech-to-Text | **Deepgram Nova** (latência 300ms) |
| Streaming de Áudio | **Fluent FFmpeg** (Node.js) |
| Conexão Real-time | **WebSocket** |
| Renderização de Vídeo | **Remotion** (React) |

---

## IDEIA-18: Cortes Automáticos de Programas

**Prioridade:** Muito Alta | **Complexidade:** Alta

### Descrição
IA identifica highlights e sugere cortes para redes sociais.

### Como Funciona
A IA analisa um programa de rádio ou vídeo e identifica automaticamente os melhores trechos. Separa vozes (diarization), detecta momentos relevantes (aplausos, declarações impactantes), cria vídeos editados com legendas sincronizadas. O usuário escolhe os cortes e publica.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Transcrição + Diarization | **Deepgram** |
| Análise de Áudio | **librosa** (Python) |
| Identificação de Highlights | **Claude 3.5 Sonnet** |
| Edição de Vídeo | **FFmpeg** + **Remotion** |
| Legendas | **SRT/WebVTT** |

---

## IDEIA-19: Personalização de Conteúdo por Região

**Prioridade:** Alta | **Complexidade:** Média-Alta

### Descrição
Adaptar matérias para diferentes regiões de cobertura.

### Como Funciona
O jornalista escreve a matéria normalmente. O sistema detecta automaticamente a localização do leitor e adapta informações regionais relevantes. A matéria é enriquecida com contexto local automaticamente (dados do IBGE, clima local, eventos regionais).

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Geolocalização | **Cloudflare Headers** ou **ipinfo.io** |
| Dados Regionais | **IBGE API** |
| Adaptação de Conteúdo | **Claude 3.5 Haiku** |

---

## IDEIA-20: Geração de Imagens com IA

**Prioridade:** Média-Alta | **Complexidade:** Alta

### Descrição
Uso de IA generativa para criar imagens ilustrativas.

### Como Funciona
Ao publicar uma matéria, o sistema pode gerar uma imagem ilustrativa automaticamente baseada no conteúdo. Se houver problemas ou a imagem não for adequada, busca alternativas em bancos de imagens. Todas as imagens geradas recebem watermarking e passam por aprovação humana obrigatória.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Geração de Imagens | **DALL-E 3** (OpenAI) |
| Banco de Imagens | **Pexels API** |
| Watermarking | **SynthID/C2PA** |
| Armazenamento | **Azure Blob Storage** |

---

## IDEIA-21: Análise de Sentimento e Tom

**Prioridade:** Média | **Complexidade:** Baixa-Média

### Descrição
Avaliar tom da matéria e detectar possível viés.

### Como Funciona
Após escrever a matéria, o jornalista recebe análise automática avaliando tom (positivo, negativo, neutro) e alertando sobre possível viés. O sistema identifica linguagem carregada, analisa equilíbrio de fontes citadas e sugere ajustes pontuais para equilibrar a cobertura.

### Implementação Técnica
| Componente | Ferramenta |
|------------|------------|
| Análise de Sentimento | **Claude 3.5 Sonnet** |
| Structured Output | **JSON Schema** |
| Calibração PT-BR | Few-shot prompting (8-10 exemplos) |

---

# PARTE 3: ARQUITETURA TÉCNICA

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│                   React 19 + Vite + Tailwind                    │
│                   Azure Static Web Apps                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY                                 │
│                   Azure Functions                                │
│            (Node.js - HTTP Triggers)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   PostgreSQL  │    │ Upstash Redis │    │  Blob Storage │
│   + pgvector  │    │    (Cache)    │    │    (Mídia)    │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Claude API   │    │    Tavily     │    │   Meilisearch │
│  (Anthropic)  │    │   (Search)    │    │   (Full-text) │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## Background Jobs

| Job | Trigger | Função |
|-----|---------|--------|
| `rss-collector` | Timer (configurável) | Coleta feeds RSS das fontes ativas |
| `trends-google` | Timer (1h) | Atualiza Google Trends via SerpAPI |
| `trends-social` | Timer (30min) | Atualiza trends do Bluesky |
| `feed-themes` | Timer (1h) | Calcula temas em alta no feed |
| `cleanup` | Timer (1x/dia) | Remove dados antigos |

---

## Serviços Externos

### IA e NLP
| Serviço | Uso |
|---------|-----|
| **Claude 3.5 Haiku** | Chat, sugestões, tags, correções |
| **Claude 3.5 Sonnet** | Geração de conteúdo, análises complexas |
| **OpenAI Embeddings** | Busca semântica (text-embedding-3-small) |
| **LanguageTool** | Correção ortográfica |

### Dados e Trends
| Serviço | Uso |
|---------|-----|
| **SerpAPI** | Google Trends |
| **Bluesky AT Protocol** | Social trends |
| **Tavily** | Enriquecimento de contexto web |

### Infraestrutura
| Serviço | Uso |
|---------|-----|
| **Azure Functions** | Backend serverless |
| **Azure PostgreSQL** | Banco de dados principal |
| **Meilisearch** | Busca full-text |
| **Upstash Redis** | Cache e rate limiting |
| **Azure Blob Storage** | Armazenamento de mídia |

---

## Modelo de Dados Completo

```sql
-- =============================================
-- AUTENTICAÇÃO
-- =============================================

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),
  avatar_url TEXT,
  role VARCHAR(50) DEFAULT 'editor',
  entra_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(255) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  theme VARCHAR(20) DEFAULT 'light',
  auto_save_interval INT DEFAULT 30,
  notifications_email BOOLEAN DEFAULT true,
  notifications_push BOOLEAN DEFAULT true,
  language VARCHAR(10) DEFAULT 'pt-BR',
  updated_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- FONTES E COLETA
-- =============================================

CREATE TABLE sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  url TEXT NOT NULL,
  favicon_url TEXT,
  active BOOLEAN DEFAULT true,
  frequency VARCHAR(10) DEFAULT '1h',
  category VARCHAR(100),
  last_fetch TIMESTAMP,
  last_error TEXT,
  articles_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE collected_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  content TEXT,
  preview TEXT,
  url TEXT UNIQUE NOT NULL,
  image_url TEXT,
  author VARCHAR(255),
  category VARCHAR(100),
  tags TEXT[],
  published_at TIMESTAMP,
  collected_at TIMESTAMP DEFAULT NOW(),
  hash VARCHAR(64) UNIQUE,
  embedding vector(1536)
);

-- =============================================
-- MATÉRIAS DO USUÁRIO
-- =============================================

CREATE TABLE my_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  content TEXT,
  preview TEXT,
  status VARCHAR(20) DEFAULT 'draft',
  category VARCHAR(100),
  tags TEXT[],
  tone VARCHAR(50),
  persona VARCHAR(50),
  seo_score INT,
  word_count INT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  published_at TIMESTAMP
);

CREATE TABLE article_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID REFERENCES my_articles(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  version_number INT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id UUID REFERENCES my_articles(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- TRENDS
-- =============================================

CREATE TABLE monitored_topics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  topic VARCHAR(255) NOT NULL,
  category VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE excluded_terms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  term VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE trends_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50) NOT NULL,
  topic VARCHAR(255) NOT NULL,
  volume VARCHAR(50),
  trend VARCHAR(20),
  region VARCHAR(10) DEFAULT 'BR',
  category VARCHAR(100),
  fetched_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- IA E GERAÇÕES
-- =============================================

CREATE TABLE ai_generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  type VARCHAR(50) NOT NULL,
  input_articles UUID[],
  selected_paragraphs JSONB,
  tone VARCHAR(50),
  persona VARCHAR(50),
  output_content TEXT,
  originality_score DECIMAL(5,2),
  word_count INT,
  tokens_used INT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- ÍNDICES
-- =============================================

CREATE INDEX idx_articles_published ON collected_articles(published_at DESC);
CREATE INDEX idx_articles_category ON collected_articles(category);
CREATE INDEX idx_articles_source ON collected_articles(source_id);
CREATE INDEX idx_articles_hash ON collected_articles(hash);
CREATE INDEX idx_my_articles_user ON my_articles(user_id);
CREATE INDEX idx_my_articles_status ON my_articles(status);
CREATE INDEX idx_trends_fetched ON trends_results(fetched_at DESC);
CREATE INDEX idx_trends_source ON trends_results(source);

-- Extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE INDEX idx_articles_embedding ON collected_articles
  USING hnsw (embedding vector_cosine_ops);
```

---

## Endpoints de API Consolidados

### Autenticação (`/api/auth`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/register` | Registro |
| POST | `/login` | Login email/senha |
| POST | `/login/entra` | Login Microsoft |
| POST | `/logout` | Logout |
| POST | `/refresh` | Renovar token |
| POST | `/forgot-password` | Solicitar reset |
| POST | `/reset-password` | Redefinir senha |
| GET | `/me` | Usuário atual |

### Fontes RSS (`/api/sources`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Listar fontes |
| POST | `/` | Criar fonte |
| GET | `/:id` | Detalhes |
| PUT | `/:id` | Atualizar |
| DELETE | `/:id` | Remover |
| PATCH | `/:id/toggle` | Ativar/desativar |
| POST | `/:id/fetch` | Forçar coleta |
| POST | `/validate` | Validar URL |

### Artigos Coletados (`/api/articles`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Listar com filtros |
| GET | `/:id` | Detalhes |
| GET | `/stats` | Estatísticas |
| GET | `/search` | Busca full-text |

### Minhas Matérias (`/api/my-articles`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Listar |
| POST | `/` | Criar |
| GET | `/:id` | Detalhes |
| PUT | `/:id` | Atualizar |
| DELETE | `/:id` | Excluir |
| POST | `/:id/duplicate` | Duplicar |
| GET | `/:id/versions` | Histórico |

### IA (`/api/ai`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/chat` | Chat assistente (SSE) |
| GET | `/chat/history/:articleId` | Histórico |
| POST | `/generate-inspired` | Geração inspirada (SSE) |
| GET | `/generations/:id` | Status/resultado |
| POST | `/suggest-titles` | Sugerir títulos |
| POST | `/check-spelling` | Correção ortográfica |

### Trends (`/api/trends`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/topics` | Temas monitorados |
| POST | `/topics` | Adicionar tema |
| DELETE | `/topics/:id` | Remover tema |
| GET | `/exclusions` | Termos excluídos |
| POST | `/exclusions` | Adicionar exclusão |
| DELETE | `/exclusions/:id` | Remover exclusão |
| GET | `/google` | Google Trends |
| GET | `/social` | Social trends |
| GET | `/feed` | Temas do feed |
| GET | `/stream` | Stream SSE |

### Usuário (`/api/users`)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/profile` | Dados do perfil |
| PUT | `/profile` | Atualizar perfil |
| POST | `/profile/avatar` | Upload avatar |
| GET | `/preferences` | Preferências |
| PUT | `/preferences` | Atualizar preferências |

---

## Prompts de IA Consolidados

### Chat Assistente
```
Você é um assistente de redação jornalística brasileiro experiente.

CONTEXTO:
- Tom: {tone}
- Persona: {persona}
- Conteúdo atual: {article_content}

VOCÊ PODE:
- Sugerir ângulos para a matéria
- Melhorar estrutura do texto
- Encontrar dados relevantes
- Responder dúvidas sobre o tema

Pergunta: {user_message}

Responda de forma concisa em português brasileiro.
```

### Geração Inspirada
```
Você é um jornalista brasileiro experiente. Crie um NOVO artigo ORIGINAL.

REGRAS:
- NÃO copie dos artigos originais
- Tom: {tone}, Persona: {persona}
- Tamanho: {minWords}-{maxWords} palavras
- Estruture: introdução, desenvolvimento, conclusão

REFERÊNCIAS:
{articles_content}

FOCO:
{selected_paragraphs}

Gere em português brasileiro, formato Markdown.
```

### Sugestão de Títulos
```
Sugira 5 títulos jornalísticos em português brasileiro.

CRITÉRIOS:
- Claros e objetivos
- Atrativos (sem clickbait)
- 50-70 caracteres
- Verbos no presente
- Variados em estilo

CONTEÚDO:
{content}

Retorne apenas os 5 títulos numerados.
```

### Insights SEO
```
Analise o texto e forneça insights de SEO:

1. Keywords principais (5-10)
2. Densidade de keywords
3. Meta description (max 160 chars)
4. Estrutura de headings
5. Sugestões de links internos
6. Score de legibilidade
7. Pontos de melhoria

TEXTO:
{content}

Retorne em JSON estruturado.
```

---

*Documento gerado em: Dezembro 2025*
*Projeto: TMC Redação - Plano Mestre*
*Versão: 1.0*
