
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Identity, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("lost_report_id", "item_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    lost_report_id: Mapped[int] = mapped_column(
        ForeignKey("lost_reports.id", ondelete="CASCADE"),
        index=True,
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"),
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(
        default=None
    )
