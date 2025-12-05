import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';
import { useEffect, useState } from 'react';

const StatusMessage = ({
  type = 'info',
  message,
  isVisible,
  onDismiss,
  autoHideDuration = 5000,
  dismissible = true,
  role = 'status'
}) => {
  const [shouldRender, setShouldRender] = useState(isVisible);

  useEffect(() => {
    if (isVisible) {
      setShouldRender(true);

      if (autoHideDuration && onDismiss) {
        const timer = setTimeout(() => {
          onDismiss();
        }, autoHideDuration);

        return () => clearTimeout(timer);
      }
    } else {
      const timer = setTimeout(() => setShouldRender(false), 300);
      return () => clearTimeout(timer);
    }
  }, [isVisible, autoHideDuration, onDismiss]);

  if (!shouldRender) return null;

  const variants = {
    success: {
      icon: CheckCircle,
      bgColor: 'bg-success/10',
      textColor: 'text-success',
      borderColor: 'border-success/30'
    },
    error: {
      icon: XCircle,
      bgColor: 'bg-error/10',
      textColor: 'text-error',
      borderColor: 'border-error/30'
    },
    warning: {
      icon: AlertCircle,
      bgColor: 'bg-warning/10',
      textColor: 'text-warning',
      borderColor: 'border-warning/30'
    },
    info: {
      icon: Info,
      bgColor: 'bg-tmc-orange/10',
      textColor: 'text-tmc-orange',
      borderColor: 'border-tmc-orange/30'
    }
  };

  const variant = variants[type] || variants.info;
  const Icon = variant.icon;

  // Use role="alert" for errors and warnings, role="status" for success and info
  const ariaRole = type === 'error' || type === 'warning' ? 'alert' : role;

  return (
    <div
      className={`${variant.bgColor} ${variant.borderColor} border rounded-lg p-4 flex items-start gap-3 transition-opacity duration-300 ${
        isVisible ? 'opacity-100' : 'opacity-0'
      }`}
      role={ariaRole}
      aria-live={ariaRole === 'alert' ? 'assertive' : 'polite'}
      aria-atomic="true"
    >
      <Icon size={20} className={`${variant.textColor} flex-shrink-0 mt-0.5`} aria-hidden="true" />

      <p className={`flex-1 text-sm ${variant.textColor} font-medium`}>
        {message}
      </p>

      {dismissible && onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className={`${variant.textColor} hover:opacity-70 transition-opacity min-h-[44px] min-w-[44px] flex items-center justify-center -mr-2 -mt-2`}
          aria-label="Fechar mensagem"
        >
          <X size={18} aria-hidden="true" />
        </button>
      )}
    </div>
  );
};

export default StatusMessage;
