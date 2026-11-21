import { api, post } from './client'
import type { ItemTransfer } from './types'

// the transfer between points (RN05)
export const transfersApi = {
  list: () => api<ItemTransfer[]>('/v1/items/transfers'),
  send: (itemId: number, transferToId: number) =>
    api<ItemTransfer>(`/v1/items/${itemId}/transfer`, post({ transfer_to_id: transferToId })),
  arrive: (itemId: number) => api<ItemTransfer>(`/v1/items/${itemId}/arrive`, post()),
}
