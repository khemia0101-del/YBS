import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { decisionsApi, type DecisionFilters } from '../api/decisions'
import { DataTable, type Column } from '../components/common/DataTable'
import { StatusBadge } from '../components/common/StatusBadge'
import { ConfidenceBadge } from '../components/common/ConfidenceBadge'
import { ApprovalButton } from '../components/common/ApprovalButton'
import type { Decision } from '../types/models'
import { DecisionLabel } from '../types/enums'
import { formatDistanceToNow } from 'date-fns'
import { Filter } from 'lucide-react'

const LABEL_OPTIONS = [
  { value: '', label: 'All Labels' },
  { value: DecisionLabel.Auto, label: 'AUTO' },
  { value: DecisionLabel.ApprovalRequired, label: 'Approval Required' },
  { value: DecisionLabel.Blocked, label: 'Blocked' },
]

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
]

function DecisionDetail({ decision }: { decision: Decision }) {
  const queryClient = useQueryClient()
  const approve = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      decisionsApi.approveDecision(id, notes),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['decisions'] }),
  })
  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      decisionsApi.rejectDecision(id, reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['decisions'] }),
  })

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 p-1">
      <div className="space-y-3">
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            Rationale
          </p>
          <p className="text-sm text-slate-700">{decision.rationale}</p>
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            Inputs
          </p>
          <div className="bg-slate-900 rounded-lg p-3 max-h-40 overflow-auto">
            <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap">
              {JSON.stringify(decision.inputs, null, 2)}
            </pre>
          </div>
        </div>
      </div>
      <div className="space-y-3">
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            Outputs
          </p>
          <div className="bg-slate-900 rounded-lg p-3 max-h-40 overflow-auto">
            <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap">
              {JSON.stringify(decision.outputs, null, 2)}
            </pre>
          </div>
        </div>
        {decision.requires_approval && decision.status === 'pending' && (
          <ApprovalButton
            onApprove={async (notes) => { await approve.mutateAsync({ id: decision.id, notes }) }}
            onReject={async (reason) => { await reject.mutateAsync({ id: decision.id, reason }) }}
            disabled={approve.isPending || reject.isPending}
          />
        )}
      </div>
    </div>
  )
}

export function DecisionsPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<DecisionFilters>({ page_size: 25 })
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['decisions', filters, page],
    queryFn: () => decisionsApi.getDecisions({ ...filters, page }).then((r) => r.data),
  })

  const updateFilter = (key: keyof DecisionFilters, value: string | boolean | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }))
    setPage(1)
  }

  const columns: Column<Decision>[] = [
    {
      key: 'decision_type',
      header: 'Type',
      render: (row) => (
        <span className="text-sm font-medium capitalize">
          {row.decision_type.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      className: 'max-w-sm',
      render: (row) => (
        <span className="text-sm text-slate-700 truncate block max-w-sm" title={row.description}>
          {row.description}
        </span>
      ),
    },
    {
      key: 'label',
      header: 'Label',
      render: (row) => <StatusBadge status={row.label} size="sm" />,
    },
    {
      key: 'risk_level',
      header: 'Risk',
      render: (row) => <StatusBadge status={row.risk_level} size="sm" />,
    },
    {
      key: 'confidence_score',
      header: 'Confidence',
      render: (row) => <ConfidenceBadge score={row.confidence_score} size="sm" />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
    {
      key: 'created_at',
      header: 'Age',
      render: (row) => (
        <span className="text-xs text-slate-500">
          {formatDistanceToNow(new Date(row.created_at), { addSuffix: true })}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            setExpandedId((p) => (p === row.id ? null : row.id))
          }}
          className="text-xs text-primary hover:underline"
        >
          {expandedId === row.id ? 'Collapse' : 'Details'}
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Decisions</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Review and act on system-generated decisions requiring approval.
        </p>
      </div>

      {/* Filters */}
      <div className="card px-4 py-3 flex flex-wrap items-center gap-3">
        <Filter className="w-4 h-4 text-slate-400" />
        <select
          className="select w-44"
          value={filters.label ?? ''}
          onChange={(e) => updateFilter('label', e.target.value)}
        >
          {LABEL_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          className="select w-36"
          value={filters.status ?? ''}
          onChange={(e) => updateFilter('status', e.target.value)}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.requires_approval === true}
            onChange={(e) =>
              updateFilter('requires_approval', e.target.checked ? 'true' : undefined)
            }
            className="rounded border-slate-300 text-primary focus:ring-primary"
          />
          <span className="text-sm text-slate-700">Approval required only</span>
        </label>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        keyExtractor={(row) => row.id}
        isLoading={isLoading}
        emptyMessage="No decisions found."
        totalItems={data?.total ?? 0}
        currentPage={page}
        pageSize={filters.page_size ?? 25}
        onPageChange={setPage}
        onRowClick={(row) => setExpandedId((p) => (p === row.id ? null : row.id))}
        expandedRowId={expandedId}
        renderExpanded={(row) => <DecisionDetail decision={row} />}
      />
    </div>
  )
}
