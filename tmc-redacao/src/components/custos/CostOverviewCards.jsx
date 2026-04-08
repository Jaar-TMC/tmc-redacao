import { memo, lazy, Suspense } from 'react';
import PropTypes from 'prop-types';
import { DollarSign, Activity, FileText, TrendingUp, AlertCircle, RefreshCw } from 'lucide-react';
import Skeleton from '../ui/Skeleton';

// Lazy-load recharts for sparklines — avoids blocking the overview cards initial render
const RechartsSparkline = lazy(() =>
  import('recharts').then(m => ({
    default: ({ data, dataKey }) => {
      const { LineChart, Line, ResponsiveContainer } = m;
      return (
        <ResponsiveContainer width="100%" height={30}>
          <LineChart data={data}>
            <Line type="monotone" dataKey={dataKey} stroke="#E87722" strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      );
    },
  }))
);

const ProviderBar = memo(({ split }) => {
  if (!split) return null;
  const total = (split.llm || 0) + (split.exa || 0) + (split.embeddings || 0);
  if (total === 0) return null;
  const llmPct = ((split.llm || 0) / total) * 100;
  const exaPct = ((split.exa || 0) / total) * 100;
  const embPct = ((split.embeddings || 0) / total) * 100;
  return (
    <div className="flex h-1.5 rounded-full overflow-hidden bg-off-white mt-3" aria-hidden="true">
      {llmPct > 0 && <div className="bg-tmc-orange" style={{ width: `${llmPct}%` }} />}
      {exaPct > 0 && <div style={{ width: `${exaPct}%`, backgroundColor: '#1A4D2E' }} />}
      {embPct > 0 && <div style={{ width: `${embPct}%`, backgroundColor: '#2D5A3D' }} />}
    </div>
  );
});
ProviderBar.displayName = 'ProviderBar';

ProviderBar.propTypes = {
  split: PropTypes.shape({
    llm: PropTypes.number,
    exa: PropTypes.number,
    embeddings: PropTypes.number,
  }),
};

const Sparkline = memo(({ data, dataKey }) => {
  if (!data || data.length < 2) return null;
  return (
    <div className="mt-2" aria-hidden="true">
      <Suspense fallback={<div className="h-[30px]" />}>
        <RechartsSparkline data={data} dataKey={dataKey} />
      </Suspense>
    </div>
  );
});
Sparkline.displayName = 'Sparkline';

Sparkline.propTypes = {
  data: PropTypes.arrayOf(PropTypes.object),
  dataKey: PropTypes.string.isRequired,
};

const formatCurrency = (value, decimals = 2) => {
  if (value == null) return '$0.00';
  return `$${Number(value).toFixed(decimals)}`;
};

const formatNumber = (value) => {
  if (value == null) return '0';
  return Number(value).toLocaleString('pt-BR');
};

// eslint-disable-next-line no-unused-vars -- Icon is used as JSX component on next line
const MetricCard = memo(({ icon: Icon, iconColor, label, value, subtitle, sparklineData, sparklineKey, providerSplit }) => (
  <div className="bg-white rounded-xl border border-light-gray p-6">
    <div className="flex items-center gap-2 mb-3">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconColor || 'bg-off-white'}`}>
        <Icon size={16} className={iconColor ? 'text-white' : 'text-medium-gray'} aria-hidden="true" />
      </div>
      <span className="text-xs font-semibold text-medium-gray uppercase tracking-wide">{label}</span>
    </div>
    <div className="text-2xl font-bold text-dark-gray">{value}</div>
    {subtitle && <p className="text-xs text-medium-gray mt-1">{subtitle}</p>}
    <Sparkline data={sparklineData} dataKey={sparklineKey || 'total'} />
  </div>
));
MetricCard.displayName = 'MetricCard';

MetricCard.propTypes = {
  icon: PropTypes.elementType.isRequired,
  iconColor: PropTypes.string,
  label: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  subtitle: PropTypes.string,
  sparklineData: PropTypes.arrayOf(PropTypes.object),
  sparklineKey: PropTypes.string,
  providerSplit: PropTypes.shape({
    llm: PropTypes.number,
    exa: PropTypes.number,
    embeddings: PropTypes.number,
  }),
};

const LoadingSkeleton = () => (
  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" role="status" aria-label="Carregando dados de custo">
    {[...Array(4)].map((_, i) => (
      <div key={i} className="bg-white rounded-xl border border-light-gray p-6 space-y-3">
        <div className="flex items-center gap-2">
          <Skeleton variant="circle" />
          <Skeleton variant="text" className="w-1/3" />
        </div>
        <Skeleton variant="title" className="w-1/2" />
        <Skeleton variant="text" className="w-2/3" />
        <Skeleton variant="default" className="h-1.5 w-full" />
      </div>
    ))}
  </div>
);

const CostOverviewCards = ({ data, trends, isLoading, error, onRetry }) => {
  if (isLoading) return <LoadingSkeleton />;

  if (error) return (
    <div className="bg-white rounded-xl border border-light-gray p-8">
      <div className="flex flex-col items-center justify-center py-8">
        <AlertCircle size={32} className="text-error mb-4" aria-hidden="true" />
        <p className="text-lg font-semibold text-dark-gray mb-2">Erro ao carregar dados</p>
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

  if (!data) return null;

  const sparklineData = trends || [];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        icon={DollarSign}
        iconColor="bg-tmc-orange"
        label="CUSTO TOTAL"
        value={`${formatCurrency(data.total_cost)} USD`}
        sparklineData={sparklineData}
        sparklineKey="total"
        providerSplit={data.provider_split}
      />
      <MetricCard
        icon={Activity}
        label="CHAMADAS DE IA"
        value={formatNumber(data.total_calls)}
        subtitle={`Sonnet: ${formatNumber(data.sonnet_calls)} · Haiku: ${formatNumber(data.haiku_calls)}`}
        sparklineData={sparklineData}
        sparklineKey="total"
        providerSplit={data.provider_split}
      />
      <MetricCard
        icon={FileText}
        label="CUSTO MÉDIO/ARTIGO"
        value={formatCurrency(data.avg_cost_per_article)}
        subtitle={`Baseado em ${formatNumber(data.articles_generated)} artigos gerados`}
        sparklineData={sparklineData}
        sparklineKey="total"
        providerSplit={data.provider_split}
      />
      <MetricCard
        icon={TrendingUp}
        label="PROJEÇÃO MENSAL"
        value={formatCurrency(data.projected_monthly)}
        subtitle="Baseado nos últimos 7 dias"
        sparklineData={sparklineData}
        sparklineKey="total"
        providerSplit={data.provider_split}
      />
    </div>
  );
};

CostOverviewCards.propTypes = {
  data: PropTypes.shape({
    total_cost: PropTypes.number,
    delta_percent: PropTypes.number,
    total_calls: PropTypes.number,
    sonnet_calls: PropTypes.number,
    haiku_calls: PropTypes.number,
    avg_cost_per_article: PropTypes.number,
    articles_generated: PropTypes.number,
    projected_monthly: PropTypes.number,
    provider_split: PropTypes.shape({
      llm: PropTypes.number,
      exa: PropTypes.number,
      embeddings: PropTypes.number,
    }),
  }),
  trends: PropTypes.arrayOf(PropTypes.object),
  isLoading: PropTypes.bool.isRequired,
  error: PropTypes.string,
  onRetry: PropTypes.func.isRequired,
};

export default memo(CostOverviewCards);
