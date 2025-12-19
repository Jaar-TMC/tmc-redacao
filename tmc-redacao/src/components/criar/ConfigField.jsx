import PropTypes from 'prop-types';
import { TooltipEducativo } from './index';

/**
 * ConfigField Component
 *
 * Campo de configuração com label, ícone e tooltip educativo.
 * Usado na página de configurações da matéria.
 *
 * O prop `icon` pode ser:
 * - String (emoji): renderiza como texto
 * - React element (lucide-react): renderiza o componente com estilo
 */
const ConfigField = ({
  label,
  icon,
  tooltip,
  required = false,
  children,
  className = ''
}) => {
  // Verifica se o ícone é um componente React ou string (emoji)
  const isReactIcon = icon && typeof icon !== 'string';

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center gap-2">
        {icon && (
          isReactIcon ? (
            <span className="text-tmc-orange">{icon}</span>
          ) : (
            <span className="text-lg">{icon}</span>
          )
        )}
        <label className="text-sm font-medium text-dark-gray">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
        {tooltip && (
          <TooltipEducativo
            title={tooltip.title}
            icon={tooltip.icon || (typeof icon === 'string' ? icon : null)}
            position={tooltip.position || 'right'}
          >
            {tooltip.content}
          </TooltipEducativo>
        )}
      </div>
      {children}
    </div>
  );
};

ConfigField.propTypes = {
  label: PropTypes.string.isRequired,
  icon: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  tooltip: PropTypes.shape({
    title: PropTypes.string.isRequired,
    icon: PropTypes.string,
    content: PropTypes.node.isRequired,
    position: PropTypes.oneOf(['auto', 'top', 'bottom', 'left', 'right'])
  }),
  required: PropTypes.bool,
  children: PropTypes.node.isRequired,
  className: PropTypes.string
};

export default ConfigField;
