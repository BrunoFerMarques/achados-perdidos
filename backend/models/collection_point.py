from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class CollectionPoint(Base):
    __tablename__ = "collection_points"
    __table_args__ = (CheckConstraint("btrim(name) <> ''", name="name"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class CollectionPointAttendant(Base):
    """Which attendant works at which collection point (RN40): one row per pair."""

    __tablename__ = "collection_point_attendants"

    # a link means nothing without either side, so it goes when the point or the user goes
    point_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collection_points.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )