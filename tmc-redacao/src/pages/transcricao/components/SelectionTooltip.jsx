import { useCallback, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { Plus, Quote, X } from 'lucide-react';

/**
 * SelectionTooltip - Tooltip que aparece ao selecionar texto na transcrição completa
 * Oferece opções para adicionar como resumo ou como citação direta
 * @param {Object} props
 * @param {boolean} props.isVisible - Se o tooltip está visível
 * @param {Object} props.position - Posição do tooltip {x, y}
 * @param {Function} props.onAddAsText - Callback ao adicionar como texto normal
 * @param {Function} props.onAddAsQuote - Callback ao adicionar como citação
 * @param {Function} props.onClose - Callback ao fechar
 */
function SelectionTooltip({
  isVisible,
  position,
  onAddAsText,
  onAddAsQuote,
  onClose
}) {
  const tooltipRef = useRef(null);

  // Fechar ao clicar fora
  useEffect(() => {
    if (!isVisible) return;

    const handleClickOutside = (e) => {
      if (tooltipRef.current && !tooltipRef.current.contains(e.target)) {
        onClose();
      }
    };

    // Pequeno delay para não fechar imediatamente após abrir
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 100);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isVisible, onClose]);

  // Fechar com Escape
  useEffect(() => {
    if (!isVisible) return;

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isVisible, onClose]);

  const handleAddAsText = useCallback(() => {
    onAddAsText();
    onClose();
  }, [onAddAsText, onClose]);

  const handleAddAsQuote = useCallback(() => {
    onAddAsQuote();
    onClose();
  }, [onAddAsQuote, onClose]);

  if (!isVisible) return null;

  return (
    <div
      ref={tooltipRef}
      role="dialog"
      aria-label="Opções de seleção"
      style={{
        position: 'fixed',
        top: `${position.y}px`,
        left: `${position.x}px`,
        transform: 'translate(-50%, -120%)',
        zIndex: 1000
      }}
      className="bg-white rounded-lg shadow-2xl border-2 border-gray-200 p-2 min-w-[240px] animate-in fade-in slide-in-from-bottom-2 duration-200"
    >
      {/* Botão de fechar */}
      <button
        type="button"
        onClick={onClose}
        className="absolute -top-2 -right-2 w-6 h-6 bg-gray-700 hover:bg-gray-800 text-white rounded-full flex items-center justify-center shadow-lg transition-colors"
        aria-label="Fechar opções"
      >
        <X className="w-3 h-3" />
      </button>

      {/* Título */}
      <div className="px-2 py-1 mb-1">
        <p className="text-xs font-semibold text-dark-gray">
          Adicionar à matéria como:
        </p>
      </div>

      {/* Opções */}
      <div className="space-y-1">
        {/* Adicionar como texto normal */}
        <button
          type="button"
          onClick={handleAddAsText}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-left hover:bg-gray-100 transition-colors group"
        >
          <div className="w-8 h-8 bg-yellow-100 group-hover:bg-yellow-200 rounded-lg flex items-center justify-center transition-colors">
            <Plus className="w-4 h-4 text-yellow-700" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-dark-gray">
              Adicionar como resumo
            </p>
            <p className="text-xs text-medium-gray">
              Texto parafraseado ou resumido
            </p>
          </div>
        </button>

        {/* Adicionar como citação */}
        <button
          type="button"
          onClick={handleAddAsQuote}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-left hover:bg-blue-50 transition-colors group"
        >
          <div className="w-8 h-8 bg-blue-100 group-hover:bg-blue-200 rounded-lg flex items-center justify-center transition-colors">
            <Quote className="w-4 h-4 text-blue-700" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-dark-gray">
              Adicionar como citação
            </p>
            <p className="text-xs text-medium-gray">
              Fala direta entre aspas
            </p>
          </div>
        </button>
      </div>

      {/* Seta do tooltip */}
      <div
        className="absolute left-1/2 bottom-0 transform -translate-x-1/2 translate-y-full"
        aria-hidden="true"
      >
        <div className="w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent border-t-gray-200" />
        <div className="w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent border-t-white absolute left-1/2 -translate-x-1/2 -top-[7px]" />
      </div>
    </div>
  );
}

SelectionTooltip.propTypes = {
  isVisible: PropTypes.bool.isRequired,
  position: PropTypes.shape({
    x: PropTypes.number.isRequired,
    y: PropTypes.number.isRequired
  }).isRequired,
  onAddAsText: PropTypes.func.isRequired,
  onAddAsQuote: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired
};

export default SelectionTooltip;
