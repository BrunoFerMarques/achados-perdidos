from fastapi import APIRouter

from dependencies import ClaimServiceDep, CurrentUserDep
from schemas.claim import ClaimCreate, ClaimOut, ClaimPickupOut, ClaimReviewOut, PickupIn
from schemas.item import QuestionOut

# toda rota pede login; quem pode fazer o quê fica no service
router = APIRouter(prefix="/v1/claims", tags=["claims"])


@router.get("/items/{item_id}/questions", response_model=list[QuestionOut])
def claim_questions(item_id: int, current_user: CurrentUserDep, claims: ClaimServiceDep):
    # formulário da reivindicação: só as perguntas, sem as respostas esperadas
    return claims.questions(current_user, item_id)


@router.post("", status_code=201, response_model=ClaimOut)
def create_claim(payload: ClaimCreate, current_user: CurrentUserDep, claims: ClaimServiceDep):
    # 201 mesmo se a nota rejeitar na hora, porque a reivindicação foi criada
    return claims.create(current_user, payload.item_id, payload.answers)


@router.get("/me", response_model=list[ClaimOut])
def list_my_claims(current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.list_mine(current_user)


@router.post("/{claim_id}/cancel", response_model=ClaimOut)
def cancel_claim(claim_id: int, current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.cancel(current_user, claim_id)


# --- análise do atendente ---


@router.get("/pending", response_model=list[ClaimReviewOut])
def list_pending_claims(current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.list_pending(current_user)


@router.post("/{claim_id}/approve", response_model=ClaimReviewOut)
def approve_claim(claim_id: int, current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.approve(current_user, claim_id)


@router.post("/{claim_id}/reject", response_model=ClaimReviewOut)
def reject_claim(claim_id: int, current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.reject(current_user, claim_id)


# --- retirada no balcão ---


@router.get("/approved", response_model=list[ClaimPickupOut])
def list_approved_claims(current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.list_approved(current_user)


@router.post("/{claim_id}/pickup", response_model=ClaimPickupOut)
def pick_up_claim(
    claim_id: int, payload: PickupIn, current_user: CurrentUserDep, claims: ClaimServiceDep
):
    # rota de ação: código, balcão e documento conferido vêm no corpo
    return claims.pick_up(
        current_user,
        claim_id,
        collection_point_id=payload.collection_point_id,
        pickup_code=payload.pickup_code,
        document_checked=payload.document_checked,
    )
