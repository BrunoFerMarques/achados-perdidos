"""Service for managing lost-item reports."""

from collections.abc import Sequence
from datetime import date

from domain.errors import (
    CategoryNotFound,
    ColorNotFound,
    LocationNotFound,
    LostReportNotFound,
)
from domain.lost_reports import LostReportStatus, ensure_transition
from domain.permissions import (
    can_access_lost_report,
    can_create_lost_report,
    can_list_lost_reports,
    ensure,
)
from models import User
from models.lost_report import LostReport
from repositories.unit_of_work import UnitOfWork


class LostReportService:
    """Lost item report use cases. Enforces permissions and business validations."""

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    def create(
        self,
        actor: User,
        category_id: int,
        location_id: int,
        color_id: int,
        description: str,
        lost_date: date,
    ) -> LostReport:
        ensure(can_create_lost_report(actor))

        # Validate existence of foreign keys before creating to avoid 500 errors
        if self._uow.categories.get(category_id) is None:
            raise CategoryNotFound()
        if self._uow.locations.get(location_id) is None:
            raise LocationNotFound()
        if self._uow.colors.get(color_id) is None:
            raise ColorNotFound()

        report = LostReport(
            user_id=actor.id,
            category_id=category_id,
            location_id=location_id,
            color_id=color_id,
            description=description,
            lost_date=lost_date,
            status=LostReportStatus.ATIVO,
        )
        self._uow.lost_reports.add(report)
        self._uow.commit()
        return report

    def get(self, actor: User, report_id: int) -> LostReport:
        return self._find(actor, report_id)

    def list_mine(self, actor: User) -> Sequence[LostReport]:
        ensure(can_list_lost_reports(actor))
        return self._uow.lost_reports.list_by_user(actor.id)

    def close(self, actor: User, report_id: int) -> LostReport:
        report = self._find(actor, report_id)
        ensure_transition(LostReportStatus(report.status), LostReportStatus.ENCERRADO)
        report.status = LostReportStatus.ENCERRADO
        self._uow.commit()
        return report

    def _find(self, actor: User, report_id: int) -> LostReport:
        report = self._uow.lost_reports.get(report_id)
        if report is None or not can_access_lost_report(actor, report.user_id):
            raise LostReportNotFound()
        return report
