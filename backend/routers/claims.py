from fastapi import APIRouter

from dependencies import ClaimServiceDep, CurrentUserDep
from schemas.claim import ClaimCreate, ClaimOut, ClaimPickupOut, ClaimReviewOut, PickupIn

# every route takes CurrentUserDep; who may do what is decided by the service
router = APIRouter(prefix="/v1/claims", tags=["claims"])


@router.post("", status_code=201, response_model=ClaimOut)
def create_claim(payload: ClaimCreate, current_user: CurrentUserDep, claims: ClaimServiceDep):
    # 201 even when the score rejects it at once: the claim exists, and its status says so (RN21)
    return claims.create(current_user, payload.item_id, payload.answers)


@router.get("/me", response_model=list[ClaimOut])
def list_my_claims(current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.list_mine(current_user)


@router.post("/{claim_id}/cancel", response_model=ClaimOut)
def cancel_claim(claim_id: int, current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.cancel(current_user, claim_id)


# --- the attendant's review (RN22, RN41) ---


@router.get("/pending", response_model=list[ClaimReviewOut])
def list_pending_claims(current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.list_pending(current_user)


@router.post("/{claim_id}/approve", response_model=ClaimReviewOut)
def approve_claim(claim_id: int, current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.approve(current_user, claim_id)


@router.post("/{claim_id}/reject", response_model=ClaimReviewOut)
def reject_claim(claim_id: int, current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.reject(current_user, claim_id)


# --- the pickup at the counter (RN44 to RN46) ---


@router.get("/approved", response_model=list[ClaimPickupOut])
def list_approved_claims(current_user: CurrentUserDep, claims: ClaimServiceDep):
    return claims.list_approved(current_user)


@router.post("/{claim_id}/pickup", response_model=ClaimPickupOut)
def pick_up_claim(
    claim_id: int, payload: PickupIn, current_user: CurrentUserDep, claims: ClaimServiceDep
):
    # an action route: the code, the counter and the photo ID check come in the body
    return claims.pick_up(
        current_user,
        claim_id,
        collection_point_id=payload.collection_point_id,
        pickup_code=payload.pickup_code,
        document_checked=payload.document_checked,
    )
