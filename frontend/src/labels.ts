import type { ClaimStatus, Role } from './api/types'

export const ROLE: Record<Role, string> = {
  usuario: 'usuário',
  atendente: 'atendente',
  admin: 'admin',
}

// o reivindicante só vê o resultado, sem nota nem motivo
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
  // data sem hora (AAAA-MM-DD): o `new Date` leria como meia-noite UTC e voltaria um dia aqui
  const [year, month, day] = isoDate.split('-')
  return `${day}/${month}/${year}`
}
