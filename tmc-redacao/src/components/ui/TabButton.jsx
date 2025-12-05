import PropTypes from 'prop-types';

/**
 * Reusable tab button component for consistent tab navigation
 * @param {Object} props
 * @param {boolean} props.active - Whether this tab is currently active
 * @param {Function} props.onClick - Click handler
 * @param {React.ReactNode} props.children - Tab label content
 * @param {string} props.ariaLabel - Accessible label for screen readers
 */
const TabButton = ({ active, onClick, children, ariaLabel }) => (
  <button
    type="button"
    onClick={onClick}
    className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      active ? 'bg-tmc-orange text-white' : 'text-medium-gray hover:text-dark-gray'
    }`}
    role="tab"
    aria-selected={active}
    aria-label={ariaLabel || undefined}
  >
    {children}
  </button>
);

TabButton.propTypes = {
  active: PropTypes.bool.isRequired,
  onClick: PropTypes.func.isRequired,
  children: PropTypes.node.isRequired,
  ariaLabel: PropTypes.string
};

export default TabButton;
