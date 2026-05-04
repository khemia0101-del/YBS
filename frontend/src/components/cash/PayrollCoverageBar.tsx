import { format } from 'date-fns'
import { CheckCircle, AlertTriangle } from 'lucide-react'
import type { CashForecastRun } from '../../types/models'
import clsx from 'clsx'

interface PayrollCoverageBarProps {
  forecast: CashForecastRun
}

export function PayrollCoverageBar({ forecast }: PayrollCoverageBarProps) {
  const coveredThrough = forecast.payroll_covered_through
  const totalWeeks = forecast.weeks.length || 13
  const coveredWeeks = forecast.weeks.filter((w) => w.payroll_covered).length
  const coveragePct = Math.round((coveredWeeks / totalWeeks) * 100)

  const isFullyCovered = coveredWeeks >= totalWeeks

  return (
    <div className="card px-5 py-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <h4 className="font-semibold text-slate-900 text-sm">Payroll Coverage</h4>
          {coveredThrough ? (
            <p className="text-sm text-slate-600 mt-0.5">
              Covered through{' '}
              <span className="font-medium text-slate-900">
                {format(new Date(coveredThrough), 'MMM d, yyyy')}
              </span>
            </p>
          ) : (
            <p className="text-sm text-red-600 font-medium mt-0.5">Payroll coverage uncertain</p>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {isFullyCovered ? (
            <CheckCircle className="w-5 h-5 text-green-600" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
          )}
          <span
            className={clsx(
              'text-sm font-semibold',
              isFullyCovered ? 'text-green-700' : 'text-yellow-700'
            )}
          >
            {coveredWeeks}/{totalWeeks} weeks
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-500',
            isFullyCovered ? 'bg-green-500' : coveragePct >= 70 ? 'bg-yellow-500' : 'bg-red-500'
          )}
          style={{ width: `${coveragePct}%` }}
        />
      </div>

      {/* Week ticks */}
      <div className="flex justify-between mt-1.5 px-0.5">
        {Array.from({ length: Math.min(totalWeeks, 13) }).map((_, i) => {
          const covered = i < coveredWeeks
          return (
            <div
              key={i}
              className={clsx(
                'w-1.5 h-1.5 rounded-full',
                covered ? 'bg-green-500' : 'bg-slate-200'
              )}
              title={`Week ${i + 1}`}
            />
          )
        })}
      </div>
      <p className="text-xs text-slate-500 mt-1.5">
        {coveragePct}% of the 13-week forecast horizon covered
      </p>
    </div>
  )
}
