import { createContext, useState, useCallback, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { tourSteps, TOUR_IDS } from './tourSteps';

// Storage key for persisting tour state
const STORAGE_KEY = 'tmc-onboarding-v1';

// Context for onboarding state
export const OnboardingContext = createContext(null);

/**
 * OnboardingProvider - Context provider for the onboarding/tour system
 *
 * Manages:
 * - Active tour and current step
 * - Tour completion persistence
 * - Auto-trigger logic for first-time users
 */
export const OnboardingProvider = ({ children }) => {
  // Current active tour state
  const [activeTour, setActiveTour] = useState(null);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isActive, setIsActive] = useState(false);

  // Persisted tour completion state
  const [completedTours, setCompletedTours] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  // Persist completed tours to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(completedTours));
    } catch (error) {
      console.warn('Failed to persist onboarding state:', error);
    }
  }, [completedTours]);

  // Get current tour steps
  const currentTourSteps = useMemo(() => {
    return activeTour ? tourSteps[activeTour] || [] : [];
  }, [activeTour]);

  // Get current step
  const currentStep = useMemo(() => {
    return currentTourSteps[currentStepIndex] || null;
  }, [currentTourSteps, currentStepIndex]);

  // Check if a tour should auto-show (first time on this page)
  const shouldShowTour = useCallback((tourId) => {
    const tourState = completedTours[tourId];
    // Show if never seen or if explicitly reset
    return !tourState || tourState.reset;
  }, [completedTours]);

  // Start a specific tour
  const startTour = useCallback((tourId) => {
    if (!tourSteps[tourId]) {
      console.warn(`Tour "${tourId}" not found`);
      return;
    }

    setActiveTour(tourId);
    setCurrentStepIndex(0);
    setIsActive(true);

    // Clear reset flag if present
    if (completedTours[tourId]?.reset) {
      setCompletedTours(prev => ({
        ...prev,
        [tourId]: { ...prev[tourId], reset: false }
      }));
    }
  }, [completedTours]);

  // Complete the tour (defined before nextStep to use in dependency)
  const completeTour = useCallback(() => {
    if (activeTour) {
      setCompletedTours(prev => ({
        ...prev,
        [activeTour]: {
          completedAt: new Date().toISOString(),
          skipped: false
        }
      }));
    }
    setIsActive(false);
    setActiveTour(null);
    setCurrentStepIndex(0);
  }, [activeTour]);

  // Go to next step
  const nextStep = useCallback(() => {
    if (currentStepIndex < currentTourSteps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    } else {
      // Tour completed
      completeTour();
    }
  }, [currentStepIndex, currentTourSteps.length, completeTour]);

  // Go to previous step
  const prevStep = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  }, [currentStepIndex]);

  // Skip/close the tour
  const skipTour = useCallback(() => {
    if (activeTour) {
      setCompletedTours(prev => ({
        ...prev,
        [activeTour]: {
          completedAt: new Date().toISOString(),
          skipped: true
        }
      }));
    }
    setIsActive(false);
    setActiveTour(null);
    setCurrentStepIndex(0);
  }, [activeTour]);

  // Reset a specific tour (for restart)
  const resetTour = useCallback((tourId) => {
    setCompletedTours(prev => ({
      ...prev,
      [tourId]: { reset: true }
    }));
  }, []);

  // Reset all tours
  const resetAllTours = useCallback(() => {
    setCompletedTours({});
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  // Check if a tour has been completed
  const isTourCompleted = useCallback((tourId) => {
    const tourState = completedTours[tourId];
    return tourState && !tourState.reset;
  }, [completedTours]);

  // Go to a specific step
  const goToStep = useCallback((stepIndex) => {
    if (stepIndex >= 0 && stepIndex < currentTourSteps.length) {
      setCurrentStepIndex(stepIndex);
    }
  }, [currentTourSteps.length]);

  const value = useMemo(() => ({
    // State
    isActive,
    activeTour,
    currentStep,
    currentStepIndex,
    totalSteps: currentTourSteps.length,
    completedTours,

    // Actions
    startTour,
    nextStep,
    prevStep,
    skipTour,
    completeTour,
    resetTour,
    resetAllTours,
    goToStep,

    // Helpers
    shouldShowTour,
    isTourCompleted,

    // Constants
    TOUR_IDS
  }), [
    isActive,
    activeTour,
    currentStep,
    currentStepIndex,
    currentTourSteps.length,
    completedTours,
    startTour,
    nextStep,
    prevStep,
    skipTour,
    completeTour,
    resetTour,
    resetAllTours,
    goToStep,
    shouldShowTour,
    isTourCompleted
  ]);

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  );
};

OnboardingProvider.propTypes = {
  children: PropTypes.node.isRequired
};

export default OnboardingProvider;
