import { apiClient } from './client'
import type { PaginatedResponse, ExceptionFilters } from '../types/api'
import type { StagedException, ExceptionStats } from '../types/models'

export const stagingApi = {
  getExceptions: (params: ExceptionFilters) =>
    apiClient.get<PaginatedResponse<StagedException>>('/staging/exceptions', { params }),

  getException: (id: string) =>
    apiClient.get<StagedException>(`/staging/exceptions/${id}`),

  approveException: (id: string, notes?: string) =>
    apiClient.post<StagedException>(`/staging/exceptions/${id}/approve`, { notes }),

  rejectException: (id: string, reason: string) =>
    apiClient.post<StagedException>(`/staging/exceptions/${id}/reject`, { reason }),

  matchException: (id: string, entityId: string, entityType: string) =>
    apiClient.post<StagedException>(`/staging/exceptions/${id}/match`, {
      entity_id: entityId,
      entity_type: entityType,
    }),

  bulkApprove: (ids: string[]) =>
    apiClient.post<{ approved: number; failed: number }>('/staging/exceptions/bulk-approve', {
      ids,
    }),

  getStats: () => apiClient.get<ExceptionStats>('/staging/stats'),
}
