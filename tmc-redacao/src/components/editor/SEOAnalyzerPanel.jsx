import { useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  CheckCircle2,
  AlertCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Type,
  FileText,
  BarChart3,
  BookOpen,
  Link2,
  Image,
  Sparkles,
  Target,
  Lightbulb
} from 'lucide-react';
import { useState } from 'react';

/**
 * SEOAnalyzerPanel - Painel de análise SEO em tempo real
 *
 * Mostra métricas de SEO para redatores otimizarem suas matérias
 */

// Função para calcular score de legibilidade (Flesch-Kincaid simplificado)
const calculateReadability = (text) => {
  if (!text || text.trim().length === 0) return { score: 0, grade: 'N/A', level: 'neutral' };

  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
  const words = text.split(/\s+/).filter(w => w.length > 0);
  const syllables = words.reduce((count, word) => {
    // Estimativa simplificada de sílabas em português
    const vowels = word.toLowerCase().match(/[aeiouáéíóúâêîôûãõ]/g);
    return count + (vowels ? vowels.length : 1);
  }, 0);

  if (sentences.length === 0 || words.length === 0) return { score: 0, grade: 'N/A', level: 'neutral' };

  const avgWordsPerSentence = words.length / sentences.length;
  const avgSyllablesPerWord = syllables / words.length;

  // Flesch Reading Ease adaptado
  const score = Math.round(206.835 - (1.015 * avgWordsPerSentence) - (84.6 * avgSyllablesPerWord));
  const clampedScore = Math.max(0, Math.min(100, score));

  let grade, level;
  if (clampedScore >= 80) { grade = 'Muito Fácil'; level = 'success'; }
  else if (clampedScore >= 60) { grade = 'Fácil'; level = 'success'; }
  else if (clampedScore >= 40) { grade = 'Moderado'; level = 'warning'; }
  else if (clampedScore >= 20) { grade = 'Difícil'; level = 'warning'; }
  else { grade = 'Muito Difícil'; level = 'error'; }

  return { score: clampedScore, grade, level };
};

// Função para extrair palavras-chave e calcular densidade
const analyzeKeywords = (text, title) => {
  if (!text || text.trim().length === 0) return [];

  const words = text.toLowerCase().split(/\s+/).filter(w => w.length > 4);
  const titleWords = title ? title.toLowerCase().split(/\s+/).filter(w => w.length > 4) : [];

  // Contar frequência
  const frequency = {};
  words.forEach(word => {
    const cleanWord = word.replace(/[^a-záéíóúâêîôûãõç]/g, '');
    if (cleanWord.length > 4) {
      frequency[cleanWord] = (frequency[cleanWord] || 0) + 1;
    }
  });

  // Ordenar por frequência e pegar top 5
  const sorted = Object.entries(frequency)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([word, count]) => ({
      word,
      count,
      density: ((count / words.length) * 100).toFixed(1),
      inTitle: titleWords.includes(word)
    }));

  return sorted;
};

// Componente de indicador de status
const StatusIndicator = ({ status, size = 16 }) => {
  const icons = {
    success: <CheckCircle2 size={size} className="text-success" />,
    warning: <AlertCircle size={size} className="text-warning" />,
    error: <XCircle size={size} className="text-error" />,
    neutral: <div className={`w-${size/4} h-${size/4} rounded-full bg-light-gray`} />
  };
  return icons[status] || icons.neutral;
};

StatusIndicator.propTypes = {
  status: PropTypes.oneOf(['success', 'warning', 'error', 'neutral']),
  size: PropTypes.number
};

// Componente de barra de progresso
const ProgressBar = ({ value, max, showLabel = true, size = 'md' }) => {
  const percentage = Math.min(100, (value / max) * 100);

  let color = 'bg-success';
  if (percentage < 50) color = 'bg-error';
  else if (percentage < 80) color = 'bg-warning';

  const heights = { sm: 'h-1', md: 'h-2', lg: 'h-3' };

  return (
    <div className="w-full">
      <div className={`w-full bg-off-white rounded-full overflow-hidden ${heights[size]}`}>
        <div
          className={`${heights[size]} ${color} rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-between mt-1">
          <span className="text-xs text-medium-gray">{value}</span>
          <span className="text-xs text-medium-gray">{max}</span>
        </div>
      )}
    </div>
  );
};

ProgressBar.propTypes = {
  value: PropTypes.number.isRequired,
  max: PropTypes.number.isRequired,
  showLabel: PropTypes.bool,
  size: PropTypes.oneOf(['sm', 'md', 'lg'])
};

// Componente de card de métrica
const MetricCard = ({ title, icon: Icon, children, defaultExpanded = true }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="bg-off-white rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-light-gray/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon size={14} className="text-medium-gray" />
          <span className="text-xs font-semibold text-dark-gray uppercase tracking-wide">{title}</span>
        </div>
        {isExpanded ? (
          <ChevronUp size={14} className="text-medium-gray" />
        ) : (
          <ChevronDown size={14} className="text-medium-gray" />
        )}
      </button>
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2">
          {children}
        </div>
      )}
    </div>
  );
};

MetricCard.propTypes = {
  title: PropTypes.string.isRequired,
  icon: PropTypes.elementType.isRequired,
  children: PropTypes.node.isRequired,
  defaultExpanded: PropTypes.bool
};

// Componente de item de checklist
const CheckItem = ({ status, children }) => (
  <div className="flex items-start gap-2">
    <StatusIndicator status={status} size={14} />
    <span className={`text-xs ${status === 'success' ? 'text-dark-gray' : status === 'warning' ? 'text-warning' : 'text-error'}`}>
      {children}
    </span>
  </div>
);

CheckItem.propTypes = {
  status: PropTypes.oneOf(['success', 'warning', 'error']).isRequired,
  children: PropTypes.node.isRequired
};

// Componente principal
const SEOAnalyzerPanel = ({ title, linhaFina, content, tags, onOptimizeWithAI }) => {
  // Calcular métricas
  const metrics = useMemo(() => {
    const titleLength = title?.length || 0;
    const linhaFinaLength = linhaFina?.length || 0;
    const wordCount = content?.split(/\s+/).filter(Boolean).length || 0;
    const readability = calculateReadability(content);
    const keywords = analyzeKeywords(content, title);

    // Análise de estrutura
    const hasImages = /<img|!\[/.test(content || '');
    const hasLinks = /<a |https?:\/\/|\[.*\]\(/.test(content || '');
    const paragraphs = (content || '').split(/\n\n+/).filter(p => p.trim().length > 0);
    const sentences = (content || '').split(/[.!?]+/).filter(s => s.trim().length > 0);
    const longSentences = sentences.filter(s => s.split(/\s+/).length > 40).length;

    // Calcular score geral
    let score = 0;

    // Título (20 pontos)
    if (titleLength >= 50 && titleLength <= 60) score += 20;
    else if (titleLength >= 40 && titleLength <= 70) score += 15;
    else if (titleLength > 0) score += 5;

    // Linha fina / Meta description (20 pontos)
    if (linhaFinaLength >= 150 && linhaFinaLength <= 160) score += 20;
    else if (linhaFinaLength >= 120 && linhaFinaLength <= 180) score += 15;
    else if (linhaFinaLength >= 80) score += 10;
    else if (linhaFinaLength > 0) score += 5;

    // Conteúdo (20 pontos)
    if (wordCount >= 800) score += 20;
    else if (wordCount >= 600) score += 15;
    else if (wordCount >= 400) score += 10;
    else if (wordCount >= 200) score += 5;

    // Legibilidade (15 pontos)
    if (readability.level === 'success') score += 15;
    else if (readability.level === 'warning') score += 8;

    // Palavras-chave (10 pontos)
    const hasKeywordInTitle = keywords.some(k => k.inTitle);
    if (hasKeywordInTitle) score += 10;
    else if (keywords.length > 0) score += 5;

    // Estrutura (15 pontos)
    if (hasImages) score += 5;
    if (hasLinks) score += 5;
    if (tags?.length >= 3) score += 5;

    return {
      score,
      titleLength,
      linhaFinaLength,
      wordCount,
      readability,
      keywords,
      hasImages,
      hasLinks,
      paragraphs: paragraphs.length,
      longSentences,
      avgWordsPerSentence: sentences.length > 0 ? Math.round(wordCount / sentences.length) : 0
    };
  }, [title, linhaFina, content, tags]);

  // Determinar cor do score
  const getScoreColor = (score) => {
    if (score >= 80) return 'text-success';
    if (score >= 50) return 'text-warning';
    return 'text-error';
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return 'Excelente';
    if (score >= 60) return 'Bom';
    if (score >= 40) return 'Regular';
    return 'Precisa melhorar';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Score Principal */}
      <div className="bg-gradient-to-br from-off-white to-light-gray/30 rounded-xl p-4 mb-4">
        <div className="text-center">
          <p className="text-xs text-medium-gray uppercase tracking-wider mb-2">Score SEO</p>
          <div className="flex items-baseline justify-center gap-1">
            <span className={`text-4xl font-bold ${getScoreColor(metrics.score)}`}>
              {metrics.score}
            </span>
            <span className="text-lg text-medium-gray">/100</span>
          </div>
          <p className={`text-sm font-medium mt-1 ${getScoreColor(metrics.score)}`}>
            {getScoreLabel(metrics.score)}
          </p>
        </div>

        {/* Barra de progresso circular visual */}
        <div className="mt-3">
          <div className="w-full bg-white rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                metrics.score >= 80 ? 'bg-success' : metrics.score >= 50 ? 'bg-warning' : 'bg-error'
              }`}
              style={{ width: `${metrics.score}%` }}
            />
          </div>
        </div>

        {/* Legenda */}
        <div className="flex justify-center gap-4 mt-3 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-success" />
            Bom
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-warning" />
            Atenção
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-error" />
            Crítico
          </span>
        </div>
      </div>

      {/* Métricas Detalhadas */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {/* Título */}
        <MetricCard title="Título" icon={Type}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-sm font-medium ${
              metrics.titleLength >= 50 && metrics.titleLength <= 60 ? 'text-success' :
              metrics.titleLength >= 40 && metrics.titleLength <= 70 ? 'text-warning' : 'text-error'
            }`}>
              {metrics.titleLength}/60 caracteres
            </span>
            <StatusIndicator
              status={
                metrics.titleLength >= 50 && metrics.titleLength <= 60 ? 'success' :
                metrics.titleLength >= 40 && metrics.titleLength <= 70 ? 'warning' : 'error'
              }
            />
          </div>
          <ProgressBar value={metrics.titleLength} max={60} showLabel={false} size="sm" />
          <div className="mt-2 space-y-1">
            {metrics.titleLength === 0 && (
              <CheckItem status="error">Adicione um título</CheckItem>
            )}
            {metrics.titleLength > 0 && metrics.titleLength < 50 && (
              <CheckItem status="warning">Título curto - ideal: 50-60 caracteres</CheckItem>
            )}
            {metrics.titleLength > 60 && (
              <CheckItem status="warning">Título longo - pode ser cortado no Google</CheckItem>
            )}
            {metrics.titleLength >= 50 && metrics.titleLength <= 60 && (
              <CheckItem status="success">Comprimento ideal para SEO</CheckItem>
            )}
          </div>
        </MetricCard>

        {/* Meta Description (Linha Fina) */}
        <MetricCard title="Meta Description" icon={FileText}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-sm font-medium ${
              metrics.linhaFinaLength >= 150 && metrics.linhaFinaLength <= 160 ? 'text-success' :
              metrics.linhaFinaLength >= 120 ? 'text-warning' : 'text-error'
            }`}>
              {metrics.linhaFinaLength}/160 caracteres
            </span>
            <StatusIndicator
              status={
                metrics.linhaFinaLength >= 150 && metrics.linhaFinaLength <= 160 ? 'success' :
                metrics.linhaFinaLength >= 120 ? 'warning' : 'error'
              }
            />
          </div>
          <ProgressBar value={metrics.linhaFinaLength} max={160} showLabel={false} size="sm" />
          <div className="mt-2 space-y-1">
            {metrics.linhaFinaLength === 0 && (
              <CheckItem status="error">Adicione uma linha fina (meta description)</CheckItem>
            )}
            {metrics.linhaFinaLength > 0 && metrics.linhaFinaLength < 120 && (
              <CheckItem status="warning">Muito curta - adicione mais contexto</CheckItem>
            )}
            {metrics.linhaFinaLength > 160 && (
              <CheckItem status="warning">Muito longa - será cortada nos resultados</CheckItem>
            )}
            {metrics.linhaFinaLength >= 150 && metrics.linhaFinaLength <= 160 && (
              <CheckItem status="success">Comprimento ideal</CheckItem>
            )}
          </div>
        </MetricCard>

        {/* Palavras-chave */}
        <MetricCard title="Palavras-chave" icon={Target} defaultExpanded={false}>
          {metrics.keywords.length > 0 ? (
            <div className="space-y-2">
              {metrics.keywords.map((kw, index) => (
                <div key={index} className="flex items-center justify-between text-xs">
                  <span className="text-dark-gray font-medium truncate max-w-[120px]">
                    "{kw.word}"
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-medium-gray">{kw.count}x ({kw.density}%)</span>
                    {kw.inTitle && (
                      <span className="px-1.5 py-0.5 bg-success/10 text-success text-[10px] rounded">
                        no título
                      </span>
                    )}
                  </div>
                </div>
              ))}
              <p className="text-xs text-medium-gray mt-2">
                Densidade ideal: 1-3% por palavra-chave
              </p>
            </div>
          ) : (
            <p className="text-xs text-medium-gray">
              Adicione conteúdo para analisar palavras-chave
            </p>
          )}
        </MetricCard>

        {/* Legibilidade */}
        <MetricCard title="Legibilidade" icon={BookOpen}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-sm font-medium ${
              metrics.readability.level === 'success' ? 'text-success' :
              metrics.readability.level === 'warning' ? 'text-warning' : 'text-error'
            }`}>
              {metrics.readability.grade}
            </span>
            <StatusIndicator status={metrics.readability.level} />
          </div>
          <div className="space-y-1 mt-2">
            <CheckItem status={metrics.avgWordsPerSentence <= 25 ? 'success' : 'warning'}>
              Média de {metrics.avgWordsPerSentence} palavras/frase
            </CheckItem>
            {metrics.longSentences > 0 && (
              <CheckItem status="warning">
                {metrics.longSentences} frase(s) muito longa(s)
              </CheckItem>
            )}
            <CheckItem status={metrics.paragraphs >= 3 ? 'success' : 'warning'}>
              {metrics.paragraphs} parágrafo(s)
            </CheckItem>
          </div>
        </MetricCard>

        {/* Estrutura do Conteúdo */}
        <MetricCard title="Estrutura" icon={BarChart3}>
          <div className="flex items-center justify-between mb-2">
            <span className={`text-sm font-medium ${
              metrics.wordCount >= 600 ? 'text-success' :
              metrics.wordCount >= 300 ? 'text-warning' : 'text-error'
            }`}>
              {metrics.wordCount} palavras
            </span>
            <span className="text-xs text-medium-gray">min: 600</span>
          </div>
          <ProgressBar value={metrics.wordCount} max={600} showLabel={false} size="sm" />
          <div className="space-y-1 mt-2">
            <CheckItem status={metrics.hasImages ? 'success' : 'warning'}>
              {metrics.hasImages ? 'Contém imagens' : 'Adicione imagens'}
            </CheckItem>
            <CheckItem status={metrics.hasLinks ? 'success' : 'warning'}>
              {metrics.hasLinks ? 'Contém links' : 'Adicione links de referência'}
            </CheckItem>
            <CheckItem status={tags?.length >= 3 ? 'success' : 'warning'}>
              {tags?.length || 0} tópico(s) - ideal: 3-5
            </CheckItem>
          </div>
        </MetricCard>
      </div>

      {/* Botão de Otimização */}
      {metrics.score < 80 && onOptimizeWithAI && (
        <div className="mt-4 pt-4 border-t border-light-gray">
          <button
            onClick={onOptimizeWithAI}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-tmc-orange to-orange-500 text-white text-sm font-medium rounded-lg hover:from-tmc-orange/90 hover:to-orange-500/90 transition-all shadow-sm"
          >
            <Sparkles size={16} />
            Otimizar com IA
          </button>
          <p className="text-xs text-medium-gray text-center mt-2">
            A IA pode sugerir melhorias para título, descrição e conteúdo
          </p>
        </div>
      )}
    </div>
  );
};

SEOAnalyzerPanel.propTypes = {
  title: PropTypes.string,
  linhaFina: PropTypes.string,
  content: PropTypes.string,
  tags: PropTypes.arrayOf(PropTypes.string),
  onOptimizeWithAI: PropTypes.func
};

export default SEOAnalyzerPanel;
