import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { esopApi } from '../../api/esop'
import { useAuthStore } from '../../stores/authStore'
import { EvidenceLink } from '../common/EvidenceLink'
import { StatusBadge } from '../common/StatusBadge'
import { MoneyDisplay } from '../common/MoneyDisplay'
import { ApprovalButton } from '../common/ApprovalButton'
import type { ESOPAdjustment } from '../../types/models'
import { UserRole } from '../../types/enums'
import clsx from 'clsx'

interface AddBackTableProps {
  adjustments: ESOPAdjustment[]
  runId: string
}

export function AddBackTable({ adjustments, runId }: AddBackTableProps) {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === UserRole.Admin
  const queryClient = useQueryClient()
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const approveAdj = useMutation({
    mutationFn: ({ adjId, notes }: { adjId: string; notes?: string }) =>
      esopApi.approveAdjustment(runId, adjId, notes).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['esop', 'latest'] }),
  })

  const rejectAdj = useMutation({
    mutationFn: ({ adjId, reason }: { adjId: string; reason: string }) =>
      esopApi.rejectAdjustment(runId, adjId, reason).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['esop', 'latest'] }),
  })

  if (adjustments.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500 text-sm">No adjustments recorded.</div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Type
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Category
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Description
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Amount
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Evidence
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Status
            </th>
            {isAdmin && (
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide">
                Actions
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {adjustments.map((adj) => {
            const isPending = adj.approval_status === 'pending'
            return (
              <>
                <tr
                  key={adj.id}
                  className={clsx(
                    'hover:bg-slate-50 cursor-pointer',
                    adj.is_addback ? 'border-l-2 border-l-green-400' : 'border-l-2 border-l-red-400'
                  )}
                  onClick={() => setExpandedId((p) => (p === adj.id ? null : adj.id))}
                >
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        'text-xs font-semibold px-2 py-0.5 rounded-full',
                        adj.is_addback
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      )}
                    >
                      {adj.is_addback ? 'Add-back' : 'Deduction'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700 capitalize">
                    {adj.category.replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700 max-w-xs truncate">
                    {adj.description}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <MoneyDisplay
                      amount={adj.is_addback ? adj.amount : -adj.amount}
                      size="sm"
                    />
                  </td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <EvidenceLink evidenceId={adj.evidence_id} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={adj.approval_status} size="sm" />
                  </td>
                  {isAdmin && (
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      {isPending ? (
                        <ApprovalButton
                          size="sm"
                          onApprove={async (notes) => {
                            await approveAdj.mutateAsync({ adjId: adj.id, notes })
                          }}
                          onReject={async (reason) => {
                            await rejectAdj.mutateAsync({ adjId: adj.id, reason })
                          }}
                          disabled={approveAdj.isPending || rejectAdj.isPending}
                        />
                      ) : (
                        <span className="text-xs text-slate-400">
                          {adj.approved_by ?? '—'}
                        </span>
                      )}
                    </td>
                  )}
                </tr>
                {expandedId === adj.id && (
                  <tr key={`${adj.id}-expanded`}>
                    <td
                      colSpan={isAdmin ? 7 : 6}
                      className="px-6 py-4 bg-slate-50 border-b border-slate-200"
                    >
                      <div className="text-sm text-slate-700">
                        <p className="font-medium mb-1">Full Description</p>
                        <p className="text-slate-600 mb-3">{adj.description}</p>
                        {adj.notes && (
                          <>
                            <p className="font-medium mb-1">Notes</p>
                            <p className="text-slate-600 italic">{adj.notes}</p>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            )
          })}
        </tbody>
        <tfoot className="bg-slate-50 border-t-2 border-slate-300">
          <tr>
            <td colSpan={3} className="px-4 py-3 text-sm font-semibold text-slate-700">
              Net Adjustments
            </td>
            <td className="px-4 py-3 text-right">
              <MoneyDisplay
                amount={adjustments.reduce(
                  (sum, a) => sum + (a.is_addback ? a.amount : -a.amount),
                  0
                )}
                size="sm"
              />
            </td>
            <td colSpan={isAdmin ? 3 : 2} />
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
