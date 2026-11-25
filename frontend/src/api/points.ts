import { useLoad } from './hooks'
import { api, post } from './client'
import type { CollectionPoint, User } from './types'

export const pointsApi = {
  // público: todos os pontos de coleta, em ordem de nome
  all: () => api<CollectionPoint[]>('/v1/collection-points'),
  // pontos onde o atendente logado trabalha (admin vê todos, o resto nenhum)
  mine: () => api<CollectionPoint[]>('/v1/collection-points/mine'),

  // daqui para baixo, só o admin (RN40)
  create: (name: string) => api<CollectionPoint>('/v1/collection-points', post({ name })),
  attendants: (pointId: number) => api<User[]>(`/v1/collection-points/${pointId}/attendants`),
  link: (pointId: number, userId: number) =>
    api<User>(`/v1/collection-points/${pointId}/attendants`, post({ user_id: userId })),
  unlink: (pointId: number, userId: number) =>
    api<void>(`/v1/collection-points/${pointId}/attendants/${userId}`, { method: 'DELETE' }),
}

/** Todos os pontos e o nome de cada um pelo id, já que a API só manda o id. */
export function usePoints() {
  const { data } = useLoad(pointsApi.all)
  const points = data ?? []
  const pointName = (id: number) => points.find((point) => point.id === id)?.name ?? `Ponto ${id}`
  return { points, pointName }
}
