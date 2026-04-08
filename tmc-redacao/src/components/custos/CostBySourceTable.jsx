import { memo, useState, useMemo, useCallback } from 'react';
import PropTypes from 'prop-types';
import { Rss, AlertCircle, RefreshCw, ChevronUp, ChevronDown } from 'lucide-react';
import Skeleton from '../ui/Skeleton';

// Pure helper — hoisted out of the component to avoid re-creating on every render
// Green: up to median (inclusive), Yellow: median..2x median, Red: above 2x median
function getEfficiencyBg(costPerArticle, medianCost) {
  if (!medianCost || costPerArticle <= 0) return 'bg-success';
  if (costPerArticle <= medianCost) return 'bg-success';
  if (costPerArticle < medianCost * 2) return 'bg-warning';
  return 'bg-error';
}

const CostBySourceTable = ({ data, isLoading, error, onRetry }) => {
  const [sortField, setSortField] = useState('total_cost');
  const [sortDirection, setSortDirection] = useState('desc');

  const handleSort = useCallback((field) => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  }, [sortField]);

  const sorted = useMemo(() => {
    if (!data?.items) return [];
    return [...data.items].sort((a, b) => {
      const aVal = a[sortField] ?? 0;
      const bVal = b[sortField] ?? 0;
      if (typeof aVal === 'string') return sortDirection === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [data, sortField, sortDirection]);

  const medianCost = useMemo(() => {
    if (!sorted.length) return 0;
    const costs = sorted.map(s => s.cost_per_article).filter(c => c > 0).sort((a, b) => a - b);
    if (!costs.length) return 0;
    const mid = Math.floor(costs.length / 2);
    return costs.length % 2 === 0 ? (costs[mid - 1] + costs[mid]) / 2 : costs[mid];
  }, [sorted]);

  if (isLoading) return (
    <div className="bg-white rounded-xl border border-light-gray p-6 space-y-3" role="status" aria-live="polite">
      <Skeleton variant="title" className="w-1/4" />
      {[...Array(5)].map((_, i) => <Skeleton key={i} variant="default" className="h-10 w-full" />)}
    </div>
  );

  if (error) return (
    <div className="bg-white rounded-xl border border-light-gray p-8">
      <div className="flex flex-col items-center justify-center py-8">
        <AlertCircle size={32} className="text-error mb-4" aria-hidden="true" />
        <p className="text-lg font-semibold text-dark-gray mb-2">Erro ao carregar custos por fonte</p>
        <p className="text-sm text-medium-gray mb-4">{error}</p>
        <button onClick={onRetry} className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center gap-2 min-h-[44px]">
          <RefreshCw size={16} aria-hidden="true" /> Tentar novamente
        </button>
      </div>
    </div>
  );

  if (!sorted.length) return null;

  const renderSortIcon = (field) => {
    if (field !== sortField) return <ChevronDown size={14} className="text-light-gray" aria-hidden="true" />;
    return sortDirection === 'asc'
      ? <ChevronUp size={14} className="text-tmc-orange" aria-hidden="true" />
      : <ChevronDown size={14} className="text-tmc-orange" aria-hidden="true" />;
  };

  const renderTh = (field, label) => (
    <th
      key={field}
      scope="col"
      className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide cursor-pointer select-none"
      onClick={() => handleSort(field)}
      aria-sort={sortField === field ? (sortDirection === 'asc' ? 'ascending' : 'descending') : undefined}
    >
      <span className="inline-flex items-center gap-1">{label}{renderSortIcon(field)}</span>
    </th>
  );

  return (
    <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
      <div className="p-6 pb-0">
        <h2 className="text-lg font-semibold text-dark-gray">Custos por Fonte</h2>
      </div>

      {/* Desktop */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full" role="table" aria-label="Custos por fonte RSS">
          <thead className="bg-off-white border-b border-light-gray">
            <tr>
              {renderTh('source_name', 'Fonte')}
              {renderTh('articles_collected', 'Artigos Coletados')}
              {renderTh('total_cost', 'Custo Total')}
              {renderTh('cost_per_article', 'Custo/Artigo')}
            </tr>
          </thead>
          <tbody>
            {sorted.map((source) => (
              <tr key={source.source_id} className="border-b border-light-gray last:border-b-0 hover:bg-off-white/50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <Rss size={16} className="text-medium-gray flex-shrink-0" aria-hidden="true" />
                    <div>
                      <span className="text-sm font-medium text-dark-gray">{source.source_name}</span>
                      {source.category && (
                        <span className="ml-2 text-xs px-2 py-0.5 bg-off-white text-medium-gray rounded-full">{source.category}</span>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-dark-gray">{source.articles_collected.toLocaleString('pt-BR')}</td>
                <td className="px-6 py-4 text-sm font-semibold text-dark-gray">${source.total_cost.toFixed(4)}</td>
                <td className="px-6 py-4 text-sm">
                  <span className="inline-flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full inline-block ${getEfficiencyBg(source.cost_per_article, medianCost)}`} aria-hidden="true" />
                    ${source.cost_per_article.toFixed(4)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile */}
      <div className="md:hidden p-4 space-y-3">
        {sorted.map((source) => (
          <div key={source.source_id} className="border border-light-gray rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Rss size={16} className="text-medium-gray" aria-hidden="true" />
              <span className="text-sm font-medium text-dark-gray">{source.source_name}</span>
              {source.category && <span className="text-xs px-2 py-0.5 bg-off-white text-medium-gray rounded-full">{source.category}</span>}
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div><span className="text-medium-gray">Artigos:</span> <span className="text-dark-gray font-medium">{source.articles_collected.toLocaleString('pt-BR')}</span></div>
              <div><span className="text-medium-gray">Custo:</span> <span className="text-dark-gray font-semibold">${source.total_cost.toFixed(4)}</span></div>
              <div className="col-span-2">
                <span className="text-medium-gray">Custo/Artigo:</span>{' '}
                <span className="font-medium text-dark-gray">${source.cost_per_article.toFixed(4)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

CostBySourceTable.propTypes = {
  data: PropTypes.shape({
    items: PropTypes.arrayOf(PropTypes.shape({
      source_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      source_name: PropTypes.string.isRequired,
      category: PropTypes.string,
      articles_collected: PropTypes.number.isRequired,
      total_cost: PropTypes.number.isRequired,
      cost_per_article: PropTypes.number.isRequired,
    })),
  }),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};

export default memo(CostBySourceTable);
