import { useState, useCallback, useEffect, useMemo } from 'react';
import { TrendingUp, Sparkles, FileText, RefreshCw } from 'lucide-react';
import TrendsSidebar from '../components/layout/TrendsSidebar';
import ActionPanel from '../components/layout/ActionPanel';
import FilterBar from '../components/ui/FilterBar';
import ArticleCard from '../components/cards/ArticleCard';
import Skeleton from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';
import ActiveFiltersBar from '../components/ui/ActiveFiltersBar';
import SmartEmptyState from '../components/ui/SmartEmptyState';
import Pagination from '../components/ui/Pagination';
import { transformArticles } from '../utils/transformers';
import { useArticles, useFilters, useUI } from '../context';
import { useArticlesQuery } from '../hooks/useArticles';
import { useOnboarding, TOUR_IDS } from '../components/onboarding';

// Stable function outside component - no re-creation on render
const deduplicateByTitle = (articles) => {
  const seen = new Set();
  return articles.filter(article => {
    const normalizedTitle = (article.title || '').toLowerCase().trim();
    if (seen.has(normalizedTitle)) return false;
    seen.add(normalizedTitle);
    return true;
  });
};

const ITEMS_PER_PAGE = 20;

// Stable noop function - avoids creating new arrow function on each render
const noop = () => {};

// Map FiltersContext values to API query param names
const buildApiFilters = (filters) => {
  const mapped = {};
  if (filters.searchQuery) mapped.search = filters.searchQuery;
  if (filters.tag) mapped.tag = filters.tag;
  if (filters.category) mapped.category = filters.category;
  if (filters.source) mapped.source = filters.source;
  if (filters.urgency) mapped.max_hours = filters.urgency;
  if (filters.scoreClassification) mapped.classification = filters.scoreClassification;
  if (filters.sortOrder && filters.sortOrder !== 'newest') mapped.order_by = filters.sortOrder;
  return mapped;
};

const RedacaoPage = () => {
  const { selectedArticles, addArticle, removeArticle, clearSelection } = useArticles();
  const { filters } = useFilters();
  const {
    trendsSidebarOpen,
    actionPanelOpen,
    openTrendsSidebar,
    closeTrendsSidebar,
    openActionPanel,
    closeActionPanel,
  } = useUI();
  const { shouldShowTour, startTour } = useOnboarding();

  // Pagination State (page is local; TanStack Query re-fetches on change)
  const [currentPage, setCurrentPage] = useState(1);

  // Reset to page 1 when any filter changes
  const filtersKey = JSON.stringify(filters);
  const [prevFiltersKey, setPrevFiltersKey] = useState(filtersKey);
  if (filtersKey !== prevFiltersKey) {
    setPrevFiltersKey(filtersKey);
    if (currentPage !== 1) {
      setCurrentPage(1);
    }
  }

  // Map frontend filter names to API param names
  const apiFilters = useMemo(() => buildApiFilters(filters), [filters]);

  // TanStack Query handles fetching, caching, abort, cursor tracking
  const {
    data: queryData,
    isLoading: queryIsLoading,
    isFetching,
    isPlaceholderData,
    error: queryError,
    refetch,
  } = useArticlesQuery(apiFilters, currentPage, ITEMS_PER_PAGE);

  // Derive UI state from query result
  const articles = useMemo(() => {
    const items = queryData?.items || [];
    const transformed = transformArticles(items);
    return deduplicateByTitle(transformed);
  }, [queryData?.items]);

  const totalItems = queryData?.total ?? articles.length;
  const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE) || 1;
  const urgencyCounts = queryData?.urgency_counts || { now: 0, recent: 0, today: 0, all: 0 };
  const facets = queryData?.facets || null;

  // Show skeleton when truly loading (no previous data to show)
  const showSkeleton = queryIsLoading && !isPlaceholderData;
  const error = queryError?.message || (queryError ? 'Erro ao carregar matérias' : null);

  // Retry fetch after error
  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleSelectArticle = useCallback((article) => {
    addArticle(article);
  }, [addArticle]);

  const handleRemoveArticle = useCallback((articleId) => {
    removeArticle(articleId);
  }, [removeArticle]);

  const handleClearAll = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  // Memoize set of selected article IDs for stable O(1) lookups without re-creating on each render
  const selectedArticleIds = useMemo(
    () => new Set(selectedArticles.map(a => a.id)),
    [selectedArticles]
  );

  // Handle page change from Pagination component
  const handlePageChange = useCallback((page) => {
    setCurrentPage(page);
    // Scroll to top of article grid when changing pages
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Auto-trigger onboarding tour for first-time users
  useEffect(() => {
    if (shouldShowTour(TOUR_IDS.HOME) && !isFetching && articles.length > 0) {
      // Delay to ensure page is fully loaded
      const timeoutId = setTimeout(() => {
        startTour(TOUR_IDS.HOME);
      }, 800);
      return () => clearTimeout(timeoutId);
    }
  }, [shouldShowTour, startTour, isFetching, articles.length]);

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
        <div className="hidden lg:block w-72 shrink-0 sticky top-16 h-[calc(100vh-4rem)]" data-tour="trends-sidebar">
          <TrendsSidebar isOpen={true} onClose={noop} />
        </div>

        {/* Mobile Trends Sidebar - Hidden on desktop */}
        <div className="lg:hidden">
          <TrendsSidebar
            isOpen={trendsSidebarOpen}
            onClose={closeTrendsSidebar}
          />
        </div>

        {/* Main Content - Articles Grid */}
        <div className="flex-1 min-w-0 p-4 md:p-6 mt-16 lg:mt-0">
          <div data-tour="filter-bar">
            <FilterBar urgencyCounts={urgencyCounts} facets={facets} />
          </div>

          <ActiveFiltersBar />

          {showSkeleton ? (
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
              <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mb-4">
                <RefreshCw size={28} className="text-tmc-orange" />
              </div>
              <h3 className="text-lg font-semibold text-dark-gray mb-2">Não foi possível carregar as matérias</h3>
              <p className="text-sm text-medium-gray mb-6 text-center max-w-md">
                {error}
              </p>
              <button
                onClick={handleRetry}
                className="px-6 py-3 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center gap-2"
              >
                <RefreshCw size={18} />
                Tentar novamente
              </button>
            </div>
          ) : articles.length === 0 ? (
            (filters.searchQuery || filters.tag || filters.category || filters.source || filters.scoreClassification) ? (
              <SmartEmptyState />
            ) : (
              <EmptyState
                icon={FileText}
                title="Nenhuma matéria encontrada"
                description="Não encontramos matérias no momento. Aguarde novas coletas."
              />
            )
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-2 gap-4">
                {articles.map((article, index) => (
                  <div key={article.id} data-tour={index === 0 ? "article-card" : undefined}>
                    <ArticleCard
                      article={article}
                      isSelected={selectedArticleIds.has(article.id)}
                      onSelect={handleSelectArticle}
                    />
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mb-20 lg:mb-8">
                  <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    totalItems={totalItems}
                    itemsPerPage={ITEMS_PER_PAGE}
                    onPageChange={handlePageChange}
                    showInfo={true}
                  />
                </div>
              )}
            </>
          )}
        </div>

        {/* Right Sidebar - Action Panel (Desktop sticky, Mobile bottom sheet) */}
        <div className="hidden lg:block w-72 xl:w-80 shrink-0 p-4 sticky top-16 h-[calc(100vh-4rem)]">
          <ActionPanel
            selectedArticles={selectedArticles}
            onRemove={handleRemoveArticle}
            onClearAll={handleClearAll}
            isOpen={true}
            onClose={noop}
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
