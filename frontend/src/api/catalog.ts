import { useLoad } from './hooks'
import { api } from './client'
import type { Option } from './types'

// the public lists the screens translate ids with (the API answers with ids only)
export const catalogApi = {
  categories: () => api<Option[]>('/v1/categories'),
  locations: () => api<Option[]>('/v1/locations'),
  colors: () => api<Option[]>('/v1/colors'),
}

/** One list, and the name of one of its entries by id. */
function useOptions(load: () => Promise<Option[]>) {
  const { data } = useLoad(load)
  const options = data ?? []
  const nameOf = (id: number) => options.find((option) => option.id === id)?.name ?? ''
  return { options, nameOf }
}

/** The three lists, each loaded once when the screen opens. */
export function useCatalog() {
  const categories = useOptions(catalogApi.categories)
  const locations = useOptions(catalogApi.locations)
  const colors = useOptions(catalogApi.colors)
  return { categories, locations, colors }
}