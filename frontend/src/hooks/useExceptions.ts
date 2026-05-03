import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { stagingApi } from '../api/staging'
import { useExceptionStore } from '../stores/exceptionStore'
import type { ExceptionFilters } from '../types/api'

export const EXCEPTION_KEYS = {
  all: ['exceptions'] as const,
  list: (filters: ExceptionFilters) => ['exceptions', 'list', filters] as const,
  detail: (id: string) => ['exceptions', 'detail', id] as const,
  stats: () => ['exceptions', 'stats'] as const,
}

export function useExceptionList() {
  const {
    status,
    record_type,
    source_system,
    min_confidence,
    max_confidence,
    date_from,
    date_to,
    page,
    page_size,
    sort_by,
    sort_dir,
  } = useExceptionStore()

  const filters: ExceptionFilters = {
    ...(status && { status }),
    ...(record_type && { record_type }),
    ...(source_system && { source_system }),
    ...(min_confidence > 0 && { min_confidence }),
    ...(max_confidence < 1 && { max_confidence }),
    ...(date_from && { date_from }),
    ...(date_to && { date_to }),
    page,
    page_size,
    sort_by,
    sort_dir,
  }

  return useQuery({
    queryKey: EXCEPTION_KEYS.list(filters),
    queryFn: () => stagingApi.getExceptions(filters).then((r) => r.data),
  })
}

export function useException(id: string) {
  return useQuery({
    queryKey: EXCEPTION_KEYS.detail(id),
    queryFn: () => stagingApi.getException(id).then((r) => r.data),
    enabled: Boolean(id),
  })
}

export function useExceptionStats() {
  return useQuery({
    queryKey: EXCEPTION_KEYS.stats(),
    queryFn: () => stagingApi.getStats().then((r) => r.data),
    refetchInterval: 60_000,
  })
}

export function useApproveException() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      stagingApi.approveException(id, notes).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: EXCEPTION_KEYS.all })
      queryClient.setQueryData(EXCEPTION_KEYS.detail(data.id), data)
    },
  })
}

export function useRejectException() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      stagingApi.rejectException(id, reason).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: EXCEPTION_KEYS.all })
      queryClient.setQueryData(EXCEPTION_KEYS.detail(data.id), data)
    },
  })
}

export function useMatchException() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      entityId,
      entityType,
    }: {
      id: string
      entityId: string
      entityType: string
    }) => stagingApi.matchException(id, entityId, entityType).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: EXCEPTION_KEYS.all })
      queryClient.setQueryData(EXCEPTION_KEYS.detail(data.id), data)
    },
  })
}

export function useBulkApproveExceptions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => stagingApi.bulkApprove(ids).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EXCEPTION_KEYS.all })
    },
  })
}
