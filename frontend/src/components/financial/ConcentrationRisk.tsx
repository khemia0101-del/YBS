import { useQuery } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts'
import { financialApi } from '../../api/financial'
import { AlertTriangle } from 'lucide-react'

function getBarColor(pct: number): string {
  if (pct > 25) return '#dc2626'
  if (pct > 20) return '#d97706'
  return '#1e40af'
}

export function ConcentrationRisk() {
  const { data: concentration, isLoading } = useQuery({
    queryKey: ['concentration'],
    queryFn: () => financialApi.getConcentrationRisk().then((r) => r.data),
    staleTime: 10 * 60_000,
  })

  if (isLoading) {
    return <div className="h-64 animate-pulse bg-slate-100 rounded-lg" />
  }

  if (!concentration || concentration.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
        No concentration data available.
      </div>
    )
  }

  const topCustomers = concentration.slice(0, 10)
  const highRisk = concentration.filter((c) => c.revenue_pct > 25)

  return (
    <div className="space-y-4">
      {highRisk.length > 0 && (
        <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-red-800">
            <span className="font-semibold">{highRisk.length} customer{highRisk.length !== 1 ? 's' : ''}</span>{' '}
            exceed 25% revenue concentration:{' '}
            {highRisk.map((c) => c.customer_name).join(', ')}.
          </div>
        </div>
      )}

      <ResponsiveContainer width="100%" height={280}>
        <BarChart
          data={topCustomers}
          layout="vertical"
          margin={{ top: 5, right: 40, left: 120, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
          <XAxis
            type="number"
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
          />
          <YAxis
            type="category"
            dataKey="customer_name"
            width={110}
            tick={{ fontSize: 11, fill: '#475569' }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            formatter={(value: number, _name: string) => [
              `${value.toFixed(1)}% ($${(
                (topCustomers.find((c) => c.revenue_pct === value)?.revenue ?? 0) / 1000
              ).toFixed(0)}k)`,
              'Revenue %',
            ]}
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: '1px solid #e2e8f0',
            }}
          />
          <Bar dataKey="revenue_pct" radius={[0, 4, 4, 0]} maxBarSize={28}>
            {topCustomers.map((entry) => (
              <Cell key={entry.customer_id} fill={getBarColor(entry.revenue_pct)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-red-600 inline-block" /> &gt;25% (High)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-yellow-600 inline-block" /> 20–25% (Medium)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-primary inline-block" /> &lt;20% (Normal)
        </span>
      </div>
    </div>
  )
}
