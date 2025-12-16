import PropTypes from 'prop-types';
import { Check } from 'lucide-react';

/**
 * StepIndicator - Indicador de progresso em etapas
 * @param {Object} props
 * @param {Array} props.steps - Lista de etapas
 * @param {number} props.currentStep - Etapa atual (1-indexed)
 */
function StepIndicator({ steps, currentStep }) {
  return (
    <nav aria-label="Progresso das etapas">
      <ol className="flex items-center gap-0">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const isCompleted = stepNumber < currentStep;
          const isCurrent = stepNumber === currentStep;
          const isLast = index === steps.length - 1;

          return (
            <li
              key={step.id}
              className="flex items-center"
            >
              {/* Círculo da etapa */}
              <div className="flex items-center shrink-0">
                <div
                  className={`
                    flex items-center justify-center w-8 h-8 rounded-full
                    font-semibold text-sm transition-all duration-300
                    ${isCompleted
                      ? 'bg-success text-white'
                      : isCurrent
                        ? 'bg-tmc-orange text-white ring-4 ring-tmc-orange/20'
                        : 'bg-light-gray text-medium-gray'
                    }
                  `}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {isCompleted ? (
                    <Check className="w-4 h-4" aria-hidden="true" />
                  ) : (
                    stepNumber
                  )}
                </div>

                {/* Label da etapa */}
                <span
                  className={`
                    ml-2 text-sm font-medium hidden sm:inline whitespace-nowrap
                    ${isCurrent
                      ? 'text-tmc-orange'
                      : isCompleted
                        ? 'text-success'
                        : 'text-medium-gray'
                    }
                  `}
                >
                  {step.label}
                </span>
              </div>

              {/* Linha conectora com traço */}
              {!isLast && (
                <div className="flex items-center px-3">
                  <span
                    className={`
                      text-lg font-light select-none
                      ${isCompleted ? 'text-success' : 'text-gray-300'}
                    `}
                    aria-hidden="true"
                  >
                    —
                  </span>
                </div>
              )}
            </li>
          );
        })}
      </ol>

      {/* Indicador mobile */}
      <div className="sm:hidden mt-2 text-center">
        <span className="text-sm text-medium-gray">
          Etapa {currentStep} de {steps.length}:{' '}
          <span className="font-medium text-dark-gray">
            {steps[currentStep - 1]?.label}
          </span>
        </span>
      </div>
    </nav>
  );
}

StepIndicator.propTypes = {
  steps: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired
    })
  ).isRequired,
  currentStep: PropTypes.number.isRequired
};

export default StepIndicator;
