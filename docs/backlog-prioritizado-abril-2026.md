# Backlog Priorizado - Abril 2026

Consolidação do feedback de usuários, bugs reportados e necessidades levantadas em aprovação.

---

## P0 - Crítico (bloqueia uso ou gera conteúdo incorreto)

### Qualidade do Texto Gerado
- **Texto com trechos iguais ao original** — o texto gerado precisa ser uma reescrita real, usando o fato como base mas criando algo novo. Não pode haver cópia de trechos.
- **Citação desnecessária de concorrentes** — evitar mencionar concorrentes no texto gerado.
- **Plataforma completa notas com informações que não procedem** — fabricação de dados difíceis de checar. Relacionado ao pipeline de anti-alucinação.
- **Fact-check não recon/ghece informações novas** — o recurso está desajustado e falha ao verificar fatos recentes/novos.

### Performance Crítica
- **Busca com palavra composta trava** — ex: "seleção brasileira" demora muito e não retorna resultados. Filtro de feed com múltiplos termos não funciona.
- **Filtro de score muito lento** — rever resultado com filtro de score, carregamento excessivo.
- **Performance da tela de custos** — página lenta ao carregar.
- **Performance geral dos filtros** — demorando muito para carregar, revisão pendente.

### Sessão / Auth
- **Persistência de sessão** — usuário volta para tela de login ao atualizar a página. Implementação feita mas não está funcionando corretamente.

---

## P1 - Alta Prioridade (impacta fluxo principal de trabalho)

### Busca / Pesquisa
- **Pesquisa na web na tela inicial** — incluir "pesquisa na web" direto na primeira tela.
- **Pesquisa com prompt pré-estabelecido** — "Quero criar uma matéria sobre [tema]" como atalho de busca web.
- **Tradução de pesquisas Exa** — priorizar resultados em português nas buscas Exa.
- **Limite de caracteres na busca em pesquisar web, retirar limite** — retirar limite minimo de 30 chars

### UX / Interface do Editor
- **Espaço de edição dos textos na tela** — área de escrita precisa de mais espaço.
- **Tópicos recuados a 150% da tela** — fica ruim de escrever, ajustar posicionamento.
- **Criar recuo no box de SEO e Tópicos** — melhorar layout dos painéis laterais.
- **Reposicionar aviso "Recomendamos verificar os fatos"** — ocupa muito espaço, reduzir footprint.
- **Orientação sobre o lide no tooltip** — corrigir tooltip de "lide" para "lead" e melhorar orientação.

### Outros
- **Retirar CTA WhatsApp** — remover "Siga a TMC no WhatsApp..." dos textos gerados.

---

## P2 - Média Prioridade (melhoria de UX/funcionalidade)

### Integração
- **Integrar com WordPress** — grande tarefa do mês. Publicação direta do editor para WordPress.

### SEO
- **Revisar algoritmo de SEO** — melhorar a qualidade das sugestões.
- **Revisar padrões/avisos de SEO** — mensagens mostradas ao usuário precisam de revisão.
- **Botão "otimizar" desativado após salvar** — após aprovar e salvar, o botão de otimizar SEO fica inativo. Deve permitir melhorias contínuas.

### Custo / Feed RSS
- **Custo alto do feed RSS** — verificar otimização de custos do pipeline de coleta.
- **Modo econômico** — implementar modo que reduza consumo de tokens/API.
- **Otimização do feed** — melhorar eficiência da coleta e processamento.

### Admin
- **Admin visualizar matérias de todos os usuários** — administrador precisa ver artigos criados por outros usuários.
- **Pausar feed RSS e componentes na tela de admin** — controle granular para pausar apenas o feed RSS.

### Conteúdo / Editorial
- **Permitir opinião em conteúdo de entretenimento** — liberar tom opinativo para categoria entretenimento.
- **Feedback do score** — mostrar ao usuário o que o score significa e como melhorar.
- **Score não aparecendo** — verificar caso "presidente da Cemig" onde score pode não ter sido calculado.

### Custos
- **Página de custos iniciar com filtro "hoje"** — default atual não é útil.
- **Mostrar consumos para o usuário** — exibir eventos que consomem "crédito".

---

## P3 - Baixa Prioridade (polish / nice-to-have)

- **Desenho de carregamento do feed** — melhorar skeleton/loading state do feed.
- **Feedback de like/dislike (mãozinhas)** — adicionar interação nos artigos.
- **Integração com mailchimp** — para envio de emails transacionais.


---

*Última atualização: 2026-04-01*
