import { useCallback, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { useAction, useLoad } from '../api/hooks'
import { pointsApi } from '../api/points'
import type { CollectionPoint, User } from '../api/types'
import { usersApi } from '../api/users'
import { FeedbackLine } from '../components/FeedbackLine'
import { LoadState, Page } from '../components/Page'

/** Pontos de coleta e quem atende em cada um (RN40). */
export function AdminPointsPage() {
  const points = useLoad(pointsApi.all)
  const users = useLoad(usersApi.all)

  // só atendente entra num ponto: o admin já atende em todos
  const attendants = users.data?.filter((user) => user.role === 'atendente') ?? []

  return (
    <Page title="Pontos de coleta" subtitle="Os balcões e quem atende em cada um.">
      <NewPointForm onCreated={points.reload} />
      <LoadState
        loading={(points.loading && !points.data) || users.loading}
        error={points.error || users.error}
      />
      {points.data?.length === 0 && <p>Nenhum ponto de coleta ainda.</p>}
      {users.data && attendants.length === 0 && (
        <p>
          Nenhuma conta é de atendente ainda. Mude o papel em{' '}
          <Link to="/admin/usuarios">Usuários</Link>.
        </p>
      )}
      {users.data &&
        points.data?.map((point) => (
          <PointCard key={point.id} point={point} attendants={attendants} />
        ))}
    </Page>
  )
}

function NewPointForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('')
  const create = useAction()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const created = await create.run(() => pointsApi.create(name), `Ponto ${name.trim()} criado.`)
    if (!created) return
    setName('')
    onCreated()
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>Novo ponto</h2>
      <label>
        Nome
        <input value={name} maxLength={120} onChange={(e) => setName(e.target.value)} required />
      </label>
      <FeedbackLine feedback={create.feedback} />
      <button type="submit" disabled={create.pending}>
        {create.pending ? 'Criando…' : 'Criar ponto'}
      </button>
    </form>
  )
}

/** Um ponto. Cada cartão carrega os próprios atendentes, porque a API responde por ponto. */
function PointCard({ point, attendants }: { point: CollectionPoint; attendants: User[] }) {
  const load = useCallback(() => pointsApi.attendants(point.id), [point.id])
  const linked = useLoad(load)
  const [chosen, setChosen] = useState('')
  const action = useAction()

  const linkedIds = new Set(linked.data?.map((user) => user.id))
  const available = attendants.filter((user) => !linkedIds.has(user.id))

  async function handleLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const done = await action.run(
      () => pointsApi.link(point.id, Number(chosen)),
      'Atendente vinculado.',
    )
    if (!done) return
    setChosen('')
    linked.reload()
  }

  async function handleUnlink(user: User) {
    const done = await action.run(
      () => pointsApi.unlink(point.id, user.id),
      `${user.name} não atende mais aqui.`,
    )
    if (done) linked.reload()
  }

  return (
    <section className="card">
      <h2>{point.name}</h2>
      <LoadState loading={linked.loading && !linked.data} error={linked.error} />
      {linked.data?.length === 0 && <p className="muted">Nenhum atendente neste ponto.</p>}
      {linked.data && linked.data.length > 0 && (
        <table>
          <tbody>
            {linked.data.map((user) => (
              <tr key={user.id}>
                <td>
                  {user.name}
                  <br />
                  <span className="muted">
                    {user.email}
                    {/* quem mudou de papel mantém o vínculo, mas a API não o deixa mais atender */}
                    {user.role !== 'atendente' && ' · não é mais atendente'}
                  </span>
                </td>
                <td>
                  <button
                    type="button"
                    disabled={action.pending}
                    aria-label={`Desvincular ${user.name} de ${point.name}`}
                    onClick={() => handleUnlink(user)}
                  >
                    Desvincular
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <FeedbackLine feedback={action.feedback} />
      {linked.data && available.length > 0 && (
        <form className="inline" onSubmit={handleLink}>
          <select
            aria-label={`Atendente para ${point.name}`}
            value={chosen}
            onChange={(e) => setChosen(e.target.value)}
            required
          >
            <option value="" disabled>
              Escolha um atendente
            </option>
            {available.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name} ({user.email})
              </option>
            ))}
          </select>
          <button type="submit" disabled={action.pending}>
            Vincular
          </button>
        </form>
      )}
    </section>
  )
}
