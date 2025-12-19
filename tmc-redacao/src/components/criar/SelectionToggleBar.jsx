import PropTypes from 'prop-types';
import { CheckSquare, Square, Trash2 } from 'lucide-react';

/**
 * SelectionToggleBar - Barra para selecionar/desselecionar todos os itens
 */
const SelectionToggleBar = ({
  selectedCount,
  totalCount,
  onSelectAll,
  onClearSelection,
  className = ''
}) => {
  const allSelected = selectedCount === totalCount && totalCount > 0;
  const someSelected = selectedCount > 0;

  return (
    <div className={`flex items-center justify-between ${className}`}>
      <div className="flex items-center gap-3">
        <button
          onClick={onSelectAll}
          disabled={allSelected}
          className={`
            flex items-center gap-2 text-sm font-medium transition-colors
            ${allSelected
              ? 'text-medium-gray cursor-default'
              : 'text-tmc-orange hover:text-tmc-orange/80'
            }
          `}
        >
          <CheckSquare size={16} />
          Selecionar Todos
        </button>

        <span className="text-light-gray">|</span>

        <button
          onClick={onClearSelection}
          disabled={!someSelected}
          className={`
            flex items-center gap-2 text-sm transition-colors
            ${someSelected
              ? 'text-medium-gray hover:text-red-500'
              : 'text-light-gray cursor-default'
            }
          `}
        >
          <Trash2 size={16} />
          Limpar
        </button>
      </div>

      <span className="text-sm text-medium-gray">
        <strong className="text-dark-gray">{selectedCount}</strong> selecionado{selectedCount !== 1 ? 's' : ''}
      </span>
    </div>
  );
};

SelectionToggleBar.propTypes = {
  selectedCount: PropTypes.number.isRequired,
  totalCount: PropTypes.number.isRequired,
  onSelectAll: PropTypes.func.isRequired,
  onClearSelection: PropTypes.func.isRequired,
  className: PropTypes.string
};

export default SelectionToggleBar;
