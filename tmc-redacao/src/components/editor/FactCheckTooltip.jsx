import { useEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';

const VERDICT_LABELS = {
  fabricated: 'Fabricada',
  unverifiable: 'Não verificável',
  opinion: 'Opinião',
};

const VERDICT_CLASS = {
  fabricated: 'fc-tooltip__verdict--fabricated',
  unverifiable: 'fc-tooltip__verdict--unverifiable',
  opinion: 'fc-tooltip__verdict--opinion',
};

/**
 * FactCheckTooltip — listens for mouse hover on `.fc-highlight` decorations
 * inside the TipTap editor and shows a floating tooltip with claim details.
 *
 * Renders a portal to document.body to avoid z-index/overflow issues.
 */
const FactCheckTooltip = ({ claims, containerRef }) => {
  const tooltipRef = useRef(null);
  const [tooltip, setTooltip] = useState(null); // { x, y, claim, verdict }
  const hideTimeoutRef = useRef(null);

  const showTooltip = useCallback((e) => {
    const el = e.target.closest('.fc-highlight');
    if (!el) return;

    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }

    const claimIndex = parseInt(el.dataset.claimIndex, 10);
    const verdict = el.dataset.verdict;
    const claim = claims?.[claimIndex];
    if (!claim) return;

    const rect = el.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top - 8;

    setTooltip({ x, y, claim, verdict });
  }, [claims]);

  const hideTooltip = useCallback(() => {
    hideTimeoutRef.current = setTimeout(() => {
      setTooltip(null);
    }, 100);
  }, []);

  useEffect(() => {
    const container = containerRef?.current;
    if (!container) return;

    container.addEventListener('mouseover', showTooltip);
    container.addEventListener('mouseout', hideTooltip);

    return () => {
      container.removeEventListener('mouseover', showTooltip);
      container.removeEventListener('mouseout', hideTooltip);
      if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current);
    };
  }, [containerRef, showTooltip, hideTooltip]);

  if (!tooltip) return null;

  // Calculate position — above the highlight, centered horizontally
  const tooltipStyle = {
    left: `${tooltip.x}px`,
    top: `${tooltip.y}px`,
    transform: 'translate(-50%, -100%)',
  };

  return createPortal(
    <div
      ref={tooltipRef}
      className={`fc-tooltip fc-tooltip--visible`}
      style={tooltipStyle}
    >
      <span className={`fc-tooltip__verdict ${VERDICT_CLASS[tooltip.verdict] || ''}`}>
        {VERDICT_LABELS[tooltip.verdict] || tooltip.verdict}
      </span>
      <div className="mt-1">{tooltip.claim.text}</div>
      {tooltip.claim.evidence && (
        <div className="fc-tooltip__evidence">
          {tooltip.claim.evidence.length > 150
            ? tooltip.claim.evidence.slice(0, 150) + '…'
            : tooltip.claim.evidence}
        </div>
      )}
    </div>,
    document.body
  );
};

FactCheckTooltip.propTypes = {
  claims: PropTypes.array,
  containerRef: PropTypes.object,
};

export default FactCheckTooltip;
