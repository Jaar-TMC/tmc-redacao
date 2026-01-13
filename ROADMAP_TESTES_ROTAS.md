# Roadmap de Testes de Simulação de Rotas - TMC Redação

Este documento define os cenários de teste para cada rota da aplicação, simulando o comportamento de redatores. Cada seção contém prompts que serão utilizados por sub-agents especializados para testar funcionalidades específicas.

---

## Índice de Rotas

| # | Rota | Página | Prioridade |
|---|------|--------|------------|
| 1 | `/` | Redação (Home) | Alta |
| 2 | `/criar` | Selecionar Fonte | Alta |
| 3 | `/criar/texto-base` | Texto Base | Alta |
| 4 | `/criar/configurar` | Configurações da Matéria | Alta |
| 5 | `/criar/revisar` | Revisar e Gerar | Alta |
| 6 | `/criar/editor` | Editor de Matéria | Crítica |
| 7 | `/transcricao` | Transcrição de Vídeos | Média |
| 8 | `/minhas-materias` | Minhas Matérias | Média |
| 9 | `/configuracoes/buscador` | Config - Buscador | Baixa |
| 10 | `/configuracoes/trends` | Config - Trends | Baixa |

---

## 1. Página Redação (Home)

**Rota:** `/`
**Componente:** `RedacaoPage.jsx`
**Descrição:** Página principal com feed de notícias e temas quentes

### Prompt para Sub-Agent de Teste

```
TESTE: Página Redação (Home)
ROTA: http://localhost:5173/

OBJETIVO: Validar a página principal da redação como um redator buscando inspiração para matérias.

CENÁRIOS DE TESTE:

1. CARREGAMENTO INICIAL
   - Navegar para a rota /
   - Verificar se o header com navegação está presente
   - Verificar se a sidebar esquerda com "Temas Quentes" está visível
   - Verificar se o feed central com cards de matérias está carregado
   - Verificar se há indicação de quantidade de matérias

2. INTERAÇÃO COM FILTROS
   - Localizar a barra de filtros
   - Testar filtro por categoria (se disponível)
   - Testar busca por texto
   - Verificar se os resultados atualizam corretamente

3. INTERAÇÃO COM CARDS DE MATÉRIA
   - Identificar um card de matéria no feed
   - Verificar se possui: título, fonte, data, preview de texto
   - Testar hover no card (deve haver feedback visual)
   - Clicar no card e verificar comportamento

4. SIDEBAR TEMAS QUENTES
   - Verificar se lista de temas está presente
   - Clicar em um tema quente
   - Verificar se filtra ou redireciona corretamente

5. NAVEGAÇÃO PARA CRIAR
   - Localizar botão "Criar" no header
   - Clicar e verificar se abre menu dropdown
   - Selecionar opção de criação e verificar redirecionamento

CRITÉRIOS DE SUCESSO:
- [ ] Página carrega sem erros de console
- [ ] Todos os elementos visuais estão renderizados
- [ ] Interações respondem corretamente
- [ ] Navegação funciona entre seções
```

---

## 2. Selecionar Fonte

**Rota:** `/criar`
**Componente:** `SelecionarFontePage.jsx`
**Descrição:** Primeira etapa do fluxo de criação - escolher fonte de inspiração

### Prompt para Sub-Agent de Teste

```
TESTE: Selecionar Fonte de Inspiração
ROTA: http://localhost:5173/criar

OBJETIVO: Validar a seleção de fonte como primeiro passo do fluxo de criação de matéria.

CENÁRIOS DE TESTE:

1. CARREGAMENTO E STEPPER
   - Navegar para /criar
   - Verificar se o stepper mostra 4 etapas: Fonte → Texto-Base → Configurar → Editor
   - Verificar se "Fonte" está marcado como etapa atual (laranja com ring)
   - Verificar se demais etapas estão pendentes (cinza)

2. OPÇÕES DE FONTE DISPONÍVEIS
   - Identificar todas as opções de fonte:
     a) Link da Web (URL de notícia)
     b) Vídeo do YouTube
     c) Feed de Notícias
     d) Tema Quente
     e) Transcrição existente
   - Verificar se cada opção tem ícone e descrição clara

3. TESTE: FONTE VIA LINK
   - Selecionar opção "Link da Web"
   - Inserir URL de teste: https://g1.globo.com/economia/noticia/exemplo
   - Clicar em "Continuar" ou equivalente
   - Verificar redirecionamento para /criar/texto-base

4. TESTE: FONTE VIA FEED
   - Selecionar opção "Feed de Notícias"
   - Verificar se lista de matérias do feed aparece
   - Selecionar uma matéria
   - Verificar redirecionamento correto

5. TESTE: FONTE VIA TEMA QUENTE
   - Selecionar opção "Tema Quente"
   - Verificar se lista de temas aparece
   - Selecionar um tema
   - Verificar comportamento esperado

6. VALIDAÇÃO DE ERROS
   - Tentar continuar sem selecionar fonte
   - Verificar mensagem de erro apropriada
   - Inserir URL inválida e verificar validação

7. TESTE DE PERSISTÊNCIA - BOTÃO VOLTAR
   - Selecionar uma fonte (ex: "Link da Web")
   - Inserir URL de teste
   - Avançar para próxima etapa (/criar/texto-base)
   - Clicar no botão "Voltar"
   - VERIFICAR: A fonte selecionada ainda está marcada?
   - VERIFICAR: A URL inserida ainda está preenchida?
   - VERIFICAR: O estado visual da seleção está preservado?

CRITÉRIOS DE SUCESSO:
- [ ] Stepper exibe etapa correta
- [ ] Todas as opções de fonte estão funcionais
- [ ] Validações funcionam corretamente
- [ ] Navegação para próxima etapa funciona
- [ ] Botão "Voltar" retorna para home
- [ ] **PERSISTÊNCIA: Dados são mantidos ao voltar**
```

---

## 3. Texto Base

**Rota:** `/criar/texto-base`
**Componente:** `TextoBasePage.jsx`
**Descrição:** Segunda etapa - visualização e edição do texto base extraído

### Prompt para Sub-Agent de Teste

```
TESTE: Visualização do Texto Base
ROTA: http://localhost:5173/criar/texto-base

PRÉ-REQUISITO: Deve ter passado pela etapa de seleção de fonte (/criar)

OBJETIVO: Validar a exibição e edição do texto base extraído da fonte selecionada.

CENÁRIOS DE TESTE:

1. CARREGAMENTO E STEPPER
   - Verificar stepper com "Texto-Base" como etapa atual
   - Verificar se "Fonte" está marcado como completo (check verde)
   - Verificar breadcrumb ou indicação de navegação

2. EXIBIÇÃO DO TEXTO BASE
   - Verificar se o texto extraído da fonte está visível
   - Verificar formatação do texto (parágrafos, títulos)
   - Verificar se metadados da fonte estão exibidos (origem, data)

3. VARIANTES POR TIPO DE FONTE
   a) TextoBaseLink - Para URLs de notícias
      - Verificar extração de conteúdo do link
      - Verificar título e corpo do texto

   b) TextoBaseVideo - Para YouTube
      - Verificar preview do vídeo
      - Verificar transcrição do vídeo
      - Verificar player ou thumbnail

   c) TextoBaseFeed - Para matérias do feed
      - Verificar conteúdo completo da matéria
      - Verificar fonte original

   d) TextoBaseTema - Para temas quentes
      - Verificar contexto do tema
      - Verificar matérias relacionadas

4. EDIÇÃO DO TEXTO BASE
   - Verificar se texto é editável (se aplicável)
   - Testar seleção de trechos importantes
   - Verificar marcação de citações

5. NAVEGAÇÃO
   - Testar botão "Voltar" (deve ir para /criar)
   - Testar botão "Continuar" (deve ir para /criar/configurar)
   - Verificar se dados são preservados na navegação

6. TESTE DE PERSISTÊNCIA - BOTÃO VOLTAR
   - Fazer edições no texto base (se editável)
   - Selecionar/marcar trechos importantes
   - Avançar para próxima etapa (/criar/configurar)
   - Clicar no botão "Voltar"
   - VERIFICAR: O texto base ainda está visível?
   - VERIFICAR: Edições feitas foram preservadas?
   - VERIFICAR: Trechos marcados ainda estão selecionados?
   - Clicar "Voltar" novamente para /criar
   - VERIFICAR: A fonte selecionada ainda está correta?

7. TESTE DE NAVEGAÇÃO VIA STEPPER
   - Clicar no step "Fonte" no stepper (deve ser clicável pois está completo)
   - VERIFICAR: Navega corretamente para /criar
   - VERIFICAR: Dados da fonte estão preservados
   - Clicar no step "Texto-Base" no stepper
   - VERIFICAR: Retorna para /criar/texto-base
   - VERIFICAR: Conteúdo do texto base está preservado

CRITÉRIOS DE SUCESSO:
- [ ] Texto base carrega corretamente
- [ ] Variante correta é exibida baseada no tipo de fonte
- [ ] Edição funciona (se aplicável)
- [ ] Navegação preserva dados
- [ ] Stepper reflete progresso corretamente
- [ ] **PERSISTÊNCIA: Dados mantidos ao usar botão Voltar**
- [ ] **PERSISTÊNCIA: Navegação via stepper preserva dados**
```

---

## 4. Configurações da Matéria

**Rota:** `/criar/configurar`
**Componente:** `ConfigurarPage.jsx`
**Descrição:** Terceira etapa - configurar parâmetros da geração

### Prompt para Sub-Agent de Teste

```
TESTE: Configurações da Matéria
ROTA: http://localhost:5173/criar/configurar

PRÉ-REQUISITO: Deve ter passado pelas etapas anteriores

OBJETIVO: Validar todas as opções de configuração para geração da matéria.

CENÁRIOS DE TESTE:

1. CARREGAMENTO E STEPPER
   - Verificar stepper com "Configurar" como etapa atual
   - Verificar se "Fonte" e "Texto-Base" estão marcados como completos
   - Ícone do step deve ser Sliders

2. SEÇÃO: CONFIGURAÇÕES PRINCIPAIS
   a) Data de Publicação
      - Verificar campo de data
      - Testar seleção de data futura
      - Verificar formato da data

   b) Orientação sobre o Lide
      - Verificar campo de texto
      - Inserir orientação: "Focar no impacto econômico"
      - Verificar placeholder informativo

   c) Declarações de Fontes
      - Verificar campo para adicionar citações
      - Adicionar: "João Silva, economista: 'A inflação deve cair'"
      - Verificar botão de adicionar mais

   d) Contexto Adicional
      - Verificar textarea
      - Inserir contexto de background

   e) Créditos a Instituição
      - Verificar opções de radio: "Não precisa" / "Sim, precisa"
      - Testar seleção de cada opção
      - Se "Sim", verificar campo adicional

3. SEÇÃO: PERSONA DA MATÉRIA
   - Verificar opções disponíveis:
     * Jornalista Imparcial
     * Especialista
     * Colunista
     * Influencer
   - Testar seleção de cada persona
   - Verificar descrição de cada opção

4. SEÇÃO: TOM DA ESCRITA
   - Verificar dropdown/select
   - Opções: Formal, Informal, Técnico, Persuasivo, Neutro
   - Testar seleção de diferentes tons

5. SEÇÃO: INSTRUÇÕES PARA IA
   - Verificar textarea para instruções adicionais
   - Inserir: "Evitar termos técnicos, manter parágrafos curtos"

6. SEÇÃO: MATERIAIS COMPLEMENTARES
   a) Link da Web complementar
      - Verificar input de URL
      - Adicionar link e verificar validação

   b) Vídeo do YouTube
      - Verificar input de URL do YouTube
      - Adicionar link de vídeo

   c) Arquivo PDF
      - Verificar área de upload
      - Testar drag-and-drop (se disponível)

7. NAVEGAÇÃO
   - Testar "Voltar" (deve ir para /criar/texto-base)
   - Testar "Revisar e Gerar" (deve ir para /criar/revisar)
   - Verificar persistência das configurações

8. TESTE DE PERSISTÊNCIA - BOTÃO VOLTAR (CRÍTICO)
   - Preencher TODAS as configurações:
     * Selecionar persona: "Especialista"
     * Selecionar tom: "Técnico"
     * Inserir orientação do lide: "Focar em dados estatísticos"
     * Adicionar declaração de fonte
     * Inserir contexto adicional
     * Marcar "Sim, precisa" para créditos
     * Adicionar instruções para IA
   - Avançar para /criar/revisar
   - Clicar no botão "Voltar"
   - VERIFICAR: Persona selecionada ("Especialista") está mantida?
   - VERIFICAR: Tom selecionado ("Técnico") está mantido?
   - VERIFICAR: Orientação do lide está preservada?
   - VERIFICAR: Declarações de fontes estão preservadas?
   - VERIFICAR: Contexto adicional está preservado?
   - VERIFICAR: Opção de créditos está mantida?
   - VERIFICAR: Instruções para IA estão preservadas?
   - VERIFICAR: Materiais complementares estão preservados?

9. TESTE DE NAVEGAÇÃO VIA STEPPER
   - Clicar no step "Fonte" no stepper
   - VERIFICAR: Navega para /criar e mantém dados
   - Clicar no step "Texto-Base" no stepper
   - VERIFICAR: Navega para /criar/texto-base e mantém dados
   - Clicar no step "Configurar" no stepper
   - VERIFICAR: Retorna para /criar/configurar
   - VERIFICAR: TODAS as configurações estão preservadas

10. TESTE DE CICLO COMPLETO DE NAVEGAÇÃO
    - Preencher configurações
    - Ir para /criar/revisar
    - Voltar para /criar/configurar (verificar dados)
    - Voltar para /criar/texto-base (verificar dados)
    - Voltar para /criar (verificar dados)
    - Avançar novamente até /criar/configurar
    - VERIFICAR: Todos os dados foram preservados no ciclo completo

CRITÉRIOS DE SUCESSO:
- [ ] Todos os campos de configuração funcionam
- [ ] Validações estão presentes onde necessário
- [ ] Persona e tom são selecionáveis
- [ ] Materiais complementares podem ser adicionados
- [ ] Dados persistem na navegação
- [ ] **PERSISTÊNCIA: Todas as configurações mantidas ao voltar**
- [ ] **PERSISTÊNCIA: Navegação via stepper preserva dados**
- [ ] **PERSISTÊNCIA: Ciclo completo de navegação preserva dados**
```

---

## 5. Revisar e Gerar

**Rota:** `/criar/revisar`
**Componente:** `RevisarPage.jsx`
**Descrição:** Quarta etapa - revisar configurações antes de gerar

### Prompt para Sub-Agent de Teste

```
TESTE: Revisar e Gerar Matéria
ROTA: http://localhost:5173/criar/revisar

PRÉ-REQUISITO: Deve ter completado todas as configurações

OBJETIVO: Validar a revisão final antes da geração da matéria.

CENÁRIOS DE TESTE:

1. RESUMO DAS CONFIGURAÇÕES
   - Verificar exibição de todas as configurações escolhidas:
     * Fonte selecionada
     * Persona escolhida
     * Tom da escrita
     * Orientações do lide
     * Contexto adicional
     * Materiais complementares

2. EDIÇÃO RÁPIDA
   - Verificar se há opção de editar configurações
   - Testar link/botão para voltar e editar seção específica

3. PREVIEW DO TEXTO BASE
   - Verificar se texto base está visível para referência
   - Verificar formatação adequada

4. AÇÃO DE GERAÇÃO
   - Localizar botão "Gerar Matéria" ou equivalente
   - Verificar se está habilitado
   - Clicar e verificar:
     * Loading state
     * Feedback de progresso
     * Redirecionamento para editor após conclusão

5. TRATAMENTO DE ERROS
   - Simular erro de geração (se possível)
   - Verificar mensagem de erro amigável
   - Verificar opção de retry

6. TESTE DE PERSISTÊNCIA - BOTÃO VOLTAR
   - Na tela de revisão, verificar resumo de todas as configurações
   - Clicar no botão "Voltar" ou "Editar Configurações"
   - VERIFICAR: Retorna para /criar/configurar
   - VERIFICAR: Todas as configurações estão preservadas
   - Fazer uma alteração (ex: mudar persona)
   - Avançar novamente para /criar/revisar
   - VERIFICAR: O resumo reflete a alteração feita
   - VERIFICAR: Demais configurações permanecem inalteradas

7. TESTE DE EDIÇÃO RÁPIDA VIA RESUMO
   - No resumo, clicar em "Editar" ao lado de uma configuração específica
   - VERIFICAR: Navega para a seção correta
   - VERIFICAR: Após editar, consegue retornar para revisão
   - VERIFICAR: Alteração é refletida no resumo

8. TESTE DE NAVEGAÇÃO VIA STEPPER
   - Clicar em cada step anterior no stepper:
     * Step "Fonte" → verificar dados
     * Step "Texto-Base" → verificar dados
     * Step "Configurar" → verificar dados
   - Retornar para /criar/revisar via navegação
   - VERIFICAR: Resumo ainda exibe todas as configurações corretamente

CRITÉRIOS DE SUCESSO:
- [ ] Resumo exibe todas as configurações
- [ ] Botão de gerar funciona
- [ ] Loading state é exibido
- [ ] Redirecionamento para editor ocorre após sucesso
- [ ] Erros são tratados adequadamente
- [ ] **PERSISTÊNCIA: Voltar preserva configurações**
- [ ] **PERSISTÊNCIA: Edições são refletidas no resumo**
- [ ] **PERSISTÊNCIA: Navegação via stepper preserva dados**
```

---

## 6. Editor de Matéria (CRÍTICO)

**Rota:** `/criar/editor`
**Componente:** `CriarPostPage.jsx`
**Descrição:** Editor WYSIWYG principal para edição da matéria

### Prompt para Sub-Agent de Teste

```
TESTE: Editor de Matéria
ROTA: http://localhost:5173/criar/editor

OBJETIVO: Validar completamente o editor de matérias como ferramenta principal do redator.

CENÁRIOS DE TESTE:

1. CARREGAMENTO INICIAL
   - Verificar carregamento do editor TipTap
   - Verificar se matéria gerada está carregada (se veio do fluxo)
   - Verificar se mockdata carrega corretamente (acesso direto)

2. HEADER DO EDITOR
   a) Campo de Título
      - Verificar input do título
      - Editar título e verificar contador de caracteres
      - Verificar limite ideal (até 60 caracteres)

   b) Linha Fina (Subtítulo)
      - Verificar campo de linha fina
      - Editar e verificar contador (até 200 caracteres)
      - Verificar largura adequada do campo

3. TOOLBAR DE FORMATAÇÃO
   - Testar cada botão da toolbar:
     * Negrito (Ctrl+B)
     * Itálico (Ctrl+I)
     * Sublinhado (Ctrl+U)
     * Títulos (H1, H2, H3)
     * Lista com bullets
     * Lista numerada
     * Citação/Blockquote
     * Link (Ctrl+K)
     * Imagem
     * Desfazer/Refazer

4. ÁREA DE EDIÇÃO
   - Verificar se conteúdo é editável
   - Testar digitação de texto
   - Testar formatação de parágrafos
   - Testar criação de listas
   - Testar inserção de citações
   - Verificar placeholder quando vazio

5. SIDEBAR DIREITA - ABAS
   a) Aba "Assistente"
      - Verificar chat com IA
      - Enviar mensagem de teste
      - Verificar resposta da IA
      - Testar sugestões de melhoria

   b) Aba "SEO"
      - Verificar painel SEO Analyzer
      - Verificar gauge de score (0-100)
      - Verificar métricas:
        * Título (caracteres)
        * Linha Fina (caracteres)
        * Conteúdo (palavras)
        * Legibilidade (score Flesch)
        * Palavras-chave (densidade)
        * Tags/Tópicos

6. PAINEL SEO DETALHADO
   - Verificar cards de métricas individuais
   - Verificar cores de status (verde/amarelo/vermelho)
   - Editar conteúdo e verificar atualização em tempo real
   - Verificar sincronização do score no footer

7. SEÇÃO DE TAGS/TÓPICOS
   - Verificar campo de tags
   - Adicionar nova tag manualmente
   - Remover tag existente
   - Testar geração de tags por IA (se disponível)

8. FOOTER DO EDITOR
   - Verificar contadores:
     * Palavras
     * Caracteres
     * Tempo de leitura
   - Verificar score SEO sincronizado
   - Verificar botão de salvar/publicar

9. ATALHOS DE TECLADO
   - Testar Ctrl+B (negrito)
   - Testar Ctrl+I (itálico)
   - Testar Ctrl+K (inserir link)
   - Testar Ctrl+Z (desfazer)
   - Testar Ctrl+S (salvar, se implementado)

10. RESPONSIVIDADE
    - Redimensionar janela
    - Verificar comportamento da sidebar
    - Verificar toolbar em telas menores

CRITÉRIOS DE SUCESSO:
- [ ] Editor carrega e é funcional
- [ ] Todas as formatações funcionam
- [ ] Sidebar com abas funciona
- [ ] SEO Analyzer atualiza em tempo real
- [ ] Score do footer sincroniza com gauge
- [ ] Tags podem ser gerenciadas
- [ ] Atalhos de teclado funcionam
- [ ] Sem erros de console
```

---

## 7. Transcrição de Vídeos

**Rota:** `/transcricao`
**Componente:** `TranscricaoPage.jsx`
**Descrição:** Ferramenta de transcrição de vídeos do YouTube

### Prompt para Sub-Agent de Teste

```
TESTE: Transcrição de Vídeos
ROTA: http://localhost:5173/transcricao

OBJETIVO: Validar o fluxo completo de transcrição de vídeos do YouTube.

CENÁRIOS DE TESTE:

1. CARREGAMENTO INICIAL
   - Navegar para /transcricao
   - Verificar interface de entrada de URL
   - Verificar instruções para o usuário

2. INPUT DE URL DO YOUTUBE
   - Localizar campo de input
   - Inserir URL válida do YouTube
   - Verificar preview do vídeo
   - Verificar metadados (título, duração, canal)

3. PROCESSO DE TRANSCRIÇÃO
   - Iniciar transcrição
   - Verificar overlay de progresso
   - Verificar indicadores de etapas
   - Aguardar conclusão

4. VISUALIZAÇÃO DA TRANSCRIÇÃO
   - Verificar exibição do texto transcrito
   - Verificar timestamps clicáveis
   - Testar clique em timestamp (deve pular no vídeo)
   - Verificar MiniPlayer do vídeo

5. SELEÇÃO DE TRECHOS
   - Selecionar trecho do texto
   - Verificar tooltip de seleção
   - Marcar como citação importante
   - Verificar sidebar de seleções

6. AÇÕES COM TRANSCRIÇÃO
   - Copiar transcrição completa
   - Usar transcrição como fonte para matéria
   - Verificar redirecionamento para fluxo de criação

CRITÉRIOS DE SUCESSO:
- [ ] Input de URL funciona com validação
- [ ] Preview do vídeo é exibido
- [ ] Transcrição é gerada (ou mock funciona)
- [ ] Timestamps são clicáveis
- [ ] Seleção de trechos funciona
- [ ] Integração com fluxo de criação funciona
```

---

## 8. Minhas Matérias

**Rota:** `/minhas-materias`
**Componente:** `MinhasMaterias.jsx`
**Descrição:** Listagem de matérias do redator

### Prompt para Sub-Agent de Teste

```
TESTE: Minhas Matérias
ROTA: http://localhost:5173/minhas-materias

OBJETIVO: Validar a gestão de matérias do redator.

CENÁRIOS DE TESTE:

1. CARREGAMENTO DA LISTA
   - Navegar para /minhas-materias
   - Verificar listagem de matérias
   - Verificar se há matérias de exemplo/mock

2. FILTROS E BUSCA
   - Testar busca por título
   - Testar filtro por status (rascunho, publicada)
   - Testar ordenação (data, título)

3. CARD DE MATÉRIA
   - Verificar informações exibidas:
     * Título
     * Data de criação/modificação
     * Status (rascunho/publicada)
     * Preview do conteúdo
   - Testar hover no card

4. AÇÕES NA MATÉRIA
   - Editar matéria (deve abrir editor)
   - Duplicar matéria
   - Excluir matéria (com confirmação)
   - Publicar/Despublicar

5. ESTADO VAZIO
   - Verificar mensagem quando não há matérias
   - Verificar CTA para criar primeira matéria

CRITÉRIOS DE SUCESSO:
- [ ] Lista carrega corretamente
- [ ] Filtros funcionam
- [ ] Ações nas matérias funcionam
- [ ] Estado vazio é tratado
- [ ] Navegação para editor funciona
```

---

## 9. Configurações - Buscador

**Rota:** `/configuracoes/buscador`
**Componente:** `BuscadorPage.jsx`
**Descrição:** Configuração de fontes de busca

### Prompt para Sub-Agent de Teste

```
TESTE: Configurações do Buscador
ROTA: http://localhost:5173/configuracoes/buscador

OBJETIVO: Validar a configuração de fontes de notícias.

CENÁRIOS DE TESTE:

1. NAVEGAÇÃO
   - Acessar via menu Configurações
   - Verificar sidebar de navegação das configurações
   - Verificar tab "Buscador" está ativa

2. LISTAGEM DE FONTES
   - Verificar tabela de fontes configuradas
   - Verificar colunas: Nome, URL, Categoria, Status

3. ADICIONAR FONTE
   - Localizar botão "Adicionar Fonte"
   - Preencher formulário/modal
   - Salvar e verificar na lista

4. EDITAR FONTE
   - Selecionar fonte existente
   - Editar informações
   - Salvar alterações

5. ATIVAR/DESATIVAR FONTE
   - Testar toggle de status
   - Verificar feedback visual

6. REMOVER FONTE
   - Excluir fonte
   - Verificar confirmação
   - Verificar remoção da lista

CRITÉRIOS DE SUCESSO:
- [ ] Navegação funciona
- [ ] CRUD de fontes funciona
- [ ] Toggle de status funciona
- [ ] Validações estão presentes
```

---

## 10. Configurações - Trends

**Rota:** `/configuracoes/trends`
**Componente:** `TrendsPage.jsx`
**Descrição:** Configuração de temas monitorados

### Prompt para Sub-Agent de Teste

```
TESTE: Configurações de Trends
ROTA: http://localhost:5173/configuracoes/trends

OBJETIVO: Validar a configuração de temas quentes monitorados.

CENÁRIOS DE TESTE:

1. NAVEGAÇÃO
   - Acessar via sidebar de configurações
   - Verificar tab "Trends" está ativa

2. LISTAGEM DE TEMAS
   - Verificar lista de temas monitorados
   - Verificar informações exibidas por tema

3. ADICIONAR TEMA
   - Adicionar novo tema para monitorar
   - Configurar alertas (se disponível)

4. GERENCIAR TEMAS
   - Editar tema existente
   - Pausar/Ativar monitoramento
   - Remover tema

5. VISUALIZAÇÃO DE TRENDS
   - Verificar gráficos ou indicadores (se disponível)
   - Verificar histórico de tendências

CRITÉRIOS DE SUCESSO:
- [ ] Listagem funciona
- [ ] CRUD de temas funciona
- [ ] Monitoramento pode ser controlado
```

---

## Fluxos Completos de Teste (End-to-End)

### Fluxo 1: Criar Matéria a partir de Link

```
TESTE E2E: Criar Matéria via Link Web
DURAÇÃO ESTIMADA: 5-10 minutos

PASSOS:
1. Iniciar em / (Home)
2. Clicar em "Criar" → "Criar com Inspiração"
3. Em /criar, selecionar "Link da Web"
4. Inserir URL: https://exemplo.com/noticia-teste
5. Continuar para /criar/texto-base
6. Verificar texto extraído
7. Continuar para /criar/configurar
8. Configurar:
   - Persona: Jornalista Imparcial
   - Tom: Formal
   - Adicionar orientação do lide
9. Continuar para /criar/revisar
10. Revisar e clicar "Gerar Matéria"
11. Em /criar/editor:
    - Editar título
    - Ajustar conteúdo
    - Verificar SEO score
    - Adicionar tags
12. Salvar matéria

CRITÉRIOS DE SUCESSO:
- [ ] Fluxo completo sem erros
- [ ] Dados persistem entre etapas
- [ ] Matéria é salva corretamente
```

### Fluxo 2: Criar Matéria a partir de Vídeo

```
TESTE E2E: Criar Matéria via Transcrição de Vídeo
DURAÇÃO ESTIMADA: 10-15 minutos

PASSOS:
1. Navegar para /transcricao
2. Inserir URL do YouTube
3. Aguardar transcrição
4. Selecionar trechos importantes
5. Clicar "Usar como fonte"
6. Seguir fluxo de criação (/criar → /criar/editor)
7. Verificar citações selecionadas no texto
8. Finalizar e salvar

CRITÉRIOS DE SUCESSO:
- [ ] Transcrição funciona
- [ ] Trechos selecionados são preservados
- [ ] Matéria final inclui referência ao vídeo
```

### Fluxo 3: Editar Matéria Existente

```
TESTE E2E: Editar Matéria Salva
DURAÇÃO ESTIMADA: 3-5 minutos

PASSOS:
1. Navegar para /minhas-materias
2. Selecionar matéria existente
3. Clicar "Editar"
4. Modificar título e conteúdo
5. Verificar atualização do SEO
6. Salvar alterações
7. Verificar na lista de matérias

CRITÉRIOS DE SUCESSO:
- [ ] Matéria abre no editor
- [ ] Edições são salvas
- [ ] SEO atualiza em tempo real
```

### Fluxo 4: Teste de Persistência com Navegação Completa (CRÍTICO)

```
TESTE E2E: Persistência de Dados ao Navegar para Trás
DURAÇÃO ESTIMADA: 10-15 minutos

OBJETIVO: Validar que TODOS os dados são preservados ao usar botões "Voltar" e navegação via stepper.

PASSOS:

FASE 1 - PREENCHIMENTO COMPLETO:
1. Navegar para /criar
2. Selecionar fonte "Link da Web"
3. Inserir URL: https://g1.globo.com/economia/noticia-teste
4. Continuar para /criar/texto-base
5. (Se editável) Marcar trechos importantes
6. Continuar para /criar/configurar
7. Preencher TODAS as configurações:
   - Persona: "Especialista"
   - Tom: "Técnico"
   - Orientação do lide: "Texto de teste para lide"
   - Declaração: "João Silva, CEO: 'Declaração de teste'"
   - Contexto: "Contexto adicional de teste"
   - Créditos: "Sim, precisa"
   - Instruções IA: "Instruções de teste"
8. Continuar para /criar/revisar
9. ANOTAR: Resumo exibido para comparação

FASE 2 - TESTE DE NAVEGAÇÃO REGRESSIVA:
10. Clicar botão "Voltar"
11. VERIFICAR em /criar/configurar:
    - [ ] Persona = "Especialista"
    - [ ] Tom = "Técnico"
    - [ ] Orientação do lide = "Texto de teste para lide"
    - [ ] Declaração presente
    - [ ] Contexto presente
    - [ ] Créditos = "Sim, precisa"
    - [ ] Instruções IA presentes

12. Clicar botão "Voltar"
13. VERIFICAR em /criar/texto-base:
    - [ ] Texto base visível
    - [ ] Trechos marcados preservados (se aplicável)

14. Clicar botão "Voltar"
15. VERIFICAR em /criar:
    - [ ] Fonte "Link da Web" selecionada
    - [ ] URL preenchida

FASE 3 - TESTE DE NAVEGAÇÃO PROGRESSIVA:
16. Avançar novamente: /criar → /criar/texto-base
17. VERIFICAR: Dados mantidos
18. Avançar: /criar/texto-base → /criar/configurar
19. VERIFICAR: TODAS as configurações mantidas
20. Avançar: /criar/configurar → /criar/revisar
21. VERIFICAR: Resumo idêntico ao anotado no passo 9

FASE 4 - TESTE VIA STEPPER:
22. Em /criar/revisar, clicar no step "Fonte" no stepper
23. VERIFICAR: Navega para /criar com dados preservados
24. Clicar no step "Configurar" no stepper
25. VERIFICAR: Navega para /criar/configurar com dados preservados
26. Clicar no step "Texto-Base" no stepper
27. VERIFICAR: Navega para /criar/texto-base com dados preservados

FASE 5 - TESTE DE MODIFICAÇÃO E PERSISTÊNCIA:
28. Em qualquer etapa, fazer uma modificação
29. Navegar para frente e para trás
30. VERIFICAR: Modificação foi preservada
31. VERIFICAR: Outros dados não foram afetados

CRITÉRIOS DE SUCESSO:
- [ ] Navegação regressiva (Voltar) preserva 100% dos dados
- [ ] Navegação progressiva (Continuar) preserva 100% dos dados
- [ ] Navegação via stepper preserva 100% dos dados
- [ ] Modificações são corretamente salvas
- [ ] Não há perda de dados em nenhum cenário
- [ ] Resumo final reflete estado correto
```

### Fluxo 5: Teste de Abandono e Retorno

```
TESTE E2E: Abandono do Fluxo e Retorno
DURAÇÃO ESTIMADA: 5-7 minutos

OBJETIVO: Testar o comportamento quando o usuário abandona o fluxo e retorna.

PASSOS:
1. Iniciar fluxo de criação em /criar
2. Preencher fonte e avançar até /criar/configurar
3. Preencher algumas configurações
4. ABANDONAR: Navegar para / (Home) via menu
5. Retornar para /criar
6. VERIFICAR: O que acontece?
   - Dados anteriores são mantidos?
   - Usuário é redirecionado para onde parou?
   - Aparece mensagem de "rascunho em andamento"?

7. Se dados foram perdidos:
   - VERIFICAR: Há confirmação antes de perder dados?
   - VERIFICAR: Mensagem clara sobre perda de dados?

8. Se dados foram mantidos:
   - VERIFICAR: Stepper reflete etapa correta?
   - VERIFICAR: Todos os dados estão presentes?

CRITÉRIOS DE SUCESSO:
- [ ] Comportamento de abandono é claro
- [ ] Se há rascunho, usuário é informado
- [ ] Se dados são perdidos, há confirmação prévia
- [ ] UX de retorno é intuitiva
```

---

## Notas para Sub-Agents

### Configuração do Ambiente
- URL Base: `http://localhost:5173`
- Browser: Chromium via Playwright
- Timeout padrão: 30 segundos

### Ferramentas Disponíveis
- `mcp__playwright__browser_navigate` - Navegar para URL
- `mcp__playwright__browser_snapshot` - Capturar estado da página
- `mcp__playwright__browser_click` - Clicar em elementos
- `mcp__playwright__browser_type` - Digitar texto
- `mcp__playwright__browser_fill_form` - Preencher formulários

### Padrão de Relatório
Cada sub-agent deve retornar:
```
## Resultado do Teste: [Nome da Rota]

### Status: ✅ PASSOU / ❌ FALHOU / ⚠️ PARCIAL

### Cenários Testados
- [x] Cenário 1 - OK
- [ ] Cenário 2 - Falhou: [descrição]
- [x] Cenário 3 - OK

### Erros Encontrados
1. [Descrição do erro]
   - Console: [mensagem de erro]
   - Impacto: [alto/médio/baixo]

### Screenshots
- [link para screenshot se relevante]

### Recomendações
- [sugestões de correção]
```

---

## Cronograma de Execução Sugerido

| Fase | Rotas | Prioridade | Estimativa |
|------|-------|------------|------------|
| 1 | `/criar/editor` | Crítica | 30 min |
| 2 | `/`, `/criar`, `/criar/*` | Alta | 60 min |
| 3 | `/transcricao`, `/minhas-materias` | Média | 30 min |
| 4 | `/configuracoes/*` | Baixa | 20 min |
| 5 | Fluxos E2E (incluindo persistência) | **Crítica** | 60 min |

**Total estimado: ~3.5 horas de teste automatizado**

### Prioridade dos Testes de Persistência

| Teste | Criticidade | Impacto se Falhar |
|-------|-------------|-------------------|
| Fluxo 4: Persistência Completa | 🔴 Crítica | Perda de trabalho do redator |
| Configurar → Voltar | 🔴 Crítica | Perda de configurações |
| Texto-Base → Voltar | 🟡 Alta | Re-trabalho necessário |
| Fonte → Voltar | 🟡 Alta | Re-seleção de fonte |
| Navegação via Stepper | 🟡 Alta | UX comprometida |
| Fluxo 5: Abandono | 🟢 Média | Confusão do usuário |

---

*Documento gerado em: 2024-12-23*
*Versão: 1.1*
*Atualização: Adicionados testes de persistência para botões "Voltar" e navegação via stepper*
