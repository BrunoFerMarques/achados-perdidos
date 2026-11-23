import { useState, type FormEvent } from 'react'
import { claimsApi } from '../api/claims'
import { useAction, useLoad, type Feedback } from '../api/hooks'
import { pointsApi } from '../api/points'
import type { ClaimPickup } from '../api/types'
import { FeedbackLine } from '../components/FeedbackLine'
import { LoadState, Page } from '../components/Page'
import { formatDateTime, isPast } from '../labels'

/** Retirada no balcão: escolhe o balcão, acha quem veio buscar qual item, digita o código
 * que a pessoa mostra e confirma o documento com foto. */
export function PickupPage() {
  const points = useLoad(pointsApi.mine)
  const queue = useLoad(claimsApi.approved)
  const [chosen, setChosen] = useState<number | null>(null)
  const [done, setDone] = useState<Feedback | null>(null)

  // começa no primeiro ponto do atendente até ele escolher outro
  const counter = chosen ?? points.data?.[0]?.id ?? null
  // o código só vale onde o item está, então a fila mostra só os itens desse balcão
  const waiting = queue.data?.filter((claim) => claim.collection_point_id === counter) ?? []

  function handOver(claim: ClaimPickup) {
    setDone({
      ok: true,
      text: `Retirada concluída: item nº ${claim.item_id} entregue a ${claim.claimant_name}.`,
    })
    queue.reload()
  }

  return (
    <Page title="Retirada no balcão">
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
      {queue.data && counter !== null && waiting.length === 0 && (
        <p>Ninguém aguardando retirada neste balcão.</p>
      )}
      {counter !== null &&
        waiting.map((claim) => (
          <PickupCard key={claim.id} claim={claim} counter={counter} onDone={() => handOver(claim)} />
        ))}
    </Page>
  )
}

function PickupCard({
  claim,
  counter,
  onDone,
}: {
  claim: ClaimPickup
  counter: number
  onDone: () => void
}) {
  const [code, setCode] = useState('')
  const [documentChecked, setDocumentChecked] = useState(false)
  const send = useAction()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const handed = await send.run(() =>
      claimsApi.pickUp(claim.id, {
        collection_point_id: counter,
        pickup_code: code,
        document_checked: documentChecked,
      }),
    )
    if (handed) onDone()
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>
        Item nº {claim.item_id}: {claim.item_description}
      </h2>
      <p>
        Para <strong>{claim.claimant_name}</strong>
      </p>
      {claim.pickup_deadline && (
        <p className={isPast(claim.pickup_deadline) ? 'error' : 'muted'}>
          {isPast(claim.pickup_deadline) ? 'Prazo vencido em ' : 'Retirar até '}
          {formatDateTime(claim.pickup_deadline)}
        </p>
      )}
      <label>
        Código que a pessoa mostrou (6 letras ou números)
        <input
          type="text"
          minLength={6}
          maxLength={6}
          pattern="[A-Za-z0-9]{6}"
          autoComplete="off"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          required
        />
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={documentChecked}
          onChange={(e) => setDocumentChecked(e.target.checked)}
        />
        Conferi o documento com foto, no nome de {claim.claimant_name}
      </label>
      <FeedbackLine feedback={send.feedback} />
      <button type="submit" disabled={send.pending}>
        {send.pending ? 'Concluindo…' : 'Concluir retirada'}
      </button>
    </form>
  )
}
