import { useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Check,
  AlertTriangle,
  X,
  Type,
  FileText,
  BarChart2,
  BookOpen,
  Link2,
  Image,
  Sparkles,
  Target,
  Hash,
  TrendingUp
} from 'lucide-react';

/**
 * SEOAnalyzerPanel - Painel de análise SEO em tempo real (v2 - Redesign)
 *
 * Design consistente com o padrão visual TMC
 */

// Função para calcular score de legibilidade (Adaptado para Português Brasileiro)
// Baseado no Índice de Legibilidade de Flesch adaptado por Martins et al.
const calculateReadability = (text) => {
  if (!text || text.trim().length === 0) return { score: 0, grade: 'N/A', level: 'neutral', tip: null, avgWordsPerSentence: 0 };

  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
  const words = text.split(/\s+/).filter(w => w.length > 0);

  // Contagem de sílabas adaptada para português
  const countSyllables = (word) => {
    const cleanWord = word.toLowerCase().replace(/[^a-záéíóúâêîôûãõç]/g, '');
    if (cleanWord.length <= 2) return 1;

    // Padrões de vogais em português (incluindo ditongos e tritongos)
    const vowelGroups = cleanWord.match(/[aeiouáéíóúâêîôûãõ]+/g);
    if (!vowelGroups) return 1;

    let syllableCount = vowelGroups.length;

    // Ajuste para ditongos comuns (contam como 1 sílaba, não 2)
    const ditongos = (cleanWord.match(/ai|au|ei|eu|oi|ou|ui|ão|ãe|õe/g) || []).length;
    syllableCount -= ditongos * 0.5; // Reduz parcialmente

    return Math.max(1, Math.round(syllableCount));
  };

  const totalSyllables = words.reduce((count, word) => count + countSyllables(word), 0);

  if (sentences.length === 0 || words.length === 0) return { score: 0, grade: 'N/A', level: 'neutral', tip: null, avgWordsPerSentence: 0 };

  const avgWordsPerSentence = words.length / sentences.length;
  const avgSyllablesPerWord = totalSyllables / words.length;

  // Fórmula adaptada para português brasileiro
  // Coeficiente de sílabas reduzido (62 vs 84.6) para compensar palavras mais longas
  const score = Math.round(248.835 - (1.015 * avgWordsPerSentence) - (84.6 * avgSyllablesPerWord));
  const clampedScore = Math.max(0, Math.min(100, score));

  let grade, level, tip;
  if (clampedScore >= 80) {
    grade = 'Muito Fácil';
    level = 'success';
    tip = 'Excelente! Texto acessível para todos os públicos.';
  }
  else if (clampedScore >= 60) {
    grade = 'Fácil';
    level = 'success';
    tip = 'Bom! Texto claro e de fácil compreensão.';
  }
  else if (clampedScore >= 40) {
    grade = 'Moderado';
    level = 'warning';
    tip = 'Tente usar frases mais curtas e palavras simples.';
  }
  else if (clampedScore >= 20) {
    grade = 'Difícil';
    level = 'warning';
    tip = 'Simplifique: frases menores, menos jargões.';
  }
  else {
    grade = 'Muito Difícil';
    level = 'error';
    tip = 'Texto complexo. Divida frases longas e use vocabulário acessível.';
  }

  return { score: clampedScore, grade, level, tip, avgWordsPerSentence };
};

// Função para extrair palavras-chave
const analyzeKeywords = (text, title) => {
  if (!text || text.trim().length === 0) return [];

  const words = text.toLowerCase().split(/\s+/).filter(w => w.length > 4);
  const titleWords = title ? title.toLowerCase().split(/\s+/).filter(w => w.length > 4) : [];

  const frequency = {};
  words.forEach(word => {
    const cleanWord = word.replace(/[^a-záéíóúâêîôûãõç]/g, '');
    if (cleanWord.length > 4) {
      frequency[cleanWord] = (frequency[cleanWord] || 0) + 1;
    }
  });

  return Object.entries(frequency)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([word, count]) => {
      const density = (count / words.length) * 100;
      const densityFormatted = density.toFixed(1);

      // Status baseado na densidade ideal (1-3%)
      let status = 'warning';
      if (density >= 1 && density <= 3) status = 'success';
      else if (density > 3) status = 'error'; // over-optimization
      else if (density < 1) status = 'warning'; // pode aumentar

      return {
        word,
        count,
        density: densityFormatted,
        densityValue: density,
        status,
        inTitle: titleWords.includes(word)
      };
    });
};

// Componente Gauge Circular
const CircularGauge = ({ value, size = 120 }) => {
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const progress = (value / 100) * circumference;
  const offset = circumference - progress;

  // Cores baseadas no score
  let strokeColor = '#EF4444'; // error
  let bgGradient = 'from-red-50 to-red-100';
  let label = 'Crítico';

  if (value >= 80) {
    strokeColor = '#10B981'; // success
    bgGradient = 'from-emerald-50 to-emerald-100';
    label = 'Excelente';
  } else if (value >= 60) {
    strokeColor = '#F59E0B'; // warning
    bgGradient = 'from-amber-50 to-amber-100';
    label = 'Bom';
  } else if (value >= 40) {
    strokeColor = '#F59E0B';
    bgGradient = 'from-amber-50 to-amber-100';
    label = 'Regular';
  }

  return (
    <div className={`relative inline-flex items-center justify-center bg-gradient-to-br ${bgGradient} rounded-full p-2`}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-dark-gray">{value}</span>
        <span className="text-[10px] text-medium-gray uppercase tracking-wider">{label}</span>
      </div>
    </div>
  );
};

CircularGauge.propTypes = {
  value: PropTypes.number.isRequired,
  size: PropTypes.number
};

// Componente de Mini Barra de Progresso
const MiniProgress = ({ value, max, variant = 'default' }) => {
  const percentage = Math.min(100, (value / max) * 100);

  let barColor = 'bg-tmc-orange';
  if (variant === 'auto') {
    if (percentage >= 80) barColor = 'bg-success';
    else if (percentage >= 50) barColor = 'bg-warning';
    else barColor = 'bg-error';
  }

  return (
    <div className="w-full h-1.5 bg-light-gray/50 rounded-full overflow-hidden">
      <div
        className={`h-full ${barColor} rounded-full transition-all duration-500`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
};

MiniProgress.propTypes = {
  value: PropTypes.number.isRequired,
  max: PropTypes.number.isRequired,
  variant: PropTypes.oneOf(['default', 'auto'])
};

// Componente de Status Dot
const StatusDot = ({ status }) => {
  const colors = {
    success: 'bg-success',
    warning: 'bg-warning',
    error: 'bg-error',
    neutral: 'bg-light-gray'
  };

  return (
    <span className={`inline-block w-2 h-2 rounded-full ${colors[status] || colors.neutral}`} />
  );
};

StatusDot.propTypes = {
  status: PropTypes.oneOf(['success', 'warning', 'error', 'neutral'])
};

// Componente de Métrica Compacta
const MetricRow = ({ icon: Icon, label, value, status, hint }) => (
  <div className="flex items-center justify-between py-2 border-b border-light-gray/50 last:border-0">
    <div className="flex items-center gap-2">
      <div className="w-7 h-7 rounded-lg bg-off-white flex items-center justify-center">
        <Icon size={14} className="text-medium-gray" />
      </div>
      <div>
        <p className="text-xs font-medium text-dark-gray">{label}</p>
        {hint && <p className="text-[10px] text-medium-gray">{hint}</p>}
      </div>
    </div>
    <div className="flex items-center gap-2">
      <span className={`text-sm font-semibold ${
        status === 'success' ? 'text-success' :
        status === 'warning' ? 'text-warning' :
        status === 'error' ? 'text-error' : 'text-dark-gray'
      }`}>
        {value}
      </span>
      <StatusDot status={status} />
    </div>
  </div>
);

MetricRow.propTypes = {
  icon: PropTypes.elementType.isRequired,
  label: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  status: PropTypes.oneOf(['success', 'warning', 'error', 'neutral']),
  hint: PropTypes.string
};

// Componente de Checklist Item
const ChecklistItem = ({ checked, children }) => (
  <div className="flex items-center gap-2 py-1">
    <div className={`w-4 h-4 rounded flex items-center justify-center ${
      checked ? 'bg-success/10' : 'bg-light-gray/50'
    }`}>
      {checked ? (
        <Check size={10} className="text-success" />
      ) : (
        <X size={10} className="text-medium-gray" />
      )}
    </div>
    <span className={`text-xs ${checked ? 'text-dark-gray' : 'text-medium-gray'}`}>
      {children}
    </span>
  </div>
);

ChecklistItem.propTypes = {
  checked: PropTypes.bool,
  children: PropTypes.node.isRequired
};

// Componente Principal
const SEOAnalyzerPanel = ({ title, linhaFina, content, tags, onOptimizeWithAI }) => {
  const metrics = useMemo(() => {
    const titleLength = title?.length || 0;
    const linhaFinaLength = linhaFina?.length || 0;
    const wordCount = content?.split(/\s+/).filter(Boolean).length || 0;
    const readability = calculateReadability(content);
    const keywords = analyzeKeywords(content, title);

    const hasImages = /<img|!\[/.test(content || '');
    const hasLinks = /<a |https?:\/\/|\[.*\]\(/.test(content || '');
    const paragraphs = (content || '').split(/\n\n+/).filter(p => p.trim().length > 0);
    const sentences = (content || '').split(/[.!?]+/).filter(s => s.trim().length > 0);

    // Score calculation
    let score = 0;
    if (titleLength >= 50 && titleLength <= 60) score += 20;
    else if (titleLength >= 40 && titleLength <= 70) score += 15;
    else if (titleLength > 0) score += 5;

    if (linhaFinaLength >= 150 && linhaFinaLength <= 160) score += 20;
    else if (linhaFinaLength >= 120 && linhaFinaLength <= 180) score += 15;
    else if (linhaFinaLength >= 80) score += 10;
    else if (linhaFinaLength > 0) score += 5;

    if (wordCount >= 800) score += 20;
    else if (wordCount >= 600) score += 15;
    else if (wordCount >= 400) score += 10;
    else if (wordCount >= 200) score += 5;

    if (readability.level === 'success') score += 15;
    else if (readability.level === 'warning') score += 8;

    if (keywords.some(k => k.inTitle)) score += 10;
    else if (keywords.length > 0) score += 5;

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
      avgWordsPerSentence: sentences.length > 0 ? Math.round(wordCount / sentences.length) : 0
    };
  }, [title, linhaFina, content, tags]);

  const getTitleStatus = () => {
    if (metrics.titleLength >= 50 && metrics.titleLength <= 60) return 'success';
    if (metrics.titleLength >= 40 && metrics.titleLength <= 70) return 'warning';
    return 'error';
  };

  const getDescStatus = () => {
    if (metrics.linhaFinaLength >= 150 && metrics.linhaFinaLength <= 160) return 'success';
    if (metrics.linhaFinaLength >= 120) return 'warning';
    return 'error';
  };

  const getWordCountStatus = () => {
    if (metrics.wordCount >= 600) return 'success';
    if (metrics.wordCount >= 300) return 'warning';
    return 'error';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Score Principal com Gauge */}
      <div className="flex flex-col items-center py-4 border-b border-light-gray">
        <CircularGauge value={metrics.score} size={110} />
        <p className="text-[10px] text-medium-gray mt-2 uppercase tracking-wider">
          Score SEO
        </p>
      </div>

      {/* Métricas Principais */}
      <div className="flex-1 overflow-y-auto">
        {/* Seção: Conteúdo */}
        <div className="p-3">
          <p className="text-[10px] font-semibold text-medium-gray uppercase tracking-wider mb-2">
            Conteúdo
          </p>

          <MetricRow
            icon={Type}
            label="Título"
            value={`${metrics.titleLength}/60`}
            status={getTitleStatus()}
            hint="Ideal: 50-60 caracteres"
          />

          <MetricRow
            icon={FileText}
            label="Meta Description"
            value={`${metrics.linhaFinaLength}/160`}
            status={getDescStatus()}
            hint="Ideal: 150-160 caracteres"
          />

          <MetricRow
            icon={BarChart2}
            label="Palavras"
            value={`${metrics.wordCount}`}
            status={getWordCountStatus()}
            hint="Mínimo: 600 palavras"
          />

        </div>

        {/* Seção: Legibilidade Expandida */}
        <div className="p-3 border-t border-light-gray">
          <p className="text-[10px] font-semibold text-medium-gray uppercase tracking-wider mb-2">
            Legibilidade
          </p>

          {/* Score e Grade */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-off-white flex items-center justify-center">
                <BookOpen size={14} className="text-medium-gray" />
              </div>
              <div>
                <p className="text-xs font-medium text-dark-gray">
                  {metrics.readability.grade}
                </p>
                <p className="text-[10px] text-medium-gray">
                  Score: {metrics.readability.score}/100
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${
                metrics.readability.level === 'success' ? 'text-success' :
                metrics.readability.level === 'warning' ? 'text-warning' : 'text-error'
              }`}>
                {metrics.readability.score >= 60 ? 'OK' : 'Melhorar'}
              </span>
              <StatusDot status={metrics.readability.level} />
            </div>
          </div>

          {/* Dica contextual */}
          <div className={`text-[10px] p-2 rounded-md ${
            metrics.readability.level === 'success' ? 'bg-success/5 text-success' :
            metrics.readability.level === 'warning' ? 'bg-warning/5 text-warning' :
            'bg-error/5 text-error'
          }`}>
            {metrics.readability.tip || 'Escreva algum conteúdo para analisar.'}
          </div>

          {/* Métrica auxiliar */}
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-light-gray/50">
            <span className="text-[10px] text-medium-gray">Média palavras/frase</span>
            <span className={`text-[10px] font-medium ${
              metrics.avgWordsPerSentence <= 20 ? 'text-success' :
              metrics.avgWordsPerSentence <= 25 ? 'text-warning' : 'text-error'
            }`}>
              {metrics.avgWordsPerSentence} {metrics.avgWordsPerSentence <= 20 ? '(ideal)' : metrics.avgWordsPerSentence <= 25 ? '(ok)' : '(longo)'}
            </span>
          </div>

          {/* Referência */}
          <div className="mt-2 px-2 py-1.5 bg-off-white rounded text-center">
            <p className="text-[9px] text-medium-gray font-medium">
              Ideal: 60+ (Fácil) • Frases até 20 palavras
            </p>
          </div>
        </div>

        {/* Seção: Palavras-chave */}
        {metrics.keywords.length > 0 && (
          <div className="p-3 border-t border-light-gray">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold text-medium-gray uppercase tracking-wider">
                Palavras-chave
              </p>
              <span className="text-[10px] text-medium-gray font-medium">Densidade</span>
            </div>

            <div className="space-y-1.5">
              {metrics.keywords.slice(0, 4).map((kw, i) => (
                <div key={i} className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-2">
                    <StatusDot status={kw.status} />
                    <span className="text-xs text-dark-gray truncate max-w-[90px]">{kw.word}</span>
                    {kw.inTitle && (
                      <span className="text-[8px] px-1 py-0.5 bg-tmc-orange/10 text-tmc-orange rounded font-medium">
                        TÍTULO
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`text-[11px] font-semibold ${
                      kw.status === 'success' ? 'text-success' :
                      kw.status === 'warning' ? 'text-warning' : 'text-error'
                    }`}>
                      {kw.density}%
                    </span>
                    <span className="text-[10px] text-dark-gray font-medium">
                      ({kw.count}x)
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Legenda de densidade */}
            <div className="mt-3 pt-2 border-t border-light-gray/50">
              <p className="text-[9px] text-medium-gray mb-1.5">
                Densidade ideal: 1% - 3% do texto
              </p>
              <div className="flex items-center gap-3 text-[9px]">
                <span className="flex items-center gap-1">
                  <StatusDot status="success" />
                  <span className="text-medium-gray">Ideal</span>
                </span>
                <span className="flex items-center gap-1">
                  <StatusDot status="warning" />
                  <span className="text-medium-gray">Baixa</span>
                </span>
                <span className="flex items-center gap-1">
                  <StatusDot status="error" />
                  <span className="text-medium-gray">Excessiva</span>
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Seção: Checklist */}
        <div className="p-3 border-t border-light-gray">
          <p className="text-[10px] font-semibold text-medium-gray uppercase tracking-wider mb-2">
            Checklist
          </p>
          <div className="space-y-0.5">
            <ChecklistItem checked={metrics.titleLength >= 50 && metrics.titleLength <= 60}>
              Título otimizado
            </ChecklistItem>
            <ChecklistItem checked={metrics.linhaFinaLength >= 150}>
              Meta description completa
            </ChecklistItem>
            <ChecklistItem checked={metrics.wordCount >= 600}>
              Conteúdo substancial (+600 palavras)
            </ChecklistItem>
            <ChecklistItem checked={metrics.hasImages}>
              Imagens incluídas
            </ChecklistItem>
            <ChecklistItem checked={metrics.hasLinks}>
              Links de referência
            </ChecklistItem>
            <ChecklistItem checked={tags?.length >= 3}>
              Tópicos/tags ({tags?.length || 0}/3)
            </ChecklistItem>
            <ChecklistItem checked={metrics.keywords.some(k => k.inTitle)}>
              Palavra-chave no título
            </ChecklistItem>
          </div>
        </div>
      </div>

      {/* Botão Otimizar */}
      {metrics.score < 80 && onOptimizeWithAI && (
        <div className="p-3 border-t border-light-gray">
          <button
            onClick={onOptimizeWithAI}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-tmc-orange text-white text-sm font-medium rounded-lg hover:bg-tmc-orange/90 transition-colors"
          >
            <Sparkles size={16} />
            Otimizar com IA
          </button>
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

// Hook utilitário para cálculo do score SEO (para uso externo)
export const calculateSEOScore = ({ title, linhaFina, content, tags }) => {
  const titleLength = title?.length || 0;
  const linhaFinaLength = linhaFina?.length || 0;
  const wordCount = content?.split(/\s+/).filter(Boolean).length || 0;
  const readability = calculateReadability(content);
  const keywords = analyzeKeywords(content, title);

  const hasImages = /<img|!\[/.test(content || '');
  const hasLinks = /<a |https?:\/\/|\[.*\]\(/.test(content || '');

  // Score calculation - mesma lógica do painel
  let score = 0;
  if (titleLength >= 50 && titleLength <= 60) score += 20;
  else if (titleLength >= 40 && titleLength <= 70) score += 15;
  else if (titleLength > 0) score += 5;

  if (linhaFinaLength >= 150 && linhaFinaLength <= 160) score += 20;
  else if (linhaFinaLength >= 120 && linhaFinaLength <= 180) score += 15;
  else if (linhaFinaLength >= 80) score += 10;
  else if (linhaFinaLength > 0) score += 5;

  if (wordCount >= 800) score += 20;
  else if (wordCount >= 600) score += 15;
  else if (wordCount >= 400) score += 10;
  else if (wordCount >= 200) score += 5;

  if (readability.level === 'success') score += 15;
  else if (readability.level === 'warning') score += 8;

  if (keywords.some(k => k.inTitle)) score += 10;
  else if (keywords.length > 0) score += 5;

  if (hasImages) score += 5;
  if (hasLinks) score += 5;
  if (tags?.length >= 3) score += 5;

  return score;
};

export default SEOAnalyzerPanel;
