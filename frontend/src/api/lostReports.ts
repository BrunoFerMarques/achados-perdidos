import { api, post } from './client'
import type { LostReport, LostReportCreate } from './types'

// relatos de perda: só o usuário comum cria, e cada um vê só os seus
export const lostReportsApi = {
  create: (report: LostReportCreate) => api<LostReport>('/v1/lost-reports', post(report)),
  mine: () => api<LostReport[]>('/v1/lost-reports'),
  // encerrar: a pessoa achou o objeto ou desistiu; o relato para de gerar avisos
  close: (reportId: number) =>
    api<LostReport>(`/v1/lost-reports/${reportId}/close`, { method: 'PATCH' }),
}
