import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';

/**
 * ScoreTooltip Component
 *
 * Rich tooltip for article score breakdown, consistent with the app's
 * dark tooltip pattern (bg-dark-gray). Shows visual progress bars for
 * each score dimension.
 */

const DIMENSIONS = [
  { key: 'scoreInesperado', label: 'Inesperado', max: 25, icon: 'bolt' },
  { key: 'scoreImpacto', label: 'Impacto', max: 30, icon: 'target' },
  { key: 'scoreBuscaAgora', label: 'Busca Agora', max: 25, icon: 'search' },
  { key: 'scoreConversa', label: 'Conversa', max: 20, icon: 'chat' },
];

const ICONS = {
  bolt: (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
      <path d="M8.5 1.5L3 9h4.5l-1 5.5L13 7H8.5l1-5.5z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  target: (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3"/>
      <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3"/>
      <circle cx="8" cy="8" r="0.8" fill="currentColor"/>
    </svg>
  ),
  search: (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
      <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    </svg>
  ),
  chat: (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
      <path d="M2 3.5C2 2.67 2.67 2 3.5 2h9c.83 0 1.5.67 1.5 1.5v6c0 .83-.67 1.5-1.5 1.5H6L3 14v-3h-.5C1.67 11 1 10.33 1 9.5v-6z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" transform="translate(0.5, 0)"/>
    </svg>
  ),
};

function getBarColor(value, max) {
  const pct = (value / max) * 100;
  if (pct >= 70) return '#34D399'; // emerald-400
  if (pct >= 40) return '#FBBF24'; // amber-400
  return '#F87171'; // red-400
}

function getClassificationStyle(classification) {
  switch (classification) {
    case 'A': return { bg: 'rgba(16, 185, 129, 0.15)', text: '#34D399', border: 'rgba(16, 185, 129, 0.3)' };
    case 'B': return { bg: 'rgba(245, 158, 11, 0.15)', text: '#FBBF24', border: 'rgba(245, 158, 11, 0.3)' };
    default:  return { bg: 'rgba(239, 68, 68, 0.15)', text: '#F87171', border: 'rgba(239, 68, 68, 0.3)' };
  }
}

const ScoreTooltip = ({ article, children }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const timeoutRef = useRef(null);
  const triggerRef = useRef(null);
  const tooltipRef = useRef(null);

  const updatePosition = useCallback(() => {
    if (!triggerRef.current || !tooltipRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const padding = 8;

    let top = triggerRect.bottom + padding;
    let left = triggerRect.right - tooltipRect.width;

    // Clamp to viewport
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    if (left < padding) left = padding;
    if (left + tooltipRect.width > vw - padding) left = vw - tooltipRect.width - padding;

    // If no room below, show above
    if (top + tooltipRect.height > vh - padding) {
      top = triggerRect.top - tooltipRect.height - padding;
    }
    if (top < padding) top = padding;

    setCoords({ top, left });
  }, []);

  useEffect(() => {
    if (isVisible) {
      // RAF to ensure tooltip is rendered before measuring
      requestAnimationFrame(updatePosition);
    }
  }, [isVisible, updatePosition]);

  const handleMouseEnter = useCallback(() => {
    timeoutRef.current = setTimeout(() => setIsVisible(true), 300);
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  }, []);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const classStyle = getClassificationStyle(article.scoreClassification);

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className="inline-flex"
      >
        {children}
      </div>

      {isVisible && createPortal(
        <div
          ref={tooltipRef}
          role="tooltip"
          className="fixed z-[9999] pointer-events-none"
          style={{ top: `${coords.top}px`, left: `${coords.left}px` }}
        >
          <div className="bg-dark-gray rounded-lg shadow-xl overflow-hidden" style={{ width: '220px' }}>
            {/* Header */}
            <div className="px-3 pt-3 pb-2 flex items-center justify-between">
              <span className="text-white/60 text-[10px] font-semibold uppercase tracking-wider">
                Score
              </span>
              <div className="flex items-center gap-2">
                <span className="text-white text-lg font-bold leading-none">
                  {article.score}
                </span>
                <span
                  className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: classStyle.bg,
                    color: classStyle.text,
                    border: `1px solid ${classStyle.border}`,
                  }}
                >
                  {article.scoreClassification}
                </span>
              </div>
            </div>

            {/* Divider */}
            <div className="mx-3 border-t border-white/10" />

            {/* Score Dimensions */}
            <div className="px-3 py-2.5 flex flex-col gap-2">
              {DIMENSIONS.map(({ key, label, max, icon }) => {
                const value = article[key];
                const hasValue = value != null;
                const pct = hasValue ? Math.round((value / max) * 100) : 0;
                const barColor = hasValue ? getBarColor(value, max) : '#555';

                return (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-white/40" style={{ lineHeight: 0 }}>
                          {ICONS[icon]}
                        </span>
                        <span className="text-white/70 text-[11px]">
                          {label}
                        </span>
                      </div>
                      <span className="text-white text-[11px] font-semibold tabular-nums">
                        {hasValue ? value : '-'}
                        <span className="text-white/30 font-normal">/{max}</span>
                      </span>
                    </div>
                    {/* Progress bar */}
                    <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: barColor,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div className="px-3 pb-2.5 pt-0.5">
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${article.score}%`,
                    background: `linear-gradient(90deg, ${classStyle.text}, ${classStyle.text}dd)`,
                  }}
                />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-white/30 text-[9px]">0</span>
                <span className="text-white/30 text-[9px]">100</span>
              </div>
            </div>
          </div>

          {/* Arrow */}
          <div
            className="absolute w-0 h-0 border-4 border-l-transparent border-r-transparent border-t-transparent border-b-dark-gray"
            style={{ top: '-7px', right: '12px' }}
          />
        </div>,
        document.body
      )}
    </>
  );
};

ScoreTooltip.propTypes = {
  article: PropTypes.shape({
    score: PropTypes.number,
    scoreClassification: PropTypes.string,
    scoreInesperado: PropTypes.number,
    scoreImpacto: PropTypes.number,
    scoreBuscaAgora: PropTypes.number,
    scoreConversa: PropTypes.number,
  }).isRequired,
  children: PropTypes.node.isRequired,
};

export default ScoreTooltip;
