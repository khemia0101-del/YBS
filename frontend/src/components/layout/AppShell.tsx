import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/exceptions': 'Exception Queue',
  '/financial': 'Financial Truth',
  '/cash': 'Cash Forecast',
  '/decisions': 'Decisions',
  '/esop': 'ESOP / QoE',
  '/agents': 'Agents',
  '/admin': 'Admin',
}

export function AppShell() {
  const location = useLocation()
  const pageTitle = PAGE_TITLES[location.pathname] ?? ''

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar pageTitle={pageTitle} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
