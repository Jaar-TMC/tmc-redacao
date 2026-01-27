/**
 * SEO Prompt Templates - Templates for AI optimization prompts by category
 *
 * These templates provide specific, actionable instructions for each SEO metric
 * that can be used to generate intelligent prompts.
 */

/**
 * Exact scoring rules that the SEO analyzer looks for
 * Pass these to AI to ensure it uses patterns that will score points
 */
export const SEO_SCORING_RULES = {
  // Power words that add points to title
  powerWords: ['exclusivo', 'revela', 'urgente', 'novo', 'inedito', 'descubra', 'veja', 'confira', 'impactante', 'surpreendente'],

  // Authority patterns for E-E-A-T scoring
  authorityPatterns: [
    'segundo apuracao',
    'em entrevista exclusiva',
    'nossa reportagem',
    'presencialmente',
    'dados oficiais',
    'documento obtido',
    'a reportagem descobriu',
    'apurou que'
  ],

  // Source citation patterns
  sourcePatterns: [
    'segundo [Nome]',
    'de acordo com',
    'informou',
    'dados da',
    'pesquisa da',
    'conforme',
    'afirmou',
    'declarou'
  ],

  // Expert keywords for expertise scoring
  expertKeywords: [
    'especialista',
    'analista',
    'professor',
    'economista',
    'medico',
    'advogado',
    'pesquisador',
    'doutor',
    'consultor'
  ],

  // Official sources for authority scoring
  officialSources: [
    'governo',
    'ministerio',
    'policia',
    'tribunal',
    'IBGE',
    'Banco Central',
    'prefeitura',
    'confederacao',
    'federacao',
    'Senado',
    'Camara',
    'STF',
    'MPF'
  ],

  // CTA words for linha fina
  ctaWords: ['saiba mais', 'veja', 'confira', 'entenda', 'descubra', 'acompanhe', 'leia'],

  // Transition words for readability
  transitionWords: [
    'alem disso',
    'portanto',
    'no entanto',
    'por outro lado',
    'assim',
    'dessa forma',
    'em contrapartida',
    'consequentemente',
    'diante disso',
    'nesse contexto',
    'sendo assim',
    'por fim'
  ],

  // Exact scoring thresholds
  thresholds: {
    title: {
      minChars: 50,
      maxChars: 60,
      keywordInFirst3Words: true
    },
    linhaFina: {
      minChars: 120,
      maxChars: 155,
      needsCTA: true,
      needsKeyword: true
    },
    firstParagraph: {
      idealWords: { min: 40, max: 60 }
    },
    paragraphs: {
      maxSentences: 4
    },
    sentences: {
      maxWords: 20
    },
    keywordDensity: {
      min: 1.0,
      max: 2.5
    }
  },

  // Categories that AI CAN optimize
  aiOptimizableMetrics: [
    'titleOptimization',
    'metaDescription',
    'keywordStrategy',
    'wordCountDepth',
    'contentStructure',
    'readability',
    'experience',
    'expertise',
    'authority',
    'trust',
    'featuredSnippet',
    'aiOverview'
  ],

  // Categories that require manual work (user must do)
  manualOnlyMetrics: [
    'internalLinks',
    'externalLinks',
    'mediaOptimization',
    'urlSlug'
  ]
};

/**
 * Stop words to filter out when extracting keywords
 */
export const STOP_WORDS = [
  'de', 'da', 'do', 'das', 'dos', 'em', 'no', 'na', 'nos', 'nas',
  'para', 'por', 'com', 'sem', 'sob', 'sobre', 'entre', 'apos',
  'que', 'como', 'onde', 'quando', 'quem', 'qual', 'quais',
  'este', 'esta', 'esse', 'essa', 'isso', 'isto', 'aquele', 'aquela',
  'seu', 'sua', 'seus', 'suas', 'dele', 'dela', 'deles', 'delas',
  'mais', 'menos', 'muito', 'pouco', 'bem', 'mal', 'ja', 'ainda',
  'tambem', 'apenas', 'somente', 'ate', 'desde', 'durante', 'alem',
  'uma', 'um', 'uns', 'umas', 'o', 'a', 'os', 'as', 'e', 'ou', 'mas',
  'porem', 'contudo', 'todavia', 'entretanto', 'porque', 'pois',
  'foi', 'sera', 'seria', 'esta', 'estao', 'tem', 'pode', 'vai',
  'fazer', 'feito', 'ter', 'sido', 'sao', 'ano', 'anos', 'dia', 'dias'
];

/**
 * Category display names (Portuguese)
 */
export const CATEGORY_NAMES = {
  contentQuality: 'Qualidade do Conteudo',
  onPageOptimization: 'Otimizacao On-Page',
  eeatSignals: 'E-E-A-T (Credibilidade)',
  technicalExcellence: 'Excelencia Tecnica',
  aiSerpOptimization: 'IA & SERP'
};

/**
 * Metric display names (Portuguese)
 */
export const METRIC_NAMES = {
  // Content Quality
  wordCountDepth: 'Extensao e Profundidade',
  contentStructure: 'Estrutura do Conteudo',
  readability: 'Legibilidade',
  // On-Page
  titleOptimization: 'Titulo',
  metaDescription: 'Linha Fina',
  keywordStrategy: 'Palavras-chave',
  urlSlug: 'URL/Slug',
  // E-E-A-T
  experience: 'Experiencia',
  expertise: 'Expertise',
  authority: 'Autoridade',
  trust: 'Confianca',
  // Technical
  internalLinks: 'Links Internos',
  externalLinks: 'Links Externos',
  mediaOptimization: 'Midia',
  // AI/SERP
  featuredSnippet: 'Featured Snippet',
  aiOverview: 'AI Overview'
};

/**
 * Prompt templates for each category and metric
 * Placeholders like {variableName} will be replaced with actual values
 */
export const SEO_PROMPT_TEMPLATES = {
  contentQuality: {
    readability: `MELHORE A LEGIBILIDADE:
- Frases atuais: {avgWordsPerSentence} palavras (ideal: <=20)
- Voz passiva: {passiveVoicePercent}% (ideal: <10%)
- Flesch Score: {fleschScore} (ideal: 60+)
- Acao: Reescreva frases longas, use voz ativa, adicione transicoes`,

    contentStructure: `MELHORE A ESTRUTURA:
- Verifique se ha introducao adequada (30-100 palavras resumindo o tema)
- Adicione subtitulos (H2/H3) a cada 300-400 palavras
- Quebre paragrafos longos (maximo 4 frases cada)
- Considere adicionar listas ou blockquotes para destacar informacoes`,

    wordCountDepth: `AJUSTE O TAMANHO DO CONTEUDO:
- Palavras atuais: {wordCount}
- O conteudo precisa ter profundidade adequada ao tipo de materia
- Adicione contexto, dados ou exemplos se muito curto
- Remova redundancias se muito longo`
  },

  onPageOptimization: {
    titleOptimization: `OTIMIZE O TITULO:
- Tamanho atual: {currentLength} caracteres (ideal: 50-60)
- Coloque a palavra-chave principal nas primeiras 3 palavras
- Adicione uma power word (exclusivo, revela, urgente, novo)
- Considere incluir um numero se relevante`,

    metaDescription: `OTIMIZE A LINHA FINA:
- Tamanho atual: {currentLength} caracteres (ideal: 120-155)
- Inclua a palavra-chave principal
- Adicione um CTA (saiba mais, veja, confira, entenda)
- Diferencie do titulo - complemente, nao repita
- Termine com pontuacao adequada`,

    keywordStrategy: `MELHORE O USO DE PALAVRAS-CHAVE:
- A palavra-chave principal deve aparecer no primeiro paragrafo
- Densidade ideal: 1-2.5% do texto
- Use variacoes semanticas (sinonimos, termos relacionados)
- Evite keyword stuffing - mantenha natural`,

    urlSlug: `OTIMIZE O SLUG:
- Maximo 60 caracteres
- Inclua a palavra-chave principal
- Remova stop words (de, da, do, para, em)
- Use apenas letras minusculas e hifens`
  },

  eeatSignals: {
    experience: `ADICIONE SINAIS DE EXPERIENCIA:
- Use expressoes de apuracao: "segundo apuracao", "a reportagem descobriu", "em entrevista exclusiva"
- Cite detalhes especificos que mostrem investigacao propria
- Adicione testemunhos ou entrevistas quando aplicavel
- Inclua observacoes de campo se for reportagem presencial`,

    expertise: `DEMONSTRE EXPERTISE:
- Cite pelo menos 2 fontes com nome completo
- Inclua citacoes de especialistas reconhecidos na area
- Use terminologia tecnica correta quando apropriado
- Considere adicionar byline do autor se disponivel`,

    authority: `AUMENTE A AUTORIDADE:
- Cite pelo menos 1 fonte oficial (governo, policia, tribunais, ministerios)
- Adicione dados de orgaos reconhecidos (IBGE, Banco Central, etc.)
- Nomeie instituicoes (universidades, fundacoes, associacoes)
- Inclua links para fontes autoritativas quando possivel`,

    trust: `MELHORE A CONFIABILIDADE:
- Fundamente afirmacoes com dados verificaveis (numeros, datas, valores)
- Apresente diferentes perspectivas quando o tema for controverso
- Nomeie suas fontes - evite "fontes anonimas" quando possivel
- Evite linguagem sensacionalista ou clickbait`
  },

  technicalExcellence: {
    // Note: internalLinks template removed - user doesn't have article database
    // so internal links would be useless placeholders

    externalLinks: `ADICIONE REFERENCIAS EXTERNAS:
- Inclua links para fontes oficiais (.gov, .edu, .org)
- Cite estudos, relatorios ou documentos originais
- Prefira fontes autoritativas e reconhecidas
- Os links devem agregar valor e credibilidade ao conteudo
- Use textos descritivos nos links (evite "clique aqui")`,

    mediaOptimization: `OTIMIZE AS IMAGENS:
- Adicione pelo menos 1 imagem relevante ao conteudo
- Use alt text descritivo (minimo 3 palavras)
- Inclua a palavra-chave no alt text quando natural
- Adicione legendas (captions) para contextualizar`
  },

  aiSerpOptimization: {
    featuredSnippet: `OTIMIZE PARA FEATURED SNIPPET:
- Primeiro paragrafo deve ter 40-60 palavras respondendo diretamente ao tema
- Atual: {firstParaWords} palavras
- Responda: quem, o que, quando, onde, por que
- Inclua uma lista ou tabela se o tema permitir
- Use subtitulos com perguntas que o leitor faria`,

    aiOverview: `OTIMIZE PARA AI OVERVIEW:
- Estruture com subtitulos claros e logicos
- Mantenha paragrafos curtos (3-4 frases)
- Inclua dados verificaveis (numeros, datas, valores)
- Evite sensacionalismo - use tom neutro e informativo
- Facilite o resumo: comece cada secao com o ponto principal`
  }
};

/**
 * Mode descriptions for UI
 */
export const OPTIMIZATION_MODES = {
  quick: {
    name: 'Otimizacao Rapida',
    description: 'Foca nas 3 melhorias de maior impacto',
    recommendationLimit: 3
  },
  complete: {
    name: 'Otimizacao Completa',
    description: 'Revisa todas as categorias com problemas',
    recommendationLimit: 5
  },
  focused: {
    name: 'Foco Especifico',
    description: 'Escolha areas especificas para melhorar',
    recommendationLimit: 3
  }
};

/**
 * Focus area options for focused optimization mode
 */
export const FOCUS_AREAS = [
  { key: 'readability', label: 'Legibilidade', category: 'contentQuality' },
  { key: 'eeat', label: 'E-E-A-T (Credibilidade)', category: 'eeatSignals' },
  { key: 'snippet', label: 'Featured Snippet', category: 'aiSerpOptimization' },
  { key: 'onPage', label: 'Titulo e Meta', category: 'onPageOptimization' }
];

/**
 * Score threshold messages
 */
export const SCORE_MESSAGES = {
  critical: {
    range: [0, 39],
    message: 'Precisa de melhorias significativas',
    color: 'error'
  },
  regular: {
    range: [40, 59],
    message: 'Tem potencial para melhorar',
    color: 'warning'
  },
  good: {
    range: [60, 79],
    message: 'Bom, com espaco para refinamento',
    color: 'warning'
  },
  excellent: {
    range: [80, 100],
    message: 'Excelente! Pequenos ajustes opcionais',
    color: 'success'
  }
};

export default {
  CATEGORY_NAMES,
  METRIC_NAMES,
  SEO_PROMPT_TEMPLATES,
  OPTIMIZATION_MODES,
  FOCUS_AREAS,
  SCORE_MESSAGES,
  SEO_SCORING_RULES,
  STOP_WORDS
};
