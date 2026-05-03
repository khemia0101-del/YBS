import { NavLink } from 'react-router-dom'
import {
  AlertCircle,
  TrendingUp,
  DollarSign,
  Gavel,
  Users,
  Bot,
  Settings,
  LayoutDashboard,
} from 'lucide-react'
import clsx from 'clsx'
import { usePendingApprovalCount } from '../../hooks/useApprovals'
import { useAuthStore } from '../../stores/authStore'
import { UserRole } from '../../types/enums'

interface NavItem {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  adminOnly?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/exceptions', label: 'Exception Queue', icon: AlertCircle },
  { to: '/financial', label: 'Financial Truth', icon: TrendingUp },
  { to: '/cash', label: 'Cash Forecast', icon: DollarSign },
  { to: '/decisions', label: 'Decisions', icon: Gavel },
  { to: '/esop', label: 'ESOP / QoE', icon: Users },
  { to: '/agents', label: 'Agents', icon: Bot },
  { to: '/admin', label: 'Admin', icon: Settings, adminOnly: true },
]

export function Sidebar() {
  const { data: pendingCount } = usePendingApprovalCount()
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === UserRole.Admin

  return (
    <aside className="w-60 flex-shrink-0 bg-slate-900 text-slate-200 flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-700">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-white font-bold text-sm">
            Y
          </div>
          <div>
            <p className="text-sm font-bold text-white">YBS OS</p>
            <p className="text-xs text-slate-400">Operations Dashboard</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group relative',
                isActive
                  ? 'bg-primary text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              )
            }
          >
            <item.icon className="w-4.5 h-4.5 flex-shrink-0" />
            <span className="flex-1">{item.label}</span>
            {item.label === 'Agents' && pendingCount && pendingCount > 0 ? (
              <span className="ml-auto bg-yellow-500 text-yellow-950 text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[1.25rem] text-center">
                {pendingCount > 99 ? '99+' : pendingCount}
              </span>
            ) : null}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-slate-700">
        <p className="text-xs text-slate-500">v0.1.0</p>
      </div>
    </aside>
  )
}
