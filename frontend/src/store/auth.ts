import { create } from 'zustand'
import type { User } from '../services/types'

interface AuthState {
  token: string | null
  user: User | null
  setToken: (t: string) => void
  setUser: (u: User | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('secflow_token'),
  user: null,
  setToken: (t) => {
    localStorage.setItem('secflow_token', t)
    set({ token: t })
  },
  setUser: (u) => set({ user: u }),
  logout: () => {
    localStorage.removeItem('secflow_token')
    set({ token: null, user: null })
  },
}))
