import PropTypes from 'prop-types';
import { Lightbulb, Info, AlertTriangle, CheckCircle } from 'lucide-react';

/**
 * TipBox - Componente padronizado para dicas e mensagens informativas
 *
 * Variantes disponíveis:
 * - tip (padrão): Dicas úteis para o usuário (laranja TMC)
 * - info: Informações gerais (azul)
 * - warning: Alertas e avisos (amarelo)
 * - success: Confirmações positivas (verde)
 */
const TipBox = ({
  children,
  variant = 'tip',
  title,
  compact = false,
  className = ''
}) => {
  const variants = {
    tip: {
      icon: Lightbulb,
      bg: 'bg-tmc-orange/5',
      border: 'border-tmc-orange/20',
      accent: 'bg-tmc-orange',
      iconBg: 'bg-tmc-orange/10',
      iconColor: 'text-tmc-orange',
      titleColor: 'text-tmc-orange',
      textColor: 'text-dark-gray',
      defaultTitle: 'Dica'
    },
    info: {
      icon: Info,
      bg: 'bg-blue-50',
      border: 'border-blue-100',
      accent: 'bg-blue-500',
      iconBg: 'bg-blue-100',
      iconColor: 'text-blue-600',
      titleColor: 'text-blue-700',
      textColor: 'text-blue-800',
      defaultTitle: 'Informação'
    },
    warning: {
      icon: AlertTriangle,
      bg: 'bg-amber-50',
      border: 'border-amber-100',
      accent: 'bg-amber-500',
      iconBg: 'bg-amber-100',
      iconColor: 'text-amber-600',
      titleColor: 'text-amber-700',
      textColor: 'text-amber-800',
      defaultTitle: 'Atenção'
    },
    success: {
      icon: CheckCircle,
      bg: 'bg-green-50',
      border: 'border-green-100',
      accent: 'bg-green-500',
      iconBg: 'bg-green-100',
      iconColor: 'text-green-600',
      titleColor: 'text-green-700',
      textColor: 'text-green-800',
      defaultTitle: 'Sucesso'
    }
  };

  const config = variants[variant] || variants.tip;
  const Icon = config.icon;
  const displayTitle = title ?? config.defaultTitle;

  if (compact) {
    return (
      <div
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg
          ${config.bg} ${config.textColor}
          ${className}
        `}
        role="note"
      >
        <Icon size={16} className={config.iconColor} aria-hidden="true" />
        <p className="text-sm">{children}</p>
      </div>
    );
  }

  return (
    <div
      className={`
        relative overflow-hidden rounded-xl border
        ${config.bg} ${config.border}
        ${className}
      `}
      role="note"
    >
      {/* Accent bar */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${config.accent}`} />

      <div className="flex items-start gap-3 p-4 pl-5">
        {/* Icon container */}
        <div
          className={`
            flex-shrink-0 w-8 h-8 rounded-lg
            flex items-center justify-center
            ${config.iconBg}
          `}
        >
          <Icon size={18} className={config.iconColor} aria-hidden="true" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {displayTitle && (
            <span className={`font-semibold text-sm ${config.titleColor}`}>
              {displayTitle}:
            </span>
          )}{' '}
          <span className={`text-sm ${config.textColor}`}>
            {children}
          </span>
        </div>
      </div>
    </div>
  );
};

TipBox.propTypes = {
  /** Conteúdo da dica */
  children: PropTypes.node.isRequired,
  /** Variante visual */
  variant: PropTypes.oneOf(['tip', 'info', 'warning', 'success']),
  /** Título customizado (null para esconder, undefined para usar padrão) */
  title: PropTypes.string,
  /** Modo compacto (inline, sem box) */
  compact: PropTypes.bool,
  /** Classes CSS adicionais */
  className: PropTypes.string
};

export default TipBox;
