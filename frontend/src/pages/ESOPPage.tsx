import { useQuery, useMutation } from '@tanstack/react-query'
import { esopApi } from '../api/esop'
import { EBITDABridge } from '../components/esop/EBITDABridge'
import { AddBackTable } from '../components/esop/AddBackTable'
import { DisclaimerBanner } from '../components/common/DisclaimerBanner'
import { MoneyDisplay } from '../components/common/MoneyDisplay'
import { format } from 'date-fns'
import { Download, RefreshCw } from 'lucide-react'

export function ESOPPage() {
  const { data: run, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['esop', 'latest'],
    queryFn: () => esopApi.getLatestQoERun().then((r) => r.data),
    staleTime: 5 * 60_000,
  })

  const exportReport = useMutation({
    mutationFn: () => esopApi.exportQoEReport(run!.id),
    onSuccess: (res) => {
      const url = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `qoe-report-${run!.id.slice(0, 8)}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  return (
    <div className="space-y-5">
      {/* ALWAYS-VISIBLE Disclaimer */}
      <DisclaimerBanner />

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">ESOP / Quality of Earnings</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Normalized EBITDA calculation with add-backs and adjustments for ESOP transaction support.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          {run && (
            <button
              type="button"
              onClick={() => exportReport.mutate()}
              disabled={exportReport.isPending}
              className="btn-primary flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              {exportReport.isPending ? 'Exporting…' : 'Export Report'}
            </button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <div className="card h-32 animate-pulse bg-slate-100" />
          <div className="card h-80 animate-pulse bg-slate-100" />
        </div>
      ) : !run ? (
        <div className="card p-10 text-center text-slate-500">
          No QoE run available.
        </div>
      ) : (
        <>
          {/* Run metadata */}
          <div className="card px-5 py-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-slate-500 font-medium mb-0.5">Period</p>
                <p className="text-sm font-semibold text-slate-900">
                  {format(new Date(run.period_start), 'MMM yyyy')} –{' '}
                  {format(new Date(run.period_end), 'MMM yyyy')}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500 font-medium mb-0.5">Book EBITDA</p>
                <MoneyDisplay amount={run.book_ebitda} colorize={false} size="lg" />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-medium mb-0.5">Net Add-backs</p>
                <MoneyDisplay amount={run.total_addbacks - run.total_deductions} size="lg" />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-medium mb-0.5">Normalized EBITDA</p>
                <MoneyDisplay amount={run.normalized_ebitda} colorize={false} size="lg" />
              </div>
            </div>
            {run.notes && (
              <p className="text-xs text-slate-500 mt-3 border-t border-slate-100 pt-3 italic">
                {run.notes}
              </p>
            )}
          </div>

          {/* EBITDA Bridge Chart */}
          <div className="card px-5 py-5">
            <h3 className="font-semibold text-slate-900 mb-1">EBITDA Bridge</h3>
            <p className="text-xs text-slate-500 mb-4">
              Book EBITDA to Normalized EBITDA waterfall
            </p>
            <EBITDABridge run={run} />
          </div>

          {/* Add-back table */}
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900">Adjustments Detail</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {run.adjustments.length} adjustments · All require independent review
                </p>
              </div>
            </div>
            <div className="p-4">
              <DisclaimerBanner compact />
              <div className="mt-4">
                <AddBackTable adjustments={run.adjustments} runId={run.id} />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
