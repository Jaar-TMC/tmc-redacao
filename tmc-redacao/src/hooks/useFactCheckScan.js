import { useState, useCallback, useRef } from 'react';
import { factCheckScan } from '../services/api';

/**
 * useFactCheckScan — manages fact-check scan state, API calls, and editor highlights.
 *
 * Usage:
 *   const { scanResult, isScanning, error, highlightsVisible, showModal, ... } = useFactCheckScan();
 *   // Trigger scan:
 *   runScan(editorRef.current?.editor, { articleText, articleTitle, sourceUrls, userArticleId });
 */
export function useFactCheckScan() {
  const [scanResult, setScanResult] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState(null);
  const [highlightsVisible, setHighlightsVisible] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [contentChangedSinceScan, setContentChangedSinceScan] = useState(false);
  const lastScannedContentRef = useRef(null);

  const runScan = useCallback(async (editor, { articleText, articleTitle, sourceUrls, userArticleId }) => {
    if (!articleText || articleText.length < 100) {
      setError('O texto precisa ter pelo menos 100 caracteres para verificação.');
      return null;
    }

    setIsScanning(true);
    setError(null);

    try {
      const result = await factCheckScan({
        articleText,
        articleTitle,
        sourceUrls,
        userArticleId,
      });

      setScanResult(result);
      lastScannedContentRef.current = articleText;
      setContentChangedSinceScan(false);

      // Apply highlights to editor
      if (editor && result.claims?.length > 0) {
        // Dynamic import to avoid circular dependencies
        const { applyFactCheckDecorations } = await import(
          '../components/editor/FactCheckHighlightPlugin'
        );
        applyFactCheckDecorations(editor, result.claims);
        setHighlightsVisible(true);

        // Auto-open modal if there are fabricated or unverifiable claims
        const hasFabricated = result.claims.some(c => c.verdict === 'fabricated');
        const hasUnverifiable = result.claims.some(c => c.verdict === 'unverifiable');
        if (hasFabricated || hasUnverifiable || result.safety_index < 50) {
          setShowModal(true);
        }
      }

      return result;
    } catch (err) {
      setError(err.message || 'Erro ao verificar o artigo.');
      return null;
    } finally {
      setIsScanning(false);
    }
  }, []);

  const toggleHighlights = useCallback(async (editor) => {
    if (!editor) return;
    const { toggleFactCheckVisibility } = await import(
      '../components/editor/FactCheckHighlightPlugin'
    );
    toggleFactCheckVisibility(editor);
    setHighlightsVisible(prev => !prev);
  }, []);

  const clearScan = useCallback(async (editor) => {
    if (editor) {
      const { clearFactCheckDecorations } = await import(
        '../components/editor/FactCheckHighlightPlugin'
      );
      clearFactCheckDecorations(editor);
    }
    setScanResult(null);
    setError(null);
    setHighlightsVisible(true);
    setContentChangedSinceScan(false);
    lastScannedContentRef.current = null;
  }, []);

  /** Call this when editor content changes to track staleness */
  const markContentChanged = useCallback(() => {
    if (lastScannedContentRef.current !== null) {
      setContentChangedSinceScan(true);
    }
  }, []);

  return {
    scanResult,
    isScanning,
    error,
    highlightsVisible,
    showModal,
    setShowModal,
    contentChangedSinceScan,
    runScan,
    toggleHighlights,
    clearScan,
    markContentChanged,
  };
}
