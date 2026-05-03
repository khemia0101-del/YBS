import { useState } from 'react'
import { CheckCircle, XCircle, X } from 'lucide-react'
import clsx from 'clsx'

interface ApprovalButtonProps {
  onApprove: (notes?: string) => Promise<void>
  onReject: (reason: string) => Promise<void>
  disabled?: boolean
  size?: 'sm' | 'md'
}

export function ApprovalButton({
  onApprove,
  onReject,
  disabled = false,
  size = 'md',
}: ApprovalButtonProps) {
  const [modal, setModal] = useState<'approve' | 'reject' | null>(null)
  const [notes, setNotes] = useState('')
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const handleApprove = async () => {
    setLoading(true)
    try {
      await onApprove(notes || undefined)
      setModal(null)
      setNotes('')
    } finally {
      setLoading(false)
    }
  }

  const handleReject = async () => {
    if (!reason.trim()) return
    setLoading(true)
    try {
      await onReject(reason)
      setModal(null)
      setReason('')
    } finally {
      setLoading(false)
    }
  }

  const btnSm = size === 'sm'

  return (
    <>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => setModal('approve')}
          className={clsx(
            'btn-success',
            btnSm ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm',
            'inline-flex items-center gap-1.5'
          )}
        >
          <CheckCircle className={btnSm ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
          Approve
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => setModal('reject')}
          className={clsx(
            'btn-danger',
            btnSm ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-sm',
            'inline-flex items-center gap-1.5'
          )}
        >
          <XCircle className={btnSm ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
          Reject
        </button>
      </div>

      {/* Approve Modal */}
      {modal === 'approve' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900">Confirm Approval</h3>
              <button
                onClick={() => setModal(null)}
                className="text-slate-400 hover:text-slate-600"
                type="button"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-slate-600 mb-4">
              Are you sure you want to approve this item? This action will be recorded in the audit log.
            </p>
            <div className="mb-4">
              <label className="label">Notes (optional)</label>
              <textarea
                className="input h-20 resize-none"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any review notes..."
              />
            </div>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setModal(null)}
                className="btn-secondary"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApprove}
                className="btn-success"
                disabled={loading}
              >
                {loading ? 'Approving…' : 'Approve'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {modal === 'reject' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-900">Confirm Rejection</h3>
              <button
                onClick={() => setModal(null)}
                className="text-slate-400 hover:text-slate-600"
                type="button"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-slate-600 mb-4">
              Provide a reason for rejection. This is required and will be visible in the audit log.
            </p>
            <div className="mb-4">
              <label className="label">
                Rejection Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                className="input h-24 resize-none"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Explain why this is being rejected..."
              />
              {reason.trim() === '' && (
                <p className="mt-1 text-xs text-red-500">Reason is required</p>
              )}
            </div>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setModal(null)}
                className="btn-secondary"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReject}
                className="btn-danger"
                disabled={loading || !reason.trim()}
              >
                {loading ? 'Rejecting…' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
