import { Search, ChevronDown, Building2, Tag, Hash } from 'lucide-react';
import { useState, useCallback, useEffect, useRef } from 'react';
import { getSources, getCategories, getAllTags } from '../../services/api';
import { transformSources, transformCategories } from '../../utils/transformers';
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

  // Search terms for dropdowns
  const [categorySearch, setCategorySearch] = useState('');
  const [sourceSearch, setSourceSearch] = useState('');
  const [tagSearch, setTagSearch] = useState('');

  // Refs to prevent race conditions between user typing and external updates
  const isUserTypingRef = useRef(false);
  const debounceTimerRef = useRef(null);
  const categorySearchRef = useRef(null);
  const sourceSearchRef = useRef(null);
  const tagSearchRef = useRef(null);

  // API State for filters
  const [categories, setCategories] = useState([]);
  const [sources, setSources] = useState([]);
  const [tags, setTags] = useState([]);

  // Fetch filter data from API on mount
  useEffect(() => {
    const fetchFilters = async () => {
      // Fetch each filter independently to avoid one failure breaking all
      try {
        const catRes = await getCategories();
        setCategories(transformCategories(catRes?.categories));
      } catch (err) {
        console.error('Error fetching categories:', err);
      }

      try {
        const srcRes = await getSources();
        setSources(transformSources(srcRes?.items || srcRes?.sources));
      } catch (err) {
        console.error('Error fetching sources:', err);
      }

      try {
        const tagsRes = await getAllTags();
        setTags(tagsRes?.items || []);
      } catch (err) {
        console.error('Error fetching tags:', err);
      }
    };
    fetchFilters();
  }, []);

  // Sync local state when filters.searchQuery changes externally (e.g., from TrendsSidebar)
  // Only update if user is not currently typing to prevent race conditions
  useEffect(() => {
    if (!isUserTypingRef.current && filters.searchQuery !== searchTerm) {
      setSearchTerm(filters.searchQuery || '');
    }
  }, [filters.searchQuery]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Handle search input change with debounce
  const handleSearchChange = useCallback((e) => {
    const value = e.target.value;
    isUserTypingRef.current = true;
    setSearchTerm(value);

    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new debounce timer
    debounceTimerRef.current = setTimeout(() => {
      updateFilter('searchQuery', value);
      isUserTypingRef.current = false;
    }, 300);
  }, [updateFilter]);

  const handleFilterClick = useCallback((type) => {
    setOpenDropdown(prev => {
      if (prev === type) {
        // Closing dropdown - clear search
        if (type === 'category') setCategorySearch('');
        if (type === 'source') setSourceSearch('');
        if (type === 'tag') setTagSearch('');
        return null;
      }
      // Opening dropdown - focus search after render
      setTimeout(() => {
        if (type === 'category' && categorySearchRef.current) {
          categorySearchRef.current.focus();
        }
        if (type === 'source' && sourceSearchRef.current) {
          sourceSearchRef.current.focus();
        }
        if (type === 'tag' && tagSearchRef.current) {
          tagSearchRef.current.focus();
        }
      }, 0);
      return type;
    });
  }, []);

  const handleSelectFilter = useCallback((type, value) => {
    updateFilter(type, value);
    setOpenDropdown(null);
  }, [updateFilter]);

  const handleCloseDropdown = useCallback(() => {
    setOpenDropdown(null);
    setCategorySearch('');
    setSourceSearch('');
    setTagSearch('');
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

  // Filtered categories based on search term
  const filteredCategories = categories.filter(cat =>
    cat.name.toLowerCase().includes(categorySearch.toLowerCase())
  );

  // Filtered sources based on search term
  const filteredSources = sources.filter(s =>
    s.active && s.name.toLowerCase().includes(sourceSearch.toLowerCase())
  );

  // Filtered tags based on search term
  const filteredTags = tags.filter(t =>
    t.theme.toLowerCase().includes(tagSearch.toLowerCase()) ||
    t.tag.toLowerCase().includes(tagSearch.toLowerCase())
  );

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
            onChange={handleSearchChange}
            className="w-full pl-10 pr-4 py-2.5 border border-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
            aria-label="Buscar matérias por título ou conteúdo"
          />
          {!searchTerm && (
            <p className="hidden xl:block absolute top-full mt-1 left-0 text-xs text-medium-gray whitespace-nowrap">
              Busque por palavras-chave, temas ou tags para filtrar em tempo real
            </p>
          )}
        </div>

        {/* Filter Buttons */}
        <div className="flex items-center gap-2 md:gap-4" role="group" aria-label="Filtros de categoria, tag e origem">
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
                {/* Search input */}
                <div className="px-2 pb-2 border-b border-light-gray mb-2">
                  <input
                    ref={categorySearchRef}
                    type="text"
                    placeholder="Pesquisar tema..."
                    value={categorySearch}
                    onChange={(e) => setCategorySearch(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full px-3 py-2 text-sm border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    aria-label="Pesquisar temas"
                  />
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {!categorySearch && (
                    <button
                      type="button"
                      onClick={() => handleSelectFilter('category', null)}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-off-white text-medium-gray"
                      role="option"
                      aria-selected={!filters.category}
                    >
                      Todos os temas
                    </button>
                  )}
                  {filteredCategories.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-medium-gray text-center">
                      Nenhum tema encontrado
                    </div>
                  ) : (
                    filteredCategories.map((cat) => (
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
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Tag Filter */}
          <div className="relative">
            <button
              type="button"
              onClick={() => handleFilterClick('tag')}
              aria-expanded={openDropdown === 'tag'}
              aria-haspopup="listbox"
              aria-label={`Filtrar por tag: ${filters.tag || 'Todas as tags'}`}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
                filters.tag
                  ? 'bg-tmc-orange text-white'
                  : 'text-dark-gray border border-light-gray hover:bg-light-gray'
              }`}
            >
              <Hash style={{ width: '18px', height: '18px' }} aria-hidden="true" />
              <span className="hidden sm:inline">{filters.tag || 'Tag'}</span>
              <ChevronDown style={{ width: '14px', height: '14px' }} aria-hidden="true" />
            </button>

            {openDropdown === 'tag' && (
              <div className="absolute top-full right-0 sm:left-0 sm:right-auto mt-2 w-64 bg-white rounded-lg border border-light-gray py-2 z-20" role="listbox" aria-label="Tags disponíveis">
                {/* Search input */}
                <div className="px-2 pb-2 border-b border-light-gray mb-2">
                  <input
                    ref={tagSearchRef}
                    type="text"
                    placeholder="Pesquisar tag..."
                    value={tagSearch}
                    onChange={(e) => setTagSearch(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full px-3 py-2 text-sm border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    aria-label="Pesquisar tags"
                  />
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {!tagSearch && (
                    <button
                      type="button"
                      onClick={() => handleSelectFilter('tag', null)}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-off-white text-medium-gray"
                      role="option"
                      aria-selected={!filters.tag}
                    >
                      Todas as tags
                    </button>
                  )}
                  {filteredTags.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-medium-gray text-center">
                      Nenhuma tag encontrada
                    </div>
                  ) : (
                    filteredTags.map((tagItem) => (
                      <button
                        type="button"
                        key={tagItem.id}
                        onClick={() => handleSelectFilter('tag', tagItem.tag)}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-off-white flex items-center justify-between"
                        role="option"
                        aria-selected={filters.tag === tagItem.tag}
                      >
                        <span className="flex items-center gap-2">
                          <Hash style={{ width: '14px', height: '14px' }} className="text-medium-gray" />
                          {tagItem.theme}
                        </span>
                        <span className="text-xs text-medium-gray bg-off-white px-2 py-0.5 rounded" aria-label={`${tagItem.count} matérias`}>
                          {tagItem.count}
                        </span>
                      </button>
                    ))
                  )}
                </div>
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
                {/* Search input */}
                <div className="px-2 pb-2 border-b border-light-gray mb-2">
                  <input
                    ref={sourceSearchRef}
                    type="text"
                    placeholder="Pesquisar origem..."
                    value={sourceSearch}
                    onChange={(e) => setSourceSearch(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="w-full px-3 py-2 text-sm border border-light-gray rounded-lg focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange"
                    aria-label="Pesquisar origens"
                  />
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {!sourceSearch && (
                    <button
                      type="button"
                      onClick={() => handleSelectFilter('source', null)}
                      className="w-full px-4 py-2 text-left text-sm hover:bg-off-white text-medium-gray"
                      role="option"
                      aria-selected={!filters.source}
                    >
                      Todas as origens
                    </button>
                  )}
                  {filteredSources.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-medium-gray text-center">
                      Nenhuma origem encontrada
                    </div>
                  ) : (
                    filteredSources.map((source) => (
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
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

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
