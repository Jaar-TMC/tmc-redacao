import { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';

/**
 * Tooltip Component
 *
 * Componente de tooltip simples para exibir dicas ao passar o mouse sobre elementos.
 * Ideal para botões de toolbar e ícones de ação.
 *
 * @example
 * <Tooltip content="Negrito (Ctrl+B)">
 *   <button><Bold /></button>
 * </Tooltip>
 *
 * @example
 * <Tooltip content="Inserir link" shortcut="Ctrl+K" position="bottom">
 *   <button><Link /></button>
 * </Tooltip>
 */
const Tooltip = ({
  children,
  content,
  shortcut,
  position = 'bottom',
  delay = 400,
  className = ''
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const timeoutRef = useRef(null);
  const triggerRef = useRef(null);
  const tooltipRef = useRef(null);

  // Calcular posição do tooltip
  const updatePosition = () => {
    if (!triggerRef.current || !tooltipRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const padding = 8;

    let top = 0;
    let left = 0;

    switch (position) {
      case 'top':
        top = triggerRect.top - tooltipRect.height - padding;
        left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2;
        break;
      case 'bottom':
        top = triggerRect.bottom + padding;
        left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2;
        break;
      case 'left':
        top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2;
        left = triggerRect.left - tooltipRect.width - padding;
        break;
      case 'right':
        top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2;
        left = triggerRect.right + padding;
        break;
      default:
        break;
    }

    // Ajustar para não sair da tela
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    if (left < padding) left = padding;
    if (left + tooltipRect.width > viewportWidth - padding) {
      left = viewportWidth - tooltipRect.width - padding;
    }
    if (top < padding) top = padding;
    if (top + tooltipRect.height > viewportHeight - padding) {
      top = viewportHeight - tooltipRect.height - padding;
    }

    setCoords({ top, left });
  };

  useEffect(() => {
    if (isVisible) {
      updatePosition();
    }
  }, [isVisible, position]);

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsVisible(false);
  };

  const handleFocus = () => {
    setIsVisible(true);
  };

  const handleBlur = () => {
    setIsVisible(false);
  };

  // Limpar timeout ao desmontar
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Classes de posição para a seta
  const arrowClasses = {
    top: 'bottom-[-4px] left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-b-transparent border-t-dark-gray',
    bottom: 'top-[-4px] left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-t-transparent border-b-dark-gray',
    left: 'right-[-4px] top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-r-transparent border-l-dark-gray',
    right: 'left-[-4px] top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-l-transparent border-r-dark-gray'
  };

  return (
    <>
      {/* Trigger element */}
      <div
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleFocus}
        onBlur={handleBlur}
        className={`inline-flex ${className}`}
      >
        {children}
      </div>

      {/* Tooltip */}
      {isVisible && (
        <div
          ref={tooltipRef}
          role="tooltip"
          className="fixed z-[9999] pointer-events-none"
          style={{
            top: `${coords.top}px`,
            left: `${coords.left}px`
          }}
        >
          <div className="bg-dark-gray text-white text-xs font-medium px-2.5 py-1.5 rounded-md shadow-lg whitespace-nowrap flex items-center gap-2">
            <span>{content}</span>
            {shortcut && (
              <kbd className="bg-white/20 px-1.5 py-0.5 rounded text-[10px] font-mono">
                {shortcut}
              </kbd>
            )}
          </div>
          {/* Seta */}
          <div
            className={`absolute w-0 h-0 border-4 ${arrowClasses[position]}`}
          />
        </div>
      )}
    </>
  );
};

Tooltip.propTypes = {
  /** Elemento filho que ativa o tooltip */
  children: PropTypes.node.isRequired,

  /** Texto do tooltip */
  content: PropTypes.string.isRequired,

  /** Atalho de teclado (opcional) */
  shortcut: PropTypes.string,

  /** Posição do tooltip */
  position: PropTypes.oneOf(['top', 'bottom', 'left', 'right']),

  /** Delay em ms antes de mostrar o tooltip */
  delay: PropTypes.number,

  /** Classes CSS adicionais */
  className: PropTypes.string
};

export default Tooltip;
