import { Search, ChevronDown, Building2, Tag, Hash, HelpCircle, ArrowDownWideNarrow, Clock } from 'lucide-react';
import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import PropTypes from 'prop-types';
import { getSources, getCategories, getAllTags } from '../../services/api';
import { transformSources, transformCategories } from '../../utils/transformers';
import { useFilters } from '../../context';
import UrgencyChips from './UrgencyChips';
import { addAccents, formatTagDisplay, normalizeForSearch } from '../../utils/accentMap';

/**
 * FilterBar Component
 *
 * WCAG 2.1 Compliance:
 * - No Keyboard Trap (2.1.2): All dropdowns can be closed with Escape key
 * - Focus Order (2.4.3): Tab order follows visual order
 * - Link Purpose in Context (2.4.4): All filters have clear labels and context
 * - Headings and Labels (2.4.6): All form controls have descriptive labels
 */
const FilterBar = ({ urgencyCounts }) => {
  const { filters, updateFilter } = useFilters();
  const [searchTerm, setSearchTerm] = useState(filters.searchQuery || '');
  const [openDropdown, setOpenDropdown] = useState(null);

  // Search terms for dropdowns
  const [categorySearch, setCategorySearch] = useState('');
  const [tagSearch, setTagSearch] = useState('');

  // Refs to prevent race conditions between user typing and external updates
  const isUserTypingRef = useRef(false);
  const debounceTimerRef = useRef(null);
  const categorySearchRef = useRef(null);
  const tagSearchRef = useRef(null);

  // API State for filters
  const [categories, setCategories] = useState([]);
  const [sources, setSources] = useState([]);
  const [tags, setTags] = useState([]);

  // Fetch filter data from API - refetch when active filters change for contextual counts
  useEffect(() => {
    const fetchFilters = async () => {
      // Build contextual filter params (exclude the filter type being fetched)
      const catParams = {};
      const tagParams = {};

      // Categories: filter by tag, source, urgency, search (not by category itself)
      if (filters.tag) catParams.tag = filters.tag;
      if (filters.source) catParams.source = filters.source;
      if (filters.urgency) catParams.max_hours = filters.urgency;
      if (filters.searchQuery) catParams.search = filters.searchQuery;

      // Tags: filter by category, source, urgency (not by tag itself)
      if (filters.category) tagParams.category = filters.category;
      if (filters.source) tagParams.source = filters.source;
      if (filters.urgency) tagParams.max_hours = filters.urgency;

      const [catRes, srcRes, tagsRes] = await Promise.allSettled([
        getCategories(catParams),
        getSources(),
        getAllTags(tagParams)
      ]);

      if (catRes.status === 'fulfilled') {
        setCategories(transformCategories(catRes.value?.categories));
      }
      if (srcRes.status === 'fulfilled') {
        setSources(transformSources(srcRes.value?.items || srcRes.value?.sources));
      }
      if (tagsRes.status === 'fulfilled') {
        setTags(tagsRes.value?.items || []);
      }
    };
    fetchFilters();
  }, [filters.tag, filters.category, filters.source, filters.urgency, filters.searchQuery]);

  // Sync local state when filters.searchQuery changes externally (e.g., from TrendsSidebar)
  // Only update if user is not currently typing to prevent race conditions
  useEffect(() => {
    if (!isUserTypingRef.current && filters.searchQuery !== searchTerm) {
      setSearchTerm(filters.searchQuery || '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally omit searchTerm to avoid sync loop
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
        if (type === 'tag') setTagSearch('');
        return null;
      }
      // Opening dropdown - focus search after render
      setTimeout(() => {
        if (type === 'category' && categorySearchRef.current) {
          categorySearchRef.current.focus();
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

  // Memoize filtered lists to avoid recomputing on every render
  const filteredCategories = useMemo(() => {
    const term = normalizeForSearch(categorySearch);
    return categories.filter(cat =>
      normalizeForSearch(cat.name).includes(term) ||
      normalizeForSearch(addAccents(cat.name)).includes(term)
    );
  }, [categories, categorySearch]);

  const filteredSources = useMemo(() =>
    sources.filter(s => s.active),
  [sources]);

  const filteredTags = useMemo(() => {
    const term = normalizeForSearch(tagSearch);
    return tags.filter(t =>
      normalizeForSearch(t.theme).includes(term) ||
      normalizeForSearch(addAccents(t.theme)).includes(term) ||
      normalizeForSearch(t.tag).includes(term)
    );
  }, [tags, tagSearch]);

  const handleUrgencyChange = useCallback((value) => {
    updateFilter('urgency', value);
  }, [updateFilter]);

  return (
    <div className="bg-white rounded-xl border border-light-gray p-4 pb-3 mb-6" role="search" aria-label="Filtros de matérias">
      <div className="flex flex-wrap items-center gap-4">
        {/* Search Input */}
        <div className="flex-1 min-w-[200px] relative">
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
              <span className="hidden xl:inline">{addAccents(filters.category) || 'Tema'}</span>
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
                        <span>{addAccents(cat.name)}</span>
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
              aria-label={`Filtrar por tag: ${formatTagDisplay(filters.tag) || 'Todas as tags'}`}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
                filters.tag
                  ? 'bg-tmc-orange text-white'
                  : 'text-dark-gray border border-light-gray hover:bg-light-gray'
              }`}
            >
              <Hash style={{ width: '18px', height: '18px' }} aria-hidden="true" />
              <span className="hidden xl:inline">{formatTagDisplay(filters.tag) || 'Tag'}</span>
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
                          {addAccents(tagItem.theme)}
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
              <span className="hidden xl:inline">{addAccents(filters.source) || 'Origem'}</span>
              <ChevronDown style={{ width: '14px', height: '14px' }} aria-hidden="true" />
            </button>

            {openDropdown === 'source' && (
              <div className="absolute top-full right-0 mt-2 w-56 bg-white rounded-lg border border-light-gray py-2 z-20" role="listbox" aria-label="Origens disponíveis">
                <div className="max-h-64 overflow-y-auto">
                  <button
                    type="button"
                    onClick={() => handleSelectFilter('source', null)}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-off-white text-medium-gray"
                    role="option"
                    aria-selected={!filters.source}
                  >
                    Todas as origens
                  </button>
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
                        <span>{addAccents(source.name)}</span>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Urgency Chips + Score Classification Chips */}
      <div className="mt-3 pt-3 border-t border-dashed border-light-gray flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-medium-gray whitespace-nowrap">Período:</span>
          <UrgencyChips
          counts={urgencyCounts}
          activeUrgency={filters.urgency}
          onUrgencyChange={handleUrgencyChange}
        />
        </div>

        {/* Score Classification Chips */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-medium-gray whitespace-nowrap">Score:</span>
          <div className="flex items-center gap-1.5" role="radiogroup" aria-label="Filtrar por score editorial">
            {[
              { value: null, label: 'Todos',
                active: 'bg-medium-gray border-medium-gray text-white font-semibold shadow-sm',
                hover: 'hover:bg-off-white hover:border-medium-gray hover:text-dark-gray',
                dot: '', dotActive: '' },
              { value: 'A', label: 'A', fullLabel: 'Destaque',
                active: 'bg-success border-success text-white font-semibold shadow-sm',
                hover: 'hover:bg-success/10 hover:border-success hover:text-success',
                dot: 'bg-success', dotActive: 'bg-white/70' },
              { value: 'B', label: 'B', fullLabel: 'Relevante',
                active: 'bg-warning border-warning text-white font-semibold shadow-sm',
                hover: 'hover:bg-warning/10 hover:border-warning hover:text-warning',
                dot: 'bg-warning', dotActive: 'bg-white/70' },
              { value: 'C', label: 'C', fullLabel: 'Baixo',
                active: 'bg-medium-gray border-medium-gray text-white font-semibold shadow-sm',
                hover: 'hover:bg-off-white hover:border-medium-gray hover:text-dark-gray',
                dot: 'bg-medium-gray', dotActive: 'bg-white/70' },
            ].map((opt) => {
              const isActive = filters.scoreClassification === opt.value;
              return (
                <button
                  key={opt.value ?? 'all-scores'}
                  type="button"
                  role="radio"
                  aria-checked={isActive}
                  aria-label={opt.fullLabel ? `Score ${opt.label} - ${opt.fullLabel}` : 'Todos os scores'}
                  onClick={() => updateFilter('scoreClassification', isActive && opt.value !== null ? null : opt.value)}
                  className={`
                    inline-flex items-center gap-1 rounded-full border text-sm font-medium
                    transition-all duration-200 cursor-pointer
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500
                    px-3 py-1.5
                    ${isActive ? opt.active : `bg-white border-light-gray text-medium-gray ${opt.hover}`}
                  `}
                >
                  {opt.value && <span className={`w-2 h-2 rounded-full ${isActive ? opt.dotActive : opt.dot}`} aria-hidden="true" />}
                  <span>{opt.label}</span>
                  {opt.fullLabel && <span className="hidden md:inline">{opt.fullLabel}</span>}
                </button>
              );
            })}
          </div>

          {/* Score Help Tooltip */}
          <div className="relative group">
            <button
              type="button"
              className="p-1 text-medium-gray hover:text-tmc-orange transition-colors rounded-full hover:bg-off-white"
              aria-label="Entenda o score editorial"
            >
              <HelpCircle style={{ width: '16px', height: '16px' }} />
            </button>
            <div className="absolute top-full right-0 mt-2 w-80 bg-dark-gray text-white text-xs rounded-lg p-4 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-30 shadow-lg pointer-events-none">
              <p className="font-bold text-sm mb-2">Score Editorial (0-100)</p>
              <p className="mb-3 text-white/80">Cada matéria recebe um score baseado em 4 sinais editoriais que medem seu potencial jornalístico:</p>
              <div className="space-y-2">
                <div>
                  <span className="font-semibold text-amber-300">Inesperado (0-25)</span>
                  <p className="text-white/70">Mede o quão surpreendente é a notícia. Fatos inéditos, reviravoltas e revelações pontuam mais.</p>
                </div>
                <div>
                  <span className="font-semibold text-blue-300">Impacto (0-30)</span>
                  <p className="text-white/70">Avalia a abrangência do impacto: quantas pessoas são afetadas e a gravidade das consequências.</p>
                </div>
                <div>
                  <span className="font-semibold text-purple-300">Busca Agora (0-25)</span>
                  <p className="text-white/70">Estima a probabilidade de as pessoas estarem buscando sobre o assunto neste momento.</p>
                </div>
                <div>
                  <span className="font-semibold text-pink-300">Conversa (0-20)</span>
                  <p className="text-white/70">Mede o potencial de gerar discussão e compartilhamento em redes sociais.</p>
                </div>
              </div>
              <div className="mt-3 pt-2 border-t border-white/20 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-success" />
                  <span><strong>A</strong> Destaque (75+) — matérias imperdíveis</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-warning" />
                  <span><strong>B</strong> Relevante (40-74) — boas pautas</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-light-gray" />
                  <span><strong>C</strong> Baixo (&lt;40) — menor relevância</span>
                </div>
              </div>
              {/* Tooltip arrow */}
              <div className="absolute -top-1 right-3 w-2 h-2 bg-dark-gray rotate-45" />
            </div>
          </div>

          {/* Sort Order Divider + Toggle */}
          <div className="w-px h-5 bg-light-gray mx-1" aria-hidden="true" />
          <span className="text-xs font-semibold text-medium-gray whitespace-nowrap">Ordenar:</span>
          <div className="flex items-center gap-1" role="radiogroup" aria-label="Ordenar matérias">
            <button
              type="button"
              role="radio"
              aria-checked={filters.sortOrder === 'newest'}
              aria-label="Ordenar por mais recentes"
              onClick={() => updateFilter('sortOrder', 'newest')}
              className={`
                inline-flex items-center gap-1 rounded-full border text-sm font-medium
                transition-all duration-200 cursor-pointer px-3 py-1.5
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500
                ${filters.sortOrder === 'newest'
                  ? 'bg-tmc-dark-green border-tmc-dark-green text-white font-semibold shadow-sm'
                  : 'bg-white border-light-gray text-medium-gray hover:bg-off-white hover:border-tmc-dark-green hover:text-tmc-dark-green'}
              `}
            >
              <Clock style={{ width: '14px', height: '14px' }} aria-hidden="true" />
              <span className="hidden md:inline">Recentes</span>
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={filters.sortOrder === 'score'}
              aria-label="Ordenar por maior score"
              onClick={() => updateFilter('sortOrder', 'score')}
              className={`
                inline-flex items-center gap-1 rounded-full border text-sm font-medium
                transition-all duration-200 cursor-pointer px-3 py-1.5
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-500
                ${filters.sortOrder === 'score'
                  ? 'bg-tmc-dark-green border-tmc-dark-green text-white font-semibold shadow-sm'
                  : 'bg-white border-light-gray text-medium-gray hover:bg-off-white hover:border-tmc-dark-green hover:text-tmc-dark-green'}
              `}
            >
              <ArrowDownWideNarrow style={{ width: '14px', height: '14px' }} aria-hidden="true" />
              <span className="hidden md:inline">Score</span>
            </button>
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

FilterBar.propTypes = {
  urgencyCounts: PropTypes.shape({
    now: PropTypes.number,
    recent: PropTypes.number,
    today: PropTypes.number,
    all: PropTypes.number,
  }),
};

export default FilterBar;
