import { useState, useMemo, useCallback, useEffect } from 'react';
import { TrendingUp, Sparkles, FileText, RefreshCw, AlertCircle } from 'lucide-react';
import TrendsSidebar from '../components/layout/TrendsSidebar';
import ActionPanel from '../components/layout/ActionPanel';
import FilterBar from '../components/ui/FilterBar';
import ArticleCard from '../components/cards/ArticleCard';
import Skeleton from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';
import Spinner from '../components/ui/Spinner';
import { getArticles } from '../services/api';
import { transformArticles } from '../utils/transformers';
import { useArticles, useFilters, useUI } from '../context';

const RedacaoPage = () => {
  const { selectedArticles, addArticle, removeArticle, clearSelection, isArticleSelected } = useArticles();
  const { filters } = useFilters();
  const {
    trendsSidebarOpen,
    actionPanelOpen,
    openTrendsSidebar,
    closeTrendsSidebar,
    openActionPanel,
    closeActionPanel,
  } = useUI();

  // API State
  const [articles, setArticles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const ARTICLES_PER_PAGE = 100;

  // Deduplicate articles by title (keep first occurrence)
  const deduplicateByTitle = (articles) => {
    const seen = new Set();
    return articles.filter(article => {
      const normalizedTitle = article.title.toLowerCase().trim();
      if (seen.has(normalizedTitle)) {
        return false;
      }
      seen.add(normalizedTitle);
      return true;
    });
  };

  // Fetch articles from API - re-fetch when search query or tag filter changes
  useEffect(() => {
    const fetchArticles = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Build API params - use server-side search for better results
        const params = {
          limit: ARTICLES_PER_PAGE,
          ...(filters.searchQuery && { search: filters.searchQuery }),
          ...(filters.tag && { tag: filters.tag }),
          ...(filters.category && { category: filters.category }),
          ...(filters.source && { source: filters.source }),
        };

        const response = await getArticles(params);
        const transformedArticles = transformArticles(response?.items);
        const uniqueArticles = deduplicateByTitle(transformedArticles);
        setArticles(uniqueArticles);
        setHasMore((response?.items?.length || 0) >= ARTICLES_PER_PAGE);
        setOffset(ARTICLES_PER_PAGE);
      } catch (err) {
        console.error('Error fetching articles:', err);
        setError(err.message || 'Erro ao carregar matérias');
      } finally {
        setIsLoading(false);
      }
    };
    fetchArticles();
  }, [filters.searchQuery, filters.tag, filters.category, filters.source]);

  // Retry fetch after error
  const handleRetry = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = {
        limit: ARTICLES_PER_PAGE,
        ...(filters.searchQuery && { search: filters.searchQuery }),
        ...(filters.tag && { tag: filters.tag }),
        ...(filters.category && { category: filters.category }),
        ...(filters.source && { source: filters.source }),
      };
      const response = await getArticles(params);
      const transformedArticles = transformArticles(response?.items);
      const uniqueArticles = deduplicateByTitle(transformedArticles);
      setArticles(uniqueArticles);
      setHasMore((response?.items?.length || 0) >= ARTICLES_PER_PAGE);
      setOffset(ARTICLES_PER_PAGE);
    } catch (err) {
      console.error('Error fetching articles:', err);
      setError(err.message || 'Erro ao carregar matérias');
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  const handleSelectArticle = useCallback((article) => {
    addArticle(article);
  }, [addArticle]);

  const handleRemoveArticle = useCallback((articleId) => {
    removeArticle(articleId);
  }, [removeArticle]);

  const handleClearAll = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  const handleLoadMore = useCallback(async () => {
    if (isLoadingMore || !hasMore) return;

    setIsLoadingMore(true);
    try {
      const params = {
        limit: ARTICLES_PER_PAGE,
        offset,
        ...(filters.searchQuery && { search: filters.searchQuery }),
        ...(filters.tag && { tag: filters.tag }),
        ...(filters.category && { category: filters.category }),
        ...(filters.source && { source: filters.source }),
      };
      const response = await getArticles(params);
      const newArticles = transformArticles(response?.items);
      setArticles(prev => deduplicateByTitle([...prev, ...newArticles]));
      setHasMore(newArticles.length >= ARTICLES_PER_PAGE);
      setOffset(prev => prev + ARTICLES_PER_PAGE);
    } catch (err) {
      console.error('Error loading more articles:', err);
    } finally {
      setIsLoadingMore(false);
    }
  }, [offset, isLoadingMore, hasMore, filters]);

  // Articles are now server-side filtered, so we just return them directly
  // Client-side filtering is only kept as a visual fallback during loading transitions
  const filteredArticles = useMemo(() => {
    // Since server-side filtering is now in place, articles are already filtered
    // We only need to do additional client-side filtering if the server doesn't support
    // certain filter types or during transitional states
    return articles;
  }, [articles]);

  return (
    <div className="min-h-screen pt-16 bg-off-white">
      {/* Mobile Toggle Buttons */}
      <div className="lg:hidden fixed top-20 left-4 right-4 z-30 flex gap-2" role="toolbar" aria-label="Ações rápidas">
        <button
          type="button"
          onClick={openTrendsSidebar}
          className="flex items-center gap-2 bg-tmc-orange text-white px-4 py-2 rounded-lg shadow-md text-sm font-semibold min-h-[44px]"
          aria-label="Abrir painel de tendências"
        >
          <TrendingUp size={18} aria-hidden="true" />
          <span>Tendências</span>
        </button>
        {selectedArticles.length > 0 && (
          <button
            type="button"
            onClick={openActionPanel}
            className="flex items-center gap-2 bg-tmc-dark-green text-white px-4 py-2 rounded-lg shadow-md text-sm font-semibold ml-auto min-h-[44px]"
            aria-label={`Abrir painel de ação - ${selectedArticles.length} matérias selecionadas`}
          >
            <Sparkles size={18} aria-hidden="true" />
            <span>{selectedArticles.length}</span>
          </button>
        )}
      </div>

      <div className="flex">
        {/* Left Sidebar - Trends (Desktop sticky, Mobile slideover) */}
        <div className="hidden lg:block w-72 sticky top-16 h-[calc(100vh-4rem)]">
          <TrendsSidebar isOpen={true} onClose={() => {}} />
        </div>

        {/* Mobile Trends Sidebar - Hidden on desktop */}
        <div className="lg:hidden">
          <TrendsSidebar
            isOpen={trendsSidebarOpen}
            onClose={closeTrendsSidebar}
          />
        </div>

        {/* Main Content - Articles Grid */}
        <div className="flex-1 p-4 md:p-6 mt-16 lg:mt-0">
          <FilterBar />

          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white rounded-xl border border-light-gray p-4 space-y-3">
                  <Skeleton variant="card" className="h-40" />
                  <Skeleton variant="title" />
                  <Skeleton className="w-full" />
                  <Skeleton className="w-2/3" />
                  <div className="flex gap-2 pt-2">
                    <Skeleton variant="button" className="w-20" />
                    <Skeleton variant="button" className="w-16" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-16">
              <AlertCircle size={48} className="text-red-500 mb-4" />
              <h3 className="text-lg font-semibold text-dark-gray mb-2">Erro ao carregar matérias</h3>
              <p className="text-sm text-medium-gray mb-6 text-center max-w-md">{error}</p>
              <button
                onClick={handleRetry}
                className="px-6 py-3 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center gap-2"
              >
                <RefreshCw size={18} />
                Tentar novamente
              </button>
            </div>
          ) : filteredArticles.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="Nenhuma matéria encontrada"
              description="Não encontramos matérias que correspondam aos filtros selecionados. Tente ajustar os filtros ou aguarde novas coletas."
            />
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-4">
                {filteredArticles.map((article) => (
                  <ArticleCard
                    key={article.id}
                    article={article}
                    isSelected={isArticleSelected(article.id)}
                    onSelect={handleSelectArticle}
                  />
                ))}
              </div>

              {/* Load More */}
              {hasMore && (
                <div className="flex justify-center mt-8 mb-20 lg:mb-8">
                  <button
                    type="button"
                    onClick={handleLoadMore}
                    disabled={isLoadingMore}
                    className="px-6 py-3 bg-white border border-light-gray rounded-lg text-sm font-medium text-dark-gray hover:bg-off-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 min-h-[44px]"
                    aria-label="Carregar mais matérias"
                  >
                    {isLoadingMore ? (
                      <>
                        <Spinner size="sm" />
                        <span>Carregando...</span>
                      </>
                    ) : (
                      'Carregar mais matérias'
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Right Sidebar - Action Panel (Desktop sticky, Mobile bottom sheet) */}
        <div className="hidden lg:block w-80 p-4 sticky top-16 h-[calc(100vh-4rem)]">
          <ActionPanel
            selectedArticles={selectedArticles}
            onRemove={handleRemoveArticle}
            onClearAll={handleClearAll}
            isOpen={true}
            onClose={() => {}}
          />
        </div>

        {/* Mobile Action Panel - Hidden on desktop */}
        <div className="lg:hidden">
          <ActionPanel
            selectedArticles={selectedArticles}
            onRemove={handleRemoveArticle}
            onClearAll={handleClearAll}
            isOpen={actionPanelOpen}
            onClose={closeActionPanel}
          />
        </div>
      </div>
    </div>
  );
};

export default RedacaoPage;
