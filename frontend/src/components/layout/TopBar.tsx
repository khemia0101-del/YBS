import { Bell, LogOut, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { useAuthStore } from '../../stores/authStore'
import { usePendingApprovalCount } from '../../hooks/useApprovals'
import { authApi } from '../../api/auth'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'

interface TopBarProps {
  pageTitle?: string
}

export function TopBar({ pageTitle }: TopBarProps) {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const { data: pendingCount } = usePendingApprovalCount()
  const navigate = useNavigate()
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch {
      // best effort
    }
    logout()
    navigate('/login', { replace: true })
  }

  const roleColors: Record<string, string> = {
    admin: 'bg-purple-100 text-purple-800',
    analyst: 'bg-blue-100 text-blue-800',
    operator: 'bg-green-100 text-green-800',
    viewer: 'bg-slate-100 text-slate-600',
  }

  const roleBadgeClass = user?.role ? (roleColors[user.role] ?? 'bg-slate-100 text-slate-600') : ''

  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0">
      <div className="flex items-center gap-3">
        {pageTitle && (
          <h1 className="text-lg font-semibold text-slate-900">{pageTitle}</h1>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Notification Bell */}
        <button
          type="button"
          onClick={() => navigate('/agents')}
          className="relative p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
          title="Pending approvals"
        >
          <Bell className="w-5 h-5" />
          {pendingCount && pendingCount > 0 ? (
            <span className="absolute top-1 right-1 w-2 h-2 bg-yellow-500 rounded-full" />
          ) : null}
        </button>

        {/* User Menu */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setUserMenuOpen((o) => !o)}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
              {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <div className="text-left hidden sm:block">
              <p className="text-sm font-medium text-slate-900 leading-tight">
                {user?.full_name ?? 'User'}
              </p>
              {user?.role && (
                <span
                  className={clsx(
                    'text-xs px-1.5 py-0.5 rounded-full font-medium',
                    roleBadgeClass
                  )}
                >
                  {user.role}
                </span>
              )}
            </div>
            <ChevronDown className="w-4 h-4 text-slate-400 hidden sm:block" />
          </button>

          {userMenuOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setUserMenuOpen(false)}
              />
              <div className="absolute right-0 top-full mt-1 z-20 w-52 bg-white rounded-lg shadow-lg border border-slate-200 py-1">
                <div className="px-4 py-2 border-b border-slate-100">
                  <p className="text-xs font-medium text-slate-900">{user?.full_name}</p>
                  <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
