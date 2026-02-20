# Analise Profunda do Pipeline de Clustering

## Data da Analise: 2026-02-05

---

## 1. RESUMO EXECUTIVO

O sistema de clustering apresenta **problemas criticos de fragmentacao**. Apesar do algoritmo estar implementado corretamente, o threshold de 0.58 resulta em **57.8% dos temas sendo singletons** (apenas 1 artigo).

### Metricas Atuais

| Metrica | Valor |
|---------|-------|
| Total de artigos | 2,353 |
| Artigos com embedding | 3,885 |
| Artigos com tema | 2,305 |
| Temas ativos | 815 |
| Temas singleton (1 artigo) | 471 (57.8%) |
| Coverage | 59.3% |
| Artigos pendentes | 123 |

---

## 2. ANALISE DO ALGORITMO

### 2.1 Configuracao Atual

```python
CLUSTERING_SIMILARITY_THRESHOLD = 0.58  # Cosine similarity minima
CLUSTERING_EMA_ALPHA = 0.25             # Peso do novo embedding no centroid
CLUSTERING_MERGE_THRESHOLD = 0.90       # Para merge de temas similares
TEMPORAL_BOOST_HOURS = 48               # Janela para boost temporal
TEMPORAL_BOOST_AMOUNT = 0.05            # +5% de similarity se recente
```

### 2.2 Fluxo de Processamento

```
1. Artigo entra no sistema
   |
2. Embedding gerado (OpenAI text-embedding-3-small, 1536 dims)
   |
3. Comparar com centroids dos temas ativos (cache em memoria)
   |
4. Se similarity >= 0.58 (+ temporal boost se aplicavel):
   |     -> Adicionar ao tema existente
   |     -> Atualizar centroid: new = 0.25*emb + 0.75*old
   |
5. Se similarity < 0.58:
   |     -> Criar novo tema (artigo vira seed)
   |
6. Verificar merge de temas (se similarity >= 0.90)
```

### 2.3 Formula do Centroid (EMA)

```
new_centroid = alpha * new_embedding + (1 - alpha) * old_centroid
             = 0.25 * new_embedding + 0.75 * old_centroid
```

**Problema identificado**: Com alpha=0.25, o centroid original se dilui rapidamente:
- Apos 5 artigos: apenas 23.7% do centroid original permanece
- Apos 10 artigos: apenas 5.6% do centroid original permanece
- **Consequencia**: Temas podem "migrar" semanticamente ao longo do tempo

---

## 3. ANALISE DAS 5 MATERIAS DE TESTE

### Materias Solicitadas:
1. "Mudanca climatica inviabilizara metade das sedes de Jogos de Inverno" (Esporte)
2. "MPF recomenda ressarcimento a aposentados - Banco Master" (Mercado/Financas)
3. "Confianca do consumidor recua" (Economia)
4. "Estatal da Bahia tenta anular negocio bilionario de ouro" (Economia/Politica)
5. "Novo imposto e mercado ilegal de cigarros" (Economia/Politica)

### Resultado da Busca no Banco:

| # | Materia | Categoria | Tema Atribuido | Similarity |
|---|---------|-----------|----------------|------------|
| 1 | Mudanca climatica inviabilizara... | Esportes | SEM TEMA | - |
| 2 | MPF recomenda ressarcimento a aposentados... | Economia | SEM TEMA | - |
| 3 | Confianca do consumidor recua... | Economia | SEM TEMA | - |
| 4 | Estatal da Bahia tenta anular... | Economia | SEM TEMA | - |
| 5 | Novo imposto reacende debate... | Economia | SEM TEMA | - |

**Observacao**: Todas as 5 materias estao PENDENTES de clustering (tem embedding mas nao tem tema).

### Matriz de Similaridade das 5 Materias:

```
           Jogos   MPF     Conf    Estatal Imposto
Jogos      ----    0.21    0.30    0.21    0.23
MPF        0.21    ----    0.32    0.33    0.32
Conf       0.30    0.32    ----    0.28    0.34
Estatal    0.21    0.33    0.28    ----    0.31
Imposto    0.23    0.32    0.34    0.31    ----
```

**Conclusao**: Nenhum par atinge o threshold de 0.58. Cada uma criaria seu proprio tema.

### Analise Semantica Manual:

- **Materia 1 (Jogos/Clima)**: Tema unico - esporte + mudanca climatica
- **Materias 2,3,4,5**: Todas relacionadas a economia/mercado, mas:
  - Similarity media entre elas: 0.31 (muito abaixo de 0.58)
  - Mesmo semanticamente relacionadas, os embeddings capturam nuances diferentes

---

## 4. PROBLEMAS IDENTIFICADOS

### 4.1 Alta Fragmentacao (CRITICO)

**471 de 815 temas (57.8%) tem apenas 1 artigo.**

Causas:
- Threshold de 0.58 pode ser muito alto para agrupar noticias do mesmo "assunto amplo"
- Noticias de economia sobre topicos diferentes (consumidor, impostos, mineracao) nao atingem 0.58

### 4.2 Distribuicao de Similarity Scores

| Faixa | Quantidade | Percentual |
|-------|------------|------------|
| Perfect (1.0 - seeds) | 700 | 30.4% |
| Very High (0.9-1.0) | 744 | 32.3% |
| High (0.7-0.9) | 835 | 36.2% |
| Threshold (0.58-0.7) | 726 | 31.5% |

**Observacao**: A maioria dos agrupamentos acontece com similarity alta (>0.7), indicando que apenas artigos muito similares sao agrupados.

### 4.3 Coerencia de Categorias nos Temas

Exemplos de temas com multiplas categorias:

| Tema | Artigos | Categoria Principal | Outras |
|------|---------|---------------------|--------|
| Idoso morre apos batida... | 74 | Brasil (47%) | Seguranca (40%), G1 (8%) |
| Festival de Verao... | 54 | Cultura (56%) | Entretenimento (13%), G1 (9%) |
| Flamengo pode esperar... | 50 | Esportes (100%) | - |
| OAB de SP... | 55 | Politica (96%) | - |

**Observacao positiva**: Temas bem formados tem coerencia de categoria (>50% em uma categoria).

### 4.4 Temas de Economia Fragmentados

- Total de temas com artigos de Economia: 90
- Temas singleton com artigos de Economia: 45 (50%)
- Poucos pares de temas economicos atingem similarity para merge (apenas 1 par >= 0.6)

---

## 5. EXEMPLO PRATICO: CLUSTER DO BANCO MASTER

A analise identificou um cluster natural sobre o **Banco Master/CPI**:

### Artigos Relacionados (26 encontrados):

| Materia | Tema Atribuido | Similarity |
|---------|----------------|------------|
| TCE-RJ vai investigar Cedae no Banco Master | Vorcaro visitou 17 vezes... | 0.756 |
| Comissao do Senado instala GT para Master | Relator da CPI... | 0.873 |
| CPMI do INSS adia depoimento de Vorcaro | Relator da CPI... | 0.813 |
| Senado instala comissao para Master | Relator da CPI... | 0.926 |
| CPMI avalia conducao coercitiva de Vorcaro | Relator da CPI... | 0.662 |
| Patrimonio dos aposentados foi atacado | Vorcaro visitou 17 vezes... | 0.641 |
| PF abre inquerito Fictor | Vorcaro visitou 17 vezes... | 0.853 |
| Oposicao protocola pedido de CPI Master | Relator da CPI... | 0.714 |

**Problema**: Artigos sobre o mesmo assunto (Banco Master) estao em 3 temas diferentes:
1. "Vorcaro visitou 17 vezes o Banco Central..." (38 artigos)
2. "Relator da CPI do Crime Organizado..." (40 artigos)
3. Varias materias ficaram SEM TEMA

**Matriz de similaridade desses artigos**: Varios pares tem similarity 0.70-0.90, mas estao em temas separados porque foram processados em ordens diferentes.

---

## 6. RECOMENDACOES

### 6.1 Ajustar Threshold (IMPACTO ALTO)

| Threshold | Efeito Esperado |
|-----------|-----------------|
| **0.58 (atual)** | Alta precisao, baixo recall - muitos singleton |
| **0.50** | Balanceado - grupos maiores, alguma contaminacao |
| **0.45** | Alto recall - grupos amplos, pode misturar topicos |

**Recomendacao**: Testar com 0.50 e monitorar qualidade dos clusters.

### 6.2 Reduzir EMA Alpha (IMPACTO MEDIO)

Mudar de `alpha=0.25` para `alpha=0.15` ou `alpha=0.10`:
- Centroid muda mais lentamente
- Tema mantem identidade original por mais tempo
- Previne "drift" semantico

### 6.3 Implementar Re-clustering Periodico (IMPACTO ALTO)

Rodar periodicamente (ex: diariamente):
1. Pegar todos os artigos das ultimas 48h
2. Re-calcular clusters do zero
3. Fazer merge de temas similares
4. Gerar novos nomes de temas via LLM

### 6.4 Adicionar Hierarquia de Temas (IMPACTO ALTO)

```
Nivel 1 (Macro): Economia
   |
Nivel 2 (Meso): Mercado Financeiro
   |
Nivel 3 (Micro): Caso Banco Master
```

Isso permitiria:
- Agrupar "Confianca do consumidor" e "Novo imposto" no nivel Economia
- Manter "Banco Master" como tema especifico

### 6.5 Usar Contexto Temporal Mais Forte

Aumentar `TEMPORAL_BOOST_AMOUNT` de 0.05 para 0.10:
- Artigos recentes tem +10% de chance de entrar em tema ativo
- Ajuda a manter "ciclos de noticias" juntos

---

## 7. AGRUPAMENTO IDEAL DAS 5 MATERIAS

### Cenario Atual (threshold 0.58):
- 5 temas separados (cada um vira singleton)

### Cenario com threshold 0.50:
- Ainda 5 temas separados (nenhum par atinge 0.50)

### Cenario com threshold 0.30:
```
Tema 1: Jogos de Inverno (1 artigo)
   - Mudanca climatica e Jogos

Tema 2: Economia/Mercado (4 artigos)
   - MPF ressarcimento
   - Confianca do consumidor
   - Estatal da Bahia
   - Novo imposto e cigarros
```

### Cenario Ideal (Hierarquico):
```
ECONOMIA (macro-tema)
├── Indicadores Economicos
│   └── Confianca do consumidor recua
├── Politica Tributaria
│   └── Novo imposto e mercado ilegal de cigarros
├── Setor Bancario
│   └── MPF ressarcimento - Banco Master
└── Negocios/Mineracao
    └── Estatal da Bahia - negocio de ouro

ESPORTE
└── Jogos de Inverno
    └── Mudanca climatica inviabilizara sedes
```

---

## 8. CONCLUSAO

O pipeline de clustering esta funcionando conforme projetado, mas o **threshold de 0.58 e muito alto** para agrupar noticias do mesmo "dominio" mas com "focos" diferentes.

### Acao Imediata:
1. Processar os 123 artigos pendentes de clustering
2. Testar threshold de 0.50 em ambiente de staging
3. Implementar merge de temas com similarity >= 0.60

### Acao de Medio Prazo:
1. Implementar hierarquia de temas (macro -> micro)
2. Criar sistema de re-clustering diario
3. Adicionar feedback humano para ajustar qualidade

---

## APENDICE: Queries de Diagnostico

```sql
-- Temas singleton
SELECT COUNT(*) FROM themes WHERE status = 'active' AND article_count = 1;

-- Artigos pendentes de clustering
SELECT COUNT(*)
FROM collected_articles a
JOIN article_embeddings e ON a.id = e.article_id
LEFT JOIN article_themes r ON a.id = r.article_id
WHERE r.article_id IS NULL;

-- Distribuicao de similarity
SELECT
    CASE
        WHEN similarity_score = 1.0 THEN 'perfect'
        WHEN similarity_score >= 0.9 THEN 'very_high'
        WHEN similarity_score >= 0.7 THEN 'high'
        ELSE 'threshold'
    END as range,
    COUNT(*) as cnt
FROM article_themes
GROUP BY
    CASE
        WHEN similarity_score = 1.0 THEN 'perfect'
        WHEN similarity_score >= 0.9 THEN 'very_high'
        WHEN similarity_score >= 0.7 THEN 'high'
        ELSE 'threshold'
    END;
```
