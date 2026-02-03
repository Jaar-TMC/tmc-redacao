import { memo, useEffect, useState, useRef, useCallback } from 'react';
import PropTypes from 'prop-types';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';

/**
 * OnboardingStep - Tooltip positioned near the target element
 *
 * Features:
 * - Smart positioning (auto-adjusts to stay in viewport)
 * - Arrow pointing to target element
 * - Navigation buttons (Prev/Next/Skip)
 * - Progress indicator
 * - Focus trap for accessibility
 *
 * WCAG 2.1 Compliance:
 * - role="dialog" and aria-modal="true"
 * - aria-labelledby for title
 * - Focus trap inside tooltip
 * - Escape key closes tour
 * - Keyboard navigation (Tab, Shift+Tab)
 */
const OnboardingStep = memo(function OnboardingStep({
  step,
  stepIndex,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
  targetSelector
}) {
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [actualPosition, setActualPosition] = useState(step?.position || 'bottom');
  const [arrowPosition, setArrowPosition] = useState({ left: '50%' });
  const tooltipRef = useRef(null);
  const titleId = `onboarding-step-title-${stepIndex}`;

  // Calculate tooltip position
  const calculatePosition = useCallback(() => {
    if (!targetSelector || !tooltipRef.current) return;

    const target = document.querySelector(targetSelector);
    if (!target) return;

    const targetRect = target.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const padding = 16;
    const arrowSize = 12;

    let preferredPosition = step?.position || 'bottom';
    let top, left;
    let finalPosition = preferredPosition;

    // Calculate position based on preference
    const positions = {
      bottom: () => ({
        top: targetRect.bottom + arrowSize + padding,
        left: targetRect.left + targetRect.width / 2 - tooltipRect.width / 2
      }),
      top: () => ({
        top: targetRect.top - tooltipRect.height - arrowSize - padding,
        left: targetRect.left + targetRect.width / 2 - tooltipRect.width / 2
      }),
      left: () => ({
        top: targetRect.top + targetRect.height / 2 - tooltipRect.height / 2,
        left: targetRect.left - tooltipRect.width - arrowSize - padding
      }),
      right: () => ({
        top: targetRect.top + targetRect.height / 2 - tooltipRect.height / 2,
        left: targetRect.right + arrowSize + padding
      })
    };

    // Try preferred position first
    const pos = positions[preferredPosition]?.() || positions.bottom();
    top = pos.top;
    left = pos.left;

    // Adjust if out of viewport
    if (preferredPosition === 'bottom' && top + tooltipRect.height > viewportHeight - padding) {
      // Try top instead
      const topPos = positions.top();
      if (topPos.top > padding) {
        top = topPos.top;
        left = topPos.left;
        finalPosition = 'top';
      }
    } else if (preferredPosition === 'top' && top < padding) {
      // Try bottom instead
      const bottomPos = positions.bottom();
      if (bottomPos.top + tooltipRect.height < viewportHeight - padding) {
        top = bottomPos.top;
        left = bottomPos.left;
        finalPosition = 'bottom';
      }
    } else if (preferredPosition === 'left' && left < padding) {
      // Try right instead
      const rightPos = positions.right();
      if (rightPos.left + tooltipRect.width < viewportWidth - padding) {
        top = rightPos.top;
        left = rightPos.left;
        finalPosition = 'right';
      }
    } else if (preferredPosition === 'right' && left + tooltipRect.width > viewportWidth - padding) {
      // Try left instead
      const leftPos = positions.left();
      if (leftPos.left > padding) {
        top = leftPos.top;
        left = leftPos.left;
        finalPosition = 'left';
      }
    }

    // Horizontal bounds check
    if (left < padding) left = padding;
    if (left + tooltipRect.width > viewportWidth - padding) {
      left = viewportWidth - tooltipRect.width - padding;
    }

    // Vertical bounds check
    if (top < padding) top = padding;
    if (top + tooltipRect.height > viewportHeight - padding) {
      top = viewportHeight - tooltipRect.height - padding;
    }

    // Calculate arrow position (centered on target)
    const targetCenter = targetRect.left + targetRect.width / 2;
    let arrowLeft;

    if (finalPosition === 'top' || finalPosition === 'bottom') {
      arrowLeft = targetCenter - left;
      // Keep arrow within tooltip bounds
      arrowLeft = Math.max(20, Math.min(arrowLeft, tooltipRect.width - 20));
    }

    setPosition({ top, left });
    setActualPosition(finalPosition);
    setArrowPosition({ left: arrowLeft ? `${arrowLeft}px` : '50%' });
  }, [targetSelector, step?.position]);

  // Update position on mount and when target changes
  useEffect(() => {
    // Small delay to ensure DOM is ready
    const timeoutId = setTimeout(calculatePosition, 50);

    window.addEventListener('scroll', calculatePosition, true);
    window.addEventListener('resize', calculatePosition);

    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener('scroll', calculatePosition, true);
      window.removeEventListener('resize', calculatePosition);
    };
  }, [calculatePosition]);

  // Focus trap and keyboard handling
  useEffect(() => {
    const tooltip = tooltipRef.current;
    if (!tooltip) return;

    // Focus the tooltip
    tooltip.focus();

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onSkip();
      } else if (e.key === 'Tab') {
        const focusableElements = tooltip.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        if (e.target.tagName !== 'BUTTON') {
          e.preventDefault();
          onNext();
        }
      } else if (e.key === 'ArrowLeft') {
        if (e.target.tagName !== 'BUTTON' && stepIndex > 0) {
          e.preventDefault();
          onPrev();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onSkip, onNext, onPrev, stepIndex]);

  // Scroll target into view
  useEffect(() => {
    if (!targetSelector) return;

    const target = document.querySelector(targetSelector);
    if (target) {
      target.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
        inline: 'center'
      });
    }
  }, [targetSelector]);

  if (!step) return null;

  const isFirstStep = stepIndex === 0;
  const isLastStep = stepIndex === totalSteps - 1;

  // Arrow classes based on position
  const arrowClasses = {
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-white border-t-transparent border-x-transparent',
    top: 'top-full left-1/2 -translate-x-1/2 border-t-white border-b-transparent border-x-transparent',
    left: 'left-full top-1/2 -translate-y-1/2 border-l-white border-r-transparent border-y-transparent',
    right: 'right-full top-1/2 -translate-y-1/2 border-r-white border-l-transparent border-y-transparent'
  };

  return (
    <div
      ref={tooltipRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      tabIndex={-1}
      className="fixed z-[9999] w-80 max-w-[calc(100vw-32px)] bg-white rounded-xl shadow-2xl outline-none"
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`
      }}
    >
      {/* Arrow */}
      <span
        className={`absolute w-0 h-0 border-[12px] ${arrowClasses[actualPosition]}`}
        style={
          (actualPosition === 'top' || actualPosition === 'bottom')
            ? { left: arrowPosition.left, transform: 'translateX(-50%)' }
            : {}
        }
        aria-hidden="true"
      />

      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <h3
          id={titleId}
          className="font-bold text-dark-gray text-base"
        >
          {step.title}
        </h3>
        <button
          type="button"
          onClick={onSkip}
          className="p-1 rounded-lg text-medium-gray hover:text-dark-gray hover:bg-gray-100 transition-colors"
          aria-label="Fechar tour"
        >
          <X size={18} aria-hidden="true" />
        </button>
      </div>

      {/* Content */}
      <div className="px-4 pb-3">
        <p className="text-sm text-medium-gray leading-relaxed">
          {step.content}
        </p>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-b-xl border-t border-gray-100">
        {/* Progress */}
        <div className="flex items-center gap-1.5">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <span
              key={i}
              className={`w-2 h-2 rounded-full transition-colors ${
                i === stepIndex ? 'bg-tmc-orange' : 'bg-gray-300'
              }`}
              aria-hidden="true"
            />
          ))}
          <span className="sr-only">
            Passo {stepIndex + 1} de {totalSteps}
          </span>
        </div>

        {/* Navigation */}
        <div className="flex items-center gap-2">
          {!isFirstStep && (
            <button
              type="button"
              onClick={onPrev}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-medium-gray hover:text-dark-gray transition-colors rounded-lg hover:bg-gray-200"
              aria-label="Passo anterior"
            >
              <ChevronLeft size={16} aria-hidden="true" />
              <span className="hidden sm:inline">Anterior</span>
            </button>
          )}
          <button
            type="button"
            onClick={onNext}
            className="flex items-center gap-1 px-4 py-1.5 text-sm font-semibold text-white bg-tmc-orange hover:bg-tmc-orange/90 transition-colors rounded-lg"
            aria-label={isLastStep ? 'Concluir tour' : 'Próximo passo'}
          >
            <span>{isLastStep ? 'Concluir' : 'Próximo'}</span>
            {!isLastStep && <ChevronRight size={16} aria-hidden="true" />}
          </button>
        </div>
      </div>
    </div>
  );
});

OnboardingStep.propTypes = {
  /** Current step object */
  step: PropTypes.shape({
    target: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    content: PropTypes.string.isRequired,
    position: PropTypes.oneOf(['auto', 'top', 'bottom', 'left', 'right']),
    beaconPosition: PropTypes.string
  }),
  /** Current step index (0-based) */
  stepIndex: PropTypes.number.isRequired,
  /** Total number of steps */
  totalSteps: PropTypes.number.isRequired,
  /** Callback for next step */
  onNext: PropTypes.func.isRequired,
  /** Callback for previous step */
  onPrev: PropTypes.func.isRequired,
  /** Callback for skipping tour */
  onSkip: PropTypes.func.isRequired,
  /** CSS selector for target element */
  targetSelector: PropTypes.string
};

export default OnboardingStep;
