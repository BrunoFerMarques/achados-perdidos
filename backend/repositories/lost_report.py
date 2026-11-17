"""Repository for lost-item reports."""

from collections.abc import Sequence

from sqlalchemy import select

from domain.lost_reports import LostReportStatus
from models.lost_report import LostReport
from repositories.base import Repository


class LostReportRepository(Repository[LostReport]):
    model = LostReport

    def list_active(self) -> Sequence[LostReport]:
        """Returns all active reports, required for the matching algorithm (RN30)."""
        stmt = (
            select(LostReport)
            .where(LostReport.status == LostReportStatus.ATIVO)
            .order_by(LostReport.id)
        )
        return self._session.scalars(stmt).all()

    def list_by_user(self, user_id: int) -> Sequence[LostReport]:
        """Lists all reports created by a specific user, newest first."""
        stmt = (
            select(LostReport).where(LostReport.user_id == user_id).order_by(LostReport.id.desc())
        )
        return self._session.scalars(stmt).all()
