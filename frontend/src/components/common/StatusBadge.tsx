import clsx from 'clsx'

type StatusValue = string

// Map raw string values to display classes
const STATUS_COLORS: Record<string, string> = {
  // shared 'pending'
  pending: 'bg-yellow-100 text-yellow-800',
  // shared 'approved'
  approved: 'bg-indigo-100 text-indigo-800',
  rejected: 'bg-red-100 text-red-800',
  needs_review: 'bg-orange-100 text-orange-800',
  auto_approved: 'bg-blue-100 text-blue-800',

  // ContractStatus / general
  active: 'bg-green-100 text-green-800',
  expired: 'bg-slate-100 text-slate-600',
  terminated: 'bg-red-100 text-red-800',
  suspended: 'bg-orange-100 text-orange-800',

  // InvoiceStatus
  draft: 'bg-slate-100 text-slate-600',
  open: 'bg-blue-100 text-blue-800',
  partial: 'bg-indigo-100 text-indigo-800',
  paid: 'bg-green-100 text-green-800',
  overdue: 'bg-red-100 text-red-800',
  void: 'bg-slate-100 text-slate-500',
  disputed: 'bg-orange-100 text-orange-800',

  // AgentTaskStatus
  queued: 'bg-slate-100 text-slate-700',
  running: 'bg-blue-100 text-blue-800',
  awaiting_approval: 'bg-yellow-100 text-yellow-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',

  // RiskLevel
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-900 font-semibold',

  // DecisionLabel
  AUTO: 'bg-green-100 text-green-800',
  APPROVAL_REQUIRED: 'bg-yellow-100 text-yellow-800',
  BLOCKED: 'bg-red-100 text-red-800',

  // UserRole
  admin: 'bg-purple-100 text-purple-800',
  analyst: 'bg-blue-100 text-blue-800',
  operator: 'bg-green-100 text-green-800',
  viewer: 'bg-slate-100 text-slate-600',
}

const STATUS_LABELS: Record<string, string> = {
  needs_review: 'Needs Review',
  auto_approved: 'Auto-Approved',
  awaiting_approval: 'Awaiting Approval',
  APPROVAL_REQUIRED: 'Approval Required',
}

interface StatusBadgeProps {
  status: StatusValue
  size?: 'sm' | 'md'
}

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const colorClass = STATUS_COLORS[status] || 'bg-slate-100 text-slate-700'
  const label =
    STATUS_LABELS[status] ||
    status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full font-medium',
        colorClass,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
      )}
    >
      {label}
    </span>
  )
}
