import { useContext } from 'react';
import { OnboardingContext } from './OnboardingProvider';

/**
 * useOnboarding - Hook to access onboarding/tour functionality
 *
 * Returns:
 * - isActive: whether a tour is currently running
 * - activeTour: ID of the current tour
 * - currentStep: current step object
 * - currentStepIndex: 0-based index of current step
 * - totalSteps: total steps in current tour
 * - completedTours: object with completion status of all tours
 *
 * Actions:
 * - startTour(tourId): start a specific tour
 * - nextStep(): go to next step
 * - prevStep(): go to previous step
 * - skipTour(): skip/close the tour
 * - completeTour(): mark tour as completed
 * - resetTour(tourId): reset a specific tour to show again
 * - resetAllTours(): reset all tours
 * - goToStep(index): go to a specific step
 *
 * Helpers:
 * - shouldShowTour(tourId): check if tour should auto-show
 * - isTourCompleted(tourId): check if tour was completed
 * - TOUR_IDS: constants for tour IDs
 */
export const useOnboarding = () => {
  const context = useContext(OnboardingContext);

  if (!context) {
    throw new Error('useOnboarding must be used within an OnboardingProvider');
  }

  return context;
};

export default useOnboarding;
