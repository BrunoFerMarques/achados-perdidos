import { claimsApi } from '../api/claims'
import { useAction, useLoad } from '../api/hooks'
import { usePoints } from '../api/points'
import type { ClaimReview } from '../api/types'
import { FeedbackLine } from '../components/FeedbackLine'
import { LoadState, Page } from '../components/Page'
import { formatDateTime } from '../labels'

/** Análise do atendente: nota e cada resposta do lado da esperada, só dos pontos dele.
 * Aprovar reserva o item e gera o código de retirada. */
export function ReviewClaimsPage() {
  const { data: claims, error, loading, reload } = useLoad(claimsApi.pending)
  const { pointName } = usePoints()
  const action = useAction()

  async function approve(claim: ClaimReview) {
    await action.run(
      () => claimsApi.approve(claim.id),
      `Reivindicação nº ${claim.id} aprovada: o item ficou reservado.`,
    )
    reload()
  }

  async function reject(claim: ClaimReview) {
    if (!window.confirm(`Rejeitar a reivindicação nº ${claim.id}?`)) return
    await action.run(() => claimsApi.reject(claim.id), `Reivindicação nº ${claim.id} rejeitada.`)
    reload()
  }

  return (
    <Page title="Analisar reivindicações">
      <FeedbackLine feedback={action.feedback} />
      <LoadState loading={loading} error={error} />
      {claims?.length === 0 && <p>Nenhuma reivindicação esperando análise nos seus pontos.</p>}
      {claims?.map((claim) => (
        <section key={claim.id} className="card">
          <h2>
            Reivindicação nº {claim.id} · item nº {claim.item_id}: {claim.item_description}
          </h2>
          <p>
            {pointName(claim.collection_point_id)} · feita em {formatDateTime(claim.created_at)}
          </p>
          <p>
            Nota: <strong>{Math.round(claim.score * 100)}%</strong> das respostas certas
          </p>
          <table>
            <thead>
              <tr>
                <th>Pergunta</th>
                <th>Resposta esperada</th>
                <th>Resposta dada</th>
              </tr>
            </thead>
            <tbody>
              {claim.answers.map((answer) => (
                <tr key={answer.position}>
                  <td>{answer.question}</td>
                  <td>{answer.expected}</td>
                  <td>{answer.given || <em>em branco</em>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="actions">
            <button
              type="button"
              disabled={action.pending}
              aria-label={`Aprovar a reivindicação nº ${claim.id}`}
              onClick={() => approve(claim)}
            >
              Aprovar
            </button>
            <button
              type="button"
              disabled={action.pending}
              aria-label={`Rejeitar a reivindicação nº ${claim.id}`}
              onClick={() => reject(claim)}
            >
              Rejeitar
            </button>
          </div>
        </section>
      ))}
    </Page>
  )
}
