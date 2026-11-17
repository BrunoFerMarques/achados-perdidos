const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'token'

export function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
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
    if (res.status === 401 && token) clearToken()
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, errorMessage(body?.detail))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}