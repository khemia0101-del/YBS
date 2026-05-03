import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ShieldAlert, ShieldCheck } from 'lucide-react'
import { StatusBadge } from '../common/StatusBadge'
import { ApprovalButton } from '../common/ApprovalButton'
import { useApprovalRequests, useApproveRequest, useRejectRequest } from '../../hooks/useApprovals'
import type { ApprovalRequest } from '../../types/models'
import { RiskLevel } from '../../types/enums'
import clsx from 'clsx'

const RISK_ORDER: Record<RiskLevel, number> = {
  [RiskLevel.Critical]: 0,
  [RiskLevel.High]: 1,
  [RiskLevel.Medium]: 2,
  [RiskLevel.Low]: 3,
}

const RISK_CARD_STYLES: Record<RiskLevel, string> = {
  [RiskLevel.Critical]: 'border-red-400 bg-red-50',
  [RiskLevel.High]: 'border-orange-400 bg-orange-50',
  [RiskLevel.Medium]: 'border-yellow-400 bg-yellow-50',
  [RiskLevel.Low]: 'border-slate-300 bg-white',
}

export function ApprovalQueue() {
  const [page] = useState(1)
  const { data, isLoading } = useApprovalRequests({ status: 'pending', page, page_size: 50 })
  const approve = useApproveRequest()
  const reject = useRejectRequest()

  const sorted = [...(data?.items ?? [])].sort(
    (a, b) =>
      (RISK_ORDER[a.risk_level as RiskLevel] ?? 99) -
      (RISK_ORDER[b.risk_level as RiskLevel] ?? 99)
  )

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card h-40 animate-pulse bg-slate-100" />
        ))}
      </div>
    )
  }

  if (sorted.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-500">
        <ShieldCheck className="w-12 h-12 mb-3 text-green-400" />
        <p className="font-medium text-slate-700">All caught up!</p>
        <p className="text-sm mt-1">No pending approval requests.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 font-medium">
        {sorted.length} pending approval{sorted.length !== 1 ? 's' : ''}
      </p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {sorted.map((req: ApprovalRequest) => (
          <div
            key={req.id}
            className={clsx(
              'rounded-xl border-2 p-5 space-y-3',
              RISK_CARD_STYLES[req.risk_level as RiskLevel] ?? 'border-slate-300 bg-white'
            )}
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <ShieldAlert
                  className={clsx(
                    'w-5 h-5 flex-shrink-0',
                    req.risk_level === RiskLevel.Critical
                      ? 'text-red-600'
                      : req.risk_level === RiskLevel.High
                      ? 'text-orange-600'
                      : req.risk_level === RiskLevel.Medium
                      ? 'text-yellow-600'
                      : 'text-slate-500'
                  )}
                />
                <StatusBadge status={req.risk_level} size="sm" />
              </div>
              <span className="text-xs text-slate-500 flex-shrink-0">
                {formatDistanceToNow(new Date(req.requested_at), { addSuffix: true })}
              </span>
            </div>

            {/* Description */}
            <div>
              <p className="text-sm font-semibold text-slate-900">{req.description}</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Requested by: <span className="font-medium">{req.requested_by}</span>
              </p>
            </div>

            {/* Context */}
            {Object.keys(req.context).length > 0 && (
              <div className="bg-white/60 rounded-lg p-3 border border-white/80">
                <div className="space-y-1">
                  {Object.entries(req.context)
                    .slice(0, 4)
                    .map(([k, v]) => (
                      <div key={k} className="flex gap-2 text-xs">
                        <span className="text-slate-400 capitalize min-w-[80px]">
                          {k.replace(/_/g, ' ')}:
                        </span>
                        <span className="text-slate-700 font-medium truncate">
                          {String(v)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <ApprovalButton
              onApprove={async (notes) => { await approve.mutateAsync({ id: req.id, notes }) }}
              onReject={async (reason) => { await reject.mutateAsync({ id: req.id, reason }) }}
              disabled={approve.isPending || reject.isPending}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
