import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ConfidenceBadge } from '../common/ConfidenceBadge'
import { StatusBadge } from '../common/StatusBadge'
import { EvidenceLink } from '../common/EvidenceLink'
import { ApprovalButton } from '../common/ApprovalButton'
import { MatchSuggestions } from './MatchSuggestions'
import { MoneyDisplay } from '../common/MoneyDisplay'
import {
  useApproveException,
  useRejectException,
  useMatchException,
} from '../../hooks/useExceptions'
import type { StagedException } from '../../types/models'
import { ExceptionStatus } from '../../types/enums'

interface ExceptionCardProps {
  exception: StagedException
}

export function ExceptionCard({ exception }: ExceptionCardProps) {
  const [reviewNotes, setReviewNotes] = useState(exception.review_notes ?? '')
  const approve = useApproveException()
  const reject = useRejectException()
  const match = useMatchException()

  const isPending =
    exception.status === ExceptionStatus.Pending ||
    exception.status === ExceptionStatus.NeedsReview

  const handleApprove = async (notes?: string) => {
    await approve.mutateAsync({ id: exception.id, notes: notes || reviewNotes || undefined })
  }

  const handleReject = async (reason: string) => {
    await reject.mutateAsync({ id: exception.id, reason })
  }

  const handleAcceptMatch = async (entityId: string, entityType: string) => {
    await match.mutateAsync({ id: exception.id, entityId, entityType })
  }

  return (
    <div className="border border-slate-200 rounded-xl bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="text-xs font-mono text-slate-500">{exception.id.slice(0, 12)}…</span>
            <StatusBadge status={exception.status} size="sm" />
            <span className="text-xs text-slate-500">
              {exception.record_type} · {exception.source_system}
            </span>
          </div>
          <p className="text-sm text-slate-700 mt-1 font-medium">{exception.exception_reason}</p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <ConfidenceBadge score={exception.confidence_score} />
          {exception.financial_impact != null && (
            <MoneyDisplay amount={exception.financial_impact} size="sm" />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-slate-200">
        {/* Left: Extracted Data */}
        <div className="p-5">
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Extracted Data
          </h4>
          <div className="bg-slate-900 rounded-lg p-4 overflow-auto max-h-64">
            <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap break-words">
              {JSON.stringify(exception.extracted_data, null, 2)}
            </pre>
          </div>

          {/* Confidence Breakdown */}
          {Object.keys(exception.confidence_breakdown).length > 0 && (
            <div className="mt-4">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Confidence by Field
              </h4>
              <div className="space-y-1.5">
                {Object.entries(exception.confidence_breakdown).map(([field, score]) => {
                  const pct = Math.round((score as number) * 100)
                  return (
                    <div key={field} className="flex items-center gap-2">
                      <span className="text-xs text-slate-600 w-32 flex-shrink-0 capitalize">
                        {field.replace(/_/g, ' ')}
                      </span>
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full">
                        <div
                          className={`h-full rounded-full ${
                            pct >= 90 ? 'bg-green-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-slate-600 w-8 text-right">
                        {pct}%
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Evidence */}
          <div className="mt-4 flex items-center gap-2">
            <span className="text-xs text-slate-500">Evidence:</span>
            <EvidenceLink evidenceId={exception.evidence_id} />
          </div>

          {/* Audit trail */}
          {exception.reviewed_at && (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                Last Action
              </h4>
              <div className="text-xs text-slate-600 space-y-1">
                <p>
                  <span className="font-medium">{exception.reviewed_by ?? 'System'}</span> changed
                  status to{' '}
                  <StatusBadge status={exception.status} size="sm" />
                </p>
                <p className="text-slate-400">
                  {formatDistanceToNow(new Date(exception.reviewed_at), { addSuffix: true })}
                </p>
                {exception.review_notes && (
                  <p className="italic text-slate-500">&ldquo;{exception.review_notes}&rdquo;</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right: Match Suggestions + Actions */}
        <div className="p-5 flex flex-col gap-4">
          <MatchSuggestions
            candidates={exception.match_candidates ?? []}
            onAcceptMatch={handleAcceptMatch}
            isLoading={match.isPending}
          />

          {isPending && (
            <div className="border-t border-slate-100 pt-4 space-y-3">
              <div>
                <label className="label">Review Notes</label>
                <textarea
                  className="input h-20 resize-none text-sm"
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Optional review notes..."
                />
              </div>
              <ApprovalButton
                onApprove={handleApprove}
                onReject={handleReject}
                disabled={approve.isPending || reject.isPending}
              />
            </div>
          )}

          {!isPending && (
            <div className="border-t border-slate-100 pt-4">
              <p className="text-sm text-slate-500">
                This exception has been{' '}
                <StatusBadge status={exception.status} size="sm" />.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
