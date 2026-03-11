/**
 * API Cache - TTL-based in-memory cache with request deduplication
 *
 * Provides two main features:
 * 1. TTL cache: Stores API responses with configurable expiry
 * 2. Request deduplication: Prevents identical in-flight requests
 *
 * Usage:
 *   import { cachedFetch, prefetch, invalidate } from './apiCache';
 *
 *   // Cached fetch with 5-minute TTL
 *   const data = await cachedFetch('sources', () => getSources(), { ttl: 300000 });
 *
 *   // Prefetch data (fire-and-forget)
 *   prefetch('sources', () => getSources(), { ttl: 300000 });
 *
 *   // Invalidate a specific key
 *   invalidate('sources');
 */

// Cache store: { [key]: { data, timestamp, ttl } }
const _cache = {};

// In-flight request deduplication: { [key]: Promise }
const _inflight = {};

/**
 * Default TTL values by data type (milliseconds)
 */
export const CACHE_TTL = {
  /** Sources rarely change - cache for 10 minutes */
  SOURCES: 10 * 60 * 1000,
  /** Categories change with new articles - cache for 5 minutes */
  CATEGORIES: 5 * 60 * 1000,
  /** Trending tags update moderately - cache for 5 minutes */
  TRENDING: 5 * 60 * 1000,
  /** Feed articles for selector - cache for 3 minutes */
  FEED_ARTICLES: 3 * 60 * 1000,
  /** Short-lived cache for dynamic data */
  SHORT: 60 * 1000,
};

/**
 * Fetch with TTL cache and request deduplication.
 *
 * If cached data exists and is not expired, returns it immediately.
 * If an identical request is already in-flight, returns the same promise (dedup).
 * Otherwise, calls fetchFn and caches the result.
 *
 * @param {string} key - Unique cache key
 * @param {() => Promise<any>} fetchFn - Function that returns a promise
 * @param {Object} [options]
 * @param {number} [options.ttl=300000] - Time-to-live in ms (default: 5 min)
 * @param {boolean} [options.forceRefresh=false] - Bypass cache and force a fresh fetch
 * @returns {Promise<any>} Cached or fresh data
 */
export async function cachedFetch(key, fetchFn, options = {}) {
  const { ttl = 5 * 60 * 1000, forceRefresh = false } = options;

  // Check cache first (unless forcing refresh)
  if (!forceRefresh) {
    const entry = _cache[key];
    if (entry && Date.now() - entry.timestamp < entry.ttl) {
      return entry.data;
    }
  }

  // Deduplicate: if same request is in-flight, return the existing promise
  if (_inflight[key]) {
    return _inflight[key];
  }

  // Execute fetch and cache result
  const promise = fetchFn()
    .then((data) => {
      _cache[key] = { data, timestamp: Date.now(), ttl };
      return data;
    })
    .finally(() => {
      delete _inflight[key];
    });

  _inflight[key] = promise;
  return promise;
}

/**
 * Prefetch data into cache (fire-and-forget).
 * Silently catches errors. Useful for preloading on hover.
 *
 * @param {string} key - Unique cache key
 * @param {() => Promise<any>} fetchFn - Function that returns a promise
 * @param {Object} [options]
 * @param {number} [options.ttl=300000] - Time-to-live in ms
 */
export function prefetch(key, fetchFn, options = {}) {
  const { ttl = 5 * 60 * 1000 } = options;

  // Skip if already cached and valid
  const entry = _cache[key];
  if (entry && Date.now() - entry.timestamp < entry.ttl) {
    return;
  }

  // Skip if already in-flight
  if (_inflight[key]) {
    return;
  }

  // Fire and forget
  cachedFetch(key, fetchFn, { ttl }).catch(() => {
    // Silently ignore prefetch errors
  });
}

/**
 * Invalidate cache entries.
 *
 * @param {string} [key] - Specific key to invalidate. If omitted, clears all cache.
 */
export function invalidate(key) {
  if (key) {
    delete _cache[key];
  } else {
    // Clear all entries
    for (const k of Object.keys(_cache)) {
      delete _cache[k];
    }
  }
}

/**
 * Get cached data synchronously (without fetching).
 * Returns null if not cached or expired.
 *
 * @param {string} key - Cache key
 * @returns {any|null} Cached data or null
 */
export function getCached(key) {
  const entry = _cache[key];
  if (!entry) return null;
  if (Date.now() - entry.timestamp >= entry.ttl) {
    delete _cache[key];
    return null;
  }
  return entry.data;
}

/**
 * Check if a request is currently in-flight for a key.
 *
 * @param {string} key - Cache key
 * @returns {boolean}
 */
export function isInFlight(key) {
  return !!_inflight[key];
}
