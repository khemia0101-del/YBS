import { useQuery } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import { financialApi } from '../../api/financial'
import { format } from 'date-fns'

const DSO_WARNING_THRESHOLD = 45

export function DSOChart() {
  const { data: snapshots, isLoading } = useQuery({
    queryKey: ['dso', 'history'],
    queryFn: () => financialApi.getDSOHistory(12).then((r) => r.data),
    staleTime: 10 * 60_000,
  })

  if (isLoading) {
    return <div className="h-64 animate-pulse bg-slate-100 rounded-lg" />
  }

  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
        No DSO history available.
      </div>
    )
  }

  const chartData = snapshots.map((s) => ({
    date: format(new Date(s.snapshot_date), 'MMM d'),
    dso: Math.round(s.dso_days),
    ar: s.ar_balance,
  }))

  const latest = snapshots[snapshots.length - 1]

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-700">
            Current DSO:{' '}
            <span
              className={`font-bold ${
                latest.dso_days > DSO_WARNING_THRESHOLD ? 'text-red-600' : 'text-green-600'
              }`}
            >
              {Math.round(latest.dso_days)} days
            </span>
          </p>
          <p className="text-xs text-slate-400">
            AR Balance: ${latest.ar_balance.toLocaleString()}
          </p>
        </div>
        {latest.dso_days > DSO_WARNING_THRESHOLD && (
          <span className="text-xs font-medium bg-red-100 text-red-700 px-2.5 py-1 rounded-full">
            Above 45-day threshold
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${v}d`}
          />
          <Tooltip
            formatter={(value: number) => [`${value} days`, 'DSO']}
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: '1px solid #e2e8f0',
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            }}
          />
          <ReferenceLine
            y={DSO_WARNING_THRESHOLD}
            stroke="#dc2626"
            strokeDasharray="4 4"
            strokeWidth={1.5}
            label={{ value: '45d threshold', fontSize: 10, fill: '#dc2626', position: 'right' }}
          />
          <Line
            type="monotone"
            dataKey="dso"
            stroke="#1e40af"
            strokeWidth={2.5}
            dot={{ r: 3, fill: '#1e40af' }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
