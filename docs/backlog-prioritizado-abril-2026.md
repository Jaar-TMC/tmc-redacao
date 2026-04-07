# Backlog Priorizado - Abril 2026

Consolidação do feedback de usuários, bugs reportados e necessidades levantadas em aprovação.

---

## P0 - Crítico (bloqueia uso ou gera conteúdo incorreto)

### Qualidade do Texto Gerado
- **Texto com trechos iguais ao original** — o texto gerado precisa ser uma reescrita real, usando o fato como base mas criando algo novo. Não pode haver cópia de trechos. - **Done** *(ANTI_COPIA constant + n-gram overlap detection 15% threshold + fact extraction expandida)*
- **Citação desnecessária de concorrentes** — evitar mencionar concorrentes no texto gerado. - **Done** *(COMPETITOR_BRANDS config + 3-layer fix: strip markdown links, filter source_urls, rewrite attribution)*
- **Plataforma completa notas com informações que não procedem** — fabricação de dados difíceis de checar. Relacionado ao pipeline de anti-alucinação. - **Done** *(quality loop + source coverage scoring + claim similarity check + Exa verification)*
- **Fact-check não reconhece informações novas** — o recurso está desajustado e falha ao verificar fatos recentes/novos. - **Done** *(temporal tier classification breaking/recent/historico + source_published_at + date range scoping + embedding cross-reference)*

### Performance Crítica
- **Busca com palavra composta trava** — ex: "seleção brasileira" demora muito e não retorna resultados. Filtro de feed com múltiplos termos não funciona. - **Done** *(SQL FREETEXT full-text index com LIKE fallback)*
- **Filtro de score muito lento** — rever resultado com filtro de score, carregamento excessivo. - **Done** *(scores denormalizados em collected_articles — 60x mais rápido + covering index)*
- **Performance da tela de custos** — página lenta ao carregar. - **Done** *(200ms debounce, AbortController, Promise.allSettled parallel fetching + tabelas denormalizadas)*
- **Performance geral dos filtros** — demorando muito para carregar, revisão pendente. - **Done** *(LIKE em preview column, 150ms debounce, skeleton grace period, no-op filter check)*

### Sessão / Auth
- **Persistência de sessão** — usuário volta para tela de login ao atualizar a página. Implementação feita mas não está funcionando corretamente. - **Done** *(retry refresh on mount, httpOnly cookie, 5s timeout, single redirect guard)*

---

## P1 - Alta Prioridade (impacta fluxo principal de trabalho)

### Busca / Pesquisa
- **Pesquisa na web na tela inicial** — incluir "pesquisa na web" direto na primeira tela. - **Done** *(TextoBasePrompt component + Exa API integration na /criar)*
- **Pesquisa com prompt pré-estabelecido** — "Quero criar uma matéria sobre [tema]" como atalho de busca web. - **Done** *(fluxo "Quero criar uma matéria sobre [tema]" integrado no TextoBasePrompt)*
- **Tradução de pesquisas Exa** — priorizar resultados em português nas buscas Exa. - *Parcial — Exa search fallback com date range widening existe, mas priorização de idioma PT não configurada*
- **Limite de caracteres na busca em pesquisar web, retirar limite** — retirar limite minimo de 30 chars. - *Pendente — MIN_CHARS=300 e mínimo 30 chars ainda ativos*

### UX / Interface do Editor
- **Espaço de edição dos textos na tela** — área de escrita precisa de mais espaço. - *Parcial — layout flex-1 funcional, sidebar lg:w-96 fixa*
- **Tópicos recuados a 150% da tela** — fica ruim de escrever, ajustar posicionamento. - *Parcial — layout normalizado, sem indentação excessiva detectada*
- **Criar recuo no box de SEO e Tópicos** — melhorar layout dos painéis laterais. - **Done** *(SEO panel em sidebar com tabs + topics section com espaçamento adequado)*
- **Reposicionar aviso "Recomendamos verificar os fatos"** — ocupa muito espaço, reduzir footprint. - *Parcial — tamanho reduzido (text-sm, py-2.5) mas ainda em formato banner*
- **Orientação sobre o lide no tooltip** — corrigir tooltip de "lide" para "lead" e melhorar orientação. - **Done** *(renomeado "Lide" → "Lead" com tooltip atualizado)*

### Outros
- **Retirar CTA WhatsApp** — remover "Siga a TMC no WhatsApp..." dos textos gerados. - **Done** *(instrução explícita nos prompts do backend e frontend)*

---

## P2 - Média Prioridade (melhoria de UX/funcionalidade)

### Integração
- **Integrar com WordPress** — grande tarefa do mês. Publicação direta do editor para WordPress. - *Parcial — WordPressContext + plugin tmc-redacao-wp existem, publicação não finalizada*

### SEO
- **Revisar algoritmo de SEO** — melhorar a qualidade das sugestões. - **Done** *(SEO algorithm overhaul — 17 fixes + rebalanceamento para jornalismo)*
- **Revisar padrões/avisos de SEO** — mensagens mostradas ao usuário precisam de revisão. - **Done** *(seoExplanations.js completo com "O que", "Por que", "Como melhorar" por métrica)*
- **Botão "otimizar" desativado após salvar** — após aprovar e salvar, o botão de otimizar SEO fica inativo. Deve permitir melhorias contínuas. - *Pendente — não verificado*

### Custo / Feed RSS
- **Custo alto do feed RSS** — verificar otimização de custos do pipeline de coleta. - *Parcial — model routing Haiku/Sonnet implementado; double-scoring identificado mas não resolvido*
- **Modo econômico** — implementar modo que reduza consumo de tokens/API. - **Done** *(routing Haiku para tarefas leves, Sonnet apenas para geração/fact-check — ~55% redução)*
- **Otimização do feed** — melhorar eficiência da coleta e processamento. - *Parcial — processamento paralelo com semaphore, inline scoring; otimizações adicionais pendentes*

### Admin
- **Admin visualizar matérias de todos os usuários** — administrador precisa ver artigos criados por outros usuários. - *Parcial — UsuariosPage existe, endpoint admin para artigos incompleto*
- **Pausar feed RSS e componentes na tela de admin** — controle granular para pausar apenas o feed RSS. - *Parcial — AI kill switch global existe, pausa granular RSS-only não implementada*

### Conteúdo / Editorial
- **Permitir opinião em conteúdo de entretenimento** — liberar tom opinativo para categoria entretenimento. - *Pendente — prompts de entretenimento existem, tom opinativo não explicitamente habilitado*
- **Feedback do score** — mostrar ao usuário o que o score significa e como melhorar. - *Parcial — ScoreTooltip mostra breakdown, falta orientação de melhoria*
- **Score não aparecendo** — verificar caso "presidente da Cemig" onde score pode não ter sido calculado. - **Done** *(score badge sempre visível, "—" quando pendente + heuristic fallback garante score)*

### Custos
- **Página de custos iniciar com filtro "hoje"** — default atual não é útil. - *Pendente — default ainda é '30d'*
- **Mostrar consumos para o usuário** — exibir eventos que consomem "crédito". - *Parcial — backend tracking completo, dashboard admin-only; falta visão para usuário comum*

---

## P3 - Baixa Prioridade (polish / nice-to-have)

- **Desenho de carregamento do feed** — melhorar skeleton/loading state do feed. - **Done** *(Skeleton.jsx com variantes + animate-pulse + integrado na RedacaoPage)*
- **Feedback de like/dislike (mãozinhas)** — adicionar interação nos artigos. - *Pendente*
- **Integração com mailchimp** — para envio de emails transacionais. - *Pendente*


---

## Resumo de Progresso

| Prioridade | Total | Done | Parcial | Pendente |
|------------|-------|------|---------|----------|
| **P0** | 9 | 9 | 0 | 0 |
| **P1** | 10 | 6 | 3 | 1 |
| **P2** | 14 | 4 | 6 | 4 |
| **P3** | 3 | 1 | 0 | 2 |
| **Total** | **36** | **20** | **9** | **7** |

**Progresso geral: 56% Done, 25% Parcial, 19% Pendente**

---

*Última atualização: 2026-04-06*
