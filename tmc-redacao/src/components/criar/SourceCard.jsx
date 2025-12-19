import PropTypes from 'prop-types';

/**
 * SourceCard - Card de seleção de fonte para criar matéria
 *
 * Estados:
 * - Default: borda light-gray, fundo white
 * - Hover: borda tmc-orange, shadow-md, scale 1.02
 * - Selected: borda tmc-orange 2px, fundo orange-50
 * - Disabled: opacity 0.5, cursor not-allowed
 *
 * O prop `icon` pode ser:
 * - String (emoji): renderiza como texto
 * - React element (lucide-react): renderiza o componente
 */
const SourceCard = ({
  icon,
  title,
  description,
  selected = false,
  disabled = false,
  onClick
}) => {
  // Verifica se o ícone é um componente React ou string (emoji)
  const isReactIcon = typeof icon !== 'string';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        relative w-full h-[200px] rounded-xl p-6
        flex flex-col items-center justify-center text-center
        transition-all duration-200
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${selected
          ? 'border-2 border-tmc-orange bg-orange-50'
          : 'border border-light-gray bg-white hover:border-tmc-orange hover:shadow-md hover:scale-[1.02]'
        }
      `}
      aria-pressed={selected}
      aria-disabled={disabled}
    >
      {/* Ícone */}
      <div
        className={`mb-4 ${isReactIcon ? 'text-tmc-orange' : 'text-5xl'}`}
        aria-hidden="true"
      >
        {isReactIcon ? (
          <div className="w-14 h-14 bg-orange-100 rounded-2xl flex items-center justify-center">
            {icon}
          </div>
        ) : (
          icon
        )}
      </div>

      {/* Título */}
      <h3 className={`text-base font-bold mb-2 ${
        selected ? 'text-tmc-orange' : 'text-dark-gray'
      }`}>
        {title}
      </h3>

      {/* Descrição */}
      <p className="text-sm text-medium-gray leading-tight">
        {description}
      </p>

      {/* Indicador de selecionado (opcional) */}
      {selected && (
        <div className="absolute top-3 right-3">
          <div className="w-6 h-6 bg-tmc-orange rounded-full flex items-center justify-center">
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
      )}
    </button>
  );
};

SourceCard.propTypes = {
  icon: PropTypes.oneOfType([PropTypes.string, PropTypes.node]).isRequired,
  title: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  selected: PropTypes.bool,
  disabled: PropTypes.bool,
  onClick: PropTypes.func.isRequired,
};

export default SourceCard;
