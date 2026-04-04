import { useMemo, useState, useEffect } from 'react';
import { Filter, Search, Hash, Tag, Building2, ArrowRight, XCircle } from 'lucide-react';
import { useFilters } from '../../context';
import { formatTagDisplay } from '../../utils/accentMap';
import { getSourcesCached } from '../../services/api';
import PropTypes from 'prop-types';

/**
 * SmartEmptyState - Shown when filters return 0 results.
 * Shows which filters are active and suggests removing each one.
 * Suggestions are derived client-side (no API calls) to avoid N+1 requests.
 */
const SmartEmptyState = ({ totalWithoutFilters = 0 }) => {
  const { filters, updateFilter, resetFilters } = useFilters();
  const [sources, setSources] = useState([]);

  // Load sources once to resolve source IDs to display names
  useEffect(() => {
    let cancelled = false;
    getSourcesCached().then(res => {
      if (!cancelled && res?.items) setSources(res.items);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // Derive suggestions statically from active filters — no API calls needed.
  // Previously this fired N separate getArticles calls (one per active filter),
  // causing an API explosion with 4+ filters. Now we simply list the active
  // filters as removal suggestions without counts.
  const suggestions = useMemo(() => {
    const active = [];
    if (filters.searchQuery) {
      active.push({ key: 'searchQuery', label: `"${filters.searchQuery}"`, icon: Search });
    }
    if (filters.tag) {
      active.push({ key: 'tag', label: formatTagDisplay(filters.tag), icon: Hash });
    }
    if (filters.category) {
      active.push({ key: 'category', label: filters.category, icon: Tag });
    }
    if (filters.source) {
      const sourceName = sources.find(s => s.id === filters.source)?.name || filters.source;
      active.push({ key: 'source', label: sourceName, icon: Building2 });
    }
    return active;
  }, [filters.searchQuery, filters.tag, filters.category, filters.source, sources]);

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

  const hasActiveFilters = suggestions.length > 0;

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

          {/* Suggestions — derived client-side, no loading state needed */}
          <div className="w-full max-w-sm space-y-2 mb-6">
            {suggestions.map((suggestion) => {
              const Icon = suggestion.icon;
              return (
                <button
                  key={suggestion.key}
                  type="button"
                  onClick={() => handleRemoveFilter(suggestion.key)}
                  className="w-full flex items-center justify-between px-4 py-2.5 rounded-lg border transition-all text-left group bg-white border-light-gray hover:border-tmc-orange hover:bg-orange-50"
                  aria-label={`Remover filtro ${suggestion.label}`}
                >
                  <span className="flex items-center gap-2 text-sm">
                    <Icon size={14} className="text-tmc-orange" />
                    <span>
                      Remover <span className="font-medium">{suggestion.label}</span>
                    </span>
                  </span>
                  <ArrowRight size={12} className="text-tmc-orange opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              );
            })}
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
