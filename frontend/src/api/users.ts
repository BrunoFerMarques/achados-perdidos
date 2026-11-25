import { api, patch, post } from './client'
import type { Role, User } from './types'

// o máximo de contas que a API manda por pedido
const PAGE_SIZE = 100

// todas as contas: pede uma página atrás da outra até vir uma incompleta
async function allUsers(): Promise<User[]> {
  const users: User[] = []
  for (;;) {
    const page = await api<User[]>(`/v1/users?limit=${PAGE_SIZE}&offset=${users.length}`)
    users.push(...page)
    if (page.length < PAGE_SIZE) return users
  }
}

export const usersApi = {
  // público: é assim que um visitante vira usuário. O papel é sempre "usuario", quem põe é a API
  register: (name: string, email: string, password: string) =>
    api<User>('/v1/users', post({ name, email, password })),

  // daqui para baixo, só o admin
  all: allUsers,
  changeRole: (userId: number, role: Role) =>
    api<User>(`/v1/users/${userId}/role`, patch({ role })),
  unblock: (userId: number) => api<void>(`/v1/users/${userId}/unblock`, post()),
}
