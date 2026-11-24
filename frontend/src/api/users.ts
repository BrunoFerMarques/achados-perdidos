import { api, post } from './client'
import type { User } from './types'

export const usersApi = {
  // público: é assim que um visitante vira usuário. O papel é sempre "usuario", quem põe é a API
  register: (name: string, email: string, password: string) =>
    api<User>('/v1/users', post({ name, email, password })),
}
