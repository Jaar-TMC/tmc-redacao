import { createContext, useContext, useState, useCallback, useRef } from 'react';
import PropTypes from 'prop-types';

const ArticlesCacheContext = createContext(null);

const CACHE_TTL = 5 * 60 * 1000; // 5 minutos

export function ArticlesCacheProvider({ children }) {
  const [cache, setCache] = useState({});
  const [trendingCache, setTrendingCache] = useState(null);
  const lastFetchRef = useRef({});

  // Gera uma chave única baseada nos filtros
  const getCacheKey = useCallback((filters, page) => {
    return JSON.stringify({
      searchQuery: filters.searchQuery || '',
      tag: filters.tag || null,
      category: filters.category || null,
      source: filters.source || null,
      page: page || 1
    });
  }, []);

  // Verifica se o cache é válido (não expirou)
  const isCacheValid = useCallback((key) => {
    const entry = cache[key];
    if (!entry) return false;
    return Date.now() - entry.timestamp < CACHE_TTL;
  }, [cache]);

  // Obtém dados do cache
  const getCachedData = useCallback((filters, page) => {
    const key = getCacheKey(filters, page);
    if (isCacheValid(key)) {
      return cache[key].data;
    }
    return null;
  }, [cache, getCacheKey, isCacheValid]);

  // Salva dados no cache
  const setCachedData = useCallback((filters, page, data) => {
    const key = getCacheKey(filters, page);
    setCache(prev => ({
      ...prev,
      [key]: {
        data,
        timestamp: Date.now()
      }
    }));
  }, [getCacheKey]);

  // Invalida cache de uma chave específica ou todo o cache
  const invalidateCache = useCallback((filters = null, page = null) => {
    if (filters && page) {
      const key = getCacheKey(filters, page);
      setCache(prev => {
        const newCache = { ...prev };
        delete newCache[key];
        return newCache;
      });
    } else {
      setCache({});
    }
  }, [getCacheKey]);

  // Verifica se já está fazendo fetch para evitar duplicatas
  const isCurrentlyFetching = useCallback((filters, page) => {
    const key = getCacheKey(filters, page);
    return lastFetchRef.current[key] === true;
  }, [getCacheKey]);

  const setFetching = useCallback((filters, page, isFetching) => {
    const key = getCacheKey(filters, page);
    lastFetchRef.current[key] = isFetching;
  }, [getCacheKey]);

  // ========== Trending Tags Cache ==========

  // Obtém trending tags do cache
  const getCachedTrending = useCallback(() => {
    if (!trendingCache) return null;
    if (Date.now() - trendingCache.timestamp > CACHE_TTL) return null;
    return trendingCache.data;
  }, [trendingCache]);

  // Salva trending tags no cache
  const setCachedTrending = useCallback((data) => {
    setTrendingCache({
      data,
      timestamp: Date.now()
    });
  }, []);

  // Invalida trending cache
  const invalidateTrendingCache = useCallback(() => {
    setTrendingCache(null);
  }, []);

  const value = {
    getCachedData,
    setCachedData,
    invalidateCache,
    isCacheValid,
    isCurrentlyFetching,
    setFetching,
    // Trending cache
    getCachedTrending,
    setCachedTrending,
    invalidateTrendingCache
  };

  return (
    <ArticlesCacheContext.Provider value={value}>
      {children}
    </ArticlesCacheContext.Provider>
  );
}

ArticlesCacheProvider.propTypes = {
  children: PropTypes.node.isRequired
};

export function useArticlesCache() {
  const context = useContext(ArticlesCacheContext);
  if (!context) {
    throw new Error('useArticlesCache must be used within ArticlesCacheProvider');
  }
  return context;
}
