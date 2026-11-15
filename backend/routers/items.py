from fastapi import APIRouter

from dependencies import CurrentUserDep, ItemServiceDep
from schemas.item import ItemCreate, ItemOut

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
