import { api, post } from './client'
import type { ItemTransfer, PublicItem } from './types'

// the public listing (RN50): no token needed; only items already at a counter come back
export const itemsApi = {
  listPublic: () => api<PublicItem[]>('/v1/items'),
}

// the transfer between points (RN05)
export const transfersApi = {
  list: () => api<ItemTransfer[]>('/v1/items/transfers'),
  send: (itemId: number, transferToId: number) =>
    api<ItemTransfer>(`/v1/items/${itemId}/transfer`, post({ transfer_to_id: transferToId })),
  arrive: (itemId: number) => api<ItemTransfer>(`/v1/items/${itemId}/arrive`, post()),
}