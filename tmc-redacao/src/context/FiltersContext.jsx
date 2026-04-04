/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback } from 'react';
import PropTypes from 'prop-types';

const DEFAULT_FILTERS = {
  searchQuery: '',
  tag: null,
  category: null,
  source: null,
  urgency: 1,
  scoreClassification: null,
  sortOrder: 'newest',
};

// Split contexts: state changes frequently, dispatch is stable
const FiltersStateContext = createContext(undefined);
const FiltersDispatchContext = createContext(undefined);

/**
 * Subscribe to filter state only. Components using this will re-render
 * when any filter value changes, but NOT when dispatch functions change
 * (they never do — they are stable refs).
 */
export const useFilterState = () => {
  const state = useContext(FiltersStateContext);
  if (state === undefined) {
    throw new Error('useFilterState must be used within FiltersProvider');
  }
  return state;
};

/**
 * Subscribe to dispatch actions only. Components using this will NEVER
 * re-render due to filter value changes — ideal for reset buttons,
 * action-only controls, or parent wrappers.
 */
export const useFilterDispatch = () => {
  const dispatch = useContext(FiltersDispatchContext);
  if (dispatch === undefined) {
    throw new Error('useFilterDispatch must be used within FiltersProvider');
  }
  return dispatch;
};

/**
 * Convenience hook to read a single filter value by name.
 * Still re-renders on any filter change (context-level granularity),
 * but makes consumer code cleaner for single-value reads.
 *
 * @param {string} filterName - Key from the filters object
 * @returns {*} The current value of that filter
 */
export const useFilterValue = (filterName) => {
  const filters = useFilterState();
  return filters[filterName];
};

/**
 * Backward-compatible hook. Returns the same shape as before:
 * { filters, updateFilter, updateFilters, resetFilters }
 *
 * Existing consumers keep working without any changes.
 */
export const useFilters = () => {
  const filters = useFilterState();
  const dispatch = useFilterDispatch();
  return { filters, ...dispatch };
};

export const FiltersProvider = ({ children }) => {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  const updateFilter = useCallback((filterName, value) => {
    setFilters((prev) => {
      if (prev[filterName] === value) return prev;
      return { ...prev, [filterName]: value };
    });
  }, []);

  const updateFilters = useCallback((newFilters) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
    }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  // Dispatch object is stable — all values are useCallback with [] deps.
  // We intentionally keep a single object ref via useState-init pattern
  // so FiltersDispatchContext never triggers re-renders.
  const [dispatch] = useState(() => ({
    updateFilter,
    updateFilters,
    resetFilters,
  }));

  return (
    <FiltersStateContext.Provider value={filters}>
      <FiltersDispatchContext.Provider value={dispatch}>
        {children}
      </FiltersDispatchContext.Provider>
    </FiltersStateContext.Provider>
  );
};

FiltersProvider.propTypes = {
  children: PropTypes.node.isRequired,
};
