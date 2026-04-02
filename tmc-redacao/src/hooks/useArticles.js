import { useQuery } from '@tanstack/react-query';
import { useRef } from 'react';
import { getArticles } from '../services/api';

/**
 * TanStack Query hook for fetching paginated articles with filters.
 * Maintains an internal cursor map for O(1) sequential page navigation.
 * When filters change, cursor state resets (per D-05/D-08).
 * Non-sequential page jumps (no cursor available) fall back to OFFSET.
 *
 * @param {Object} filters - Active filter values (category, source, search, tag, max_hours, classification, order_by)
 * @param {number} page - Current page number (1-based)
 * @param {number} [limit=20] - Items per page
 * @param {Object} [options={}] - Additional options
 * @param {boolean} [options.skipFacets=false] - Skip facet counts (useful for page > 1)
 * @returns {import('@tanstack/react-query').UseQueryResult} Query result with data, isLoading, error, etc.
 */
export function useArticlesQuery(filters, page, limit = 20, options = {}) {
  const { skipFacets = false } = options;

  // D-05: Internal cursor map -- stores cursors keyed by page number
  const cursorMapRef = useRef({});
  const prevFiltersRef = useRef(null);

  // D-08: Reset cursor map when filters change
  const filtersKey = JSON.stringify(filters);
  if (prevFiltersRef.current !== null && prevFiltersRef.current !== filtersKey) {
    cursorMapRef.current = {};
  }
  prevFiltersRef.current = filtersKey;

  // D-04: Use cursor for sequential navigation, OFFSET for non-sequential jumps
  const cursor = cursorMapRef.current[page] || null;

  return useQuery({
    queryKey: ['articles', { ...filters, page, limit, skipFacets }],
    queryFn: async ({ signal }) => {
      const params = {
        page,
        limit,
        skip_facets: skipFacets || page > 1,
        ...filters,
      };

      // Add cursor if available (sequential navigation)
      if (cursor) {
        params.cursor = cursor;
      }

      // Remove empty/null filter values so they don't appear as query params
      Object.keys(params).forEach(key => {
        if (params[key] === null || params[key] === undefined || params[key] === '') {
          delete params[key];
        }
      });

      const data = await getArticles(params, { signal });

      // Store cursors from response for next/prev page navigation
      if (data.nextCursor) {
        cursorMapRef.current[page + 1] = data.nextCursor;
      }
      if (data.prevCursor) {
        cursorMapRef.current[page - 1] = data.prevCursor;
      }

      return data;
    },
    placeholderData: (previousData) => previousData,
  });
}
