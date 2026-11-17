import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useAuth } from './useAuth'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <p>Carregando…</p>
  if (!user) return <Navigate to="/login" replace />
  return children
}