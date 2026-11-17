import { createContext, useContext } from 'react'
import type { User } from '../api/types'

export type AuthState = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth() {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth precisa estar dentro do AuthProvider')
  return auth
}