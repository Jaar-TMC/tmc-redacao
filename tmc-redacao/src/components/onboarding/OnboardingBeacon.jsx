import { memo } from 'react';
import PropTypes from 'prop-types';

/**
 * OnboardingBeacon - Pulsing orange circle to draw attention to elements
 *
 * Positioned absolutely within a relative container.
 * Respects prefers-reduced-motion by disabling animation.
 *
 * WCAG 2.1 Compliance:
 * - Respects prefers-reduced-motion
 * - Non-flashing (smooth pulse, not rapid blink)
 * - Decorative only (aria-hidden)
 */
const OnboardingBeacon = memo(function OnboardingBeacon({
  position = 'top-right',
  size = 20,
  className = ''
}) {
  // Position classes based on beacon position
  const positionClasses = {
    'top-right': '-top-2 -right-2',
    'top-left': '-top-2 -left-2',
    'bottom-right': '-bottom-2 -right-2',
    'bottom-left': '-bottom-2 -left-2',
    'center': 'top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2'
  };

  const positionClass = positionClasses[position] || positionClasses['top-right'];

  return (
    <span
      className={`
        absolute z-[9997] pointer-events-none
        ${positionClass}
        ${className}
      `}
      aria-hidden="true"
    >
      {/* Outer pulsing ring */}
      <span
        className="absolute inset-0 rounded-full bg-tmc-orange animate-beacon-pulse"
        style={{ width: size, height: size }}
      />
      {/* Inner solid circle */}
      <span
        className="relative block rounded-full bg-tmc-orange"
        style={{ width: size, height: size }}
      />
    </span>
  );
});

OnboardingBeacon.propTypes = {
  /** Position of beacon relative to parent */
  position: PropTypes.oneOf(['top-right', 'top-left', 'bottom-right', 'bottom-left', 'center']),
  /** Size of the beacon in pixels */
  size: PropTypes.number,
  /** Additional CSS classes */
  className: PropTypes.string
};

export default OnboardingBeacon;
