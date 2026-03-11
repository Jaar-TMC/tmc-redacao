import { useState, useCallback, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Search, Globe, Calendar, Check, AlertTriangle, RefreshCw, Loader2, ExternalLink } from 'lucide-react';
import { SourceBadge } from '../../../components/criar';
import { researchTopic } from '../../../services/api';

/**
 * TextoBasePrompt - Variante da pagina Texto-Base para Criar por Prompt
 *
 * Fluxo em duas fases:
 * A. Prompt Input - usuario descreve o tema e seleciona periodo
 * B. Source Review - exibe fontes encontradas para selecao
 */

const DATE_RANGE_OPTIONS = [
  { value: 3, label: 'Últimos 3 dias' },
  { value: 7, label: 'Últimos 7 dias' },
  { value: 15, label: 'Últimos 15 dias' },
  { value: 30, label: 'Últimos 30 dias' },
];

const MIN_CHARS = 300;

const TextoBasePrompt = ({
  fonte: _fonte,
  onChangeSource,
  onDataChange
}) => {
  // State
  const [prompt, setPrompt] = useState('');
  const [dateRange, setDateRange] = useState(7);
  const [isSearching, setIsSearching] = useState(false);
  const [sources, setSources] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [searchQueries, setSearchQueries] = useState([]);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Computed stats
  const stats = useMemo(() => {
    let totalChars = 0;
    let totalWords = 0;

    sources.forEach(s => {
      if (selectedIds.has(s.id || s.url)) {
        const text = s.full_text || '';
        totalChars += text.length;
        totalWords += text.trim() ? text.split(/\s+/).filter(Boolean).length : 0;
      }
    });

    return {
      selectedCount: selectedIds.size,
      totalChars,
      totalWords,
    };
  }, [sources, selectedIds]);

  const isInsufficient = stats.totalChars < MIN_CHARS && stats.selectedCount > 0;

  // Notify parent whenever selection changes so the parent's Continuar button enables
  const MAX_CHARS_PER_SOURCE = 2000;
  useEffect(() => {
    if (!onDataChange || !hasSearched || sources.length === 0) return;

    const selectedSources = sources.filter(s => selectedIds.has(s.id || s.url));
    if (selectedSources.length === 0) return;

    const assembledText = selectedSources
      .map(s => {
        const text = (s.full_text || '').slice(0, MAX_CHARS_PER_SOURCE);
        return `[Fonte: ${s.domain} - ${s.published_date || 'sem data'}]\n${text}`;
      })
      .join('\n\n---\n\n');

    onDataChange({
      selectedTopics: ['pesquisa-prompt'],
      topicTexts: { 'pesquisa-prompt': assembledText },
      wordCount: stats.totalWords,
      _promptMeta: {
        source_type: 'prompt',
        research_prompt: prompt,
        research_source_urls: selectedSources.map(s => s.url),
        source_count: selectedSources.length,
      }
    });
  }, [selectedIds, sources, hasSearched, onDataChange, prompt, stats.totalWords]);

  // Handlers
  const handleSearch = useCallback(async () => {
    if (prompt.length < 30) return;

    setIsSearching(true);
    setError(null);

    try {
      const result = await researchTopic({
        prompt,
        dateRangeDays: dateRange,
        maxResults: 10,
      });

      const foundSources = result.sources || result.results || [];
      setSources(foundSources);
      setSearchQueries(result.search_queries || []);
      setHasSearched(true);

      // Select top 5 by default
      const defaultSelected = new Set();
      foundSources.slice(0, 5).forEach(s => {
        defaultSelected.add(s.id || s.url);
      });
      setSelectedIds(defaultSelected);
    } catch (err) {
      setError(err.message || 'Erro ao pesquisar fontes');
      setHasSearched(true);
    } finally {
      setIsSearching(false);
    }
  }, [prompt, dateRange]);

  const handleToggleSource = useCallback((sourceKey) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sourceKey)) {
        newSet.delete(sourceKey);
      } else {
        newSet.add(sourceKey);
      }
      return newSet;
    });
  }, []);

  const handleSearchAgain = useCallback(() => {
    setSources([]);
    setSelectedIds(new Set());
    setSearchQueries([]);
    setError(null);
    setHasSearched(false);
  }, []);

  // Helper to format domain from URL
  const getDomain = (source) => {
    if (source.domain) return source.domain;
    try {
      return new URL(source.url).hostname.replace('www.', '');
    } catch {
      return 'fonte';
    }
  };

  // Helper to get snippet preview
  const getSnippet = (source) => {
    const text = source.full_text || source.snippet || '';
    if (text.length <= 200) return text;
    return text.substring(0, 200) + '...';
  };

  // Helper to count words
  const getWordCount = (source) => {
    const text = source.full_text || '';
    return text.trim() ? text.split(/\s+/).filter(Boolean).length : 0;
  };

  // ── Phase B: Source Review ──
  if (hasSearched && !error && sources.length > 0) {
    return (
      <div className="space-y-6">
        <SourceBadge
          type="link"
          title="Pesquisa na Web"
          subtitle={`${sources.length} fontes encontradas`}
          onChangeSource={onChangeSource}
        />

        <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b border-light-gray">
            <h3 className="font-semibold text-dark-gray">
              Fontes encontradas ({sources.length} resultados)
            </h3>
            {searchQueries.length > 0 && (
              <p className="text-sm text-medium-gray mt-1">
                Buscas realizadas: {searchQueries.map((q, i) => (
                  <span key={i}>
                    {i > 0 && ', '}
                    <span className="italic">&ldquo;{q}&rdquo;</span>
                  </span>
                ))}
              </p>
            )}
          </div>

          {/* Source list */}
          <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto">
            {sources.map((source, index) => {
              const sourceKey = source.id || source.url;
              const isSelected = selectedIds.has(sourceKey);
              const wordCount = getWordCount(source);

              return (
                <div
                  key={sourceKey || index}
                  onClick={() => handleToggleSource(sourceKey)}
                  className={`
                    p-4 rounded-lg border transition-all cursor-pointer
                    ${isSelected
                      ? 'border-tmc-orange bg-orange-50'
                      : 'border-gray-200 bg-white hover:shadow-md'
                    }
                  `}
                >
                  <div className="flex items-start gap-3">
                    {/* Checkbox */}
                    <div
                      className={`
                        w-5 h-5 rounded border-2 flex-shrink-0 mt-0.5
                        flex items-center justify-center
                        ${isSelected
                          ? 'bg-tmc-orange border-tmc-orange'
                          : 'border-medium-gray'
                        }
                      `}
                    >
                      {isSelected && (
                        <Check size={12} className="text-white" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <h4 className="font-semibold text-dark-gray mb-1 leading-tight">
                        {source.title || 'Sem título'}
                      </h4>

                      <div className="flex items-center gap-2 text-xs text-medium-gray mb-2 flex-wrap">
                        <span className="flex items-center gap-1">
                          <Globe size={12} />
                          {getDomain(source)}
                        </span>
                        {source.published_date && (
                          <>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <Calendar size={12} />
                              {source.published_date}
                            </span>
                          </>
                        )}
                        <span>•</span>
                        <span>{wordCount} palavras</span>
                        {source.is_gov_source && (
                          <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                            Gov
                          </span>
                        )}
                      </div>

                      <p className="text-sm text-medium-gray line-clamp-3">
                        {getSnippet(source)}
                      </p>
                    </div>

                    {/* External link */}
                    {source.url && (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 text-medium-gray hover:text-tmc-orange transition-colors flex-shrink-0"
                        title="Abrir fonte"
                      >
                        <ExternalLink size={16} />
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selection summary bar */}
          <div className="border-t border-light-gray px-4 py-3 bg-off-white/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-medium-gray">
                <Search size={16} className="text-tmc-orange" />
                <span>
                  <strong className="text-dark-gray">{stats.selectedCount}</strong> fontes selecionadas
                  <span className="mx-2">&middot;</span>
                  ~<strong className="text-dark-gray">{stats.totalWords.toLocaleString()}</strong> palavras
                </span>
              </div>

              {isInsufficient && (
                <div className="flex items-center gap-1.5 text-amber-600 text-sm">
                  <AlertTriangle size={14} />
                  <span>Material insuficiente. Selecione mais fontes.</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-start">
          <button
            onClick={handleSearchAgain}
            className="flex items-center gap-2 px-4 py-2 text-sm text-medium-gray hover:text-tmc-orange border border-light-gray rounded-lg hover:border-tmc-orange/50 transition-colors"
          >
            <RefreshCw size={16} />
            Pesquisar novamente
          </button>
        </div>
      </div>
    );
  }

  // ── Phase A: Prompt Input ──
  return (
    <div className="space-y-6">
      <SourceBadge
        type="link"
        title="Pesquisa na Web"
        subtitle="Descreva o tema para buscar fontes"
        onChangeSource={onChangeSource}
      />

      <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-light-gray flex items-center gap-2">
          <Search size={20} className="text-tmc-orange" />
          <h3 className="font-semibold text-dark-gray">Pesquisar Fontes por Tema</h3>
        </div>

        {/* Form */}
        <div className="p-4 space-y-4">
          {/* Prompt textarea */}
          <div>
            <label className="block text-sm font-medium text-dark-gray mb-1.5">
              Descreva o tema da pesquisa
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              maxLength={500}
              placeholder="Descreva o tema que deseja pesquisar..."
              className="w-full h-32 p-4 border border-light-gray rounded-lg resize-none text-sm text-dark-gray leading-relaxed focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange placeholder:text-medium-gray/60"
            />
            <div className="flex items-center justify-between mt-1.5">
              <span className={`text-xs ${prompt.length < 30 ? 'text-amber-500' : 'text-medium-gray'}`}>
                {prompt.length < 30 ? `Mínimo 30 caracteres (faltam ${30 - prompt.length})` : 'Pronto para pesquisar'}
              </span>
              <span className={`text-xs ${prompt.length > 500 ? 'text-red-500' : 'text-medium-gray'}`}>
                {prompt.length}/500
              </span>
            </div>
          </div>

          {/* Date range */}
          <div>
            <label className="block text-sm font-medium text-dark-gray mb-1.5">
              Período de busca
            </label>
            <div className="relative">
              <Calendar size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-medium-gray pointer-events-none" />
              <select
                value={dateRange}
                onChange={(e) => setDateRange(Number(e.target.value))}
                className="w-full pl-10 pr-4 py-2.5 border border-light-gray rounded-lg text-sm text-dark-gray focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange appearance-none bg-white"
              >
                {DATE_RANGE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertTriangle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm text-red-700">{error}</p>
                <button
                  onClick={handleSearch}
                  className="text-sm text-tmc-orange hover:underline mt-1"
                >
                  Tentar novamente
                </button>
              </div>
            </div>
          )}

          {/* No results message */}
          {hasSearched && !error && sources.length === 0 && (
            <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle size={16} className="text-amber-500 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-amber-700">
                Nenhuma fonte encontrada para este tema. Tente ampliar o período ou reformular a pesquisa.
              </p>
            </div>
          )}

          {/* Search button */}
          <button
            onClick={handleSearch}
            disabled={prompt.length < 30 || isSearching}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-tmc-orange text-white rounded-lg font-medium hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSearching ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Pesquisando fontes...
              </>
            ) : (
              <>
                <Search size={18} />
                Pesquisar Fontes
              </>
            )}
          </button>
        </div>
      </div>

      {/* Tip */}
      <div className="bg-orange-50 border border-orange-100 rounded-lg p-4">
        <p className="text-sm text-dark-gray">
          <strong>Dica:</strong> Seja específico na descrição do tema. Por exemplo, em vez de
          &ldquo;economia&rdquo;, tente &ldquo;impacto da taxa Selic na inflação em março de 2026&rdquo;.
          Quanto mais detalhado, melhores serão as fontes encontradas.
        </p>
      </div>
    </div>
  );
};

TextoBasePrompt.propTypes = {
  onDataChange: PropTypes.func.isRequired,
  initialData: PropTypes.object,
  fonte: PropTypes.object,
  onChangeSource: PropTypes.func,
};

export default TextoBasePrompt;
