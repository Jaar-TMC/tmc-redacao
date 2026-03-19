import { memo, useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Sparkles, Edit2, Shield, SearchCheck, ListTree, Merge, Tag,
  Globe, Rss, Database, BarChart3, Network, AlertCircle, RefreshCw, ChevronUp, ChevronDown
} from 'lucide-react';
import Skeleton from '../ui/Skeleton';

const ACTION_LABELS = {
  generate_article:  { label: 'Gerar Artigo', icon: Sparkles },
  edit_article:      { label: 'Editar Artigo', icon: Edit2 },
  fact_check_scan:   { label: 'Fact-Check Scan', icon: Shield },
  deep_verify:       { label: 'Verificação Profunda', icon: SearchCheck },
  extract_topics:    { label: 'Extrair Tópicos', icon: ListTree },
  merge_topics:      { label: 'Mesclar Tópicos', icon: Merge },
  generate_tags:     { label: 'Gerar Tags', icon: Tag },
  research:          { label: 'Pesquisar (Exa)', icon: Globe },
  system_rss:        { label: 'Sistema: RSS', icon: Rss },
  system_embedding:  { label: 'Sistema: Embeddings', icon: Database },
  system_scoring:    { label: 'Sistema: Scoring', icon: BarChart3 },
  system_clustering: { label: 'Sistema: Clustering', icon: Network },
  system_clustering_maintenance: { label: 'Sistema: Manutenção', icon: Network },
};

const SortIcon = ({ field, sortField, sortDirection }) => {
  if (field !== sortField) return <ChevronDown size={14} className="text-light-gray" aria-hidden="true" />;
  return sortDirection === 'asc'
    ? <ChevronUp size={14} className="text-tmc-orange" aria-hidden="true" />
    : <ChevronDown size={14} className="text-tmc-orange" aria-hidden="true" />;
};
SortIcon.propTypes = {
  field: PropTypes.string.isRequired,
  sortField: PropTypes.string.isRequired,
  sortDirection: PropTypes.oneOf(['asc', 'desc']).isRequired,
};

const CostBreakdownTable = ({ data, isLoading, error, onRetry }) => {
  const [sortField, setSortField] = useState('total_cost');
  const [sortDirection, setSortDirection] = useState('desc');

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sorted = useMemo(() => {
    if (!data?.items) return [];
    return [...data.items].sort((a, b) => {
      const aVal = a[sortField] ?? 0;
      const bVal = b[sortField] ?? 0;
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [data, sortField, sortDirection]);

  if (isLoading) return (
    <div className="bg-white rounded-xl border border-light-gray p-6 space-y-3" role="status" aria-live="polite">
      <Skeleton variant="title" className="w-1/4" />
      {[...Array(8)].map((_, i) => <Skeleton key={i} variant="default" className="h-10 w-full" />)}
    </div>
  );

  if (error) return (
    <div className="bg-white rounded-xl border border-light-gray p-8">
      <div className="flex flex-col items-center justify-center py-8">
        <AlertCircle size={32} className="text-error mb-4" aria-hidden="true" />
        <p className="text-lg font-semibold text-dark-gray mb-2">Erro ao carregar custos por ação</p>
        <p className="text-sm text-medium-gray mb-4">{error}</p>
        <button onClick={onRetry} className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center gap-2 min-h-[44px]">
          <RefreshCw size={16} aria-hidden="true" /> Tentar novamente
        </button>
      </div>
    </div>
  );

  if (!sorted.length) return null;

  const renderTh = (field, label) => (
    <th
      key={field}
      scope="col"
      className="text-left px-6 py-4 text-xs font-semibold text-medium-gray uppercase tracking-wide cursor-pointer select-none"
      onClick={() => handleSort(field)}
      aria-sort={sortField === field ? (sortDirection === 'asc' ? 'ascending' : 'descending') : undefined}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <SortIcon field={field} sortField={sortField} sortDirection={sortDirection} />
      </span>
    </th>
  );

  return (
    <div className="bg-white rounded-xl border border-light-gray overflow-hidden">
      <div className="p-6 pb-0">
        <h2 className="text-lg font-semibold text-dark-gray">Custos por Ação</h2>
      </div>

      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full" role="table" aria-label="Custos por ação">
          <thead className="bg-off-white border-b border-light-gray">
            <tr>
              {renderTh('action', 'Ação')}
              {renderTh('call_count', 'Chamadas')}
              {renderTh('total_cost', 'Custo Total')}
              {renderTh('avg_cost', 'Custo Médio')}
              {renderTh('pct_of_total', '% do Total')}
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => {
              const meta = ACTION_LABELS[item.action] || { label: item.action, icon: BarChart3 };
              const Icon = meta.icon;
              return (
                <tr key={item.action} className="border-b border-light-gray last:border-b-0 hover:bg-off-white/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <Icon size={16} className="text-medium-gray flex-shrink-0" aria-hidden="true" />
                      <span className="text-sm font-medium text-dark-gray">{meta.label}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-dark-gray">{item.call_count.toLocaleString('pt-BR')}</td>
                  <td className="px-6 py-4 text-sm font-semibold text-dark-gray">${item.total_cost.toFixed(2)}</td>
                  <td className="px-6 py-4 text-sm text-medium-gray">${item.avg_cost.toFixed(4)}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-off-white rounded-full overflow-hidden max-w-[120px]">
                        <div className="h-full bg-tmc-orange rounded-full" style={{ width: `${Math.min(item.pct_of_total, 100)}%` }} />
                      </div>
                      <span className="text-xs text-medium-gray w-12 text-right">{item.pct_of_total.toFixed(1)}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden p-4 space-y-3">
        {sorted.map((item) => {
          const meta = ACTION_LABELS[item.action] || { label: item.action, icon: BarChart3 };
          const Icon = meta.icon;
          return (
            <div key={item.action} className="border border-light-gray rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon size={16} className="text-medium-gray" aria-hidden="true" />
                <span className="text-sm font-medium text-dark-gray">{meta.label}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-medium-gray">Chamadas:</span> <span className="text-dark-gray font-medium">{item.call_count.toLocaleString('pt-BR')}</span></div>
                <div><span className="text-medium-gray">Custo:</span> <span className="text-dark-gray font-semibold">${item.total_cost.toFixed(2)}</span></div>
                <div><span className="text-medium-gray">Médio:</span> <span className="text-dark-gray">${item.avg_cost.toFixed(4)}</span></div>
                <div><span className="text-medium-gray">% Total:</span> <span className="text-dark-gray">{item.pct_of_total.toFixed(1)}%</span></div>
              </div>
              <div className="mt-2 h-1.5 bg-off-white rounded-full overflow-hidden">
                <div className="h-full bg-tmc-orange rounded-full" style={{ width: `${Math.min(item.pct_of_total, 100)}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

CostBreakdownTable.propTypes = {
  data: PropTypes.shape({
    items: PropTypes.arrayOf(PropTypes.shape({
      action: PropTypes.string.isRequired,
      call_count: PropTypes.number.isRequired,
      total_cost: PropTypes.number.isRequired,
      avg_cost: PropTypes.number.isRequired,
      pct_of_total: PropTypes.number.isRequired,
    })),
    total_cost: PropTypes.number,
  }),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};

export default memo(CostBreakdownTable);
