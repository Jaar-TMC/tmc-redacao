import { useState, useCallback, useMemo } from 'react';

/**
 * Hook para gerenciar fluxo de steps/wizard
 * @param {number} totalSteps - Número total de etapas
 * @param {number} initialStep - Etapa inicial (default: 1)
 * @returns {Object} Estado e funções de navegação
 */
function useSteps(totalSteps, initialStep = 1) {
  const [currentStep, setCurrentStep] = useState(initialStep);

  const goToStep = useCallback((step) => {
    if (step >= 1 && step <= totalSteps) {
      setCurrentStep(step);
    }
  }, [totalSteps]);

  const nextStep = useCallback(() => {
    setCurrentStep(prev => Math.min(prev + 1, totalSteps));
  }, [totalSteps]);

  const prevStep = useCallback(() => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
  }, []);

  const reset = useCallback(() => {
    setCurrentStep(initialStep);
  }, [initialStep]);

  const progress = useMemo(() => {
    return Math.round((currentStep / totalSteps) * 100);
  }, [currentStep, totalSteps]);

  return {
    currentStep,
    totalSteps,
    progress,
    isFirstStep: currentStep === 1,
    isLastStep: currentStep === totalSteps,
    goToStep,
    nextStep,
    prevStep,
    reset
  };
}

export default useSteps;
