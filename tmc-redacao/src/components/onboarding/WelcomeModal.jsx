import { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { Rocket } from 'lucide-react';

function WelcomeModal({ userName, onDismiss, onStartTour }) {
  const modalRef = useRef(null);

  // Lock body scroll
  useEffect(() => {
    const original = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = original; };
  }, []);

  // Focus trap
  useEffect(() => {
    modalRef.current?.focus();
  }, []);

  // Escape to close
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onDismiss(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onDismiss]);

  const handleStartTour = () => {
    onDismiss();
    // Small delay so modal unmounts before tour starts
    setTimeout(() => onStartTour(), 100);
  };

  return (
    <div
      className="fixed inset-0 flex items-center justify-center p-4"
      style={{ zIndex: 10000 }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="welcome-title"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onDismiss} />

      {/* Modal */}
      <div
        ref={modalRef}
        tabIndex={-1}
        className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-tmc-dark-green to-tmc-light-green p-8 text-center text-white">
          <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Rocket className="w-8 h-8" aria-hidden="true" />
          </div>
          <h2 id="welcome-title" className="text-2xl font-bold">
            Bem-vindo, {userName}!
          </h2>
          <p className="text-white/80 mt-1">TMC Redação</p>
        </div>

        {/* Body */}
        <div className="p-8 text-center">
          <p className="text-medium-gray mb-8">
            Preparamos um tour guiado para você conhecer a ferramenta. Leva apenas 2 minutos!
          </p>

          <div className="flex gap-3 justify-center">
            <button
              onClick={onDismiss}
              className="px-6 py-3 border border-gray-300 text-medium-gray hover:bg-gray-50 rounded-lg font-medium transition-colors"
            >
              Pular
            </button>
            <button
              onClick={handleStartTour}
              className="px-6 py-3 bg-tmc-orange hover:bg-tmc-orange/90 text-white rounded-lg font-semibold transition-colors"
            >
              Começar tour →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

WelcomeModal.propTypes = {
  userName: PropTypes.string.isRequired,
  onDismiss: PropTypes.func.isRequired,
  onStartTour: PropTypes.func.isRequired,
};

export default WelcomeModal;
