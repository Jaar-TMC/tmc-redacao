import { memo, useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useOnboarding } from './useOnboarding';
import OnboardingOverlay from './OnboardingOverlay';
import OnboardingStep from './OnboardingStep';

/**
 * OnboardingTour - Main component that renders the active tour
 *
 * Renders:
 * - Dark overlay with spotlight on target element
 * - Tooltip with step content and navigation
 *
 * Uses React Portal to render at document root level
 * to ensure proper stacking above all other content.
 *
 * WCAG 2.1 Compliance:
 * - Focus management (trap inside tooltip)
 * - Keyboard navigation (Tab, Escape, Arrow keys)
 * - Screen reader announcements via live region
 */
const OnboardingTour = memo(function OnboardingTour() {
  const {
    isActive,
    currentStep,
    currentStepIndex,
    totalSteps,
    nextStep,
    prevStep,
    skipTour
  } = useOnboarding();

  const [targetExists, setTargetExists] = useState(false);
  const skipAttemptedRef = useRef(false);
  const lastStepIndexRef = useRef(-1);
  const nextStepRef = useRef(nextStep);

  // Keep nextStep ref updated
  useEffect(() => {
    nextStepRef.current = nextStep;
  }, [nextStep]);

  // Reset skip flag when step changes
  useEffect(() => {
    if (currentStepIndex !== lastStepIndexRef.current) {
      skipAttemptedRef.current = false;
      lastStepIndexRef.current = currentStepIndex;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- resetting state on step transition
      setTargetExists(false); // Reset while checking new element
    }
  }, [currentStepIndex]);

  // Check if target element exists - syncs DOM state with React state
  useEffect(() => {
    if (!isActive || !currentStep?.target) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing DOM observation result
      setTargetExists(false);
      return;
    }

    // Small delay to allow DOM to render
    const checkElement = () => {
      const element = document.querySelector(currentStep.target);
      if (element) {
        setTargetExists(true);
        skipAttemptedRef.current = false;
      } else {
        setTargetExists(false);
        // Only auto-skip once per step to avoid infinite loops
        if (!skipAttemptedRef.current) {
          console.warn(`Onboarding: Element not found for selector "${currentStep.target}", skipping step`);
          skipAttemptedRef.current = true;
          // Use setTimeout and ref to avoid state update during render
          setTimeout(() => nextStepRef.current(), 50);
        }
      }
    };

    const timeoutId = setTimeout(checkElement, 150);
    return () => clearTimeout(timeoutId);
  }, [isActive, currentStep?.target, currentStepIndex]); // Use currentStepIndex instead of nextStep

  // Don't render if no active tour
  if (!isActive || !currentStep) {
    return null;
  }

  // Don't render if target doesn't exist yet
  if (!targetExists) {
    return null;
  }

  const content = (
    <>
      {/* Screen reader announcement */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        Tour: passo {currentStepIndex + 1} de {totalSteps}. {currentStep.title}: {currentStep.content}
      </div>

      {/* Dark overlay with spotlight */}
      <OnboardingOverlay
        targetSelector={currentStep.target}
        padding={8}
        borderRadius={8}
        onClickOutside={skipTour}
      />

      {/* Tooltip with step content */}
      <OnboardingStep
        step={currentStep}
        stepIndex={currentStepIndex}
        totalSteps={totalSteps}
        onNext={nextStep}
        onPrev={prevStep}
        onSkip={skipTour}
        targetSelector={currentStep.target}
      />
    </>
  );

  // Use portal to render at document root
  return createPortal(content, document.body);
});

export default OnboardingTour;
