/**
 * OpinionToggle - Opinion mode toggle component
 *
 * Shows a toggle switch for enabling opinion mode.
 * Only available for categories that allow opinion (Esportes, Politica, Economia).
 */

import PropTypes from 'prop-types';
import { MessageSquareText, Info } from 'lucide-react';
import { CATEGORIAS_EDITORIAIS } from '../../constants/editorial';

const OpinionToggle = ({
  categoryId,
  isEnabled,
  onToggle,
  tipoMateria = '',
  className = ''
}) => {
  const categoria = CATEGORIAS_EDITORIAIS[categoryId];

  // Don't render if category doesn't allow opinion
  if (!categoria?.allowsOpinion) {
    return null;
  }

  // Auto-enabled hint for column type
  const isColumnType = tipoMateria === 'coluna';
  const showAutoEnabled = isColumnType && !isEnabled;

  return (
    <div className={`bg-orange-50 border border-orange-200 rounded-xl p-4 ${className}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-orange-100 rounded-lg">
            <MessageSquareText size={20} className="text-orange-600" />
          </div>
          <div>
            <h3 className="font-semibold text-dark-gray flex items-center gap-2">
              Modo Opinativo
              {isEnabled && (
                <span className="text-xs font-medium text-orange-600 bg-orange-100 px-2 py-0.5 rounded-full">
                  ATIVO
                </span>
              )}
            </h3>
            <p className="text-sm text-medium-gray mt-1">
              Permite expressar ponto de vista e usar adjetivos valorativos.
              Ideal para colunas, analises e comentarios.
            </p>

            {/* Auto-enabled notice for column type */}
            {showAutoEnabled && (
              <div className="flex items-center gap-1.5 mt-2 text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded">
                <Info size={12} />
                <span>Sera ativado automaticamente para tipo "Coluna"</span>
              </div>
            )}

            {/* What changes with opinion mode */}
            {isEnabled && (
              <div className="mt-3 p-3 bg-white rounded-lg border border-orange-100">
                <p className="text-xs font-medium text-dark-gray mb-2">Com modo opinativo:</p>
                <ul className="space-y-1 text-xs text-medium-gray">
                  <li className="flex items-center gap-1.5">
                    <span className="w-1 h-1 bg-orange-400 rounded-full" />
                    Pode expressar ponto de vista claro
                  </li>
                  <li className="flex items-center gap-1.5">
                    <span className="w-1 h-1 bg-orange-400 rounded-full" />
                    Adjetivos valorativos liberados
                  </li>
                  <li className="flex items-center gap-1.5">
                    <span className="w-1 h-1 bg-orange-400 rounded-full" />
                    Pode usar primeira pessoa
                  </li>
                  <li className="flex items-center gap-1.5">
                    <span className="w-1 h-1 bg-orange-400 rounded-full" />
                    Argumentacao com posicionamento
                  </li>
                </ul>
                <p className="text-xs text-red-600 mt-2 font-medium">
                  Vetos universais ainda se aplicam (sem preconceito, ataques, etc.)
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Toggle Switch */}
        <button
          type="button"
          role="switch"
          aria-checked={isEnabled}
          onClick={() => onToggle(!isEnabled)}
          className={`
            relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full
            border-2 border-transparent transition-colors duration-200 ease-in-out
            focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2
            ${isEnabled ? 'bg-orange-500' : 'bg-gray-200'}
          `}
        >
          <span className="sr-only">Ativar modo opinativo</span>
          <span
            className={`
              pointer-events-none inline-block h-5 w-5 transform rounded-full
              bg-white shadow ring-0 transition duration-200 ease-in-out
              ${isEnabled ? 'translate-x-5' : 'translate-x-0'}
            `}
          />
        </button>
      </div>
    </div>
  );
};

OpinionToggle.propTypes = {
  categoryId: PropTypes.string.isRequired,
  isEnabled: PropTypes.bool.isRequired,
  onToggle: PropTypes.func.isRequired,
  tipoMateria: PropTypes.string,
  className: PropTypes.string
};

export default OpinionToggle;
