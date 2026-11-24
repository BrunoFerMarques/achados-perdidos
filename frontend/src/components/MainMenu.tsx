import { Link } from 'react-router'
import { useAuth } from '../auth/useAuth'
import { CLAIMANTS, STAFF } from '../auth/roles'
import './page.css'

/** Links da página inicial de acordo com o papel. A API continua checando cada ação. */
export function MainMenu() {
  const { user } = useAuth()
  if (!user) return null

  return (
    <nav className="menu">
      {CLAIMANTS.includes(user.role) && <Link to="/reivindicacoes">Minhas reivindicações</Link>}
      {STAFF.includes(user.role) && (
        <>
          <Link to="/atendimento/recebimento">Receber itens</Link>
          <Link to="/atendimento/analise">Analisar reivindicações</Link>
          <Link to="/atendimento/retirada">Retirada no balcão</Link>
          <Link to="/atendimento/transferencias">Transferências</Link>
        </>
      )}
    </nav>
  )
}