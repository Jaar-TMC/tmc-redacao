import { X, Search, Hash, Tag, Building2, XCircle, Award, Clock } from 'lucide-react';
import { useFilters } from '../../context';
import { addAccents, formatTagDisplay } from '../../utils/accentMap';
import PropTypes from 'prop-types';

/**
 * ActiveFiltersBar - Shows removable chips for each active filter.
 * Appears between FilterBar and article grid when any filter is active.
 * Urgency is excluded (always visible in UrgencyChips).
 */
const ActiveFiltersBar = ({ className = '' }) => {
  const { filters, updateFilter, resetFilters } = useFilters();

  // Build list of active filters
  const activeFilters = [];

  if (filters.urgency) {
    const urgencyLabels = { 1: 'Última hora', 3: 'Últimas 3h', 8: 'Últimas 8h' };
    activeFilters.push({
      key: 'urgency',
      label: urgencyLabels[filters.urgency] || `${filters.urgency}h`,
      icon: Clock,
      color: 'bg-sky-50 text-sky-700 border-sky-200',
      hoverColor: 'hover:bg-sky-100',
    });
  }

  if (filters.searchQuery) {
    activeFilters.push({
      key: 'searchQuery',
      label: `"${filters.searchQuery}"`,
      icon: Search,
      color: 'bg-blue-50 text-blue-700 border-blue-200',
      hoverColor: 'hover:bg-blue-100',
    });
  }

  if (filters.tag) {
    activeFilters.push({
      key: 'tag',
      label: formatTagDisplay(filters.tag),
      icon: Hash,
      color: 'bg-orange-50 text-orange-700 border-orange-200',
      hoverColor: 'hover:bg-orange-100',
    });
  }

  if (filters.category) {
    activeFilters.push({
      key: 'category',
      label: addAccents(filters.category),
      icon: Tag,
      color: 'bg-purple-50 text-purple-700 border-purple-200',
      hoverColor: 'hover:bg-purple-100',
    });
  }

  if (filters.source) {
    activeFilters.push({
      key: 'source',
      label: addAccents(filters.source),
      icon: Building2,
      color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      hoverColor: 'hover:bg-emerald-100',
    });
  }

  if (filters.scoreClassification) {
    const classLabels = { A: 'A - Destaque', B: 'B - Relevante', C: 'C - Baixo' };
    const classColors = {
      A: { color: 'bg-success/10 text-success border-success/30', hoverColor: 'hover:bg-success/20' },
      B: { color: 'bg-warning/10 text-warning border-warning/30', hoverColor: 'hover:bg-warning/20' },
      C: { color: 'bg-medium-gray/10 text-medium-gray border-medium-gray/30', hoverColor: 'hover:bg-medium-gray/20' },
    };
    const colors = classColors[filters.scoreClassification] || classColors.B;
    activeFilters.push({
      key: 'scoreClassification',
      label: classLabels[filters.scoreClassification] || filters.scoreClassification,
      icon: Award,
      color: colors.color,
      hoverColor: colors.hoverColor,
    });
  }

  // Don't render if no active filters
  if (activeFilters.length === 0) return null;

  const handleRemoveFilter = (filterKey) => {
    if (filterKey === 'searchQuery') {
      updateFilter('searchQuery', '');
    } else {
      updateFilter(filterKey, null);
    }
  };

  const handleClearAll = () => {
    // Keep urgency, clear everything else
    resetFilters();
  };

  return (
    <div
      className={`flex items-center gap-2 flex-wrap mb-4 ${className}`}
      role="status"
      aria-label="Filtros ativos"
    >
      <span className="text-xs text-medium-gray font-medium mr-1">Filtros:</span>

      {activeFilters.map((filter) => {
        const Icon = filter.icon;
        return (
          <span
            key={filter.key}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${filter.color}`}
          >
            <Icon size={12} aria-hidden="true" />
            <span className="max-w-[150px] truncate">{filter.label}</span>
            <button
              type="button"
              onClick={() => handleRemoveFilter(filter.key)}
              className={`ml-0.5 p-0.5 rounded-full transition-colors ${filter.hoverColor}`}
              aria-label={`Remover filtro: ${filter.label}`}
            >
              <X size={12} />
            </button>
          </span>
        );
      })}

      {activeFilters.length > 1 && (
        <button
          type="button"
          onClick={handleClearAll}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium text-medium-gray hover:text-red-600 hover:bg-red-50 transition-colors"
          aria-label="Limpar todos os filtros"
        >
          <XCircle size={12} />
          Limpar tudo
        </button>
      )}
    </div>
  );
};

ActiveFiltersBar.propTypes = {
  className: PropTypes.string,
};

export default ActiveFiltersBar;
