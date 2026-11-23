import type { ReactNode } from 'react'
import type { Role } from '../api/types'
import { Page } from '../components/Page'
import { RequireAuth } from './RequireAuth'
import { useAuth } from './useAuth'

/** Igual ao RequireAuth, mas só pra alguns papéis. Só esconde a tela, quem bloqueia de verdade
 * é a API (se alguém forçar a URL, leva 403). */
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
