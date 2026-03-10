import { useState, useCallback, useEffect, useRef } from 'react';
import { TrendingUp, Sparkles, FileText, RefreshCw, AlertCircle } from 'lucide-react';
import TrendsSidebar from '../components/layout/TrendsSidebar';
import ActionPanel from '../components/layout/ActionPanel';
import FilterBar from '../components/ui/FilterBar';
import ArticleCard from '../components/cards/ArticleCard';
import Skeleton from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';
import ActiveFiltersBar from '../components/ui/ActiveFiltersBar';
import SmartEmptyState from '../components/ui/SmartEmptyState';
import Pagination from '../components/ui/Pagination';
import { getArticles } from '../services/api';
import { transformArticles } from '../utils/transformers';
import { useArticles, useFilters, useUI } from '../context';
import { useArticlesCache } from '../context/ArticlesCacheContext';
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

// Build API params from filters and page - shared between fetch and retry
const buildArticleParams = (filters, page) => ({
  limit: ITEMS_PER_PAGE,
  page,
  ...(filters.searchQuery && { search: filters.searchQuery }),
  ...(filters.tag && { tag: filters.tag }),
  ...(filters.category && { category: filters.category }),
  ...(filters.source && { source: filters.source }),
  ...(filters.urgency && { max_hours: filters.urgency }),
  ...(filters.scoreClassification && { classification: filters.scoreClassification }),
  ...(filters.sortOrder && filters.sortOrder !== 'newest' && { order_by: filters.sortOrder }),
});

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
  const { shouldShowTour, startTour } = useOnboarding();
  const { getCachedData, setCachedData } = useArticlesCache();

  // API State
  const [articles, setArticles] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [_isInitialized, setIsInitialized] = useState(false);
  const [urgencyCounts, setUrgencyCounts] = useState({ now: 0, recent: 0, today: 0, all: 0 });
  const [facets, setFacets] = useState(null);

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Ref for AbortController
  const abortControllerRef = useRef(null);

  // Ref to track previous filter values to detect filter changes vs page changes
  const prevFiltersRef = useRef({
    searchQuery: filters.searchQuery,
    tag: filters.tag,
    category: filters.category,
    source: filters.source,
    urgency: filters.urgency,
    scoreClassification: filters.scoreClassification,
    sortOrder: filters.sortOrder,
  });

  // Ref to skip redundant fetch after page reset
  const skipNextFetchRef = useRef(false);

  // Fetch articles from API with AbortController for request cancellation
  useEffect(() => {
    // Skip this fetch if flagged (happens after filter-triggered page reset)
    if (skipNextFetchRef.current) {
      skipNextFetchRef.current = false;
      return;
    }

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Check if filters changed (not just page)
    const filtersChanged =
      prevFiltersRef.current.searchQuery !== filters.searchQuery ||
      prevFiltersRef.current.tag !== filters.tag ||
      prevFiltersRef.current.category !== filters.category ||
      prevFiltersRef.current.source !== filters.source ||
      prevFiltersRef.current.urgency !== filters.urgency ||
      prevFiltersRef.current.scoreClassification !== filters.scoreClassification ||
      prevFiltersRef.current.sortOrder !== filters.sortOrder;

    // Update prev filters ref
    prevFiltersRef.current = {
      searchQuery: filters.searchQuery,
      tag: filters.tag,
      category: filters.category,
      source: filters.source,
      urgency: filters.urgency,
      scoreClassification: filters.scoreClassification,
      sortOrder: filters.sortOrder,
    };

    // When filters change, always fetch from page 1 (and sync state)
    // When only page changes, use the current page
    const effectivePage = filtersChanged ? 1 : currentPage;

    // Sync page state if filters changed and we weren't on page 1
    // Set flag to skip the next fetch triggered by setCurrentPage
    if (filtersChanged && currentPage !== 1) {
      skipNextFetchRef.current = true;
      setCurrentPage(1);
      // Continue with the fetch using effectivePage=1
    }

    // Check cache first
    const cachedData = getCachedData(filters, effectivePage);
    if (cachedData) {
      setArticles(cachedData.articles);
      setTotalItems(cachedData.totalItems);
      setTotalPages(cachedData.totalPages);
      if (cachedData.urgencyCounts) {
        setUrgencyCounts(cachedData.urgencyCounts);
      }
      if (cachedData.facets) {
        setFacets(cachedData.facets);
      }
      setIsLoading(false);
      setIsInitialized(true);
      return;
    }

    // Create new AbortController for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const fetchArticles = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const params = buildArticleParams(filters, effectivePage);
        const response = await getArticles(params, { signal: abortController.signal });

        // Only update state if request wasn't aborted
        if (!abortController.signal.aborted) {
          const transformedArticles = transformArticles(response?.items || []);
          const uniqueArticles = deduplicateByTitle(transformedArticles);

          setArticles(uniqueArticles);

          // Update urgency counts from server response
          if (response?.urgency_counts) {
            setUrgencyCounts(response.urgency_counts);
          }

          if (response?.facets) {
            setFacets(response.facets);
          }

          // Update pagination info from response - use nullish coalescing to handle 0 correctly
          const total = response?.total ?? uniqueArticles.length;
          setTotalItems(total);
          setTotalPages(Math.ceil(total / ITEMS_PER_PAGE) || 1);

          // Save to cache
          setCachedData(filters, effectivePage, {
            articles: uniqueArticles,
            totalItems: total,
            totalPages: Math.ceil(total / ITEMS_PER_PAGE) || 1,
            urgencyCounts: response?.urgency_counts || null,
            facets: response?.facets || null,
          });

          setIsInitialized(true);
        }
      } catch (err) {
        // Ignore AbortError - this is expected when request is cancelled
        if (err.name === 'AbortError') {
          return;
        }
        console.error('Error fetching articles:', err);
        setError(err.message || 'Erro ao carregar matérias');
      } finally {
        // Only set loading to false if not aborted
        if (!abortController.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    fetchArticles();

    // Cleanup: abort request when dependencies change or component unmounts
    return () => {
      abortController.abort();
    };
  }, [filters.searchQuery, filters.tag, filters.category, filters.source, filters.urgency, filters.scoreClassification, filters.sortOrder, currentPage, getCachedData, setCachedData]);

  // Retry fetch after error
  const handleRetry = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = buildArticleParams(filters, currentPage);
      const response = await getArticles(params);
      const transformedArticles = transformArticles(response?.items);
      const uniqueArticles = deduplicateByTitle(transformedArticles);
      setArticles(uniqueArticles);

      // Update urgency counts from response, or calculate from article timestamps as fallback
      if (response?.urgency_counts) {
        setUrgencyCounts(response.urgency_counts);
      }

      if (response?.facets) {
        setFacets(response.facets);
      }

      // Update pagination info from response - use nullish coalescing to handle 0 correctly
      const total = response?.total ?? uniqueArticles.length;
      setTotalItems(total);
      setTotalPages(Math.ceil(total / ITEMS_PER_PAGE) || 1);

      // Save to cache
      setCachedData(filters, currentPage, {
        articles: uniqueArticles,
        totalItems: total,
        totalPages: Math.ceil(total / ITEMS_PER_PAGE) || 1,
        urgencyCounts: response?.urgency_counts || null,
        facets: response?.facets || null,
      });

      setIsInitialized(true);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('A requisição expirou. Tente novamente.');
      } else {
        console.error('Error fetching articles:', err);
        setError(err.message || 'Erro ao carregar matérias');
      }
    } finally {
      setIsLoading(false);
    }
  }, [filters, currentPage, setCachedData]);

  const handleSelectArticle = useCallback((article) => {
    addArticle(article);
  }, [addArticle]);

  const handleRemoveArticle = useCallback((articleId) => {
    removeArticle(articleId);
  }, [removeArticle]);

  const handleClearAll = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  // Handle page change from Pagination component
  const handlePageChange = useCallback((page) => {
    setCurrentPage(page);
    // Scroll to top of article grid when changing pages
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Auto-trigger onboarding tour for first-time users
  useEffect(() => {
    if (shouldShowTour(TOUR_IDS.HOME) && !isLoading && articles.length > 0) {
      // Delay to ensure page is fully loaded
      const timeoutId = setTimeout(() => {
        startTour(TOUR_IDS.HOME);
      }, 800);
      return () => clearTimeout(timeoutId);
    }
  }, [shouldShowTour, startTour, isLoading, articles.length]);

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
        <div className="flex-1 min-w-0 p-4 md:p-6 mt-16 lg:mt-0">
          <div data-tour="filter-bar">
            <FilterBar urgencyCounts={urgencyCounts} facets={facets} />
          </div>

          <ActiveFiltersBar />

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
                      isSelected={isArticleSelected(article.id)}
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
