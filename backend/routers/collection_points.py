from fastapi import APIRouter

from dependencies import CollectionPointServiceDep, CurrentUserDep
from schemas.collection_point import AttendantLink, CollectionPointCreate, CollectionPointOut
from schemas.user import UserOut

# listing is public, like categories; everything else is admin only, checked by the service (403)
router = APIRouter(prefix="/v1/collection-points", tags=["collection points"])


@router.get("", response_model=list[CollectionPointOut])
def list_collection_points(points: CollectionPointServiceDep):
    return points.list_all()


@router.post("", status_code=201, response_model=CollectionPointOut)
def create_collection_point(
    payload: CollectionPointCreate, current_user: CurrentUserDep, points: CollectionPointServiceDep
):
    return points.create(current_user, payload.name)


@router.get("/{point_id}/attendants", response_model=list[UserOut])
def list_attendants(point_id: int, current_user: CurrentUserDep, points: CollectionPointServiceDep):
    return points.list_attendants(current_user, point_id)


@router.post("/{point_id}/attendants", status_code=201, response_model=UserOut)
def link_attendant(
    point_id: int,
    payload: AttendantLink,
    current_user: CurrentUserDep,
    points: CollectionPointServiceDep,
):
    return points.link(current_user, point_id, payload.user_id)


@router.delete("/{point_id}/attendants/{user_id}", status_code=204)
def unlink_attendant(
    point_id: int, user_id: int, current_user: CurrentUserDep, points: CollectionPointServiceDep
):
    points.unlink(current_user, point_id, user_id)
