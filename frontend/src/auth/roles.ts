import type { Role } from '../api/types'

// quem reivindica itens, quem trabalha nos balcões e quem administra
export const CLAIMANTS: Role[] = ['usuario']
export const STAFF: Role[] = ['atendente', 'admin']
export const ADMINS: Role[] = ['admin']
