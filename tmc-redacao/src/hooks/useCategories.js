import { useQuery } from '@tanstack/react-query';
import { getCategories } from '../services/api';

/**
 * TanStack Query hook for fetching article categories with counts.
 * Categories change infrequently so we use a longer staleTime.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult} Query result with data, isLoading, error, etc.
 */
export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => getCategories(),
    staleTime: 5 * 60 * 1000, // 5 minutes — categories change infrequently
  });
}
