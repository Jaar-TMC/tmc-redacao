import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,   // 2 minutes (matches RSS collection cadence)
      gcTime: 10 * 60 * 1000,      // 10 minutes garbage collection
      retry: 2,
      refetchOnWindowFocus: true,   // newsroom users switch tabs often
    },
  },
});
