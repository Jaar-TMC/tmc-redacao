/* eslint-disable react-refresh/only-export-components */
import { createContext, useState, useCallback, useEffect, useMemo, useContext } from 'react';
import PropTypes from 'prop-types';
import { authLogin, authRefresh, authLogout, authGetMe, authUpdateMe, setAuthToken, clearAuthToken, getAuthToken } from '../services/auth';
import { registerAuthHandlers, resetRedirectGuard } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const isAuthenticated = !!user;

  // Register auth handlers for api.js 401 handling + auto-refresh
  useEffect(() => {
    registerAuthHandlers(
      () => getAuthToken(),
      () => { clearAuthToken(); setUser(null); },
      async () => {
        // Try to refresh the token silently
        try {
          const data = await authRefresh();
          if (data?.access_token) {
            setAuthToken(data.access_token);
            return data.access_token;
          }
        } catch {
          // Refresh failed
        }
        return null;
      }
    );
  }, []);

  // Silent refresh on mount — retry once to handle Azure cold starts
  useEffect(() => {
    const tryRefresh = async () => {
      const MAX_RETRIES = 1;
      const RETRY_DELAY_MS = 1000;

      // Retry loop covers only the authRefresh() call (network/cold-start failures)
      let token = null;
      for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        try {
          const data = await authRefresh();
          if (data?.access_token) {
            token = data.access_token;
            break; // Got a token — exit retry loop
          }
          // Server responded but no token — no point retrying
          clearAuthToken();
          setUser(null);
          return;
        } catch (err) {
          console.error('[Auth] Refresh attempt', attempt + 1, 'failed:', err.message || err);
          if (attempt < MAX_RETRIES) {
            await new Promise(r => setTimeout(r, RETRY_DELAY_MS));
          }
        }
      }

      if (!token) {
        // All retries exhausted — clear auth state
        clearAuthToken();
        setUser(null);
        return;
      }

      // Token refreshed — fetch user profile (not retried, token is already valid)
      try {
        setAuthToken(token);
        const userData = await authGetMe();
        setUser(userData);
      } catch (err) {
        console.error('[Auth] Failed to fetch user profile:', err.message || err);
        clearAuthToken();
        setUser(null);
      }
    };

    tryRefresh().finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email, password, rememberMe = false) => {
    setError(null);
    const data = await authLogin(email, password, rememberMe);
    setAuthToken(data.access_token);
    setUser(data.user);
    resetRedirectGuard(); // Allow 401 handling after re-login
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authLogout();
    } catch {
      // Ignore logout errors
    }
    clearAuthToken();
    setUser(null);
  }, []);

  const dismissWelcome = useCallback(async () => {
    await authUpdateMe({ is_new_user: false });
    setUser(prev => ({ ...prev, isNewUser: false }));
  }, []);

  const value = useMemo(() => ({
    user, isAuthenticated, isLoading, error,
    login, logout, dismissWelcome, setError
  }), [user, isAuthenticated, isLoading, error, login, logout, dismissWelcome]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
