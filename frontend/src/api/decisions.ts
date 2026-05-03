import { apiClient } from './client'
import type { Decision } from '../types/models'
import type { PaginatedResponse } from '../types/api'

export interface DecisionFilters {
  status?: string
  label?: string
  decision_type?: string
  requires_approval?: boolean
  page?: number
  page_size?: number
}

export const decisionsApi = {
  getDecisions: (params: DecisionFilters = {}) =>
    apiClient.get<PaginatedResponse<Decision>>('/decisions', { params }),

  getDecision: (id: string) =>
    apiClient.get<Decision>(`/decisions/${id}`),

  approveDecision: (id: string, notes?: string) =>
    apiClient.post<Decision>(`/decisions/${id}/approve`, { notes }),

  rejectDecision: (id: string, reason: string) =>
    apiClient.post<Decision>(`/decisions/${id}/reject`, { reason }),

  getPendingApprovals: () =>
    apiClient.get<PaginatedResponse<Decision>>('/decisions', {
      params: { requires_approval: true, status: 'pending' },
    }),
}
