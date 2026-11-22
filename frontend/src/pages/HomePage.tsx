import { Link } from 'react-router'
import { useCatalog } from '../api/catalog'
import { useLoad } from '../api/hooks'
import { itemsApi } from '../api/items'
import { usePoints } from '../api/points'
import { CLAIMANTS } from '../auth/roles'
import { useAuth } from '../auth/useAuth'
import { MainMenu } from '../components/MainMenu'
import { LoadState } from '../components/Page'

// the API sends year-month-day; new Date() would read it as midnight UTC and show the day before
function brDate(isoDate: string) {
  return isoDate.split('-').reverse().join('/')
}

export function HomePage() {
  const { user, logout } = useAuth()
  const { data, error, loading } = useLoad(itemsApi.listPublic)
  const { categories, locations, colors } = useCatalog()
  const { pointName } = usePoints()
  const items = data ?? []
  // a visitor goes through the login first; the staff doesn't claim items
  const canClaim = !user || CLAIMANTS.includes(user.role)

  return (
    <main className="page">
      <header>
        {user ? (
          <>
            <p>Olá, {user.name}!</p>
            <MainMenu />
            <Link to="/itens/novo">Registrar item achado</Link>
            <button type="button" onClick={logout}>
              Sair
            </button>
          </>
        ) : (
          <Link to="/login">Entrar</Link>
        )}
      </header>

      <h1>Achados e Perdidos</h1>
      <LoadState loading={loading} error={error} />
      {!loading && !error && items.length === 0 && <p>Nenhum item encontrado.</p>}
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <strong>{item.public_description}</strong>
            <p>
              {categories.nameOf(item.category_id)} · {colors.nameOf(item.color_id)} · achado em{' '}
              {locations.nameOf(item.location_id)}
            </p>
            <p>
              {brDate(item.found_date)} · guardado em {pointName(item.collection_point_id)}
            </p>
            {canClaim && <Link to={`/itens/${item.id}/reivindicar`}>Reivindicar</Link>}
          </li>
        ))}
      </ul>
    </main>
  )
}