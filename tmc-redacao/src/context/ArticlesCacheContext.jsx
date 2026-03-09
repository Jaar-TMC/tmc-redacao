/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useCallback, useRef, useMemo } from 'react';
import PropTypes from 'prop-types';

const ArticlesCacheContext = createContext(null);

const CACHE_TTL = 5 * 60 * 1000; // 5 minutos
const MAX_CACHE_ENTRIES = 50; // Evict oldest entries beyond this

export function ArticlesCacheProvider({ children }) {
  // Use refs instead of state to avoid re-renders on cache updates
  const cacheRef = useRef({});
  const trendingCacheRef = useRef({});
  const fetchingRef = useRef({});

  // Gera uma chave única baseada nos filtros
  const getCacheKey = useCallback((filters, page) => {
    return JSON.stringify({
      searchQuery: filters.searchQuery || '',
      tag: filters.tag || null,
      category: filters.category || null,
      source: filters.source || null,
      urgency: filters.urgency || null,
      scoreClassification: filters.scoreClassification || null,
      sortOrder: filters.sortOrder || 'newest',
      page: page || 1
    });
  }, []);

  // Evict oldest cache entries if over limit
  const evictIfNeeded = useCallback((cache) => {
    const keys = Object.keys(cache);
    if (keys.length <= MAX_CACHE_ENTRIES) return;

    // Sort by timestamp ascending (oldest first)
    const sorted = keys.sort((a, b) => (cache[a].timestamp || 0) - (cache[b].timestamp || 0));
    const toEvict = sorted.slice(0, keys.length - MAX_CACHE_ENTRIES);
    for (const key of toEvict) {
      delete cache[key];
    }
  }, []);

  // Obtém dados do cache (reads ref - no re-render)
  const getCachedData = useCallback((filters, page) => {
    const key = getCacheKey(filters, page);
    const entry = cacheRef.current[key];
    if (!entry) return null;
    if (Date.now() - entry.timestamp >= CACHE_TTL) {
      delete cacheRef.current[key];
      return null;
    }
    return entry.data;
  }, [getCacheKey]);

  // Salva dados no cache (writes ref - no re-render)
  const setCachedData = useCallback((filters, page, data) => {
    const key = getCacheKey(filters, page);
    cacheRef.current[key] = {
      data,
      timestamp: Date.now()
    };
    evictIfNeeded(cacheRef.current);
  }, [getCacheKey, evictIfNeeded]);

  // Invalida cache
  const invalidateCache = useCallback((filters = null, page = null) => {
    if (filters && page) {
      const key = getCacheKey(filters, page);
      delete cacheRef.current[key];
    } else {
      cacheRef.current = {};
    }
  }, [getCacheKey]);

  // Verifica se já está fazendo fetch
  const isCurrentlyFetching = useCallback((filters, page) => {
    const key = getCacheKey(filters, page);
    return fetchingRef.current[key] === true;
  }, [getCacheKey]);

  const setFetching = useCallback((filters, page, isFetching) => {
    const key = getCacheKey(filters, page);
    fetchingRef.current[key] = isFetching;
  }, [getCacheKey]);

  // ========== Trending Tags Cache ==========

  const getCachedTrending = useCallback((key = 'all') => {
    const entry = trendingCacheRef.current[key];
    if (!entry) return null;
    if (Date.now() - entry.timestamp > CACHE_TTL) {
      delete trendingCacheRef.current[key];
      return null;
    }
    return entry.data;
  }, []);

  const setCachedTrending = useCallback((data, key = 'all') => {
    trendingCacheRef.current[key] = {
      data,
      timestamp: Date.now()
    };
  }, []);

  const invalidateTrendingCache = useCallback(() => {
    trendingCacheRef.current = {};
  }, []);

  // Memoize value object - all callbacks are stable (empty deps)
  const value = useMemo(() => ({
    getCachedData,
    setCachedData,
    invalidateCache,
    isCurrentlyFetching,
    setFetching,
    getCachedTrending,
    setCachedTrending,
    invalidateTrendingCache
  }), [getCachedData, setCachedData, invalidateCache, isCurrentlyFetching, setFetching, getCachedTrending, setCachedTrending, invalidateTrendingCache]);

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
