from fastapi import APIRouter

from dependencies import CurrentUserDep, LostReportServiceDep
from schemas.lost_report import LostReportCreate, LostReportOut

router = APIRouter(prefix="/v1/lost-reports", tags=["lost reports"])


@router.post("", status_code=201, response_model=LostReportOut)
def create_lost_report(
    payload: LostReportCreate,
    current_user: CurrentUserDep,
    reports: LostReportServiceDep,
):
    return reports.create(
        actor=current_user,
        category_id=payload.category_id,
        location_id=payload.location_id,
        color_id=payload.color_id,
        description=payload.description,
        lost_date=payload.lost_date,
    )


@router.get("", response_model=list[LostReportOut])
def list_my_lost_reports(
    current_user: CurrentUserDep,
    reports: LostReportServiceDep,
):
    return reports.list_mine(current_user)


@router.get("/{report_id}", response_model=LostReportOut)
def get_lost_report(
    report_id: int,
    current_user: CurrentUserDep,
    reports: LostReportServiceDep,
):
    return reports.get(current_user, report_id)


@router.patch("/{report_id}/close", response_model=LostReportOut)
def close_lost_report(
    report_id: int,
    current_user: CurrentUserDep,
    reports: LostReportServiceDep,
):
    return reports.close(current_user, report_id)
