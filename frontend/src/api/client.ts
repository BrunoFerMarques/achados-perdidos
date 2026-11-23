const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'token'

export function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function hasToken() {
  return localStorage.getItem(TOKEN_KEY) !== null
}

let onSessionExpired = () => {}

export function setOnSessionExpired(handler: () => void) {
  onSessionExpired = handler
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type ValidationIssue = { loc: (string | number)[]; msg: string }

function errorMessage(detail: unknown): string {
  if (Array.isArray(detail)) {
    return detail
      .map((issue: ValidationIssue) => `${issue.loc.at(-1)}: ${issue.msg}`)
      .join('; ')
  }
  if (typeof detail === 'string') return detail
  return 'Erro inesperado'
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (!res.ok) {
    if (res.status === 401 && token) {
      clearToken()
      onSessionExpired()
    }
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, errorMessage(body?.detail))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}
// monta um POST com corpo JSON opcional, pras rotas de ação (aprovar, retirar, transferir...)
export function post(body?: unknown): RequestInit {
  return { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }
}

export function errorText(err: unknown): string {
  // a API já manda a mensagem em português, pronta pro usuário
  if (err instanceof ApiError) return err.message
  return 'Não foi possível falar com a API. Tente de novo.'
}
