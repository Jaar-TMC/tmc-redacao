# TMC Redação - Coletor de Feeds RSS

## Documento de Arquitetura e Implementação Técnica
**Azure Functions + Python + SQL Server**

---

## 1. Visão Geral

Sistema de coleta automática de feeds RSS para o TMC Redação. Coleta notícias de múltiplas fontes brasileiras, processa e armazena no banco de dados para servir como contexto na geração de matérias com IA.

### 1.1 Stack Tecnológica

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| Runtime | Azure Functions | v4 |
| Linguagem | **Python** | 3.11 |
| Banco de Dados | Azure SQL Database | - |
| Parser RSS | feedparser | 6.0+ |
| HTTP Client | httpx | 0.25+ |
| Monitoramento | Application Insights | - |

> **Por que Python?**
> - **feedparser** é a biblioteca mais robusta para parsing RSS/Atom
> - Azure Functions tem excelente suporte para Python
> - Claude Code (Opus 4.5) performa excepcionalmente bem em Python para tarefas de coleta/processamento de dados
> - Ecossistema maduro para web scraping (BeautifulSoup, httpx)
> - Fácil integração com SQL Server via pyodbc

### 1.2 Infraestrutura

| Recurso | Configuração |
|---------|--------------|
| Azure Function App | Consumption Plan, Python 3.11 |
| SQL Server | bi4ia-tmc.database.windows.net |
| Database | tmc |
| Application Insights | Integrado ao Function App |

---

## 2. Arquitetura do Sistema

### 2.1 Diagrama de Fluxo

```
[Feeds RSS] → [Azure Function Timer] → [Parser] → [Deduplicação] → [SQL Server]
```

### 2.2 Componentes

| Componente | Responsabilidade |
|------------|------------------|
| Timer Trigger | Executa a cada 15 minutos, inicia o processo de coleta |
| HTTP Trigger | Permite coleta manual de uma fonte específica |
| RSS Parser | Faz fetch e parse dos feeds RSS/Atom |
| Deduplicador | Gera hash MD5 e verifica duplicatas no banco |
| Enricher | Extrai imagens via Open Graph quando não disponível no feed |
| Database Service | Gerencia conexões e queries ao SQL Server |
| Logger | Logging estruturado para Application Insights |

### 2.3 Fluxo de Execução Detalhado

1. Timer dispara a cada 15 minutos
2. Sistema busca todas as fontes ativas no banco
3. Filtra fontes que devem ser coletadas (baseado na frequência configurada)
4. Processa fontes em paralelo (máximo 10 simultâneas)
5. Para cada fonte: fetch → parse → deduplica → enriquece → insere
6. Atualiza last_fetch da fonte e registra log de execução
7. Envia métricas para Application Insights

---

## 3. Estrutura do Projeto

```
tmc-rss-collector/
├── function_app.py              # Entry point Azure Functions v2
├── requirements.txt             # Dependências Python
├── host.json                    # Configuração do host
├── local.settings.json          # Variáveis locais (git ignore)
│
├── functions/
│   ├── __init__.py
│   ├── rss_collector.py         # Timer trigger (a cada 15min)
│   ├── rss_collector_manual.py  # HTTP trigger para coleta manual
│   └── health_check.py          # HTTP trigger para monitoramento
│
├── services/
│   ├── __init__.py
│   ├── rss_parser.py            # Lógica de parsing RSS/Atom
│   ├── database.py              # Conexão e queries SQL Server
│   ├── deduplication.py         # Hash e verificação de duplicatas
│   └── enrichment.py            # Extração de imagem, favicon
│
├── models/
│   ├── __init__.py
│   ├── source.py                # Dataclass para Source
│   └── article.py               # Dataclass para Article
│
├── utils/
│   ├── __init__.py
│   ├── logger.py                # Configuração de logging
│   └── retry.py                 # Decorator para retry
│
└── tests/
    ├── test_rss_parser.py
    ├── test_database.py
    └── test_deduplication.py
```

---

## 4. Modelo de Dados

### 4.1 Tabela: sources

Armazena as configurações de cada fonte RSS cadastrada.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UNIQUEIDENTIFIER | Identificador único (PK) |
| name | NVARCHAR(255) | Nome amigável da fonte |
| url | NVARCHAR(2048) | URL do feed RSS |
| favicon_url | NVARCHAR(2048) | URL do ícone do site |
| active | BIT | Se a fonte está ativa (1) ou não (0) |
| frequency | NVARCHAR(10) | Frequência: '15min', '30min', '1h', '2h', '6h' |
| category | NVARCHAR(100) | Categoria (Política, Economia, etc) |
| last_fetch | DATETIME2 | Data/hora da última coleta |
| last_error | NVARCHAR(MAX) | Último erro (se houver) |
| articles_count | INT | Total de artigos coletados |
| created_at | DATETIME2 | Data de criação |
| updated_at | DATETIME2 | Data de atualização |

### 4.2 Tabela: collected_articles

Armazena cada artigo coletado dos feeds RSS.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UNIQUEIDENTIFIER | Identificador único (PK) |
| source_id | UNIQUEIDENTIFIER | FK para sources |
| title | NVARCHAR(1000) | Título do artigo |
| content | NVARCHAR(MAX) | Conteúdo completo (quando disponível) |
| preview | NVARCHAR(500) | Resumo/preview do artigo |
| url | NVARCHAR(2048) | URL original do artigo (UNIQUE) |
| image_url | NVARCHAR(2048) | URL da imagem principal |
| author | NVARCHAR(255) | Autor (quando disponível) |
| category | NVARCHAR(100) | Categoria do artigo |
| tags | NVARCHAR(MAX) | JSON array de tags |
| published_at | DATETIME2 | Data de publicação original |
| collected_at | DATETIME2 | Data/hora da coleta |
| hash | NVARCHAR(64) | MD5 para deduplicação (UNIQUE) |

### 4.3 Tabela: collection_logs

Registra logs de cada execução de coleta para auditoria.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UNIQUEIDENTIFIER | Identificador único (PK) |
| source_id | UNIQUEIDENTIFIER | FK para sources (opcional) |
| started_at | DATETIME2 | Início da execução |
| finished_at | DATETIME2 | Fim da execução |
| status | NVARCHAR(20) | 'success', 'partial', 'error' |
| articles_found | INT | Artigos encontrados no feed |
| articles_new | INT | Artigos novos inseridos |
| articles_duplicate | INT | Artigos duplicados ignorados |
| error_message | NVARCHAR(MAX) | Mensagem de erro (se houver) |
| duration_ms | INT | Duração em milissegundos |

---

## 5. Scripts SQL

### 5.1 Criação das Tabelas

```sql
-- Tabela de Fontes RSS
CREATE TABLE sources (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name NVARCHAR(255) NOT NULL,
    url NVARCHAR(2048) NOT NULL,
    favicon_url NVARCHAR(2048),
    active BIT DEFAULT 1,
    frequency NVARCHAR(10) DEFAULT '1h',
    category NVARCHAR(100),
    last_fetch DATETIME2,
    last_error NVARCHAR(MAX),
    articles_count INT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    updated_at DATETIME2 DEFAULT GETUTCDATE()
);

-- Tabela de Artigos Coletados
CREATE TABLE collected_articles (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    source_id UNIQUEIDENTIFIER NOT NULL,
    title NVARCHAR(1000) NOT NULL,
    content NVARCHAR(MAX),
    preview NVARCHAR(500),
    url NVARCHAR(2048) NOT NULL,
    image_url NVARCHAR(2048),
    author NVARCHAR(255),
    category NVARCHAR(100),
    tags NVARCHAR(MAX),
    published_at DATETIME2,
    collected_at DATETIME2 DEFAULT GETUTCDATE(),
    hash NVARCHAR(64) NOT NULL,
    
    CONSTRAINT FK_articles_source FOREIGN KEY (source_id) 
        REFERENCES sources(id) ON DELETE CASCADE,
    CONSTRAINT UQ_articles_hash UNIQUE (hash),
    CONSTRAINT UQ_articles_url UNIQUE (url)
);

-- Tabela de Logs de Coleta
CREATE TABLE collection_logs (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    source_id UNIQUEIDENTIFIER,
    started_at DATETIME2 NOT NULL,
    finished_at DATETIME2,
    status NVARCHAR(20) NOT NULL,
    articles_found INT DEFAULT 0,
    articles_new INT DEFAULT 0,
    articles_duplicate INT DEFAULT 0,
    error_message NVARCHAR(MAX),
    duration_ms INT,
    
    CONSTRAINT FK_logs_source FOREIGN KEY (source_id) 
        REFERENCES sources(id) ON DELETE SET NULL
);
```

### 5.2 Índices para Performance

```sql
-- Índices para sources
CREATE INDEX IX_sources_active ON sources(active) WHERE active = 1;
CREATE INDEX IX_sources_frequency ON sources(frequency, last_fetch);

-- Índices para collected_articles
CREATE INDEX IX_articles_published ON collected_articles(published_at DESC);
CREATE INDEX IX_articles_source ON collected_articles(source_id);
CREATE INDEX IX_articles_category ON collected_articles(category);
CREATE INDEX IX_articles_collected ON collected_articles(collected_at DESC);
CREATE INDEX IX_articles_hash ON collected_articles(hash);

-- Índice composto para queries comuns
CREATE INDEX IX_articles_source_date ON collected_articles(source_id, published_at DESC);
CREATE INDEX IX_articles_category_date ON collected_articles(category, published_at DESC);

-- Índices para collection_logs
CREATE INDEX IX_logs_source_date ON collection_logs(source_id, started_at DESC);
CREATE INDEX IX_logs_status ON collection_logs(status, started_at DESC);
```

---

## 6. Dependências Python

### 6.1 requirements.txt

```
# Azure Functions
azure-functions>=1.17.0

# RSS Parsing
feedparser>=6.0.10
httpx>=0.25.0

# Database
pyodbc>=5.0.1

# Validação e Models
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Utilities
python-dateutil>=2.8.2
tenacity>=8.2.3
beautifulsoup4>=4.12.0

# Monitoramento
opencensus-ext-azure>=1.1.0
```

### 6.2 Descrição das Dependências

| Pacote | Uso |
|--------|-----|
| azure-functions | Runtime do Azure Functions |
| feedparser | Parser de feeds RSS e Atom |
| httpx | Cliente HTTP assíncrono (melhor que requests) |
| pyodbc | Driver para conexão com SQL Server |
| pydantic | Validação de dados e modelos tipados |
| pydantic-settings | Carregar configurações de variáveis de ambiente |
| python-dateutil | Parsing robusto de datas em diversos formatos |
| tenacity | Retry com backoff exponencial |
| beautifulsoup4 | Extração de metadados Open Graph |
| opencensus-ext-azure | Integração com Application Insights |

---

## 7. Configuração de Ambiente

### 7.1 Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| SQL_SERVER | Host do banco de dados | bi4ia-tmc.database.windows.net |
| SQL_DATABASE | Nome do banco | tmc |
| SQL_USERNAME | Usuário do banco | tmc_collector |
| SQL_PASSWORD | Senha do banco | (configurar no App Settings) |
| RSS_FETCH_TIMEOUT | Timeout por feed em segundos | 30 |
| RSS_MAX_CONCURRENT | Máximo de feeds simultâneos | 10 |
| RSS_MAX_ARTICLES_PER_FEED | Limite de artigos por feed | 100 |
| APPINSIGHTS_CONNECTION_STRING | Connection string do App Insights | InstrumentationKey=... |

### 7.2 Configuração no Azure Portal

As variáveis devem ser configuradas diretamente no Application Settings do Azure Function App:

1. Acesse o Azure Portal → Function App → Configuration
2. Em Application Settings, adicione cada variável
3. Clique em Save para aplicar as alterações
4. O Function App será reiniciado automaticamente

---

## 8. Tratamento de Erros e Resiliência

### 8.1 Estratégia de Retry

| Cenário | Tentativas | Backoff | Ação após falha |
|---------|------------|---------|-----------------|
| Feed indisponível (HTTP) | 3 | 2s, 4s, 8s | Logar erro, continuar próxima fonte |
| Timeout de conexão | 3 | 2s, 4s, 8s | Logar erro, continuar próxima fonte |
| Erro de parsing XML | 1 | - | Logar erro, continuar próxima fonte |
| Banco indisponível | 3 | 5s, 10s, 20s | Logar erro, encerrar execução |
| Erro de constraint (duplicata) | 1 | - | Ignorar artigo, continuar |

### 8.2 Circuit Breaker por Fonte

Se uma fonte falhar 3 vezes consecutivas:

- Marcar fonte como 'em observação' no banco
- Reduzir frequência de tentativas (1x por hora)
- Após 1 sucesso: retornar ao comportamento normal
- Após 10 falhas: desativar fonte e notificar administrador

### 8.3 Timeouts e Limites

| Operação | Timeout/Limite |
|----------|----------------|
| Fetch de 1 feed (HTTP) | 30 segundos |
| Parse de 1 feed (XML) | 10 segundos |
| Artigos por feed | Máximo 100 |
| Execução total do timer | 5 minutos |
| Conexão com SQL Server | 30 segundos |
| Pool de conexões SQL | 10 conexões |
| Fontes em paralelo | 10 simultâneas |

---

## 9. Monitoramento e Observabilidade

### 9.1 Métricas Customizadas (Application Insights)

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| rss_feeds_processed | Counter | Número de feeds processados por execução |
| rss_articles_collected | Counter | Número de artigos novos coletados |
| rss_articles_duplicates | Counter | Número de artigos duplicados ignorados |
| rss_fetch_duration_ms | Histogram | Tempo de fetch por fonte |
| rss_parse_duration_ms | Histogram | Tempo de parse por fonte |
| rss_errors | Counter | Erros por tipo (http, parse, db) |
| rss_execution_duration_ms | Histogram | Duração total da execução |

### 9.2 Alertas Recomendados

| Alerta | Condição | Severidade |
|--------|----------|------------|
| Execução falhou | 3 falhas consecutivas do timer | Alta |
| Fonte com erro persistente | Fonte específica falha 5+ vezes | Média |
| Latência alta | Execução > 4 minutos | Baixa |
| Zero artigos coletados | Nenhum artigo novo em 2 horas | Média |
| Erro de banco de dados | Qualquer erro de conexão SQL | Alta |

### 9.3 Logs Estruturados

Formato JSON para facilitar queries no Application Insights:

```json
{
    "timestamp": "2025-01-07T15:30:00Z",
    "level": "INFO",
    "function": "rss_collector",
    "execution_id": "abc-123-def",
    "source_id": "456-789-ghi",
    "source_name": "G1 - Política",
    "event": "fetch_completed",
    "articles_found": 15,
    "articles_new": 3,
    "articles_duplicate": 12,
    "duration_ms": 1250
}
```

---

## 10. Lógica de Frequência de Coleta

O sistema executa a cada 15 minutos, mas cada fonte tem sua própria frequência configurada.

### 10.1 Frequências Disponíveis

| Frequência | Intervalo | Uso Recomendado |
|------------|-----------|-----------------|
| 15min | 15 minutos | Breaking news, portais de alta frequência |
| 30min | 30 minutos | Portais de notícias gerais |
| 1h | 1 hora | Padrão para a maioria das fontes |
| 2h | 2 horas | Blogs, portais especializados |
| 6h | 6 horas | Fontes de baixa frequência |

### 10.2 Lógica de Verificação

```python
from datetime import datetime, timedelta

def should_fetch(source: Source, now: datetime) -> bool:
    """Verifica se a fonte deve ser coletada nesta execução."""
    
    # Primeira coleta: sempre executar
    if source.last_fetch is None:
        return True
    
    # Mapear frequência para intervalo
    intervals = {
        '15min': timedelta(minutes=15),
        '30min': timedelta(minutes=30),
        '1h': timedelta(hours=1),
        '2h': timedelta(hours=2),
        '6h': timedelta(hours=6),
    }
    
    interval = intervals.get(source.frequency, timedelta(hours=1))
    elapsed = now - source.last_fetch
    
    return elapsed >= interval
```

---

## 11. Estratégia de Deduplicação

O sistema utiliza hash MD5 para identificar artigos duplicados de forma eficiente.

### 11.1 Geração do Hash

```python
import hashlib

def generate_article_hash(title: str, url: str) -> str:
    """Gera hash único para identificar o artigo."""
    
    # Normalizar título (lowercase, remover espaços extras)
    normalized_title = ' '.join(title.lower().split())
    
    # Combinar título + URL
    content = f"{normalized_title}|{url}"
    
    # Gerar MD5
    return hashlib.md5(content.encode('utf-8')).hexdigest()
```

### 11.2 Verificação em Batch

Para otimizar performance, verificamos múltiplos hashes em uma única query:

```python
from typing import List, Set

async def check_duplicates(hashes: List[str]) -> Set[str]:
    """Retorna conjunto de hashes que já existem no banco."""
    
    if not hashes:
        return set()
    
    placeholders = ','.join(['?' for _ in hashes])
    query = f"""
        SELECT hash FROM collected_articles 
        WHERE hash IN ({placeholders})
    """
    
    result = await db.fetch_all(query, hashes)
    return {row['hash'] for row in result}
```

### 11.3 Fluxo de Deduplicação

1. Coletar todos os artigos do feed
2. Gerar hash para cada artigo
3. Fazer uma única query com todos os hashes
4. Filtrar apenas artigos com hash não existente
5. Inserir artigos novos em batch

---

## 12. Enriquecimento de Dados

Quando o feed não fornece imagem, o sistema tenta extrair via Open Graph.

### 12.1 Extração de Imagem

```python
from typing import Optional
from bs4 import BeautifulSoup
import httpx

async def extract_image_url(article_url: str) -> Optional[str]:
    """Extrai imagem do artigo via Open Graph tags."""
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                article_url, 
                timeout=10,
                follow_redirects=True
            )
            
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tentar og:image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']
        
        # Fallback: twitter:image
        tw_image = soup.find('meta', {'name': 'twitter:image'})
        if tw_image and tw_image.get('content'):
            return tw_image['content']
            
        return None
        
    except Exception:
        return None
```

### 12.2 Extração de Favicon

```python
def get_favicon_url(site_url: str) -> str:
    """Retorna URL do favicon usando Google Favicon API."""
    
    from urllib.parse import urlparse
    domain = urlparse(site_url).netloc
    
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
```

---

## 13. Lista de Feeds RSS

Feeds RSS de portais brasileiros para popular a tabela sources. Todos os links foram verificados.

### 13.1 Grupo Globo (G1 e GloboEsporte)

| Portal | URL do Feed | Categoria |
|--------|-------------|-----------|
| G1 - Principal | https://g1.globo.com/rss/g1/ | Geral |
| G1 - Política | https://g1.globo.com/rss/g1/politica/ | Política |
| G1 - Economia | https://g1.globo.com/rss/g1/economia/ | Economia |
| G1 - Tecnologia | https://g1.globo.com/rss/g1/tecnologia/ | Tecnologia |
| G1 - Mundo | https://g1.globo.com/rss/g1/mundo/ | Internacional |
| G1 - Ciência e Saúde | https://g1.globo.com/rss/g1/ciencia-e-saude/ | Ciência |
| G1 - Educação | https://g1.globo.com/rss/g1/educacao/ | Educação |
| G1 - Pop & Arte | https://g1.globo.com/rss/g1/pop-arte/ | Entretenimento |
| G1 - São Paulo | https://g1.globo.com/rss/g1/sao-paulo/ | Regional |
| G1 - Rio de Janeiro | https://g1.globo.com/rss/g1/rio-de-janeiro/ | Regional |
| GloboEsporte - Futebol | https://ge.globo.com/rss/ge/futebol/ | Esportes |
| GloboEsporte - Futebol Internacional | https://ge.globo.com/rss/ge/futebol/futebol-internacional/ | Esportes |
| GloboEsporte - Corinthians | https://ge.globo.com/rss/ge/futebol/times/corinthians/ | Esportes |
| GloboEsporte - Palmeiras | https://ge.globo.com/rss/ge/futebol/times/palmeiras/ | Esportes |

### 13.2 Folha de S.Paulo e UOL

| Portal | URL do Feed | Categoria |
|--------|-------------|-----------|
| Folha - Principal | https://feeds.folha.uol.com.br/folha/emcimadahora/rss091.xml | Geral |
| Folha - Poder (Política) | https://feeds.folha.uol.com.br/poder/rss091.xml | Política |
| Folha - Mercado | https://feeds.folha.uol.com.br/mercado/rss091.xml | Economia |
| Folha - Mundo | https://feeds.folha.uol.com.br/mundo/rss091.xml | Internacional |
| Folha - Cotidiano | https://feeds.folha.uol.com.br/cotidiano/rss091.xml | Cidades |
| Folha - Esporte | https://feeds.folha.uol.com.br/esporte/rss091.xml | Esportes |
| Folha - Ilustrada | https://feeds.folha.uol.com.br/ilustrada/rss091.xml | Entretenimento |
| Folha - Ciência | https://feeds.folha.uol.com.br/ciencia/rss091.xml | Ciência |
| Folha - Ambiente | https://feeds.folha.uol.com.br/ambiente/rss091.xml | Meio Ambiente |
| UOL - Notícias | https://rss.uol.com.br/feed/noticias.xml | Geral |
| UOL - Economia | https://rss.uol.com.br/feed/economia.xml | Economia |
| UOL - Esporte | https://rss.uol.com.br/feed/esporte.xml | Esportes |
| UOL - Entretenimento | https://rss.uol.com.br/feed/entretenimento.xml | Entretenimento |

### 13.3 Estadão

| Portal | URL do Feed | Categoria |
|--------|-------------|-----------|
| Estadão - Principal | https://www.estadao.com.br/rss/ultimas.xml | Geral |
| Estadão - Política | https://www.estadao.com.br/rss/politica.xml | Política |
| Estadão - Economia | https://www.estadao.com.br/rss/economia.xml | Economia |
| Estadão - Internacional | https://www.estadao.com.br/rss/internacional.xml | Internacional |
| Estadão - Esportes | https://www.estadao.com.br/rss/esportes.xml | Esportes |
| Estadão - Cultura | https://www.estadao.com.br/rss/cultura.xml | Entretenimento |
| Estadão - Saúde | https://www.estadao.com.br/rss/saude.xml | Saúde |
| Estadão - Ciência | https://www.estadao.com.br/rss/ciencia.xml | Ciência |
| Estadão - Educação | https://www.estadao.com.br/rss/educacao.xml | Educação |

### 13.4 TV e Redes Nacionais

| Portal | URL do Feed | Categoria |
|--------|-------------|-----------|
| CNN Brasil | https://admin.cnnbrasil.com.br/feed/ | Geral |
| R7 - Notícias | https://noticias.r7.com/feed.xml | Geral |
| Band - Notícias | https://www.band.uol.com.br/rss/noticias.xml | Geral |

### 13.5 Governo e Fontes Oficiais

| Portal | URL do Feed | Categoria |
|--------|-------------|-----------|
| Agência Brasil | https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml | Governo |
| Agência Brasil - Política | https://agenciabrasil.ebc.com.br/rss/politica/feed.xml | Política |
| Agência Brasil - Economia | https://agenciabrasil.ebc.com.br/rss/economia/feed.xml | Economia |
| Senado Notícias | https://www12.senado.leg.br/noticias/feed | Política |
| Câmara Notícias | https://www.camara.leg.br/noticias/feed.xml | Política |

### 13.6 Jornais Regionais

| Portal | URL do Feed | Categoria |
|--------|-------------|-----------|
| O Globo | https://oglobo.globo.com/rss.xml | Geral |
| Zero Hora (RS) | https://gauchazh.clicrbs.com.br/ultimas-noticias/rss.xml | Regional |
| Correio Braziliense | https://www.correiobraziliense.com.br/rss/noticias.xml | Regional |
| Diário de Pernambuco | https://www.diariodepernambuco.com.br/rss/rss.xml | Regional |
| A Tarde (BA) | https://atarde.uol.com.br/rss | Regional |
| Jornal do Commercio (PE) | https://jc.ne10.uol.com.br/rss/rss.xml | Regional |

### 13.7 Portais Especializados

| Portal | URL do Feed | Categoria |
|--------|-------------|-----------|
| TecMundo | https://rss.tecmundo.com.br/feed | Tecnologia |
| Olhar Digital | https://olhardigital.com.br/feed/ | Tecnologia |
| Canaltech | https://canaltech.com.br/rss/ | Tecnologia |
| InfoMoney | https://www.infomoney.com.br/feed/ | Economia |
| Valor Econômico | https://valor.globo.com/rss/ | Economia |
| Exame | https://exame.com/feed/ | Economia |
| Lance! | https://www.lance.com.br/rss.xml | Esportes |

### 13.8 Veículos Internacionais (em Português)

| Portal | URL do Feed | Categoria |
|--------|-------------|-----------|
| BBC Brasil | https://www.bbc.com/portuguese/index.xml | Internacional |
| Deutsche Welle Brasil | https://rss.dw.com/xml/rss-br-all | Internacional |
| El País Brasil | https://feeds.elpais.com/mrss-s/pages/ep/site/brasil.elpais.com/portada | Internacional |

### 13.9 Script SQL para Popular Fontes Iniciais

```sql
-- Inserir fontes iniciais na tabela sources
INSERT INTO sources (name, url, category, frequency, active) VALUES
-- Grupo Globo
('G1 - Principal', 'https://g1.globo.com/rss/g1/', 'Geral', '30min', 1),
('G1 - Política', 'https://g1.globo.com/rss/g1/politica/', 'Política', '30min', 1),
('G1 - Economia', 'https://g1.globo.com/rss/g1/economia/', 'Economia', '1h', 1),
('G1 - Tecnologia', 'https://g1.globo.com/rss/g1/tecnologia/', 'Tecnologia', '1h', 1),
('G1 - Mundo', 'https://g1.globo.com/rss/g1/mundo/', 'Internacional', '1h', 1),
('G1 - Ciência e Saúde', 'https://g1.globo.com/rss/g1/ciencia-e-saude/', 'Ciência', '2h', 1),
('G1 - São Paulo', 'https://g1.globo.com/rss/g1/sao-paulo/', 'Regional', '1h', 1),
('GloboEsporte - Futebol', 'https://ge.globo.com/rss/ge/futebol/', 'Esportes', '30min', 1),

-- Folha
('Folha - Principal', 'https://feeds.folha.uol.com.br/folha/emcimadahora/rss091.xml', 'Geral', '30min', 1),
('Folha - Política', 'https://feeds.folha.uol.com.br/poder/rss091.xml', 'Política', '30min', 1),
('Folha - Mercado', 'https://feeds.folha.uol.com.br/mercado/rss091.xml', 'Economia', '1h', 1),
('Folha - Mundo', 'https://feeds.folha.uol.com.br/mundo/rss091.xml', 'Internacional', '1h', 1),
('Folha - Esporte', 'https://feeds.folha.uol.com.br/esporte/rss091.xml', 'Esportes', '1h', 1),

-- Estadão
('Estadão - Principal', 'https://www.estadao.com.br/rss/ultimas.xml', 'Geral', '30min', 1),
('Estadão - Política', 'https://www.estadao.com.br/rss/politica.xml', 'Política', '30min', 1),
('Estadão - Economia', 'https://www.estadao.com.br/rss/economia.xml', 'Economia', '1h', 1),

-- TV
('CNN Brasil', 'https://admin.cnnbrasil.com.br/feed/', 'Geral', '30min', 1),
('R7 - Notícias', 'https://noticias.r7.com/feed.xml', 'Geral', '1h', 1),

-- Governo
('Agência Brasil', 'https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml', 'Governo', '1h', 1),
('Senado Notícias', 'https://www12.senado.leg.br/noticias/feed', 'Política', '2h', 1),
('Câmara Notícias', 'https://www.camara.leg.br/noticias/feed.xml', 'Política', '2h', 1),

-- Especializados
('InfoMoney', 'https://www.infomoney.com.br/feed/', 'Economia', '1h', 1),
('TecMundo', 'https://rss.tecmundo.com.br/feed', 'Tecnologia', '1h', 1),
('Valor Econômico', 'https://valor.globo.com/rss/', 'Economia', '1h', 1),

-- Internacional
('BBC Brasil', 'https://www.bbc.com/portuguese/index.xml', 'Internacional', '1h', 1),
('Deutsche Welle Brasil', 'https://rss.dw.com/xml/rss-br-all', 'Internacional', '2h', 1);
```

---

## 14. API REST para Integração com Frontend

O coletor RSS expõe endpoints HTTP para integração com o frontend React do TMC Redação.

### 14.1 Endpoints de Artigos Coletados

```
GET /api/articles
```
Lista artigos coletados com paginação e filtros.

**Query Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| page | int | Página atual (default: 1) |
| limit | int | Itens por página (default: 20, max: 100) |
| category | string | Filtrar por categoria |
| source | string | Filtrar por fonte (source_id) |
| period | string | 'today', 'week', 'month' |
| search | string | Busca por título/conteúdo |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Título do artigo",
      "preview": "Resumo...",
      "content": "Conteúdo completo...",
      "url": "https://...",
      "image_url": "https://...",
      "source": "G1 - Política",
      "source_id": "uuid",
      "favicon": "https://...",
      "category": "Política",
      "tags": ["eleições", "governo"],
      "author": "Nome do autor",
      "published_at": "2025-01-07T10:30:00Z",
      "collected_at": "2025-01-07T10:45:00Z"
    }
  ],
  "total": 1250,
  "page": 1,
  "pages": 63
}
```

```
GET /api/articles/:id
```
Retorna um artigo específico com conteúdo completo.

### 14.2 Endpoints de Fontes RSS

```
GET /api/sources
```
Lista todas as fontes RSS configuradas.

```
POST /api/sources
```
Adiciona nova fonte RSS.

**Body:**
```json
{
  "name": "G1 - Política",
  "url": "https://g1.globo.com/rss/g1/politica/",
  "category": "Política",
  "frequency": "30min",
  "active": true
}
```

```
PUT /api/sources/:id
```
Atualiza configuração de uma fonte.

```
DELETE /api/sources/:id
```
Remove uma fonte (soft delete ou desativa).

```
POST /api/sources/:id/collect
```
Dispara coleta manual de uma fonte específica.

### 14.3 Endpoints de Estatísticas

```
GET /api/stats/collection
```
Retorna estatísticas de coleta.

**Response:**
```json
{
  "total_articles": 15420,
  "articles_today": 342,
  "active_sources": 28,
  "last_collection": "2025-01-07T15:30:00Z",
  "by_category": {
    "Política": 3200,
    "Economia": 2800,
    "Esportes": 2100
  }
}
```

### 14.4 Health Check

```
GET /api/health
```
Verifica status do serviço.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "last_successful_collection": "2025-01-07T15:30:00Z",
  "version": "1.0.0"
}
```

### 14.5 Estrutura de Projeto Atualizada

A pasta `functions/` deve incluir os endpoints REST:

```
tmc-rss-collector/
├── functions/
│   ├── __init__.py
│   ├── rss_collector.py         # Timer trigger (coleta automática)
│   ├── rss_collector_manual.py  # POST /api/sources/:id/collect
│   ├── health_check.py          # GET /api/health
│   ├── articles_list.py         # GET /api/articles
│   ├── articles_get.py          # GET /api/articles/:id
│   ├── sources_crud.py          # GET/POST/PUT/DELETE /api/sources
│   └── stats.py                 # GET /api/stats/collection
```

---

## 15. Estratégia de Desenvolvimento

### 15.1 Desenvolvimento Isolado

O coletor RSS será desenvolvido **separadamente** do frontend, na pasta `FeedRSS/`:

```
FeedRSS/
├── LevantamentosFeedRSS.md      # Este documento
├── tmc-rss-collector/           # Projeto Azure Functions
│   ├── function_app.py
│   ├── requirements.txt
│   ├── host.json
│   ├── local.settings.json
│   ├── functions/
│   ├── services/
│   ├── models/
│   ├── utils/
│   └── tests/
└── scripts/
    ├── create_tables.sql
    ├── seed_sources.sql
    └── test_feeds.py
```

**Vantagens desta abordagem:**
1. **Isolamento**: Backend pode ser testado independentemente
2. **Deploy independente**: Azure Functions tem seu próprio ciclo de deploy
3. **Sem conflitos**: Não polui o repositório do frontend React
4. **Desenvolvimento paralelo**: Equipes podem trabalhar simultaneamente

### 15.2 Fluxo de Integração

1. **Fase 1 - Desenvolvimento**: Implementar na pasta `FeedRSS/`
2. **Fase 2 - Validação**: Testar coleta e API localmente
3. **Fase 3 - Deploy**: Publicar Azure Functions
4. **Fase 4 - Integração**: Conectar frontend via variável `REACT_APP_API_BASE_URL`

### 15.3 Configuração do Frontend para Integração

No frontend React (`tmc-redacao/`), adicionar:

```javascript
// src/services/api.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:7071/api';

export const articlesApi = {
  list: (params) => fetch(`${API_BASE_URL}/articles?${new URLSearchParams(params)}`),
  get: (id) => fetch(`${API_BASE_URL}/articles/${id}`),
};

export const sourcesApi = {
  list: () => fetch(`${API_BASE_URL}/sources`),
  create: (data) => fetch(`${API_BASE_URL}/sources`, { method: 'POST', body: JSON.stringify(data) }),
  update: (id, data) => fetch(`${API_BASE_URL}/sources/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id) => fetch(`${API_BASE_URL}/sources/${id}`, { method: 'DELETE' }),
  collect: (id) => fetch(`${API_BASE_URL}/sources/${id}/collect`, { method: 'POST' }),
};
```

---

## 16. Checklist de Implementação

### Fase 1: Setup Inicial

- [ ] Criar estrutura de pastas `FeedRSS/tmc-rss-collector/`
- [ ] Configurar `requirements.txt` e `host.json`
- [ ] Criar `local.settings.json` com variáveis de ambiente
- [ ] Executar scripts SQL de criação de tabelas no Azure SQL
- [ ] Configurar Application Insights

### Fase 2: Desenvolvimento Core

- [ ] Implementar `models/source.py` e `models/article.py`
- [ ] Implementar `services/database.py`
- [ ] Implementar `services/rss_parser.py`
- [ ] Implementar `services/deduplication.py`
- [ ] Implementar `services/enrichment.py`
- [ ] Implementar `functions/rss_collector.py` (timer trigger)
- [ ] Testes unitários locais

### Fase 3: API REST

- [ ] Implementar `functions/articles_list.py`
- [ ] Implementar `functions/articles_get.py`
- [ ] Implementar `functions/sources_crud.py`
- [ ] Implementar `functions/stats.py`
- [ ] Implementar `functions/health_check.py`
- [ ] Configurar CORS para o frontend

### Fase 4: Resiliência

- [ ] Implementar retry com backoff (tenacity)
- [ ] Implementar circuit breaker por fonte
- [ ] Implementar logging estruturado
- [ ] Implementar métricas customizadas (Application Insights)

### Fase 5: Deploy e Integração

- [ ] Criar Azure Function App (Python 3.11, Consumption Plan)
- [ ] Configurar variáveis de ambiente no App Settings
- [ ] Deploy para ambiente de staging
- [ ] Popular tabela sources com feeds iniciais
- [ ] Testes end-to-end da API
- [ ] Conectar frontend React via `VITE_API_BASE_URL`
- [ ] Deploy para produção
- [ ] Configurar alertas no Application Insights

---

## 17. Considerações Finais

### Compatibilidade com Frontend

O modelo de dados foi projetado para ser compatível com o frontend React do TMC Redação:

- **RedacaoPage** (`/`): Consome `GET /api/articles` para exibir o feed
- **BuscadorPage** (`/configuracoes/buscador`): Consome `/api/sources` para CRUD de fontes
- **FeedSelector**: Usa os artigos retornados pela API para seleção múltipla

### Próximos Passos após RSS

1. **Transcrição de Vídeos**: Endpoint para processar vídeos do YouTube
2. **Google Trends Integration**: API para buscar tendências
3. **Geração com IA**: Endpoint para gerar matérias via OpenAI/Claude
4. **Autenticação**: Implementar JWT/Azure AD para proteger endpoints

---

*TMC Redação - Coletor RSS - Documento Técnico - Atualizado em Janeiro 2026*