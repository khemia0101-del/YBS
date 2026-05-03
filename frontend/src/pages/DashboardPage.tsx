import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Bot, Clock, CheckCircle, XCircle, Activity } from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { apiClient } from '../api/client'
import type { SystemHealth } from '../types/models'
import { useExceptionStats } from '../hooks/useExceptions'
import { usePendingApprovalCount } from '../hooks/useApprovals'
import clsx from 'clsx'

function useSystemHealth() {
  return useQuery({
    queryKey: ['system-health'],
    queryFn: () => apiClient.get<SystemHealth>('/system/health').then((r) => r.data),
    refetchInterval: 30_000,
    retry: false,
  })
}

interface SummaryCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ComponentType<{ className?: string }>
  onClick?: () => void
  accent?: 'blue' | 'yellow' | 'red' | 'green'
}

function SummaryCard({ title, value, subtitle, icon: Icon, onClick, accent = 'blue' }: SummaryCardProps) {
  const accentMap = {
    blue: 'bg-blue-100 text-blue-700',
    yellow: 'bg-yellow-100 text-yellow-700',
    red: 'bg-red-100 text-red-700',
    green: 'bg-green-100 text-green-700',
  }

  return (
    <div
      className={clsx('card px-5 py-5 flex items-center gap-4', onClick && 'cursor-pointer hover:shadow-md transition-shadow')}
      onClick={onClick}
    >
      <div className={clsx('w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0', accentMap[accent])}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-xs font-medium text-slate-500 mb-0.5">{title}</p>
        <p className="text-2xl font-bold text-slate-900">{value}</p>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const { data: health, isLoading: healthLoading } = useSystemHealth()
  const { data: stats } = useExceptionStats()
  const { data: pendingApprovals } = usePendingApprovalCount()

  const statusColor =
    health?.status === 'healthy'
      ? 'text-green-600 bg-green-100'
      : health?.status === 'degraded'
      ? 'text-yellow-600 bg-yellow-100'
      : 'text-red-600 bg-red-100'

  return (
    <div className="space-y-6">
      {/* System Health Banner */}
      <div className="card px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-primary" />
            <span className="font-semibold text-slate-900">System Health</span>
            {healthLoading ? (
              <div className="w-20 h-6 bg-slate-100 animate-pulse rounded-full" />
            ) : (
              <span className={clsx('text-xs font-semibold px-2.5 py-1 rounded-full capitalize', statusColor)}>
                {health?.status ?? 'Unknown'}
              </span>
            )}
          </div>
          <div className="flex items-center gap-5 text-sm text-slate-600">
            {health?.last_sync && (
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-slate-400" />
                Last sync: {formatDistanceToNow(new Date(health.last_sync), { addSuffix: true })}
              </span>
            )}
            {health?.last_profitability_run && (
              <span className="text-xs text-slate-400">
                Profitability: {format(new Date(health.last_profitability_run), 'MMM d')}
              </span>
            )}
            {health?.last_cash_forecast && (
              <span className="text-xs text-slate-400">
                Cash forecast: {format(new Date(health.last_cash_forecast), 'MMM d')}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          title="Pending Exceptions"
          value={stats?.pending ?? '—'}
          subtitle={`${stats?.needs_review ?? 0} needs review`}
          icon={AlertCircle}
          accent={stats && stats.pending > 10 ? 'red' : 'yellow'}
          onClick={() => navigate('/exceptions')}
        />
        <SummaryCard
          title="Pending Approvals"
          value={pendingApprovals ?? '—'}
          subtitle="Agent tasks awaiting review"
          icon={Bot}
          accent={pendingApprovals && pendingApprovals > 0 ? 'yellow' : 'green'}
          onClick={() => navigate('/agents')}
        />
        <SummaryCard
          title="Auto-Approved Today"
          value={stats?.auto_approved ?? '—'}
          subtitle="High-confidence records"
          icon={CheckCircle}
          accent="green"
        />
        <SummaryCard
          title="Rejected"
          value={stats?.rejected ?? '—'}
          subtitle="Require manual action"
          icon={XCircle}
          accent={stats && stats.rejected > 0 ? 'red' : 'blue'}
          onClick={() => navigate('/exceptions')}
        />
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Recent exceptions summary */}
        <div className="card px-5 py-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-900">Exception Summary</h3>
            <button
              type="button"
              onClick={() => navigate('/exceptions')}
              className="text-sm text-primary hover:underline"
            >
              View all →
            </button>
          </div>
          {stats ? (
            <div className="space-y-2.5">
              {[
                { label: 'Pending', value: stats.pending, color: 'bg-yellow-400' },
                { label: 'Needs Review', value: stats.needs_review, color: 'bg-orange-400' },
                { label: 'Auto-Approved', value: stats.auto_approved, color: 'bg-blue-400' },
                { label: 'Approved', value: stats.approved, color: 'bg-green-400' },
                { label: 'Rejected', value: stats.rejected, color: 'bg-red-400' },
              ].map((item) => {
                const pct = stats.total > 0 ? (item.value / stats.total) * 100 : 0
                return (
                  <div key={item.label} className="flex items-center gap-3">
                    <span className="text-sm text-slate-600 w-28 flex-shrink-0">{item.label}</span>
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${item.color}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-slate-700 w-10 text-right">
                      {item.value}
                    </span>
                  </div>
                )
              })}
              {stats.pending_financial_impact > 0 && (
                <p className="text-xs text-slate-500 pt-2 border-t border-slate-100 mt-2">
                  Pending financial impact:{' '}
                  <span className="font-semibold text-slate-700">
                    ${stats.pending_financial_impact.toLocaleString()}
                  </span>
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-6 bg-slate-100 animate-pulse rounded" />
              ))}
            </div>
          )}
        </div>

        {/* Quick nav */}
        <div className="card px-5 py-5">
          <h3 className="font-semibold text-slate-900 mb-4">Quick Access</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Financial Truth', path: '/financial', desc: 'Profitability & DSO' },
              { label: 'Cash Forecast', path: '/cash', desc: '13-week outlook' },
              { label: 'Decisions', path: '/decisions', desc: 'Pending decisions' },
              { label: 'ESOP / QoE', path: '/esop', desc: 'Normalized EBITDA' },
            ].map((item) => (
              <button
                key={item.path}
                type="button"
                onClick={() => navigate(item.path)}
                className="text-left p-3 rounded-lg border border-slate-200 hover:border-primary hover:bg-blue-50 transition-colors"
              >
                <p className="text-sm font-medium text-slate-900">{item.label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{item.desc}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
