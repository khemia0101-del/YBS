import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cashApi, type StressTestParams } from '../api/cash'
import { CashForecastChart } from '../components/cash/CashForecastChart'
import { PayrollCoverageBar } from '../components/cash/PayrollCoverageBar'
import { MoneyDisplay } from '../components/common/MoneyDisplay'
import { RefreshCw, Play, AlertTriangle } from 'lucide-react'
import { format } from 'date-fns'

export function CashForecastPage() {
  const queryClient = useQueryClient()
  const [showStressForm, setShowStressForm] = useState(false)
  const [stressParams, setStressParams] = useState<Omit<StressTestParams, 'scenario_name'>>({
    revenue_reduction_pct: 10,
    ar_delay_days: 15,
    payroll_increase_pct: 5,
  })

  const { data: forecast, isLoading } = useQuery({
    queryKey: ['cash', 'latest'],
    queryFn: () => cashApi.getLatestForecast().then((r) => r.data),
    staleTime: 5 * 60_000,
  })

  const triggerForecast = useMutation({
    mutationFn: () => cashApi.triggerForecast(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cash'] }),
  })

  const runStressTest = useMutation({
    mutationFn: () =>
      cashApi.runStressTest(forecast!.id, {
        ...stressParams,
        scenario_name: `Stress: -${stressParams.revenue_reduction_pct}% rev`,
      }),
    onSuccess: () => {
      setShowStressForm(false)
      queryClient.invalidateQueries({ queryKey: ['cash'] })
    },
  })

  const negativeWeeks = forecast?.weeks.filter((w) => w.ending_cash < 0) ?? []

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">13-Week Cash Forecast</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Rolling cash flow projection with payroll coverage tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowStressForm((v) => !v)}
            className="btn-secondary flex items-center gap-2"
          >
            <AlertTriangle className="w-4 h-4" />
            Stress Test
          </button>
          <button
            type="button"
            onClick={() => triggerForecast.mutate()}
            disabled={triggerForecast.isPending}
            className="btn-primary flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${triggerForecast.isPending ? 'animate-spin' : ''}`} />
            Re-run Forecast
          </button>
        </div>
      </div>

      {/* Stress test panel */}
      {showStressForm && (
        <div className="card px-5 py-5 border-amber-300 bg-amber-50">
          <h3 className="font-semibold text-slate-900 mb-4">Stress Test Parameters</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="label">Revenue Reduction %</label>
              <input
                type="number"
                className="input"
                min={0}
                max={100}
                value={stressParams.revenue_reduction_pct}
                onChange={(e) =>
                  setStressParams((p) => ({
                    ...p,
                    revenue_reduction_pct: Number(e.target.value),
                  }))
                }
              />
            </div>
            <div>
              <label className="label">AR Delay (days)</label>
              <input
                type="number"
                className="input"
                min={0}
                max={90}
                value={stressParams.ar_delay_days}
                onChange={(e) =>
                  setStressParams((p) => ({ ...p, ar_delay_days: Number(e.target.value) }))
                }
              />
            </div>
            <div>
              <label className="label">Payroll Increase %</label>
              <input
                type="number"
                className="input"
                min={0}
                max={50}
                value={stressParams.payroll_increase_pct}
                onChange={(e) =>
                  setStressParams((p) => ({
                    ...p,
                    payroll_increase_pct: Number(e.target.value),
                  }))
                }
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              disabled={runStressTest.isPending || !forecast}
              onClick={() => runStressTest.mutate()}
              className="btn-primary flex items-center gap-2"
            >
              <Play className="w-4 h-4" />
              {runStressTest.isPending ? 'Running…' : 'Run Stress Test'}
            </button>
            <button
              type="button"
              onClick={() => setShowStressForm(false)}
              className="btn-secondary"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-4">
          <div className="card h-80 animate-pulse bg-slate-100" />
          <div className="card h-24 animate-pulse bg-slate-100" />
        </div>
      ) : !forecast ? (
        <div className="card p-10 text-center text-slate-500">
          No cash forecast available. Click &quot;Re-run Forecast&quot; to generate.
        </div>
      ) : (
        <>
          {/* Warning for negative weeks */}
          {negativeWeeks.length > 0 && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-300 rounded-lg px-4 py-3">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-900">
                  {negativeWeeks.length} week{negativeWeeks.length !== 1 ? 's' : ''} with negative
                  cash balance
                </p>
                <p className="text-xs text-red-700 mt-0.5">
                  Weeks:{' '}
                  {negativeWeeks
                    .map((w) => `Wk ${w.week_number} (${format(new Date(w.week_start), 'MMM d')})`)
                    .join(', ')}
                </p>
              </div>
            </div>
          )}

          {/* Summary stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="card px-4 py-3">
              <p className="text-xs text-slate-500 font-medium">Beginning Cash</p>
              <MoneyDisplay amount={forecast.beginning_cash} colorize={false} size="lg" />
            </div>
            <div className="card px-4 py-3">
              <p className="text-xs text-slate-500 font-medium">Min Ending Cash</p>
              <MoneyDisplay amount={forecast.min_ending_cash} size="lg" />
            </div>
            <div className="card px-4 py-3">
              <p className="text-xs text-slate-500 font-medium">Forecast Date</p>
              <p className="text-base font-semibold text-slate-900">
                {format(new Date(forecast.run_date), 'MMM d, yyyy')}
              </p>
            </div>
            <div className="card px-4 py-3">
              <p className="text-xs text-slate-500 font-medium">Status</p>
              <p className="text-base font-semibold text-slate-900 capitalize">
                {forecast.status}
              </p>
            </div>
          </div>

          {/* Main chart */}
          <div className="card px-5 py-5">
            <h3 className="font-semibold text-slate-900 mb-4">Weekly Cash Flow</h3>
            <CashForecastChart weeks={forecast.weeks} />
          </div>

          {/* Payroll coverage */}
          <PayrollCoverageBar forecast={forecast} />

          {/* Weekly detail table */}
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200">
              <h3 className="font-semibold text-slate-900">Weekly Detail</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    {['Week', 'Start', 'Beginning Cash', 'Inflows', 'Outflows', 'Net', 'Ending Cash', 'Payroll'].map(
                      (h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide whitespace-nowrap"
                        >
                          {h}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {forecast.weeks.map((week) => (
                    <tr
                      key={week.id}
                      className={week.ending_cash < 0 ? 'bg-red-50' : ''}
                    >
                      <td className="px-4 py-2.5 text-sm font-medium">{week.week_number}</td>
                      <td className="px-4 py-2.5 text-sm text-slate-600">
                        {format(new Date(week.week_start), 'MMM d')}
                      </td>
                      <td className="px-4 py-2.5">
                        <MoneyDisplay amount={week.beginning_cash} colorize={false} size="sm" />
                      </td>
                      <td className="px-4 py-2.5">
                        <MoneyDisplay amount={week.inflows} colorize={false} size="sm" />
                      </td>
                      <td className="px-4 py-2.5">
                        <MoneyDisplay amount={-week.outflows} size="sm" />
                      </td>
                      <td className="px-4 py-2.5">
                        <MoneyDisplay amount={week.net_cash} size="sm" />
                      </td>
                      <td className="px-4 py-2.5">
                        <MoneyDisplay amount={week.ending_cash} size="sm" />
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={`text-xs font-medium ${
                            week.payroll_covered ? 'text-green-700' : 'text-red-600'
                          }`}
                        >
                          {week.payroll_covered ? 'Covered' : 'Gap'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
