import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation } from 'react-router'
import { ApiError, errorText } from '../api/client'
import { usersApi } from '../api/users'
import { useAuth } from '../auth/useAuth'
import { Page } from '../components/Page'

/** Criar conta. Deu certo, a pessoa já entra, sem digitar tudo de novo no login. */
export function SignUpPage() {
  const { user, login } = useAuth()
  // a tela de onde o RequireAuth mandou pro login; o login repassa pra cá
  const state = useLocation().state as { from?: string } | null
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  // vale pra quem já estava logado e também logo depois do cadastro
  if (user) return <Navigate to={state?.from ?? '/'} replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSending(true)
    let created = false
    try {
      await usersApi.register(name, email, password)
      created = true
      await login(email, password)
    } catch (err) {
      // a conta existe: tentar de novo aqui daria "E-mail já cadastrado"
      if (created) setError('Conta criada, mas não deu para entrar. Use a tela Entrar.')
      // o 422 vem em inglês e só acontece no que o navegador deixa passar (ex.: ana@site)
      else if (err instanceof ApiError && err.status === 422)
        setError('Confira o nome, o e-mail e a senha.')
      else setError(errorText(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <Page title="Criar conta" narrow>
      <form onSubmit={handleSubmit}>
        <label>
          Nome
          <input
            type="text"
            autoComplete="name"
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>
        <label>
          E-mail
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Senha (8 caracteres ou mais)
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button type="submit" disabled={sending}>
          {sending ? 'Criando…' : 'Criar conta'}
        </button>
      </form>
      <p>
        Já tem conta?{' '}
        <Link to="/login" state={state}>
          Entrar
        </Link>
      </p>
    </Page>
  )
}
