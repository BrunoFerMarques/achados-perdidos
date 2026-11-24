import type { ReactNode } from 'react'
import { Link } from 'react-router'
import './page.css'

/** Moldura das telas internas: link pro início, título e conteúdo. */
export function Page({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="page">
      <Link to="/">← Início</Link>
      <h1>{title}</h1>
      {children}
    </main>
  )
}

/** Mensagem de carregando ou de erro que as telas de lista mostram antes do conteúdo. */
export function LoadState({ loading, error }: { loading: boolean; error: string }) {
  if (error) return <p role="alert" className="error">{error}</p>
  if (loading) return <p>Carregando…</p>
  return null
}
