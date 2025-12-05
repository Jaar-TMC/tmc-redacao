import { useState, useCallback } from 'react';

/**
 * Custom hook for managing form state and validation
 * @param {Object} initialValues - Initial form values
 * @param {Function} validate - Optional validation function
 * @returns {Object} Form state and handlers
 * @example
 * const { values, errors, handleChange, handleSubmit, resetForm } = useForm(
 *   { email: '', password: '' },
 *   (values) => { ... }
 * );
 */
const useForm = (initialValues = {}, validate = null) => {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  /**
   * Handle input change events
   * @param {Event|string} e - Event object or field name
   * @param {*} value - Value (if first param is field name)
   */
  const handleChange = useCallback((e, value) => {
    // Support both event objects and direct field/value pairs
    if (typeof e === 'string') {
      setValues(prev => ({ ...prev, [e]: value }));
    } else {
      const { name, value: eventValue, type, checked } = e.target;
      setValues(prev => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : eventValue
      }));
    }
  }, []);

  /**
   * Handle form submission
   * @param {Function} onSubmit - Callback function to execute on valid submit
   */
  const handleSubmit = useCallback((onSubmit) => {
    return async (e) => {
      if (e) e.preventDefault();

      setIsSubmitting(true);

      // Run validation if provided
      if (validate) {
        const validationErrors = validate(values);
        setErrors(validationErrors);

        if (Object.keys(validationErrors).length > 0) {
          setIsSubmitting(false);
          return;
        }
      }

      try {
        await onSubmit(values);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Form submission error:', error);
      } finally {
        setIsSubmitting(false);
      }
    };
  }, [values, validate]);

  /**
   * Reset form to initial values
   */
  const resetForm = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setIsSubmitting(false);
  }, [initialValues]);

  /**
   * Set multiple values at once
   */
  const setFormValues = useCallback((newValues) => {
    setValues(prev => ({ ...prev, ...newValues }));
  }, []);

  return {
    values,
    errors,
    isSubmitting,
    handleChange,
    handleSubmit,
    resetForm,
    setFormValues,
    setErrors
  };
};

export default useForm;
