import { memo, useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { Calculator, ChevronDown, AlertCircle, RefreshCw, Info } from 'lucide-react';
import Skeleton from '../ui/Skeleton';

const WhatIfCalculator = ({ sourceEstimate, isLoading, error, onRetry }) => {
  const [sourceCount, setSourceCount] = useState(5);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [urlText, setUrlText] = useState('');

  const parsedCount = useMemo(() => {
    if (!urlText.trim()) return 0;
    return urlText.split('\n').filter(line => line.trim().length > 0).length;
  }, [urlText]);

  const handleUrlChange = (e) => {
    setUrlText(e.target.value);
    const count = e.target.value.split('\n').filter(line => line.trim().length > 0).length;
    if (count > 0) setSourceCount(count);
  };

  const handleCountChange = (e) => {
    const val = Math.max(1, Math.min(100, Number(e.target.value) || 1));
    setSourceCount(val);
    if (urlText.trim()) setUrlText('');
  };

  const projections = useMemo(() => {
    if (!sourceEstimate) return null;
    const {
      avg_articles_per_source_per_day = 20,
      avg_cost_per_article_pipeline = 0.002,
      avg_cost_per_generated_article = 0.18,
      avg_articles_generated_per_source = 0.28,
    } = sourceEstimate;

    const dailyPipeline = sourceCount * avg_articles_per_source_per_day * avg_cost_per_article_pipeline;
    const weeklyGenerated = sourceCount * avg_articles_generated_per_source * 7;
    const weeklyGenerationCost = weeklyGenerated * avg_cost_per_generated_article;
    const monthlyPipeline = dailyPipeline * 30;
    const monthlyGeneration = weeklyGenerationCost * (30 / 7);

    return {
      articlesPerDay: Math.round(sourceCount * avg_articles_per_source_per_day),
      dailyPipeline: dailyPipeline.toFixed(2),
      avgCostPerGenerated: avg_cost_per_generated_article.toFixed(2),
      weeklyGenerated: Math.round(weeklyGenerated),
      monthlyPipeline: monthlyPipeline.toFixed(2),
      monthlyGeneration: monthlyGeneration.toFixed(2),
      annualPipeline: (monthlyPipeline * 12).toFixed(2),
      annualGeneration: (monthlyGeneration * 12).toFixed(2),
      totalMonthly: (monthlyPipeline + monthlyGeneration).toFixed(2),
    };
  }, [sourceCount, sourceEstimate]);

  if (isLoading) return (
    <div className="border-t-4 border-tmc-orange rounded-xl bg-white border border-light-gray p-6 space-y-4" role="status" aria-live="polite">
      <Skeleton variant="title" className="w-1/3" />
      <Skeleton variant="default" className="h-10 w-32" />
      <Skeleton variant="default" className="h-32 w-full" />
    </div>
  );

  if (error) return (
    <div className="border-t-4 border-tmc-orange rounded-xl bg-white border border-light-gray p-8">
      <div className="flex flex-col items-center justify-center py-4">
        <AlertCircle size={32} className="text-error mb-4" aria-hidden="true" />
        <p className="text-lg font-semibold text-dark-gray mb-2">Erro ao carregar estimativas</p>
        <p className="text-sm text-medium-gray mb-4">{error}</p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center gap-2 min-h-[44px]"
          aria-label="Tentar carregar estimativas novamente"
        >
          <RefreshCw size={16} aria-hidden="true" /> Tentar novamente
        </button>
      </div>
    </div>
  );

  return (
    <div className="border-t-4 border-tmc-orange rounded-xl bg-white border border-light-gray p-6">
      <div className="flex items-center gap-2 mb-4">
        <Calculator size={20} className="text-tmc-orange" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-dark-gray">Simulador de Custos</h2>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Input */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-dark-gray mb-2">
              Quantidade de novas fontes
            </label>
            <input
              type="number"
              min="1"
              max="100"
              value={sourceCount}
              onChange={handleCountChange}
              className="w-32 px-3 py-2 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange min-h-[44px]"
              aria-label="Quantidade de novas fontes RSS"
            />
          </div>

          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-tmc-orange hover:underline flex items-center gap-1 min-h-[44px]"
            aria-expanded={showAdvanced}
            aria-controls="advanced-rss-input"
          >
            <ChevronDown className={`transition-transform ${showAdvanced ? 'rotate-180' : ''}`} size={16} aria-hidden="true" />
            Avançado: colar links RSS
          </button>

          {showAdvanced && (
            <div id="advanced-rss-input">
              <label className="block text-sm font-medium text-dark-gray mb-2">
                Cole os links RSS das novas fontes (um por linha)
              </label>
              <textarea
                value={urlText}
                onChange={handleUrlChange}
                placeholder={"https://rss.example.com/feed1\nhttps://rss.example.com/feed2"}
                className="w-full p-3 border border-light-gray rounded-lg text-sm min-h-[100px] focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                aria-label="Links RSS das novas fontes, um por linha"
              />
              <p className="text-xs text-medium-gray mt-1">{parsedCount} fontes detectadas</p>
            </div>
          )}
        </div>

        {/* Output */}
        <div className="space-y-4">
          {projections && (
            <>
              <p className="text-sm font-medium text-medium-gray">Baseado nas médias atuais da plataforma:</p>

              <div className="space-y-3 text-sm">
                <div>
                  <p className="font-semibold text-dark-gray mb-1">Coleta e Processamento (por fonte/dia)</p>
                  <p className="text-medium-gray">~{projections.articlesPerDay} artigos coletados/dia (média atual)</p>
                  <p className="text-medium-gray">Classificação + Scoring + Embedding: ${projections.dailyPipeline}/dia por {sourceCount} fontes</p>
                </div>

                <div>
                  <p className="font-semibold text-dark-gray mb-1">Geração estimada</p>
                  <p className="text-medium-gray">~{projections.weeklyGenerated} artigos gerados por semana (média atual)</p>
                  <p className="text-medium-gray">Custo médio por artigo gerado: ${projections.avgCostPerGenerated}</p>
                </div>

                <div className="bg-tmc-orange/5 border border-tmc-orange/20 rounded-lg p-4">
                  <p className="font-bold text-dark-gray mb-2">CUSTO ADICIONAL ESTIMADO ({sourceCount} fontes)</p>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-medium-gray">Mensal (pipeline):</span>
                      <span className="font-semibold text-dark-gray">${projections.monthlyPipeline}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-medium-gray">Mensal (gerações):</span>
                      <span className="font-semibold text-dark-gray">~${projections.monthlyGeneration}</span>
                    </div>
                    <div className="flex justify-between border-t border-light-gray pt-1 mt-1">
                      <span className="font-bold text-dark-gray">Total mensal:</span>
                      <span className="font-bold text-tmc-orange text-lg">~${projections.totalMonthly}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-tmc-orange/10 border border-tmc-orange/30 rounded-lg p-4 text-sm text-tmc-orange flex items-start gap-2" role="note">
                <Info size={16} className="flex-shrink-0 mt-0.5" aria-hidden="true" />
                <span>Os custos de pipeline (coleta, classificação, scoring, embedding) são automáticos. Os custos de geração dependem de quantos artigos os redatores criam a partir dessas fontes.</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

WhatIfCalculator.propTypes = {
  sourceEstimate: PropTypes.shape({
    avg_articles_per_source_per_day: PropTypes.number,
    avg_cost_per_article_pipeline: PropTypes.number,
    avg_cost_per_generated_article: PropTypes.number,
    avg_articles_generated_per_source: PropTypes.number,
  }),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};

export default memo(WhatIfCalculator);
