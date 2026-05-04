import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import { format } from 'date-fns'
import type { CashForecastWeek } from '../../types/models'

interface CashForecastChartProps {
  weeks: CashForecastWeek[]
}

const USD_SHORT = (v: number) => {
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}k`
  return `$${v.toFixed(0)}`
}

export function CashForecastChart({ weeks }: CashForecastChartProps) {
  if (!weeks || weeks.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
        No forecast data available.
      </div>
    )
  }

  const chartData = weeks.map((w) => ({
    week: `Wk ${w.week_number}`,
    weekLabel: `${format(new Date(w.week_start), 'MMM d')}`,
    inflows: w.inflows,
    outflows: -w.outflows,
    endingCash: w.ending_cash,
    payrollCovered: w.payroll_covered,
  }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 20, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="weekLabel"
          tick={{ fontSize: 10, fill: '#94a3b8' }}
          tickLine={false}
          axisLine={false}
          angle={-30}
          textAnchor="end"
          height={48}
        />
        <YAxis
          tickFormatter={USD_SHORT}
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          formatter={(value: number, name: string) => {
            const label = name === 'endingCash' ? 'Ending Cash' : name === 'inflows' ? 'Inflows' : 'Outflows'
            return [USD_SHORT(Math.abs(value)), label]
          }}
          contentStyle={{
            fontSize: 12,
            borderRadius: 8,
            border: '1px solid #e2e8f0',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        <ReferenceLine y={0} stroke="#94a3b8" strokeWidth={1} />

        <Bar dataKey="inflows" name="Inflows" fill="#16a34a" opacity={0.8} radius={[2, 2, 0, 0]} maxBarSize={28} />
        <Bar dataKey="outflows" name="Outflows" fill="#dc2626" opacity={0.8} radius={[2, 2, 0, 0]} maxBarSize={28} />

        <Line
          type="monotone"
          dataKey="endingCash"
          name="endingCash"
          stroke="#1e40af"
          strokeWidth={2.5}
          dot={(props) => {
            const { cx, cy, payload } = props as { cx: number; cy: number; payload: typeof chartData[0] }
            const isNeg = payload.endingCash < 0
            return (
              <circle
                key={`dot-${payload.week}`}
                cx={cx}
                cy={cy}
                r={4}
                fill={isNeg ? '#dc2626' : '#1e40af'}
                stroke="white"
                strokeWidth={1.5}
              />
            )
          }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
