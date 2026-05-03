export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ApiError {
  detail: string
  status_code: number
}

export interface ExceptionFilters {
  status?: string
  record_type?: string
  source_system?: string
  min_confidence?: number
  max_confidence?: number
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_dir?: 'asc' | 'desc'
}

export interface ApprovalFilters {
  status?: string
  risk_level?: string
  page?: number
  page_size?: number
}

export interface AgentTaskFilters {
  status?: string
  task_type?: string
  page?: number
  page_size?: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}
