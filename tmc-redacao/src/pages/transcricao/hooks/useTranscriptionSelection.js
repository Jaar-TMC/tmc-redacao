import { useState, useCallback, useMemo } from 'react';

/**
 * Hook unificado para gerenciar seleções na transcrição
 * Suporta seleção de cards completos e seleção de texto com marcação de citação
 *
 * @param {Array} initialSelection - IDs ou objetos inicialmente selecionados
 * @returns {Object} Estado e funções de seleção
 */
function useTranscriptionSelection(initialSelection = []) {
  // Seleções de cards (modo cards)
  // Estrutura: Set de IDs com Map para armazenar se é citação
  const [cardSelections, setCardSelections] = useState(new Map());

  // Seleções de texto (modo full)
  // Estrutura: Array de objetos { id, text, isQuote }
  const [textSelections, setTextSelections] = useState([]);

  // --- Métodos para cards ---

  /**
   * Adiciona ou remove um card da seleção
   */
  const toggleCard = useCallback((id) => {
    setCardSelections(prev => {
      const next = new Map(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.set(id, { isQuote: false });
      }
      return next;
    });
  }, []);

  /**
   * Marca ou desmarca um card como citação
   */
  const toggleCardQuote = useCallback((id) => {
    setCardSelections(prev => {
      const next = new Map(prev);
      if (next.has(id)) {
        const current = next.get(id);
        next.set(id, { ...current, isQuote: !current.isQuote });
      }
      return next;
    });
  }, []);

  /**
   * Verifica se um card está selecionado
   */
  const isCardSelected = useCallback((id) => {
    return cardSelections.has(id);
  }, [cardSelections]);

  /**
   * Verifica se um card está marcado como citação
   */
  const isCardQuote = useCallback((id) => {
    return cardSelections.get(id)?.isQuote || false;
  }, [cardSelections]);

  /**
   * Seleciona todos os cards fornecidos
   */
  const selectAllCards = useCallback((ids) => {
    const newMap = new Map();
    ids.forEach(id => {
      newMap.set(id, { isQuote: false });
    });
    setCardSelections(newMap);
  }, []);

  /**
   * Limpa todas as seleções de cards
   */
  const deselectAllCards = useCallback(() => {
    setCardSelections(new Map());
  }, []);

  // --- Métodos para seleção de texto ---

  /**
   * Adiciona uma seleção de texto
   * @param {string} text - Texto selecionado
   * @param {boolean} isQuote - Se é citação direta
   */
  const addTextSelection = useCallback((text, isQuote = false) => {
    setTextSelections(prev => {
      // Evitar duplicatas
      const exists = prev.some(s => s.text === text);
      if (exists) return prev;

      return [...prev, {
        id: Date.now().toString() + Math.random(),
        text,
        isQuote
      }];
    });
  }, []);

  /**
   * Remove uma seleção específica (card ou texto)
   */
  const removeSelection = useCallback((id) => {
    // Tentar remover de cards
    setCardSelections(prev => {
      const next = new Map(prev);
      next.delete(id);
      return next;
    });

    // Tentar remover de text selections
    setTextSelections(prev => prev.filter(s => s.id !== id));
  }, []);

  /**
   * Verifica se um texto está selecionado
   */
  const isTextSelected = useCallback((text) => {
    return textSelections.some(s => s.text === text);
  }, [textSelections]);

  /**
   * Limpa todas as seleções de texto
   */
  const clearTextSelections = useCallback(() => {
    setTextSelections([]);
  }, []);

  /**
   * Limpa todas as seleções (cards e texto)
   */
  const clearAll = useCallback(() => {
    setCardSelections(new Map());
    setTextSelections([]);
  }, []);

  // --- Métricas computadas ---

  const selectedCardIds = useMemo(() => {
    return Array.from(cardSelections.keys());
  }, [cardSelections]);

  const selectedCardsWithQuote = useMemo(() => {
    return Array.from(cardSelections.entries()).map(([id, data]) => ({
      id,
      ...data
    }));
  }, [cardSelections]);

  const cardCount = cardSelections.size;
  const textCount = textSelections.length;
  const totalCount = cardCount + textCount;
  const hasSelection = totalCount > 0;

  // Contar citações
  const quoteCount = useMemo(() => {
    const cardQuotes = Array.from(cardSelections.values()).filter(v => v.isQuote).length;
    const textQuotes = textSelections.filter(s => s.isQuote).length;
    return cardQuotes + textQuotes;
  }, [cardSelections, textSelections]);

  return {
    // Estados
    cardSelections: selectedCardsWithQuote,
    selectedCardIds,
    textSelections,

    // Métodos para cards
    toggleCard,
    toggleCardQuote,
    isCardSelected,
    isCardQuote,
    selectAllCards,
    deselectAllCards,

    // Métodos para texto
    addTextSelection,
    isTextSelected,
    clearTextSelections,

    // Métodos gerais
    removeSelection,
    clearAll,

    // Métricas
    cardCount,
    textCount,
    totalCount,
    quoteCount,
    hasSelection
  };
}

export default useTranscriptionSelection;
