import { useState } from 'react';
import Stepper from './Stepper';

/**
 * EXEMPLO DE USO DO COMPONENTE STEPPER
 *
 * Este arquivo demonstra diferentes cenários de uso do componente Stepper
 * no fluxo de criação de matéria.
 */

// ============================================================================
// EXEMPLO 1: Uso Básico
// ============================================================================

function ExemploBasico() {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = ['Fonte', 'Texto-Base', 'Configurar', 'Editor'];

  return (
    <div className="p-8 bg-white">
      <h2 className="text-xl font-bold mb-4">Exemplo Básico</h2>

      <Stepper
        steps={steps}
        currentStep={currentStep}
        onStepClick={(stepIndex) => {
          console.log(`Navegando para etapa: ${steps[stepIndex]}`);
          setCurrentStep(stepIndex);
        }}
      />

      <div className="mt-8 flex gap-4 justify-center">
        <button
          onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
          disabled={currentStep === 0}
          className="px-4 py-2 bg-gray-200 rounded-lg disabled:opacity-50"
        >
          Voltar
        </button>
        <button
          onClick={() => setCurrentStep(Math.min(steps.length - 1, currentStep + 1))}
          disabled={currentStep === steps.length - 1}
          className="px-4 py-2 bg-tmc-orange text-white rounded-lg disabled:opacity-50"
        >
          Continuar
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// EXEMPLO 2: Com Navegação por Rota
// ============================================================================

function ExemploComRotas() {
  // Simula o uso com React Router
  const steps = ['Fonte', 'Texto-Base', 'Configurar', 'Editor'];
  const currentStep = 2; // Simulando que está na etapa "Configurar"

  const stepRoutes = [
    '/criar',
    '/criar/texto-base',
    '/criar/configurar',
    '/criar/editor'
  ];

  const handleStepClick = (stepIndex) => {
    // Em produção, usar: navigate(stepRoutes[stepIndex])
    console.log(`Navegaria para: ${stepRoutes[stepIndex]}`);
  };

  return (
    <div className="p-8 bg-white">
      <h2 className="text-xl font-bold mb-4">Exemplo com Rotas</h2>

      <Stepper
        steps={steps}
        currentStep={currentStep}
        onStepClick={handleStepClick}
      />

      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <p className="text-sm text-medium-gray">
          <strong>Etapa atual:</strong> {steps[currentStep]} ({stepRoutes[currentStep]})
        </p>
        <p className="text-sm text-medium-gray mt-2">
          Clique em etapas anteriores para navegar de volta.
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// EXEMPLO 3: Diferentes Estados
// ============================================================================

function ExemploDiferentesEstados() {
  return (
    <div className="p-8 bg-white space-y-8">
      <h2 className="text-xl font-bold mb-4">Diferentes Estados do Stepper</h2>

      {/* Primeira etapa */}
      <div>
        <h3 className="text-sm font-semibold text-medium-gray mb-2">Primeira Etapa</h3>
        <Stepper
          steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
          currentStep={0}
          onStepClick={() => {}}
        />
      </div>

      {/* Segunda etapa */}
      <div>
        <h3 className="text-sm font-semibold text-medium-gray mb-2">Segunda Etapa</h3>
        <Stepper
          steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
          currentStep={1}
          onStepClick={() => {}}
        />
      </div>

      {/* Terceira etapa */}
      <div>
        <h3 className="text-sm font-semibold text-medium-gray mb-2">Terceira Etapa</h3>
        <Stepper
          steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
          currentStep={2}
          onStepClick={() => {}}
        />
      </div>

      {/* Última etapa */}
      <div>
        <h3 className="text-sm font-semibold text-medium-gray mb-2">Última Etapa</h3>
        <Stepper
          steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
          currentStep={3}
          onStepClick={() => {}}
        />
      </div>
    </div>
  );
}

// ============================================================================
// EXEMPLO 4: Com Validação de Etapa
// ============================================================================

function ExemploComValidacao() {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState([]);

  const steps = ['Fonte', 'Texto-Base', 'Configurar', 'Editor'];

  const handleNext = () => {
    // Validação simulada
    const isValid = Math.random() > 0.3; // 70% de chance de validar

    if (isValid) {
      setCompletedSteps([...completedSteps, currentStep]);
      setCurrentStep(Math.min(steps.length - 1, currentStep + 1));
    } else {
      alert('Preencha todos os campos obrigatórios antes de continuar.');
    }
  };

  const handleStepClick = (stepIndex) => {
    // Só permite navegar para etapas já completadas
    if (completedSteps.includes(stepIndex)) {
      setCurrentStep(stepIndex);
    }
  };

  return (
    <div className="p-8 bg-white">
      <h2 className="text-xl font-bold mb-4">Exemplo com Validação</h2>

      <Stepper
        steps={steps}
        currentStep={currentStep}
        onStepClick={handleStepClick}
      />

      <div className="mt-8 p-4 bg-blue-50 border-l-4 border-blue-500">
        <p className="text-sm text-blue-900">
          <strong>Etapas completadas:</strong>{' '}
          {completedSteps.length > 0
            ? completedSteps.map(i => steps[i]).join(', ')
            : 'Nenhuma'}
        </p>
      </div>

      <div className="mt-4 flex gap-4 justify-center">
        <button
          onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
          disabled={currentStep === 0}
          className="px-4 py-2 bg-gray-200 rounded-lg disabled:opacity-50"
        >
          Voltar
        </button>
        <button
          onClick={handleNext}
          disabled={currentStep === steps.length - 1}
          className="px-4 py-2 bg-tmc-orange text-white rounded-lg disabled:opacity-50"
        >
          Continuar
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// EXEMPLO 5: Responsividade (Desktop vs Mobile)
// ============================================================================

function ExemploResponsividade() {
  return (
    <div className="p-8 bg-white">
      <h2 className="text-xl font-bold mb-4">Teste de Responsividade</h2>

      <div className="space-y-8">
        {/* Desktop Preview */}
        <div className="border-2 border-gray-300 rounded-lg p-4">
          <p className="text-sm font-semibold text-medium-gray mb-4">
            Desktop (redimensione a janela para testar)
          </p>
          <Stepper
            steps={['Fonte', 'Texto-Base', 'Configurar', 'Editor']}
            currentStep={2}
            onStepClick={() => {}}
          />
        </div>

        <div className="mt-4 p-4 bg-yellow-50 border-l-4 border-yellow-500">
          <p className="text-sm text-yellow-900">
            <strong>Dica:</strong> Redimensione a janela do navegador para ver o stepper
            alternar entre os modos horizontal (desktop) e vertical (mobile).
          </p>
          <p className="text-sm text-yellow-900 mt-2">
            - <strong>Desktop (≥768px):</strong> Stepper horizontal com linhas conectoras
          </p>
          <p className="text-sm text-yellow-900">
            - <strong>Mobile (&lt;768px):</strong> Stepper vertical com indicadores de status
          </p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// EXEMPLO 6: Acessibilidade
// ============================================================================

function ExemploAcessibilidade() {
  const [currentStep, setCurrentStep] = useState(1);
  const steps = ['Fonte', 'Texto-Base', 'Configurar', 'Editor'];

  return (
    <div className="p-8 bg-white">
      <h2 className="text-xl font-bold mb-4">Teste de Acessibilidade</h2>

      <Stepper
        steps={steps}
        currentStep={currentStep}
        onStepClick={setCurrentStep}
      />

      <div className="mt-8 space-y-4">
        <div className="p-4 bg-green-50 border-l-4 border-green-500">
          <p className="text-sm font-semibold text-green-900 mb-2">
            Recursos de Acessibilidade:
          </p>
          <ul className="text-sm text-green-900 space-y-1 list-disc list-inside">
            <li>Navegação por teclado (Tab, Enter/Space)</li>
            <li>ARIA labels descritivos em cada etapa</li>
            <li>aria-current="step" na etapa atual</li>
            <li>Focus indicators visíveis (outline laranja)</li>
            <li>Status anunciados para leitores de tela</li>
            <li>Transições respeitam prefers-reduced-motion</li>
          </ul>
        </div>

        <div className="p-4 bg-blue-50 border-l-4 border-blue-500">
          <p className="text-sm font-semibold text-blue-900 mb-2">
            Teste com teclado:
          </p>
          <ul className="text-sm text-blue-900 space-y-1 list-disc list-inside">
            <li>Pressione <kbd className="px-2 py-1 bg-white rounded">Tab</kbd> para navegar entre etapas</li>
            <li>Pressione <kbd className="px-2 py-1 bg-white rounded">Enter</kbd> ou <kbd className="px-2 py-1 bg-white rounded">Space</kbd> para ativar uma etapa</li>
            <li>Observe o outline laranja ao focar em cada elemento</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// EXPORT EXAMPLES (para Storybook ou testes)
// ============================================================================

export default function StepperExamples() {
  return (
    <div className="space-y-12 bg-off-white p-8">
      <ExemploBasico />
      <hr className="border-light-gray" />
      <ExemploComRotas />
      <hr className="border-light-gray" />
      <ExemploDiferentesEstados />
      <hr className="border-light-gray" />
      <ExemploComValidacao />
      <hr className="border-light-gray" />
      <ExemploResponsividade />
      <hr className="border-light-gray" />
      <ExemploAcessibilidade />
    </div>
  );
}

// Export individual examples
export {
  ExemploBasico,
  ExemploComRotas,
  ExemploDiferentesEstados,
  ExemploComValidacao,
  ExemploResponsividade,
  ExemploAcessibilidade
};
