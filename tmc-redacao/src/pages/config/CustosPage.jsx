import { useState, useEffect, useRef, useCallback } from 'react';
import { Download, AlertCircle, Calendar } from 'lucide-react';
import TabButton from '../../components/ui/TabButton';
import StatusMessage from '../../components/ui/StatusMessage';
import CostOverviewCards from '../../components/custos/CostOverviewCards';
import CostTrendsChart from '../../components/custos/CostTrendsChart';
import CostBreakdownTable from '../../components/custos/CostBreakdownTable';
import CostByUserTable from '../../components/custos/CostByUserTable';
import CostBySourceTable from '../../components/custos/CostBySourceTable';
import WhatIfCalculator from '../../components/custos/WhatIfCalculator';
import {
  getCostOverview,
  getCostTrends,
  getCostBreakdown,
  getCostByUser,
  getCostBySource,
  getSourceEstimate,
} from '../../services/costsApi';

const PERIODS = [
  { value: 'today', label: 'Hoje' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: '90d', label: '90d' },
  { value: 'year', label: 'Ano' },
  { value: 'custom', label: 'Personalizado' },
];

function toDateString(d) {
  return d.toISOString().split('T')[0];
}

function granularityForDays(days) {
  if (days <= 1) return 'hour';
  if (days <= 60) return 'day';
  if (days <= 180) return 'week';
  return 'month';
}

function periodToDateRange(period, customStart, customEnd) {
  if (period === 'custom' && customStart && customEnd) {
    const days = Math.max(1, Math.round((new Date(customEnd) - new Date(customStart)) / 86400000));
    return { startDate: customStart, endDate: customEnd, granularity: granularityForDays(days) };
  }

  const now = new Date();
  const end = toDateString(now);
  let start;
  let granularity;

  switch (period) {
    case 'today':
      start = end;
      granularity = 'hour';
      break;
    case '7d':
      start = toDateString(new Date(now - 7 * 86400000));
      granularity = 'day';
      break;
    case '30d':
      start = toDateString(new Date(now - 30 * 86400000));
      granularity = 'day';
      break;
    case '90d':
      start = toDateString(new Date(now - 90 * 86400000));
      granularity = 'week';
      break;
    case 'year':
      start = `${now.getFullYear()}-01-01`;
      granularity = 'month';
      break;
    default:
      start = toDateString(new Date(now - 30 * 86400000));
      granularity = 'day';
  }

  return { startDate: start, endDate: end, granularity };
}

const CustosPage = () => {
  const [period, setPeriod] = useState('30d');
  const [customStart, setCustomStart] = useState(() => toDateString(new Date(Date.now() - 30 * 86400000)));
  const [customEnd, setCustomEnd] = useState(() => toDateString(new Date()));
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState(null);
  const [breakdown, setBreakdown] = useState(null);
  const [byUser, setByUser] = useState(null);
  const [bySource, setBySource] = useState(null);
  const [sourceEstimate, setSourceEstimate] = useState(null);
  const [granularity, setGranularity] = useState('day');

  const [loadingStates, setLoadingStates] = useState({
    overview: true, trends: true, breakdown: true,
    byUser: true, bySource: true, sourceEstimate: true,
  });
  const [errors, setErrors] = useState({
    overview: null, trends: null, breakdown: null,
    byUser: null, bySource: null, sourceEstimate: null,
  });
  const [lastFetchTime, setLastFetchTime] = useState(null);
  const [statusMessage, setStatusMessage] = useState({ type: 'success', message: '', isVisible: false });

  const abortControllerRef = useRef(null);
  const periodDebounceRef = useRef(null);

  const fetchAllData = useCallback(async (currentPeriod, cStart, cEnd) => {
    // Cancel previous requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const { signal } = controller;

    const { startDate, endDate, granularity: gran } = periodToDateRange(currentPeriod, cStart, cEnd);
    setGranularity(gran);

    const isCustom = currentPeriod === 'custom';
    const periodParam = isCustom ? undefined : currentPeriod;

    // Set all loading
    setLoadingStates({
      overview: true, trends: true, breakdown: true,
      byUser: true, bySource: true, sourceEstimate: true,
    });
    setErrors({
      overview: null, trends: null, breakdown: null,
      byUser: null, bySource: null, sourceEstimate: null,
    });

    const results = await Promise.allSettled([
      getCostOverview(periodParam, { signal, start: isCustom ? startDate : undefined, end: isCustom ? endDate : undefined }),
      getCostTrends({ granularity: gran, start: startDate, end: endDate, period: periodParam }, { signal }),
      getCostBreakdown({ start: startDate, end: endDate, period: periodParam }, { signal }),
      getCostByUser({ start: startDate, end: endDate, period: periodParam }, { signal }),
      getCostBySource({ start: startDate, end: endDate, period: periodParam }, { signal }),
      getSourceEstimate({ signal }),
    ]);

    // Don't update state if this request was aborted
    if (signal.aborted) return;

    const keys = ['overview', 'trends', 'breakdown', 'byUser', 'bySource', 'sourceEstimate'];
    const setters = [setOverview, setTrends, setBreakdown, setByUser, setBySource, setSourceEstimate];
    const newLoadingStates = {};
    const newErrors = {};

    results.forEach((result, i) => {
      const key = keys[i];
      newLoadingStates[key] = false;

      if (result.status === 'fulfilled') {
        setters[i](result.value);
        newErrors[key] = null;
      } else {
        if (result.reason?.name === 'AbortError') return;
        newErrors[key] = result.reason?.message || 'Erro ao carregar dados';
      }
    });

    setLoadingStates(prev => ({ ...prev, ...newLoadingStates }));
    setErrors(prev => ({ ...prev, ...newErrors }));
    setLastFetchTime(new Date());
  }, []);

  const handlePeriodChange = useCallback((newPeriod) => {
    setPeriod(newPeriod);
    if (newPeriod === 'custom') return; // wait for date inputs
    clearTimeout(periodDebounceRef.current);
    periodDebounceRef.current = setTimeout(() => {
      fetchAllData(newPeriod);
    }, 200);
  }, [fetchAllData]);

  const handleCustomDateApply = useCallback(() => {
    if (!customStart || !customEnd || customStart > customEnd) return;
    clearTimeout(periodDebounceRef.current);
    periodDebounceRef.current = setTimeout(() => {
      fetchAllData('custom', customStart, customEnd);
    }, 200);
  }, [fetchAllData, customStart, customEnd]);

  const retrySection = useCallback((key) => {
    const isCustom = period === 'custom';
    const { startDate, endDate, granularity: gran } = periodToDateRange(period, customStart, customEnd);
    const periodParam = isCustom ? undefined : period;
    const fetchMap = {
      overview: () => getCostOverview(periodParam, { start: isCustom ? startDate : undefined, end: isCustom ? endDate : undefined }),
      trends: () => getCostTrends({ granularity: gran, start: startDate, end: endDate, period: periodParam }),
      breakdown: () => getCostBreakdown({ start: startDate, end: endDate, period: periodParam }),
      byUser: () => getCostByUser({ start: startDate, end: endDate, period: periodParam }),
      bySource: () => getCostBySource({ start: startDate, end: endDate, period: periodParam }),
      sourceEstimate: () => getSourceEstimate(),
    };
    const setterMap = { overview: setOverview, trends: setTrends, breakdown: setBreakdown, byUser: setByUser, bySource: setBySource, sourceEstimate: setSourceEstimate };
    const fetchFn = fetchMap[key];
    const setter = setterMap[key];
    if (!fetchFn || !setter) return;

    setLoadingStates(prev => ({ ...prev, [key]: true }));
    setErrors(prev => ({ ...prev, [key]: null }));
    fetchFn()
      .then(data => { setter(data); setErrors(prev => ({ ...prev, [key]: null })); })
      .catch(err => { setErrors(prev => ({ ...prev, [key]: err?.message || 'Erro ao carregar dados' })); })
      .finally(() => { setLoadingStates(prev => ({ ...prev, [key]: false })); });
  }, [period, customStart, customEnd]);

  // Initial fetch on mount
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: initial data load on mount
    fetchAllData(period);
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
      clearTimeout(periodDebounceRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleExportCSV = useCallback(() => {
    try {
      const rows = [['Ação', 'Chamadas', 'Custo Total', 'Custo Médio', '% do Total']];
      if (breakdown?.items) {
        breakdown.items.forEach(item => {
          rows.push([item.action, item.call_count, item.total_cost, item.avg_cost, item.pct_of_total]);
        });
      }
      const csv = rows.map(r => r.join(',')).join('\n');
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const suffix = period === 'custom' ? `${customStart}_${customEnd}` : period;
      a.download = `custos-tmc-${suffix}-${toDateString(new Date())}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      setStatusMessage({ type: 'success', message: 'CSV exportado com sucesso', isVisible: true });
    } catch {
      setStatusMessage({ type: 'error', message: 'Erro ao exportar CSV', isVisible: true });
    }
  }, [breakdown, period, customStart, customEnd]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-gray">Custos</h1>
          <p className="text-sm text-medium-gray mt-1">Acompanhe os gastos com IA, busca e embeddings</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {lastFetchTime && (
            <span className="text-xs text-medium-gray">
              Atualizado em {lastFetchTime.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 text-sm font-medium text-medium-gray hover:text-dark-gray border border-light-gray rounded-lg hover:bg-off-white transition-colors flex items-center gap-2 min-h-[44px]"
            aria-label="Exportar dados de custos em CSV"
          >
            <Download size={16} aria-hidden="true" />
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-error/10 border-2 border-error/30 rounded-xl px-5 py-4 flex items-start gap-3">
        <AlertCircle size={22} className="text-error flex-shrink-0 mt-0.5" aria-hidden="true" />
        <div>
          <p className="text-sm font-bold text-error mb-1">Valores estimados — não representam a fatura real</p>
          <p className="text-sm text-dark-gray">Os custos são calculados com base nos tokens consumidos e nos preços publicados pela Anthropic. Os valores não incluem impostos e podem divergir da fatura real em caso de acordos comerciais, descontos ou alterações de preço. Custos de Exa e embeddings usam valores médios configuráveis via variáveis de ambiente.</p>
        </div>
      </div>

      {/* Period selector */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          {/* Mobile: select */}
          <select
            value={period}
            onChange={(e) => handlePeriodChange(e.target.value)}
            className="md:hidden px-3 py-2 border border-light-gray rounded-lg text-sm bg-white min-h-[44px]"
            aria-label="Período de custos"
          >
            {PERIODS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
          </select>

          {/* Desktop: TabButtons */}
          <div className="hidden md:flex flex-wrap gap-1 bg-off-white p-1 rounded-lg w-fit" role="tablist" aria-label="Período de custos">
            {PERIODS.map(p => (
              <TabButton
                key={p.value}
                active={period === p.value}
                onClick={() => handlePeriodChange(p.value)}
                ariaLabel={`Período: ${p.label}`}
              >
                {p.value === 'custom' ? (
                  <span className="flex items-center gap-1.5">
                    <Calendar size={14} aria-hidden="true" />
                    {p.label}
                  </span>
                ) : p.label}
              </TabButton>
            ))}
          </div>
        </div>

        {/* Custom date range inputs */}
        {period === 'custom' && (
          <div className="flex flex-wrap items-end gap-3 bg-off-white border border-light-gray rounded-lg p-3">
            <div className="flex flex-col gap-1">
              <label htmlFor="custom-start" className="text-xs font-medium text-medium-gray">Início</label>
              <input
                id="custom-start"
                type="date"
                value={customStart}
                max={customEnd}
                onChange={(e) => setCustomStart(e.target.value)}
                className="px-3 py-2 border border-light-gray rounded-lg text-sm bg-white min-h-[44px]"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="custom-end" className="text-xs font-medium text-medium-gray">Fim</label>
              <input
                id="custom-end"
                type="date"
                value={customEnd}
                min={customStart}
                max={toDateString(new Date())}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="px-3 py-2 border border-light-gray rounded-lg text-sm bg-white min-h-[44px]"
              />
            </div>
            <button
              onClick={handleCustomDateApply}
              disabled={!customStart || !customEnd || customStart > customEnd}
              className="px-5 py-2 text-sm font-medium text-white bg-tmc-orange rounded-lg hover:bg-tmc-orange/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
            >
              Aplicar
            </button>
            {customStart && customEnd && customStart <= customEnd && (
              <span className="text-xs text-medium-gray self-center">
                {Math.round((new Date(customEnd) - new Date(customStart)) / 86400000) + 1} dias
              </span>
            )}
          </div>
        )}
      </div>

      {/* Status message */}
      <StatusMessage
        type={statusMessage.type}
        message={statusMessage.message}
        isVisible={statusMessage.isVisible}
        onDismiss={() => setStatusMessage(prev => ({ ...prev, isVisible: false }))}
      />

      {/* Sections */}
      <CostOverviewCards
        data={overview}
        trends={trends?.data}
        isLoading={loadingStates.overview}
        error={errors.overview}
        onRetry={() => retrySection('overview')}
      />

      <CostTrendsChart
        data={trends?.data}
        granularity={granularity}
        isLoading={loadingStates.trends}
        error={errors.trends}
        onRetry={() => retrySection('trends')}
      />

      <CostBreakdownTable
        data={breakdown}
        isLoading={loadingStates.breakdown}
        error={errors.breakdown}
        onRetry={() => retrySection('breakdown')}
      />

      <CostByUserTable
        data={byUser}
        isLoading={loadingStates.byUser}
        error={errors.byUser}
        onRetry={() => retrySection('byUser')}
      />

      <CostBySourceTable
        data={bySource}
        isLoading={loadingStates.bySource}
        error={errors.bySource}
        onRetry={() => retrySection('bySource')}
      />

      <WhatIfCalculator
        sourceEstimate={sourceEstimate}
        isLoading={loadingStates.sourceEstimate}
        error={errors.sourceEstimate}
        onRetry={() => retrySection('sourceEstimate')}
      />
    </div>
  );
};

export default CustosPage;
