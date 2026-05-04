import axios from 'axios'

// Import lazily to avoid circular dependency at module init time
let getAuthState: (() => { accessToken: string | null; logout: () => void }) | null = null

export function setAuthStateGetter(
  fn: () => { accessToken: string | null; logout: () => void }
) {
  getAuthState = fn
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = getAuthState?.().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      getAuthState?.().logout()
    }
    return Promise.reject(error)
  }
)
