# Planejamento UI/UX - Ferramenta de Redação Jornalística

## 1. Página Redação (Principal)

### Layout Geral
```
[Header com Logo e Menu] | [Nome do Usuário]
─────────────────────────────────────────────────
[Barra de Filtros e Busca]
─────────────────────────────────────────────────
[Sidebar Esquerda]  |  [Grid de Matérias]  |  [Sidebar Direita]
     30%            |        40%            |        30%
```

### Header (Fixo no topo)
- **Esquerda**: Logo da ferramenta + Navegação principal (Redação, Minhas Matérias, Configurações)
- **Direita**: Ícone de notificações + Avatar do usuário

### Barra de Filtros (Logo abaixo do header)
- **Campo de busca**: Input grande e centralizado com ícone de lupa
- **Filtros rápidos** (chips clicáveis):
  - "Origem" (dropdown com lista de sites)
  - "Tema" (dropdown com categorias jornalísticas)
  - "Data" (hoje, última semana, último mês)
- **Toggle**: "Top 10 temas do dia" / "Top 10 temas da semana"
- **Botão destacado à direita**: "+ Criar do Zero" (primário, cor de destaque)

### Sidebar Esquerda - Temas em Alta
**Título**: "Temas em Alta"

**Google Trends** (primeira metade):
- Lista numerada (1-5) com temas
- Cada item mostra: posição, título do tema, crescimento percentual
- Hover: mini gráfico de tendência

**Twitter Trending** (segunda metade):
- Lista com hashtags e tópicos
- Badge com número de menções
- Ícone do Twitter em cada item

**Rodapé da sidebar**: Timestamp da última atualização

### Área Central - Grid de Matérias
- **Grid responsivo**: 2 colunas em desktop, 1 em mobile
- **Cada Card contém**:
  - **Checkbox no canto superior esquerdo**: para seleção
  - **Tag colorida no topo**: categoria/tema (Política, Esporte, Economia)
  - **Título da matéria**: 2 linhas máximo, truncado com "..."
  - **Favicon + Nome da origem**: fonte da notícia
  - **Data de publicação**: relativa (há 2h, há 1 dia)
  - **Preview de texto**: 2-3 linhas do conteúdo
  - **Botão de ação**: ícone de link externo (abre matéria original)

- **Espaçamento**: 16px entre cards
- **Hover**: leve elevação (shadow) e borda colorida

### Sidebar Direita - Painel de Ação
**Estado 1 - Nenhuma matéria selecionada**:
- Ilustração vazia
- Texto: "Selecione matérias para criar com inspiração"
- Estatísticas: "X matérias coletadas hoje"

**Estado 2 - Matérias selecionadas** (1 ou mais):
- **Contador**: "X matérias selecionadas"
- **Lista compacta** das selecionadas (título truncado + origem)
- **Botão primário grande**: "Criar com Inspiração"
- **Botão secundário**: "Limpar Seleção"

### Paginação/Scroll Infinito
- Rodapé da grid com "Carregar mais" ou scroll infinito automático
- Indicador de loading skeleton ao carregar

---

## 2. Tela: Criar Posts do Zero

### Layout Geral
```
[Header com navegação de voltar]
─────────────────────────────────────────────────
[Área de Edição 65%]  |  [Chat IA Lateral 35%]
```

### Header
- **Esquerda**: Botão "← Voltar para Redação"
- **Centro**: Campo editável "Título da Matéria" (placeholder: "Sem título")
- **Direita**:
  - Botão "Salvar Rascunho" (secundário)
  - Botão "Publicar" (primário, desabilitado se vazio)

### Área de Edição (Lado Esquerdo)

**Toolbar de Ferramentas** (fixo no topo da área de edição):
- **Linha 1 - Formatação básica**:
  - Negrito, Itálico, Sublinhado
  - Lista, Lista numerada
  - Link, Imagem
  - Desfazer/Refazer

- **Linha 2 - IA e Qualidade** (botões com ícones + labels):
  - "Tom" (dropdown: Formal, Informal, Técnico, Persuasivo)
  - "Persona" (dropdown: Jornalista, Especialista, Influencer)
  - "Correção Ortográfica" (toggle on/off) ou botão revisar e corrigir
  - "Traduzir" (dropdown: PT→EN, EN→PT, ES)
  - "Insights SEO" (abre modal)
  - "Sugerir Título" (gera sugestões baseadas no conteúdo)

**Editor de Texto**:
- Editor WYSIWYG estilo Medium/Notion
- Placeholder: "Comece a escrever ou peça ajuda à IA..."
- Contador de palavras no rodapé
- Indicador de "score SEO" (0-100) no rodapé

### Chat IA Lateral (Lado Direito)

**Header do Chat**:
- Ícone de IA + "Assistente de Redação"
- Botão "Limpar conversa" (ícone de lixeira)

**Área de Mensagens**:
- Mensagens do usuário: alinhadas à direita, fundo azul
- Respostas da IA: alinhadas à esquerda, fundo cinza claro
- Scroll automático para última mensagem

**Sugestões Rápidas** (chips clicáveis acima do input):
- "Pesquise sobre [tema]"
- "Sugira introdução"
- "Melhore este parágrafo"
- "Crie um resumo"

**Input do Chat**:
- Campo de texto expansível
- Placeholder: "Pergunte algo ou peça ajuda..."
- Botão enviar (ícone de seta)
- Atalho: "Enter para enviar"

**Funcionalidades Especiais**:
- Seleção de texto no editor → aparece botão flutuante "Perguntar à IA sobre isso"
- Respostas da IA têm botão "Inserir no texto"

---

## 3. Tela: Criar com Inspiração

### Fluxo: Etapa 1 - Configuração

```
[Header com progresso]
─────────────────────────────────────────────────
[Lista de Matérias] | [Painel de Configuração]
       50%           |          50%
```

### Header
- Breadcrumb: "Redação > Criar com Inspiração"
- Indicador de progresso: "1/3 - Selecionar Conteúdo"

### Lista de Matérias Selecionadas (Lado Esquerdo)
- **Card expandível para cada matéria**:
  - Header compacto: favicon, título, origem
  - Botão expandir/colapsar (chevron)

  **Quando expandido**:
  - Texto completo da matéria
  - **Checkboxes por parágrafo**: usuário marca o que quer usar
  - Highlight visual nos parágrafos selecionados
  - Contador: "X de Y parágrafos selecionados"

- Botão no rodapé: "+ Adicionar mais matérias"

### Painel de Configuração (Lado Direito)

**Seção 1 - Resumo da Seleção**:
- "X matérias | Y parágrafos selecionados"
- Estimativa: "~Z palavras no resultado"

**Seção 2 - Tom e Persona**:
- **Dropdown "Tom"**:
  - Opções: Formal, Informal, Técnico, Persuasivo, Neutro
  - Preview da descrição ao passar o mouse

- **Dropdown "Persona do Redator"**:
  - Opções: Jornalista Imparcial, Especialista, Colunista, Influencer
  - Preview da descrição

**Seção 3 - Configurações Avançadas** (colapsável):
- Slider "Criatividade": Factual ←→ Criativo
- Toggle "Incluir citações diretas"
- Toggle "Adicionar introdução e conclusão"
- Input "Palavras-chave SEO" (chips)

**Rodapé Fixo**:
- Botão "Cancelar" (secundário)
- Botão "Gerar Matéria" (primário, grande, destacado)

---

### Fluxo: Etapa 2 - Geração

```
[Header]
─────────────────────────────────────────────────
[Tela de Loading com Animação]
```

**Elemento Central**:
- Animação de IA trabalhando (spinner ou ilustração)
- Textos rotativos:
  - "Analisando matérias selecionadas..."
  - "Aplicando tom e persona..."
  - "Gerando conteúdo original..."
  - "Otimizando para SEO..."
- Barra de progresso (0-100%)
- Estimativa de tempo: "~30 segundos"

---

### Fluxo: Etapa 3 - Resultado

```
[Header com ações]
─────────────────────────────────────────────────
[Preview da Matéria] | [Painel de Análise]
        65%          |        35%
```

### Header
- **Esquerda**: Botão "← Refazer" (volta para configuração)
- **Centro**: "Matéria Gerada com Sucesso"
- **Direita**:
  - Botão "Regenerar" (com ícone de refresh)
  - Botão "Usar como Draft" (primário)

### Preview da Matéria (Lado Esquerdo)
- **Título sugerido** (editável)
- **Corpo do texto** em formato de leitura
- Toolbar de edição no topo (mesma do "Criar do Zero")
- Parágrafos editáveis inline
- Highlights das partes vindas de cada fonte (cores diferentes)

### Painel de Análise (Lado Direito)

**Seção 1 - Métricas**:
- Card com estatísticas:
  - Total de palavras
  - Tempo de leitura estimado
  - Score de originalidade (%)
  - Score SEO (0-100)

**Seção 2 - Fontes Utilizadas**:
- Lista compacta das matérias usadas
- Porcentagem de conteúdo de cada fonte
- Links para originais

**Seção 3 - Sugestões de Melhoria**:
- Lista de sugestões da IA:
  - "Adicione mais contexto no parágrafo 3"
  - "Considere incluir dados estatísticos"
  - "Título pode ser mais chamativo"
- Cada sugestão tem botão "Aplicar"

**Seção 4 - SEO**:
- Palavras-chave detectadas (chips)
- Densidade de keywords
- Sugestões de meta description

---

## 4. Página: Configurações - Buscador de Notícias

### Layout Geral
```
[Header]
─────────────────────────────────────────────────
[Sidebar Config]  |  [Área de Configuração]
      25%         |          75%
```

### Sidebar de Configurações
- Menu vertical:
  - **Buscador de Notícias** (ativo)
  - Google Trends
  - Perfil
  - Integrações
  - Preferências

### Área de Configuração

**Header da Seção**:
- Título: "Buscador de Notícias"
- Descrição: "Configure as fontes de onde deseja coletar matérias"
- Botão: "+ Adicionar Nova Fonte"

**Tabela de Fontes Configuradas**:

| Status | Favicon | Nome do Site | URL | Frequência | Última Coleta | Ações |
|--------|---------|--------------|-----|------------|---------------|-------|
| On/Off | [img] | G1 | g1.globo.com | A cada 1h | há 15 min | [Editar] [Excluir] |

- **Colunas**:
  - **Status**: Toggle on/off (ativa/desativa coleta)
  - **Favicon**: ícone do site
  - **Nome**: nome amigável editável
  - **URL**: endereço do RSS ou site
  - **Frequência**: dropdown (15min, 30min, 1h, 2h, 6h)
  - **Última Coleta**: timestamp relativo
  - **Ações**: botões de editar e excluir

**Estatísticas no Rodapé**:
- "X fontes ativas | Y matérias coletadas hoje | Z matérias na última semana"

### Modal: Adicionar Nova Fonte

```
┌─────────────────────────────────────────┐
│ Adicionar Nova Fonte          [X Fechar]│
├─────────────────────────────────────────┤
│                                         │
│ Nome da Fonte*                          │
│ [________________]                      │
│                                         │
│ URL (RSS ou Site)*                      │
│ [________________]                      │
│ Exemplo: https://site.com/rss           │
│                                         │
│ Categoria                               │
│ [Dropdown: Notícias Gerais]             │
│                                         │
│ Frequência de Coleta                    │
│ [Dropdown: A cada 1 hora]               │
│                                         │
│ [ ] Coletar apenas matérias em destaque │
│                                         │
├─────────────────────────────────────────┤
│              [Cancelar]  [Adicionar]    │
└─────────────────────────────────────────┘
```

**Validação**:
- Testa URL antes de salvar
- Mostra preview de matérias encontradas
- Feedback visual de sucesso/erro

---

## 5. Página: Configurações - Google Trends

### Layout Similar à página anterior
- Mesma sidebar de navegação
- Google Trends ativo no menu

### Área de Configuração

**Header da Seção**:
- Título: "Google Trends"
- Descrição: "Gerencie temas e termos a serem monitorados ou excluídos"

**Abas (Tabs)**:
- **Monitorar** (ativa)
- **Excluir**

### Aba: Monitorar

**Seção 1 - Adicionar Temas**:
- Input grande: "Digite temas ou palavras-chave"
- Tags/chips são criadas ao pressionar Enter
- Exemplo visual: [Tecnologia] [Inteligência Artificial] [Bitcoin]
- Botão: "Adicionar aos Monitorados"

**Seção 2 - Temas Monitorados**:
- Lista em cards:
  ```
  ┌──────────────────────────────────────┐
  │ Tecnologia                       [X] │
  │ Adicionado em: 20/11/2025            │
  │ Tendências encontradas: 45           │
  │ [Ver Tendências]                     │
  └──────────────────────────────────────┘
  ```

### Aba: Excluir

**Descrição**:
"Termos e frases que serão ignorados ao buscar tendências"

**Lista de Exclusão**:
- Input: "Adicionar termo a excluir"
- Lista editável com termos:
  - Cada item tem botão de remover
  - Exemplo: "Celebridade X", "Reality show Y", etc.

**Configurações Adicionais**:
- **Região**: Dropdown (Brasil, Estados Unidos, Global)
- **Categorias de Interesse**: Checkboxes múltiplos
  - [ ] Notícias
  - [ ] Tecnologia
  - [ ] Esportes
  - [ ] Entretenimento
  - [ ] Negócios

**Botão de Salvar**: Fixo no rodapé

---

## Sugestões de Melhoria UX

### 1. Atalhos de Teclado
- Ctrl+K: abrir busca rápida
- Ctrl+N: criar do zero
- Ctrl+S: salvar rascunho
- Esc: fechar modais

### 2. Onboarding Interativo
- Tour guiado na primeira utilização
- Tooltips contextuais
- Checklist de primeiros passos

### 3. Modo de Visualização
- Toggle entre grid e lista na página principal
- Modo leitura (sem distrações) no editor
- Modo escuro/claro

### 4. Histórico e Versionamento
- Histórico de versões das matérias
- Comparação lado a lado
- Restaurar versões antigas

### 5. Colaboração
- Comentários inline
- Sugestões de edição
- Notificações em tempo real

### 6. Analytics
- Dashboard com métricas de produtividade
- Temas mais usados
- Performance das matérias

### 7. Mobile First
- Layout responsivo
- App mobile dedicado
- Edição offline com sincronização

### 8. Acessibilidade
- Alto contraste
- Navegação por teclado completa
- Leitor de tela compatível
- Fontes ajustáveis

### 9. Integrações
- Export direto para WordPress, Medium
- Integração com Grammarly
- API para automações

### 10. Feedbacks Visuais
- Loading states claros
- Animações suaves (não intrusivas)
- Toasts para confirmações
- Estados vazios ilustrados

---

## Paleta de Cores Sugerida

- **Primária**: Azul profissional (#2563EB)
- **Secundária**: Cinza neutro (#6B7280)
- **Sucesso**: Verde (#10B981)
- **Alerta**: Amarelo (#F59E0B)
- **Erro**: Vermelho (#EF4444)
- **Fundo**: Branco/Cinza claro (#F9FAFB)
- **Texto**: Cinza escuro (#111827)

## Tipografia

- **Títulos**: Inter/Roboto Bold (24-32px)
- **Corpo**: Inter/Roboto Regular (14-16px)
- **Botões**: Inter/Roboto Medium (14px)
- **Legendas**: Inter/Roboto Regular (12px)
