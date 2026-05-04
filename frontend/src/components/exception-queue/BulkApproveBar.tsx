import { CheckCircle, X } from 'lucide-react'
import { useBulkApproveExceptions } from '../../hooks/useExceptions'
import { useExceptionStore } from '../../stores/exceptionStore'

interface BulkApproveBarProps {
  selectedCount: number
  selectedIds: string[]
}

export function BulkApproveBar({ selectedCount, selectedIds }: BulkApproveBarProps) {
  const clearSelected = useExceptionStore((s) => s.clearSelected)
  const bulkApprove = useBulkApproveExceptions()

  if (selectedCount === 0) return null

  const handleBulkApprove = async () => {
    const result = await bulkApprove.mutateAsync(selectedIds)
    clearSelected()
    // brief toast-like behavior via alert for now
    if (result.failed > 0) {
      console.warn(`${result.failed} exceptions failed to approve`)
    }
  }

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-4 bg-slate-900 text-white px-5 py-3.5 rounded-2xl shadow-2xl border border-slate-700 animate-in slide-in-from-bottom-4 duration-200">
      <span className="text-sm font-medium">
        <span className="text-yellow-400 font-bold">{selectedCount}</span>{' '}
        {selectedCount === 1 ? 'item' : 'items'} selected
      </span>

      <div className="w-px h-5 bg-slate-600" />

      <button
        type="button"
        onClick={handleBulkApprove}
        disabled={bulkApprove.isPending}
        className="flex items-center gap-2 px-3.5 py-1.5 bg-success text-white rounded-lg text-sm font-medium hover:bg-green-600 transition-colors disabled:opacity-50"
      >
        <CheckCircle className="w-4 h-4" />
        {bulkApprove.isPending ? 'Approving…' : 'Approve All'}
      </button>

      <button
        type="button"
        onClick={clearSelected}
        className="flex items-center gap-1.5 px-3 py-1.5 text-slate-300 hover:text-white rounded-lg text-sm hover:bg-slate-700 transition-colors"
      >
        <X className="w-4 h-4" />
        Deselect All
      </button>
    </div>
  )
}
