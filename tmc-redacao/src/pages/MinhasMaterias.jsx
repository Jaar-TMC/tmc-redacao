import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PenLine } from 'lucide-react';
import MyArticleFilterBar from '../components/ui/MyArticleFilterBar';
import MyArticleCard from '../components/cards/MyArticleCard';
import Pagination from '../components/ui/Pagination';
import EmptyState, { EmptyStatePresets } from '../components/ui/EmptyState';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import { myArticles } from '../data/mockData';

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

  // Filter articles based on active filters
  const filteredArticles = useMemo(() => {
    let results = [...myArticles];

    // Search query filter
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      results = results.filter(article =>
        article.title.toLowerCase().includes(query) ||
        article.preview.toLowerCase().includes(query) ||
        article.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Status filter
    if (filters.status) {
      results = results.filter(article => article.status === filters.status);
    }

    // Category filter
    if (filters.category) {
      results = results.filter(article => article.category === filters.category);
    }

    // Date range filter
    if (filters.dateRange) {
      const now = new Date();
      results = results.filter(article => {
        const articleDate = article.createdAt;
        const diffInMs = now - articleDate;
        const diffInHours = diffInMs / (1000 * 60 * 60);
        const diffInDays = diffInHours / 24;

        switch (filters.dateRange) {
          case '24h':
            return diffInHours <= 24;
          case '7d':
            return diffInDays <= 7;
          case '30d':
            return diffInDays <= 30;
          case '3m':
            return diffInDays <= 90;
          case 'year':
            return articleDate.getFullYear() === now.getFullYear();
          default:
            return true;
        }
      });
    }

    return results;
  }, [filters]);

  // Pagination
  const totalPages = Math.ceil(filteredArticles.length / ITEMS_PER_PAGE);
  const paginatedArticles = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredArticles.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredArticles, currentPage]);

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
    console.log('Viewing article:', articleId);
    // TODO: Implement view functionality
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
    const article = myArticles.find(a => a.id === articleId);
    if (article) {
      setDeleteDialog({
        open: true,
        articleId,
        articleTitle: article.title
      });
    }
  }, []);

  const handleDeleteConfirm = useCallback(() => {
    // TODO: Actually delete the article
    console.log('Deleting article:', deleteDialog.articleId);

    // Reset dialog state (will be closed by ConfirmDialog)
    setDeleteDialog({ open: false, articleId: null, articleTitle: '' });

    // Show success toast
    // TODO: Implement toast notification
  }, [deleteDialog.articleId]);

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
  const hasNoArticles = myArticles.length === 0;
  const hasNoResults = filteredArticles.length === 0 && !hasNoArticles;

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
                {filteredArticles.length} {filteredArticles.length === 1 ? 'matéria encontrada' : 'matérias encontradas'}
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
            resultsCount={filteredArticles.length}
          />
        )}

        {/* Content Area */}
        <main>
          {/* Empty States */}
          {hasNoArticles ? (
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
                {paginatedArticles.map((article) => (
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
                  totalItems={filteredArticles.length}
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
        confirmText="Excluir"
        cancelText="Cancelar"
        variant="danger"
        onConfirm={handleDeleteConfirm}
        onClose={handleDeleteCancel}
      />
    </div>
  );
};

export default MinhasMaterias;
