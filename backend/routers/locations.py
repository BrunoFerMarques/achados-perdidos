from fastapi import APIRouter

from dependencies import LocationServiceDep
from schemas.location import LocationOut

router = APIRouter(prefix="/v1/locations", tags=["locations"])


@router.get("", response_model=list[LocationOut])
def list_locations(locations: LocationServiceDep):
    return locations.list_all()
