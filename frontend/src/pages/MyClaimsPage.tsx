import { claimsApi } from '../api/claims'
import { useAction, useLoad } from '../api/hooks'
import { usePoints } from '../api/points'
import type { Claim, ClaimStatus } from '../api/types'
import { FeedbackLine } from '../components/FeedbackLine'
import { LoadState, Page } from '../components/Page'
import { CLAIM_STATUS, formatDateTime, isPast } from '../labels'

// só as ativas podem ser canceladas
const CANCELLABLE: readonly ClaimStatus[] = ['pendente', 'aprovada']

/** Reivindicações do usuário: status, ponto de coleta e, depois de aprovada, o código de
 * retirada com o prazo. Nada de nota nem de dados do achador. */
export function MyClaimsPage() {
  const { data: claims, error, loading, reload } = useLoad(claimsApi.mine)
  const { pointName } = usePoints()
  const action = useAction()

  async function cancel(claim: Claim) {
    if (!window.confirm(`Cancelar a reivindicação do item nº ${claim.item_id}?`)) return
    const done = await action.run(
      () => claimsApi.cancel(claim.id),
      `Reivindicação do item nº ${claim.item_id} cancelada.`,
    )
    if (done) reload()
  }

  return (
    <Page title="Minhas reivindicações">
      <FeedbackLine feedback={action.feedback} />
      <LoadState loading={loading} error={error} />
      {claims?.length === 0 && <p>Você ainda não reivindicou nenhum item.</p>}
      {claims?.map((claim) => (
        <section key={claim.id} className="card">
          <h2>
            Item nº {claim.item_id}: {claim.item_public_description}
          </h2>
          <p>
            <strong>{CLAIM_STATUS[claim.status]}</strong> · {pointName(claim.collection_point_id)}
          </p>
          <p className="muted">Feita em {formatDateTime(claim.created_at)}</p>
          {claim.pickup_code && claim.pickup_deadline && (
            <div>
              <p>Código de retirada:</p>
              <p className="code">{claim.pickup_code}</p>
              {isPast(claim.pickup_deadline) ? (
                <p className="error">
                  O prazo de retirada venceu em {formatDateTime(claim.pickup_deadline)}.
                </p>
              ) : (
                <p>
                  Retire até {formatDateTime(claim.pickup_deadline)} em{' '}
                  {pointName(claim.collection_point_id)}, com um documento com foto.
                </p>
              )}
            </div>
          )}
          {CANCELLABLE.includes(claim.status) && (
            <div className="actions">
              <button
                type="button"
                disabled={action.pending}
                aria-label={`Cancelar a reivindicação do item nº ${claim.item_id}`}
                onClick={() => cancel(claim)}
              >
                Cancelar
              </button>
            </div>
          )}
        </section>
      ))}
    </Page>
  )
}
