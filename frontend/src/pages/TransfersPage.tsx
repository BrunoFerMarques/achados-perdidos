import { useState, type FormEvent } from 'react'
import { useAction, useLoad } from '../api/hooks'
import { transfersApi } from '../api/items'
import { pointsApi, usePoints } from '../api/points'
import type { CollectionPoint, ItemTransfer } from '../api/types'
import { FeedbackLine } from '../components/FeedbackLine'
import { LoadState, Page } from '../components/Page'
import { formatDate } from '../labels'

/** Moving an item between collection points (RN05): the origin sends it, the destination
 * confirms the arrival. The API checks that each attendant works at the right end (RN41). */
export function TransfersPage() {
  const myPoints = useLoad(pointsApi.mine)
  const transfers = useLoad(transfersApi.list)
  const { points, pointName } = usePoints()
  const action = useAction()

  const mine = new Set(myPoints.data?.map((point) => point.id))

  async function arrive(item: ItemTransfer) {
    await action.run(() => transfersApi.arrive(item.id), `Chegada do item nº ${item.id} confirmada.`)
    transfers.reload()
  }

  return (
    <Page title="Transferências">
      <SendForm points={points} pointName={pointName} onSent={transfers.reload} />

      <h2>A caminho</h2>
      <FeedbackLine feedback={action.feedback} />
      <LoadState
        loading={transfers.loading || myPoints.loading}
        error={transfers.error || myPoints.error}
      />
      {transfers.data?.length === 0 && <p>Nenhum item a caminho dos seus pontos.</p>}
      {transfers.data && transfers.data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>De</th>
              <th>Para</th>
              <th>Ação</th>
            </tr>
          </thead>
          <tbody>
            {transfers.data.map((item) => (
              <tr key={item.id}>
                <td>
                  nº {item.id}: {item.description}
                  <br />
                  <span className="muted">achado em {formatDate(item.found_date)}</span>
                </td>
                <td>{pointName(item.collection_point_id)}</td>
                <td>{item.transfer_to_id !== null && pointName(item.transfer_to_id)}</td>
                <td>
                  {item.transfer_to_id !== null && mine.has(item.transfer_to_id) ? (
                    <button
                      type="button"
                      disabled={action.pending}
                      aria-label={`Confirmar a chegada do item nº ${item.id}`}
                      onClick={() => arrive(item)}
                    >
                      Confirmar chegada
                    </button>
                  ) : (
                    <span className="muted">Saindo daqui</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Page>
  )
}

function SendForm({
  points,
  pointName,
  onSent,
}: {
  points: CollectionPoint[]
  pointName: (id: number) => string
  onSent: () => void
}) {
  const [itemId, setItemId] = useState('')
  const [destination, setDestination] = useState('')
  const send = useAction()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const to = Number(destination)
    const sent = await send.run(
      () => transfersApi.send(Number(itemId), to),
      `Item nº ${itemId} enviado para ${pointName(to)}.`,
    )
    if (!sent) return
    setItemId('')
    onSent()
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Enviar item</h2>
      <p className="muted">
        Só um item disponível no seu ponto pode ser enviado; um item reservado espera o dono onde
        está.
      </p>
      <label>
        Número do item
        <input
          type="number"
          min={1}
          value={itemId}
          onChange={(e) => setItemId(e.target.value)}
          required
        />
      </label>
      <label>
        Para o ponto
        <select value={destination} onChange={(e) => setDestination(e.target.value)} required>
          <option value="" disabled>
            Escolha o destino
          </option>
          {points.map((point) => (
            <option key={point.id} value={point.id}>
              {point.name}
            </option>
          ))}
        </select>
      </label>
      <FeedbackLine feedback={send.feedback} />
      <button type="submit" disabled={send.pending}>
        {send.pending ? 'Enviando…' : 'Enviar'}
      </button>
    </form>
  )
}
