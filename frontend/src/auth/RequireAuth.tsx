import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { useAuth } from './useAuth'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <p>Carregando…</p>
  // the login page sends the user back here (e.g. to the item they were about to claim)
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}
