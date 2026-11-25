import { useState } from 'react'
import { useAction, useLoad } from '../api/hooks'
import type { Role, User } from '../api/types'
import { usersApi } from '../api/users'
import { useAuth } from '../auth/useAuth'
import { FeedbackLine } from '../components/FeedbackLine'
import { LoadState, Page } from '../components/Page'
import { ROLE } from '../labels'

/** As contas do site: mudar o papel e desbloquear (RN16). */
export function AdminUsersPage() {
  const { user: me } = useAuth()
  const users = useLoad(usersApi.all)
  const [search, setSearch] = useState('')

  const term = search.trim().toLowerCase()
  const found = users.data?.filter(
    (user) => user.name.toLowerCase().includes(term) || user.email.toLowerCase().includes(term),
  )

  return (
    <Page title="Usuários" subtitle="O papel de cada conta e o desbloqueio de quem errou demais.">
      <label>
        Buscar por nome ou e-mail
        <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} />
      </label>
      <LoadState loading={users.loading && !users.data} error={users.error} />
      {found?.length === 0 && <p>Nenhuma conta encontrada.</p>}
      {found && found.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Conta</th>
              <th>Papel</th>
              <th>Desbloqueio</th>
            </tr>
          </thead>
          <tbody>
            {found.map((user) => (
              <UserRow
                key={user.id}
                user={user}
                isMe={user.id === me?.id}
                onChanged={users.reload}
              />
            ))}
          </tbody>
        </table>
      )}
    </Page>
  )
}

function UserRow({ user, isMe, onChanged }: { user: User; isMe: boolean; onChanged: () => void }) {
  const [role, setRole] = useState<Role>(user.role)
  const action = useAction()

  async function handleRole() {
    const done = await action.run(
      () => usersApi.changeRole(user.id, role),
      `Agora o papel é ${ROLE[role]}.`,
    )
    if (done) onChanged()
  }

  return (
    <tr>
      <td>
        {user.name}
        <br />
        <span className="muted">{user.email}</span>
        <FeedbackLine feedback={action.feedback} />
      </td>
      <td>
        {/* ninguém muda o próprio papel, para o admin não se trancar para fora */}
        {isMe ? (
          <span className="muted">{ROLE[user.role]} (você)</span>
        ) : (
          <div className="inline">
            <select
              aria-label={`Papel de ${user.name}`}
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
            >
              {Object.entries(ROLE).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={action.pending || role === user.role}
              aria-label={`Mudar o papel de ${user.name}`}
              onClick={handleRole}
            >
              Mudar
            </button>
          </div>
        )}
      </td>
      <td>
        {/* só quem reivindica pode estar bloqueado. A API não diz quem está, então o botão
            aparece sempre; sem bloqueio, ele só zera as tentativas erradas */}
        {user.role === 'usuario' && (
          <button
            type="button"
            disabled={action.pending}
            aria-label={`Desbloquear ${user.name}`}
            onClick={() => action.run(() => usersApi.unblock(user.id), 'Pode reivindicar de novo.')}
          >
            Desbloquear
          </button>
        )}
      </td>
    </tr>
  )
}
