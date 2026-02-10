/**
 * SEO Constants - Power words, patterns, and thresholds for SEO analysis
 *
 * Based on Google's 2025-2026 ranking factors, E-E-A-T principles,
 * and AI Overview optimization guidelines.
 */

// ═══════════════════════════════════════════════════════════════
// ARTICLE TYPE THRESHOLDS
// ═══════════════════════════════════════════════════════════════

export const ARTICLE_TYPE_THRESHOLDS = {
  noticia: {
    name: 'Notícia',
    min: 300,
    ideal: 500,
    max: 800,
    description: 'Informação factual e objetiva'
  },
  reportagem: {
    name: 'Reportagem',
    min: 800,
    ideal: 1500,
    max: 3000,
    description: 'Cobertura aprofundada com contexto'
  },
  analise: {
    name: 'Análise',
    min: 1000,
    ideal: 2000,
    max: 4000,
    description: 'Interpretação técnica e especializada'
  },
  opiniao: {
    name: 'Opinião',
    min: 400,
    ideal: 700,
    max: 1200,
    description: 'Artigo de opinião ou editorial'
  },
  default: {
    name: 'Artigo',
    min: 400,
    ideal: 800,
    max: 2000,
    description: 'Tipo de artigo geral'
  }
};

// ═══════════════════════════════════════════════════════════════
// POWER WORDS (Portuguese)
// ═══════════════════════════════════════════════════════════════

export const POWER_WORDS = {
  urgency: [
    'agora', 'urgente', 'última hora', 'breaking', 'ao vivo',
    'imediato', 'hoje', 'acaba de', 'neste momento', 'atualizado',
    'em tempo real', 'minuto a minuto', 'plantão'
  ],
  exclusivity: [
    'exclusivo', 'revelado', 'inédito', 'bastidores', 'vazou',
    'em primeira mão', 'antecipado', 'só aqui', 'nunca visto',
    'informações exclusivas', 'apuração própria', 'com exclusividade'
  ],
  impact: [
    'chocante', 'surpreendente', 'histórico', 'recorde', 'impressionante',
    'bombástico', 'polêmico', 'emocionante', 'inacreditável', 'épico',
    'marcante', 'decisivo', 'transformador', 'revolucionário'
  ],
  utility: [
    'como', 'guia', 'dicas', 'passo a passo', 'tutorial',
    'aprenda', 'descubra', 'saiba', 'entenda', 'conheça',
    'veja como', 'o que fazer', 'por que', 'quando', 'onde'
  ],
  numbers: [
    'motivos', 'razões', 'fatos', 'dicas', 'passos',
    'maneiras', 'formas', 'segredos', 'erros', 'verdades'
  ],
  emotional: [
    'emocionante', 'comovente', 'incrível', 'fantástico', 'terrível',
    'assustador', 'alegre', 'triste', 'revoltante', 'inspirador',
    'esperança', 'medo', 'alegria', 'tristeza', 'raiva'
  ]
};

// Flatten all power words for easy checking
export const ALL_POWER_WORDS = [
  ...POWER_WORDS.urgency,
  ...POWER_WORDS.exclusivity,
  ...POWER_WORDS.impact,
  ...POWER_WORDS.utility,
  ...POWER_WORDS.numbers,
  ...POWER_WORDS.emotional
];

// ═══════════════════════════════════════════════════════════════
// E-E-A-T DETECTION PATTERNS
// ═══════════════════════════════════════════════════════════════

export const EXPERIENCE_PATTERNS = [
  /segundo\s+(fontes|apuração|informações|levantamento)/i,
  /em\s+entrevista\s+(exclusiva|ao|à|para)/i,
  /presenciou|testemunhou|acompanhou|esteve\s+presente/i,
  /nossa\s+reportagem|nossa\s+equipe|nosso\s+repórter/i,
  /apuração\s+(exclusiva|própria|do|da)/i,
  /reportagem\s+(exclusiva|especial|investigativa)/i,
  /a\s+reportagem\s+(apurou|descobriu|revelou)/i,
  /o\s+repórter\s+(esteve|foi|conversou|entrevistou)/i,
  /durante\s+(visita|viagem|cobertura)/i,
  /no\s+local|in\s+loco|presencialmente/i
];

export const EXPERTISE_PATTERNS = {
  sourceCitation: [
    /segundo\s+[A-Z][a-záéíóúâêîôûãõç]+/,
    /de\s+acordo\s+com\s+/i,
    /informou|afirmou|declarou|disse|explicou|destacou/i,
    /dados\s+d[oa]\s+/i,
    /pesquisa\s+(da|do|de)\s+/i,
    /estudo\s+(da|do|de|publicado)/i,
    /relatório\s+(da|do|de|divulgado)/i,
    /conforme\s+(dados|informações|levantamento)/i
  ],
  expertQuote: [
    /especialista|expert|analista|professor|pesquisador/i,
    /economista|advogado|médico|engenheiro|cientista/i,
    /diretor|presidente|secretário|ministro|coordenador/i,
    /doutor|mestre|PhD|pós-graduado/i
  ]
};

export const AUTHORITY_SOURCES = {
  government: [
    'governo', 'ministério', 'prefeitura', 'tribunal', 'senado',
    'câmara', 'congresso', 'presidência', 'secretaria', 'autarquia'
  ],
  official: [
    'polícia', 'bombeiros', 'defesa civil', 'exército', 'marinha',
    'aeronáutica', 'receita federal', 'banco central', 'cvm'
  ],
  institutions: [
    'ibge', 'inpe', 'anvisa', 'anatel', 'anac', 'ibama', 'ipea',
    'fgv', 'usp', 'unicamp', 'ufrj', 'cnpq', 'capes', 'inep'
  ],
  sports: [
    'cbf', 'conmebol', 'fifa', 'cob', 'coi', 'confederação',
    'federação', 'liga', 'associação'
  ],
  international: [
    'onu', 'oms', 'omc', 'fmi', 'bird', 'unesco', 'unicef',
    'banco mundial', 'opep', 'otan', 'mercosul'
  ]
};

// All authority sources flattened
export const ALL_AUTHORITY_SOURCES = [
  ...AUTHORITY_SOURCES.government,
  ...AUTHORITY_SOURCES.official,
  ...AUTHORITY_SOURCES.institutions,
  ...AUTHORITY_SOURCES.sports,
  ...AUTHORITY_SOURCES.international
];

export const TRUST_SIGNALS = {
  multipleViewpoints: [
    /por\s+outro\s+lado/i,
    /em\s+contrapartida/i,
    /já\s+a\s+oposição/i,
    /críticos\s+(apontam|afirmam|dizem)/i,
    /defensores\s+(destacam|argumentam)/i,
    /enquanto\s+(uns|alguns|outros)/i,
    /há\s+quem\s+(defenda|critique|acredite)/i,
    /pontos\s+de\s+vista/i,
    /ambos\s+os\s+lados/i
  ],
  factualClaims: [
    /dados\s+(mostram|indicam|revelam|apontam)/i,
    /números\s+(comprovam|demonstram)/i,
    /estatísticas\s+(indicam|mostram)/i,
    /segundo\s+(levantamento|pesquisa|estudo)/i,
    /de\s+acordo\s+com\s+(os\s+)?dados/i
  ]
};

// ═══════════════════════════════════════════════════════════════
// AUTHORITY DOMAINS FOR EXTERNAL LINKS
// ═══════════════════════════════════════════════════════════════

export const AUTHORITY_DOMAINS = {
  government: [
    'gov.br', 'gov.com', 'gov.org',
    'senado.leg.br', 'camara.leg.br', 'planalto.gov.br',
    'stf.jus.br', 'stj.jus.br', 'tse.jus.br'
  ],
  education: [
    'edu.br', 'edu.com',
    'usp.br', 'unicamp.br', 'ufrj.br', 'ufmg.br'
  ],
  organizations: [
    'org.br', 'org.com',
    'who.int', 'un.org', 'worldbank.org'
  ],
  news: [
    'reuters.com', 'apnews.com', 'afp.com', 'bbc.com', 'cnn.com',
    'globo.com', 'uol.com.br', 'folha.uol.com.br', 'estadao.com.br',
    'g1.globo.com', 'valor.globo.com', 'infomoney.com.br'
  ],
  research: [
    'scielo.br', 'scholar.google.com', 'pubmed.gov',
    'nature.com', 'science.org', 'ieee.org'
  ]
};

// All authority domains flattened
export const ALL_AUTHORITY_DOMAINS = [
  ...AUTHORITY_DOMAINS.government,
  ...AUTHORITY_DOMAINS.education,
  ...AUTHORITY_DOMAINS.organizations,
  ...AUTHORITY_DOMAINS.news,
  ...AUTHORITY_DOMAINS.research
];

// ═══════════════════════════════════════════════════════════════
// TRANSITION WORDS (Portuguese)
// ═══════════════════════════════════════════════════════════════

export const TRANSITION_WORDS = {
  addition: [
    'além disso', 'também', 'ainda', 'ademais', 'inclusive',
    'igualmente', 'da mesma forma', 'não só', 'bem como',
    'assim como', 'do mesmo modo', 'por sua vez'
  ],
  contrast: [
    'porém', 'contudo', 'entretanto', 'no entanto', 'todavia',
    'mas', 'embora', 'apesar de', 'por outro lado', 'em contrapartida',
    'ao contrário', 'não obstante', 'pelo contrário'
  ],
  cause: [
    'porque', 'pois', 'já que', 'visto que', 'uma vez que',
    'dado que', 'por causa de', 'devido a', 'em razão de',
    'em virtude de', 'graças a', 'por conta de'
  ],
  consequence: [
    'portanto', 'assim', 'logo', 'então', 'por isso',
    'consequentemente', 'como resultado', 'dessa forma',
    'desse modo', 'por conseguinte', 'sendo assim'
  ],
  time: [
    'primeiro', 'depois', 'em seguida', 'posteriormente',
    'anteriormente', 'finalmente', 'por fim', 'enquanto isso',
    'simultaneamente', 'ao mesmo tempo', 'desde então'
  ],
  example: [
    'por exemplo', 'como', 'tal como', 'a exemplo de',
    'exemplificando', 'ilustrando', 'nesse sentido',
    'em outras palavras', 'ou seja', 'isto é'
  ],
  conclusion: [
    'em suma', 'em resumo', 'em síntese', 'concluindo',
    'para concluir', 'em conclusão', 'por fim',
    'resumindo', 'sintetizando', 'em última análise'
  ]
};

// All transition words flattened
export const ALL_TRANSITION_WORDS = [
  ...TRANSITION_WORDS.addition,
  ...TRANSITION_WORDS.contrast,
  ...TRANSITION_WORDS.cause,
  ...TRANSITION_WORDS.consequence,
  ...TRANSITION_WORDS.time,
  ...TRANSITION_WORDS.example,
  ...TRANSITION_WORDS.conclusion
];

// ═══════════════════════════════════════════════════════════════
// STOP WORDS (Portuguese) - for slug optimization
// ═══════════════════════════════════════════════════════════════

export const STOP_WORDS = [
  'a', 'o', 'e', 'é', 'de', 'do', 'da', 'dos', 'das',
  'em', 'no', 'na', 'nos', 'nas', 'um', 'uma', 'uns', 'umas',
  'para', 'por', 'com', 'sem', 'sob', 'sobre', 'entre',
  'que', 'qual', 'quais', 'quando', 'como', 'onde',
  'se', 'mas', 'ou', 'nem', 'não', 'mais', 'menos',
  'muito', 'pouco', 'bem', 'mal', 'já', 'ainda',
  'seu', 'sua', 'seus', 'suas', 'esse', 'essa', 'esses', 'essas',
  'este', 'esta', 'estes', 'estas', 'aquele', 'aquela',
  'ele', 'ela', 'eles', 'elas', 'nós', 'vocês',
  'ao', 'aos', 'à', 'às', 'pelo', 'pela', 'pelos', 'pelas'
];

// ═══════════════════════════════════════════════════════════════
// SCORING THRESHOLDS
// ═══════════════════════════════════════════════════════════════

export const SCORING_THRESHOLDS = {
  title: {
    min: 40,
    idealMin: 50,
    idealMax: 60,
    max: 70
  },
  metaDescription: {
    min: 120,
    idealMin: 150,
    idealMax: 160,
    max: 180
  },
  slug: {
    maxLength: 60,
    idealMaxLength: 50
  },
  readability: {
    excellent: 80,
    good: 60,
    moderate: 40,
    difficult: 20
  },
  keywordDensity: {
    min: 1,
    idealMin: 1.5,
    idealMax: 2.5,
    max: 3
  },
  paragraphLength: {
    idealMax: 150, // words
    maxSentences: 4
  },
  sentenceLength: {
    ideal: 20, // words
    max: 25
  },
  featuredSnippet: {
    answerMinWords: 40,
    answerMaxWords: 60
  }
};

// ═══════════════════════════════════════════════════════════════
// SCORE LABELS AND COLORS
// ═══════════════════════════════════════════════════════════════

export const SCORE_LABELS = {
  excellent: { min: 80, label: 'Excelente', color: '#10B981' },
  good: { min: 60, label: 'Bom', color: '#F59E0B' },
  regular: { min: 40, label: 'Regular', color: '#F59E0B' },
  critical: { min: 0, label: 'Crítico', color: '#EF4444' }
};

export const getScoreLabel = (score) => {
  if (score >= 80) return SCORE_LABELS.excellent;
  if (score >= 60) return SCORE_LABELS.good;
  if (score >= 40) return SCORE_LABELS.regular;
  return SCORE_LABELS.critical;
};

// ═══════════════════════════════════════════════════════════════
// CATEGORY WEIGHTS (Total = 100 points)
// ═══════════════════════════════════════════════════════════════

export const CATEGORY_WEIGHTS = {
  contentQuality: {
    total: 30,
    metrics: {
      wordCountDepth: 10,
      contentStructure: 10,
      readability: 10
    }
  },
  onPageOptimization: {
    total: 25,
    metrics: {
      titleOptimization: 8,
      metaDescription: 7,
      keywordStrategy: 5,
      urlSlug: 5
    }
  },
  eeatSignals: {
    total: 20,
    metrics: {
      experience: 5,
      expertise: 5,
      authority: 5,
      trust: 5
    }
  },
  technicalExcellence: {
    total: 5,
    metrics: {
      internalLinks: 0,       // Manual action only - not scored (feature not available)
      externalLinks: 5,
      mediaOptimization: 0    // Manual action only - not scored (feature not available)
    }
  },
  aiSerpOptimization: {
    total: 10,
    metrics: {
      featuredSnippet: 5,
      aiOverview: 5
    }
  }
};

// ═══════════════════════════════════════════════════════════════
// LSI KEYWORD ASSOCIATIONS (Portuguese - Sports/News focused)
// ═══════════════════════════════════════════════════════════════

export const LSI_ASSOCIATIONS = {
  // Football teams
  corinthians: ['timão', 'parque são jorge', 'fiel', 'neo química arena', 'alvinegro', 'coringão', 'sccp'],
  palmeiras: ['verdão', 'alviverde', 'allianz parque', 'porco', 'sep', 'palestra'],
  flamengo: ['mengão', 'rubro-negro', 'maracanã', 'nação', 'fla', 'crf'],
  saopaulo: ['tricolor', 'morumbi', 'spfc', 'soberano', 'são paulo'],
  santos: ['peixe', 'vila belmiro', 'alvinegro praiano', 'sfc'],

  // General football
  futebol: ['campeonato', 'partida', 'jogo', 'gol', 'vitória', 'derrota', 'empate', 'time', 'equipe'],
  brasileirao: ['série a', 'campeonato brasileiro', 'pontos', 'tabela', 'rodada', 'classificação'],
  libertadores: ['conmebol', 'sul-americana', 'copa', 'mata-mata', 'oitavas', 'quartas', 'semifinal', 'final'],

  // Economy
  economia: ['mercado', 'inflação', 'juros', 'dólar', 'bolsa', 'investimento', 'pib', 'crescimento'],
  inflacao: ['ipca', 'igpm', 'preços', 'custo de vida', 'poder de compra', 'reajuste'],
  selic: ['taxa de juros', 'copom', 'banco central', 'política monetária', 'crédito'],

  // Politics
  eleicoes: ['voto', 'urna', 'candidato', 'campanha', 'tse', 'segundo turno', 'eleitorado'],
  governo: ['presidente', 'ministro', 'planalto', 'brasília', 'congresso', 'senado', 'câmara'],

  // Health
  saude: ['hospital', 'médico', 'tratamento', 'vacina', 'sus', 'doença', 'sintomas'],
  covid: ['coronavirus', 'pandemia', 'vacina', 'variante', 'casos', 'óbitos', 'isolamento'],

  // Technology
  tecnologia: ['inteligência artificial', 'ia', 'startup', 'inovação', 'digital', 'app', 'software'],
  ia: ['inteligência artificial', 'machine learning', 'chatgpt', 'automação', 'algoritmo']
};

// ═══════════════════════════════════════════════════════════════
// CLICKBAIT PATTERNS (to avoid)
// ═══════════════════════════════════════════════════════════════

export const CLICKBAIT_PATTERNS = [
  /você\s+não\s+vai\s+acreditar/i,
  /ninguém\s+esperava/i,
  /o\s+que\s+aconteceu\s+depois/i,
  /chocante!\s*/i,
  /bombástico!\s*/i,
  /urgente!\s*/i,
  /inacreditável!\s*/i,
  /veja\s+o\s+que\s+aconteceu/i,
  /isso\s+vai\s+te\s+surpreender/i,
  /descubra\s+o\s+segredo/i,
  /a\s+verdade\s+que\s+ninguém\s+conta/i
];

// ═══════════════════════════════════════════════════════════════
// REPORTING VERBS (Portuguese)
// ═══════════════════════════════════════════════════════════════

export const REPORTING_VERBS = [
  'disse', 'afirmou', 'declarou', 'informou', 'explicou',
  'destacou', 'ressaltou', 'pontuou', 'comentou', 'revelou',
  'anunciou', 'confirmou', 'negou', 'alertou', 'apontou',
  'mencionou', 'relatou', 'contou', 'acrescentou', 'completou',
  'finalizou', 'concluiu', 'argumentou', 'defendeu', 'criticou'
];

// ═══════════════════════════════════════════════════════════════
// HEADING PATTERNS
// ═══════════════════════════════════════════════════════════════

export const HEADING_PATTERNS = {
  h2: /<h2[^>]*>.*?<\/h2>/gi,
  h3: /<h3[^>]*>.*?<\/h3>/gi,
  h4: /<h4[^>]*>.*?<\/h4>/gi,
  markdown: {
    h2: /^##\s+.+$/gm,
    h3: /^###\s+.+$/gm,
    h4: /^####\s+.+$/gm
  }
};

// ═══════════════════════════════════════════════════════════════
// CONTENT STRUCTURE PATTERNS
// ═══════════════════════════════════════════════════════════════

export const STRUCTURE_PATTERNS = {
  bulletList: /<ul[^>]*>.*?<\/ul>/gis,
  numberedList: /<ol[^>]*>.*?<\/ol>/gis,
  blockquote: /<blockquote[^>]*>.*?<\/blockquote>/gis,
  table: /<table[^>]*>.*?<\/table>/gis,
  image: /<img[^>]*>/gi,
  link: /<a[^>]*href=["']([^"']+)["'][^>]*>/gi,
  paragraph: /<p[^>]*>.*?<\/p>/gis,
  markdown: {
    bulletList: /^[\*\-]\s+.+$/gm,
    numberedList: /^\d+\.\s+.+$/gm,
    blockquote: /^>\s+.+$/gm,
    image: /!\[.*?\]\(.*?\)/g,
    link: /\[.*?\]\(.*?\)/g
  }
};

export default {
  ARTICLE_TYPE_THRESHOLDS,
  POWER_WORDS,
  ALL_POWER_WORDS,
  EXPERIENCE_PATTERNS,
  EXPERTISE_PATTERNS,
  AUTHORITY_SOURCES,
  ALL_AUTHORITY_SOURCES,
  TRUST_SIGNALS,
  AUTHORITY_DOMAINS,
  ALL_AUTHORITY_DOMAINS,
  TRANSITION_WORDS,
  ALL_TRANSITION_WORDS,
  STOP_WORDS,
  SCORING_THRESHOLDS,
  SCORE_LABELS,
  getScoreLabel,
  CATEGORY_WEIGHTS,
  LSI_ASSOCIATIONS,
  CLICKBAIT_PATTERNS,
  REPORTING_VERBS,
  HEADING_PATTERNS,
  STRUCTURE_PATTERNS
};
