import { useEffect, useState, type ReactNode } from 'react'
import { api, clearToken, hasToken, saveToken, setOnSessionExpired } from '../api/client'
import type { Token, User } from '../api/types'
import { AuthContext } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(hasToken)

  useEffect(() => {
    setOnSessionExpired(() => setUser(null))
    if (!hasToken()) return
    api<User>('/v1/auth/me')
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const token = await api<Token>('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    saveToken(token.access_token)
    setUser(await api<User>('/v1/auth/me'))
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  return <AuthContext value={{ user, loading, login, logout }}>{children}</AuthContext>
}