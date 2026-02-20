/**
 * Definição dos steps de cada tour de onboarding
 *
 * Cada tour é identificado por um ID único e contém uma lista de steps.
 * Cada step define:
 * - target: seletor CSS ou data-tour attribute do elemento a destacar
 * - title: título do tooltip
 * - content: explicação do elemento
 * - position: posicionamento preferido do tooltip (auto, top, bottom, left, right)
 * - beaconPosition: onde posicionar o beacon no elemento (top-right, top-left, etc)
 */

export const TOUR_IDS = {
  HOME: 'home',
  CRIAR: 'criar',
  EDITOR: 'editor',
  CONFIG: 'config'
};

export const tourSteps = {
  // Tour 1: Tela Inicial (RedacaoPage)
  [TOUR_IDS.HOME]: [
    {
      target: '[data-tour="filter-bar"]',
      title: 'Barra de Filtros',
      content: 'Use a barra de filtros para buscar matérias por título, categoria ou fonte.',
      position: 'bottom',
      beaconPosition: 'top-right'
    },
    {
      target: '[data-tour="article-card"]',
      title: 'Cards de Matérias',
      content: 'Clique em uma matéria para ver detalhes ou selecione várias para criar conteúdo.',
      position: 'right',
      beaconPosition: 'top-left'
    },
    {
      target: '[data-tour="trends-sidebar"]',
      title: 'Temas Quentes',
      content: 'Veja os temas quentes do momento. Clique em um tema para filtrar as matérias relacionadas.',
      position: 'right',
      beaconPosition: 'top-right'
    },
    {
      target: '[data-tour="create-button"]',
      title: 'Criar Nova Matéria',
      content: 'Comece a criar uma nova matéria a partir daqui.',
      position: 'bottom',
      beaconPosition: 'top-right'
    }
  ],

  // Tour 2: Tela de Criação (SelecionarFontePage)
  // Nota: source-video e source-tema são condicionais (feature flags)
  // O tour vai pular automaticamente steps cujo elemento não existe
  [TOUR_IDS.CRIAR]: [
    {
      target: '[data-tour="stepper"]',
      title: 'Etapas da Criação',
      content: 'Acompanhe as 4 etapas: Fonte → Texto-Base → Configurar → Editor.',
      position: 'bottom',
      beaconPosition: 'top-right'
    },
    {
      target: '[data-tour="source-feed"]',
      title: 'Matérias do Feed',
      content: 'Use matérias de concorrentes como ponto de partida.',
      position: 'bottom',
      beaconPosition: 'top-right'
    },
    {
      target: '[data-tour="source-zero"]',
      title: 'Criar do Zero',
      content: 'Cole qualquer texto ou comece do zero.',
      position: 'bottom',
      beaconPosition: 'top-right'
    },
    {
      target: '[data-tour="tip-box"]',
      title: 'Materiais Complementares',
      content: 'Você pode adicionar materiais complementares na etapa 3.',
      position: 'top',
      beaconPosition: 'top-right'
    }
  ],

  // Tour 3: Editor (CriarPostPage) - Para implementação futura
  [TOUR_IDS.EDITOR]: [
    {
      target: '[data-tour="editor-toolbar"]',
      title: 'Tom e Persona',
      content: 'Defina o estilo de escrita da IA.',
      position: 'bottom',
      beaconPosition: 'top-right'
    },
    {
      target: '[data-tour="chat-assistant"]',
      title: 'Chat Assistente',
      content: 'Peça edições, melhorias ou correções.',
      position: 'left',
      beaconPosition: 'top-right'
    },
    {
      target: '[data-tour="seo-panel"]',
      title: 'Painel SEO',
      content: 'Acompanhe a pontuação SEO em tempo real.',
      position: 'left',
      beaconPosition: 'top-right'
    },
    {
      target: '[data-tour="tags-input"]',
      title: 'Tags',
      content: 'Adicione tags para melhorar o SEO.',
      position: 'top',
      beaconPosition: 'top-right'
    },
    {
      target: '[data-tour="publish-button"]',
      title: 'Salvar e Publicar',
      content: 'Salve rascunhos ou publique direto no WordPress.',
      position: 'bottom',
      beaconPosition: 'top-left'
    }
  ],

  // Tour 4: Configurações
  [TOUR_IDS.CONFIG]: [
    {
      target: '[data-tour="config-sidebar"]',
      title: 'Menu de Configurações',
      content: 'Navegue entre as diferentes configurações do sistema.',
      position: 'right'
    },
    {
      target: '[data-tour="config-buscador"]',
      title: 'Buscador de Notícias',
      content: 'Configure as fontes de notícias e feeds RSS monitorados.',
      position: 'bottom'
    },
    {
      target: '[data-tour="config-trends"]',
      title: 'Google Trends',
      content: 'Configure os temas para monitoramento de tendências.',
      position: 'bottom'
    }
  ]
};

export default tourSteps;
