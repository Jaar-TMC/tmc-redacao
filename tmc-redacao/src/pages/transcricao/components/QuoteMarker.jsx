import { useCallback } from 'react';
import PropTypes from 'prop-types';
import { Quote } from 'lucide-react';

/**
 * QuoteMarker - Botão/toggle para marcar seleção como citação direta
 * @param {Object} props
 * @param {boolean} props.isQuote - Se está marcado como citação
 * @param {Function} props.onToggle - Callback ao alternar estado
 * @param {string} [props.size] - Tamanho do botão ('sm' | 'md')
 * @param {boolean} [props.disabled] - Se está desabilitado
 */
function QuoteMarker({ isQuote, onToggle, size = 'md', disabled = false }) {
  const handleClick = useCallback((e) => {
    e.stopPropagation();
    if (!disabled) {
      onToggle();
    }
  }, [onToggle, disabled]);

  const handleKeyDown = useCallback((e) => {
    if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
      e.preventDefault();
      e.stopPropagation();
      onToggle();
    }
  }, [onToggle, disabled]);

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs gap-1',
    md: 'px-3 py-1.5 text-sm gap-1.5'
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4'
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      disabled={disabled}
      aria-pressed={isQuote}
      aria-label={isQuote ? 'Remover marcação de citação' : 'Marcar como citação direta'}
      className={`
        inline-flex items-center font-medium rounded-lg
        transition-all duration-200
        ${sizeClasses[size]}
        ${isQuote
          ? 'bg-blue-500 text-white hover:bg-blue-600 shadow-sm'
          : 'bg-white text-medium-gray border border-light-gray hover:border-blue-300 hover:text-blue-600 hover:bg-blue-50'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
      `}
    >
      <Quote className={iconSizes[size]} aria-hidden="true" />
      <span>{isQuote ? 'Citação' : 'Marcar citação'}</span>
    </button>
  );
}

QuoteMarker.propTypes = {
  isQuote: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  size: PropTypes.oneOf(['sm', 'md']),
  disabled: PropTypes.bool
};

export default QuoteMarker;
