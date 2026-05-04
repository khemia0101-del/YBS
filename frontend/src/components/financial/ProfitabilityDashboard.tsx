import { useQuery } from '@tanstack/react-query'
import { financialApi } from '../../api/financial'
import { ConfidenceBadge } from '../common/ConfidenceBadge'
import { MoneyDisplay } from '../common/MoneyDisplay'
import { DataTable, type Column } from '../common/DataTable'
import type { ProfitabilityRunLine } from '../../types/models'
import { format } from 'date-fns'
import { RefreshCw } from 'lucide-react'

export function ProfitabilityDashboard() {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['profitability', 'latest'],
    queryFn: () => financialApi.getLatestProfitabilityRun().then((r) => r.data),
    staleTime: 5 * 60_000,
  })

  const lines = data?.lines ?? []
  const sorted = [...lines].sort((a, b) => a.gross_margin - b.gross_margin)

  const summaryCards = data
    ? [
        { label: 'Total Revenue', value: data.total_revenue },
        { label: 'Total Labor Cost', value: data.total_labor_cost },
        { label: 'Gross Profit', value: data.gross_profit },
      ]
    : []

  const columns: Column<ProfitabilityRunLine>[] = [
    {
      key: 'customer_name',
      header: 'Customer',
      render: (row) => <span className="font-medium">{row.customer_name}</span>,
    },
    {
      key: 'contract_number',
      header: 'Contract',
      render: (row) => <span className="font-mono text-xs">{row.contract_number}</span>,
    },
    {
      key: 'revenue',
      header: 'Revenue',
      render: (row) => <MoneyDisplay amount={row.revenue} colorize={false} size="sm" />,
    },
    {
      key: 'labor_cost',
      header: 'Labor Cost',
      render: (row) => <MoneyDisplay amount={row.labor_cost} colorize={false} size="sm" />,
    },
    {
      key: 'gross_profit',
      header: 'Gross Profit',
      render: (row) => <MoneyDisplay amount={row.gross_profit} size="sm" />,
    },
    {
      key: 'gross_margin',
      header: 'Margin %',
      render: (row) => <MoneyDisplay amount={row.gross_margin} isMargin size="sm" />,
    },
    {
      key: 'confidence_score',
      header: 'Confidence',
      render: (row) => <ConfidenceBadge score={row.confidence_score} size="sm" />,
    },
    {
      key: 'flags',
      header: 'Flags',
      render: (row) =>
        row.flags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {row.flags.map((f) => (
              <span
                key={f}
                className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded font-medium"
              >
                {f}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-slate-400">—</span>
        ),
    },
  ]

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-5 h-24 animate-pulse bg-slate-100" />
          ))}
        </div>
        <div className="card h-64 animate-pulse bg-slate-100" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="card p-10 text-center text-slate-500">
        No profitability run available. Run a profitability analysis to see results.
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500">
            Period: {format(new Date(data.period_start), 'MMM d, yyyy')} –{' '}
            {format(new Date(data.period_end), 'MMM d, yyyy')}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            Run: {format(new Date(data.run_at), 'MMM d, yyyy h:mm a')}
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="btn-secondary"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {summaryCards.map((card) => (
          <div key={card.label} className="card px-5 py-4">
            <p className="text-xs text-slate-500 font-medium mb-1">{card.label}</p>
            <MoneyDisplay amount={card.value} colorize={false} size="lg" />
          </div>
        ))}
        <div className="card px-5 py-4">
          <p className="text-xs text-slate-500 font-medium mb-1">Gross Margin</p>
          <MoneyDisplay amount={data.gross_margin} isMargin size="lg" />
        </div>
      </div>

      {/* Per-contract table — worst margin first */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-900">Contract Margins</h3>
          <p className="text-xs text-slate-500 mt-0.5">Sorted by margin ascending (worst first)</p>
        </div>
        <div className="p-4">
          <DataTable
            columns={columns}
            data={sorted}
            keyExtractor={(row) => row.id}
            emptyMessage="No contract margin data available."
          />
        </div>
      </div>
    </div>
  )
}
