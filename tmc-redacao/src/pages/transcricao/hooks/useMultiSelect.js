import { useState, useCallback, useMemo } from 'react';

/**
 * Hook para gerenciar seleção múltipla de itens
 * @param {Array} initialSelection - IDs inicialmente selecionados
 * @returns {Object} Estado e funções de seleção
 */
function useMultiSelect(initialSelection = []) {
  const [selectedIds, setSelectedIds] = useState(new Set(initialSelection));

  const toggle = useCallback((id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const select = useCallback((id) => {
    setSelectedIds(prev => new Set([...prev, id]));
  }, []);

  const deselect = useCallback((id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const selectAll = useCallback((ids) => {
    setSelectedIds(new Set(ids));
  }, []);

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isSelected = useCallback((id) => {
    return selectedIds.has(id);
  }, [selectedIds]);

  const selectedArray = useMemo(() => {
    return Array.from(selectedIds);
  }, [selectedIds]);

  return {
    selectedIds: selectedArray,
    selectedCount: selectedIds.size,
    toggle,
    select,
    deselect,
    selectAll,
    deselectAll,
    isSelected,
    hasSelection: selectedIds.size > 0
  };
}

export default useMultiSelect;
