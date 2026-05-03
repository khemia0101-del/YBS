import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useAuthStore } from '../stores/authStore'
import { UserRole } from '../types/enums'
import type { User } from '../types/models'
import { ShieldAlert } from 'lucide-react'
import { format } from 'date-fns'
import { StatusBadge } from '../components/common/StatusBadge'

function useUsers() {
  return useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => apiClient.get<User[]>('/admin/users').then((r) => r.data),
  })
}

export function AdminPage() {
  const user = useAuthStore((s) => s.user)
  const { data: users, isLoading } = useUsers()

  if (user?.role !== UserRole.Admin) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-500">
        <ShieldAlert className="w-12 h-12 mb-4 text-red-400" />
        <p className="font-semibold text-slate-700">Access Denied</p>
        <p className="text-sm mt-1">This page requires admin privileges.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Admin</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          User management and system configuration.
        </p>
      </div>

      {/* Users table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-900">Users</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                {['Name', 'Email', 'Role', 'Active', 'Last Login'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wide"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {isLoading ? (
                [...Array(4)].map((_, i) => (
                  <tr key={i}>
                    {[...Array(5)].map((__, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 bg-slate-100 animate-pulse rounded" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : !users?.length ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500 text-sm">
                    No users found.
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm font-medium text-slate-900">
                      {u.full_name}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">{u.email}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={u.role} size="sm" />
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs font-medium ${
                          u.is_active ? 'text-green-700' : 'text-red-600'
                        }`}
                      >
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-500">
                      {u.last_login ? format(new Date(u.last_login), 'MMM d, yyyy') : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
