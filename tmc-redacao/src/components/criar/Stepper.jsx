import PropTypes from 'prop-types';
import { Link2, FileText, Sliders, PenLine, Check } from 'lucide-react';

// Mapeamento de ícones por label do step
const stepIcons = {
  'Fonte': Link2,
  'Texto-Base': FileText,
  'Configurar': Sliders,
  'Editor': PenLine
};

/**
 * Stepper - Componente de navegação por etapas para o fluxo de criação de matéria
 *
 * Características:
 * - Exibe progresso visual com círculos e linhas conectoras
 * - Suporta navegação por teclado (Tab, Enter, Space)
 * - Responsivo: horizontal em desktop, vertical em mobile
 * - Transições suaves (300ms ease)
 * - Acessível (ARIA labels, focus indicators)
 *
 * Estados dos steps:
 * - Completo: círculo preenchido (tmc-orange), linha preenchida
 * - Atual: círculo preenchido, borda destacada (ring)
 * - Pendente: círculo vazio (light-gray), linha cinza
 * - Clicável: steps anteriores ao atual podem ser clicados
 *
 * @param {Object} props
 * @param {string[]} props.steps - Lista de nomes das etapas
 * @param {number} props.currentStep - Índice da etapa atual (0-indexed)
 * @param {Function} props.onStepClick - Callback quando uma etapa é clicada (recebe o índice)
 *
 * @example
 * <Stepper
 *   steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
 *   currentStep={2}
 *   onStepClick={(stepIndex) => navigate(stepRoutes[stepIndex])}
 * />
 */
function Stepper({ steps, currentStep, onStepClick }) {
  return (
    <div className="w-full py-4">
      {/* Stepper horizontal (desktop e tablet) */}
      <nav aria-label="Progresso da criação de matéria" className="hidden md:block">
        <ol className="flex items-center justify-center">
          {steps.map((stepLabel, index) => {
            const isCompleted = index < currentStep;
            const isCurrent = index === currentStep;
            const isPending = index > currentStep;
            const isClickable = index < currentStep;
            const isLast = index === steps.length - 1;

            return (
              <li key={index} className="flex items-center">
                {/* Container do step com botão */}
                <button
                  type="button"
                  onClick={() => isClickable && onStepClick && onStepClick(index)}
                  disabled={!isClickable}
                  className={`
                    flex flex-col items-center gap-2 transition-all duration-300 ease-in-out
                    ${isClickable
                      ? 'cursor-pointer hover:scale-105 focus-visible:outline-tmc-orange'
                      : 'cursor-default'
                    }
                    p-2 rounded-lg
                  `}
                  aria-current={isCurrent ? 'step' : undefined}
                  aria-label={`${stepLabel}${isCompleted ? ' - Completo' : isCurrent ? ' - Atual' : ' - Pendente'}`}
                  tabIndex={isClickable || isCurrent ? 0 : -1}
                >
                  {/* Círculo da etapa com ícone personalizado */}
                  <div
                    className={`
                      relative flex items-center justify-center w-10 h-10 rounded-full
                      font-semibold text-sm transition-all duration-300 ease-in-out
                      ${isCompleted
                        ? 'bg-tmc-orange text-white'
                        : isCurrent
                          ? 'bg-tmc-orange text-white ring-4 ring-tmc-orange/20'
                          : 'bg-light-gray text-medium-gray'
                      }
                    `}
                  >
                    {/* Ícone específico do step */}
                    {(() => {
                      const IconComponent = stepIcons[stepLabel] || Link2;
                      return <IconComponent className="w-5 h-5" aria-hidden="true" />;
                    })()}

                    {/* Badge de check para steps completos */}
                    {isCompleted && (
                      <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-success rounded-full flex items-center justify-center border-2 border-white">
                        <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />
                      </div>
                    )}
                  </div>

                  {/* Label da etapa */}
                  <span
                    className={`
                      text-xs font-medium text-center whitespace-nowrap transition-colors duration-300
                      ${isCurrent
                        ? 'text-tmc-orange font-semibold'
                        : isCompleted
                          ? 'text-tmc-orange'
                          : 'text-medium-gray'
                      }
                    `}
                  >
                    {stepLabel}
                  </span>

                  {/* Status para leitores de tela */}
                  {isCurrent && <span className="sr-only">Etapa atual</span>}
                  {isCompleted && <span className="sr-only">Completo</span>}
                  {isPending && <span className="sr-only">Pendente</span>}
                </button>

                {/* Linha conectora */}
                {!isLast && (
                  <div
                    className={`
                      h-0.5 w-12 lg:w-20 mx-1 transition-all duration-300 ease-in-out
                      ${isCompleted ? 'bg-tmc-orange' : 'bg-light-gray'}
                    `}
                    aria-hidden="true"
                  />
                )}
              </li>
            );
          })}
        </ol>
      </nav>

      {/* Stepper vertical (mobile) */}
      <nav aria-label="Progresso da criação de matéria" className="md:hidden">
        <ol className="flex flex-col gap-3 max-w-xs mx-auto">
          {steps.map((stepLabel, index) => {
            const isCompleted = index < currentStep;
            const isCurrent = index === currentStep;
            const isPending = index > currentStep;
            const isClickable = index < currentStep;
            const isLast = index === steps.length - 1;

            return (
              <li key={index}>
                <div className="flex items-start gap-3">
                  {/* Coluna do indicador */}
                  <div className="flex flex-col items-center flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => isClickable && onStepClick && onStepClick(index)}
                      disabled={!isClickable}
                      className={`
                        relative flex items-center justify-center w-8 h-8 rounded-full
                        font-semibold text-xs transition-all duration-300 ease-in-out
                        ${isClickable
                          ? 'cursor-pointer focus-visible:outline-tmc-orange'
                          : 'cursor-default'
                        }
                        ${isCompleted
                          ? 'bg-tmc-orange text-white'
                          : isCurrent
                            ? 'bg-tmc-orange text-white ring-4 ring-tmc-orange/20'
                            : 'bg-light-gray text-medium-gray'
                        }
                      `}
                      aria-current={isCurrent ? 'step' : undefined}
                      aria-label={`${stepLabel}${isCompleted ? ' - Completo' : isCurrent ? ' - Atual' : ' - Pendente'}`}
                      tabIndex={isClickable || isCurrent ? 0 : -1}
                    >
                      {/* Ícone específico do step (mobile) */}
                      {(() => {
                        const IconComponent = stepIcons[stepLabel] || Link2;
                        return <IconComponent className="w-4 h-4" aria-hidden="true" />;
                      })()}

                      {/* Badge de check para steps completos (mobile) */}
                      {isCompleted && (
                        <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-success rounded-full flex items-center justify-center border-2 border-white">
                          <Check className="w-2 h-2 text-white" strokeWidth={3} />
                        </div>
                      )}
                    </button>

                    {/* Linha vertical conectora */}
                    {!isLast && (
                      <div
                        className={`
                          w-0.5 h-8 mt-1 transition-all duration-300 ease-in-out
                          ${isCompleted ? 'bg-tmc-orange' : 'bg-light-gray'}
                        `}
                        aria-hidden="true"
                      />
                    )}
                  </div>

                  {/* Coluna do label e status */}
                  <div className="flex flex-col pt-1 min-w-0 flex-1">
                    <span
                      className={`
                        text-sm font-medium transition-colors duration-300
                        ${isCurrent
                          ? 'text-tmc-orange'
                          : isCompleted
                            ? 'text-tmc-orange'
                            : 'text-medium-gray'
                        }
                      `}
                    >
                      {stepLabel}
                    </span>

                    {/* Status visual */}
                    <span
                      className={`
                        text-xs mt-0.5 transition-colors duration-300
                        ${isCurrent
                          ? 'text-tmc-orange'
                          : isCompleted
                            ? 'text-success'
                            : 'text-medium-gray'
                        }
                      `}
                    >
                      {isCompleted && 'Completo'}
                      {isCurrent && 'Atual'}
                      {isPending && 'Pendente'}
                    </span>

                    {/* Status para leitores de tela */}
                    <span className="sr-only">
                      {isCompleted && ' - Completo'}
                      {isCurrent && ' - Etapa atual'}
                      {isPending && ' - Pendente'}
                    </span>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>

        {/* Indicador de progresso mobile */}
        <div className="mt-4 text-center">
          <span className="text-sm text-medium-gray">
            Etapa {currentStep + 1} de {steps.length}
          </span>
        </div>
      </nav>
    </div>
  );
}

Stepper.propTypes = {
  steps: PropTypes.arrayOf(PropTypes.string).isRequired,
  currentStep: PropTypes.number.isRequired,
  onStepClick: PropTypes.func
};

export default Stepper;
