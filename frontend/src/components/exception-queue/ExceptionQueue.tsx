import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { RefreshCw, Filter, X } from 'lucide-react'
import { DataTable, type Column } from '../common/DataTable'
import { ConfidenceBadge } from '../common/ConfidenceBadge'
import { StatusBadge } from '../common/StatusBadge'
import { MoneyDisplay } from '../common/MoneyDisplay'
import { ExceptionCard } from './ExceptionCard'
import { BulkApproveBar } from './BulkApproveBar'
import {
  useExceptionList,
  useExceptionStats,
} from '../../hooks/useExceptions'
import { useExceptionStore } from '../../stores/exceptionStore'
import type { StagedException } from '../../types/models'
import { ExceptionStatus } from '../../types/enums'

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: ExceptionStatus.Pending, label: 'Pending' },
  { value: ExceptionStatus.NeedsReview, label: 'Needs Review' },
  { value: ExceptionStatus.Approved, label: 'Approved' },
  { value: ExceptionStatus.AutoApproved, label: 'Auto-Approved' },
  { value: ExceptionStatus.Rejected, label: 'Rejected' },
]

const RECORD_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'invoice', label: 'Invoice' },
  { value: 'payment', label: 'Payment' },
  { value: 'labor_shift', label: 'Labor Shift' },
  { value: 'contract', label: 'Contract' },
  { value: 'customer', label: 'Customer' },
]

const SOURCE_SYSTEM_OPTIONS = [
  { value: '', label: 'All Sources' },
  { value: 'quickbooks', label: 'QuickBooks' },
  { value: 'deputy', label: 'Deputy' },
  { value: 'workiz', label: 'Workiz' },
  { value: 'manual', label: 'Manual' },
]

interface StatCardProps {
  label: string
  count: number
  highlight?: boolean
}

function StatCard({ label, count, highlight }: StatCardProps) {
  return (
    <div className={`card px-4 py-3 ${highlight ? 'border-yellow-300 bg-yellow-50' : ''}`}>
      <p className="text-xs text-slate-500 font-medium mb-0.5">{label}</p>
      <p className={`text-2xl font-bold ${highlight ? 'text-yellow-700' : 'text-slate-900'}`}>
        {count.toLocaleString()}
      </p>
    </div>
  )
}

export function ExceptionQueue() {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [showFilters, setShowFilters] = useState(false)

  const {
    status,
    record_type,
    source_system,
    min_confidence,
    max_confidence,
    date_from,
    date_to,
    page,
    page_size,
    sort_by,
    sort_dir,
    selectedIds,
    setStatus,
    setRecordType,
    setSourceSystem,
    setConfidenceRange,
    setDateRange,
    setPage,
    setSortBy,
    toggleSelected,
    selectAll,
    clearSelected,
    resetFilters,
  } = useExceptionStore()

  const { data, isLoading, refetch, isFetching } = useExceptionList()
  const { data: stats } = useExceptionStats()

  const handleRowClick = (row: StagedException) => {
    setExpandedId((prev) => (prev === row.id ? null : row.id))
  }

  const hasActiveFilters =
    status !== '' ||
    record_type !== '' ||
    source_system !== '' ||
    min_confidence > 0 ||
    max_confidence < 1 ||
    date_from !== '' ||
    date_to !== ''

  const columns: Column<StagedException>[] = [
    {
      key: 'record_type',
      header: 'Type',
      sortable: true,
      render: (row) => (
        <span className="capitalize font-medium text-slate-700">
          {row.record_type.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'source_system',
      header: 'Source',
      sortable: true,
      render: (row) => (
        <span className="text-slate-600 capitalize">{row.source_system}</span>
      ),
    },
    {
      key: 'confidence_score',
      header: 'Confidence',
      sortable: true,
      render: (row) => <ConfidenceBadge score={row.confidence_score} size="sm" />,
    },
    {
      key: 'financial_impact',
      header: 'Financial Impact',
      sortable: true,
      render: (row) =>
        row.financial_impact != null ? (
          <MoneyDisplay amount={row.financial_impact} size="sm" />
        ) : (
          <span className="text-slate-400">—</span>
        ),
    },
    {
      key: 'age_days',
      header: 'Age',
      sortable: true,
      render: (row) => (
        <span
          className={`text-sm ${row.age_days > 3 ? 'text-orange-600 font-medium' : 'text-slate-600'}`}
        >
          {formatDistanceToNow(new Date(row.created_at), { addSuffix: true })}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            handleRowClick(row)
          }}
          className="text-xs text-primary hover:underline font-medium"
        >
          {expandedId === row.id ? 'Collapse' : 'Review'}
        </button>
      ),
    },
  ]

  const selectedArray = Array.from(selectedIds)

  return (
    <div className="space-y-5">
      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard label="Total" count={stats.total} />
          <StatCard label="Pending" count={stats.pending} highlight />
          <StatCard label="Needs Review" count={stats.needs_review} />
          <StatCard label="Auto-Approved" count={stats.auto_approved} />
          <StatCard label="Approved" count={stats.approved} />
          <StatCard label="Rejected" count={stats.rejected} />
        </div>
      )}

      {/* Toolbar */}
      <div className="card px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Status filter */}
          <select
            className="select w-44"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>

          {/* Type filter */}
          <select
            className="select w-40"
            value={record_type}
            onChange={(e) => setRecordType(e.target.value)}
          >
            {RECORD_TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>

          {/* Source filter */}
          <select
            className="select w-36"
            value={source_system}
            onChange={(e) => setSourceSystem(e.target.value)}
          >
            {SOURCE_SYSTEM_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>

          {/* Advanced filters toggle */}
          <button
            type="button"
            onClick={() => setShowFilters((v) => !v)}
            className={`btn-secondary flex items-center gap-1.5 ${hasActiveFilters ? 'border-primary text-primary' : ''}`}
          >
            <Filter className="w-4 h-4" />
            Filters
            {hasActiveFilters && (
              <span className="w-2 h-2 rounded-full bg-primary flex-shrink-0" />
            )}
          </button>

          {hasActiveFilters && (
            <button
              type="button"
              onClick={resetFilters}
              className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"
            >
              <X className="w-3.5 h-3.5" />
              Clear filters
            </button>
          )}

          {/* Spacer */}
          <div className="flex-1" />

          {/* Refresh */}
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="btn-secondary"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Advanced filters panel */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="label">Min Confidence</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={Math.round(min_confidence * 100)}
                  onChange={(e) =>
                    setConfidenceRange(Number(e.target.value) / 100, max_confidence)
                  }
                  className="w-full accent-primary"
                />
                <span className="text-sm font-mono w-10 text-right">
                  {Math.round(min_confidence * 100)}%
                </span>
              </div>
            </div>
            <div>
              <label className="label">Max Confidence</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={Math.round(max_confidence * 100)}
                  onChange={(e) =>
                    setConfidenceRange(min_confidence, Number(e.target.value) / 100)
                  }
                  className="w-full accent-primary"
                />
                <span className="text-sm font-mono w-10 text-right">
                  {Math.round(max_confidence * 100)}%
                </span>
              </div>
            </div>
            <div>
              <label className="label">From Date</label>
              <input
                type="date"
                className="input"
                value={date_from}
                onChange={(e) => setDateRange(e.target.value, date_to)}
              />
            </div>
            <div>
              <label className="label">To Date</label>
              <input
                type="date"
                className="input"
                value={date_to}
                onChange={(e) => setDateRange(date_from, e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={data?.items ?? []}
        keyExtractor={(row) => row.id}
        isLoading={isLoading}
        emptyMessage="No exceptions found for the current filters."
        totalItems={data?.total ?? 0}
        currentPage={page}
        pageSize={page_size}
        onPageChange={setPage}
        onRowClick={handleRowClick}
        expandedRowId={expandedId}
        renderExpanded={(row) => <ExceptionCard exception={row} />}
        selectable
        selectedIds={selectedIds}
        onSelectRow={toggleSelected}
        onSelectAll={(ids) => {
          if (selectedIds.size === ids.length) {
            clearSelected()
          } else {
            selectAll(ids)
          }
        }}
        sortBy={sort_by}
        sortDir={sort_dir}
        onSort={setSortBy}
      />

      {/* Bulk approve bar */}
      <BulkApproveBar selectedCount={selectedIds.size} selectedIds={selectedArray} />
    </div>
  )
}
