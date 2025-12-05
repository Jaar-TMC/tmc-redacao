import { useState, useCallback } from 'react';

/**
 * Custom hook for managing boolean toggle state
 * @param {boolean} initialValue - Initial state value (default: false)
 * @returns {[boolean, Function, Function]} Tuple of [value, toggle, setValue]
 * @example
 * const [isOpen, toggleOpen, setIsOpen] = useToggle(false);
 */
const useToggle = (initialValue = false) => {
  const [value, setValue] = useState(initialValue);

  const toggle = useCallback(() => {
    setValue(v => !v);
  }, []);

  return [value, toggle, setValue];
};

export default useToggle;
