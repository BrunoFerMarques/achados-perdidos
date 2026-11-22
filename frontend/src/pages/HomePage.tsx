import { useAuth } from '../auth/useAuth'
import { MainMenu } from '../components/MainMenu'

export function HomePage() {
  const { user, logout } = useAuth()

  return (
    <main>
      <h1>Achados e Perdidos</h1>
      <p>Olá, {user?.name}!</p>
      <MainMenu />
      <button type="button" onClick={logout}>
        Sair
      </button>
    </main>
  )
}