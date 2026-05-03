import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentsApi } from '../api/agents'
import type { ApprovalFilters } from '../types/api'

export const APPROVAL_KEYS = {
  all: ['approvals'] as const,
  list: (filters: ApprovalFilters) => ['approvals', 'list', filters] as const,
  count: () => ['approvals', 'count'] as const,
}

export function useApprovalRequests(filters: ApprovalFilters = {}) {
  return useQuery({
    queryKey: APPROVAL_KEYS.list(filters),
    queryFn: () => agentsApi.getApprovalRequests(filters).then((r) => r.data),
  })
}

export function usePendingApprovalCount() {
  return useQuery({
    queryKey: APPROVAL_KEYS.count(),
    queryFn: () => agentsApi.getPendingApprovalCount().then((r) => r.data.count),
    refetchInterval: 30_000,
  })
}

export function useApproveRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      agentsApi.approveRequest(id, notes).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: APPROVAL_KEYS.all })
    },
  })
}

export function useRejectRequest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      agentsApi.rejectRequest(id, reason).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: APPROVAL_KEYS.all })
    },
  })
}
