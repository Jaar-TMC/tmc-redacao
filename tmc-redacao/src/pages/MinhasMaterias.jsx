import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PenLine, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import MyArticleFilterBar from '../components/ui/MyArticleFilterBar';
import MyArticleCard from '../components/cards/MyArticleCard';
import Pagination from '../components/ui/Pagination';
import EmptyState, { EmptyStatePresets } from '../components/ui/EmptyState';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import ArticleViewModal from '../components/ui/ArticleViewModal';
import { getUserArticles, deleteUserArticle } from '../services/api';

const ITEMS_PER_PAGE = 6;

/**
 * MinhasMaterias Page
 *
 * Página principal de gerenciamento de matérias do usuário
 * Segue especificações do documento de planejamento UI/UX
 *
 * WCAG 2.1 Compliance:
 * - Proper heading hierarchy
 * - Keyboard navigation support
 * - Clear focus indicators
 * - Accessible filter and pagination controls
 */
const MinhasMaterias = () => {
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(1);
  const [filters, setFilters] = useState({
    searchQuery: '',
    status: null,
    category: null,
    dateRange: null,
    author: null
  });
  const [deleteDialog, setDeleteDialog] = useState({
    open: false,
    articleId: null,
    articleTitle: ''
  });

  // View modal state
  const [viewModal, setViewModal] = useState({
    open: false,
    article: null
  });

  // API state
  const [articles, setArticles] = useState([]);
  const [totalArticles, setTotalArticles] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch articles from API
  const fetchArticles = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = {
        page: currentPage,
        limit: ITEMS_PER_PAGE,
      };

      // Add filters to params (server-side filtering)
      if (filters.searchQuery) {
        params.search = filters.searchQuery;
      }
      if (filters.status) {
        params.status = filters.status;
      }
      if (filters.category) {
        params.category = filters.category;
      }
      if (filters.dateRange) {
        params.dateRange = filters.dateRange;
      }

      const response = await getUserArticles(params);

      // Convert dates from ISO strings to Date objects for compatibility
      const articlesWithDates = response.items.map(article => ({
        ...article,
        createdAt: article.createdAt ? new Date(article.createdAt) : null,
        updatedAt: article.updatedAt ? new Date(article.updatedAt) : null,
        publishedAt: article.publishedAt ? new Date(article.publishedAt) : null
      }));

      setArticles(articlesWithDates);
      setTotalArticles(response.total);
      setTotalPages(response.pages);
    } catch (err) {
      console.error('Error fetching articles:', err);
      setError(err.message || 'Erro ao carregar matérias');
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, filters]);

  // Fetch articles when page or filters change
  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  // Reset to page 1 when filters change
  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
    setCurrentPage(1);
  }, []);

  // Navigation handlers
  const handleCreateNew = useCallback(() => {
    navigate('/criar');
  }, [navigate]);

  const handleView = useCallback((articleId) => {
    const article = articles.find(a => a.id === articleId);
    if (article) {
      setViewModal({
        open: true,
        article
      });
    }
  }, [articles]);

  const handleViewClose = useCallback(() => {
    setViewModal({ open: false, article: null });
  }, []);

  const handleEdit = useCallback((articleId) => {
    console.log('Editing article:', articleId);
    navigate(`/editar/${articleId}`);
  }, [navigate]);

  const handleMetrics = useCallback((articleId) => {
    console.log('Viewing metrics for article:', articleId);
    // TODO: Implement metrics modal
  }, []);

  const handleDeleteClick = useCallback((articleId) => {
    const article = articles.find(a => a.id === articleId);
    if (article) {
      setDeleteDialog({
        open: true,
        articleId,
        articleTitle: article.title
      });
    }
  }, [articles]);

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteDialog.articleId) return;

    setIsDeleting(true);
    try {
      await deleteUserArticle(deleteDialog.articleId);

      // Refetch articles to update the list
      await fetchArticles();

      // Reset dialog state
      setDeleteDialog({ open: false, articleId: null, articleTitle: '' });
    } catch (err) {
      console.error('Error deleting article:', err);
      setError(err.message || 'Erro ao excluir matéria');
    } finally {
      setIsDeleting(false);
    }
  }, [deleteDialog.articleId, fetchArticles]);

  const handleDeleteCancel = useCallback(() => {
    setDeleteDialog({ open: false, articleId: null, articleTitle: '' });
  }, []);

  const handleClearFilters = useCallback(() => {
    setFilters({
      searchQuery: '',
      status: null,
      category: null,
      dateRange: null,
      author: null
    });
    setCurrentPage(1);
  }, []);

  const hasActiveFilters = Object.values(filters).some(v => v !== null && v !== '');
  const hasNoArticles = totalArticles === 0 && !hasActiveFilters && !isLoading;
  const hasNoResults = articles.length === 0 && !hasNoArticles && !isLoading;

  return (
    <div className="min-h-screen pt-16 bg-off-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Page Header */}
        <div className="bg-white rounded-xl border border-light-gray p-6 sm:p-8 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-dark-gray mb-2">
                Minhas Matérias
              </h1>
              <p className="text-sm text-medium-gray">
                {isLoading ? (
                  'Carregando...'
                ) : (
                  `${totalArticles} ${totalArticles === 1 ? 'matéria encontrada' : 'matérias encontradas'}`
                )}
              </p>
            </div>
            <button
              onClick={handleCreateNew}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-tmc-orange text-white rounded-lg font-semibold hover:bg-tmc-orange/90 transition-colors focus:outline-none focus:ring-2 focus:ring-tmc-orange focus:ring-offset-2"
              aria-label="Criar nova matéria"
            >
              <PenLine style={{ width: '18px', height: '18px' }} aria-hidden="true" />
              <span>Nova Matéria</span>
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        {!hasNoArticles && (
          <MyArticleFilterBar
            onFilterChange={handleFilterChange}
            resultsCount={totalArticles}
          />
        )}

        {/* Content Area */}
        <main>
          {/* Loading State */}
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Loader2 className="w-10 h-10 text-tmc-orange animate-spin mb-4" />
              <p className="text-medium-gray">Carregando matérias...</p>
            </div>
          ) : error ? (
            /* Error State */
            <div className="flex flex-col items-center justify-center py-16 bg-white rounded-xl border border-light-gray">
              <AlertCircle className="w-12 h-12 text-error mb-4" />
              <h3 className="text-lg font-semibold text-dark-gray mb-2">
                Erro ao carregar matérias
              </h3>
              <p className="text-medium-gray text-center mb-6 max-w-md">
                {error}
              </p>
              <button
                onClick={fetchArticles}
                className="flex items-center gap-2 px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors"
              >
                <RefreshCw size={18} />
                <span>Tentar novamente</span>
              </button>
            </div>
          ) : hasNoArticles ? (
            /* Empty States */
            <EmptyStatePresets.NoArticles onCreateArticle={handleCreateNew} />
          ) : hasNoResults ? (
            hasActiveFilters ? (
              <EmptyStatePresets.FilteredEmpty
                onClearFilters={handleClearFilters}
                onCreateArticle={handleCreateNew}
              />
            ) : (
              <EmptyStatePresets.NoResults onClearFilters={handleClearFilters} />
            )
          ) : (
            <>
              {/* Articles Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {articles.map((article) => (
                  <MyArticleCard
                    key={article.id}
                    article={article}
                    onView={handleView}
                    onEdit={handleEdit}
                    onDelete={handleDeleteClick}
                    onMetrics={handleMetrics}
                    showAuthor={false}
                  />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  totalItems={totalArticles}
                  itemsPerPage={ITEMS_PER_PAGE}
                  onPageChange={setCurrentPage}
                  showInfo={true}
                />
              )}
            </>
          )}
        </main>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={deleteDialog.open}
        title="Excluir Matéria?"
        message={`Tem certeza que deseja excluir "${deleteDialog.articleTitle}"? Esta ação não pode ser desfeita.`}
        confirmText={isDeleting ? "Excluindo..." : "Excluir"}
        cancelText="Cancelar"
        variant="danger"
        onConfirm={handleDeleteConfirm}
        onClose={handleDeleteCancel}
        isLoading={isDeleting}
      />

      {/* Article View Modal */}
      <ArticleViewModal
        article={viewModal.article}
        isOpen={viewModal.open}
        onClose={handleViewClose}
        onEdit={handleEdit}
      />
    </div>
  );
};

export default MinhasMaterias;
