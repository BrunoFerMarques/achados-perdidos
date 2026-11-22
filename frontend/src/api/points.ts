import { useLoad } from './hooks'
import { api } from './client'
import type { CollectionPoint } from './types'

export const pointsApi = {
  // public: every collection point, by name
  all: () => api<CollectionPoint[]>('/v1/collection-points'),
  // where the logged-in attendant works; every point for an admin, none for anyone else (RN41)
  mine: () => api<CollectionPoint[]>('/v1/collection-points/mine'),
}

/** Every collection point, and the name of one by its id (the API answers with ids only). */
export function usePoints() {
  const { data } = useLoad(pointsApi.all)
  const points = data ?? []
  const pointName = (id: number) => points.find((point) => point.id === id)?.name ?? `Ponto ${id}`
  return { points, pointName }
}
