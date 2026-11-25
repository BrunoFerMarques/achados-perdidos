import { useState, type FormEvent } from 'react'
import { useCatalog } from '../api/catalog'
import { useAction, useLoad, type Feedback } from '../api/hooks'
import { receiptsApi } from '../api/items'
import { pointsApi, usePoints } from '../api/points'
import type { RegisteredItem } from '../api/types'
import { FeedbackLine } from '../components/FeedbackLine'
import { LoadState, Page } from '../components/Page'
import { formatDate } from '../labels'

/** Recebimento no balcão (RN02): escolhe o balcão, acha o item que a pessoa trouxe, ajusta a
 * descrição pública se precisar (RN51) e confirma. */
export function ReceiveItemsPage() {
  const points = useLoad(pointsApi.mine)
  const queue = useLoad(receiptsApi.list)
  const { categories, locations, colors } = useCatalog()
  const { pointName } = usePoints()
  const [chosen, setChosen] = useState<number | null>(null)
  const [done, setDone] = useState<Feedback | null>(null)

  // começa no primeiro ponto do atendente até ele escolher outro
  const counter = chosen ?? points.data?.[0]?.id ?? null

  function received(item: RegisteredItem, pointId: number) {
    setDone({
      ok: true,
      text: `Item nº ${item.id} recebido em ${pointName(pointId)}. Ele já aparece no mural.`,
    })
    queue.reload()
  }

  return (
    <Page title="Receber itens">
      <LoadState loading={points.loading} error={points.error} />
      {points.data?.length === 0 && <p>Você não está vinculado a nenhum ponto de coleta.</p>}
      {points.data && points.data.length > 0 && (
        <label>
          Balcão
          <select
            value={counter ?? ''}
            onChange={(e) => {
              setChosen(Number(e.target.value))
              setDone(null)
            }}
          >
            {points.data.map((point) => (
              <option key={point.id} value={point.id}>
                {point.name}
              </option>
            ))}
          </select>
        </label>
      )}
      <FeedbackLine feedback={done} />
      {!points.loading && <LoadState loading={queue.loading} error={queue.error} />}
      {queue.data?.length === 0 && counter !== null && <p>Nenhum item esperando recebimento.</p>}
      {/* RN02: a fila não é filtrada pelo balcão, qualquer ponto pode receber qualquer item */}
      {counter !== null &&
        queue.data?.map((item) => (
          <ReceiveCard
            key={item.id}
            item={item}
            counter={counter}
            details={[
              categories.nameOf(item.category_id),
              colors.nameOf(item.color_id),
              `achado em ${locations.nameOf(item.location_id)}`,
              formatDate(item.found_date),
            ].join(' · ')}
            expectedPoint={pointName(item.collection_point_id)}
            onDone={() => received(item, counter)}
          />
        ))}
    </Page>
  )
}

function ReceiveCard({
  item,
  counter,
  details,
  expectedPoint,
  onDone,
}: {
  item: RegisteredItem
  counter: number
  details: string
  expectedPoint: string
  onDone: () => void
}) {
  // começa com o texto do achador; o atendente só mexe se precisar
  const [description, setDescription] = useState(item.description)
  const send = useAction()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const ok = await send.run(() =>
      receiptsApi.receive(item.id, { collection_point_id: counter, description }),
    )
    if (ok) onDone()
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Item nº {item.id}</h2>
      <p>{details}</p>
      <p className="muted">O achador indicou o ponto: {expectedPoint}</p>
      <label>
        Descrição pública
        <textarea
          required
          maxLength={500}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <p className="muted">
        Todos vão ler este texto. Tire o que só o dono saberia (nome, número, marca escondida).
      </p>
      <FeedbackLine feedback={send.feedback} />
      <button
        type="submit"
        disabled={send.pending}
        aria-label={`Confirmar recebimento do item nº ${item.id}`}
      >
        {send.pending ? 'Recebendo…' : 'Confirmar recebimento'}
      </button>
    </form>
  )
}