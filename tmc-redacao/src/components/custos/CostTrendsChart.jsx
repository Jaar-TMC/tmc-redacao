import { memo, useState, useCallback, lazy, Suspense } from 'react';
import PropTypes from 'prop-types';
import { DollarSign, AlertCircle, RefreshCw } from 'lucide-react';
import TabButton from '../ui/TabButton';
import EmptyState from '../ui/EmptyState';
import Skeleton from '../ui/Skeleton';

// Lazy-load recharts — it's ~150 KB parsed JS and not needed until the chart section renders
const RechartsLine = lazy(() =>
  import('recharts').then(m => ({
    default: ({ data, tickFormatter, tooltipContent }) => {
      const { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } = m;
      return (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
            <XAxis dataKey="date" tickFormatter={tickFormatter} tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={v => `$${v.toFixed(2)}`} tick={{ fontSize: 12 }} />
            <Tooltip content={tooltipContent} />
            <Line type="monotone" dataKey="total" stroke="#E87722" strokeWidth={2} name="Custo Total" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      );
    },
  }))
);

const RechartsArea = lazy(() =>
  import('recharts').then(m => ({
    default: ({ data, height, tickFormatter, tooltipContent }) => {
      const { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } = m;
      return (
        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
            <XAxis dataKey="date" tickFormatter={tickFormatter} tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={v => `$${v.toFixed(4)}`} tick={{ fontSize: 12 }} />
            <Tooltip content={tooltipContent} />
            <Area stackId="1" dataKey="embeddings" fill="#2D5A3D" stroke="#2D5A3D" fillOpacity={0.6} name="Embeddings" />
            <Area stackId="1" dataKey="exa" fill="#1A4D2E" stroke="#1A4D2E" fillOpacity={0.6} name="Exa (Pesquisa)" />
          </AreaChart>
        </ResponsiveContainer>
      );
    },
  }))
);

const ChartSkeleton = ({ height }) => (
  <div className="animate-pulse bg-off-white rounded" style={{ height }} aria-hidden="true" />
);
ChartSkeleton.propTypes = { height: PropTypes.number.isRequired };

const formatDatePtBR = (dateStr, granularity) => {
  if (!dateStr) return '';
  try {
    if (granularity === 'hour') {
      return dateStr.split(' ')[1] || dateStr;
    }
    if (granularity === 'month') {
      const [, month] = dateStr.split('-');
      const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
      return months[parseInt(month, 10) - 1] || dateStr;
    }
    // day or week: DD/MM
    const parts = dateStr.split('-');
    if (parts.length >= 3) return `${parts[2]}/${parts[1]}`;
    return dateStr;
  } catch {
    return dateStr;
  }
};

const CustomTooltip = memo(({ active, payload, label, nonLlmOnly }) => {
  if (!active || !payload || payload.length === 0) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="bg-white border border-light-gray rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-dark-gray mb-1">{label}</p>
      {!nonLlmOnly && (
        <p className="text-tmc-orange">Total: ${data.total?.toFixed(4)}</p>
      )}
      {!nonLlmOnly && (
        <p style={{ color: '#E87722' }}>LLM: ${data.llm?.toFixed(4)}</p>
      )}
      <p style={{ color: '#1A4D2E' }}>Exa: ${data.exa?.toFixed(4)}</p>
      <p style={{ color: '#2D5A3D' }}>Embeddings: ${data.embeddings?.toFixed(6)}</p>
    </div>
  );
});
CustomTooltip.displayName = 'CustomTooltip';

CustomTooltip.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.array,
  label: PropTypes.string,
  nonLlmOnly: PropTypes.bool,
};

const CostTrendsChart = ({ data, granularity, isLoading, error, onRetry }) => {
  const [chartMode, setChartMode] = useState('all');

  const tickFormatter = useCallback((val) => formatDatePtBR(val, granularity), [granularity]);

  if (isLoading) return (
    <div className="bg-white rounded-xl border border-light-gray p-6 space-y-4" role="status" aria-label="Carregando gráfico de tendências">
      <div className="flex items-center justify-between">
        <Skeleton variant="title" className="w-1/4" />
        <Skeleton variant="button" className="w-32" />
      </div>
      <Skeleton variant="default" className="h-[250px] w-full" />
      <Skeleton variant="default" className="h-[150px] w-full" />
    </div>
  );

  if (error) return (
    <div className="bg-white rounded-xl border border-light-gray p-8">
      <div className="flex flex-col items-center justify-center py-8">
        <AlertCircle size={32} className="text-error mb-4" aria-hidden="true" />
        <p className="text-lg font-semibold text-dark-gray mb-2">Erro ao carregar tendências</p>
        <p className="text-sm text-medium-gray mb-4">{error}</p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-tmc-orange text-white rounded-lg hover:bg-tmc-orange/90 transition-colors font-medium flex items-center gap-2 min-h-[44px]"
        >
          <RefreshCw size={16} aria-hidden="true" />
          Tentar novamente
        </button>
      </div>
    </div>
  );

  if (!data || data.length === 0) return (
    <div className="bg-white rounded-xl border border-light-gray p-6">
      <EmptyState
        icon={DollarSign}
        title="Nenhum dado de custo disponível"
        description="Não há dados de custo para o período selecionado."
      />
    </div>
  );

  return (
    <div className="bg-white rounded-xl border border-light-gray p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-dark-gray">Tendência de Custos</h2>
        <div className="flex gap-1 bg-off-white p-1 rounded-lg" role="tablist" aria-label="Modo de visualização">
          <TabButton active={chartMode === 'all'} onClick={() => setChartMode('all')} ariaLabel="Todos os custos">
            Todos
          </TabButton>
          <TabButton active={chartMode === 'non-llm'} onClick={() => setChartMode('non-llm')} ariaLabel="Sem custos LLM">
            Sem LLM
          </TabButton>
        </div>
      </div>

      {chartMode === 'all' && (
        <>
          <Suspense fallback={<ChartSkeleton height={250} />}>
            <RechartsLine
              data={data}
              tickFormatter={tickFormatter}
              tooltipContent={<CustomTooltip />}
            />
          </Suspense>

          <p className="text-xs text-medium-gray mt-4 mb-2 font-medium">
            Custos Exa + Embeddings (escala própria)
          </p>

          <Suspense fallback={<ChartSkeleton height={150} />}>
            <RechartsArea
              data={data}
              height={150}
              tickFormatter={tickFormatter}
              tooltipContent={<CustomTooltip nonLlmOnly />}
            />
          </Suspense>
        </>
      )}

      {chartMode === 'non-llm' && (
        <Suspense fallback={<ChartSkeleton height={300} />}>
          <RechartsArea
            data={data}
            height={300}
            tickFormatter={tickFormatter}
            tooltipContent={<CustomTooltip nonLlmOnly />}
          />
        </Suspense>
      )}
    </div>
  );
};

CostTrendsChart.propTypes = {
  data: PropTypes.arrayOf(PropTypes.shape({
    date: PropTypes.string.isRequired,
    total: PropTypes.number.isRequired,
    llm: PropTypes.number.isRequired,
    exa: PropTypes.number.isRequired,
    embeddings: PropTypes.number.isRequired,
  })),
  granularity: PropTypes.oneOf(['hour', 'day', 'week', 'month']),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};

export default memo(CostTrendsChart);
