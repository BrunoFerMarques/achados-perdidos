import { startTransition } from 'react'
import { Link, NavLink, useNavigate } from 'react-router'
import { CLAIMANTS, STAFF } from '../auth/roles'
import { useAuth } from '../auth/useAuth'
import { ROLE } from '../labels'
import './header.css'

/** Cabeçalho de todas as telas. O menu muda com o papel, mas quem protege é a API. */
export function Header() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()

  // vai para o mural: ficando na tela, o RequireAuth a guardaria para o login da próxima pessoa.
  // O navigate do react-router roda como transition, que o React deixa para depois; com o logout
  // também numa transition, os dois valem juntos
  function handleLogout() {
    navigate('/')
    startTransition(logout)
  }

  return (
    <header className="header">
      <div className="header-inner">
        <Link to="/" className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          Achados e Perdidos
        </Link>
        <nav aria-label="Menu principal">
          <NavLink to="/" end>
            Mural
          </NavLink>
          {user && <NavLink to="/itens/novo">Registrar item</NavLink>}
          {user && CLAIMANTS.includes(user.role) && (
            <NavLink to="/reivindicacoes">Minhas reivindicações</NavLink>
          )}
          {user && STAFF.includes(user.role) && (
            <>
              <NavLink to="/atendimento/recebimento">Receber</NavLink>
              <NavLink to="/atendimento/analise">Analisar</NavLink>
              <NavLink to="/atendimento/retirada">Retirada</NavLink>
              <NavLink to="/atendimento/transferencias">Transferências</NavLink>
            </>
          )}
        </nav>
        {/* enquanto confere o token, não mostra nem o nome nem o "Entrar" */}
        {!loading && (
          <div className="session">
            {user ? (
              <>
                <span className="session-name">
                  {user.name} ({ROLE[user.role]})
                </span>
                <button type="button" className="button" onClick={handleLogout}>
                  Sair
                </button>
              </>
            ) : (
              <>
                <Link to="/criar-conta" className="button">
                  Criar conta
                </Link>
                <Link to="/login" className="button primary">
                  Entrar
                </Link>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  )
}
