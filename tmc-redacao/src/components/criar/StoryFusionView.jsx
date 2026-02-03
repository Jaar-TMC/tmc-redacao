import { useState, useCallback, useMemo, useEffect } from 'react';
import PropTypes from 'prop-types';
import { LayoutGrid, FileText, RefreshCw, AlertCircle, Sparkles } from 'lucide-react';
import { SourceBadge, ContentStats, ModeTabs } from './index';
import GroupedStructureTab from './GroupedStructureTab';
import OriginalTextsTab from './OriginalTextsTab';
import { mergeTopics } from '../../services/api';

/**
 * StoryFusionView - Multi-Source Article Composition
 *
 * Transforms from "select topics from articles" to "build a story from facts across sources."
 * AI analyzes all selected articles together and organizes by story element, not source.
 *
 * Two viewing modes:
 * 1. Estrutura Agrupada: AI-grouped view showing story elements with version selection
 * 2. Textos Originais: All original texts side-by-side with edit capability
 */

const MAX_ARTICLES = 3;

const StoryFusionView = ({
  fonte,
  onChangeSource,
  onDataChange
}) => {
  // Tab state
  const [activeTab, setActiveTab] = useState('grouped');

  // Loading/Error states
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loadingProgress, setLoadingProgress] = useState(0);

  // Merged data from AI
  const [mergedData, setMergedData] = useState(null);

  // Selection state for grouped view
  const [selectedVersions, setSelectedVersions] = useState({});
  const [includedGroups, setIncludedGroups] = useState(new Set());
  const [includedExclusives, setIncludedExclusives] = useState(new Set());
  const [includedQuotes, setIncludedQuotes] = useState(new Set());

  // Edited original texts
  const [editedTexts, setEditedTexts] = useState({});

  // Articles from fonte
  const articles = useMemo(() => {
    if (!fonte?.dados || !Array.isArray(fonte.dados)) return [];
    return fonte.dados.slice(0, MAX_ARTICLES);
  }, [fonte?.dados]);

  // Tabs configuration
  const tabs = useMemo(() => [
    { id: 'grouped', label: 'Estrutura Agrupada', icon: <LayoutGrid size={16} /> },
    { id: 'originals', label: 'Textos Originais', icon: <FileText size={16} /> }
  ], []);

  // Initialize edited texts from articles
  useEffect(() => {
    if (articles.length > 0) {
      const initialTexts = {};
      articles.forEach(article => {
        initialTexts[article.id] = {
          original: article.content || article.preview || '',
          edited: article.content || article.preview || '',
          source: article.source
        };
      });
      setEditedTexts(initialTexts);
    }
  }, [articles]);

  // Load merged topics from API
  const loadMergedTopics = useCallback(async () => {
    if (articles.length === 0) return;

    setIsLoading(true);
    setError(null);
    setLoadingProgress(0);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setLoadingProgress(prev => Math.min(prev + 10, 90));
    }, 500);

    try {
      // Prepare articles for API - ensure we have content
      const articlesForApi = articles.map(article => {
        const content = article.content || article.preview || '';
        return {
          id: String(article.id),
          title: article.title,
          content: content,
          preview: article.preview || content.substring(0, 500),
          source: article.source
        };
      });

      // Validate that articles have enough content
      const invalidArticles = articlesForApi.filter(a => (a.content?.length || 0) < 50);
      if (invalidArticles.length > 0) {
        throw new Error(
          `${invalidArticles.length} matéria(s) não possuem conteúdo suficiente para análise. ` +
          `Selecione matérias com mais texto.`
        );
      }

      const result = await mergeTopics(articlesForApi);

      clearInterval(progressInterval);
      setLoadingProgress(100);

      setMergedData(result);

      // Initialize selections - select all groups by default with AI recommendations
      const initialGroups = new Set();
      const initialVersions = {};

      result.groups?.forEach(group => {
        initialGroups.add(group.id);
        // Select AI recommended version or first version
        const recommended = group.versions?.find(v => v.isRecommended) ||
                          group.versions?.[0];
        if (recommended) {
          initialVersions[group.id] = recommended.id;
        }
      });

      // Include all exclusives by default
      const initialExclusives = new Set(result.exclusives?.map(e => e.id) || []);

      // Include all quotes by default
      const initialQuotes = new Set(result.quotes?.map(q => q.id) || []);

      setIncludedGroups(initialGroups);
      setSelectedVersions(initialVersions);
      setIncludedExclusives(initialExclusives);
      setIncludedQuotes(initialQuotes);

    } catch (err) {
      clearInterval(progressInterval);
      console.error('Error merging topics:', err);

      // Parse error message for better UX
      let errorMessage = 'Erro ao agrupar conteúdo. Tente novamente.';
      if (err.message) {
        if (err.message.includes('conteúdo suficiente') || err.message.includes('50 characters')) {
          errorMessage = 'Uma ou mais matérias não possuem conteúdo suficiente. Selecione matérias com mais texto.';
        } else if (err.message.includes('503') || err.message.includes('indisponível')) {
          errorMessage = 'O serviço de IA está temporariamente indisponível. Tente novamente em alguns segundos.';
        } else if (err.message.includes('timeout') || err.message.includes('Timeout')) {
          errorMessage = 'A análise demorou muito. Tente com menos matérias ou textos menores.';
        } else {
          errorMessage = err.message;
        }
      }

      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [articles]);

  // Load on mount or when articles change
  useEffect(() => {
    if (articles.length > 0 && !mergedData && !isLoading && !error) {
      loadMergedTopics();
    }
  }, [articles.length, mergedData, isLoading, error, loadMergedTopics]);

  // Handlers for grouped view
  const handleVersionSelect = useCallback((groupId, versionId) => {
    setSelectedVersions(prev => ({
      ...prev,
      [groupId]: versionId
    }));
  }, []);

  const handleToggleGroup = useCallback((groupId) => {
    setIncludedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupId)) {
        newSet.delete(groupId);
      } else {
        newSet.add(groupId);
      }
      return newSet;
    });
  }, []);

  const handleToggleExclusive = useCallback((exclusiveId) => {
    setIncludedExclusives(prev => {
      const newSet = new Set(prev);
      if (newSet.has(exclusiveId)) {
        newSet.delete(exclusiveId);
      } else {
        newSet.add(exclusiveId);
      }
      return newSet;
    });
  }, []);

  const handleToggleQuote = useCallback((quoteId) => {
    setIncludedQuotes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(quoteId)) {
        newSet.delete(quoteId);
      } else {
        newSet.add(quoteId);
      }
      return newSet;
    });
  }, []);

  // Handler for original texts editing
  const handleTextEdit = useCallback((articleId, newText) => {
    setEditedTexts(prev => ({
      ...prev,
      [articleId]: {
        ...prev[articleId],
        edited: newText
      }
    }));
  }, []);

  // Calculate stats
  const stats = useMemo(() => {
    let selectedElements = 0;
    let totalElements = 0;
    let wordCount = 0;

    if (mergedData) {
      // Count groups
      totalElements += mergedData.groups?.length || 0;
      mergedData.groups?.forEach(group => {
        if (includedGroups.has(group.id)) {
          selectedElements++;
          const selectedVersion = group.versions?.find(v => v.id === selectedVersions[group.id]);
          wordCount += selectedVersion?.wordCount || 0;
        }
      });

      // Count exclusives
      totalElements += mergedData.exclusives?.length || 0;
      mergedData.exclusives?.forEach(exc => {
        if (includedExclusives.has(exc.id)) {
          selectedElements++;
          wordCount += exc.wordCount || 0;
        }
      });

      // Count quotes
      totalElements += mergedData.quotes?.length || 0;
      mergedData.quotes?.forEach(quote => {
        if (includedQuotes.has(quote.id)) {
          selectedElements++;
          wordCount += quote.text?.split(/\s+/).filter(Boolean).length || 0;
        }
      });
    }

    return {
      selected: selectedElements,
      total: totalElements,
      words: wordCount,
      sources: articles.length
    };
  }, [mergedData, includedGroups, includedExclusives, includedQuotes, selectedVersions, articles.length]);

  // Notify parent of data changes
  useEffect(() => {
    if (onDataChange && mergedData) {
      const selectedContent = {
        groups: mergedData.groups?.filter(g => includedGroups.has(g.id)).map(g => ({
          ...g,
          selectedVersion: g.versions?.find(v => v.id === selectedVersions[g.id])
        })) || [],
        exclusives: mergedData.exclusives?.filter(e => includedExclusives.has(e.id)) || [],
        quotes: mergedData.quotes?.filter(q => includedQuotes.has(q.id)) || [],
        editedTexts,
        wordCount: stats.words,
        activeTab
      };
      onDataChange(selectedContent);
    }
  }, [mergedData, includedGroups, includedExclusives, includedQuotes, selectedVersions, editedTexts, stats.words, activeTab, onDataChange]);

  // Empty state
  if (articles.length === 0) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-xl border border-light-gray p-8 text-center">
          <div className="w-16 h-16 bg-off-white rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={32} className="text-medium-gray" />
          </div>
          <h3 className="font-semibold text-dark-gray mb-2">
            Nenhuma matéria selecionada
          </h3>
          <p className="text-sm text-medium-gray mb-4">
            Volte para a tela de Redação e selecione até 3 matérias para combinar.
          </p>
          <button
            onClick={onChangeSource}
            className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium"
          >
            Selecionar matérias
          </button>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <SourceBadge
          type="feed"
          title={`${articles.length} matérias selecionadas`}
          onChangeSource={onChangeSource}
        />

        <div className="bg-white rounded-xl border border-light-gray p-12 text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-tmc-orange/20 to-tmc-orange/5 rounded-full flex items-center justify-center mx-auto mb-6">
            <Sparkles size={36} className="text-tmc-orange animate-pulse" />
          </div>
          <h3 className="font-semibold text-dark-gray mb-2">
            Analisando matérias com IA...
          </h3>
          <p className="text-sm text-medium-gray mb-6">
            Identificando elementos comuns, exclusivos e citações
          </p>

          {/* Progress bar */}
          <div className="w-full max-w-xs mx-auto bg-off-white rounded-full h-2 overflow-hidden">
            <div
              className="h-full bg-tmc-orange transition-all duration-300 ease-out"
              style={{ width: `${loadingProgress}%` }}
            />
          </div>
          <p className="text-xs text-medium-gray mt-2">{loadingProgress}%</p>
        </div>
      </div>
    );
  }

  // Error state with fallback
  if (error) {
    return (
      <div className="space-y-6">
        <SourceBadge
          type="feed"
          title={`${articles.length} matérias selecionadas`}
          onChangeSource={onChangeSource}
        />

        <div className="bg-white rounded-xl border border-red-200 p-8 text-center">
          <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={32} className="text-red-500" />
          </div>
          <h3 className="font-semibold text-dark-gray mb-2">
            Não foi possível agrupar automaticamente
          </h3>
          <p className="text-sm text-medium-gray mb-4">
            {error}
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={loadMergedTopics}
              className="flex items-center gap-2 px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium"
            >
              <RefreshCw size={16} />
              Tentar novamente
            </button>
            <button
              onClick={onChangeSource}
              className="px-4 py-2 border border-light-gray text-medium-gray rounded-lg hover:border-dark-gray hover:text-dark-gray transition-colors"
            >
              Mudar seleção
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SourceBadge
        type="feed"
        title={`${articles.length} matérias combinadas`}
        onChangeSource={onChangeSource}
      />

      <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
        {/* Header with tabs */}
        <div className="p-4 border-b border-light-gray">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-dark-gray">
                Story Fusion View
              </h3>
              {mergedData?.summary?.mainTopic && (
                <p className="text-sm text-medium-gray line-clamp-1">
                  {mergedData.summary.mainTopic}
                </p>
              )}
            </div>
            <button
              onClick={loadMergedTopics}
              className="flex items-center gap-1 text-sm text-medium-gray hover:text-tmc-orange transition-colors"
              title="Reprocessar agrupamento"
            >
              <RefreshCw size={14} />
              <span className="hidden sm:inline">Reprocessar</span>
            </button>
          </div>

          <ModeTabs
            activeTab={activeTab}
            onTabChange={setActiveTab}
            tabs={tabs}
          />
        </div>

        {/* Tab content */}
        <div className="p-4">
          {activeTab === 'grouped' ? (
            <GroupedStructureTab
              groups={mergedData?.groups || []}
              exclusives={mergedData?.exclusives || []}
              quotes={mergedData?.quotes || []}
              selectedVersions={selectedVersions}
              includedGroups={includedGroups}
              includedExclusives={includedExclusives}
              includedQuotes={includedQuotes}
              onVersionSelect={handleVersionSelect}
              onToggleGroup={handleToggleGroup}
              onToggleExclusive={handleToggleExclusive}
              onToggleQuote={handleToggleQuote}
              articles={articles}
            />
          ) : (
            <OriginalTextsTab
              articles={articles}
              editedTexts={editedTexts}
              onTextEdit={handleTextEdit}
            />
          )}
        </div>

        {/* Footer stats */}
        <ContentStats
          selectedCount={stats.selected}
          totalCount={stats.total}
          wordCount={stats.words}
          sourceCount={stats.sources}
          variant="feed"
        />
      </div>
    </div>
  );
};

StoryFusionView.propTypes = {
  fonte: PropTypes.shape({
    tipo: PropTypes.string,
    dados: PropTypes.array
  }),
  onChangeSource: PropTypes.func,
  onDataChange: PropTypes.func
};

export default StoryFusionView;
