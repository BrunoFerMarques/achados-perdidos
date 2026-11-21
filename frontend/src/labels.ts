import type { ClaimStatus } from './api/types'

// RN21: the claimant only sees the result, never the score or the reason
export const CLAIM_STATUS: Record<ClaimStatus, string> = {
  pendente: 'Em análise',
  aprovada: 'Aprovada: aguardando retirada',
  rejeitada: 'Rejeitada',
  cancelada: 'Cancelada',
  concluida: 'Retirada',
  expirada: 'Prazo de retirada vencido',
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

export function isPast(iso: string): boolean {
  return new Date(iso).getTime() <= Date.now()
}

export function formatDate(isoDate: string): string {
  // a plain date (YYYY-MM-DD): read as UTC midnight, `new Date` would move it a day back here
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year}`
}
