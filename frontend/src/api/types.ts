export type Role = 'usuario' | 'atendente' | 'admin'

export type User = {
  id: number
  name: string
  email: string
  role: Role
  created_at: string
}

export type Token = {
  access_token: string
  token_type: string
}