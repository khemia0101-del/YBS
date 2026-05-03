import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentsApi } from '../../api/agents'
import { DataTable, type Column } from '../common/DataTable'
import { StatusBadge } from '../common/StatusBadge'
import type { AgentTask } from '../../types/models'
import { AgentTaskStatus } from '../../types/enums'
import { formatDistanceToNow } from 'date-fns'
import { XCircle, RefreshCw, FileText } from 'lucide-react'
import clsx from 'clsx'

const PRIORITY_LABELS: Record<number, { label: string; class: string }> = {
  1: { label: 'Critical', class: 'text-red-700 bg-red-100' },
  2: { label: 'High', class: 'text-orange-700 bg-orange-100' },
  3: { label: 'Medium', class: 'text-yellow-700 bg-yellow-100' },
  4: { label: 'Low', class: 'text-slate-600 bg-slate-100' },
}

interface TaskLogsModalProps {
  taskId: string
  onClose: () => void
}

function TaskLogsModal({ taskId, onClose }: TaskLogsModalProps) {
  const { data: logs, isLoading } = useQuery({
    queryKey: ['agent-logs', taskId],
    queryFn: () => agentsApi.getTaskLogs(taskId).then((r) => r.data),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-900">Task Action Logs</h3>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <XCircle className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-14 bg-slate-100 animate-pulse rounded-lg" />
              ))}
            </div>
          ) : !logs?.length ? (
            <p className="text-center text-slate-500 text-sm py-8">No action logs.</p>
          ) : (
            <div className="space-y-3">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className={clsx(
                    'border rounded-lg p-3',
                    log.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span
                        className={clsx(
                          'text-xs font-semibold px-2 py-0.5 rounded',
                          log.success
                            ? 'bg-green-200 text-green-800'
                            : 'bg-red-200 text-red-800'
                        )}
                      >
                        {log.action_type}
                      </span>
                      <p className="text-sm text-slate-700 mt-1">{log.description}</p>
                      {log.error_message && (
                        <p className="text-xs text-red-700 mt-1 font-mono">{log.error_message}</p>
                      )}
                    </div>
                    <span className="text-xs text-slate-400 flex-shrink-0">
                      {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface AgentTaskListProps {
  statusFilter?: AgentTaskStatus | ''
}

export function AgentTaskList({ statusFilter = '' }: AgentTaskListProps) {
  const [page, setPage] = useState(1)
  const [logTaskId, setLogTaskId] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['agent-tasks', statusFilter, page],
    queryFn: () =>
      agentsApi
        .getTasks({ ...(statusFilter && { status: statusFilter }), page, page_size: 20 })
        .then((r) => r.data),
  })

  const cancelTask = useMutation({
    mutationFn: (id: string) => agentsApi.cancelTask(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agent-tasks'] }),
  })

  const retryTask = useMutation({
    mutationFn: (id: string) => agentsApi.retryTask(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agent-tasks'] }),
  })

  const columns: Column<AgentTask>[] = [
    {
      key: 'task_type',
      header: 'Task Type',
      render: (row) => (
        <span className="text-sm font-medium text-slate-800 capitalize">
          {row.task_type.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      className: 'max-w-xs',
      render: (row) => (
        <span className="text-sm text-slate-600 truncate block max-w-xs" title={row.description}>
          {row.description}
        </span>
      ),
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (row) => {
        const p = PRIORITY_LABELS[row.priority] ?? PRIORITY_LABELS[4]
        return (
          <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', p.class)}>
            {p.label}
          </span>
        )
      },
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <StatusBadge status={row.status} size="sm" />,
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (row) => (
        <span className="text-xs text-slate-500">
          {formatDistanceToNow(new Date(row.created_at), { addSuffix: true })}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setLogTaskId(row.id)}
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            <FileText className="w-3.5 h-3.5" />
            Logs
          </button>
          {(row.status === AgentTaskStatus.Queued ||
            row.status === AgentTaskStatus.Running) && (
            <button
              type="button"
              onClick={() => cancelTask.mutate(row.id)}
              disabled={cancelTask.isPending}
              className="text-xs text-red-600 hover:underline flex items-center gap-1"
            >
              <XCircle className="w-3.5 h-3.5" />
              Cancel
            </button>
          )}
          {row.status === AgentTaskStatus.Failed && (
            <button
              type="button"
              onClick={() => retryTask.mutate(row.id)}
              disabled={retryTask.isPending}
              className="text-xs text-slate-600 hover:underline flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry
            </button>
          )}
        </div>
      ),
    },
  ]

  return (
    <>
      <DataTable
        columns={columns}
        data={data?.items ?? []}
        keyExtractor={(row) => row.id}
        isLoading={isLoading}
        emptyMessage="No tasks found."
        totalItems={data?.total ?? 0}
        currentPage={page}
        pageSize={20}
        onPageChange={setPage}
      />
      {logTaskId && (
        <TaskLogsModal taskId={logTaskId} onClose={() => setLogTaskId(null)} />
      )}
    </>
  )
}
