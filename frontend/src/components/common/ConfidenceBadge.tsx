import clsx from 'clsx'

interface ConfidenceBadgeProps {
  score: number
  size?: 'sm' | 'md'
}

function getConfidenceColor(score: number) {
  if (score >= 0.92) return { dot: 'bg-green-500', text: 'text-green-700', bg: 'bg-green-50' }
  if (score >= 0.70) return { dot: 'bg-yellow-500', text: 'text-yellow-700', bg: 'bg-yellow-50' }
  return { dot: 'bg-red-500', text: 'text-red-700', bg: 'bg-red-50' }
}

export function ConfidenceBadge({ score, size = 'md' }: ConfidenceBadgeProps) {
  const colors = getConfidenceColor(score)
  const pct = Math.round(score * 100)

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        colors.bg,
        colors.text,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
      )}
    >
      <span
        className={clsx(
          'rounded-full flex-shrink-0',
          colors.dot,
          size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'
        )}
      />
      {pct}%
    </span>
  )
}
