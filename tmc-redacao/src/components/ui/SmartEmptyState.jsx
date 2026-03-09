import { useState, useEffect } from 'react';
import { Filter, Search, Hash, Tag, Building2, ArrowRight, XCircle } from 'lucide-react';
import { useFilters } from '../../context';
import { getArticles } from '../../services/api';
import { formatTagDisplay } from '../../utils/accentMap';
import PropTypes from 'prop-types';

/**
 * SmartEmptyState - Shown when filters return 0 results.
 * Shows which filters are active and suggests removing each one,
 * with live counts of how many results each removal would yield.
 */
const SmartEmptyState = ({ totalWithoutFilters = 0 }) => {
  const { filters, updateFilter, resetFilters } = useFilters();
  const [suggestions, setSuggestions] = useState([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  // Build active filters list
  const activeFilters = [];
  if (filters.searchQuery) {
    activeFilters.push({ key: 'searchQuery', label: `"${filters.searchQuery}"`, icon: Search });
  }
  if (filters.tag) {
    activeFilters.push({ key: 'tag', label: formatTagDisplay(filters.tag), icon: Hash });
  }
  if (filters.category) {
    activeFilters.push({ key: 'category', label: filters.category, icon: Tag });
  }
  if (filters.source) {
    activeFilters.push({ key: 'source', label: filters.source, icon: Building2 });
  }

  // Fetch counts for each filter removal suggestion
  useEffect(() => {
    if (activeFilters.length === 0) return;

    const controller = new AbortController();

    const debounceTimer = setTimeout(() => {
      const fetchSuggestionCounts = async () => {
        setIsLoadingSuggestions(true);
        const results = [];

        // For each active filter, check what happens if we remove it
        const promises = activeFilters.map(async (filter) => {
          try {
            const params = { limit: 1 };
            // Add all filters EXCEPT the one being removed
            if (filter.key !== 'searchQuery' && filters.searchQuery) {
              params.search = filters.searchQuery;
            }
            if (filter.key !== 'tag' && filters.tag) {
              params.tag = filters.tag;
            }
            if (filter.key !== 'category' && filters.category) {
              params.category = filters.category;
            }
            if (filter.key !== 'source' && filters.source) {
              params.source = filters.source;
            }
            if (filters.urgency) {
              params.max_hours = filters.urgency;
            }

            const response = await getArticles(params, { signal: controller.signal });
            return {
              ...filter,
              count: response?.total || 0,
            };
          } catch (err) {
            if (err.name === 'AbortError') return null;
            return { ...filter, count: null };
          }
        });

        const settled = await Promise.allSettled(promises);
        // If aborted, don't update state
        if (controller.signal.aborted) return;

        for (const result of settled) {
          if (result.status === 'fulfilled' && result.value) {
            results.push(result.value);
          }
        }

        // Sort by count descending (most results first)
        results.sort((a, b) => (b.count || 0) - (a.count || 0));
        setSuggestions(results);
        setIsLoadingSuggestions(false);
      };

      fetchSuggestionCounts();
    }, 500);

    return () => {
      clearTimeout(debounceTimer);
      controller.abort();
    };
  }, [filters.searchQuery, filters.tag, filters.category, filters.source, filters.urgency]);

  const handleRemoveFilter = (filterKey) => {
    if (filterKey === 'searchQuery') {
      updateFilter('searchQuery', '');
    } else {
      updateFilter(filterKey, null);
    }
  };

  const handleClearAll = () => {
    resetFilters();
  };

  const hasActiveFilters = activeFilters.length > 0;

  return (
    <div
      className="flex flex-col items-center justify-center text-center py-12 px-6 bg-white rounded-xl border border-light-gray"
      role="status"
      aria-live="polite"
    >
      <div className="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center mb-5" aria-hidden="true">
        <Filter size={32} className="text-amber-500" />
      </div>

      <h3 className="font-bold text-dark-gray mb-2 text-lg">
        Nenhuma matéria encontrada
      </h3>

      {hasActiveFilters ? (
        <>
          <p className="text-sm text-medium-gray mb-6 max-w-md">
            A combinação de filtros ativos não retornou resultados. Tente remover um dos filtros abaixo:
          </p>

          {/* Suggestions */}
          <div className="w-full max-w-sm space-y-2 mb-6">
            {isLoadingSuggestions ? (
              // Loading skeleton
              [...Array(activeFilters.length)].map((_, i) => (
                <div key={i} className="flex items-center justify-between px-4 py-2.5 bg-off-white rounded-lg animate-pulse">
                  <div className="h-4 w-32 bg-light-gray rounded" />
                  <div className="h-4 w-20 bg-light-gray rounded" />
                </div>
              ))
            ) : (
              suggestions.map((suggestion) => {
                const Icon = suggestion.icon;
                const hasResults = suggestion.count != null && suggestion.count > 0;
                return (
                  <button
                    key={suggestion.key}
                    type="button"
                    onClick={() => handleRemoveFilter(suggestion.key)}
                    className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg border transition-all text-left group ${
                      hasResults
                        ? 'bg-white border-light-gray hover:border-tmc-orange hover:bg-orange-50'
                        : 'bg-off-white border-transparent text-medium-gray'
                    }`}
                    aria-label={`Remover filtro ${suggestion.label}${hasResults ? `, ${suggestion.count} matérias` : ''}`}
                  >
                    <span className="flex items-center gap-2 text-sm">
                      <Icon size={14} className={hasResults ? 'text-tmc-orange' : 'text-medium-gray'} />
                      <span>
                        Remover <span className="font-medium">{suggestion.label}</span>
                      </span>
                    </span>
                    <span className="flex items-center gap-1.5 text-xs">
                      {suggestion.count != null && (
                        <span className={`font-medium ${hasResults ? 'text-tmc-orange' : 'text-medium-gray'}`}>
                          {suggestion.count} mat.
                        </span>
                      )}
                      {hasResults && (
                        <ArrowRight size={12} className="text-tmc-orange opacity-0 group-hover:opacity-100 transition-opacity" />
                      )}
                    </span>
                  </button>
                );
              })
            )}
          </div>

          {/* Clear all */}
          <button
            type="button"
            onClick={handleClearAll}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-medium-gray hover:text-red-600 hover:bg-red-50 border border-light-gray hover:border-red-200 transition-colors"
          >
            <XCircle size={16} />
            Limpar todos os filtros
            {totalWithoutFilters > 0 && (
              <span className="text-xs opacity-70">({totalWithoutFilters} mat.)</span>
            )}
          </button>
        </>
      ) : (
        <p className="text-sm text-medium-gray max-w-md">
          Não encontramos matérias no momento. Aguarde novas coletas.
        </p>
      )}
    </div>
  );
};

SmartEmptyState.propTypes = {
  totalWithoutFilters: PropTypes.number,
};

export default SmartEmptyState;
