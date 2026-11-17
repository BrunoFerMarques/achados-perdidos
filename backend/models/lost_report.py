from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, func
from sqlalchemy.orm import Mapped, mapped_column

from domain.lost_reports import LostReportStatus
from models.base import Base


class LostReport(Base):
    __tablename__ = "lost_reports"
    __table_args__ = (
        CheckConstraint("btrim(description) <> ''", name="description"),
        CheckConstraint(
            "status IN ('ativo', 'encerrado', 'expirado')",
            name="status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    color_id: Mapped[int] = mapped_column(ForeignKey("colors.id"))
    description: Mapped[str]
    lost_date: Mapped[date]
    status: Mapped[str] = mapped_column(
        default=LostReportStatus.ATIVO.value,
        server_default=LostReportStatus.ATIVO.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
