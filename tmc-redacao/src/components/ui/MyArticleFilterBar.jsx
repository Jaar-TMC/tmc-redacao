import { Search, ChevronDown, X, Tag, Calendar, User } from 'lucide-react';
import { useState, useCallback, useEffect, useMemo } from 'react';
import { mockCategories } from '../../data/mockData';
import PropTypes from 'prop-types';

/**
 * MyArticleFilterBar Component
 *
 * Barra de filtros para a página "Minhas Matérias"
 * Segue especificações do documento de planejamento UI/UX
 *
 * WCAG 2.1 Compliance:
 * - No Keyboard Trap: All dropdowns can be closed with Escape
 * - Proper ARIA labels and roles for all interactive elements
 * - Keyboard navigation support
 * - Focus management
 */
const MyArticleFilterBar = ({ onFilterChange, resultsCount = 0 }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [openDropdown, setOpenDropdown] = useState(null);
  const [filters, setFilters] = useState({
    status: null,
    category: null,
    dateRange: null,
    author: null
  });

  const statusOptions = useMemo(() => [
    { id: 'all', label: 'Todos' },
    { id: 'draft', label: 'Rascunho' },
    { id: 'published', label: 'Publicada' }
  ], []);

  const dateRangeOptions = useMemo(() => [
    { id: 'all', label: 'Qualquer data' },
    { id: '24h', label: 'Últimas 24 horas' },
    { id: '7d', label: 'Últimos 7 dias' },
    { id: '30d', label: 'Últimos 30 dias' },
    { id: '3m', label: 'Últimos 3 meses' },
    { id: 'year', label: 'Este ano' }
  ], []);

  // Debounce search term updates
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      onFilterChange({ ...filters, searchQuery: searchTerm });
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm, filters, onFilterChange]);

  const handleFilterClick = useCallback((type) => {
    setOpenDropdown(prev => prev === type ? null : type);
  }, []);

  const handleSelectFilter = useCallback((type, value) => {
    const newFilters = { ...filters, [type]: value === 'all' ? null : value };
    setFilters(newFilters);
    onFilterChange({ ...newFilters, searchQuery: searchTerm });
    setOpenDropdown(null);
  }, [filters, searchTerm, onFilterChange]);

  const handleClearFilters = useCallback(() => {
    setSearchTerm('');
    setFilters({
      status: null,
      category: null,
      dateRange: null,
      author: null
    });
    onFilterChange({ searchQuery: '', status: null, category: null, dateRange: null, author: null });
  }, [onFilterChange]);

  const handleRemoveFilter = useCallback((type) => {
    const newFilters = { ...filters, [type]: null };
    setFilters(newFilters);
    onFilterChange({ ...newFilters, searchQuery: searchTerm });
  }, [filters, searchTerm, onFilterChange]);

  const handleCloseDropdown = useCallback(() => {
    setOpenDropdown(null);
  }, []);

  // Handle Escape key to close dropdowns
  useEffect(() => {
    const handleEscapeKey = (e) => {
      if (e.key === 'Escape' && openDropdown) {
        handleCloseDropdown();
      }
    };

    document.addEventListener('keydown', handleEscapeKey);
    return () => document.removeEventListener('keydown', handleEscapeKey);
  }, [openDropdown, handleCloseDropdown]);

  const activeFiltersCount = Object.values(filters).filter(v => v !== null).length;
  const hasActiveFilters = activeFiltersCount > 0 || searchTerm.length > 0;

  return (
    <div className="bg-white rounded-xl border border-light-gray p-6 mb-6 shadow-sm" role="search" aria-label="Filtros de matérias">
      {/* Search Input */}
      <div className="mb-4">
        <label htmlFor="search-my-articles" className="sr-only">Buscar minhas matérias</label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray" style={{ width: '20px', height: '20px' }} aria-hidden="true" />
          <input
            id="search-my-articles"
            type="search"
            placeholder="Buscar por título, conteúdo ou tags..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-11 pr-4 py-3 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange transition-all"
            aria-label="Buscar matérias por título, conteúdo ou tags"
          />
        </div>
      </div>

      {/* Filter Buttons */}
      <div className="flex items-center gap-3 mb-4" role="group" aria-label="Filtros disponíveis">
        {/* Status Filter */}
        <div className="relative">
          <button
            type="button"
            onClick={() => handleFilterClick('status')}
            aria-expanded={openDropdown === 'status'}
            aria-haspopup="listbox"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filters.status
                ? 'bg-tmc-orange text-white'
                : 'text-dark-gray border border-light-gray hover:bg-off-white'
            }`}
          >
            <span>Status</span>
            <ChevronDown style={{ width: '14px', height: '14px' }} aria-hidden="true" />
          </button>

          {openDropdown === 'status' && (
            <div className="absolute top-full left-0 mt-2 w-48 bg-white rounded-lg border border-light-gray shadow-lg py-2 z-20" role="listbox" aria-label="Opções de status">
              {statusOptions.map((option) => (
                <button
                  type="button"
                  key={option.id}
                  onClick={() => handleSelectFilter('status', option.id)}
                  className={`w-full px-4 py-2 text-left text-sm hover:bg-off-white transition-colors ${
                    (filters.status === option.id) || (!filters.status && option.id === 'all') ? 'text-tmc-orange font-semibold' : 'text-dark-gray'
                  }`}
                  role="option"
                  aria-selected={(filters.status === option.id) || (!filters.status && option.id === 'all')}
                >
                  {option.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Category Filter */}
        <div className="relative">
          <button
            type="button"
            onClick={() => handleFilterClick('category')}
            aria-expanded={openDropdown === 'category'}
            aria-haspopup="listbox"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filters.category
                ? 'bg-tmc-orange text-white'
                : 'text-dark-gray border border-light-gray hover:bg-off-white'
            }`}
          >
            <Tag style={{ width: '16px', height: '16px' }} aria-hidden="true" />
            <span>{filters.category || 'Tema'}</span>
            <ChevronDown style={{ width: '14px', height: '14px' }} aria-hidden="true" />
          </button>

          {openDropdown === 'category' && (
            <div className="absolute top-full left-0 mt-2 w-56 bg-white rounded-lg border border-light-gray shadow-lg py-2 z-20 max-h-80 overflow-y-auto" role="listbox" aria-label="Temas disponíveis">
              <button
                type="button"
                onClick={() => handleSelectFilter('category', 'all')}
                className="w-full px-4 py-2 text-left text-sm hover:bg-off-white text-medium-gray"
                role="option"
                aria-selected={!filters.category}
              >
                Todos os temas
              </button>
              {mockCategories.map((cat) => (
                <button
                  type="button"
                  key={cat.id}
                  onClick={() => handleSelectFilter('category', cat.name)}
                  className={`w-full px-4 py-2 text-left text-sm hover:bg-off-white transition-colors ${
                    filters.category === cat.name ? 'text-tmc-orange font-semibold' : 'text-dark-gray'
                  }`}
                  role="option"
                  aria-selected={filters.category === cat.name}
                >
                  {cat.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Date Range Filter */}
        <div className="relative">
          <button
            type="button"
            onClick={() => handleFilterClick('dateRange')}
            aria-expanded={openDropdown === 'dateRange'}
            aria-haspopup="listbox"
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filters.dateRange
                ? 'bg-tmc-orange text-white'
                : 'text-dark-gray border border-light-gray hover:bg-off-white'
            }`}
          >
            <Calendar style={{ width: '16px', height: '16px' }} aria-hidden="true" />
            <span>Data</span>
            <ChevronDown style={{ width: '14px', height: '14px' }} aria-hidden="true" />
          </button>

          {openDropdown === 'dateRange' && (
            <div className="absolute top-full left-0 mt-2 w-56 bg-white rounded-lg border border-light-gray shadow-lg py-2 z-20" role="listbox" aria-label="Períodos disponíveis">
              {dateRangeOptions.map((option) => (
                <button
                  type="button"
                  key={option.id}
                  onClick={() => handleSelectFilter('dateRange', option.id)}
                  className={`w-full px-4 py-2 text-left text-sm hover:bg-off-white transition-colors ${
                    (filters.dateRange === option.id) || (!filters.dateRange && option.id === 'all') ? 'text-tmc-orange font-semibold' : 'text-dark-gray'
                  }`}
                  role="option"
                  aria-selected={(filters.dateRange === option.id) || (!filters.dateRange && option.id === 'all')}
                >
                  {option.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Clear Filters Button */}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={handleClearFilters}
            className="ml-auto text-sm text-medium-gray hover:text-tmc-orange font-medium transition-colors"
            aria-label="Limpar todos os filtros"
          >
            Limpar Filtros
          </button>
        )}
      </div>

      {/* Active Filters Pills */}
      {hasActiveFilters && (
        <div className="pt-4 border-t border-light-gray">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-xs text-medium-gray font-medium">Filtros ativos:</span>

            {filters.status && (
              <div className="inline-flex items-center gap-2 bg-orange-50 border border-tmc-orange rounded-full px-3 py-1 text-xs font-medium text-tmc-orange">
                <span>{statusOptions.find(s => s.id === filters.status)?.label}</span>
                <button
                  onClick={() => handleRemoveFilter('status')}
                  className="hover:bg-tmc-orange/10 rounded-full p-0.5 transition-colors"
                  aria-label="Remover filtro de status"
                >
                  <X style={{ width: '12px', height: '12px' }} aria-hidden="true" />
                </button>
              </div>
            )}

            {filters.category && (
              <div className="inline-flex items-center gap-2 bg-orange-50 border border-tmc-orange rounded-full px-3 py-1 text-xs font-medium text-tmc-orange">
                <span>{filters.category}</span>
                <button
                  onClick={() => handleRemoveFilter('category')}
                  className="hover:bg-tmc-orange/10 rounded-full p-0.5 transition-colors"
                  aria-label="Remover filtro de categoria"
                >
                  <X style={{ width: '12px', height: '12px' }} aria-hidden="true" />
                </button>
              </div>
            )}

            {filters.dateRange && (
              <div className="inline-flex items-center gap-2 bg-orange-50 border border-tmc-orange rounded-full px-3 py-1 text-xs font-medium text-tmc-orange">
                <span>{dateRangeOptions.find(d => d.id === filters.dateRange)?.label}</span>
                <button
                  onClick={() => handleRemoveFilter('dateRange')}
                  className="hover:bg-tmc-orange/10 rounded-full p-0.5 transition-colors"
                  aria-label="Remover filtro de data"
                >
                  <X style={{ width: '12px', height: '12px' }} aria-hidden="true" />
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Close dropdown overlay */}
      {openDropdown && (
        <div
          className="fixed inset-0 z-10"
          onClick={handleCloseDropdown}
          aria-hidden="true"
        />
      )}
    </div>
  );
};

MyArticleFilterBar.propTypes = {
  onFilterChange: PropTypes.func.isRequired,
  resultsCount: PropTypes.number
};

export default MyArticleFilterBar;
