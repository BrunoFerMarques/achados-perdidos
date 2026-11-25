import { useCallback, useState } from 'react'
import { Link } from 'react-router'
import { useCatalog } from '../api/catalog'
import { useLoad } from '../api/hooks'
import { itemsApi } from '../api/items'
import { usePoints } from '../api/points'
import { CLAIMANTS, STAFF } from '../auth/roles'
import { useAuth } from '../auth/useAuth'
import { LoadState, Page } from '../components/Page'
import { formatDate } from '../labels'

export function HomePage() {
  const { user } = useAuth()
  const { categories, locations, colors } = useCatalog()
  const { pointName } = usePoints()

  // one state per filter; '' means no filter ("Todas", "Todos", no date)
  const [q, setQ] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [locationId, setLocationId] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')

  // a new load whenever a filter changes, so useLoad asks the API again
  const load = useCallback(() => {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (categoryId) params.set('category_id', categoryId)
    if (locationId) params.set('location_id', locationId)
    if (from) params.set('found_from', from)
    if (to) params.set('found_to', to)
    return itemsApi.listPublic(params)
  }, [q, categoryId, locationId, from, to])

  const { data, error, loading } = useLoad(load)
  const items = data ?? []
  // a visitor goes through the login first; the staff doesn't claim items
  const canClaim = !user || CLAIMANTS.includes(user.role)

  return (
    <Page
      title="Perdeu alguma coisa?"
      subtitle="Veja o que já está guardado nos pontos de coleta e reivindique o que é seu."
    >
      <section className="card filters" aria-label="Filtros">
        <label>
          Buscar
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <label>
          Categoria
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">Todas</option>
            {categories.options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Local
          <select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
            <option value="">Todos</option>
            {locations.options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Achado de
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label>
          Até
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </section>

      <LoadState loading={loading} error={error} />
      {!loading && !error && items.length === 0 && <p>Nenhum item encontrado.</p>}
      <ul className="grid">
        {items.map((item) => (
          <li key={item.id} className="card">
            <span className="chip">{categories.nameOf(item.category_id)}</span>
            <strong>{item.public_description}</strong>
            <span className="muted">
              {colors.nameOf(item.color_id)} · achado em {locations.nameOf(item.location_id)}, dia{' '}
              {formatDate(item.found_date)}
            </span>
            <span className="muted">
              Item nº {item.id} · guardado em {pointName(item.collection_point_id)}
            </span>
            {canClaim && (
              <Link to={`/itens/${item.id}/reivindicar`} className="button primary">
                Reivindicar
              </Link>
            )}
            {user && STAFF.includes(user.role) && (
              <Link to={`/atendimento/historico?item=${item.id}`} className="button">
                Ver histórico
              </Link>
            )}
          </li>
        ))}
      </ul>
    </Page>
  )
}
