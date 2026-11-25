import { Link } from 'react-router'
import { useCatalog } from '../api/catalog'
import { useLoad } from '../api/hooks'
import { itemsApi } from '../api/items'
import { usePoints } from '../api/points'
import { LoadState, Page } from '../components/Page'
import { formatDate, ITEM_STATUS } from '../labels'

/** What the logged-in person registered, and the status of each item. Never who claimed it
 * (RN53). */
export function MyItemsPage() {
  const { data: items, error, loading } = useLoad(itemsApi.mine)
  const { categories } = useCatalog()
  const { pointName } = usePoints()

  return (
    <Page title="Meus itens" subtitle="O que você achou e registrou, do mais novo para o mais antigo.">
      <LoadState loading={loading} error={error} />
      {items?.length === 0 && (
        <p>
          Você ainda não registrou nenhum item. <Link to="/itens/novo">Registrar item</Link>
        </p>
      )}
      <ul className="grid">
        {items?.map((item) => (
          <li key={item.id} className="card">
            <span className="chip">{categories.nameOf(item.category_id)}</span>
            <strong>{item.description}</strong>
            <span>{ITEM_STATUS[item.status]}</span>
            <span className="muted">
              Item nº {item.id} · achado em {formatDate(item.found_date)}
            </span>
            <span className="muted">Ponto de coleta: {pointName(item.collection_point_id)}</span>
          </li>
        ))}
      </ul>
    </Page>
  )
}
