/**
 * SEO Prompt Generator - Generates intelligent prompts for AI optimization
 *
 * This utility analyzes SEO data and generates contextual, data-driven prompts
 * to help the AI chat make targeted article improvements.
 *
 * V2: Enhanced with exact scoring rules to maximize AI optimization effectiveness.
 */

import {
  SEO_PROMPT_TEMPLATES,
  CATEGORY_NAMES,
  METRIC_NAMES,
  SEO_SCORING_RULES,
  STOP_WORDS
} from '../constants/seoPromptTemplates';

/**
 * Extract primary keyword from title, content, and tags
 * @param {string} title - Article title
 * @param {string} content - Article content
 * @param {Array} tags - Article tags
 * @returns {string} - Primary keyword
 */
export const extractPrimaryKeyword = (title = '', content = '', tags = []) => {
  // 1. Check tags first (user-defined intent)
  if (tags && tags.length > 0) {
    return tags[0].toLowerCase().trim();
  }

  // 2. Extract significant words from title
  const normalizedTitle = title.toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // Remove accents
    .replace(/[^a-z0-9\s]/g, ' ');

  const titleWords = normalizedTitle
    .split(/\s+/)
    .filter(w => w.length > 3 && !STOP_WORDS.includes(w));

  if (titleWords.length === 0) {
    return '';
  }

  // 3. Count frequency in content for each title word
  const normalizedContent = content.toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

  const wordFreq = {};
  titleWords.forEach(word => {
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    const matches = normalizedContent.match(regex);
    wordFreq[word] = matches ? matches.length : 0;
  });

  // Return most frequent word from title that appears in content
  const sortedWords = Object.entries(wordFreq)
    .sort((a, b) => b[1] - a[1]);

  // Prefer words that appear at least once in content
  const wordInContent = sortedWords.find(([, count]) => count > 0);
  if (wordInContent) {
    return wordInContent[0];
  }

  // Fallback to first significant word in title
  return titleWords[0] || '';
};

/**
 * Calculate AI-optimizable vs manual-only potential improvement
 * @param {Object} categories - Categories from SEO analysis
 * @returns {Object} - { aiPotential, manualPotential, total, aiMetrics, manualMetrics }
 */
export const calculateSplitPotential = (categories) => {
  let aiPotential = 0;
  let manualPotential = 0;
  const aiMetrics = [];
  const manualMetrics = [];

  Object.entries(categories).forEach(([categoryKey, category]) => {
    Object.entries(category.metrics || {}).forEach(([metricKey, metric]) => {
      const available = metric.maxScore - metric.score;

      if (available <= 0) return;

      if (SEO_SCORING_RULES.aiOptimizableMetrics.includes(metricKey)) {
        aiPotential += available;
        aiMetrics.push({
          category: categoryKey,
          metric: metricKey,
          name: METRIC_NAMES[metricKey] || metricKey,
          points: available
        });
      } else if (SEO_SCORING_RULES.manualOnlyMetrics.includes(metricKey)) {
        manualPotential += available;
        manualMetrics.push({
          category: categoryKey,
          metric: metricKey,
          name: METRIC_NAMES[metricKey] || metricKey,
          points: available
        });
      }
    });
  });

  return {
    aiPotential,
    manualPotential,
    total: aiPotential + manualPotential,
    aiMetrics: aiMetrics.sort((a, b) => b.points - a.points),
    manualMetrics: manualMetrics.sort((a, b) => b.points - a.points)
  };
};

/**
 * Generate deficit analysis showing exactly what's wrong with current content
 * @param {Object} categories - Categories from SEO analysis
 * @returns {Array} - List of deficit strings
 */
const generateDeficitAnalysis = (categories) => {
  const deficits = [];

  // Check linha fina (meta description)
  const metaDesc = categories.onPageOptimization?.metrics?.metaDescription;
  if (metaDesc?.details?.length?.value) {
    const len = metaDesc.details.length.value;
    if (len < 150) {
      deficits.push(`LINHA FINA: ${len} caracteres (PRECISA: 150-160) - ADICIONE ${150 - len} caracteres`);
    } else if (len > 160) {
      deficits.push(`LINHA FINA: ${len} caracteres (PRECISA: 150-160) - REMOVA ${len - 160} caracteres`);
    }
  }

  // Check title
  const title = categories.onPageOptimization?.metrics?.titleOptimization;
  if (title?.details?.length?.value) {
    const len = title.details.length.value;
    if (len < 50) {
      deficits.push(`TITULO: ${len} caracteres (PRECISA: 50-60) - ADICIONE ${50 - len} caracteres`);
    } else if (len > 60) {
      deficits.push(`TITULO: ${len} caracteres (PRECISA: 50-60) - REMOVA ${len - 60} caracteres`);
    }
  }

  // Check first paragraph for featured snippet
  const snippet = categories.aiSerpOptimization?.metrics?.featuredSnippet;
  if (snippet?.details?.directAnswer?.words) {
    const words = snippet.details.directAnswer.words;
    if (words < 40) {
      deficits.push(`PRIMEIRO PARAGRAFO: ${words} palavras (PRECISA: 40-60) - ADICIONE ${40 - words} palavras`);
    } else if (words > 60) {
      deficits.push(`PRIMEIRO PARAGRAFO: ${words} palavras (PRECISA: 40-60) - REMOVA ${words - 60} palavras`);
    }
  }

  return deficits;
};

/**
 * Generate the exact scoring rules section for the prompt
 * Enhanced with hard constraints, calibration examples, priority hierarchy, and validation
 * @param {string} primaryKeyword - The detected primary keyword
 * @param {Object} categories - Categories from SEO analysis for deficit analysis
 * @returns {string} - Scoring rules as prompt text
 */
const generateScoringRulesSection = (primaryKeyword, categories = {}) => {
  const rules = SEO_SCORING_RULES;

  // Get deficit analysis
  const deficits = generateDeficitAnalysis(categories);

  let prompt = `
## REGRAS DE PONTUACAO - REQUISITOS OBRIGATORIOS

### TITULO (ate 8 pts):

COMPRIMENTO OBRIGATORIO: EXATAMENTE ${rules.thresholds.title.minChars}-${rules.thresholds.title.maxChars} caracteres
- Se <${rules.thresholds.title.minChars}: FALHA - perdera 2 pontos
- Se >${rules.thresholds.title.maxChars}: FALHA - perdera 2 pontos
- Se ${rules.thresholds.title.minChars}-${rules.thresholds.title.maxChars}: SUCESSO - ganhara 2 pontos

ISTO E INEGOCIAVEL. Ajuste o texto ate que esteja no range correto.

Outros requisitos:
- Palavra-chave "${primaryKeyword || '[termo principal]'}" nas primeiras 3 palavras: +2 pts
- Power word (escolha uma: ${rules.powerWords.slice(0, 5).join(', ')}): +1 pt
- Numero no titulo quando relevante: +1 pt

### TITULO - EXEMPLOS DE CALIBRACAO:

EXEMPLO CORRETO (55 caracteres - SUCESSO):
"Imposto trabalhista: novas regras afetam 50 milhoes"
- Comprimento: 55 caracteres (entre 50-60) OK
- Palavra-chave no inicio: OK
- Numero: presente OK
- RESULTADO: 8/8 pontos

EXEMPLO INCORRETO (38 caracteres - FALHA):
"Novo imposto afeta trabalhadores"
- Comprimento: 38 caracteres (ABAIXO de 50 - faltam 12) FALHA
- RESULTADO: 4/8 pontos

### LINHA FINA (ate 7 pts):

COMPRIMENTO OBRIGATORIO: EXATAMENTE ${rules.thresholds.linhaFina.minChars}-${rules.thresholds.linhaFina.maxChars} caracteres
- Se <${rules.thresholds.linhaFina.minChars}: FALHA - perdera 2 pontos
- Se >${rules.thresholds.linhaFina.maxChars}: FALHA - perdera 2 pontos
- Se ${rules.thresholds.linhaFina.minChars}-${rules.thresholds.linhaFina.maxChars}: SUCESSO - ganhara 2 pontos

ISTO E INEGOCIAVEL. Ajuste o texto ate que esteja no range correto.

Outros requisitos:
- Incluir palavra-chave "${primaryKeyword || '[termo principal]'}": +2 pts
- CTA no final (use: ${rules.ctaWords.join(', ')}): +1 pt
- Texto diferente do titulo - complemente, nao repita: +1 pt

### LINHA FINA - EXEMPLOS DE CALIBRACAO:

EXEMPLO CORRETO (155 caracteres - SUCESSO):
"Descubra como o novo imposto trabalhista afeta sua renda em 2026. Entenda as mudancas legais, os impactos financeiros e as excecoes previstas. Confira o guia."
- Comprimento: 155 caracteres (entre 150-160) OK
- Palavra-chave: presente OK
- CTA ("Confira"): presente OK
- RESULTADO: 7/7 pontos

EXEMPLO INCORRETO (112 caracteres - FALHA):
"Novo imposto de 2026. Confira as mudancas nas regras tributarias para trabalhadores."
- Comprimento: 112 caracteres (ABAIXO de 150 - faltam 38) FALHA
- RESULTADO: 1/7 pontos

VOCE DEVE gerar como o EXEMPLO CORRETO. Se sua linha fina tiver menos de 150 caracteres, ADICIONE mais contexto ate atingir 150-160.

### PRIORIDADE DE REQUISITOS (quando houver conflito):

PRIORIDADE 1 (NUNCA viole - inegociavel):
1. Comprimento exato: Titulo 50-60 chars, Linha Fina 150-160 chars
2. Frase completa com pontuacao correta

PRIORIDADE 2 (Mantenha se possivel):
- Palavra-chave principal no inicio
- CTA (saiba mais, confira, veja, entenda)

PRIORIDADE 3 (Opcional se espaco permitir):
- Diferenciacao do titulo
- Power words adicionais

NUNCA sacrifique o comprimento correto pela perfeicao de outro requisito. Se precisar escolher, SEMPRE mantenha o comprimento no range.

### E-E-A-T - Use estas frases EXATAS para ganhar pontos:
EXPERIENCIA (ate 5 pts):
- Use: "${rules.authorityPatterns[0]}", "${rules.authorityPatterns[1]}", "${rules.authorityPatterns[6]}"
- Cite detalhes especificos que mostrem investigacao propria

EXPERTISE (ate 5 pts):
- Mencione especialistas: "${rules.expertKeywords.slice(0, 4).join('", "')}"
- Exemplo: "segundo [Nome], ${rules.expertKeywords[0]} em [area]..."

AUTORIDADE (ate 5 pts):
- Cite fontes oficiais: ${rules.officialSources.slice(0, 6).join(', ')}
- Exemplo: "de acordo com dados do ${rules.officialSources[4]}..." ou "conforme o ${rules.officialSources[1]}..."
- OBRIGATORIO: Use LINKS MARKDOWN para fontes oficiais:
  CORRETO: "conforme o [Ministerio da Agricultura](https://www.gov.br/agricultura)"
  INCORRETO: "conforme o Ministerio da Agricultura"

CONFIANCA (ate 5 pts):
- Fundamente com dados verificaveis (numeros, datas, valores exatos)
- Apresente multiplas perspectivas quando o tema permitir

### ESTRUTURA DO CONTEUDO:
- Primeiro paragrafo: ${rules.thresholds.firstParagraph.idealWords.min}-${rules.thresholds.firstParagraph.idealWords.max} palavras (para Featured Snippet)
- Subtitulos: Use ## (H2) SEM espaco antes - colado na margem esquerda
- Paragrafos: maximo ${rules.thresholds.paragraphs.maxSentences} frases cada
- Listas: Use - para cada item, um por linha

### LEGIBILIDADE:
- Frases: maximo ${rules.thresholds.sentences.maxWords} palavras em media
- Adicione transicoes entre paragrafos: "${rules.transitionWords.slice(0, 5).join('", "')}"
- Use VOZ ATIVA, nao passiva (ex: "O governo anunciou" em vez de "Foi anunciado pelo governo")
- Densidade da palavra-chave: ${rules.thresholds.keywordDensity.min}%-${rules.thresholds.keywordDensity.max}% do texto

### VALIDACAO OBRIGATORIA (Chain-of-Thought):

ANTES DE FINALIZAR, VALIDE CADA ITEM:

Para a LINHA FINA:
1. Conte os caracteres (incluindo espacos e pontuacao)
2. Esta entre 150-160? Se NAO, REESCREVA adicionando ou removendo palavras
3. Tem CTA (confira, saiba mais, veja, entenda)? Se NAO, ADICIONE
4. Repita ate estar correto - NAO FINALIZE com comprimento errado

Para o TITULO:
1. Conte os caracteres
2. Esta entre 50-60? Se NAO, REESCREVA
3. Palavra-chave nas primeiras 3 palavras? Se NAO, REORDENE

Para LINKS (E-E-A-T Autoridade):
1. Citou fonte oficial (ministerio, IBGE, etc)?
2. Usou formato [Nome](URL)? Se NAO, CONVERTA
3. Exemplo: [Ministerio da Agricultura](https://www.gov.br/agricultura)`;

  // Add deficit analysis if there are issues
  if (deficits.length > 0) {
    prompt += `

### DEFICITS ATUAIS QUE VOCE DEVE CORRIGIR:
`;
    deficits.forEach(d => {
      prompt += `- ${d}\n`;
    });
    prompt += `
ATENCAO: Os deficits acima mostram EXATAMENTE o que esta errado. Corrija cada um deles na sua resposta.`;
  }

  return prompt;
};

/**
 * Get the weakest categories sorted by percentage score
 * @param {Object} categories - Categories from SEO analysis
 * @returns {Array} - Sorted array of [categoryKey, category] pairs
 */
const getWeakestCategories = (categories) => {
  return Object.entries(categories)
    .map(([key, cat]) => ({
      key,
      category: cat,
      percentage: (cat.score / cat.maxScore) * 100,
      pointsAvailable: cat.maxScore - cat.score
    }))
    .filter(item => item.percentage < 90) // Only include categories that need improvement
    .sort((a, b) => a.percentage - b.percentage); // Weakest first
};

/**
 * Get top recommendations by impact (points available)
 * @param {Array} recommendations - Recommendations from SEO analysis
 * @param {number} limit - Maximum number of recommendations
 * @returns {Array} - Top recommendations
 */
const getTopRecommendations = (recommendations, limit = 3) => {
  return recommendations
    // Filter out internalLinks - user doesn't have article database
    .filter(rec => rec.metric !== 'internalLinks')
    .slice(0, limit)
    .filter(rec => rec.pointsAvailable > 0);
};

/**
 * Generate specific improvement instructions based on metric details
 * @param {string} categoryKey - Category identifier
 * @param {string} metricKey - Metric identifier
 * @param {Object} metric - Metric data
 * @returns {string} - Specific instruction for improvement
 */
const generateMetricInstruction = (categoryKey, metricKey, metric) => {
  const template = SEO_PROMPT_TEMPLATES[categoryKey]?.[metricKey];

  if (!template) {
    return metric.message || '';
  }

  // Replace placeholders with actual values from metric details
  let instruction = template;

  if (metric.details) {
    Object.entries(metric.details).forEach(([key, detail]) => {
      if (typeof detail === 'object' && detail.value !== undefined) {
        instruction = instruction.replace(`{${key}}`, detail.value);
      } else if (typeof detail === 'object' && detail.count !== undefined) {
        instruction = instruction.replace(`{${key}Count}`, detail.count);
      }
    });
  }

  // Replace common placeholders
  if (metric.fleschScore !== undefined) {
    instruction = instruction.replace('{fleschScore}', metric.fleschScore);
  }
  if (metric.details?.avgWordsPerSentence?.value !== undefined) {
    instruction = instruction.replace('{avgWordsPerSentence}', metric.details.avgWordsPerSentence.value);
  }
  if (metric.details?.passiveVoice?.percentage !== undefined) {
    instruction = instruction.replace('{passiveVoicePercent}', metric.details.passiveVoice.percentage);
  }
  if (metric.details?.length?.value !== undefined) {
    instruction = instruction.replace('{currentLength}', metric.details.length.value);
    instruction = instruction.replace('{idealLength}', metric.details.length.ideal);
  }
  if (metric.wordCount !== undefined) {
    instruction = instruction.replace('{wordCount}', metric.wordCount);
  }
  if (metric.details?.directAnswer?.words !== undefined) {
    instruction = instruction.replace('{firstParaWords}', metric.details.directAnswer.words);
  }

  return instruction;
};

/**
 * Get what's already optimized (to tell AI not to change)
 * @param {Object} categories - Categories from SEO analysis
 * @returns {Array} - List of optimized elements
 */
const getOptimizedElements = (categories) => {
  const optimized = [];

  // Only lock elements that have PERFECT scores (no room to improve)
  const titleMetric = categories.onPageOptimization?.metrics?.titleOptimization;
  if (titleMetric && titleMetric.score === titleMetric.maxScore) {
    const titleLength = titleMetric.details?.length?.value;
    optimized.push(`Titulo (${titleLength || ''} caracteres, otimizado)`);
  }

  const metaMetric = categories.onPageOptimization?.metrics?.metaDescription;
  if (metaMetric && metaMetric.score === metaMetric.maxScore) {
    const metaLength = metaMetric.details?.length?.value;
    optimized.push(`Linha fina (${metaLength || ''} caracteres)`);
  }

  const keywordMetric = categories.onPageOptimization?.metrics?.keywordStrategy;
  if (keywordMetric && keywordMetric.score === keywordMetric.maxScore) {
    const density = keywordMetric.details?.primaryDensity?.value;
    optimized.push(`Palavras-chave (densidade de ${density || ''}%)`);
  }

  if (categories.contentQuality?.metrics?.readability?.score === categories.contentQuality?.metrics?.readability?.maxScore) {
    optimized.push('Legibilidade');
  }

  if (categories.contentQuality?.metrics?.contentStructure?.score === categories.contentQuality?.metrics?.contentStructure?.maxScore) {
    optimized.push('Estrutura do conteudo');
  }

  return optimized;
};

/**
 * Calculate potential score improvement
 * @param {Array} recommendations - Recommendations to implement
 * @returns {number} - Total potential points
 */
const calculatePotentialImprovement = (recommendations) => {
  return recommendations.reduce((total, rec) => total + rec.pointsAvailable, 0);
};

/**
 * Generate SEO optimization prompt based on analysis results
 * @param {Object} seoAnalysis - Full SEO analysis from performSEOAnalysis()
 * @param {string} articleType - Type of article (noticia, reportagem, etc.)
 * @param {string} mode - Optimization mode: 'quick', 'complete', or 'focused'
 * @param {Array} focusAreas - Specific areas to focus on (for 'focused' mode)
 * @param {Object} articleData - Optional article data for keyword extraction { title, content, tags }
 * @returns {string} - Contextual prompt for AI optimization
 */
export const generateSEOOptimizationPrompt = (
  seoAnalysis,
  _articleType = 'default',
  mode = 'quick',
  focusAreas = [],
  articleData = {}
) => {
  if (!seoAnalysis) {
    return 'Analise meu texto e sugira melhorias para SEO.';
  }

  const { score, categories, recommendations } = seoAnalysis;
  const targetScore = 80;

  // Extract primary keyword if article data is provided
  const primaryKeyword = articleData.targetKeyword ||
    extractPrimaryKeyword(articleData.title || '', articleData.content || '', articleData.tags || []);

  // Calculate split potential (AI vs manual)
  const splitPotential = calculateSplitPotential(categories);

  // Handle perfect or near-perfect scores
  if (score >= 80) {
    return generateHighScorePrompt(seoAnalysis, categories, primaryKeyword);
  }

  // Get prioritized improvements - only AI-optimizable ones
  const aiOptimizableRecs = recommendations.filter(rec =>
    SEO_SCORING_RULES.aiOptimizableMetrics.includes(rec.metric)
  );

  const topRecommendations = mode === 'complete'
    ? aiOptimizableRecs.slice(0, 5)
    : getTopRecommendations(aiOptimizableRecs, 3);

  const potentialImprovement = calculatePotentialImprovement(topRecommendations);
  const optimizedElements = getOptimizedElements(categories);

  // Build the prompt
  let prompt = '';

  // Score context with keyword focus
  if (score < 40) {
    prompt += `Seu artigo precisa de melhorias significativas de SEO. Score atual: ${score}/100.\n`;
  } else if (score < 60) {
    prompt += `Seu artigo tem potencial para melhorar. Score atual: ${score}/100. Objetivo: ${targetScore}+ (Excelente).\n`;
  } else {
    prompt += `Artigo com bom potencial. Score: ${score}/100 (Bom). Meta: ${targetScore}+ (Excelente).\n`;
  }

  // Add keyword context
  if (primaryKeyword) {
    prompt += `\nPALAVRA-CHAVE PRINCIPAL: "${primaryKeyword}" - use em titulo, linha fina, primeiro paragrafo e ao longo do texto.\n`;
  }

  // Add AI potential vs manual potential context
  prompt += `\nPOTENCIAL DE MELHORIA: IA pode otimizar +${splitPotential.aiPotential} pts`;
  if (splitPotential.manualPotential > 0) {
    prompt += ` | ${splitPotential.manualPotential} pts adicionais requerem acao manual (links, imagens)`;
  }
  prompt += '\n';

  // Add exact scoring rules section (now with categories for deficit analysis)
  prompt += generateScoringRulesSection(primaryKeyword, categories);
  prompt += '\n\n';

  // Improvements section
  if (mode === 'quick') {
    prompt += `PRIORIDADES DE MELHORIA (em ordem de impacto):\n\n`;
  } else if (mode === 'complete') {
    prompt += `MELHORIAS COMPLETAS:\n\n`;
  } else if (mode === 'focused' && focusAreas.length > 0) {
    prompt += `MELHORIAS FOCADAS (${focusAreas.map(a => CATEGORY_NAMES[a] || a).join(', ')}):\n\n`;
  }

  // Add detailed instructions for each recommendation
  topRecommendations.forEach((rec, index) => {
    const categoryName = CATEGORY_NAMES[rec.category] || rec.category;
    const metricName = METRIC_NAMES[rec.metric] || rec.metric;
    const category = categories[rec.category];
    const metric = category?.metrics?.[rec.metric];

    prompt += `${index + 1}. ${categoryName.toUpperCase()} - ${metricName} (pode ganhar +${rec.pointsAvailable} pts):\n`;

    // Get specific instruction
    if (metric) {
      const instruction = generateMetricInstruction(rec.category, rec.metric, metric);
      if (instruction) {
        prompt += `   ${instruction}\n`;
      }
    }

    // Add action items based on category
    const actionItems = getActionItems(rec.category, rec.metric, metric);
    actionItems.forEach(item => {
      prompt += `   - ${item}\n`;
    });

    prompt += '\n';
  });

  // What NOT to change
  if (optimizedElements.length > 0) {
    prompt += `NAO ALTERE (ja otimizados):\n`;
    optimizedElements.forEach(element => {
      prompt += `- ${element}\n`;
    });
    prompt += '\n';
  }

  // Final instruction with realistic expectation
  prompt += `Faca as melhorias mantendo o tom e estilo do artigo. `;

  if (potentialImprovement > 0) {
    // Use AI potential for realistic estimate
    const realisticGain = Math.min(potentialImprovement, splitPotential.aiPotential);
    const estimatedNewScore = Math.min(100, score + realisticGain);
    prompt += `Score estimado apos otimizacao IA: ${score} -> ~${estimatedNewScore} pts.`;
  }

  // Add mandatory formatting instructions
  prompt += `

FORMATO DE SAIDA OBRIGATORIO:
- Links DEVEM usar sintaxe markdown: [texto visivel](https://url-completa)
- Exemplo correto: [Ministerio da Agricultura](https://www.gov.br/agricultura)
- Exemplo INCORRETO: Ministerio da Agricultura (https://www.gov.br)
- Destaques com **negrito** usando asteriscos duplos
- Subtitulos com ## (H2) ou ### (H3)
- Listas: cada item em uma LINHA SEPARADA, comecando com - (sem espaco antes)
  Exemplo correto:
  - Item um
  - Item dois
  - Item tres
- Paragrafos separados por linha em branco
- NAO use HTML, apenas markdown puro`;

  return prompt;
};

/**
 * Generate prompt for high-score articles (78+)
 */
const generateHighScorePrompt = (seoAnalysis, categories, primaryKeyword = '') => {
  const { score } = seoAnalysis;
  const weakest = getWeakestCategories(categories);

  let prompt = `Artigo quase excelente! Score: ${score}/100. `;

  if (primaryKeyword) {
    prompt += `Palavra-chave: "${primaryKeyword}". `;
  }

  if (score < 80) {
    const pointsToExcellent = 80 - score;
    prompt += `Faltam apenas ${pointsToExcellent} pts para Excelente.\n\n`;
    prompt += `POLIMENTO FINAL:\n\n`;

    if (weakest.length > 0) {
      const topWeak = weakest[0];
      const category = categories[topWeak.key];
      const weakMetrics = Object.entries(category.metrics)
        .filter(([, m]) => m.status !== 'success')
        .filter(([metricKey]) => SEO_SCORING_RULES.aiOptimizableMetrics.includes(metricKey))
        .slice(0, 2);

      weakMetrics.forEach(([metricKey, metric], index) => {
        const metricName = METRIC_NAMES[metricKey] || metricKey;
        prompt += `${index + 1}. ${metricName} (+${metric.maxScore - metric.score} pts):\n`;
        prompt += `   - ${metric.message}\n\n`;
      });
    }
  } else {
    prompt += `Score ja esta excelente!\n\n`;
    prompt += `SUGESTOES OPCIONAIS:\n`;
    prompt += `- Considere adicionar uma lista resumindo pontos-chave\n`;
    prompt += `- Uma citacao em destaque (blockquote) pode melhorar escaneabilidade\n`;
  }

  prompt += `\nNAO MODIFIQUE o restante - esta otimizado.`;

  // Add formatting instructions for high score articles too
  prompt += `

FORMATO: Use markdown - links como [texto](url), **negrito**, listas com -.`;

  return prompt;
};

/**
 * Get specific action items for each category/metric combination
 */
const getActionItems = (categoryKey, metricKey, metric) => {
  const items = [];

  switch (categoryKey) {
    case 'contentQuality':
      if (metricKey === 'readability') {
        if (metric?.details?.avgWordsPerSentence?.value > 20) {
          items.push(`Reduza frases de ${metric.details.avgWordsPerSentence.value} para maximo 20 palavras`);
        }
        if (metric?.details?.passiveVoice?.percentage > 10) {
          items.push('Substitua voz passiva por voz ativa');
        }
        items.push('Divida paragrafos longos em 3-4 frases');
        items.push('Adicione palavras de transicao entre paragrafos');
      } else if (metricKey === 'contentStructure') {
        if (!metric?.details?.hasSubheadings?.passed) {
          items.push('Adicione subtitulos (H2/H3) a cada 300-400 palavras');
        }
        if (!metric?.details?.hasList?.passed) {
          items.push('Adicione lista com pontos-chave');
        }
        if (!metric?.details?.hasIntroduction?.passed) {
          items.push('Melhore o paragrafo introdutorio (30-100 palavras resumindo o fato)');
        }
      }
      break;

    case 'eeatSignals':
      if (metricKey === 'experience') {
        items.push('Use expressoes como "segundo apuracao", "a reportagem descobriu"');
        items.push('Cite detalhes especificos que mostrem investigacao');
        items.push('Adicione testemunhos ou entrevistas se aplicavel');
      } else if (metricKey === 'expertise') {
        items.push('Cite pelo menos 2 fontes com nome');
        items.push('Inclua citacoes de especialistas na area');
      } else if (metricKey === 'authority') {
        items.push('Cite pelo menos 1 fonte oficial (governo, instituicao)');
        items.push('Adicione dados de orgaos reconhecidos (IBGE, Banco Central, etc.)');
        items.push('Nomeie especialistas citados');
      } else if (metricKey === 'trust') {
        items.push('Fundamente afirmacoes com dados verificaveis');
        items.push('Apresente diferentes perspectivas quando aplicavel');
      }
      break;

    case 'onPageOptimization':
      if (metricKey === 'titleOptimization') {
        if (metric?.details?.length?.value > 60) {
          items.push(`Reduza o titulo de ${metric.details.length.value} para 50-60 caracteres`);
        } else if (metric?.details?.length?.value < 45) {
          items.push(`Expanda o titulo de ${metric.details.length.value} para 50-60 caracteres`);
        }
        if (!metric?.details?.powerWords?.found) {
          items.push('Adicione palavra de impacto (exclusivo, revela, novo, etc.)');
        }
      } else if (metricKey === 'metaDescription') {
        if (metric?.details?.length?.value < 150) {
          items.push('Expanda a linha fina para 150-160 caracteres');
        }
        if (!metric?.details?.cta?.found) {
          items.push('Adicione convite para ler (saiba mais, veja, confira)');
        }
      }
      break;

    case 'aiSerpOptimization':
      if (metricKey === 'featuredSnippet') {
        const words = metric?.details?.directAnswer?.words || 0;
        if (words < 40 || words > 60) {
          items.push(`Reescreva primeiro paragrafo com 40-60 palavras (atual: ${words})`);
        }
        items.push('Responda diretamente: quem, o que, quando, onde');
        if (!metric?.details?.hasList?.found) {
          items.push('Inclua uma lista se relevante para o tema');
        }
      } else if (metricKey === 'aiOverview') {
        items.push('Estruture com subtitulos claros e paragrafos curtos');
        items.push('Inclua dados verificaveis (numeros, datas, nomes)');
      }
      break;

    case 'technicalExcellence':
      // Note: internalLinks case removed - user doesn't have article database
      // so AI-generated internal links would be useless placeholders
      if (metricKey === 'externalLinks') {
        items.push('Adicione links para fontes oficiais (.gov, .edu, .org)');
        items.push('Use textos descritivos nos links (evite "clique aqui")');
      } else if (metricKey === 'mediaOptimization') {
        items.push('Adicione pelo menos 1 imagem com alt text descritivo');
      }
      break;
  }

  return items;
};

/**
 * Generate a summary of what the AI optimization will do
 * @param {Object} seoAnalysis - Full SEO analysis
 * @param {Object} articleData - Optional article data { title, content, tags }
 * @returns {Object} - Summary with potential improvements including AI vs manual split
 */
export const generateOptimizationSummary = (seoAnalysis) => {
  if (!seoAnalysis) {
    return {
      potentialGain: 0,
      improvements: [],
      estimatedScore: 0,
      aiPotential: 0,
      manualPotential: 0,
      manualTasks: []
    };
  }

  const { score, recommendations, categories } = seoAnalysis;

  // Calculate split potential
  const splitPotential = calculateSplitPotential(categories);

  // Get only AI-optimizable recommendations
  const aiOptimizableRecs = recommendations.filter(rec =>
    SEO_SCORING_RULES.aiOptimizableMetrics.includes(rec.metric)
  );
  const topRecommendations = getTopRecommendations(aiOptimizableRecs, 3);
  const aiPotentialGain = calculatePotentialImprovement(topRecommendations);

  // Get manual tasks that need user action
  const manualTasks = splitPotential.manualMetrics.map(m => ({
    metric: m.name,
    points: m.points,
    action: getManualTaskAction(m.metric)
  }));

  return {
    currentScore: score,
    potentialGain: aiPotentialGain, // Use AI potential for display
    estimatedScore: Math.min(100, score + aiPotentialGain),
    aiPotential: splitPotential.aiPotential,
    manualPotential: splitPotential.manualPotential,
    improvements: topRecommendations.map(rec => ({
      category: CATEGORY_NAMES[rec.category] || rec.category,
      metric: METRIC_NAMES[rec.metric] || rec.metric,
      pointsAvailable: rec.pointsAvailable,
      message: rec.message,
      isAiOptimizable: true
    })),
    manualTasks
  };
};

/**
 * Get action description for manual tasks
 */
const getManualTaskAction = (metricKey) => {
  const actions = {
    internalLinks: 'Adicionar links internos para outras materias do site',
    mediaOptimization: 'Adicionar imagem com alt text descritivo',
    urlSlug: 'Otimizar URL/slug do artigo'
  };
  return actions[metricKey] || 'Acao manual necessaria';
};

export default {
  generateSEOOptimizationPrompt,
  generateOptimizationSummary,
  extractPrimaryKeyword,
  calculateSplitPotential
};
