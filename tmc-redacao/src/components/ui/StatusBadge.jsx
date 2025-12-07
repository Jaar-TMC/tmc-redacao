import { FileEdit, CheckCircle, Clock } from 'lucide-react';
import PropTypes from 'prop-types';

const BADGE_CONFIG = {
  draft: {
    label: 'RASCUNHO',
    color: '#E87722',
    bgColor: '#FFF5EE',
    borderColor: '#E87722',
    icon: FileEdit
  },
  published: {
    label: 'PUBLICADA',
    color: '#10B981',
    bgColor: '#E8F5E9',
    borderColor: '#10B981',
    icon: CheckCircle
  },
  'in-review': {
    label: 'EM REVISÃO',
    color: '#F59E0B',
    bgColor: '#FFF8E6',
    borderColor: '#F59E0B',
    icon: Clock
  }
};

/**
 * StatusBadge Component
 *
 * Exibe o status de uma matéria (Rascunho, Publicada, Em Revisão)
 * Segue especificações do documento de planejamento UI/UX
 *
 * WCAG 2.1 Compliance:
 * - Uses color AND icon AND text to convey status (not color alone)
 * - Proper ARIA labels for accessibility
 * - Clear visual distinction between states
 */
const StatusBadge = ({ status, size = 'md', showIcon = true, className = '' }) => {
  const config = BADGE_CONFIG[status] || BADGE_CONFIG.draft;
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs gap-1',
    md: 'px-3 py-1.5 text-xs gap-1.5',
    lg: 'px-4 py-2 text-sm gap-2'
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16
  };

  return (
    <div
      className={`inline-flex items-center rounded-md font-semibold uppercase tracking-wide ${sizeClasses[size]} ${className}`}
      style={{
        backgroundColor: config.bgColor,
        color: config.color,
        border: `1px solid ${config.borderColor}`
      }}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      {showIcon && (
        <Icon
          style={{ width: `${iconSizes[size]}px`, height: `${iconSizes[size]}px` }}
          aria-hidden="true"
        />
      )}
      <span>{config.label}</span>
    </div>
  );
};

StatusBadge.propTypes = {
  status: PropTypes.oneOf(['draft', 'published', 'in-review']).isRequired,
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  showIcon: PropTypes.bool,
  className: PropTypes.string
};

export default StatusBadge;
