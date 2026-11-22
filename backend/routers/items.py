from datetime import date

from fastapi import APIRouter

from dependencies import CurrentUserDep, ItemServiceDep
from schemas.custody import CustodyRecordOut
from schemas.item import ItemCreate, ItemOut, ItemPublicOut, ItemTransferOut, ReceiveIn, TransferIn

router = APIRouter(prefix="/v1/items", tags=["items"])


@router.get("", response_model=list[ItemPublicOut])
def list_items(
    items: ItemServiceDep,
    q: str | None = None,
    category_id: int | None = None,
    location_id: int | None = None,
    found_from: date | None = None,
    found_to: date | None = None,
):
    # public (RN50): no current_user; every filter is optional and comes in the query string
    return items.list_public(
        q=q,
        category_id=category_id,
        location_id=location_id,
        found_from=found_from,
        found_to=found_to,
    )


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


@router.post("/{item_id}/transfer", response_model=ItemTransferOut)
def transfer_item(
    item_id: int, payload: TransferIn, current_user: CurrentUserDep, items: ItemServiceDep
):
    # RN05: the origin's attendant sends it; it stays in transfer until the destination confirms
    return items.transfer(current_user, item_id, payload.transfer_to_id)


@router.post("/{item_id}/arrive", response_model=ItemTransferOut)
def arrive_item(item_id: int, current_user: CurrentUserDep, items: ItemServiceDep):
    # RN05: the destination's attendant confirms it reached the shelf
    return items.arrive(current_user, item_id)


@router.get("/transfers", response_model=list[ItemTransferOut])
def list_items_in_transfer(current_user: CurrentUserDep, items: ItemServiceDep):
    # what is leaving or heading to the actor's points
    return items.list_in_transfer(current_user)


@router.get("/{item_id}/history", response_model=list[CustodyRecordOut])
def item_history(item_id: int, current_user: CurrentUserDep, items: ItemServiceDep):
    # RN53: only the staff sees it; the service decides who that is
    return items.history(current_user, item_id)
