import { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { HelpCircle, X } from 'lucide-react';

/**
 * TooltipEducativo Component
 *
 * Componente de tooltip educativo para orientar o usuário durante o fluxo de criação de matéria.
 * Aparece ao clicar no ícone de ajuda e pode ser posicionado automaticamente para evitar sair da tela.
 *
 * WCAG 2.1 Compliance:
 * - No Keyboard Trap (2.1.2): Tooltip pode ser fechado com Escape
 * - Focus Management: Retorna foco ao botão que abriu após fechar
 * - Keyboard Navigation (2.1.1): Totalmente navegável por teclado
 * - Name, Role, Value (4.1.2): Aria labels apropriados
 *
 * @example
 * <TooltipEducativo
 *   title="Orientação sobre o Lide"
 *   icon="📝"
 * >
 *   <p>O lide é o primeiro parágrafo da matéria...</p>
 *   <ul>
 *     <li>"Focar no impacto econômico"</li>
 *   </ul>
 * </TooltipEducativo>
 */
const TooltipEducativo = ({
  title,
  icon,
  children,
  position = 'right', // 'right', 'left', 'top', 'bottom', 'auto'
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [calculatedPosition, setCalculatedPosition] = useState(position);
  const buttonRef = useRef(null);
  const tooltipRef = useRef(null);
  const previousFocusRef = useRef(null);

  // Calcular posição inteligente do tooltip based on DOM measurements
  // setState is necessary here because position depends on DOM layout (getBoundingClientRect)
  useEffect(() => {
    if (isOpen && tooltipRef.current && buttonRef.current && position === 'auto') {
      const buttonRect = buttonRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let newPosition = 'right';

      // Verificar se há espaço à direita
      if (buttonRect.right + tooltipRect.width > viewportWidth - 20) {
        // Se não couber à direita, tentar à esquerda
        if (buttonRect.left - tooltipRect.width > 20) {
          newPosition = 'left';
        } else {
          // Se não couber nem à direita nem à esquerda, colocar embaixo
          newPosition = 'bottom';
        }
      }

      // Verificar se há espaço embaixo (se foi escolhido bottom)
      if (newPosition === 'bottom' && buttonRect.bottom + tooltipRect.height > viewportHeight - 20) {
        newPosition = 'top';
      }

      setCalculatedPosition(newPosition); // eslint-disable-line react-hooks/set-state-in-effect
    }
  }, [isOpen, position]);

  const handleOpen = () => {
    setIsOpen(true);
  };

  const handleClose = () => {
    setIsOpen(false);
    // Retornar foco ao botão que abriu
    if (buttonRef.current) {
      buttonRef.current.focus();
    }
  };

  const handleToggle = () => {
    if (isOpen) {
      handleClose();
    } else {
      handleOpen();
    }
  };

  // Gerenciar foco e teclas
  useEffect(() => {
    if (isOpen) {
      previousFocusRef.current = document.activeElement;

      const handleEscape = (e) => {
        if (e.key === 'Escape') {
          handleClose();
        }
      };

      const handleClickOutside = (e) => {
        if (
          tooltipRef.current &&
          !tooltipRef.current.contains(e.target) &&
          buttonRef.current &&
          !buttonRef.current.contains(e.target)
        ) {
          handleClose();
        }
      };

      document.addEventListener('keydown', handleEscape);
      document.addEventListener('mousedown', handleClickOutside);

      return () => {
        document.removeEventListener('keydown', handleEscape);
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  // Estilos de posicionamento
  const positionStyles = {
    right: 'left-full ml-2 top-0',
    left: 'right-full mr-2 top-0',
    top: 'bottom-full mb-2 left-0',
    bottom: 'top-full mt-2 left-0'
  };

  const currentPosition = position === 'auto' ? calculatedPosition : position;

  // Responsividade: em mobile sempre embaixo
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  const finalPosition = isMobile ? 'bottom' : currentPosition;

  return (
    <div className={`relative inline-block ${className}`}>
      {/* Botão de Ajuda */}
      <button
        ref={buttonRef}
        type="button"
        onClick={handleToggle}
        className="inline-flex items-center justify-center w-5 h-5 text-medium-gray hover:text-tmc-orange transition-colors rounded-full hover:bg-off-white min-h-[44px] min-w-[44px] -m-2"
        aria-label={`Ajuda: ${title}`}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
      >
        <HelpCircle size={20} aria-hidden="true" />
      </button>

      {/* Tooltip */}
      {isOpen && (
        <div
          ref={tooltipRef}
          role="dialog"
          aria-modal="false"
          aria-labelledby="tooltip-title"
          className={`
            absolute z-50 w-80 max-w-[90vw] bg-white rounded-lg shadow-xl border border-light-gray
            ${positionStyles[finalPosition]}
            animate-fade-in
          `}
          style={{
            animation: 'fadeIn 200ms ease-in'
          }}
        >
          {/* Header */}
          <div className="flex items-start justify-between p-4 border-b border-light-gray">
            <div className="flex items-center gap-2 flex-1">
              {icon && (
                <span className="text-2xl flex-shrink-0" aria-hidden="true">
                  {icon}
                </span>
              )}
              <h3
                id="tooltip-title"
                className="text-sm font-bold text-dark-gray uppercase tracking-wide"
              >
                {title}
              </h3>
            </div>
            <button
              type="button"
              onClick={handleClose}
              className="p-1 hover:bg-off-white rounded transition-colors flex-shrink-0 min-h-[44px] min-w-[44px] -m-2"
              aria-label="Fechar tooltip"
            >
              <X size={18} className="text-medium-gray" aria-hidden="true" />
            </button>
          </div>

          {/* Content */}
          <div className="p-4 text-sm text-medium-gray max-h-96 overflow-y-auto">
            <div className="prose prose-sm prose-slate max-w-none">
              {children}
            </div>
          </div>
        </div>
      )}

      {/* CSS para animação */}
      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fade-in {
          animation: fadeIn 200ms ease-in;
        }

        /* Estilos para conteúdo do tooltip */
        .prose p {
          margin-bottom: 0.75rem;
          line-height: 1.6;
        }

        .prose p:last-child {
          margin-bottom: 0;
        }

        .prose ul {
          margin-top: 0.5rem;
          margin-bottom: 0.75rem;
          padding-left: 1.25rem;
          list-style-type: disc;
        }

        .prose ul:last-child {
          margin-bottom: 0;
        }

        .prose li {
          margin-bottom: 0.25rem;
          line-height: 1.6;
        }

        .prose li:last-child {
          margin-bottom: 0;
        }

        .prose strong {
          font-weight: 600;
          color: #111827;
        }

        .prose code {
          background-color: #f3f4f6;
          padding: 0.125rem 0.25rem;
          border-radius: 0.25rem;
          font-size: 0.875em;
          font-family: ui-monospace, monospace;
        }
      `}</style>
    </div>
  );
};

TooltipEducativo.propTypes = {
  /** Título do tooltip (obrigatório) */
  title: PropTypes.string.isRequired,

  /** Ícone emoji ou texto para exibir ao lado do título */
  icon: PropTypes.string,

  /** Conteúdo do tooltip (pode ser JSX) */
  children: PropTypes.node.isRequired,

  /**
   * Posição preferencial do tooltip
   * 'auto' calcula a melhor posição automaticamente
   */
  position: PropTypes.oneOf(['right', 'left', 'top', 'bottom', 'auto']),

  /** Classes CSS adicionais para o container */
  className: PropTypes.string
};

export default TooltipEducativo;
