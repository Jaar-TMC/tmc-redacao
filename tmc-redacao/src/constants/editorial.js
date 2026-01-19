/**
 * TMC Editorial Constants
 *
 * Category-based editorial guidelines for the TMC Redação tool.
 * Based on instrucoesia.md - TMC's real editorial guidelines.
 */

import {
  Trophy,
  Film,
  Landmark,
  TrendingUp,
  Newspaper
} from 'lucide-react';

/**
 * The 5 TMC Editorial Categories
 * Each category has distinct voice, rules, and available tones.
 */
export const CATEGORIAS_EDITORIAIS = {
  esportes: {
    id: 'esportes',
    name: 'Esportes',
    icon: Trophy,
    description: 'Cobertura esportiva com paixão e proximidade ao torcedor',
    reference: 'CazéTV',
    allowsOpinion: true,
    defaultTone: 'informal',
    availableTones: ['informal', 'emocional', 'sobrio'],
    dos: [
      'Use gírias esportivas moderadamente',
      'Expressões como "jogo pegado", "clima de decisão"',
      'Humor em contextos apropriados',
      'Tom emocionado para grandes momentos',
      'Explore bastidores e memes de clubes'
    ],
    donts: [
      'Discurso machista',
      'Humilhar atletas ou torcedores',
      'Body shaming, xenofobia, homofobia',
      'Incitar rivalidade violenta',
      'Piadas sobre acidentes ou violência'
    ],
    color: 'emerald',
    colorClasses: {
      bg: 'bg-emerald-50',
      border: 'border-emerald-500',
      text: 'text-emerald-700',
      icon: 'text-emerald-600'
    }
  },
  entretenimento: {
    id: 'entretenimento',
    name: 'Entretenimento',
    icon: Film,
    description: 'Cobertura leve, pop e divertida de cultura e celebridades',
    reference: 'The News + Pop',
    allowsOpinion: false,
    defaultTone: 'informal',
    availableTones: ['informal', 'leve', 'criativo'],
    dos: [
      'Use tom leve e criativo',
      'Referências pop (filmes, séries, músicas)',
      'Trocadilhos bem-humorados',
      'Linguagem conversacional e próxima'
    ],
    donts: [
      'Body shaming ou julgamento moral',
      'Expor dados íntimos não autorizados',
      'Fazer piada de questões sensíveis',
      'Fofoca tóxica ou invasiva'
    ],
    color: 'purple',
    colorClasses: {
      bg: 'bg-purple-50',
      border: 'border-purple-500',
      text: 'text-purple-700',
      icon: 'text-purple-600'
    }
  },
  politica: {
    id: 'politica',
    name: 'Política',
    icon: Landmark,
    description: 'Cobertura política sóbria, direta e didática',
    reference: 'Sóbrio/Didático',
    allowsOpinion: true,
    defaultTone: 'sobrio',
    availableTones: ['sobrio', 'didatico'],
    dos: [
      'Explique termos técnicos ("Em resumo...")',
      'Indique impacto na vida das pessoas',
      'Use perguntas-guia ("Por que isso importa?")',
      'Títulos diretos e sóbrios',
      'Sempre cite a fonte para denúncias'
    ],
    donts: [
      'Piadas, memes, trocadilhos, emojis',
      'Preferência partidária',
      'Adjetivos valorativos (exceto colunas)',
      'Linguagem informal'
    ],
    color: 'blue',
    colorClasses: {
      bg: 'bg-blue-50',
      border: 'border-blue-500',
      text: 'text-blue-700',
      icon: 'text-blue-600'
    }
  },
  economia: {
    id: 'economia',
    name: 'Economia',
    icon: TrendingUp,
    description: 'Cobertura econômica traduzida para o cotidiano',
    reference: 'Traduzir para cotidiano',
    allowsOpinion: true,
    defaultTone: 'didatico',
    availableTones: ['didatico', 'analitico'],
    dos: [
      'Traduza para o cotidiano ("Com juros mais altos...")',
      'Use exemplos concretos (salário, aluguel)',
      'Traga contexto e tendências',
      'Explique TODAS as siglas (Selic, CDI, PIB)',
      'Cite fontes confiáveis'
    ],
    donts: [
      'Prometer resultados de investimento',
      'Humor sobre crise ou desemprego',
      'Siglas sem explicação',
      'Tom de pânico ou sensacionalismo'
    ],
    color: 'amber',
    colorClasses: {
      bg: 'bg-amber-50',
      border: 'border-amber-500',
      text: 'text-amber-700',
      icon: 'text-amber-600'
    }
  },
  geral: {
    id: 'geral',
    name: 'Geral/Variedades',
    icon: Newspaper,
    description: 'Cobertura de variedades com tom conversacional',
    reference: 'Conversacional',
    allowsOpinion: false,
    defaultTone: 'conversacional',
    availableTones: ['conversacional', 'informativo'],
    dos: [
      'Tom conversacional e próximo',
      'Perguntas retóricas para engajar',
      'Humor em temas neutros',
      'SEMPRE cite fontes em saúde/ciência'
    ],
    donts: [
      'Humor com tragédia ou violência',
      'Sensacionalismo em crimes/acidentes',
      'Exposição desnecessária de vítimas',
      'Dicas de saúde sem fonte médica'
    ],
    color: 'gray',
    colorClasses: {
      bg: 'bg-gray-50',
      border: 'border-gray-500',
      text: 'text-gray-700',
      icon: 'text-gray-600'
    }
  }
};

/**
 * Tones available per category
 * Each tone has a description optimized for the category context.
 */
export const TONS_POR_CATEGORIA = {
  esportes: {
    informal: {
      id: 'informal',
      label: 'Informal',
      description: 'Linguagem descontraída e próxima do torcedor, com gírias moderadas.'
    },
    emocional: {
      id: 'emocional',
      label: 'Emocional',
      description: 'Tom emocionado e vibrante, ideal para grandes jogos e momentos históricos.'
    },
    sobrio: {
      id: 'sobrio',
      label: 'Sóbrio',
      description: 'Tom sério para coberturas de acidentes, violência ou temas sensíveis.'
    }
  },
  entretenimento: {
    informal: {
      id: 'informal',
      label: 'Informal',
      description: 'Leve e conversacional, como uma conversa entre amigos.'
    },
    leve: {
      id: 'leve',
      label: 'Leve',
      description: 'Descontraído e divertido, focando no lado positivo e interessante.'
    },
    criativo: {
      id: 'criativo',
      label: 'Criativo',
      description: 'Mais elaborado, com referências pop e trocadilhos inteligentes.'
    }
  },
  politica: {
    sobrio: {
      id: 'sobrio',
      label: 'Sóbrio',
      description: 'Direto, sério e factual. Ideal para hard news política.'
    },
    didatico: {
      id: 'didatico',
      label: 'Didático',
      description: 'Explicativo, focando em contextualizar e traduzir termos técnicos.'
    }
  },
  economia: {
    didatico: {
      id: 'didatico',
      label: 'Didático',
      description: 'Foco em explicar e traduzir para o cotidiano do cidadão.'
    },
    analitico: {
      id: 'analitico',
      label: 'Analítico',
      description: 'Mais aprofundado, com análise de cenários e tendências.'
    }
  },
  geral: {
    conversacional: {
      id: 'conversacional',
      label: 'Conversacional',
      description: 'Próximo e engajador, como uma conversa com o leitor.'
    },
    informativo: {
      id: 'informativo',
      label: 'Informativo',
      description: 'Mais direto e objetivo, focando na informação útil.'
    }
  }
};

/**
 * Get available tones for a category
 * @param {string} categoriaId - Category ID
 * @returns {Array} Array of tone objects
 */
export function getTonesForCategory(categoriaId) {
  const tones = TONS_POR_CATEGORIA[categoriaId];
  if (!tones) return [];
  return Object.values(tones);
}

/**
 * Get default tone for a category
 * @param {string} categoriaId - Category ID
 * @returns {string} Default tone ID
 */
export function getDefaultToneForCategory(categoriaId) {
  const categoria = CATEGORIAS_EDITORIAIS[categoriaId];
  return categoria?.defaultTone || 'formal';
}

/**
 * Check if a category allows opinion mode
 * @param {string} categoriaId - Category ID
 * @returns {boolean} Whether opinion mode is allowed
 */
export function categoryAllowsOpinion(categoriaId) {
  const categoria = CATEGORIAS_EDITORIAIS[categoriaId];
  return categoria?.allowsOpinion || false;
}

/**
 * Get all categories as an array (for iteration)
 */
export const CATEGORIAS_ARRAY = Object.values(CATEGORIAS_EDITORIAIS);

/**
 * Article type options (unchanged from original)
 */
export const TIPO_MATERIA_OPTIONS = [
  { id: 'destaque', label: 'Destaque Principal', description: 'Matéria principal da home' },
  { id: 'principal-secao', label: 'Principal da Seção', description: 'Destaque dentro de uma editoria' },
  { id: 'secundaria', label: 'Secundária da Seção', description: 'Matéria de apoio na editoria' },
  { id: 'coluna', label: 'Coluna', description: 'Texto opinativo ou de colunista' },
  { id: 'mais-lidas', label: 'Mais Lidas', description: 'Conteúdo para seção popular' },
  { id: 'original', label: 'Conteúdo Original', description: 'Reportagem exclusiva' },
  { id: 'servico', label: 'Serviço', description: 'Informação útil ao leitor' }
];

/**
 * Credit options for source attribution
 */
export const CREDITO_OPTIONS = [
  { id: 'agencia-brasil', label: 'Agência Brasil' },
  { id: 'reuters', label: 'Reuters' },
  { id: 'afp', label: 'AFP' },
  { id: 'assessoria', label: 'Assessoria de Imprensa' },
  { id: 'outro', label: 'Outro...' }
];
