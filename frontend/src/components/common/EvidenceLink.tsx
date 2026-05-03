import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import clsx from 'clsx'

interface EvidenceLinkProps {
  evidenceId: string | null
  className?: string
}

export function EvidenceLink({ evidenceId, className }: EvidenceLinkProps) {
  const [copied, setCopied] = useState(false)

  if (!evidenceId) {
    return <span className="text-slate-400 text-sm italic">No evidence</span>
  }

  const truncated = `${evidenceId.slice(0, 8)}…${evidenceId.slice(-4)}`

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(evidenceId)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // clipboard not available
    }
  }

  return (
    <span className={clsx('inline-flex items-center gap-1.5 group', className)}>
      <span
        className="font-mono text-xs text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200"
        title={evidenceId}
      >
        {truncated}
      </span>
      <button
        onClick={handleCopy}
        className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-slate-600"
        title={copied ? 'Copied!' : 'Copy evidence ID'}
        type="button"
      >
        {copied ? (
          <Check className="w-3.5 h-3.5 text-green-600" />
        ) : (
          <Copy className="w-3.5 h-3.5" />
        )}
      </button>
    </span>
  )
}
