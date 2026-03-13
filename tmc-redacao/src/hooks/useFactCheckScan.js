import { useState, useCallback, useRef } from 'react';
import { factCheckScan, factCheckDeepVerify } from '../services/api';

/**
 * useFactCheckScan — manages fact-check scan state, API calls, and editor highlights.
 *
 * Usage:
 *   const { scanResult, isScanning, error, highlightsVisible, showModal, ... } = useFactCheckScan();
 *   // Trigger scan:
 *   runScan(editorRef.current?.editor, { articleText, articleTitle, sourceUrls, userArticleId });
 *   // Deep verify unverifiable claims:
 *   runDeepVerify(scanResult, articleTitle);
 */
const SEVERITY_WEIGHTS = { critical: 25, high: 15, medium: 8, low: 3 };

/**
 * Recalculate ASI after deep verify, mirroring backend calculate_asi().
 * Claim-dependent components (grounding 35%, severity 20%) are recalculated.
 * Other components (credibility 15%, corroboration 15%, factcheck 10%, opinion 5%)
 * are derived from the original ASI to keep them unchanged.
 */
function recalculateASI(claims, originalResult) {
  const factual = claims.filter(c => c.verdict !== 'opinion');
  if (!factual.length) return 85;

  // Component 1: Grounding (35%)
  const grounded = factual.filter(c => c.verdict === 'grounded').length;
  const groundingScore = (grounded / factual.length) * 100;

  // Component 2: Severity penalty (20%)
  let penalty = 0;
  for (const c of factual) {
    if (c.verdict === 'fabricated' || c.verdict === 'unverifiable') {
      penalty += SEVERITY_WEIGHTS[c.severity] || 5;
    }
  }
  const severityScore = Math.max(0, 100 - penalty);

  // Components 3-6: Extract from original ASI (45% total)
  // Original ASI = grounding*0.35 + severity*0.20 + other*0.45
  // We back-calculate the "other" portion from the original values
  const origClaims = originalResult.claims || [];
  const origFactual = origClaims.filter(c => c.verdict !== 'opinion');
  let origGrounding = 50, origSeverity = 50;
  if (origFactual.length) {
    const origGrounded = origFactual.filter(c => c.verdict === 'grounded').length;
    origGrounding = (origGrounded / origFactual.length) * 100;
    let origPenalty = 0;
    for (const c of origFactual) {
      if (c.verdict === 'fabricated' || c.verdict === 'unverifiable') {
        origPenalty += SEVERITY_WEIGHTS[c.severity] || 5;
      }
    }
    origSeverity = Math.max(0, 100 - origPenalty);
  }
  const origAsi = originalResult.safety_index || 50;
  const otherComponent = origAsi - origGrounding * 0.35 - origSeverity * 0.20;

  const asi = groundingScore * 0.35 + severityScore * 0.20 + otherComponent;
  return Math.max(0, Math.min(100, Math.round(asi)));
}

function getASILabel(asi) {
  if (asi >= 80) return 'seguro';
  if (asi >= 60) return 'atencao';
  if (asi >= 40) return 'risco';
  return 'critico';
}

export function useFactCheckScan() {
  const [scanResult, setScanResult] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isDeepVerifying, setIsDeepVerifying] = useState(false);
  const [error, setError] = useState(null);
  const [highlightsVisible, setHighlightsVisible] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [contentChangedSinceScan, setContentChangedSinceScan] = useState(false);
  const lastScannedContentRef = useRef(null);

  const runScan = useCallback(async (editor, { articleText, articleTitle, sourceUrls, userArticleId, forceRescan = false }) => {
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
        forceRescan,
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

  const runDeepVerify = useCallback(async (currentScanResult, articleTitle) => {
    if (!currentScanResult?.claims?.length) {
      setError('Nenhuma afirmação encontrada para verificar.');
      return null;
    }

    const unverifiableCount = currentScanResult.claims.filter(c => c.verdict === 'unverifiable').length;
    if (unverifiableCount === 0) {
      setError('Não há afirmações não-verificáveis para verificar.');
      return null;
    }

    setIsDeepVerifying(true);
    setError(null);

    try {
      const result = await factCheckDeepVerify({
        claims: currentScanResult.claims,
        articleTitle,
      });

      if (result.updated_claims?.length > 0) {
        // Merge updated claims back into scan result
        const updatedClaims = [...currentScanResult.claims];
        for (const update of result.updated_claims) {
          const idx = update.index;
          if (idx >= 0 && idx < updatedClaims.length) {
            updatedClaims[idx] = {
              ...updatedClaims[idx],
              verdict: update.verdict,
              evidence: update.evidence || updatedClaims[idx].evidence,
              sources: update.sources || updatedClaims[idx].sources,
              severity: update.severity || updatedClaims[idx].severity,
            };
          }
        }

        // Recalculate counts
        const grounded = updatedClaims.filter(c => c.verdict === 'grounded').length;
        const fabricated = updatedClaims.filter(c => c.verdict === 'fabricated').length;
        const unverifiable = updatedClaims.filter(c => c.verdict === 'unverifiable').length;

        // Recalculate ASI using same formula as backend
        const newAsi = recalculateASI(updatedClaims, currentScanResult);

        const updatedScanResult = {
          ...currentScanResult,
          claims: updatedClaims,
          grounded_claims: grounded,
          fabricated_claims: fabricated,
          unverifiable_claims: unverifiable,
          safety_index: newAsi,
          safety_label: getASILabel(newAsi),
          _deep_verify: {
            claims_resolved: result.claims_resolved,
            sources_searched: result.sources_searched,
            duration_ms: result.deep_verify_duration_ms,
          },
        };

        setScanResult(updatedScanResult);
        return updatedScanResult;
      }

      return currentScanResult;
    } catch (err) {
      setError(err.message || 'Erro na verificação profunda.');
      return null;
    } finally {
      setIsDeepVerifying(false);
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
    isDeepVerifying,
    error,
    highlightsVisible,
    showModal,
    setShowModal,
    contentChangedSinceScan,
    runScan,
    runDeepVerify,
    toggleHighlights,
    clearScan,
    markContentChanged,
  };
}
