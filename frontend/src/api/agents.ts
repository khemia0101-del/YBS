import { apiClient } from './client'
import type { AgentTask, AgentActionLog, ApprovalRequest } from '../types/models'
import type { PaginatedResponse, AgentTaskFilters, ApprovalFilters } from '../types/api'

export const agentsApi = {
  getTasks: (params: AgentTaskFilters = {}) =>
    apiClient.get<PaginatedResponse<AgentTask>>('/agents/tasks', { params }),

  getTask: (id: string) =>
    apiClient.get<AgentTask>(`/agents/tasks/${id}`),

  cancelTask: (id: string) =>
    apiClient.post<AgentTask>(`/agents/tasks/${id}/cancel`),

  retryTask: (id: string) =>
    apiClient.post<AgentTask>(`/agents/tasks/${id}/retry`),

  getTaskLogs: (taskId: string) =>
    apiClient.get<AgentActionLog[]>(`/agents/tasks/${taskId}/logs`),

  getApprovalRequests: (params: ApprovalFilters = {}) =>
    apiClient.get<PaginatedResponse<ApprovalRequest>>('/agents/approvals', { params }),

  approveRequest: (id: string, notes?: string) =>
    apiClient.post<ApprovalRequest>(`/agents/approvals/${id}/approve`, { notes }),

  rejectRequest: (id: string, reason: string) =>
    apiClient.post<ApprovalRequest>(`/agents/approvals/${id}/reject`, { reason }),

  getPendingApprovalCount: () =>
    apiClient.get<{ count: number }>('/agents/approvals/count'),
}
