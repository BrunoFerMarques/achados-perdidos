import { Link } from 'react-router'
import { useCatalog } from '../api/catalog'
import { useAction, useLoad } from '../api/hooks'
import { lostReportsApi } from '../api/lostReports'
import { announceNotificationsChanged, notificationsApi } from '../api/notifications'
import { usePoints } from '../api/points'
import type { Notification } from '../api/types'
import { FeedbackLine } from '../components/FeedbackLine'
import { LoadState, Page } from '../components/Page'
import { formatDate } from '../labels'

// os avisos só trazem o id do relato; os relatos vêm junto para mostrar qual perda bateu
const loadAll = () => Promise.all([notificationsApi.mine(), lostReportsApi.mine()])

/** Os avisos de match: um item parecido com um relato da pessoa chegou a um balcão (RN30).
 * Mostra só a parte pública do item (RN32); quem prova que é dono é a reivindicação. */
export function NotificationsPage() {
  const { categories, locations, colors } = useCatalog()
  const { pointName } = usePoints()
  const { data, error, loading, reload } = useLoad(loadAll)
  const action = useAction()
  const [notifications, reports] = data ?? [[], []]

  const reportOf = (n: Notification) => reports.find((report) => report.id === n.lost_report_id)

  async function markRead(n: Notification) {
    const done = await action.run(() => notificationsApi.markRead(n.id))
    if (!done) return
    reload()
    announceNotificationsChanged()
  }

  return (
    <Page title="Avisos" subtitle="Quando um item parecido com o que você perdeu chega a um balcão, ele aparece aqui.">
      <FeedbackLine feedback={action.feedback} />
      <LoadState loading={loading} error={error} />
      {data && notifications.length === 0 && (
        <p>
          Nenhum aviso ainda. Se perdeu algo, conte em <Link to="/perdi-algo">Perdi algo</Link>.
        </p>
      )}
      <ul className="grid">
        {notifications.map((n) => (
          <li key={n.id} className={n.read_at ? 'card read' : 'card'}>
            <span className="chip">{n.read_at ? 'Lido' : 'Novo'}</span>
            <strong>{n.item.public_description}</strong>
            <span className="muted">
              {categories.nameOf(n.item.category_id)} · {colors.nameOf(n.item.color_id)} · achado em{' '}
              {locations.nameOf(n.item.location_id)} em {formatDate(n.item.found_date)}
            </span>
            <span>Está no balcão: {pointName(n.item.collection_point_id)}</span>
            <span className="muted">Parece com o seu relato: {reportOf(n)?.description ?? `nº ${n.lost_report_id}`}</span>
            {/* o item pode já ter sido reivindicado por outra pessoa depois do aviso */}
            {n.item_available ? (
              <Link to={`/itens/${n.item_id}/reivindicar`} className="button primary">
                Reivindicar
              </Link>
            ) : (
              <span className="muted">Este item não está mais disponível.</span>
            )}
            {!n.read_at && (
              <button type="button" disabled={action.pending} onClick={() => markRead(n)}>
                Marcar como lido
              </button>
            )}
          </li>
        ))}
      </ul>
    </Page>
  )
}
