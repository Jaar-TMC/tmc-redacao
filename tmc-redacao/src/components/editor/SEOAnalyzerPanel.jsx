import React, { useMemo, useState, useRef } from 'react';
import PropTypes from 'prop-types';
import {
  Check,
  AlertTriangle,
  X,
  Type,
  FileText,
  BarChart2,
  Link2,
  Image,
  Sparkles,
  Target,
  Hash,
  TrendingUp,
  ChevronDown,
  ChevronRight,
  Shield,
  Settings,
  HelpCircle,
  Lightbulb,
  ExternalLink,
  Award,
  Zap,
  ArrowUp
} from 'lucide-react';
import { performSEOAnalysis, calculateSEOScore } from '../../utils/seoUtils';
import { SEO_EXPLANATIONS, getScoreTips } from '../../constants/seoExplanations';
import { CATEGORY_WEIGHTS } from '../../constants/seoConstants';
import { generateOptimizationSummary, extractPrimaryKeyword } from '../../utils/seoPromptGenerator';

/**
 * SEOAnalyzerPanel - Painel de análise SEO em tempo real (v3 - Algorithm Excellence)
 *
 * Based on Google's 2025-2026 ranking factors, E-E-A-T principles,
 * and AI Overview optimization guidelines.
 *
 * 5 Categories (90 pts raw, normalized to 0-100):
 * 1. Content Quality (30 pts)
 * 2. On-Page Optimization (25 pts)
 * 3. E-E-A-T Signals (20 pts)
 * 4. Technical Excellence (5 pts scored + links internos/mídia as manual actions)
 * 5. AI & SERP Optimization (10 pts)
 */

// ═══════════════════════════════════════════════════════════════
// UI COMPONENTS
// ═══════════════════════════════════════════════════════════════

// Circular Gauge Component
const CircularGauge = ({ value, size = 120 }) => {
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const progress = (value / 100) * circumference;
  const offset = circumference - progress;

  let strokeColor = '#EF4444';
  let bgGradient = 'from-red-50 to-red-100';
  let label = 'Crítico';

  if (value >= 80) {
    strokeColor = '#10B981';
    bgGradient = 'from-emerald-50 to-emerald-100';
    label = 'Excelente';
  } else if (value >= 60) {
    strokeColor = '#F59E0B';
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
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={strokeWidth}
        />
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

// Mini Progress Bar
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

// Status Dot
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

// Category Icon mapping
const CategoryIcon = ({ category, size = 14 }) => {
  const icons = {
    contentQuality: FileText,
    onPageOptimization: Target,
    eeatSignals: Shield,
    technicalExcellence: Settings,
    aiSerpOptimization: Sparkles
  };
  const Icon = icons[category] || FileText;
  return <Icon size={size} />;
};

CategoryIcon.propTypes = {
  category: PropTypes.string.isRequired,
  size: PropTypes.number
};

// Help Tooltip Component - Uses fixed positioning to avoid overflow clipping
const HelpTooltip = ({ content, children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef(null);

  const handleClick = () => {
    if (!isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      // Position tooltip to the left of the button, centered vertically
      setPosition({
        top: rect.top + window.scrollY,
        left: Math.max(10, rect.left - 290) // 290 = tooltip width (288) + gap
      });
    }
    setIsOpen(!isOpen);
  };

  return (
    <div className="relative inline-block">
      <button
        ref={buttonRef}
        onClick={handleClick}
        className="text-medium-gray hover:text-dark-gray transition-colors"
      >
        {children}
      </button>
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-[100]"
            onClick={() => setIsOpen(false)}
          />
          <div
            className="fixed z-[101] w-72 p-3 bg-white rounded-lg shadow-xl border border-light-gray text-left max-h-80 overflow-y-auto"
            style={{
              top: `${position.top}px`,
              left: `${position.left}px`
            }}
          >
            <button
              onClick={() => setIsOpen(false)}
              className="absolute top-2 right-2 text-medium-gray hover:text-dark-gray"
            >
              <X size={12} />
            </button>
            {content}
          </div>
        </>
      )}
    </div>
  );
};

HelpTooltip.propTypes = {
  content: PropTypes.node.isRequired,
  children: PropTypes.node.isRequired
};

// Expandable Category Card
const CategoryCard = ({ categoryKey, category, explanations, isExpanded, onToggle }) => {
  const categoryNames = {
    contentQuality: 'Qualidade do Conteúdo',
    onPageOptimization: 'Otimização On-Page',
    eeatSignals: 'E-E-A-T',
    technicalExcellence: 'Excelência Técnica',
    aiSerpOptimization: 'IA & SERP'
  };

  const percentage = Math.round((category.score / category.maxScore) * 100);

  return (
    <div className="border-b border-light-gray last:border-0">
      {/* Category Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 hover:bg-off-white/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
            category.status === 'success' ? 'bg-success/10 text-success' :
            category.status === 'warning' ? 'bg-warning/10 text-warning' :
            'bg-error/10 text-error'
          }`}>
            <CategoryIcon category={categoryKey} size={14} />
          </div>
          <div className="text-left">
            <p className="text-xs font-medium text-dark-gray">
              {categoryNames[categoryKey]}
            </p>
            <p className="text-[10px] text-medium-gray">
              {category.score}/{category.maxScore} pts
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-16">
            <MiniProgress value={category.score} max={category.maxScore} variant="auto" />
          </div>
          {isExpanded ? (
            <ChevronDown size={14} className="text-medium-gray" />
          ) : (
            <ChevronRight size={14} className="text-medium-gray" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2">
          {/* Category explanation */}
          {explanations && (
            <div className="text-[10px] text-medium-gray bg-off-white/50 rounded p-2 mb-2">
              {explanations.categoryDescription}
            </div>
          )}

          {/* Metrics */}
          {Object.entries(category.metrics).map(([metricKey, metric]) => (
            <MetricItem
              key={metricKey}
              metricKey={metricKey}
              metric={metric}
              explanation={explanations?.metrics?.[metricKey]}
            />
          ))}
        </div>
      )}
    </div>
  );
};

CategoryCard.propTypes = {
  categoryKey: PropTypes.string.isRequired,
  category: PropTypes.object.isRequired,
  explanations: PropTypes.object,
  isExpanded: PropTypes.bool,
  onToggle: PropTypes.func.isRequired
};

// Metric Item Component
const MetricItem = ({ metricKey, metric, explanation }) => {
  const metricNames = {
    wordCountDepth: 'Extensão e Profundidade',
    contentStructure: 'Estrutura do Conteúdo',
    readability: 'Legibilidade',
    titleOptimization: 'Título',
    metaDescription: 'Meta Description',
    keywordStrategy: 'Palavras-chave',
    urlSlug: 'URL/Slug',
    experience: 'Experiência',
    expertise: 'Expertise',
    authority: 'Autoridade',
    trust: 'Confiança',
    internalLinks: 'Links Internos',
    externalLinks: 'Links Externos',
    mediaOptimization: 'Mídia',
    featuredSnippet: 'Featured Snippet',
    aiOverview: 'AI Overview'
  };

  return (
    <div className="flex items-center justify-between py-1.5 border-b border-light-gray/30 last:border-0">
      <div className="flex items-center gap-2">
        <StatusDot status={metric.status} />
        <span className="text-[11px] text-dark-gray">
          {metricNames[metricKey] || metricKey}
        </span>
        {explanation && (
          <HelpTooltip
            content={
              <div>
                <p className="font-medium text-dark-gray text-xs mb-1">{explanation.name}</p>
                <p className="text-[10px] text-medium-gray mb-2">{explanation.description}</p>
                {explanation.howToImprove && (
                  <div className="text-[10px]">
                    <p className="font-medium text-dark-gray mb-1">Como melhorar:</p>
                    <ul className="list-disc list-inside text-medium-gray space-y-0.5">
                      {explanation.howToImprove.slice(0, 3).map((tip, i) => (
                        <li key={i}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {explanation.tip && (
                  <div className="mt-2 p-1.5 bg-amber-50 rounded text-[10px] text-amber-700">
                    <Lightbulb size={10} className="inline mr-1" />
                    {explanation.tip}
                  </div>
                )}
              </div>
            }
          >
            <HelpCircle size={10} />
          </HelpTooltip>
        )}
      </div>
      <div className="flex items-center gap-1.5">
        {metricKey === 'internalLinks' || metricKey === 'mediaOptimization' ? (
          <span className="text-[10px] font-medium text-amber-600">
            ação manual
          </span>
        ) : (
          <span className={`text-[10px] font-medium ${
            metric.status === 'success' ? 'text-success' :
            metric.status === 'warning' ? 'text-warning' :
            metric.status === 'error' ? 'text-error' : 'text-medium-gray'
          }`}>
            {metric.score}/{metric.maxScore}
          </span>
        )}
      </div>
    </div>
  );
};

MetricItem.propTypes = {
  metricKey: PropTypes.string.isRequired,
  metric: PropTypes.object.isRequired,
  explanation: PropTypes.object
};

// Recommendations Panel
const RecommendationsPanel = ({ recommendations }) => {
  if (!recommendations || recommendations.length === 0) return null;

  const categoryNames = {
    contentQuality: 'Conteúdo',
    onPageOptimization: 'On-Page',
    eeatSignals: 'E-E-A-T',
    technicalExcellence: 'Técnico',
    aiSerpOptimization: 'IA/SERP'
  };

  return (
    <div className="p-3 border-t border-light-gray">
      <div className="flex items-center gap-1.5 mb-2">
        <Zap size={12} className="text-tmc-orange" />
        <p className="text-[10px] font-semibold text-dark-gray uppercase tracking-wider">
          Próximos Passos
        </p>
      </div>
      <div className="space-y-1.5">
        {recommendations.slice(0, 3).map((rec, index) => (
          <div
            key={index}
            className={`flex items-start gap-2 p-2 rounded text-[10px] ${
              rec.priority === 'high' ? 'bg-error/5' : 'bg-warning/5'
            }`}
          >
            <div className={`mt-0.5 w-4 h-4 rounded flex items-center justify-center flex-shrink-0 ${
              rec.priority === 'high' ? 'bg-error/10' : 'bg-warning/10'
            }`}>
              {rec.priority === 'high' ? (
                <AlertTriangle size={10} className="text-error" />
              ) : (
                <Lightbulb size={10} className="text-warning" />
              )}
            </div>
            <div>
              <span className="text-[9px] font-medium text-medium-gray uppercase">
                {categoryNames[rec.category]}
              </span>
              <p className="text-dark-gray">{rec.message}</p>
              <span className="text-[9px] text-medium-gray">
                +{rec.pointsAvailable} pts disponíveis
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

RecommendationsPanel.propTypes = {
  recommendations: PropTypes.array
};

// Keywords Panel
const KeywordsPanel = ({ keywords }) => {
  if (!keywords || keywords.length === 0) return null;

  return (
    <div className="p-3 border-t border-light-gray">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-semibold text-medium-gray uppercase tracking-wider">
          Palavras-chave
        </p>
        <span className="text-[10px] text-medium-gray">Densidade</span>
      </div>
      <div className="space-y-1">
        {keywords.slice(0, 4).map((kw, i) => (
          <div key={i} className="flex items-center justify-between py-1">
            <div className="flex items-center gap-2">
              <StatusDot status={kw.status} />
              <span className="text-[11px] text-dark-gray truncate max-w-[90px]">
                {kw.word}
              </span>
              {kw.inTitle && (
                <span className="text-[8px] px-1 py-0.5 bg-tmc-orange/10 text-tmc-orange rounded font-medium">
                  TÍTULO
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`text-[10px] font-semibold ${
                kw.status === 'success' ? 'text-success' :
                kw.status === 'warning' ? 'text-warning' : 'text-error'
              }`}>
                {kw.density}%
              </span>
              <span className="text-[9px] text-medium-gray">
                ({kw.count}x)
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 px-2 py-1.5 bg-off-white rounded text-center">
        <p className="text-[9px] text-medium-gray">
          Densidade ideal: 1% - 2.5%
        </p>
      </div>
    </div>
  );
};

KeywordsPanel.propTypes = {
  keywords: PropTypes.array
};

// Manual Tasks Panel - shows what user needs to do manually
const ManualTasksPanel = ({ manualTasks, manualPotential }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!manualTasks || manualTasks.length === 0) return null;

  return (
    <div className="border-t border-light-gray bg-amber-50/30">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-1.5 p-3 hover:bg-amber-50/50 transition-colors"
      >
        <AlertTriangle size={12} className="text-amber-600" />
        <p className="text-[10px] font-semibold text-amber-800 uppercase tracking-wider">
          Ações Manuais Necessárias
        </p>
        <span className="text-[9px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full ml-auto">
          +{manualPotential} pts
        </span>
        {isExpanded ? (
          <ChevronDown size={14} className="text-amber-600" />
        ) : (
          <ChevronRight size={14} className="text-amber-600" />
        )}
      </button>
      {isExpanded && (
        <div className="px-3 pb-3">
          <p className="text-[9px] text-amber-700 mb-2">
            A IA não pode otimizar estes itens automaticamente:
          </p>
          <div className="space-y-1.5">
            {manualTasks.map((task, index) => (
              <div
                key={index}
                className="flex items-start gap-2 p-2 bg-white/80 rounded text-[10px]"
              >
                <div className="mt-0.5 w-4 h-4 rounded bg-amber-100 flex items-center justify-center flex-shrink-0">
                  {task.metric === 'Links Internos' && <Link2 size={10} className="text-amber-700" />}
                  {task.metric === 'Links Externos' && <ExternalLink size={10} className="text-amber-700" />}
                  {task.metric === 'Mídia' && <Image size={10} className="text-amber-700" />}
                  {task.metric === 'URL/Slug' && <Hash size={10} className="text-amber-700" />}
                  {!['Links Internos', 'Links Externos', 'Mídia', 'URL/Slug'].includes(task.metric) &&
                    <AlertTriangle size={10} className="text-amber-700" />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-dark-gray">{task.metric}</span>
                    <span className="text-[9px] text-amber-600">+{task.points} pts</span>
                  </div>
                  <p className="text-medium-gray">{task.action}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

ManualTasksPanel.propTypes = {
  manualTasks: PropTypes.array,
  manualPotential: PropTypes.number
};

// ═══════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════

const SEOAnalyzerPanel = ({
  title,
  linhaFina,
  content,
  tags,
  slug,
  articleType = 'default',
  targetKeyword,
  hasAuthor = false,
  onOptimizeWithAI
}) => {
  const [expandedCategories, setExpandedCategories] = useState({
    contentQuality: false,
    onPageOptimization: false,
    eeatSignals: false,
    technicalExcellence: false,
    aiSerpOptimization: false
  });

  // Perform SEO analysis
  const analysis = useMemo(() => {
    return performSEOAnalysis({
      title,
      linhaFina,
      content,
      tags,
      slug,
      articleType,
      targetKeyword,
      hasAuthor
    });
  }, [title, linhaFina, content, tags, slug, articleType, targetKeyword, hasAuthor]);

  // Get optimization summary for potential improvement display (with AI/manual split)
  const optimizationSummary = useMemo(() => {
    return generateOptimizationSummary(analysis, { title, content, tags, targetKeyword });
  }, [analysis, title, content, tags, targetKeyword]);

  // Get score tips
  const scoreTips = getScoreTips(analysis.score);

  // Toggle category expansion
  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  // Expand all categories
  const expandAll = () => {
    setExpandedCategories({
      contentQuality: true,
      onPageOptimization: true,
      eeatSignals: true,
      technicalExcellence: true,
      aiSerpOptimization: true
    });
  };

  // Collapse all categories
  const collapseAll = () => {
    setExpandedCategories({
      contentQuality: false,
      onPageOptimization: false,
      eeatSignals: false,
      technicalExcellence: false,
      aiSerpOptimization: false
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Score Principal */}
      <div className="flex flex-col items-center py-4 border-b border-light-gray">
        <CircularGauge value={analysis.score} size={110} />
        <p className="text-[10px] text-medium-gray mt-2 uppercase tracking-wider">
          Score SEO
        </p>

        {/* Score message */}
        <p className={`text-[10px] mt-1 px-2 py-1 rounded ${
          analysis.status === 'success' ? 'bg-success/10 text-success' :
          analysis.status === 'warning' ? 'bg-warning/10 text-warning' :
          'bg-error/10 text-error'
        }`}>
          {scoreTips.message}
        </p>
      </div>

      {/* Expand/Collapse Controls */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-light-gray bg-off-white/30">
        <p className="text-[10px] font-semibold text-medium-gray uppercase tracking-wider">
          Categorias
        </p>
        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="text-[9px] text-tmc-orange hover:underline"
          >
            Expandir
          </button>
          <span className="text-medium-gray">|</span>
          <button
            onClick={collapseAll}
            className="text-[9px] text-tmc-orange hover:underline"
          >
            Recolher
          </button>
        </div>
      </div>

      {/* Categories */}
      <div className="flex-1 overflow-y-auto">
        {Object.entries(analysis.categories).map(([categoryKey, category]) => (
          <CategoryCard
            key={categoryKey}
            categoryKey={categoryKey}
            category={category}
            explanations={SEO_EXPLANATIONS[categoryKey]}
            isExpanded={expandedCategories[categoryKey]}
            onToggle={() => toggleCategory(categoryKey)}
          />
        ))}

        {/* Keywords Panel */}
        <KeywordsPanel keywords={analysis.keywords} />

        {/* Recommendations */}
        <RecommendationsPanel recommendations={analysis.recommendations} />
      </div>

      {/* Manual Tasks Panel - shows what needs manual work */}
      {optimizationSummary.manualTasks?.length > 0 && (
        <ManualTasksPanel
          manualTasks={optimizationSummary.manualTasks}
          manualPotential={optimizationSummary.manualPotential}
        />
      )}

      {/* Optimize Button */}
      {analysis.score < 80 && onOptimizeWithAI && (
        <div className="p-3 border-t border-light-gray">
          {/* Potential improvement indicator with AI/Manual split */}
          {(optimizationSummary.aiPotential > 0 || optimizationSummary.manualPotential > 0) && (
            <div className="mb-2 px-3 py-2 bg-gradient-to-r from-tmc-orange/5 to-tmc-orange/10 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Sparkles size={12} className="text-tmc-orange" />
                  <span className="text-[10px] text-medium-gray">Potencial IA:</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-xs font-semibold text-tmc-orange">
                    +{optimizationSummary.aiPotential} pts
                  </span>
                  <span className="text-[10px] text-medium-gray">
                    → {optimizationSummary.estimatedScore}/100
                  </span>
                </div>
              </div>
              {optimizationSummary.manualPotential > 0 && (
                <div className="mt-1 flex items-center justify-between text-[9px]">
                  <span className="text-amber-600">
                    + {optimizationSummary.manualPotential} pts com ações manuais
                  </span>
                  <span className="text-medium-gray">
                    (total: +{optimizationSummary.aiPotential + optimizationSummary.manualPotential})
                  </span>
                </div>
              )}
              {optimizationSummary.improvements.length > 0 && (
                <div className="mt-1.5 text-[9px] text-medium-gray border-t border-tmc-orange/10 pt-1.5">
                  <span className="text-tmc-orange font-medium">IA vai otimizar: </span>
                  {optimizationSummary.improvements.slice(0, 2).map((imp, i) => (
                    <span key={i}>
                      {imp.metric} (+{imp.pointsAvailable})
                      {i < Math.min(optimizationSummary.improvements.length, 2) - 1 ? ', ' : ''}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
          <button
            onClick={() => onOptimizeWithAI(analysis)}
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
  slug: PropTypes.string,
  articleType: PropTypes.oneOf(['noticia', 'reportagem', 'analise', 'opiniao', 'default']),
  targetKeyword: PropTypes.string,
  hasAuthor: PropTypes.bool,
  onOptimizeWithAI: PropTypes.func
};

// Re-export calculateSEOScore for backward compatibility
export { calculateSEOScore };

export default SEOAnalyzerPanel;
