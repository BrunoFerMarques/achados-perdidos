import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { useAuth } from './useAuth'

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <p>Carregando…</p>
  // depois do login a pessoa volta pra cá (ex.: pro item que ela ia reivindicar)
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return children
}
