import { api, post } from './client'
import type { Claim, ClaimPickup, ClaimReview, PickupIn, Question } from './types'

// rotas da reivindicação: primeiro as do reivindicante, depois análise e balcão
export const claimsApi = {
  questions: (itemId: number) => api<Question[]>(`/v1/claims/items/${itemId}/questions`),
  create: (itemId: number, answers: string[]) =>
    api<Claim>('/v1/claims', post({ item_id: itemId, answers })),
  mine: () => api<Claim[]>('/v1/claims/me'),
  cancel: (claimId: number) => api<Claim>(`/v1/claims/${claimId}/cancel`, post()),

  pending: () => api<ClaimReview[]>('/v1/claims/pending'),
  approve: (claimId: number) => api<ClaimReview>(`/v1/claims/${claimId}/approve`, post()),
  reject: (claimId: number) => api<ClaimReview>(`/v1/claims/${claimId}/reject`, post()),

  approved: () => api<ClaimPickup[]>('/v1/claims/approved'),
  pickUp: (claimId: number, form: PickupIn) =>
    api<ClaimPickup>(`/v1/claims/${claimId}/pickup`, post(form)),
}
