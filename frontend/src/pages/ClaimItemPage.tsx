import { useCallback, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { claimsApi } from '../api/claims'
import { useAction, useLoad } from '../api/hooks'
import type { Claim } from '../api/types'
import { FeedbackLine } from '../components/FeedbackLine'
import { LoadState, Page } from '../components/Page'

/** The route: checks the id, and gives each item its own form (`key`), so going from one item to
 * another never keeps the answers or the result of the previous one. */
export function ClaimItemRoute() {
  const itemId = Number(useParams().id)
  if (!Number.isInteger(itemId) || itemId <= 0) {
    return <Page title="Reivindicar item">Item inválido.</Page>
  }
  return <ClaimItemPage key={itemId} itemId={itemId} />
}

/** Claiming an item (scope §6, §7): one answer per verification question. The public listing
 * links here; the questions only show up once the user is logged in (RN50). */
function ClaimItemPage({ itemId }: { itemId: number }) {
  const loadQuestions = useCallback(() => claimsApi.questions(itemId), [itemId])
  const { data: questions, error, loading } = useLoad(loadQuestions)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [claim, setClaim] = useState<Claim | null>(null)
  const send = useAction()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!questions) return
    await send.run(async () => {
      setClaim(await claimsApi.create(itemId, questions.map((q) => answers[q.position] ?? '')))
    })
  }

  if (claim) {
    return (
      <Page title="Reivindicar item">
        {claim.status === 'pendente' ? (
          <p className="ok">
            Sua reivindicação está em análise. O atendente do ponto de coleta vai conferir as
            respostas.
          </p>
        ) : (
          // RN21: only the result, never the score or which answers were wrong
          <p className="error">Sua reivindicação foi rejeitada.</p>
        )}
        <p>
          <Link to="/reivindicacoes">Ver minhas reivindicações</Link>
        </p>
      </Page>
    )
  }

  return (
    <Page title={`Reivindicar o item nº ${itemId}`}>
      <LoadState loading={loading} error={error} />
      {questions && (
        <form onSubmit={handleSubmit}>
          <p className="muted">
            Responda o que souber sobre o objeto. Quem achou fez estas perguntas para confirmar
            que ele é seu; deixar em branco conta como resposta errada.
          </p>
          {questions.map((q) => (
            <label key={q.position}>
              {q.question}
              <input
                type="text"
                maxLength={500}
                value={answers[q.position] ?? ''}
                onChange={(e) => setAnswers({ ...answers, [q.position]: e.target.value })}
              />
            </label>
          ))}
          <FeedbackLine feedback={send.feedback} />
          <button type="submit" disabled={send.pending}>
            {send.pending ? 'Enviando…' : 'Enviar reivindicação'}
          </button>
        </form>
      )}
    </Page>
  )
}
