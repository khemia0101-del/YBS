import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  LabelList,
  ResponsiveContainer,
} from 'recharts'
import type { QoERun } from '../../types/models'

interface EBITDABridgeProps {
  run: QoERun
}

interface BridgeBar {
  name: string
  value: number
  base: number
  fill: string
  isTotal: boolean
}

function buildBridgeData(run: QoERun): BridgeBar[] {
  const addbacks = run.adjustments.filter((a) => a.is_addback)
  const deductions = run.adjustments.filter((a) => !a.is_addback)

  const bars: BridgeBar[] = []

  // Book EBITDA (baseline)
  bars.push({
    name: 'Book EBITDA',
    value: run.book_ebitda,
    base: 0,
    fill: '#1e40af',
    isTotal: true,
  })

  // Addbacks — stacked on top
  let running = run.book_ebitda
  addbacks.forEach((adj) => {
    bars.push({
      name: adj.category,
      value: adj.amount,
      base: running,
      fill: '#16a34a',
      isTotal: false,
    })
    running += adj.amount
  })

  // Deductions — subtract
  deductions.forEach((adj) => {
    bars.push({
      name: adj.category,
      value: -adj.amount,
      base: running - adj.amount,
      fill: '#dc2626',
      isTotal: false,
    })
    running -= adj.amount
  })

  // Normalized EBITDA
  bars.push({
    name: 'Normalized EBITDA',
    value: run.normalized_ebitda,
    base: 0,
    fill: '#7c3aed',
    isTotal: true,
  })

  return bars
}

const USD_K = (v: number) => {
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  return `$${(v / 1_000).toFixed(0)}k`
}

export function EBITDABridge({ run }: EBITDABridgeProps) {
  const bridgeData = buildBridgeData(run)

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3 text-center mb-2">
        <div className="card px-3 py-3">
          <p className="text-xs text-slate-500 mb-1">Book EBITDA</p>
          <p className="text-lg font-bold text-primary">{USD_K(run.book_ebitda)}</p>
        </div>
        <div className="card px-3 py-3 border-green-200 bg-green-50">
          <p className="text-xs text-slate-500 mb-1">Total Add-backs</p>
          <p className="text-lg font-bold text-green-700">+{USD_K(run.total_addbacks)}</p>
        </div>
        <div className="card px-3 py-3 border-purple-200 bg-purple-50">
          <p className="text-xs text-slate-500 mb-1">Normalized EBITDA</p>
          <p className="text-lg font-bold text-purple-700">{USD_K(run.normalized_ebitda)}</p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={bridgeData} margin={{ top: 20, right: 20, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10, fill: '#475569' }}
            tickLine={false}
            axisLine={false}
            angle={-35}
            textAnchor="end"
            height={70}
          />
          <YAxis
            tickFormatter={USD_K}
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            formatter={(value: number, _name: string, props: { payload?: BridgeBar }) => {
              const bar = props.payload
              if (!bar) return [USD_K(value), '']
              return [bar.isTotal ? USD_K(bar.value) : `${bar.value >= 0 ? '+' : ''}${USD_K(bar.value)}`, bar.name]
            }}
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: '1px solid #e2e8f0',
            }}
          />
          {/* Invisible base bar for stacking effect */}
          <Bar dataKey="base" stackId="bridge" fill="transparent" />
          <Bar dataKey="value" stackId="bridge" radius={[4, 4, 0, 0]} maxBarSize={60}>
            <LabelList
              dataKey="value"
              position="top"
              formatter={USD_K}
              style={{ fontSize: 10, fill: '#475569', fontWeight: 600 }}
            />
            {bridgeData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} opacity={entry.isTotal ? 1 : 0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="flex items-center gap-4 text-xs text-slate-500 justify-center">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-primary inline-block" /> Baseline
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-green-600 inline-block" /> Add-backs
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-red-600 inline-block" /> Deductions
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-purple-700 inline-block" /> Normalized
        </span>
      </div>
    </div>
  )
}
