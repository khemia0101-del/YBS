import { apiClient } from './client'
import type { CashForecastRun, StressTestRun } from '../types/models'
import type { PaginatedResponse } from '../types/api'

export interface StressTestParams {
  revenue_reduction_pct: number
  ar_delay_days: number
  payroll_increase_pct: number
  scenario_name: string
}

export const cashApi = {
  getLatestForecast: () =>
    apiClient.get<CashForecastRun>('/cash/forecast/latest'),

  getForecasts: (page = 1, pageSize = 10) =>
    apiClient.get<PaginatedResponse<CashForecastRun>>('/cash/forecast', {
      params: { page, page_size: pageSize },
    }),

  triggerForecast: () =>
    apiClient.post<CashForecastRun>('/cash/forecast/run'),

  runStressTest: (forecastRunId: string, params: StressTestParams) =>
    apiClient.post<StressTestRun>('/cash/stress-test', {
      forecast_run_id: forecastRunId,
      ...params,
    }),

  getStressTests: (forecastRunId: string) =>
    apiClient.get<StressTestRun[]>('/cash/stress-tests', {
      params: { forecast_run_id: forecastRunId },
    }),
}
