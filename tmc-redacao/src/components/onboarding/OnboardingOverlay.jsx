import { memo, useEffect, useState } from 'react';
import PropTypes from 'prop-types';

/**
 * OnboardingOverlay - Dark backdrop with spotlight cutout on target element
 *
 * Uses SVG mask to create a "hole" that reveals the highlighted element.
 * Automatically tracks element position on scroll/resize.
 *
 * WCAG 2.1 Compliance:
 * - High contrast overlay (75% opacity black)
 * - Click outside closes tour (accessible dismissal)
 */
const OnboardingOverlay = memo(function OnboardingOverlay({
  targetSelector,
  padding = 8,
  borderRadius = 8,
  onClickOutside
}) {
  const [targetRect, setTargetRect] = useState(null);

  // Track target element position
  useEffect(() => {
    if (!targetSelector) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTargetRect(null);
      return;
    }

    const updateRect = () => {
      const element = document.querySelector(targetSelector);
      if (element) {
        const rect = element.getBoundingClientRect();
        setTargetRect({
          x: rect.x - padding,
          y: rect.y - padding,
          width: rect.width + padding * 2,
          height: rect.height + padding * 2
        });
      } else {
        setTargetRect(null);
      }
    };

    // Initial update
    updateRect();

    // Update on scroll and resize
    window.addEventListener('scroll', updateRect, true);
    window.addEventListener('resize', updateRect);

    // Use ResizeObserver for element size changes
    const element = document.querySelector(targetSelector);
    let resizeObserver;
    if (element && window.ResizeObserver) {
      resizeObserver = new ResizeObserver(updateRect);
      resizeObserver.observe(element);
    }

    return () => {
      window.removeEventListener('scroll', updateRect, true);
      window.removeEventListener('resize', updateRect);
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
    };
  }, [targetSelector, padding]);

  // Handle click on overlay (outside spotlight)
  const handleOverlayClick = (e) => {
    // Only trigger if clicking directly on the overlay, not the spotlight area
    if (e.target === e.currentTarget && onClickOutside) {
      onClickOutside();
    }
  };

  // Don't render if no target
  if (!targetRect) {
    return null;
  }

  const maskId = 'onboarding-spotlight-mask';

  return (
    <svg
      className="fixed inset-0 z-[9998] pointer-events-auto"
      style={{ width: '100vw', height: '100vh' }}
      onClick={handleOverlayClick}
      aria-hidden="true"
    >
      <defs>
        <mask id={maskId}>
          {/* White background = visible overlay */}
          <rect fill="white" width="100%" height="100%" />
          {/* Black rectangle = transparent cutout (spotlight) */}
          <rect
            fill="black"
            x={targetRect.x}
            y={targetRect.y}
            width={targetRect.width}
            height={targetRect.height}
            rx={borderRadius}
            ry={borderRadius}
          />
        </mask>
      </defs>

      {/* Dark overlay with spotlight cutout */}
      <rect
        fill="rgba(0, 0, 0, 0.75)"
        mask={`url(#${maskId})`}
        width="100%"
        height="100%"
        style={{ pointerEvents: 'auto' }}
      />

      {/* Highlight border around spotlight */}
      <rect
        fill="none"
        stroke="var(--color-tmc-orange)"
        strokeWidth="2"
        x={targetRect.x}
        y={targetRect.y}
        width={targetRect.width}
        height={targetRect.height}
        rx={borderRadius}
        ry={borderRadius}
        style={{ pointerEvents: 'none' }}
      />
    </svg>
  );
});

OnboardingOverlay.propTypes = {
  /** CSS selector for the target element to highlight */
  targetSelector: PropTypes.string.isRequired,
  /** Padding around the spotlight in pixels */
  padding: PropTypes.number,
  /** Border radius of the spotlight in pixels */
  borderRadius: PropTypes.number,
  /** Callback when clicking outside the spotlight */
  onClickOutside: PropTypes.func
};

export default OnboardingOverlay;
