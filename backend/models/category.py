from sqlalchemy import BigInteger, CheckConstraint, Identity
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (CheckConstraint("btrim(name) <> ''", name="name"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
