# Guia: Anthropic Batch API para TMC

> Referência: Março 2026
> Fonte: [Anthropic Batch Processing Docs](https://platform.claude.com/docs/en/docs/build-with-claude/batch-processing)

---

## O Que É Batch Processing?

Batch processing é um modo de chamar a API do Claude onde, em vez de enviar uma requisição e esperar a resposta imediatamente, você **envia várias requisições de uma vez** e recebe todas as respostas depois (geralmente em menos de 1 hora).

### Analogia Simples

```
MODO ATUAL (real-time):
  Artigo 1 → enviar → esperar → resposta    (paga preço cheio)
  Artigo 2 → enviar → esperar → resposta    (paga preço cheio)
  Artigo 3 → enviar → esperar → resposta    (paga preço cheio)

MODO BATCH:
  Artigo 1 ─┐
  Artigo 2 ──┼── enviar tudo junto → esperar ~30min → todas as respostas
  Artigo 3 ─┘                                         (paga 50% do preço)
```

**A resposta é idêntica.** Mesmo modelo, mesmos prompts, mesma qualidade. A única diferença é que você espera um pouco mais (minutos/horas ao invés de segundos).

---

## Por Que 50% Mais Barato?

A Anthropic oferece o desconto porque batch permite que eles:
- Processem nas horas de menor demanda
- Otimizem o uso dos GPUs
- Não precisem garantir latência de segundos

Para o TMC isso é perfeito porque **todo o pipeline é assíncrono** — o collector roda a cada 15min, o scoring a cada 10min. Ninguém está esperando resultado em tempo real.

---

## Redução de Custo para o TMC

### Preços Comparados (por milhão de tokens)

| Modelo | Standard Input | Standard Output | **Batch Input** | **Batch Output** |
|--------|---:|---:|---:|---:|
| Claude Sonnet 4.5 | $3.00 | $15.00 | **$1.50** | **$7.50** |
| Claude Haiku 4.5 | $1.00 | $5.00 | **$0.50** | **$2.50** |

### Impacto no Custo Mensal do TMC

```
┌──────────────────────────────────────────────────────────────────────────┐
│  COMPONENTE                       │  Standard    │  Batch (-50%)        │
├───────────────────────────────────┼──────────────┼──────────────────────┤
│  Sonnet — geração + extras        │  $84/mês     │  $42/mês             │
│  Haiku — classificação (61K)      │  $18/mês     │  $9/mês              │
│  Haiku — scoring (61K)            │  $184/mês    │  $92/mês             │
│  Haiku — temas                    │  $5/mês      │  $3/mês              │
│  Exa API (sem desconto LLM)       │  $10/mês     │  $10/mês             │
│  Infraestrutura (sem desconto)    │  $22/mês     │  $22/mês             │
├───────────────────────────────────┼──────────────┼──────────────────────┤
│  TOTAL                            │  $323/mês    │  $178/mês            │
│  TOTAL BRL                        │  R$1.667     │  R$919               │
├───────────────────────────────────┼──────────────┼──────────────────────┤
│  ECONOMIA                         │              │  $145/mês (R$748)    │
└───────────────────────────────────┴──────────────┴──────────────────────┘
```

**Economia anual: ~$1,740 / R$8,978**

---

## O Que Precisa Mudar no TMC

### 1. Criar conta na Anthropic Direct API

O TMC hoje usa **Azure AI Services** como proxy para o Claude. Para usar Batch API, precisa da **Anthropic Direct API**.

**Passos:**
1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. Crie uma conta / organização
3. Adicione créditos (cartão de crédito)
4. Gere uma API key em Settings → API Keys
5. Adicione no `local.settings.json`:
   ```json
   {
     "ANTHROPIC_API_KEY": "sk-ant-api03-..."
   }
   ```

> O código do TMC (`llm_service.py:1643-1654`) já suporta Anthropic Direct API como fallback. Se `AZURE_AI_API_KEY` não estiver configurada e `ANTHROPIC_API_KEY` estiver, ele usa a API direta automaticamente.

### 2. Modificar o código para usar Batch API

O pipeline atual faz chamadas **uma a uma** (real-time). Para batch, precisa:

1. **Acumular as requisições** em vez de enviar imediatamente
2. **Enviar como batch** quando tiver um grupo pronto
3. **Buscar os resultados** quando o batch terminar
4. **Processar as respostas** e continuar o pipeline

#### Quais partes do TMC são candidatas a batch?

| Componente | Chamadas/mês | Candidato? | Por quê |
|---|---:|:---:|---|
| **Haiku scoring** (61K) | ~61,470 | **SIM** | Maior volume, totalmente assíncrono |
| **Haiku classification** (61K) | ~61,470 | **SIM** | Mesmo caso — alto volume, async |
| **Haiku theme naming** | ~3,000 | **SIM** | Async, roda a cada 30min |
| Sonnet article generation | ~650 | Talvez | Depende se a latência de ~1h é aceitável |
| Sonnet claim extraction | ~600 | Talvez | Roda junto com geração |
| Sonnet enrichment | ~300 | Provavelmente não | Baixo volume, benefício marginal |

**O maior ganho está no Haiku scoring + classification** — eles representam ~80% do custo total de LLM.

### 3. Exemplo de implementação (Python)

#### Criar um batch de scoring

```python
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY do env

# Acumular artigos para scoring
scoring_requests = []
for article in articles_to_score:
    scoring_requests.append(
        Request(
            custom_id=str(article.id),  # ID do artigo para mapear depois
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5",
                max_tokens=300,
                system=SCORING_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": SCORING_USER_PROMPT_TEMPLATE.format(
                            title=article.title,
                            content=article.content[:5000],
                            category=article.category or 'Nao especificada'
                        ),
                    }
                ],
            ),
        )
    )

# Enviar batch (até 100K requisições por batch)
message_batch = client.messages.batches.create(
    requests=scoring_requests
)

print(f"Batch criado: {message_batch.id}")
print(f"Status: {message_batch.processing_status}")
# → "in_progress"
```

#### Verificar status do batch

```python
# Polling para verificar status
batch_status = client.messages.batches.retrieve(message_batch.id)

print(f"Status: {batch_status.processing_status}")
print(f"Contagens: {batch_status.request_counts}")
# → request_counts.succeeded = 61470
# → request_counts.errored = 0
# → request_counts.processing = 0
```

#### Buscar resultados quando pronto

```python
# Iterar sobre os resultados
for result in client.messages.batches.results(message_batch.id):
    article_id = result.custom_id  # O ID do artigo que você enviou

    if result.result.type == "succeeded":
        # Extrair o JSON de scoring da resposta
        response_text = result.result.message.content[0].text
        scoring_data = json.loads(response_text)

        # Salvar no banco
        db.save_article_score(article_id, scoring_data)

    elif result.result.type == "errored":
        print(f"Erro no artigo {article_id}: {result.result.error}")
```

### 4. Arquitetura sugerida para o TMC

```
FLUXO ATUAL (real-time, caro):
┌─────────────┐    ┌──────────┐    ┌──────────┐
│ RSS Collector│───▶│ Score 1  │───▶│ Score 2  │───▶ ... (61K chamadas/mês)
│  (15 min)   │    │ (Haiku)  │    │ (Haiku)  │
└─────────────┘    └──────────┘    └──────────┘

FLUXO BATCH (assíncrono, 50% mais barato):
┌─────────────┐    ┌──────────────────┐    ┌────────────────┐
│ RSS Collector│───▶│ Acumular artigos │───▶│ Enviar Batch   │
│  (15 min)   │    │ (tabela "pending │    │ (a cada 30min  │
└─────────────┘    │  _scoring")      │    │  ou 1000 arts) │
                   └──────────────────┘    └───────┬────────┘
                                                   │
                                           ┌───────▼────────┐
                                           │ Polling/Webhook │
                                           │ (verificar se   │
                                           │  batch terminou)│
                                           └───────┬────────┘
                                                   │
                                           ┌───────▼────────┐
                                           │ Processar       │
                                           │ resultados e    │
                                           │ salvar scores   │
                                           └────────────────┘
```

---

## Limitações e Considerações

### Latência
- A maioria dos batches termina em **menos de 1 hora**
- Tempo máximo: **24 horas** (batches expiram depois disso)
- Resultados ficam disponíveis por **29 dias**

### Limites
- Máximo **100.000 requisições** por batch (ou 256 MB)
- Rate limits se aplicam ao número de requisições pendentes
- Em períodos de alta demanda, processamento pode ser mais lento

### O que funciona com Batch
- Vision (imagens)
- Tool use
- System messages
- Multi-turn conversations
- Prompt caching (com cache de 1 hora recomendado)

### O que NÃO funciona com Batch
- Streaming (respostas são completas, não parciais)
- Zero Data Retention (ZDR)
- Fast mode

### Para o TMC especificamente
- **Scoring/Classification**: Perfeito para batch — alto volume, sem urgência
- **Article generation**: Possível, mas depende se o usuário pode esperar ~1h pelo artigo gerado. Se o fluxo for "clicou gerar → espera resultado", talvez batch não seja ideal para geração. Mas se for "solicitar geração → pegar resultado depois", funciona.
- **Prompt caching**: Pode ser combinado com batch. O system prompt de scoring (~900 tokens) se repete em todas as chamadas. Usando cache de 1 hora + batch = economia dupla.

---

## Plano de Implementação

### Fase 1: Haiku Scoring + Classification via Batch (maior impacto)

| Passo | O que fazer | Esforço |
|-------|-------------|---------|
| 1 | Criar conta Anthropic Direct API + API key | 15 min |
| 2 | Instalar `anthropic` SDK no projeto (`pip install anthropic`) | 5 min |
| 3 | Criar novo service `batch_scoring_service.py` | 2-4 horas |
| 4 | Criar tabela `pending_scoring` no Azure SQL | 30 min |
| 5 | Criar timer trigger `batch_scorer` (envia batch a cada 30min) | 1-2 horas |
| 6 | Criar timer trigger `batch_results` (busca resultados) | 1-2 horas |
| 7 | Testar com um batch pequeno (100 artigos) | 1 hora |
| 8 | Deploy e monitorar por 1 semana | — |

**Economia: ~$103/mês (Haiku scoring $92 + classification $9)**

### Fase 2: Sonnet Generation via Batch (se latência for aceitável)

| Passo | O que fazer | Esforço |
|-------|-------------|---------|
| 1 | Modificar `generation_api.py` para modo async/batch | 3-4 horas |
| 2 | Criar fila de geração e polling de resultados | 2-3 horas |
| 3 | Adaptar frontend para mostrar status "gerando..." | 2-3 horas |

**Economia adicional: ~$42/mês (Sonnet na metade do preço)**

---

## Resumo

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  BATCH API = mesma qualidade, 50% mais barato                           │
│                                                                          │
│  O que muda:  Respostas demoram minutos/horas ao invés de segundos      │
│  O que NÃO muda:  Modelo, prompts, qualidade das respostas             │
│                                                                          │
│  Economia mensal:  $145 (R$ 748)                                        │
│  Economia anual:   $1.740 (R$ 8.978)                                    │
│                                                                          │
│  Custo mensal com Batch:  $178 (R$ 920 — 1.250 com margem)             │
│  Custo mensal sem Batch:  $323 (R$ 1.650 — 2.200 com margem)           │
│                                                                          │
│  Requisitos:                                                             │
│    1. Conta na Anthropic Direct API (console.anthropic.com)             │
│    2. Modificar código para acumular e enviar em batch                   │
│    3. Criar polling para buscar resultados                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```
