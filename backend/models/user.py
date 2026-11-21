from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, FetchedValue, Identity, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from domain.roles import Role
from models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="name"),
        CheckConstraint(r"email ~ '^[^@\s]+@[^@\s]+$'", name="email"),
        CheckConstraint("role IN ('usuario', 'atendente', 'admin')", name="role"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str]
    email: Mapped[str]
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(server_default=Role.USUARIO)
    # RN16: the last time an admin lifted a block; failed claims before it no longer count.
    # The block itself isn't stored: domain/blocking.py works it out from the rejections
    unblocked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # kept current by the set_updated_at trigger
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), server_onupdate=FetchedValue()
    )


# one account per e-mail, regardless of case
Index("users_email_key", func.lower(User.email), unique=True)
