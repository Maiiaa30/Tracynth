import { useQuery } from '@tanstack/react-query';
import { apiRequest, asPage } from '../lib/api';
import type { ApiRecord, Page } from '../types/api';

export function useResource(path: string, refetchInterval?: number) {
  return useQuery({
    queryKey: ['resource', path],
    queryFn: async () => asPage(await apiRequest<Page<ApiRecord> | ApiRecord[]>(path)),
    refetchInterval,
  });
}
