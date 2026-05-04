import { apiClient } from './client'
import type { LoginResponse } from '../types/api'
import type { User } from '../types/models'

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<LoginResponse>('/auth/login', { email, password }),

  logout: () => apiClient.post('/auth/logout'),

  me: () => apiClient.get<User>('/auth/me'),

  refreshToken: () => apiClient.post<LoginResponse>('/auth/refresh'),
}
