from fastapi import APIRouter

from dependencies import CategoryServiceDep
from schemas.category import CategoryOut

router = APIRouter(prefix="/v1/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(categories: CategoryServiceDep):
    return categories.list_all()
