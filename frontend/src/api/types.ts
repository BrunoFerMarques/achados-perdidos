export type Role = 'usuario' | 'atendente' | 'admin'

export type User = {
  id: number
  name: string
  email: string
  role: Role
  created_at: string
}

export type Token = {
  access_token: string
  token_type: string
}
export type CollectionPoint = {
  id: number
  name: string
}

export type Question = {
  position: number
  question: string
}

export type ClaimStatus =
  | 'pendente'
  | 'aprovada'
  | 'rejeitada'
  | 'cancelada'
  | 'concluida'
  | 'expirada'

// o que o reivindicante vê (ClaimOut): sem nota, sem motivo e sem resposta esperada
export type Claim = {
  id: number
  item_id: number
  item_public_description: string
  status: ClaimStatus
  collection_point_id: number
  pickup_code: string | null
  pickup_deadline: string | null
  created_at: string
}

export type ReviewedAnswer = {
  position: number
  question: string
  expected: string
  given: string
}

// o que o atendente analisa (ClaimReviewOut)
export type ClaimReview = {
  id: number
  item_id: number
  item_description: string
  claimant_id: number
  status: ClaimStatus
  score: number
  collection_point_id: number
  created_at: string
  answers: ReviewedAnswer[]
}

// fila do balcão (ClaimPickupOut): tem o nome pra conferir o documento, mas não o código
export type ClaimPickup = {
  id: number
  item_id: number
  item_description: string
  claimant_id: number
  claimant_name: string
  status: ClaimStatus
  collection_point_id: number
  pickup_deadline: string | null
}

export type ItemStatus =
  | 'registrado'
  | 'disponivel'
  | 'em_transferencia'
  | 'reservado'
  | 'devolvido'
  | 'expirado'
  | 'destinado'
  | 'cancelado'

export type CustodyEvent =
  | 'registro'
  | 'recebimento'
  | 'transferencia_saida'
  | 'transferencia_chegada'
  | 'reserva'
  | 'liberacao'
  | 'devolucao'
  | 'expiracao'
  | 'destinacao'
  | 'cancelamento'

// one line of the custody history (CustodyRecordOut); no name when the account was deleted
export type CustodyRecord = {
  event: CustodyEvent
  collection_point_id: number
  actor_name: string | null
  at: string
}

// an item the logged-in person registered (ItemOut). Only the fields the screen uses
export type MyItem = {
  id: number
  category_id: number
  collection_point_id: number
  description: string
  found_date: string
  status: ItemStatus
}

// item em transferência visto pela equipe (ItemTransferOut). Só os campos que a tela usa, a
// API manda mais
export type ItemTransfer = {
  id: number
  description: string
  status: ItemStatus
  collection_point_id: number
  transfer_to_id: number | null
  found_date: string
  created_at: string
}

// o que o atendente envia no balcão (PickupIn)
export type PickupIn = {
  collection_point_id: number
  pickup_code: string
  document_checked: boolean
}

// one entry of the public lists: categories, locations and colors (CategoryOut, LocationOut, ColorOut)
export type Option = {
  id: number
  name: string
}

// what anyone sees on the public listing (ItemPublicOut, RN50): no questions, no finder, no status
export type PublicItem = {
  id: number
  category_id: number
  location_id: number
  color_id: number
  collection_point_id: number
  public_description: string
  found_date: string
}

// one verification question with its expected answer, sent only when registering (RN20, RN23)
export type QuestionInput = {
  question: string
  answer: string
}

// the body of POST /v1/items (ItemCreate): no status and no finder, the API fills them in
export type ItemCreate = {
  category_id: number
  location_id: number
  color_id: number
  collection_point_id: number
  description: string
  found_date: string
  questions: QuestionInput[]
}

// item registrado à espera do recebimento (ItemOut). Só os campos que a tela usa, a API manda
// mais
export type RegisteredItem = {
  id: number
  category_id: number
  location_id: number
  color_id: number
  collection_point_id: number
  description: string
  found_date: string
}

// o que o atendente envia ao receber (ReceiveIn): o balcão onde ele está (RN02) e a descrição
// pública, que ele pode ter editado (RN51)
export type ReceiveIn = {
  collection_point_id: number
  description: string
}
// o relato de quem perdeu algo (LostReportOut): ativo até achar, encerrar ou vencer (RN33)
export type LostReportStatus = 'ativo' | 'encerrado' | 'expirado'

export type LostReport = {
  id: number
  category_id: number
  location_id: number
  color_id: number
  description: string
  lost_date: string
  status: LostReportStatus
  created_at: string
}

// o corpo de POST /v1/lost-reports (LostReportCreate): o dono vem do token
export type LostReportCreate = {
  category_id: number
  location_id: number
  color_id: number
  description: string
  lost_date: string
}

// um aviso de match (NotificationOut, RN30 a RN32): só a parte pública do item, nunca o achador
export type Notification = {
  id: number
  lost_report_id: number
  item_id: number
  created_at: string
  read_at: string | null
  item_available: boolean
  item: PublicItem
}
