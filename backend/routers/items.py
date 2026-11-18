from fastapi import APIRouter

from dependencies import CurrentUserDep, ItemServiceDep
from schemas.custody import CustodyRecordOut
from schemas.item import ItemCreate, ItemOut, ReceiveIn

router = APIRouter(prefix="/v1/items", tags=["items"])


@router.post("", status_code=201, response_model=ItemOut)
def register_item(payload: ItemCreate, current_user: CurrentUserDep, items: ItemServiceDep):
    # any logged-in user can register an object they found
    return items.register(
        current_user,
        category_id=payload.category_id,
        location_id=payload.location_id,
        color_id=payload.color_id,
        collection_point_id=payload.collection_point_id,
        description=payload.description,
        found_date=payload.found_date,
        questions=[(q.question, q.answer) for q in payload.questions],
    )


@router.post("/{item_id}/receive", response_model=ItemOut)
def receive_item(
    item_id: int, payload: ReceiveIn, current_user: CurrentUserDep, items: ItemServiceDep
):
    # an action route, not a PATCH on the status: receiving has rules of its own (RN02, RN41)
    return items.receive(current_user, item_id, payload.collection_point_id)


@router.get("/{item_id}/history", response_model=list[CustodyRecordOut])
def item_history(item_id: int, current_user: CurrentUserDep, items: ItemServiceDep):
    # RN53: only the staff sees it; the service decides who that is
    return items.history(current_user, item_id)
