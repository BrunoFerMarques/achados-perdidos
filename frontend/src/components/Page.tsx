import type { ReactNode } from 'react'
import './page.css'

/** Moldura das telas: título, uma linha de apoio opcional e o conteúdo. Com `narrow`, a coluna
 * fica estreita, para as telas que são só um formulário pequeno. */
export function Page({
  title,
  subtitle,
  narrow = false,
  children,
}: {
  title: string
  subtitle?: string
  narrow?: boolean
  children: ReactNode
}) {
  return (
    <main className={narrow ? 'page narrow' : 'page'}>
      <h1>{title}</h1>
      {subtitle && <p className="subtitle">{subtitle}</p>}
      {children}
    </main>
  )
}

/** Mensagem de carregando ou de erro que as telas de lista mostram antes do conteúdo. */
export function LoadState({ loading, error }: { loading: boolean; error: string }) {
  if (error) return <p role="alert" className="error">{error}</p>
  if (loading) return <p className="muted">Carregando…</p>
  return null
}
