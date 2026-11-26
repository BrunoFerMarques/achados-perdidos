import logging

from domain.items import ItemStatus
from domain.lost_reports import LostReportStatus
from domain.match import DEFAULT_CONFIG, MatchConfig, calculate_match
from models import Item, LostReport
from repositories.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class MatchHandler:
    """Process matches after the originating operation commits.

    The caller must commit its changes before invoking this handler.
    Each event runs in a separate transaction.

    If matching fails, all notifications from that event are
    rolled back without undoing the originating operation.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        config: MatchConfig = DEFAULT_CONFIG,
    ):
        self._uow = uow
        self._config = config

    def on_item_available(self, item: Item) -> None:
        try:
            # RN30: compare available items with active reports
            if item.status != ItemStatus.AVAILABLE:
                return

            for report in self._uow.lost_reports.list_active(category_id=item.category_id):
                self._match(report, item)

            self._uow.commit()

        except Exception:
            self._uow.rollback()
            logger.exception("Erro no match de item disponível")

    def on_report_created(self, report: LostReport) -> None:
        try:
            # RN30: compare active reports with available items
            if report.status != LostReportStatus.ATIVO:
                return

            for item in self._uow.items.list_available(category_id=report.category_id):
                self._match(report, item)

            self._uow.commit()

        except Exception:
            self._uow.rollback()
            logger.exception("Erro no match de relato criado")

    def _match(self, report: LostReport, item: Item) -> None:
        result = calculate_match(report, item, self._config)

        if result.matched:
            # RN31: prevent duplicate notifications
            self._uow.notifications.create_if_not_exists(
                report.id,
                item.id,
            )
