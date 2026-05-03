import { apiClient } from './client'
import type { QoERun, ESOPAdjustment } from '../types/models'
import type { PaginatedResponse } from '../types/api'

export const esopApi = {
  getLatestQoERun: () =>
    apiClient.get<QoERun>('/esop/qoe/latest'),

  getQoERuns: (page = 1, pageSize = 10) =>
    apiClient.get<PaginatedResponse<QoERun>>('/esop/qoe', {
      params: { page, page_size: pageSize },
    }),

  getAdjustments: (runId: string) =>
    apiClient.get<ESOPAdjustment[]>(`/esop/qoe/${runId}/adjustments`),

  approveAdjustment: (runId: string, adjustmentId: string, notes?: string) =>
    apiClient.post<ESOPAdjustment>(
      `/esop/qoe/${runId}/adjustments/${adjustmentId}/approve`,
      { notes }
    ),

  rejectAdjustment: (runId: string, adjustmentId: string, reason: string) =>
    apiClient.post<ESOPAdjustment>(
      `/esop/qoe/${runId}/adjustments/${adjustmentId}/reject`,
      { reason }
    ),

  exportQoEReport: (runId: string) =>
    apiClient.get(`/esop/qoe/${runId}/export`, { responseType: 'blob' }),
}
