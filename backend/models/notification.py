from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Identity, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.item import Item


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # RN31: um par relato e item nunca gera duas notificações
        UniqueConstraint(
            "lost_report_id",
            "item_id",
            name="notifications_lost_report_id_item_id_key",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    lost_report_id: Mapped[int] = mapped_column(
        ForeignKey("lost_reports.id", ondelete="CASCADE"),
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(default=None)

    item: Mapped[Item] = relationship()
