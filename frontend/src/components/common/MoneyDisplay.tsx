import clsx from 'clsx'

interface MoneyDisplayProps {
  amount: number | null | undefined
  colorize?: boolean
  isMargin?: boolean
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const USD = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
})

const USD_CENTS = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function MoneyDisplay({
  amount,
  colorize = true,
  isMargin = false,
  className,
  size = 'md',
}: MoneyDisplayProps) {
  if (amount == null) {
    return <span className={clsx('text-slate-400', className)}>—</span>
  }

  const formatted = Math.abs(amount) < 10000 ? USD_CENTS.format(amount) : USD.format(amount)

  const colorClass = colorize
    ? isMargin
      ? amount >= 0.25
        ? 'text-green-700'
        : amount >= 0.10
        ? 'text-yellow-700'
        : 'text-red-700'
      : amount < 0
      ? 'text-red-700'
      : 'text-green-700'
    : ''

  const sizeClass =
    size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-lg font-semibold' : 'text-base'

  return (
    <span className={clsx('font-mono tabular-nums', colorClass, sizeClass, className)}>
      {isMargin ? `${(amount * 100).toFixed(1)}%` : formatted}
    </span>
  )
}
