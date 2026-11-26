import { startTransition } from 'react'
import { Link, NavLink, useNavigate } from 'react-router'
import { useUnreadCount } from '../api/notifications'
import { ADMINS, CLAIMANTS, STAFF } from '../auth/roles'
import { useAuth } from '../auth/useAuth'
import { ROLE } from '../labels'
import './header.css'

/** Cabeçalho de todas as telas. O menu muda com o papel, mas quem protege é a API. */
export function Header() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const isStaff = user !== null && STAFF.includes(user.role)
  const isClaimant = user !== null && CLAIMANTS.includes(user.role)
  const unread = useUnreadCount(isClaimant)

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
          <img src={`${import.meta.env.BASE_URL}favicon.svg`} alt="" width={28} height={28} />
          Achados e Perdidos
        </Link>
        {/* o menu da equipe é comprido e ganha uma linha só para ele */}
        <nav aria-label="Menu principal" className={isStaff ? 'own-line' : undefined}>
          <div className="nav-group">
            <NavLink to="/" end>
              Mural
            </NavLink>
            {user && (
              <>
                <NavLink to="/itens/novo">Registrar item</NavLink>
                <NavLink to="/itens/meus">Meus itens</NavLink>
              </>
            )}
            {isClaimant && (
              <>
                <NavLink to="/perdi-algo">Perdi algo</NavLink>
                <NavLink to="/reivindicacoes">Minhas reivindicações</NavLink>
                {/* o número só aparece quando há aviso sem ler */}
                <NavLink to="/avisos" aria-label={unread > 0 ? `Avisos, ${unread} sem ler` : 'Avisos'}>
                  🔔 Avisos
                  {unread > 0 && <span className="badge">{unread}</span>}
                </NavLink>
              </>
            )}
          </div>
          {isStaff && (
            <div className="nav-group">
              <NavLink to="/atendimento/recebimento">Receber</NavLink>
              <NavLink to="/atendimento/analise">Analisar</NavLink>
              <NavLink to="/atendimento/retirada">Retirada</NavLink>
              <NavLink to="/atendimento/transferencias">Transferências</NavLink>
              <NavLink to="/atendimento/historico">Histórico</NavLink>
            </div>
          )}
          {user && ADMINS.includes(user.role) && (
            <div className="nav-group">
              <NavLink to="/admin/pontos">Pontos</NavLink>
              <NavLink to="/admin/usuarios">Usuários</NavLink>
            </div>
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
