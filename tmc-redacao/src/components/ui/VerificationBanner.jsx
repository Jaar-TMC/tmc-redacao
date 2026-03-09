import { useMemo } from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import PropTypes from 'prop-types';

/**
 * VerificationBanner - Shows article verification status from the anti-hallucination pipeline.
 *
 * Colors:
 * - Green: Verified (confidence >= 0.7, risk low/medium)
 * - Yellow: Partial verification (confidence 0.4-0.7)
 * - Red: High risk (confidence < 0.4 or risk critical/high)
 *
 * Props:
 * - verification: Verification data object from API response
 * - publishBlocked: Whether publishing is blocked
 * - blockReason: Reason for blocking
 */
const VerificationBanner = ({ verification, publishBlocked, blockReason, humanReviewRequired, reviewReasons }) => {
  const [expanded, setExpanded] = useState(false);

  const status = useMemo(() => {
    if (!verification || !verification.is_verified) {
      return null; // No verification data - don't show banner
    }

    const { confidence_score, risk_level, total_claims: _total_claims, grounded_claims: _grounded_claims, fabricated_claims: _fabricated_claims, unverifiable_claims: _unverifiable_claims } = verification;

    if (publishBlocked || risk_level === 'critical' || confidence_score < 0.4) {
      return {
        level: 'danger',
        icon: ShieldAlert,
        title: 'Risco alto - revise antes de publicar',
        bgClass: 'bg-red-50 border-red-200',
        textClass: 'text-red-800',
        subtextClass: 'text-red-600',
        iconClass: 'text-red-500',
        badgeClass: 'bg-red-100 text-red-700',
      };
    }

    if (risk_level === 'high') {
      return {
        level: 'warning',
        icon: AlertTriangle,
        title: 'Risco alto - revisão recomendada',
        bgClass: 'bg-amber-50 border-amber-200',
        textClass: 'text-amber-800',
        subtextClass: 'text-amber-600',
        iconClass: 'text-amber-500',
        badgeClass: 'bg-amber-100 text-amber-700',
      };
    }

    if (confidence_score >= 0.7 && (risk_level === 'low' || risk_level === 'medium')) {
      return {
        level: 'safe',
        icon: ShieldCheck,
        title: 'Verificado',
        bgClass: 'bg-green-50 border-green-200',
        textClass: 'text-green-800',
        subtextClass: 'text-green-600',
        iconClass: 'text-green-500',
        badgeClass: 'bg-green-100 text-green-700',
      };
    }

    return {
      level: 'warning',
      icon: AlertTriangle,
      title: 'Verificação parcial',
      bgClass: 'bg-amber-50 border-amber-200',
      textClass: 'text-amber-800',
      subtextClass: 'text-amber-600',
      iconClass: 'text-amber-500',
      badgeClass: 'bg-amber-100 text-amber-700',
    };
  }, [verification, publishBlocked]);

  if (!status) return null;

  const { confidence_score = 0, total_claims = 0, grounded_claims = 0, fabricated_claims = 0, unverifiable_claims = 0 } = verification;
  const Icon = status.icon;

  return (
    <div className={`border rounded-lg ${status.bgClass} mb-4`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2.5"
      >
        <div className="flex items-center gap-2.5">
          <Icon size={18} className={status.iconClass} />
          <span className={`text-sm font-semibold ${status.textClass}`}>
            {status.title}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${status.badgeClass}`}>
            {Math.round(confidence_score * 100)}% confiança
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            {grounded_claims > 0 && (
              <span className="text-green-600">{grounded_claims} verificadas</span>
            )}
            {unverifiable_claims > 0 && (
              <span className="text-amber-600">{unverifiable_claims} incertas</span>
            )}
            {fabricated_claims > 0 && (
              <span className="text-red-600 font-semibold">{fabricated_claims} fabricadas</span>
            )}
          </div>
          {expanded ? (
            <ChevronUp size={16} className={status.subtextClass} />
          ) : (
            <ChevronDown size={16} className={status.subtextClass} />
          )}
        </div>
      </button>

      {expanded && (
        <div className={`border-t px-4 py-3 space-y-2 ${status.bgClass}`}>
          {/* Claims summary */}
          {total_claims > 0 && (
            <div className="text-xs space-y-1">
              <p className={`font-medium ${status.textClass}`}>
                {total_claims} afirmações analisadas:
              </p>
              <div className="flex gap-4">
                <span className="text-green-700">{grounded_claims} fundamentadas</span>
                <span className="text-amber-700">{unverifiable_claims} inverificáveis</span>
                <span className="text-red-700">{fabricated_claims} fabricadas</span>
              </div>
            </div>
          )}

          {/* Risk level and expansion ratio */}
          <div className="flex gap-4 text-xs">
            <span className={status.subtextClass}>
              Risco: <strong>{verification.risk_level}</strong>
            </span>
            {verification.expansion_ratio > 0 && (
              <span className={status.subtextClass}>
                Expansão: <strong>{verification.expansion_ratio?.toFixed(1)}x</strong>
              </span>
            )}
            {verification.source_sufficiency && (
              <span className={status.subtextClass}>
                Material: <strong>{verification.source_sufficiency}</strong>
              </span>
            )}
          </div>

          {/* Warnings */}
          {verification.warnings && verification.warnings.length > 0 && (
            <div className="text-xs space-y-1">
              <p className={`font-medium ${status.textClass}`}>Avisos:</p>
              {verification.warnings.map((warning, i) => (
                <p key={i} className={status.subtextClass}>- {warning}</p>
              ))}
            </div>
          )}

          {/* Block reason */}
          {publishBlocked && blockReason && (
            <div className="bg-red-100 rounded px-3 py-2 text-xs text-red-800 font-medium">
              Publicação bloqueada: {blockReason}
            </div>
          )}

          {/* Human review warning */}
          {humanReviewRequired && !publishBlocked && reviewReasons?.length > 0 && (
            <div className="bg-amber-100 rounded px-3 py-2 text-xs text-amber-800">
              <p className="font-medium mb-1">Revisão humana recomendada:</p>
              {reviewReasons.map((reason, i) => (
                <p key={i} className="text-amber-700">- {reason}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

VerificationBanner.propTypes = {
  verification: PropTypes.object,
  publishBlocked: PropTypes.bool,
  blockReason: PropTypes.string,
  humanReviewRequired: PropTypes.bool,
  reviewReasons: PropTypes.arrayOf(PropTypes.string),
};

export default VerificationBanner;
