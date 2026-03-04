import { createContext, useState, useCallback, useEffect, useMemo, useContext } from 'react';
import PropTypes from 'prop-types';
import { authLogin, authRefresh, authLogout, authGetMe, authUpdateMe, setAuthToken, clearAuthToken, getAuthToken } from '../services/auth';
import { registerAuthHandlers } from '../services/api';

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

  // Silent refresh on mount
  useEffect(() => {
    const tryRefresh = async () => {
      try {
        const data = await authRefresh();
        if (data?.access_token) {
          setAuthToken(data.access_token);
          const userData = await authGetMe();
          setUser(userData);
        }
      } catch {
        // Refresh failed - user not authenticated, that's OK
      } finally {
        setIsLoading(false);
      }
    };
    tryRefresh();
  }, []);

  const login = useCallback(async (email, password, rememberMe = false) => {
    setError(null);
    const data = await authLogin(email, password, rememberMe);
    setAuthToken(data.access_token);
    setUser(data.user);
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
