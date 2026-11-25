import { api, post } from './client'
import type {
  CustodyRecord,
  ItemCreate,
  ItemTransfer,
  MyItem,
  PublicItem,
  ReceiveIn,
  RegisteredItem,
} from './types'

// the public listing (RN50): no token needed; only items already at a counter come back
export const itemsApi = {
  // every filter is optional and goes in the query string; an empty one stays out
  listPublic: (params: URLSearchParams) => api<PublicItem[]>(`/v1/items?${params}`),
  // the finder registers what they found (needs the token); the API answers with the new item
  register: (item: ItemCreate) => api<{ id: number }>('/v1/items', post(item)),
  // RN53: the finder follows what they registered
  mine: () => api<MyItem[]>('/v1/items/mine'),
  // RN53: the custody history, staff only
  history: (itemId: number) => api<CustodyRecord[]>(`/v1/items/${itemId}/history`),
}

// recebimento no balcão, só para a equipe
export const receiptsApi = {
  list: () => api<RegisteredItem[]>('/v1/items/registered'),
  receive: (itemId: number, data: ReceiveIn) =>
    api<{ id: number }>(`/v1/items/${itemId}/receive`, post(data)),
}

// transferência entre pontos
export const transfersApi = {
  list: () => api<ItemTransfer[]>('/v1/items/transfers'),
  send: (itemId: number, transferToId: number) =>
    api<ItemTransfer>(`/v1/items/${itemId}/transfer`, post({ transfer_to_id: transferToId })),
  arrive: (itemId: number) => api<ItemTransfer>(`/v1/items/${itemId}/arrive`, post()),
}