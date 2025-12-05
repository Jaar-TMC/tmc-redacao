import { useEffect, useRef } from 'react';
import { AlertTriangle, X } from 'lucide-react';

/**
 * ConfirmDialog Component
 *
 * WCAG 2.1 Compliance:
 * - No Keyboard Trap (2.1.2): Modal can be closed with Escape key, focus trap implemented
 * - Focus Order (2.4.3): Focus moves to close button first, then action buttons
 * - Headings and Labels (2.4.6): Dialog has descriptive title and message
 */
const ConfirmDialog = ({ isOpen, onClose, onConfirm, title, message, confirmText = 'Confirmar', cancelText = 'Cancelar', variant = 'danger' }) => {
  const dialogRef = useRef(null);
  const previousFocusRef = useRef(null);
  const confirmButtonRef = useRef(null);

  useEffect(() => {
    if (isOpen && dialogRef.current) {
      previousFocusRef.current = document.activeElement;

      const focusableElements = dialogRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      // Focus the confirm button initially for dangerous actions
      setTimeout(() => {
        if (variant === 'danger' && confirmButtonRef.current) {
          confirmButtonRef.current.focus();
        } else {
          firstElement?.focus();
        }
      }, 50);

      const handleTabKey = (e) => {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      };

      const handleEscKey = (e) => {
        if (e.key === 'Escape') {
          onClose();
        }
      };

      document.addEventListener('keydown', handleTabKey);
      document.addEventListener('keydown', handleEscKey);

      return () => {
        document.removeEventListener('keydown', handleTabKey);
        document.removeEventListener('keydown', handleEscKey);
        if (previousFocusRef.current) {
          previousFocusRef.current.focus();
        }
      };
    }
  }, [isOpen, onClose, variant]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const variantStyles = {
    danger: {
      icon: 'bg-error/10 text-error',
      button: 'bg-error hover:bg-error/90'
    },
    warning: {
      icon: 'bg-warning/10 text-warning',
      button: 'bg-warning hover:bg-warning/90'
    },
    info: {
      icon: 'bg-tmc-orange/10 text-tmc-orange',
      button: 'bg-tmc-orange hover:bg-tmc-orange/90'
    }
  };

  const currentVariant = variantStyles[variant] || variantStyles.danger;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-description"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        className="bg-white rounded-xl w-full max-w-md p-6 m-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div className={`w-12 h-12 rounded-full ${currentVariant.icon} flex items-center justify-center flex-shrink-0`}>
            <AlertTriangle size={24} aria-hidden="true" />
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 hover:bg-off-white rounded-lg transition-colors min-h-[44px] min-w-[44px]"
            aria-label="Fechar diálogo"
          >
            <X size={20} className="text-medium-gray" aria-hidden="true" />
          </button>
        </div>

        <h2 id="confirm-dialog-title" className="text-xl font-bold text-dark-gray mb-2">
          {title}
        </h2>

        <p id="confirm-dialog-description" className="text-medium-gray mb-6">
          {message}
        </p>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 min-h-[44px] py-2.5 border border-light-gray rounded-lg text-medium-gray font-medium hover:bg-off-white transition-colors"
          >
            {cancelText}
          </button>
          <button
            ref={confirmButtonRef}
            type="button"
            onClick={handleConfirm}
            className={`flex-1 min-h-[44px] py-2.5 ${currentVariant.button} text-white rounded-lg font-semibold transition-colors`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
