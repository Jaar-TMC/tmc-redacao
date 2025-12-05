import { useState, useMemo, useCallback } from 'react';
import { TrendingUp, Sparkles, FileText } from 'lucide-react';
import TrendsSidebar from '../components/layout/TrendsSidebar';
import ActionPanel from '../components/layout/ActionPanel';
import FilterBar from '../components/ui/FilterBar';
import ArticleCard from '../components/cards/ArticleCard';
import Skeleton from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';
import Spinner from '../components/ui/Spinner';
import { mockArticles } from '../data/mockData';
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

  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const handleSelectArticle = useCallback((article) => {
    addArticle(article);
  }, [addArticle]);

  const handleRemoveArticle = useCallback((articleId) => {
    removeArticle(articleId);
  }, [removeArticle]);

  const handleClearAll = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  const handleLoadMore = useCallback(() => {
    setIsLoadingMore(true);
    // Simulate API call
    setTimeout(() => {
      setIsLoadingMore(false);
    }, 1000);
  }, []);

  // Filter articles based on active filters - memoized for performance
  const filteredArticles = useMemo(() => {
    return mockArticles.filter((article) => {
      if (filters.category && article.category !== filters.category) return false;
      if (filters.source && article.source !== filters.source) return false;
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        return (
          article.title.toLowerCase().includes(query) ||
          article.preview.toLowerCase().includes(query)
        );
      }
      return true;
    });
  }, [filters]);

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
