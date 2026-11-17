import { useAuth } from '../auth/useAuth'

export function HomePage() {
  const { user, logout } = useAuth()

  return (
    <main>
      <h1>Achados e Perdidos</h1>
      <p>Olá, {user?.name}!</p>
      <button type="button" onClick={logout}>
        Sair
      </button>
    </main>
  )
}