import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '../types/models'
import { setAuthStateGetter } from '../api/client'

interface AuthState {
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      login: (accessToken, user) =>
        set({ accessToken, user, isAuthenticated: true }),
      logout: () =>
        set({ accessToken: null, user: null, isAuthenticated: false }),
    }),
    { name: 'ybs-auth' }
  )
)

// Wire up the auth state getter for the API client (avoids circular imports)
setAuthStateGetter(() => ({
  accessToken: useAuthStore.getState().accessToken,
  logout: useAuthStore.getState().logout,
}))
