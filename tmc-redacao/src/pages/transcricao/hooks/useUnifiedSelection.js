import { useState, useCallback, useMemo } from 'react';

/**
 * Hook unificado para gerenciar selecoes em ambas visualizacoes (Topicos e Completa)
 *
 * Gerencia um array de selecoes com estrutura:
 * {
 *   id: string,
 *   text: string,
 *   source: 'card' | 'text',
 *   segmentId?: string,
 *   startTime?: string,
 * }
 *
 * @returns {Object} Estado e funcoes de selecao unificadas
 */
function useUnifiedSelection() {
  const [selections, setSelections] = useState([]);

  /**
   * Adiciona selecao de um card (visualizacao Topicos)
   * @param {string} segmentId - ID do segmento
   * @param {string} segmentText - Texto do segmento
   * @param {string} startTime - Timestamp de inicio
   */
  const addCardSelection = useCallback((segmentId, segmentText, startTime) => {
    setSelections(prev => {
      // Verificar se ja existe
      const exists = prev.some(s => s.source === 'card' && s.segmentId === segmentId);
      if (exists) {
        // Remover se ja existe (toggle)
        return prev.filter(s => !(s.source === 'card' && s.segmentId === segmentId));
      }

      // Adicionar nova selecao de card
      const newSelection = {
        id: `card-${segmentId}`,
        text: segmentText,
        source: 'card',
        segmentId,
        startTime,
        isQuote: false
      };

      return [...prev, newSelection];
    });
  }, []);

  /**
   * Adiciona selecao de texto livre (visualizacao Completa)
   * @param {string} text - Texto selecionado
   * @param {boolean} isQuote - Se é citação direta (default: false)
   */
  const addTextSelection = useCallback((text, isQuote = false) => {
    setSelections(prev => {
      // Verificar se ja existe texto identico
      const exists = prev.some(s => s.source === 'text' && s.text === text);
      if (exists) {
        return prev;
      }

      // Adicionar nova selecao de texto
      const newSelection = {
        id: `text-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        text,
        source: 'text',
        isQuote
      };

      return [...prev, newSelection];
    });
  }, []);

  /**
   * Remove uma selecao por ID
   * @param {string} id - ID da selecao
   */
  const removeSelection = useCallback((id) => {
    setSelections(prev => prev.filter(s => s.id !== id));
  }, []);

  /**
   * Remove selecao de texto especifico (para compatibilidade com highlight)
   * @param {string} text - Texto a remover
   */
  const removeTextSelection = useCallback((text) => {
    setSelections(prev => prev.filter(s => !(s.source === 'text' && s.text === text)));
  }, []);

  /**
   * Remove selecao de card especifico (para compatibilidade)
   * @param {string} segmentId - ID do segmento
   */
  const removeCardSelection = useCallback((segmentId) => {
    setSelections(prev => prev.filter(s => !(s.source === 'card' && s.segmentId === segmentId)));
  }, []);

  /**
   * Limpa todas as selecoes
   */
  const clearAll = useCallback(() => {
    setSelections([]);
  }, []);

  /**
   * Retorna todas as selecoes
   */
  const getSelections = useCallback(() => {
    return selections;
  }, [selections]);

  /**
   * Verifica se um card esta selecionado
   * @param {string} segmentId - ID do segmento
   */
  const isCardSelected = useCallback((segmentId) => {
    return selections.some(s => s.source === 'card' && s.segmentId === segmentId);
  }, [selections]);

  /**
   * Verifica se um texto esta selecionado
   * @param {string} text - Texto a verificar
   */
  const isTextSelected = useCallback((text) => {
    return selections.some(s => s.source === 'text' && s.text === text);
  }, [selections]);

  /**
   * Seleciona todos os cards de uma lista de segmentos
   * @param {Array} segments - Array de segmentos
   */
  const selectAllCards = useCallback((segments) => {
    setSelections(prev => {
      // Remover todas as selecoes de card existentes
      const nonCardSelections = prev.filter(s => s.source !== 'card');

      // Adicionar todas as novas selecoes de card
      const cardSelections = segments.map(seg => ({
        id: `card-${seg.id}`,
        text: seg.text,
        source: 'card',
        segmentId: seg.id,
        startTime: seg.startTime
      }));

      return [...nonCardSelections, ...cardSelections];
    });
  }, []);

  /**
   * Remove todas as selecoes de cards
   */
  const clearCardSelections = useCallback(() => {
    setSelections(prev => prev.filter(s => s.source !== 'card'));
  }, []);

  /**
   * Remove todas as selecoes de texto
   */
  const clearTextSelections = useCallback(() => {
    setSelections(prev => prev.filter(s => s.source !== 'text'));
  }, []);

  /**
   * Alterna o status de citação de uma seleção (card ou texto)
   * @param {string} id - ID da seleção (pode ser segmentId para cards)
   */
  const toggleQuote = useCallback((id) => {
    setSelections(prev => prev.map(s => {
      // Para cards, o id pode ser o segmentId
      if (s.segmentId === id || s.id === id) {
        return { ...s, isQuote: !s.isQuote };
      }
      return s;
    }));
  }, []);

  /**
   * Verifica se uma seleção é citação
   * @param {string} id - ID da seleção ou segmentId
   */
  const isQuote = useCallback((id) => {
    const selection = selections.find(s => s.segmentId === id || s.id === id);
    return selection?.isQuote || false;
  }, [selections]);

  // Contadores e estatisticas
  const selectedCount = useMemo(() => selections.length, [selections]);

  const cardSelectionCount = useMemo(
    () => selections.filter(s => s.source === 'card').length,
    [selections]
  );

  const textSelectionCount = useMemo(
    () => selections.filter(s => s.source === 'text').length,
    [selections]
  );

  const hasSelection = useMemo(() => selections.length > 0, [selections]);

  const totalWords = useMemo(() => {
    return selections.reduce((acc, s) => {
      const words = s.text.split(/\s+/).filter(w => w.trim()).length;
      return acc + words;
    }, 0);
  }, [selections]);

  const quoteCount = useMemo(() => {
    return selections.filter(s => s.isQuote).length;
  }, [selections]);

  // Retornar selecoes de cards como array de IDs (compatibilidade)
  const cardSelectionIds = useMemo(
    () => selections.filter(s => s.source === 'card').map(s => s.segmentId),
    [selections]
  );

  // Retornar selecoes de texto como array de objetos (compatibilidade)
  const textSelections = useMemo(
    () => selections.filter(s => s.source === 'text'),
    [selections]
  );

  return {
    // Estado
    selections,
    selectedCount,
    cardSelectionCount,
    textSelectionCount,
    hasSelection,
    totalWords,
    quoteCount,
    cardSelectionIds,
    textSelections,

    // Funcoes de adicao
    addCardSelection,
    addTextSelection,

    // Funcoes de remocao
    removeSelection,
    removeTextSelection,
    removeCardSelection,

    // Funcoes de limpeza
    clearAll,
    clearCardSelections,
    clearTextSelections,

    // Funcoes de verificacao
    isCardSelected,
    isTextSelected,
    isQuote,
    getSelections,

    // Funcoes de selecao em massa
    selectAllCards,

    // Funcoes de citacao
    toggleQuote
  };
}

export default useUnifiedSelection;
