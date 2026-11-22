import type { ReactNode } from 'react'
import type { Role } from '../api/types'
import { Page } from '../components/Page'
import { RequireAuth } from './RequireAuth'
import { useAuth } from './useAuth'

/** RequireAuth, and then only for some roles. It only hides the screen: the API is what refuses
 * (domain/permissions.py), so a forced URL still gets a 403 from it. */
export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  return (
    <RequireAuth>
      <RoleGate roles={roles}>{children}</RoleGate>
    </RequireAuth>
  )
}

function RoleGate({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user } = useAuth()
  if (!user || !roles.includes(user.role)) {
    return <Page title="Acesso negado">Esta tela não é para o seu perfil.</Page>
  }
  return children
}
