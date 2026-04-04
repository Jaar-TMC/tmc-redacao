import { useQuery } from '@tanstack/react-query';
import { getTrendingTags } from '../services/api';

/**
 * TanStack Query hook for fetching trending tags ("Temas Quentes").
 * Tags change infrequently so we use a longer staleTime.
 *
 * @param {number} [limit=20] - Maximum number of trending tags to return
 * @returns {import('@tanstack/react-query').UseQueryResult} Query result with data, isLoading, error, etc.
 */
export function useTrendingTags(limit = 20) {
  return useQuery({
    queryKey: ['trending-tags', limit],
    queryFn: () => getTrendingTags({ limit }),
    staleTime: 5 * 60 * 1000, // 5 minutes — trending tags change infrequently
  });
}
