import { Search, ChevronDown, Calendar, Building2, Tag } from 'lucide-react';
import { useState, useCallback, useEffect, useMemo } from 'react';
import { mockCategories, mockSources } from '../../data/mockData';
import { useFilters } from '../../context';

/**
 * FilterBar Component
 *
 * WCAG 2.1 Compliance:
 * - No Keyboard Trap (2.1.2): All dropdowns can be closed with Escape key
 * - Focus Order (2.4.3): Tab order follows visual order
 * - Link Purpose in Context (2.4.4): All filters have clear labels and context
 * - Headings and Labels (2.4.6): All form controls have descriptive labels
 */
const FilterBar = () => {
  const { filters, updateFilter } = useFilters();
  const [searchTerm, setSearchTerm] = useState(filters.searchQuery || '');
  const [openDropdown, setOpenDropdown] = useState(null);

  const periods = useMemo(() => [
    { id: 'today', label: 'Hoje' },
    { id: 'week', label: 'Esta semana' },
    { id: 'month', label: 'Este mês' }
  ], []);

  // Debounce search term updates
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchTerm !== filters.searchQuery) {
        updateFilter('searchQuery', searchTerm);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm, filters.searchQuery, updateFilter]);

  const handleFilterClick = useCallback((type) => {
    setOpenDropdown(prev => prev === type ? null : type);
  }, []);

  const handleSelectFilter = useCallback((type, value) => {
    updateFilter(type, value);
    setOpenDropdown(null);
  }, [updateFilter]);

  const handleCloseDropdown = useCallback(() => {
    setOpenDropdown(null);
  }, []);

  // Handle Escape key to close dropdowns (WCAG 2.1.2 - No Keyboard Trap)
  useEffect(() => {
    const handleEscapeKey = (e) => {
      if (e.key === 'Escape' && openDropdown) {
        handleCloseDropdown();
      }
    };

    document.addEventListener('keydown', handleEscapeKey);
    return () => document.removeEventListener('keydown', handleEscapeKey);
  }, [openDropdown, handleCloseDropdown]);

  return (
    <div className={`bg-white rounded-xl border border-light-gray p-4 mb-6 ${!searchTerm ? 'lg:pb-8' : ''}`} role="search" aria-label="Filtros de matérias">
      <div className="flex items-center gap-4">
        {/* Search Input */}
        <div className="flex-1 relative">
          <label htmlFor="search-articles" className="sr-only">Buscar matérias</label>
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray" style={{ width: '20px', height: '20px' }} aria-hidden="true" />
          <input
            id="search-articles"
            type="search"
            placeholder="Ex: inteligência artificial, eleições, mercado financeiro..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
            aria-label="Buscar matérias por título ou conteúdo"
          />
          {!searchTerm && (
            <p className="hidden lg:block absolute top-full mt-1 left-0 text-xs text-medium-gray">
              Busque por palavras-chave, temas ou tags para filtrar em tempo real
            </p>
          )}
        </div>

        {/* Filter Buttons */}
        <div className="flex items-center gap-4" role="group" aria-label="Filtros de categoria, origem e período">
          {/* Category Filter */}
          <div className="relative">
            <button
              type="button"
              onClick={() => handleFilterClick('category')}
              aria-expanded={openDropdown === 'category'}
              aria-haspopup="listbox"
              aria-label={`Filtrar por tema: ${filters.category || 'Todos os temas'}`}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
                filters.category
                  ? 'bg-tmc-orange text-white'
                  : 'text-dark-gray border border-light-gray hover:bg-light-gray'
              }`}
            >
              <Tag style={{ width: '18px', height: '18px' }} aria-hidden="true" />
              <span>{filters.category || 'Tema'}</span>
              <ChevronDown style={{ width: '14px', height: '14px' }} aria-hidden="true" />
            </button>

            {openDropdown === 'category' && (
              <div className="absolute top-full left-0 mt-2 w-56 bg-white rounded-lg border border-light-gray py-2 z-20" role="listbox" aria-label="Temas disponíveis">
                <button
                  type="button"
                  onClick={() => handleSelectFilter('category', null)}
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
                    className="w-full px-4 py-2 text-left text-sm hover:bg-off-white flex items-center justify-between"
                    role="option"
                    aria-selected={filters.category === cat.name}
                  >
                    <span>{cat.name}</span>
                    <span className="text-xs text-medium-gray bg-off-white px-2 py-0.5 rounded" aria-label={`${cat.count} matérias`}>
                      {cat.count}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Source Filter */}
          <div className="relative">
            <button
              type="button"
              onClick={() => handleFilterClick('source')}
              aria-expanded={openDropdown === 'source'}
              aria-haspopup="listbox"
              aria-label={`Filtrar por origem: ${filters.source || 'Todas as origens'}`}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
                filters.source
                  ? 'bg-tmc-orange text-white'
                  : 'text-dark-gray border border-light-gray hover:bg-light-gray'
              }`}
            >
              <Building2 style={{ width: '18px', height: '18px' }} aria-hidden="true" />
              <span>{filters.source || 'Origem'}</span>
              <ChevronDown style={{ width: '14px', height: '14px' }} aria-hidden="true" />
            </button>

            {openDropdown === 'source' && (
              <div className="absolute top-full left-0 mt-2 w-56 bg-white rounded-lg border border-light-gray py-2 z-20" role="listbox" aria-label="Origens disponíveis">
                <button
                  type="button"
                  onClick={() => handleSelectFilter('source', null)}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-off-white text-medium-gray"
                  role="option"
                  aria-selected={!filters.source}
                >
                  Todas as origens
                </button>
                {mockSources.filter(s => s.active).map((source) => (
                  <button
                    type="button"
                    key={source.id}
                    onClick={() => handleSelectFilter('source', source.name)}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-off-white flex items-center gap-2"
                    role="option"
                    aria-selected={filters.source === source.name}
                  >
                    <img src={source.favicon} alt="" className="w-4 h-4 rounded" aria-hidden="true" />
                    <span>{source.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Period Filter */}
          <div className="relative">
            <button
              type="button"
              onClick={() => handleFilterClick('period')}
              aria-expanded={openDropdown === 'period'}
              aria-haspopup="listbox"
              aria-label={`Filtrar por período: ${periods.find(p => p.id === filters.period)?.label}`}
              className="flex items-center gap-2 px-4 py-2.5 text-dark-gray rounded-lg font-medium border border-light-gray hover:bg-light-gray transition-colors"
            >
              <Calendar style={{ width: '18px', height: '18px' }} aria-hidden="true" />
              <span>{periods.find(p => p.id === filters.period)?.label}</span>
              <ChevronDown style={{ width: '14px', height: '14px' }} aria-hidden="true" />
            </button>

            {openDropdown === 'period' && (
              <div className="absolute top-full right-0 mt-2 w-40 bg-white rounded-lg border border-light-gray py-2 z-20" role="listbox" aria-label="Períodos disponíveis">
                {periods.map((period) => (
                  <button
                    type="button"
                    key={period.id}
                    onClick={() => handleSelectFilter('period', period.id)}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-off-white ${
                      filters.period === period.id ? 'text-tmc-orange font-medium' : ''
                    }`}
                    role="option"
                    aria-selected={filters.period === period.id}
                  >
                    {period.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Top 10 Toggle */}
        <div className="flex items-center bg-off-white rounded-lg p-1" role="group" aria-label="Top 10 matérias">
          <button
            type="button"
            onClick={() => handleSelectFilter('period', 'today')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              filters.period === 'today'
                ? 'bg-tmc-orange text-white'
                : 'text-medium-gray hover:text-dark-gray'
            }`}
            aria-pressed={filters.period === 'today'}
          >
            Top 10 do dia
          </button>
          <button
            type="button"
            onClick={() => handleSelectFilter('period', 'week')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              filters.period === 'week'
                ? 'bg-tmc-orange text-white'
                : 'text-medium-gray hover:text-dark-gray'
            }`}
            aria-pressed={filters.period === 'week'}
          >
            Top 10 da semana
          </button>
        </div>
      </div>

      {/* Close dropdown when clicking outside */}
      {openDropdown && (
        <div
          className="fixed inset-0 z-10"
          onClick={handleCloseDropdown}
        />
      )}
    </div>
  );
};

export default FilterBar;
