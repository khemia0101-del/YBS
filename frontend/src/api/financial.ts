import { apiClient } from './client'
import type { ProfitabilityRun, DSOSnapshot } from '../types/models'
import type { PaginatedResponse } from '../types/api'

export interface ConcentrationEntry {
  customer_id: string
  customer_name: string
  revenue: number
  revenue_pct: number
  invoice_count: number
}

export const financialApi = {
  getLatestProfitabilityRun: () =>
    apiClient.get<ProfitabilityRun>('/financial/profitability/latest'),

  getProfitabilityRuns: (page = 1, pageSize = 10) =>
    apiClient.get<PaginatedResponse<ProfitabilityRun>>('/financial/profitability', {
      params: { page, page_size: pageSize },
    }),

  triggerProfitabilityRun: (periodStart: string, periodEnd: string) =>
    apiClient.post<ProfitabilityRun>('/financial/profitability/run', {
      period_start: periodStart,
      period_end: periodEnd,
    }),

  getDSOHistory: (limit = 12) =>
    apiClient.get<DSOSnapshot[]>('/financial/dso', { params: { limit } }),

  getConcentrationRisk: () =>
    apiClient.get<ConcentrationEntry[]>('/financial/concentration'),
}
