import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  X,
  ChevronRight,
  Clock,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Eye,
  Search,
  Loader2,
  Wand2,
  RefreshCw,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const VERDICT_CONFIG = {
  grounded: {
    label: 'Verificada',
    border: 'border-l-green-500',
    bg: 'bg-green-50',
    badgeBg: 'bg-green-100',
    badgeText: 'text-green-700',
    Icon: CheckCircle2,
  },
  fabricated: {
    label: 'Fabricada',
    border: 'border-l-red-500',
    bg: 'bg-red-50',
    badgeBg: 'bg-red-100',
    badgeText: 'text-red-700',
    Icon: AlertTriangle,
  },
  unverifiable: {
    label: 'Não verificável',
    border: 'border-l-amber-500',
    bg: 'bg-amber-50',
    badgeBg: 'bg-amber-100',
    badgeText: 'text-amber-700',
    Icon: HelpCircle,
  },
  opinion: {
    label: 'Opinião',
    border: 'border-l-blue-500',
    bg: 'bg-blue-50',
    badgeBg: 'bg-blue-100',
    badgeText: 'text-blue-700',
    Icon: Eye,
  },
};

function getVerdictConfig(verdict) {
  return VERDICT_CONFIG[verdict] || VERDICT_CONFIG.unverifiable;
}

function getAsiColor(asi) {
  if (asi >= 80) return '#10B981';
  if (asi >= 50) return '#F59E0B';
  return '#EF4444';
}

const SAFETY_LABEL_DISPLAY = {
  seguro: 'Seguro',
  atencao: 'Atenção',
  inseguro: 'Inseguro',
  critico: 'Crítico',
};

function getSafetyLabelDisplay(label) {
  return SAFETY_LABEL_DISPLAY[label] || label;
}

function getSafetyLabelStyle(label) {
  switch (label) {
    case 'seguro':
      return 'text-success';
    case 'atencao':
      return 'text-warning';
    case 'inseguro':
    case 'critico':
      return 'text-error';
    default:
      return 'text-medium-gray';
  }
}

function formatDuration(ms) {
  if (!ms) return '--';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function SeverityDots({ severity }) {
  switch (severity) {
    case 'critical':
      return (
        <span className="flex items-center gap-0.5" title="Crítico">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
        </span>
      );
    case 'high':
      return (
        <span className="flex items-center gap-0.5" title="Alto">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
        </span>
      );
    case 'medium':
      return (
        <span className="flex items-center gap-0.5" title="Médio">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        </span>
      );
    case 'low':
    default:
      return (
        <span className="flex items-center gap-0.5" title="Baixo">
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
        </span>
      );
  }
}

SeverityDots.propTypes = {
  severity: PropTypes.string,
};

// ---------------------------------------------------------------------------
// ASI Gauge (SVG)
// ---------------------------------------------------------------------------

const GAUGE_RADIUS = 54;
const GAUGE_STROKE = 8;
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * GAUGE_RADIUS;

function AsiGauge({ value, label }) {
  const [offset, setOffset] = useState(GAUGE_CIRCUMFERENCE);
  const color = getAsiColor(value);

  useEffect(() => {
    // Trigger animation on mount
    const target = GAUGE_CIRCUMFERENCE - (value / 100) * GAUGE_CIRCUMFERENCE;
    const frame = requestAnimationFrame(() => setOffset(target));
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-32 w-32">
        <svg
          className="h-full w-full -rotate-90"
          viewBox="0 0 128 128"
        >
          {/* Background track */}
          <circle
            cx="64"
            cy="64"
            r={GAUGE_RADIUS}
            fill="none"
            stroke="#E5E7EB"
            strokeWidth={GAUGE_STROKE}
          />
          {/* Foreground arc */}
          <circle
            cx="64"
            cy="64"
            r={GAUGE_RADIUS}
            fill="none"
            stroke={color}
            strokeWidth={GAUGE_STROKE}
            strokeLinecap="round"
            strokeDasharray={GAUGE_CIRCUMFERENCE}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 1s ease-out' }}
          />
        </svg>
        {/* Number overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold" style={{ color }}>
            {value}
          </span>
          <span className="text-[10px] font-medium text-medium-gray tracking-wide uppercase">
            ASI
          </span>
        </div>
      </div>
      {label && (
        <span
          className={`mt-1.5 text-sm font-semibold ${getSafetyLabelStyle(label)}`}
        >
          {getSafetyLabelDisplay(label)}
        </span>
      )}
    </div>
  );
}

AsiGauge.propTypes = {
  value: PropTypes.number.isRequired,
  label: PropTypes.string,
};

// ---------------------------------------------------------------------------
// Stat Card
// ---------------------------------------------------------------------------

function StatCard({ value, label, colorClass }) {
  return (
    <div className="flex flex-col items-center rounded-lg bg-white px-3 py-2 min-w-0 flex-1 shadow-sm">
      <span className={`text-lg font-bold ${colorClass || 'text-dark-gray'}`}>
        {value ?? '--'}
      </span>
      <span className="text-[11px] text-dark-gray text-center leading-tight mt-0.5">
        {label}
      </span>
    </div>
  );
}

StatCard.propTypes = {
  value: PropTypes.number,
  label: PropTypes.string.isRequired,
  colorClass: PropTypes.string,
};

// ---------------------------------------------------------------------------
// Claim Card
// ---------------------------------------------------------------------------

function ClaimCard({ claim, index, onClick, onFixClaim, isFixDisabled }) {
  const cfg = getVerdictConfig(claim.verdict);
  const VerdictIcon = cfg.Icon;

  return (
    <button
      type="button"
      onClick={() => onClick(index)}
      className={`group w-full text-left rounded-lg border-l-4 ${cfg.border} bg-white p-4 shadow-sm
        hover:shadow-md transition-shadow duration-150 cursor-pointer`}
    >
      {/* Top row: badge + severity */}
      <div className="flex items-center justify-between mb-2">
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cfg.badgeBg} ${cfg.badgeText}`}
        >
          <VerdictIcon className="h-3 w-3" />
          {cfg.label}
        </span>
        <SeverityDots severity={claim.severity} />
      </div>

      {/* Claim text */}
      <p className="text-sm font-medium text-dark-gray leading-snug">
        {claim.text}
      </p>

      {/* Evidence */}
      {claim.evidence && (
        <p className="mt-1.5 text-xs italic text-medium-gray leading-relaxed">
          {claim.evidence}
        </p>
      )}

      {/* Bottom row: category + actions */}
      <div className="mt-3 flex items-center justify-between">
        {claim.category ? (
          <span className="inline-block rounded-md bg-gray-100 px-2 py-0.5 text-[11px] text-medium-gray font-medium">
            {claim.category}
          </span>
        ) : (
          <span />
        )}
        <div className="flex items-center gap-3">
          {(claim.verdict === 'fabricated' || claim.verdict === 'unverifiable') && onFixClaim && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onFixClaim(claim);
              }}
              disabled={isFixDisabled}
              className={`flex items-center gap-1 text-xs font-medium
                ${claim.verdict === 'fabricated' ? 'text-red-600 hover:text-red-700' : 'text-amber-600 hover:text-amber-700'}
                disabled:opacity-50 disabled:cursor-not-allowed transition-colors`}
              title={claim.verdict === 'fabricated' ? 'Sugerir correção via Assistente' : 'Sugerir atribuição via Assistente'}
            >
              <Wand2 className="h-3 w-3" />
              Corrigir
            </button>
          )}
          <span className="flex items-center gap-0.5 text-xs text-tmc-orange opacity-0 group-hover:opacity-100 transition-opacity">
            Localizar
            <ChevronRight className="h-3 w-3" />
          </span>
        </div>
      </div>
    </button>
  );
}

ClaimCard.propTypes = {
  claim: PropTypes.shape({
    text: PropTypes.string,
    verdict: PropTypes.string,
    severity: PropTypes.string,
    category: PropTypes.string,
    evidence: PropTypes.string,
    position_hint: PropTypes.string,
    sources: PropTypes.array,
    external_fact_check: PropTypes.any,
  }).isRequired,
  index: PropTypes.number.isRequired,
  onClick: PropTypes.func.isRequired,
  onFixClaim: PropTypes.func,
  isFixDisabled: PropTypes.bool,
};

// ---------------------------------------------------------------------------
// FactCheckModal
// ---------------------------------------------------------------------------

export default function FactCheckModal({ isOpen, onClose, scanResult, onClaimClick, onDeepVerify, isDeepVerifying, onFixClaim, isFixDisabled, onRescan }) {
  // The modal animates via CSS — always show at full opacity/scale since
  // the modal mounts/unmounts with isOpen. CSS transition on initial render
  // is handled by the browser's layout-then-paint cycle.
  const animated = isOpen;

  // Escape key closes
  useEffect(() => {
    if (!isOpen) return;
    function handleKey(e) {
      if (e.key === 'Escape') onClose?.();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  if (!isOpen || !scanResult) return null;

  const {
    safety_index = 0,
    safety_label,
    claims = [],
    total_claims = 0,
    grounded_claims = 0,
    fabricated_claims = 0,
    unverifiable_claims = 0,
    scan_duration_ms,
    scan_id,
    cached: isCached,
    error: scanError,
  } = scanResult;

  // Determine header gradient based on safety — use darker shades for legibility
  let headerGradient = 'from-green-700 to-emerald-800';
  if (safety_index < 80) headerGradient = 'from-amber-700 to-orange-800';
  if (safety_index < 50) headerGradient = 'from-red-700 to-rose-800';

  // Pick the header shield icon
  let HeaderIcon = ShieldCheck;
  if (safety_index < 80) HeaderIcon = Shield;
  if (safety_index < 50) HeaderIcon = ShieldAlert;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className={`absolute inset-0 bg-black/50 transition-opacity duration-200
          ${animated ? 'opacity-100' : 'opacity-0'}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Content */}
      <div
        className={`relative flex flex-col bg-white rounded-2xl shadow-2xl
          max-w-2xl w-full mx-4 max-h-[85vh] overflow-hidden
          transition-all duration-300 ease-out
          ${animated ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Resultado do Fact-Check"
      >
        {/* ── HEADER ────────────────────────────────────────────── */}
        <div
          className={`relative bg-gradient-to-br ${headerGradient} px-6 pt-6 pb-5 text-white shrink-0`}
        >
          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            className="absolute top-3 right-3 rounded-full p-1.5 text-white/70 hover:text-white
              hover:bg-white/15 transition-colors"
            aria-label="Fechar"
          >
            <X className="h-5 w-5" />
          </button>

          {/* Title row */}
          <div className="flex items-center gap-2 mb-4">
            <HeaderIcon className="h-5 w-5 text-white/80" />
            <h2 className="text-base font-semibold tracking-tight">
              Fact-Check Scan
            </h2>
          </div>

          {/* Gauge centered */}
          <div className="flex justify-center">
            <AsiGauge value={safety_index} label={safety_label} />
          </div>

          {/* Stats row */}
          <div className="mt-4 flex gap-2">
            <StatCard
              value={total_claims}
              label="Total"
              colorClass="text-dark-gray"
            />
            <StatCard
              value={grounded_claims}
              label="Verificadas"
              colorClass="text-green-600"
            />
            <StatCard
              value={fabricated_claims}
              label="Fabricadas"
              colorClass="text-red-600"
            />
            <StatCard
              value={unverifiable_claims}
              label="Não verificáveis"
              colorClass="text-amber-600"
            />
          </div>

          {/* Cached indicator + re-scan */}
          {isCached && (
            <div className="mt-3 flex items-center justify-between text-xs text-white/70">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Resultado em cache
              </span>
              {onRescan && (
                <button
                  type="button"
                  onClick={onRescan}
                  className="flex items-center gap-1 text-white/80 hover:text-white transition-colors"
                >
                  <RefreshCw className="h-3 w-3" />
                  Nova verificação
                </button>
              )}
            </div>
          )}
        </div>

        {/* ── CLAIMS LIST ───────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-6 py-4 bg-off-white">
          <h3 className="text-sm font-semibold text-dark-gray mb-3 flex items-center gap-1.5">
            Análise por Verificação
            <span className="inline-flex items-center justify-center rounded-full bg-gray-200 px-2 py-0.5 text-[11px] font-medium text-medium-gray">
              {claims.length}
            </span>
          </h3>

          {/* Deep Verify button — only when there are unverifiable claims */}
          {unverifiable_claims > 0 && !scanError && (
            <button
              type="button"
              onClick={onDeepVerify}
              disabled={isDeepVerifying}
              className="mb-3 w-full flex items-center justify-center gap-2 rounded-lg border border-tmc-orange
                px-4 py-2 text-sm font-medium text-tmc-orange
                hover:bg-tmc-orange/10 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isDeepVerifying ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Verificando {unverifiable_claims} claims...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Verificação Profunda ({unverifiable_claims} não verificáveis)
                </>
              )}
            </button>
          )}

          {/* Deep verify success badge */}
          {scanResult?._deep_verify && (
            <div className="mb-3 flex items-center gap-2 rounded-lg bg-green-50 border border-green-200 px-3 py-2 text-xs text-green-700">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {scanResult._deep_verify.claims_resolved} claim(s) resolvidas via verificação profunda
              <span className="text-green-500 ml-auto">
                {scanResult._deep_verify.sources_searched} fontes pesquisadas
              </span>
            </div>
          )}

          {scanError ? (
            <div className="flex flex-col items-center gap-2 py-8">
              <AlertTriangle className="h-6 w-6 text-red-500" />
              <p className="text-sm font-medium text-red-600 text-center">
                Erro na verificação
              </p>
              <p className="text-xs text-medium-gray text-center max-w-md">
                {scanError}
              </p>
            </div>
          ) : claims.length === 0 ? (
            <p className="text-sm text-medium-gray text-center py-8">
              Nenhuma afirmação encontrada para analisar.
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {claims.map((claim, idx) => (
                <ClaimCard
                  key={idx}
                  claim={claim}
                  index={idx}
                  onClick={onClaimClick}
                  onFixClaim={onFixClaim}
                  isFixDisabled={isFixDisabled}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── FOOTER ────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-light-gray bg-white shrink-0">
          <div className="flex items-center gap-3 text-xs text-medium-gray min-w-0">
            {scan_id && (
              <span className="truncate max-w-[180px]" title={scan_id}>
                {scan_id}
              </span>
            )}
            {scan_duration_ms != null && (
              <span className="flex items-center gap-1 whitespace-nowrap">
                <Clock className="h-3 w-3" />
                {formatDuration(scan_duration_ms)}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-light-gray px-4 py-1.5 text-sm font-medium text-dark-gray
              hover:bg-gray-50 transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

FactCheckModal.propTypes = {
  isOpen: PropTypes.bool,
  onClose: PropTypes.func,
  scanResult: PropTypes.shape({
    safety_index: PropTypes.number,
    safety_label: PropTypes.string,
    claims: PropTypes.arrayOf(
      PropTypes.shape({
        text: PropTypes.string,
        verdict: PropTypes.string,
        severity: PropTypes.string,
        category: PropTypes.string,
        evidence: PropTypes.string,
        position_hint: PropTypes.string,
        sources: PropTypes.array,
        external_fact_check: PropTypes.any,
      }),
    ),
    total_claims: PropTypes.number,
    grounded_claims: PropTypes.number,
    fabricated_claims: PropTypes.number,
    unverifiable_claims: PropTypes.number,
    corroboration_score: PropTypes.number,
    fact_check_matches: PropTypes.number,
    source_credibility: PropTypes.shape({
      sources_found: PropTypes.number,
      avg_credibility: PropTypes.number,
      tier_breakdown: PropTypes.any,
    }),
    scan_duration_ms: PropTypes.number,
    scan_id: PropTypes.string,
    scanned_at: PropTypes.string,
    cached: PropTypes.bool,
    error: PropTypes.string,
  }),
  onClaimClick: PropTypes.func,
  onDeepVerify: PropTypes.func,
  isDeepVerifying: PropTypes.bool,
  onFixClaim: PropTypes.func,
  isFixDisabled: PropTypes.bool,
  onRescan: PropTypes.func,
};
