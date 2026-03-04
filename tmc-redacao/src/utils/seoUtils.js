/**
 * SEO Utilities - Comprehensive SEO analysis functions
 *
 * Based on Google's 2025-2026 ranking factors, E-E-A-T principles,
 * and AI Overview optimization guidelines.
 */

import {
  ARTICLE_TYPE_THRESHOLDS,
  ALL_POWER_WORDS,
  EXPERIENCE_PATTERNS,
  EXPERTISE_PATTERNS,
  ALL_AUTHORITY_SOURCES,
  TRUST_SIGNALS,
  ALL_AUTHORITY_DOMAINS,
  ALL_TRANSITION_WORDS,
  STOP_WORDS,
  SCORING_THRESHOLDS,
  CATEGORY_WEIGHTS,
  LSI_ASSOCIATIONS,
  CLICKBAIT_PATTERNS,
  REPORTING_VERBS,
  STRUCTURE_PATTERNS
} from '../constants/seoConstants';

// ═══════════════════════════════════════════════════════════════
// BASIC TEXT UTILITIES
// ═══════════════════════════════════════════════════════════════

/**
 * Strip HTML tags from content
 */
export const stripHtml = (html) => {
  if (!html) return '';
  return html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
};

/**
 * Count words in text
 */
export const countWords = (text) => {
  const cleanText = stripHtml(text);
  if (!cleanText) return 0;
  return cleanText.split(/\s+/).filter(w => w.length > 0).length;
};

/**
 * Count sentences in text
 */
export const countSentences = (text) => {
  const cleanText = stripHtml(text);
  if (!cleanText) return 0;
  return cleanText.split(/[.!?]+/).filter(s => s.trim().length > 0).length;
};

/**
 * Count paragraphs in content
 */
export const countParagraphs = (content) => {
  if (!content) return 0;

  // Check for HTML paragraphs
  const htmlParagraphs = (content.match(/<p[^>]*>/gi) || []).length;
  if (htmlParagraphs > 0) return htmlParagraphs;

  // Check for line breaks
  const textParagraphs = content.split(/\n\n+/).filter(p => p.trim().length > 0).length;
  return textParagraphs || 1;
};

/**
 * Get first paragraph from content
 */
export const getFirstParagraph = (content) => {
  if (!content) return '';

  // Try to extract from HTML
  const htmlMatch = content.match(/<p[^>]*>(.*?)<\/p>/is);
  if (htmlMatch) return stripHtml(htmlMatch[1]);

  // Fall back to text splitting
  const paragraphs = content.split(/\n\n+/);
  return stripHtml(paragraphs[0] || '');
};

/**
 * Count syllables in Portuguese word
 */
export const countSyllables = (word) => {
  const cleanWord = word.toLowerCase().replace(/[^a-záéíóúâêîôûãõç]/g, '');
  if (cleanWord.length <= 2) return 1;

  const vowelGroups = cleanWord.match(/[aeiouáéíóúâêîôûãõ]+/g);
  if (!vowelGroups) return 1;

  let syllableCount = vowelGroups.length;
  const ditongos = (cleanWord.match(/ai|au|ei|eu|oi|ou|ui|ão|ãe|õe/g) || []).length;
  syllableCount -= ditongos * 0.5;

  return Math.max(1, Math.round(syllableCount));
};

// ═══════════════════════════════════════════════════════════════
// 1. CONTENT QUALITY ANALYSIS (30 pts)
// ═══════════════════════════════════════════════════════════════

/**
 * Analyze word count and depth based on article type
 */
export const analyzeContentDepth = (content, articleType = 'default') => {
  const wordCount = countWords(content);
  const thresholds = ARTICLE_TYPE_THRESHOLDS[articleType] || ARTICLE_TYPE_THRESHOLDS.default;

  let score = 0;
  let status = 'error';
  let message = '';

  if (wordCount >= thresholds.min && wordCount <= thresholds.max) {
    if (wordCount >= thresholds.ideal * 0.8 && wordCount <= thresholds.ideal * 1.3) {
      score = 10;
      status = 'success';
      message = `Tamanho ideal para ${thresholds.name.toLowerCase()} (${wordCount} palavras)`;
    } else {
      score = 7;
      status = 'success';
      message = `Dentro do range aceitável (${wordCount} palavras)`;
    }
  } else if (wordCount >= thresholds.min * 0.7 || (wordCount > thresholds.max && wordCount <= thresholds.max * 1.3)) {
    score = 4;
    status = 'warning';
    message = wordCount < thresholds.min
      ? `Texto curto para ${thresholds.name.toLowerCase()} (ideal: ${thresholds.min}+ palavras)`
      : `Texto extenso para ${thresholds.name.toLowerCase()} (ideal: até ${thresholds.max} palavras)`;
  } else if (wordCount > 0) {
    score = 2;
    status = 'warning';
    message = wordCount < thresholds.min
      ? `Muito curto (${wordCount}/${thresholds.min} palavras mínimas)`
      : `Muito extenso (considere dividir o artigo)`;
  } else {
    score = 0;
    status = 'error';
    message = 'Adicione conteúdo ao artigo';
  }

  return {
    score,
    maxScore: 10,
    status,
    message,
    wordCount,
    thresholds,
    articleType
  };
};

/**
 * Analyze content structure
 */
export const analyzeContentStructure = (content) => {
  const results = {
    score: 0,
    maxScore: 10,
    details: {}
  };

  // Check for introduction (first paragraph summary)
  const firstPara = getFirstParagraph(content);
  const firstParaWords = countWords(firstPara);
  const hasIntroduction = firstParaWords >= 30 && firstParaWords <= 100;
  results.details.hasIntroduction = {
    passed: hasIntroduction,
    points: hasIntroduction ? 2 : 0,
    message: hasIntroduction ? 'Introdução adequada' : 'Melhore o parágrafo introdutório (30-100 palavras)'
  };
  results.score += results.details.hasIntroduction.points;

  // Check for subheadings (H2, H3)
  const h2Count = (content.match(/<h2[^>]*>/gi) || []).length;
  const h3Count = (content.match(/<h3[^>]*>/gi) || []).length;
  const mdH2Count = (content.match(/^##\s+/gm) || []).length;
  const mdH3Count = (content.match(/^###\s+/gm) || []).length;
  const totalHeadings = h2Count + h3Count + mdH2Count + mdH3Count;
  const hasSubheadings = totalHeadings >= 2;
  results.details.hasSubheadings = {
    passed: hasSubheadings,
    points: hasSubheadings ? 2 : (totalHeadings >= 1 ? 1 : 0),
    count: totalHeadings,
    message: hasSubheadings ? `${totalHeadings} subtítulos encontrados` : 'Adicione subtítulos (H2/H3) para organizar o conteúdo'
  };
  results.score += results.details.hasSubheadings.points;

  // Check for conclusion (last paragraph)
  const paragraphs = content.split(/<\/p>|<br\s*\/?>\s*<br\s*\/?>|\n\n+/i).filter(p => stripHtml(p).trim().length > 0);
  const lastPara = paragraphs.length > 0 ? stripHtml(paragraphs[paragraphs.length - 1]) : '';
  const hasConclusion = lastPara.length >= 50 && (
    /em\s+(resumo|suma|síntese)|concluindo|portanto|assim|por\s+fim|finalmente/i.test(lastPara) ||
    paragraphs.length >= 3
  );
  results.details.hasConclusion = {
    passed: hasConclusion,
    points: hasConclusion ? 2 : (paragraphs.length >= 3 ? 1 : 0),
    message: hasConclusion ? 'Conclusão presente' : 'Adicione uma conclusão ao artigo'
  };
  results.score += results.details.hasConclusion.points;

  // Check paragraph length
  const paragraphLengths = paragraphs.map(p => countWords(p));
  const avgParagraphLength = paragraphLengths.length > 0
    ? paragraphLengths.reduce((a, b) => a + b, 0) / paragraphLengths.length
    : 0;
  const shortParagraphs = avgParagraphLength <= 150;
  results.details.shortParagraphs = {
    passed: shortParagraphs,
    points: shortParagraphs ? 2 : (avgParagraphLength <= 200 ? 1 : 0),
    avgLength: Math.round(avgParagraphLength),
    message: shortParagraphs
      ? `Parágrafos bem dimensionados (média: ${Math.round(avgParagraphLength)} palavras)`
      : `Parágrafos muito longos (média: ${Math.round(avgParagraphLength)} palavras) - ideal: até 150`
  };
  results.score += results.details.shortParagraphs.points;

  // Check for lists
  const hasBulletList = STRUCTURE_PATTERNS.bulletList.test(content) || STRUCTURE_PATTERNS.markdown.bulletList.test(content);
  const hasNumberedList = STRUCTURE_PATTERNS.numberedList.test(content) || STRUCTURE_PATTERNS.markdown.numberedList.test(content);
  const hasList = hasBulletList || hasNumberedList;
  results.details.hasList = {
    passed: hasList,
    points: hasList ? 1 : 0,
    message: hasList ? 'Listas presentes' : 'Considere adicionar listas para informações sequenciais'
  };
  results.score += results.details.hasList.points;

  // Check for blockquotes
  const hasQuotes = STRUCTURE_PATTERNS.blockquote.test(content) || STRUCTURE_PATTERNS.markdown.blockquote.test(content);
  results.details.hasQuotes = {
    passed: hasQuotes,
    points: hasQuotes ? 1 : 0,
    message: hasQuotes ? 'Citações em destaque presentes' : 'Considere destacar citações importantes'
  };
  results.score += results.details.hasQuotes.points;

  // Overall status
  results.status = results.score >= 8 ? 'success' : results.score >= 5 ? 'warning' : 'error';
  results.message = results.score >= 8
    ? 'Estrutura excelente'
    : results.score >= 5
      ? 'Estrutura pode ser melhorada'
      : 'Melhore a estrutura do conteúdo';

  return results;
};

/**
 * Analyze readability using Flesch-PT formula
 */
export const analyzeReadability = (content) => {
  const text = stripHtml(content);
  if (!text || text.trim().length === 0) {
    return {
      score: 0,
      maxScore: 10,
      fleschScore: 0,
      grade: 'N/A',
      status: 'neutral',
      message: 'Adicione conteúdo para analisar',
      details: {}
    };
  }

  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
  const words = text.split(/\s+/).filter(w => w.length > 0);

  if (sentences.length === 0 || words.length === 0) {
    return {
      score: 0,
      maxScore: 10,
      fleschScore: 0,
      grade: 'N/A',
      status: 'neutral',
      message: 'Texto muito curto para análise',
      details: {}
    };
  }

  // Calculate metrics
  const totalSyllables = words.reduce((count, word) => count + countSyllables(word), 0);
  const avgWordsPerSentence = words.length / sentences.length;
  const avgSyllablesPerWord = totalSyllables / words.length;

  // Flesch score adapted for Portuguese
  const fleschScore = Math.round(248.835 - (1.015 * avgWordsPerSentence) - (84.6 * avgSyllablesPerWord));
  const clampedFlesch = Math.max(0, Math.min(100, fleschScore));

  // Determine grade
  let grade, gradeStatus;
  if (clampedFlesch >= 80) {
    grade = 'Muito Fácil';
    gradeStatus = 'success';
  } else if (clampedFlesch >= 60) {
    grade = 'Fácil';
    gradeStatus = 'success';
  } else if (clampedFlesch >= 40) {
    grade = 'Moderado';
    gradeStatus = 'warning';
  } else if (clampedFlesch >= 20) {
    grade = 'Difícil';
    gradeStatus = 'warning';
  } else {
    grade = 'Muito Difícil';
    gradeStatus = 'error';
  }

  // Check passive voice (simplified detection for Portuguese)
  const passivePatterns = /foi\s+\w+[ao]|foram\s+\w+[ao]s?|é\s+\w+[ao]|são\s+\w+[ao]s?|será\s+\w+[ao]|serão\s+\w+[ao]s?|sendo\s+\w+[ao]/gi;
  const passiveMatches = (text.match(passivePatterns) || []).length;
  const passivePercentage = sentences.length > 0 ? (passiveMatches / sentences.length) * 100 : 0;

  // Check transition words
  const transitionCount = ALL_TRANSITION_WORDS.reduce((count, word) => {
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    return count + (text.match(regex) || []).length;
  }, 0);
  const hasGoodTransitions = transitionCount >= Math.ceil(sentences.length * 0.3);

  // Calculate score
  let score = 0;

  // Flesch score component (4 pts)
  if (clampedFlesch >= 60) score += 4;
  else if (clampedFlesch >= 40) score += 2;
  else if (clampedFlesch >= 20) score += 1;

  // Sentence length component (2 pts)
  if (avgWordsPerSentence <= 20) score += 2;
  else if (avgWordsPerSentence <= 25) score += 1;

  // Passive voice component (2 pts)
  if (passivePercentage < 10) score += 2;
  else if (passivePercentage < 20) score += 1;

  // Transition words component (2 pts)
  if (hasGoodTransitions) score += 2;
  else if (transitionCount >= 2) score += 1;

  return {
    score,
    maxScore: 10,
    fleschScore: clampedFlesch,
    grade,
    status: score >= 8 ? 'success' : score >= 5 ? 'warning' : 'error',
    message: score >= 8
      ? `Excelente legibilidade (Flesch: ${clampedFlesch})`
      : score >= 5
        ? `Legibilidade pode melhorar (Flesch: ${clampedFlesch})`
        : `Texto difícil de ler (Flesch: ${clampedFlesch})`,
    details: {
      fleschScore: { value: clampedFlesch, grade, status: gradeStatus },
      avgWordsPerSentence: { value: Math.round(avgWordsPerSentence * 10) / 10, ideal: 20, status: avgWordsPerSentence <= 20 ? 'success' : avgWordsPerSentence <= 25 ? 'warning' : 'error' },
      passiveVoice: { percentage: Math.round(passivePercentage), ideal: 10, status: passivePercentage < 10 ? 'success' : passivePercentage < 20 ? 'warning' : 'error' },
      transitionWords: { count: transitionCount, hasGood: hasGoodTransitions, status: hasGoodTransitions ? 'success' : transitionCount >= 2 ? 'warning' : 'error' }
    }
  };
};

// ═══════════════════════════════════════════════════════════════
// 2. ON-PAGE OPTIMIZATION (25 pts)
// ═══════════════════════════════════════════════════════════════

/**
 * Analyze title optimization
 */
export const analyzeTitleOptimization = (title, content, targetKeyword) => {
  const results = {
    score: 0,
    maxScore: 8,
    details: {}
  };

  const titleLength = title?.length || 0;
  const titleWords = title?.toLowerCase().split(/\s+/) || [];
  const cleanTitle = title?.toLowerCase() || '';

  // Length check (2 pts)
  const { idealMin, idealMax, min, max } = SCORING_THRESHOLDS.title;
  let lengthScore = 0;
  let lengthStatus = 'error';
  if (titleLength >= idealMin && titleLength <= idealMax) {
    lengthScore = 2;
    lengthStatus = 'success';
  } else if (titleLength >= min && titleLength <= max) {
    lengthScore = 1;
    lengthStatus = 'warning';
  }
  results.details.length = {
    value: titleLength,
    ideal: `${idealMin}-${idealMax}`,
    points: lengthScore,
    status: lengthStatus,
    message: lengthStatus === 'success'
      ? `Tamanho ideal (${titleLength} caracteres)`
      : titleLength < idealMin
        ? `Muito curto (${titleLength}/${idealMin} caracteres)`
        : `Muito longo (${titleLength}/${idealMax} caracteres)`
  };
  results.score += lengthScore;

  // Keyword position (2 pts)
  const keyword = targetKeyword?.toLowerCase() || '';
  const keywordWords = keyword.split(/\s+/).filter(w => w.length > 3);
  const first3Words = titleWords.slice(0, 3).join(' ');
  const keywordInFirst3 = keywordWords.some(kw => first3Words.includes(kw));
  const keywordInTitle = keywordWords.some(kw => cleanTitle.includes(kw));
  let keywordScore = 0;
  if (keywordInFirst3) keywordScore = 2;
  else if (keywordInTitle) keywordScore = 1;
  results.details.keywordPosition = {
    inFirst3: keywordInFirst3,
    inTitle: keywordInTitle,
    points: keywordScore,
    status: keywordInFirst3 ? 'success' : keywordInTitle ? 'warning' : 'error',
    message: keywordInFirst3
      ? 'Palavra-chave nas primeiras 3 palavras'
      : keywordInTitle
        ? 'Palavra-chave presente, mas não no início'
        : 'Adicione a palavra-chave ao título'
  };
  results.score += keywordScore;

  // Power words (1 pt)
  const hasPowerWord = ALL_POWER_WORDS.some(pw => cleanTitle.includes(pw.toLowerCase()));
  results.details.powerWords = {
    found: hasPowerWord,
    points: hasPowerWord ? 1 : 0,
    status: hasPowerWord ? 'success' : 'neutral',
    message: hasPowerWord ? 'Power word detectada' : 'Considere usar power words (exclusivo, urgente, revelado...)'
  };
  results.score += results.details.powerWords.points;

  // Numbers (1 pt)
  const hasNumbers = /\d+/.test(title || '');
  results.details.numbers = {
    found: hasNumbers,
    points: hasNumbers ? 1 : 0,
    status: hasNumbers ? 'success' : 'neutral',
    message: hasNumbers ? 'Número no título' : 'Números aumentam CTR em 36%'
  };
  results.score += results.details.numbers.points;

  // Emotional appeal (1 pt)
  const emotionalWords = ['exclusivo', 'urgente', 'chocante', 'surpreendente', 'inédito', 'histórico', 'polêmico', 'emocionante'];
  const hasEmotional = emotionalWords.some(ew => cleanTitle.includes(ew));
  results.details.emotional = {
    found: hasEmotional,
    points: hasEmotional ? 1 : 0,
    status: hasEmotional ? 'success' : 'neutral',
    message: hasEmotional ? 'Apelo emocional presente' : 'Considere adicionar apelo emocional'
  };
  results.score += results.details.emotional.points;

  // Uniqueness/not generic (1 pt)
  const genericStarts = ['notícia sobre', 'artigo sobre', 'informações sobre', 'saiba mais sobre', 'tudo sobre'];
  const isGeneric = genericStarts.some(gs => cleanTitle.startsWith(gs));
  results.details.uniqueness = {
    isGeneric,
    points: isGeneric ? 0 : 1,
    status: isGeneric ? 'warning' : 'success',
    message: isGeneric ? 'Título genérico - seja mais específico' : 'Título original'
  };
  results.score += results.details.uniqueness.points;

  // Overall status
  results.status = results.score >= 6 ? 'success' : results.score >= 4 ? 'warning' : 'error';
  results.message = results.score >= 6
    ? 'Título bem otimizado'
    : results.score >= 4
      ? 'Título pode ser melhorado'
      : 'Otimize o título para melhor SEO';

  return results;
};

/**
 * Analyze meta description (linha fina)
 */
export const analyzeMetaDescription = (linhaFina, title, targetKeyword) => {
  const results = {
    score: 0,
    maxScore: 7,
    details: {}
  };

  const length = linhaFina?.length || 0;
  const cleanMeta = linhaFina?.toLowerCase() || '';
  const cleanTitle = title?.toLowerCase() || '';

  // Length check (2 pts)
  const { idealMin, idealMax, min } = SCORING_THRESHOLDS.metaDescription;
  let lengthScore = 0;
  let lengthStatus = 'error';
  if (length >= idealMin && length <= idealMax) {
    lengthScore = 2;
    lengthStatus = 'success';
  } else if (length >= min) {
    lengthScore = 1;
    lengthStatus = 'warning';
  }
  results.details.length = {
    value: length,
    ideal: `${idealMin}-${idealMax}`,
    points: lengthScore,
    status: lengthStatus,
    message: lengthStatus === 'success'
      ? `Tamanho ideal (${length} caracteres)`
      : length < min
        ? `Muito curta (${length}/${min} caracteres mínimos)`
        : `Pode ser mais concisa (${length} caracteres)`
  };
  results.score += lengthScore;

  // Keyword check (2 pts)
  const keyword = targetKeyword?.toLowerCase() || '';
  const keywordWords = keyword.split(/\s+/).filter(w => w.length > 3);
  const hasKeyword = keywordWords.some(kw => cleanMeta.includes(kw));
  results.details.keyword = {
    found: hasKeyword,
    points: hasKeyword ? 2 : 0,
    status: hasKeyword ? 'success' : 'error',
    message: hasKeyword ? 'Palavra-chave presente' : 'Inclua a palavra-chave na meta description'
  };
  results.score += results.details.keyword.points;

  // CTA or hook (1 pt)
  const ctaPatterns = /saiba|veja|confira|descubra|entenda|conheça|leia|assista|acompanhe/i;
  const hasCTA = ctaPatterns.test(linhaFina || '');
  results.details.cta = {
    found: hasCTA,
    points: hasCTA ? 1 : 0,
    status: hasCTA ? 'success' : 'neutral',
    message: hasCTA ? 'Call-to-action presente' : 'Adicione um convite para ler (saiba mais, veja...)'
  };
  results.score += results.details.cta.points;

  // Different from title (1 pt)
  const titleWords = cleanTitle.split(/\s+/).filter(w => w.length > 3);
  const metaWords = cleanMeta.split(/\s+/).filter(w => w.length > 3);
  const overlap = titleWords.filter(w => metaWords.includes(w)).length;
  const overlapPercentage = titleWords.length > 0 ? (overlap / titleWords.length) * 100 : 0;
  const isDifferent = overlapPercentage < 70;
  results.details.unique = {
    overlapPercentage: Math.round(overlapPercentage),
    points: isDifferent ? 1 : 0,
    status: isDifferent ? 'success' : 'warning',
    message: isDifferent ? 'Complementa o título' : 'Muito similar ao título - diferencie o conteúdo'
  };
  results.score += results.details.unique.points;

  // Complete sentence (1 pt)
  const isComplete = /[.!?]$/.test((linhaFina || '').trim());
  results.details.complete = {
    isComplete,
    points: isComplete ? 1 : 0,
    status: isComplete ? 'success' : 'warning',
    message: isComplete ? 'Frase completa' : 'Termine com pontuação adequada'
  };
  results.score += results.details.complete.points;

  // Overall status
  results.status = results.score >= 5 ? 'success' : results.score >= 3 ? 'warning' : 'error';
  results.message = results.score >= 5
    ? 'Meta description bem otimizada'
    : results.score >= 3
      ? 'Meta description pode ser melhorada'
      : 'Melhore a meta description';

  return results;
};

/**
 * Analyze keyword strategy
 */
export const analyzeKeywordStrategy = (content, title, targetKeyword) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {},
    keywords: []
  };

  const text = stripHtml(content).toLowerCase();
  const wordCount = countWords(content);

  if (wordCount === 0) {
    return {
      ...results,
      status: 'error',
      message: 'Adicione conteúdo para analisar'
    };
  }

  // Extract keywords
  const words = text.split(/\s+/).filter(w => w.length > 4);
  const frequency = {};
  words.forEach(word => {
    const cleanWord = word.replace(/[^a-záéíóúâêîôûãõç]/g, '');
    if (cleanWord.length > 4 && !STOP_WORDS.includes(cleanWord)) {
      frequency[cleanWord] = (frequency[cleanWord] || 0) + 1;
    }
  });

  // Get top keywords
  const topKeywords = Object.entries(frequency)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([word, count]) => {
      const density = (count / wordCount) * 100;
      let status = 'warning';
      if (density >= 1 && density <= 2.5) status = 'success';
      else if (density > 3) status = 'error';

      return {
        word,
        count,
        density: Math.round(density * 10) / 10,
        status,
        inTitle: title?.toLowerCase().includes(word) || false
      };
    });

  results.keywords = topKeywords;

  // Primary keyword density (2 pts)
  const primaryKeyword = targetKeyword?.toLowerCase() || topKeywords[0]?.word || '';
  const primaryCount = primaryKeyword ? (text.match(new RegExp(primaryKeyword, 'gi')) || []).length : 0;
  const primaryDensity = wordCount > 0 ? (primaryCount / wordCount) * 100 : 0;
  const densityStatus = primaryDensity >= 1 && primaryDensity <= 2.5 ? 'success' : primaryDensity > 0 && primaryDensity < 3 ? 'warning' : 'error';
  results.details.primaryDensity = {
    value: Math.round(primaryDensity * 10) / 10,
    ideal: '1-2.5%',
    count: primaryCount,
    points: densityStatus === 'success' ? 2 : densityStatus === 'warning' ? 1 : 0,
    status: densityStatus,
    message: densityStatus === 'success'
      ? `Densidade ideal (${Math.round(primaryDensity * 10) / 10}%)`
      : primaryDensity > 2.5
        ? `Densidade alta - evite keyword stuffing (${Math.round(primaryDensity * 10) / 10}%)`
        : `Densidade baixa (${Math.round(primaryDensity * 10) / 10}%) - ideal: 1-2.5%`
  };
  results.score += results.details.primaryDensity.points;

  // LSI keywords (1 pt)
  const lsiWords = LSI_ASSOCIATIONS[primaryKeyword] || [];
  const foundLSI = lsiWords.filter(lsi => text.includes(lsi.toLowerCase()));
  const hasLSI = foundLSI.length >= 2;
  results.details.lsiKeywords = {
    found: foundLSI,
    count: foundLSI.length,
    points: hasLSI ? 1 : 0,
    status: hasLSI ? 'success' : 'neutral',
    message: hasLSI ? `${foundLSI.length} palavras LSI encontradas` : 'Adicione variações semânticas'
  };
  results.score += results.details.lsiKeywords.points;

  // Keyword variations (1 pt)
  const hasVariations = topKeywords.length >= 3 && topKeywords.some(k => k.status === 'success');
  results.details.variations = {
    count: topKeywords.length,
    points: hasVariations ? 1 : 0,
    status: hasVariations ? 'success' : 'warning',
    message: hasVariations ? 'Boas variações de keywords' : 'Diversifique as palavras-chave'
  };
  results.score += results.details.variations.points;

  // Natural placement (1 pt)
  const firstPara = getFirstParagraph(content).toLowerCase();
  const keywordInFirst = primaryKeyword && firstPara.includes(primaryKeyword);
  results.details.naturalPlacement = {
    inFirstParagraph: keywordInFirst,
    points: keywordInFirst ? 1 : 0,
    status: keywordInFirst ? 'success' : 'warning',
    message: keywordInFirst ? 'Keyword no primeiro parágrafo' : 'Inclua a keyword no início do texto'
  };
  results.score += results.details.naturalPlacement.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Boa estratégia de keywords'
    : results.score >= 2
      ? 'Melhore o uso de palavras-chave'
      : 'Estratégia de keywords precisa de atenção';

  return results;
};

/**
 * Analyze URL/slug optimization
 */
export const analyzeSlug = (slug, title, targetKeyword) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {}
  };

  const cleanSlug = slug?.toLowerCase() || '';
  const slugLength = cleanSlug.length;

  // Length check (1 pt)
  const lengthOk = slugLength > 0 && slugLength <= 60;
  results.details.length = {
    value: slugLength,
    ideal: '≤60',
    points: lengthOk ? 1 : 0,
    status: lengthOk ? 'success' : slugLength === 0 ? 'error' : 'warning',
    message: lengthOk ? `Tamanho OK (${slugLength} caracteres)` : slugLength === 0 ? 'Slug não definido' : `Muito longo (${slugLength}/60)`
  };
  results.score += results.details.length.points;

  // Keyword present (2 pts)
  const keyword = targetKeyword?.toLowerCase() || '';
  const keywordWords = keyword.split(/\s+/).filter(w => w.length > 3);
  const keywordInSlug = keywordWords.some(kw => cleanSlug.includes(kw));
  results.details.keywordPresent = {
    found: keywordInSlug,
    points: keywordInSlug ? 2 : 0,
    status: keywordInSlug ? 'success' : 'error',
    message: keywordInSlug ? 'Palavra-chave no slug' : 'Inclua a keyword no slug'
  };
  results.score += results.details.keywordPresent.points;

  // No stop words (1 pt)
  const slugWords = cleanSlug.split(/[-_]/);
  const stopWordsInSlug = slugWords.filter(w => STOP_WORDS.includes(w));
  const fewStopWords = stopWordsInSlug.length <= 1;
  results.details.noStopWords = {
    stopWords: stopWordsInSlug,
    points: fewStopWords ? 1 : 0,
    status: fewStopWords ? 'success' : 'warning',
    message: fewStopWords ? 'Mínimo de stop words' : `Remova stop words: ${stopWordsInSlug.join(', ')}`
  };
  results.score += results.details.noStopWords.points;

  // Readability (1 pt)
  const isReadable = /^[a-z0-9-]+$/.test(cleanSlug) && !cleanSlug.includes('--') && slugWords.length >= 2;
  results.details.readability = {
    isReadable,
    points: isReadable ? 1 : 0,
    status: isReadable ? 'success' : 'warning',
    message: isReadable ? 'Slug legível' : 'Melhore a legibilidade do slug'
  };
  results.score += results.details.readability.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Slug bem otimizado'
    : results.score >= 2
      ? 'Slug pode ser melhorado'
      : 'Otimize o slug';

  return results;
};

// ═══════════════════════════════════════════════════════════════
// 3. E-E-A-T SIGNALS (20 pts)
// ═══════════════════════════════════════════════════════════════

/**
 * Analyze Experience indicators
 */
export const analyzeExperience = (content) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {}
  };

  const text = content || '';

  // First person account / reporting (2 pts)
  const reportingMatches = EXPERIENCE_PATTERNS.filter(pattern => pattern.test(text));
  const hasReporting = reportingMatches.length >= 1;
  results.details.firstPersonAccount = {
    found: hasReporting,
    matches: reportingMatches.length,
    points: hasReporting ? 2 : 0,
    status: hasReporting ? 'success' : 'warning',
    message: hasReporting
      ? 'Indicadores de reportagem própria detectados'
      : 'Adicione indicadores de apuração própria'
  };
  results.score += results.details.firstPersonAccount.points;

  // Specific details (2 pts)
  const hasNumbers = /\d+/.test(text);
  const hasNames = /[A-Z][a-záéíóúâêîôûãõç]+\s+[A-Z][a-záéíóúâêîôûãõç]+/.test(text);
  const hasDates = /\d{1,2}\s*(de\s+)?(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)|\d{2}\/\d{2}\/\d{4}/i.test(text);
  const specificCount = [hasNumbers, hasNames, hasDates].filter(Boolean).length;
  const hasSpecificDetails = specificCount >= 2;
  results.details.specificDetails = {
    hasNumbers,
    hasNames,
    hasDates,
    points: hasSpecificDetails ? 2 : specificCount >= 1 ? 1 : 0,
    status: hasSpecificDetails ? 'success' : specificCount >= 1 ? 'warning' : 'error',
    message: hasSpecificDetails
      ? 'Detalhes específicos presentes'
      : 'Adicione números, nomes e datas específicos'
  };
  results.score += results.details.specificDetails.points;

  // Original insights (1 pt)
  const genericPhrases = /dizem\s+que|segundo\s+rumores|há\s+rumores|pode\s+ser\s+que|possivelmente/i;
  const hasGenericContent = genericPhrases.test(text);
  results.details.originalInsights = {
    isOriginal: !hasGenericContent,
    points: hasGenericContent ? 0 : 1,
    status: hasGenericContent ? 'warning' : 'success',
    message: hasGenericContent
      ? 'Evite linguagem vaga (rumores, possivelmente...)'
      : 'Conteúdo com tom original'
  };
  results.score += results.details.originalInsights.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Bons indicadores de experiência'
    : results.score >= 2
      ? 'Demonstre mais experiência no assunto'
      : 'Adicione indicadores de experiência';

  return results;
};

/**
 * Analyze Expertise signals
 */
export const analyzeExpertise = (content, hasAuthor = false) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {}
  };

  const text = content || '';

  // Author byline (1 pt)
  results.details.authorByline = {
    hasAuthor,
    points: hasAuthor ? 1 : 0,
    status: hasAuthor ? 'success' : 'warning',
    message: hasAuthor ? 'Artigo com autor identificado' : 'Considere adicionar byline do autor'
  };
  results.score += results.details.authorByline.points;

  // Sources cited (2 pts)
  const sourcePatterns = EXPERTISE_PATTERNS.sourceCitation;
  let sourceCount = 0;
  sourcePatterns.forEach(pattern => {
    const matches = text.match(pattern);
    if (matches) sourceCount += matches.length;
  });
  const hasSources = sourceCount >= 2;
  results.details.sourcesCited = {
    count: sourceCount,
    points: hasSources ? 2 : sourceCount >= 1 ? 1 : 0,
    status: hasSources ? 'success' : sourceCount >= 1 ? 'warning' : 'error',
    message: hasSources
      ? `${sourceCount} fontes citadas`
      : sourceCount >= 1
        ? 'Apenas 1 fonte citada - adicione mais'
        : 'Cite pelo menos 2 fontes credíveis'
  };
  results.score += results.details.sourcesCited.points;

  // Technical accuracy / expert quotes (2 pts)
  const expertPatterns = EXPERTISE_PATTERNS.expertQuote;
  let expertCount = 0;
  expertPatterns.forEach(pattern => {
    const matches = text.match(pattern);
    if (matches) expertCount += matches.length;
  });
  const hasExperts = expertCount >= 1;
  results.details.technicalAccuracy = {
    expertCount,
    points: hasExperts ? 2 : 0,
    status: hasExperts ? 'success' : 'warning',
    message: hasExperts
      ? `Citações de especialistas encontradas`
      : 'Inclua citações de especialistas'
  };
  results.score += results.details.technicalAccuracy.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Bons sinais de expertise'
    : results.score >= 2
      ? 'Demonstre mais expertise'
      : 'Adicione fontes e especialistas';

  return results;
};

/**
 * Analyze Authority markers
 */
export const analyzeAuthority = (content) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {}
  };

  const text = (content || '').toLowerCase();

  // Official sources (2 pts)
  const officialSourcesFound = ALL_AUTHORITY_SOURCES.filter(source => text.includes(source));
  const hasOfficialSources = officialSourcesFound.length >= 1;
  results.details.officialSources = {
    found: officialSourcesFound,
    count: officialSourcesFound.length,
    points: hasOfficialSources ? 2 : 0,
    status: hasOfficialSources ? 'success' : 'warning',
    message: hasOfficialSources
      ? `Fontes oficiais: ${officialSourcesFound.slice(0, 3).join(', ')}`
      : 'Cite fontes oficiais (governo, polícia, tribunais...)'
  };
  results.score += results.details.officialSources.points;

  // Expert quotes (2 pts)
  const reportingVerbsFound = REPORTING_VERBS.filter(verb =>
    new RegExp(`\\b${verb}\\b`, 'i').test(content || '')
  );
  const hasExpertQuotes = reportingVerbsFound.length >= 2;
  results.details.expertQuotes = {
    verbsFound: reportingVerbsFound.length,
    points: hasExpertQuotes ? 2 : reportingVerbsFound.length >= 1 ? 1 : 0,
    status: hasExpertQuotes ? 'success' : reportingVerbsFound.length >= 1 ? 'warning' : 'error',
    message: hasExpertQuotes
      ? 'Múltiplas declarações citadas'
      : 'Inclua mais declarações de fontes'
  };
  results.score += results.details.expertQuotes.points;

  // Institutional references (1 pt)
  const institutionPatterns = /\b(universidade|instituto|fundação|associação|confederação|federação|ministério)\s+[A-Za-z]/i;
  const hasInstitutions = institutionPatterns.test(content || '');
  results.details.institutionalRefs = {
    found: hasInstitutions,
    points: hasInstitutions ? 1 : 0,
    status: hasInstitutions ? 'success' : 'neutral',
    message: hasInstitutions
      ? 'Referências institucionais presentes'
      : 'Considere citar instituições reconhecidas'
  };
  results.score += results.details.institutionalRefs.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Bons marcadores de autoridade'
    : results.score >= 2
      ? 'Aumente a autoridade do conteúdo'
      : 'Adicione fontes oficiais e institucionais';

  return results;
};

/**
 * Analyze Trust elements
 */
export const analyzeTrust = (content, title) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {}
  };

  const text = content || '';

  // Factual claims (2 pts)
  let factualCount = 0;
  TRUST_SIGNALS.factualClaims.forEach(pattern => {
    const matches = text.match(pattern);
    if (matches) factualCount += matches.length;
  });
  const hasFactualClaims = factualCount >= 2;
  results.details.factualClaims = {
    count: factualCount,
    points: hasFactualClaims ? 2 : factualCount >= 1 ? 1 : 0,
    status: hasFactualClaims ? 'success' : factualCount >= 1 ? 'warning' : 'error',
    message: hasFactualClaims
      ? 'Afirmações baseadas em dados'
      : 'Fundamente afirmações com dados'
  };
  results.score += results.details.factualClaims.points;

  // Balanced perspective (1 pt)
  let balanceCount = 0;
  TRUST_SIGNALS.multipleViewpoints.forEach(pattern => {
    if (pattern.test(text)) balanceCount++;
  });
  const hasBalance = balanceCount >= 1;
  results.details.balancedPerspective = {
    indicators: balanceCount,
    points: hasBalance ? 1 : 0,
    status: hasBalance ? 'success' : 'neutral',
    message: hasBalance
      ? 'Múltiplos pontos de vista apresentados'
      : 'Considere apresentar diferentes perspectivas'
  };
  results.score += results.details.balancedPerspective.points;

  // Transparent sourcing (1 pt)
  const namedSourcePattern = /segundo\s+[A-Z][a-záéíóúâêîôûãõç]+|[A-Z][a-záéíóúâêîôûãõç]+\s+(disse|afirmou|declarou)/;
  const hasNamedSources = namedSourcePattern.test(text);
  results.details.transparentSourcing = {
    found: hasNamedSources,
    points: hasNamedSources ? 1 : 0,
    status: hasNamedSources ? 'success' : 'warning',
    message: hasNamedSources
      ? 'Fontes nomeadas'
      : 'Nomeie suas fontes quando possível'
  };
  results.score += results.details.transparentSourcing.points;

  // No clickbait (1 pt)
  const isClickbait = CLICKBAIT_PATTERNS.some(pattern => pattern.test(title || ''));
  results.details.noClickbait = {
    isClickbait,
    points: isClickbait ? 0 : 1,
    status: isClickbait ? 'error' : 'success',
    message: isClickbait
      ? 'Título pode parecer clickbait'
      : 'Título apropriado'
  };
  results.score += results.details.noClickbait.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Boa confiabilidade'
    : results.score >= 2
      ? 'Aumente a confiabilidade'
      : 'Melhore a transparência e equilíbrio';

  return results;
};

// ═══════════════════════════════════════════════════════════════
// 4. TECHNICAL EXCELLENCE (15 pts)
// ═══════════════════════════════════════════════════════════════

/**
 * Analyze internal links
 */
export const analyzeInternalLinks = (content) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {},
    links: []
  };

  // Extract links from HTML
  const linkRegex = /<a[^>]*href=["']([^"']+)["'][^>]*>(.*?)<\/a>/gi;
  const mdLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;

  let match;
  const allLinks = [];

  while ((match = linkRegex.exec(content || '')) !== null) {
    allLinks.push({ href: match[1], text: stripHtml(match[2]), type: 'html' });
  }

  while ((match = mdLinkRegex.exec(content || '')) !== null) {
    allLinks.push({ href: match[2], text: match[1], type: 'markdown' });
  }

  // Filter internal links (relative URLs or same domain)
  const internalLinks = allLinks.filter(link =>
    link.href.startsWith('/') ||
    link.href.startsWith('#') ||
    !link.href.startsWith('http')
  );

  results.links = internalLinks;

  // Has internal links (2 pts)
  const hasEnoughLinks = internalLinks.length >= 2;
  results.details.hasInternalLinks = {
    count: internalLinks.length,
    points: hasEnoughLinks ? 2 : internalLinks.length >= 1 ? 1 : 0,
    status: hasEnoughLinks ? 'success' : internalLinks.length >= 1 ? 'warning' : 'error',
    message: hasEnoughLinks
      ? `${internalLinks.length} links internos`
      : internalLinks.length >= 1
        ? 'Adicione mais links internos'
        : 'Inclua links para outros artigos'
  };
  results.score += results.details.hasInternalLinks.points;

  // Relevant anchors (2 pts)
  const genericAnchors = ['clique aqui', 'saiba mais', 'leia mais', 'aqui', 'link'];
  const descriptiveLinks = internalLinks.filter(link =>
    !genericAnchors.some(ga => link.text.toLowerCase().includes(ga)) && link.text.length > 3
  );
  const hasDescriptive = descriptiveLinks.length >= internalLinks.length * 0.8 || internalLinks.length === 0;
  results.details.relevantAnchors = {
    descriptive: descriptiveLinks.length,
    total: internalLinks.length,
    points: hasDescriptive && internalLinks.length > 0 ? 2 : descriptiveLinks.length > 0 ? 1 : 0,
    status: hasDescriptive && internalLinks.length > 0 ? 'success' : 'warning',
    message: hasDescriptive && internalLinks.length > 0
      ? 'Âncoras descritivas'
      : 'Use textos descritivos nos links'
  };
  results.score += results.details.relevantAnchors.points;

  // Distribution (1 pt)
  // Simplified: just check if there are links and they're not all at the end
  const hasDistribution = internalLinks.length >= 1;
  results.details.distribution = {
    points: hasDistribution ? 1 : 0,
    status: hasDistribution ? 'success' : 'neutral',
    message: hasDistribution
      ? 'Links distribuídos'
      : 'Distribua links ao longo do texto'
  };
  results.score += results.details.distribution.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Boa linkagem interna'
    : results.score >= 2
      ? 'Melhore a linkagem interna'
      : 'Adicione links internos';

  return results;
};

/**
 * Analyze external links
 */
export const analyzeExternalLinks = (content) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {},
    links: []
  };

  // Extract links
  const linkRegex = /<a[^>]*href=["']([^"']+)["'][^>]*>(.*?)<\/a>/gi;
  const mdLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;

  let match;
  const allLinks = [];

  while ((match = linkRegex.exec(content || '')) !== null) {
    allLinks.push({ href: match[1], text: stripHtml(match[2]) });
  }

  while ((match = mdLinkRegex.exec(content || '')) !== null) {
    allLinks.push({ href: match[2], text: match[1] });
  }

  // Filter external links
  const externalLinks = allLinks.filter(link =>
    link.href.startsWith('http://') || link.href.startsWith('https://')
  );

  results.links = externalLinks;

  // Has external refs (2 pts)
  const hasExternalRefs = externalLinks.length >= 1;
  results.details.hasExternalRefs = {
    count: externalLinks.length,
    points: hasExternalRefs ? 2 : 0,
    status: hasExternalRefs ? 'success' : 'warning',
    message: hasExternalRefs
      ? `${externalLinks.length} referências externas`
      : 'Considere adicionar links para fontes'
  };
  results.score += results.details.hasExternalRefs.points;

  // Quality sources (2 pts)
  const authorityLinks = externalLinks.filter(link =>
    ALL_AUTHORITY_DOMAINS.some(domain => link.href.includes(domain))
  );
  const hasQuality = authorityLinks.length >= 1;
  results.details.qualitySources = {
    count: authorityLinks.length,
    points: hasQuality ? 2 : externalLinks.length > 0 ? 1 : 0,
    status: hasQuality ? 'success' : externalLinks.length > 0 ? 'warning' : 'neutral',
    message: hasQuality
      ? 'Links para fontes autoritativas'
      : externalLinks.length > 0
        ? 'Prefira fontes autoritativas (.gov, .edu, .org)'
        : 'Sem links externos'
  };
  results.score += results.details.qualitySources.points;

  // Relevance (1 pt)
  const hasRelevance = externalLinks.length > 0;
  results.details.relevance = {
    points: hasRelevance ? 1 : 0,
    status: hasRelevance ? 'success' : 'neutral',
    message: hasRelevance
      ? 'Links contextuais presentes'
      : 'Adicione links relevantes ao contexto'
  };
  results.score += results.details.relevance.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Boas referências externas'
    : results.score >= 2
      ? 'Melhore as referências'
      : 'Adicione links para fontes externas';

  return results;
};

/**
 * Analyze media optimization
 */
export const analyzeMediaOptimization = (content) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {},
    images: []
  };

  // Extract images
  const imgRegex = /<img[^>]*(?:src=["']([^"']+)["'])?[^>]*(?:alt=["']([^"']*)["'])?[^>]*>/gi;
  const mdImgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;

  let match;
  const images = [];

  while ((match = imgRegex.exec(content || '')) !== null) {
    images.push({
      src: match[1] || '',
      alt: match[2] || '',
      type: 'html'
    });
  }

  while ((match = mdImgRegex.exec(content || '')) !== null) {
    images.push({
      alt: match[1] || '',
      src: match[2] || '',
      type: 'markdown'
    });
  }

  results.images = images;

  // Has images (2 pts)
  const hasImages = images.length >= 1;
  results.details.hasImages = {
    count: images.length,
    points: hasImages ? 2 : 0,
    status: hasImages ? 'success' : 'warning',
    message: hasImages
      ? `${images.length} imagem(ns) encontrada(s)`
      : 'Adicione pelo menos 1 imagem'
  };
  results.score += results.details.hasImages.points;

  // Has alt text (1 pt)
  const imagesWithAlt = images.filter(img => img.alt && img.alt.length > 5);
  const hasAltText = imagesWithAlt.length === images.length && images.length > 0;
  results.details.hasAltText = {
    withAlt: imagesWithAlt.length,
    total: images.length,
    points: hasAltText ? 1 : 0,
    status: hasAltText ? 'success' : images.length > 0 ? 'warning' : 'neutral',
    message: hasAltText
      ? 'Todas as imagens têm alt text'
      : images.length > 0
        ? `${images.length - imagesWithAlt.length} imagem(ns) sem alt text`
        : 'Sem imagens para verificar'
  };
  results.score += results.details.hasAltText.points;

  // Image relevance (1 pt)
  const descriptiveAlt = imagesWithAlt.filter(img => img.alt.split(/\s+/).length >= 3);
  const hasRelevance = descriptiveAlt.length >= 1;
  results.details.imageRelevance = {
    descriptive: descriptiveAlt.length,
    points: hasRelevance ? 1 : 0,
    status: hasRelevance ? 'success' : 'neutral',
    message: hasRelevance
      ? 'Alt text descritivo'
      : 'Use alt text mais descritivo (3+ palavras)'
  };
  results.score += results.details.imageRelevance.points;

  // Captions (1 pt)
  const captionRegex = /<figcaption[^>]*>.*?<\/figcaption>/gi;
  const hasCaptions = captionRegex.test(content || '');
  results.details.captions = {
    found: hasCaptions,
    points: hasCaptions ? 1 : 0,
    status: hasCaptions ? 'success' : 'neutral',
    message: hasCaptions
      ? 'Legendas presentes'
      : 'Considere adicionar legendas às imagens'
  };
  results.score += results.details.captions.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Mídia bem otimizada'
    : results.score >= 2
      ? 'Melhore a otimização de mídia'
      : 'Adicione e otimize imagens';

  return results;
};

// ═══════════════════════════════════════════════════════════════
// 5. AI & SERP OPTIMIZATION (10 pts)
// ═══════════════════════════════════════════════════════════════

/**
 * Analyze featured snippet readiness
 */
export const analyzeFeaturedSnippetReadiness = (content, title) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {}
  };

  const firstPara = getFirstParagraph(content);
  const firstParaWords = countWords(firstPara);

  // Direct answer (2 pts)
  const hasDirectAnswer = firstParaWords >= 30 && firstParaWords <= 80;
  results.details.directAnswer = {
    words: firstParaWords,
    ideal: '40-60',
    points: hasDirectAnswer ? 2 : firstParaWords >= 20 ? 1 : 0,
    status: hasDirectAnswer ? 'success' : firstParaWords >= 20 ? 'warning' : 'error',
    message: hasDirectAnswer
      ? 'Primeiro parágrafo com tamanho ideal para snippet'
      : firstParaWords < 30
        ? 'Primeiro parágrafo muito curto para snippet'
        : 'Primeiro parágrafo muito longo para snippet'
  };
  results.score += results.details.directAnswer.points;

  // Has list (1 pt)
  const hasList = STRUCTURE_PATTERNS.bulletList.test(content || '') ||
                  STRUCTURE_PATTERNS.numberedList.test(content || '') ||
                  STRUCTURE_PATTERNS.markdown.bulletList.test(content || '') ||
                  STRUCTURE_PATTERNS.markdown.numberedList.test(content || '');
  results.details.hasList = {
    found: hasList,
    points: hasList ? 1 : 0,
    status: hasList ? 'success' : 'neutral',
    message: hasList
      ? 'Lista estruturada presente'
      : 'Adicione listas para snippets de lista'
  };
  results.score += results.details.hasList.points;

  // Has table (1 pt)
  const hasTable = STRUCTURE_PATTERNS.table.test(content || '');
  results.details.hasTable = {
    found: hasTable,
    points: hasTable ? 1 : 0,
    status: hasTable ? 'success' : 'neutral',
    message: hasTable
      ? 'Tabela presente'
      : 'Tabelas ajudam em snippets de comparação'
  };
  results.score += results.details.hasTable.points;

  // Concise answer (1 pt)
  const idealAnswer = firstParaWords >= 40 && firstParaWords <= 60;
  results.details.conciseAnswer = {
    isIdeal: idealAnswer,
    points: idealAnswer ? 1 : 0,
    status: idealAnswer ? 'success' : 'neutral',
    message: idealAnswer
      ? 'Resposta concisa (40-60 palavras)'
      : `Ajuste para 40-60 palavras (atual: ${firstParaWords})`
  };
  results.score += results.details.conciseAnswer.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Pronto para Featured Snippet'
    : results.score >= 2
      ? 'Otimize para Featured Snippet'
      : 'Melhore estrutura para snippets';

  return results;
};

/**
 * Analyze AI Overview optimization
 */
export const analyzeAIOverviewOptimization = (content, title) => {
  const results = {
    score: 0,
    maxScore: 5,
    details: {}
  };

  const text = content || '';

  // Clear structure (2 pts)
  const hasHeadings = /<h[2-4][^>]*>/i.test(text) || /^#{2,4}\s+/m.test(text);
  const hasParagraphs = countParagraphs(text) >= 3;
  const hasStructure = hasHeadings && hasParagraphs;
  results.details.clearStructure = {
    hasHeadings,
    hasParagraphs,
    points: hasStructure ? 2 : (hasHeadings || hasParagraphs) ? 1 : 0,
    status: hasStructure ? 'success' : 'warning',
    message: hasStructure
      ? 'Estrutura clara e lógica'
      : 'Melhore a estrutura com subtítulos e parágrafos'
  };
  results.score += results.details.clearStructure.points;

  // Factual statements (1 pt)
  const hasNumbers = /\d+%?|\bR\$\s*[\d.,]+|\d{4}/.test(text);
  const hasDates = /\d{1,2}\s*(de\s+)?(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)|\d{2}\/\d{2}\/\d{4}/i.test(text);
  const hasFactual = hasNumbers || hasDates;
  results.details.factualStatements = {
    hasNumbers,
    hasDates,
    points: hasFactual ? 1 : 0,
    status: hasFactual ? 'success' : 'warning',
    message: hasFactual
      ? 'Dados verificáveis presentes'
      : 'Adicione números, datas e fatos específicos'
  };
  results.score += results.details.factualStatements.points;

  // Concise/summarizable (1 pt)
  const wordCount = countWords(text);
  const sentenceCount = countSentences(text);
  const avgSentenceLength = sentenceCount > 0 ? wordCount / sentenceCount : 0;
  const isConcise = avgSentenceLength <= 25;
  results.details.conciseSummary = {
    avgSentenceLength: Math.round(avgSentenceLength),
    points: isConcise ? 1 : 0,
    status: isConcise ? 'success' : 'warning',
    message: isConcise
      ? 'Conteúdo resumível'
      : 'Frases muito longas dificultam resumo por IA'
  };
  results.score += results.details.conciseSummary.points;

  // No misleading/clickbait (1 pt)
  const isClickbait = CLICKBAIT_PATTERNS.some(pattern => pattern.test(title || ''));
  const hasExcessiveEmoji = /[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]/gu.test(title || '');
  const isClean = !isClickbait && !hasExcessiveEmoji;
  results.details.noMisleading = {
    isClickbait,
    hasExcessiveEmoji,
    points: isClean ? 1 : 0,
    status: isClean ? 'success' : 'warning',
    message: isClean
      ? 'Tom neutro e informativo'
      : 'Evite sensacionalismo e clickbait'
  };
  results.score += results.details.noMisleading.points;

  // Overall status
  results.status = results.score >= 4 ? 'success' : results.score >= 2 ? 'warning' : 'error';
  results.message = results.score >= 4
    ? 'Otimizado para AI Overview'
    : results.score >= 2
      ? 'Melhore para AI Overview'
      : 'Otimize conteúdo para IA';

  return results;
};

// ═══════════════════════════════════════════════════════════════
// MAIN SEO ANALYSIS FUNCTION
// ═══════════════════════════════════════════════════════════════

/**
 * Perform complete SEO analysis
 */
export const performSEOAnalysis = ({
  title = '',
  tituloCurto = '',
  linhaFina = '',
  content = '',
  tags = [],
  slug = '',
  articleType = 'default',
  targetKeyword = '',
  hasAuthor = false
}) => {
  // Derive target keyword from title if not provided
  const effectiveKeyword = targetKeyword || (title ? title.split(/\s+/).slice(0, 3).join(' ') : '');

  // 1. Content Quality (30 pts)
  const contentDepth = analyzeContentDepth(content, articleType);
  const contentStructure = analyzeContentStructure(content);
  const readability = analyzeReadability(content);

  const contentQualityScore = contentDepth.score + contentStructure.score + readability.score;
  const contentQuality = {
    score: contentQualityScore,
    maxScore: CATEGORY_WEIGHTS.contentQuality.total,
    status: contentQualityScore >= 24 ? 'success' : contentQualityScore >= 15 ? 'warning' : 'error',
    metrics: {
      wordCountDepth: contentDepth,
      contentStructure,
      readability
    }
  };

  // 2. On-Page Optimization (25 pts)
  const titleOptimization = analyzeTitleOptimization(title, content, effectiveKeyword);
  const metaDescription = analyzeMetaDescription(linhaFina, title, effectiveKeyword);
  const keywordStrategy = analyzeKeywordStrategy(content, title, effectiveKeyword);
  const urlSlug = analyzeSlug(slug, title, effectiveKeyword);

  // Short title (titulo curto) optimization - informational metric (0 pts, not scored)
  const shortTitleLen = tituloCurto?.length || 0;
  let shortTitleStatus = 'neutral';
  let shortTitleMessage = 'Título curto não definido. Recomendado para feeds e redes sociais.';
  if (shortTitleLen > 0 && shortTitleLen <= 70) {
    shortTitleStatus = 'success';
    shortTitleMessage = `Título curto com ${shortTitleLen} caracteres (ideal: até 70)`;
  } else if (shortTitleLen > 70) {
    shortTitleStatus = 'error';
    shortTitleMessage = `Título curto muito longo: ${shortTitleLen} caracteres (máximo: 70)`;
  } else {
    shortTitleStatus = 'warning';
  }
  const shortTitleOptimization = {
    score: 0,
    maxScore: 0,
    status: shortTitleStatus,
    message: shortTitleMessage,
    details: {
      length: shortTitleLen,
      maxLength: 70
    }
  };

  const onPageScore = titleOptimization.score + metaDescription.score + keywordStrategy.score + urlSlug.score;
  const onPageOptimization = {
    score: onPageScore,
    maxScore: CATEGORY_WEIGHTS.onPageOptimization.total,
    status: onPageScore >= 20 ? 'success' : onPageScore >= 12 ? 'warning' : 'error',
    metrics: {
      titleOptimization,
      shortTitleOptimization,
      metaDescription,
      keywordStrategy,
      urlSlug
    }
  };

  // 3. E-E-A-T Signals (20 pts)
  const experience = analyzeExperience(content);
  const expertise = analyzeExpertise(content, hasAuthor);
  const authority = analyzeAuthority(content);
  const trust = analyzeTrust(content, title);

  const eeatScore = experience.score + expertise.score + authority.score + trust.score;
  const eeatSignals = {
    score: eeatScore,
    maxScore: CATEGORY_WEIGHTS.eeatSignals.total,
    status: eeatScore >= 16 ? 'success' : eeatScore >= 10 ? 'warning' : 'error',
    metrics: {
      experience,
      expertise,
      authority,
      trust
    }
  };

  // 4. Technical Excellence (5 pts scored + manual actions)
  // internalLinks and mediaOptimization are analyzed but NOT scored
  // (features not yet available in the tool) - shown as manual tasks only
  const internalLinks = analyzeInternalLinks(content);
  const externalLinks = analyzeExternalLinks(content);
  const mediaOptimization = analyzeMediaOptimization(content);

  const technicalScore = externalLinks.score; // Only external links count in score
  const technicalExcellence = {
    score: technicalScore,
    maxScore: CATEGORY_WEIGHTS.technicalExcellence.total,
    status: technicalScore >= 4 ? 'success' : technicalScore >= 2 ? 'warning' : 'error',
    metrics: {
      internalLinks,
      externalLinks,
      mediaOptimization
    }
  };

  // 5. AI & SERP Optimization (10 pts)
  const featuredSnippet = analyzeFeaturedSnippetReadiness(content, title);
  const aiOverview = analyzeAIOverviewOptimization(content, title);

  const aiSerpScore = featuredSnippet.score + aiOverview.score;
  const aiSerpOptimization = {
    score: aiSerpScore,
    maxScore: CATEGORY_WEIGHTS.aiSerpOptimization.total,
    status: aiSerpScore >= 8 ? 'success' : aiSerpScore >= 5 ? 'warning' : 'error',
    metrics: {
      featuredSnippet,
      aiOverview
    }
  };

  // Total Score (raw max is 90 since internalLinks and mediaOptimization are excluded)
  // Normalize to 0-100 scale for consistent display
  const rawScore = contentQualityScore + onPageScore + eeatScore + technicalScore + aiSerpScore;
  const maxRawScore = 90;
  const totalScore = Math.round((rawScore / maxRawScore) * 100);

  // Generate priority recommendations
  const recommendations = generateRecommendations({
    contentQuality,
    onPageOptimization,
    eeatSignals,
    technicalExcellence,
    aiSerpOptimization
  });

  return {
    score: totalScore,
    maxScore: 100,
    status: totalScore >= 80 ? 'success' : totalScore >= 60 ? 'warning' : totalScore >= 40 ? 'warning' : 'error',
    label: totalScore >= 80 ? 'Excelente' : totalScore >= 60 ? 'Bom' : totalScore >= 40 ? 'Regular' : 'Crítico',
    categories: {
      contentQuality,
      onPageOptimization,
      eeatSignals,
      technicalExcellence,
      aiSerpOptimization
    },
    recommendations,
    keywords: keywordStrategy.keywords || []
  };
};

/**
 * Generate priority recommendations based on analysis
 */
const generateRecommendations = (categories) => {
  const recommendations = [];

  // Check each category for improvement opportunities
  Object.entries(categories).forEach(([categoryKey, category]) => {
    if (category.status !== 'success') {
      Object.entries(category.metrics).forEach(([metricKey, metric]) => {
        if (metric.status === 'error' || (metric.status === 'warning' && metric.score < metric.maxScore * 0.5)) {
          recommendations.push({
            category: categoryKey,
            metric: metricKey,
            priority: metric.status === 'error' ? 'high' : 'medium',
            message: metric.message,
            pointsAvailable: metric.maxScore - metric.score,
            currentScore: metric.score,
            maxScore: metric.maxScore
          });
        }
      });
    }
  });

  // Sort by points available (highest impact first)
  recommendations.sort((a, b) => b.pointsAvailable - a.pointsAvailable);

  return recommendations.slice(0, 5); // Return top 5 recommendations
};

/**
 * Quick SEO score calculation (for use in other components)
 */
export const calculateSEOScore = ({ title, linhaFina, content, tags, slug, articleType, targetKeyword, hasAuthor }) => {
  const analysis = performSEOAnalysis({
    title,
    linhaFina,
    content,
    tags,
    slug,
    articleType,
    targetKeyword,
    hasAuthor
  });
  return analysis.score;
};

export default {
  performSEOAnalysis,
  calculateSEOScore,
  stripHtml,
  countWords,
  countSentences,
  countParagraphs,
  analyzeContentDepth,
  analyzeContentStructure,
  analyzeReadability,
  analyzeTitleOptimization,
  analyzeMetaDescription,
  analyzeKeywordStrategy,
  analyzeSlug,
  analyzeExperience,
  analyzeExpertise,
  analyzeAuthority,
  analyzeTrust,
  analyzeInternalLinks,
  analyzeExternalLinks,
  analyzeMediaOptimization,
  analyzeFeaturedSnippetReadiness,
  analyzeAIOverviewOptimization
};
