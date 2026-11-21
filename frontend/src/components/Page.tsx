import type { ReactNode } from 'react'
import { Link } from 'react-router'
import './page.css'

/** The frame of an inner screen: a way back home, the title, the content. */
export function Page({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="page">
      <Link to="/">← Início</Link>
      <h1>{title}</h1>
      {children}
    </main>
  )
}

/** The loading and error lines every list screen shows before its content. */
export function LoadState({ loading, error }: { loading: boolean; error: string }) {
  if (error) return <p role="alert" className="error">{error}</p>
  if (loading) return <p>Carregando…</p>
  return null
}
