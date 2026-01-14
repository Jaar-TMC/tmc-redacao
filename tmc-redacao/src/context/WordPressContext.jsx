import { createContext, useContext, useMemo } from 'react';
import PropTypes from 'prop-types';

/**
 * WordPress Context
 *
 * Provides WordPress-specific configuration and user data to the React app.
 * When running in WordPress, this data comes from wp_localize_script.
 * When running standalone, provides fallback/default values.
 */

const WordPressContext = createContext(undefined);

/**
 * Hook to access WordPress context
 *
 * @returns {Object} WordPress configuration and user data
 */
export const useWordPress = () => {
  const context = useContext(WordPressContext);
  if (!context) {
    throw new Error('useWordPress must be used within WordPressProvider');
  }
  return context;
};

/**
 * Get configuration from WordPress (window.tmcRedacaoConfig)
 *
 * @returns {Object} Configuration object
 */
const getWordPressConfig = () => {
  if (typeof window !== 'undefined' && window.tmcRedacaoConfig) {
    return window.tmcRedacaoConfig;
  }

  // Fallback for standalone development
  return {
    user: {
      id: 0,
      displayName: 'Desenvolvedor',
      email: 'dev@tmc.com.br',
      roles: ['administrator'],
      avatar: null,
    },
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:7071/api',
    nonce: '',
    restNonce: '',
    pluginUrl: '',
    isWordPress: false,
    adminUrl: '',
    siteUrl: '',
  };
};

/**
 * WordPress Provider Component
 */
export const WordPressProvider = ({ children }) => {
  const value = useMemo(() => {
    const config = getWordPressConfig();

    return {
      // User information
      user: config.user,
      isAuthenticated: config.user?.id > 0,

      // WordPress-specific flags
      isWordPress: config.isWordPress || false,

      // API configuration
      apiBaseUrl: config.apiBaseUrl || '',

      // Security nonces
      nonce: config.nonce || '',
      restNonce: config.restNonce || '',

      // URLs
      pluginUrl: config.pluginUrl || '',
      adminUrl: config.adminUrl || '',
      siteUrl: config.siteUrl || '',

      // Helper to get full asset URL (for WordPress plugin assets)
      getAssetUrl: (path) => {
        if (config.pluginUrl) {
          return `${config.pluginUrl}assets/${path}`;
        }
        return path;
      },

      // Check if user has a specific role
      hasRole: (role) => {
        return config.user?.roles?.includes(role) || false;
      },

      // Check if user can perform an action (capability check)
      can: (capability) => {
        // In WordPress context, this would be handled server-side
        // Client-side we just check for admin role
        const adminCapabilities = ['manage_options', 'edit_posts', 'publish_posts'];
        if (adminCapabilities.includes(capability)) {
          return config.user?.roles?.includes('administrator') ||
                 config.user?.roles?.includes('editor');
        }
        return true;
      },
    };
  }, []);

  return (
    <WordPressContext.Provider value={value}>
      {children}
    </WordPressContext.Provider>
  );
};

WordPressProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export default WordPressContext;
