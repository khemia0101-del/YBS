import { useState } from 'react'
import { AgentTaskList } from '../components/agents/AgentTaskList'
import { ApprovalQueue } from '../components/agents/ApprovalQueue'
import { usePendingApprovalCount } from '../hooks/useApprovals'
import { AgentTaskStatus } from '../types/enums'
import clsx from 'clsx'

type Tab = 'active' | 'approvals' | 'completed'

const TABS = [
  { id: 'active' as Tab, label: 'Active Tasks' },
  { id: 'approvals' as Tab, label: 'Pending Approvals' },
  { id: 'completed' as Tab, label: 'Completed / Failed' },
]

export function AgentsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('approvals')
  const { data: pendingCount } = usePendingApprovalCount()

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Agents</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Monitor agent tasks, review pending approvals, and inspect action logs.
        </p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
              )}
            >
              {tab.label}
              {tab.id === 'approvals' && pendingCount && pendingCount > 0 ? (
                <span className="bg-yellow-500 text-yellow-950 text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[1.25rem] text-center">
                  {pendingCount}
                </span>
              ) : null}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'active' && (
          <AgentTaskList statusFilter={AgentTaskStatus.Running} />
        )}
        {activeTab === 'approvals' && <ApprovalQueue />}
        {activeTab === 'completed' && (
          <AgentTaskList statusFilter={AgentTaskStatus.Completed} />
        )}
      </div>
    </div>
  )
}
