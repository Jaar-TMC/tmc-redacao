import { memo, useState, useMemo, useCallback } from 'react';
import PropTypes from 'prop-types';
import { User, Cpu, AlertTriangle, AlertCircle, RefreshCw, Search, ChevronUp, ChevronDown } from 'lucide-react';
import Skeleton from '../ui/Skeleton';

const CostByUserTable = ({ data, isLoading, error, onRetry }) => {
  const [searchTerm, setSearchTerm] = useState('');
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

  const filtered = useMemo(() => {
    if (!data?.items) return [];
    let items = data.items;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      items = items.filter(u =>
        (u.user_name || '').toLowerCase().includes(term) ||
        (u.user_email || '').toLowerCase().includes(term)
      );
    }
    return [...items].sort((a, b) => {
      const aVal = a[sortField] ?? 0;
      const bVal = b[sortField] ?? 0;
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [data, searchTerm, sortField, sortDirection]);

  const avgCostPerArticle = useMemo(() => {
    if (!data?.items?.length) return 0;
    const total = data.items.reduce((s, u) => s + (u.cost_per_article || 0), 0);
    return total / data.items.length;
  }, [data]);

  const highestCostId = useMemo(() => {
    if (!filtered.length) return null;
    return filtered.reduce((max, u) => (u.total_cost > (max?.total_cost || 0)) ? u : max, filtered[0])?.user_id;
  }, [filtered]);

  if (isLoading) return (
    <div className="bg-white rounded-xl border border-light-gray p-6 space-y-3" role="status" aria-live="polite">
      <Skeleton variant="title" className="w-1/4" />
      <Skeleton variant="default" className="h-10 w-64" />
      {[...Array(5)].map((_, i) => <Skeleton key={i} variant="default" className="h-12 w-full" />)}
    </div>
  );

  if (error) return (
    <div className="bg-white rounded-xl border border-light-gray p-8">
      <div className="flex flex-col items-center justify-center py-8">
        <AlertCircle size={32} className="text-error mb-4" aria-hidden="true" />
        <p className="text-lg font-semibold text-dark-gray mb-2">Erro ao carregar custos por usuário</p>
        <p className="text-sm text-medium-gray mb-4">{error}</p>
        <button onClick={onRetry} className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center gap-2 min-h-[44px]">
          <RefreshCw size={16} aria-hidden="true" /> Tentar novamente
        </button>
      </div>
    </div>
  );

  if (!data?.items?.length && !data?.system_cost) return null;

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
      <div className="p-6 pb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h2 className="text-lg font-semibold text-dark-gray">Custos por Usuário</h2>
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-medium-gray" aria-hidden="true" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por nome ou email..."
            className="pl-9 pr-3 py-2 border border-light-gray rounded-lg text-sm w-full sm:w-64 focus:outline-none focus:ring-2 focus:ring-tmc-orange/50 focus:border-tmc-orange min-h-[44px]"
            aria-label="Buscar por nome ou email"
          />
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full" role="table" aria-label="Custos por usuário">
          <thead className="bg-off-white border-b border-light-gray">
            <tr>
              {renderTh('user_name', 'Usuário')}
              {renderTh('articles_generated', 'Artigos')}
              {renderTh('edits', 'Edições')}
              {renderTh('scans', 'Scans')}
              {renderTh('total_cost', 'Custo Total')}
              {renderTh('cost_per_article', 'Custo/Artigo')}
            </tr>
          </thead>
          <tbody>
            {filtered.map((user) => (
              <tr
                key={user.user_id}
                className={`border-b border-light-gray last:border-b-0 hover:bg-off-white/50 transition-colors ${
                  user.user_id === highestCostId ? 'border-l-4 border-l-tmc-orange' : ''
                }`}
              >
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-off-white rounded-full flex items-center justify-center flex-shrink-0">
                      <User size={14} className="text-medium-gray" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-dark-gray">{user.user_name}</p>
                      {user.user_email && <p className="text-xs text-medium-gray">{user.user_email}</p>}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-dark-gray">{user.articles_generated}</td>
                <td className="px-6 py-4 text-sm text-dark-gray">{user.edits || 0}</td>
                <td className="px-6 py-4 text-sm text-dark-gray">{user.scans || 0}</td>
                <td className="px-6 py-4 text-sm font-semibold text-dark-gray">${user.total_cost.toFixed(2)}</td>
                <td className="px-6 py-4 text-sm text-dark-gray">
                  <span className="inline-flex items-center gap-1">
                    ${(user.cost_per_article || 0).toFixed(2)}
                    {avgCostPerArticle > 0 && (user.cost_per_article || 0) > avgCostPerArticle * 2 && (
                      <AlertTriangle size={14} className="text-warning" aria-hidden="true" />
                    )}
                  </span>
                </td>
              </tr>
            ))}
            {data.system_cost > 0 && (
              <tr className="bg-off-white/50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-off-white rounded-full flex items-center justify-center flex-shrink-0">
                      <Cpu size={14} className="text-medium-gray" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-medium-gray">Sistema (Automático)</p>
                      <p className="text-xs text-medium-gray">Timers e processos automáticos</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-medium-gray">—</td>
                <td className="px-6 py-4 text-sm text-medium-gray">—</td>
                <td className="px-6 py-4 text-sm text-medium-gray">—</td>
                <td className="px-6 py-4 text-sm font-semibold text-medium-gray">${data.system_cost.toFixed(2)}</td>
                <td className="px-6 py-4 text-sm text-medium-gray">—</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Mobile */}
      <div className="md:hidden p-4 space-y-3">
        {filtered.map((user) => (
          <div key={user.user_id} className={`border border-light-gray rounded-lg p-4 ${user.user_id === highestCostId ? 'border-l-4 border-l-tmc-orange' : ''}`}>
            <div className="flex items-center gap-2 mb-2">
              <User size={16} className="text-medium-gray" aria-hidden="true" />
              <div>
                <p className="text-sm font-medium text-dark-gray">{user.user_name}</p>
                {user.user_email && <p className="text-xs text-medium-gray">{user.user_email}</p>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div><span className="text-medium-gray">Artigos:</span> <span className="text-dark-gray font-medium">{user.articles_generated}</span></div>
              <div><span className="text-medium-gray">Custo:</span> <span className="text-dark-gray font-semibold">${user.total_cost.toFixed(2)}</span></div>
              <div><span className="text-medium-gray">Edições:</span> <span className="text-dark-gray">{user.edits || 0}</span></div>
              <div><span className="text-medium-gray">Custo/Art:</span> <span className="text-dark-gray">${(user.cost_per_article || 0).toFixed(2)}</span></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

CostByUserTable.propTypes = {
  data: PropTypes.shape({
    items: PropTypes.arrayOf(PropTypes.shape({
      user_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      user_name: PropTypes.string.isRequired,
      user_email: PropTypes.string,
      articles_generated: PropTypes.number.isRequired,
      edits: PropTypes.number,
      scans: PropTypes.number,
      total_cost: PropTypes.number.isRequired,
      cost_per_article: PropTypes.number,
    })),
    system_cost: PropTypes.number,
  }),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};

export default memo(CostByUserTable);
