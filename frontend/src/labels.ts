import type { ClaimStatus, CustodyEvent, ItemStatus, LostReportStatus, Role } from './api/types'

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

// what the finder reads: the status only, never who claimed it (RN53)
export const ITEM_STATUS: Record<ItemStatus, string> = {
  registrado: 'Esperando a entrega no ponto de coleta',
  disponivel: 'Guardado no ponto de coleta',
  em_transferencia: 'A caminho de outro ponto de coleta',
  reservado: 'Reservado: aguardando a retirada',
  devolvido: 'Devolvido ao dono',
  expirado: 'Prazo de guarda vencido',
  destinado: 'Doado ou descartado',
  cancelado: 'Registro cancelado',
}

export const CUSTODY_EVENT: Record<CustodyEvent, string> = {
  registro: 'Registrado no site',
  recebimento: 'Recebido no balcão',
  transferencia_saida: 'Enviado para outro ponto',
  transferencia_chegada: 'Chegou de outro ponto',
  reserva: 'Reservado para o dono',
  liberacao: 'Voltou a ficar disponível',
  devolucao: 'Devolvido ao dono',
  expiracao: 'Prazo de guarda vencido',
  destinacao: 'Doado ou descartado',
  cancelamento: 'Registro cancelado',
}

export const LOST_REPORT_STATUS: Record<LostReportStatus, string> = {
  ativo: 'Procurando',
  encerrado: 'Encerrado',
  expirado: 'Vencido (60 dias)',
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
