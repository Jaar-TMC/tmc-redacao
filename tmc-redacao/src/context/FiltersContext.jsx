import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import PropTypes from 'prop-types';

const FiltersContext = createContext(undefined);

export const useFilters = () => {
  const context = useContext(FiltersContext);
  if (!context) {
    throw new Error('useFilters must be used within FiltersProvider');
  }
  return context;
};

export const FiltersProvider = ({ children }) => {
  const [filters, setFilters] = useState({
    searchQuery: '',
    category: null,
    source: null,
    period: 'today',
  });

  const updateFilter = useCallback((filterName, value) => {
    setFilters((prev) => ({
      ...prev,
      [filterName]: value,
    }));
  }, []);

  const updateFilters = useCallback((newFilters) => {
    setFilters((prev) => ({
      ...prev,
      ...newFilters,
    }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({
      searchQuery: '',
      category: null,
      source: null,
      period: 'today',
    });
  }, []);

  const value = useMemo(
    () => ({
      filters,
      updateFilter,
      updateFilters,
      resetFilters,
    }),
    [filters, updateFilter, updateFilters, resetFilters]
  );

  return (
    <FiltersContext.Provider value={value}>
      {children}
    </FiltersContext.Provider>
  );
};

FiltersProvider.propTypes = {
  children: PropTypes.node.isRequired,
};
