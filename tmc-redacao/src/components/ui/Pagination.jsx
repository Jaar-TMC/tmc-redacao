import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useMemo } from 'react';
import PropTypes from 'prop-types';

/**
 * Pagination Component
 *
 * Componente de paginação para navegação entre páginas
 * Segue especificações do documento de planejamento UI/UX
 *
 * WCAG 2.1 Compliance:
 * - Proper ARIA labels for navigation
 * - Keyboard accessible
 * - Clear visual indication of current page
 * - Disabled state properly communicated
 */
const Pagination = ({
  currentPage,
  totalPages,
  totalItems,
  itemsPerPage,
  onPageChange,
  showInfo = true
}) => {
  const visiblePages = useMemo(() => {
    const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
    const maxVisible = isMobile ? 3 : 7;
    const pages = [];

    if (totalPages <= maxVisible) {
      // Show all pages if total is less than max
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always include first page
      pages.push(1);

      // Calculate range around current page
      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);

      // Add ellipsis if there's a gap after first page
      if (start > 2) {
        pages.push('...');
      }

      // Add pages around current page
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      // Add ellipsis if there's a gap before last page
      if (end < totalPages - 1) {
        pages.push('...');
      }

      // Always include last page
      if (totalPages > 1) {
        pages.push(totalPages);
      }
    }

    return pages;
  }, [currentPage, totalPages]);

  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  const handlePrevious = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const handlePageClick = (page) => {
    if (typeof page === 'number' && page !== currentPage) {
      onPageChange(page);
    }
  };

  if (totalPages <= 1) {
    return null;
  }

  return (
    <nav
      className="flex flex-col items-center gap-4 py-8"
      role="navigation"
      aria-label="Paginação de matérias"
    >
      {/* Page Numbers */}
      <div className="flex items-center gap-2">
        {/* Previous Button */}
        <button
          onClick={handlePrevious}
          disabled={currentPage === 1}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-light-gray bg-white text-medium-gray hover:bg-off-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Página anterior"
        >
          <ChevronLeft style={{ width: '16px', height: '16px' }} aria-hidden="true" />
          <span className="hidden sm:inline">Anterior</span>
        </button>

        {/* Page Number Buttons */}
        {visiblePages.map((page, index) => {
          if (page === '...') {
            return (
              <span
                key={`ellipsis-${index}`}
                className="w-10 h-10 flex items-center justify-center text-medium-gray"
                aria-hidden="true"
              >
                ...
              </span>
            );
          }

          const isActive = page === currentPage;

          return (
            <button
              key={page}
              onClick={() => handlePageClick(page)}
              className={`w-10 h-10 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-tmc-orange text-white border border-tmc-orange'
                  : 'bg-white text-medium-gray border border-light-gray hover:bg-off-white hover:border-tmc-orange'
              }`}
              aria-label={`${isActive ? 'Página atual, ' : ''}Página ${page}`}
              aria-current={isActive ? 'page' : undefined}
            >
              {page}
            </button>
          );
        })}

        {/* Next Button */}
        <button
          onClick={handleNext}
          disabled={currentPage === totalPages}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-light-gray bg-white text-medium-gray hover:bg-off-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Próxima página"
        >
          <span className="hidden sm:inline">Próximo</span>
          <ChevronRight style={{ width: '16px', height: '16px' }} aria-hidden="true" />
        </button>
      </div>

      {/* Info Text */}
      {showInfo && (
        <p className="text-sm text-medium-gray">
          Mostrando {startItem}-{endItem} de {totalItems} matérias
        </p>
      )}
    </nav>
  );
};

Pagination.propTypes = {
  currentPage: PropTypes.number.isRequired,
  totalPages: PropTypes.number.isRequired,
  totalItems: PropTypes.number.isRequired,
  itemsPerPage: PropTypes.number.isRequired,
  onPageChange: PropTypes.func.isRequired,
  showInfo: PropTypes.bool
};

export default Pagination;
