import { api, post } from './client'
import type { ItemCreate, ItemTransfer, PublicItem } from './types'

// the public listing (RN50): no token needed; only items already at a counter come back
export const itemsApi = {
  // every filter is optional and goes in the query string; an empty one stays out
  listPublic: (params: URLSearchParams) => api<PublicItem[]>(`/v1/items?${params}`),
  // the finder registers what they found (needs the token); the API answers with the new item
  register: (item: ItemCreate) => api<{ id: number }>('/v1/items', post(item)),
}

// the transfer between points (RN05)
export const transfersApi = {
  list: () => api<ItemTransfer[]>('/v1/items/transfers'),
  send: (itemId: number, transferToId: number) =>
    api<ItemTransfer>(`/v1/items/${itemId}/transfer`, post({ transfer_to_id: transferToId })),
  arrive: (itemId: number) => api<ItemTransfer>(`/v1/items/${itemId}/arrive`, post()),
}