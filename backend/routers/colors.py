from fastapi import APIRouter

from dependencies import ColorServiceDep
from schemas.color import ColorOut

router = APIRouter(prefix="/v1/colors", tags=["colors"])


@router.get("", response_model=list[ColorOut])
def list_colors(colors: ColorServiceDep):
    return colors.list_all()
