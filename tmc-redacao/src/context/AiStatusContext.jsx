/* eslint-disable react-refresh/only-export-components */
import { createContext, useState, useCallback, useEffect, useMemo, useContext, useRef } from 'react';
import PropTypes from 'prop-types';
import { getAiStatus, setAiStatus } from '../services/api';
import { useAuth } from './AuthContext';

const AiStatusContext = createContext(null);

const POLL_INTERVAL_MS = 60000; // 60 seconds

export function AiStatusProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [status, setStatus] = useState({
    aiPaused: false,
    pausedBy: null,
    pausedAt: null,
    estimatedSavings: 0,
    hoursPaused: 0,
    avgHourlyCost: 0,
  });
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getAiStatus();
      setStatus({
        aiPaused: data.paused ?? false,
        pausedBy: data.paused_by ?? null,
        pausedAt: data.paused_at ?? null,
        estimatedSavings: data.estimated_savings_usd ?? 0,
        hoursPaused: data.hours_paused ?? 0,
        avgHourlyCost: data.avg_hourly_cost_usd ?? 0,
      });
    } catch {
      // Silently ignore — status polling is best-effort
    }
  }, []);

  // Poll when authenticated
  useEffect(() => {
    if (!isAuthenticated) return;

    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isAuthenticated, fetchStatus]);

  const toggleAi = useCallback(async (paused) => {
    setLoading(true);
    try {
      await setAiStatus(paused);
      await fetchStatus();
    } finally {
      setLoading(false);
    }
  }, [fetchStatus]);

  const refreshStatus = useCallback(() => fetchStatus(), [fetchStatus]);

  const value = useMemo(() => ({
    ...status,
    toggleAi,
    loading,
    refreshStatus,
  }), [status, toggleAi, loading, refreshStatus]);

  return <AiStatusContext.Provider value={value}>{children}</AiStatusContext.Provider>;
}

AiStatusProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useAiStatus() {
  const ctx = useContext(AiStatusContext);
  if (!ctx) throw new Error('useAiStatus must be used within AiStatusProvider');
  return ctx;
}
