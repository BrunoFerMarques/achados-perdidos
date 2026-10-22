from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, FetchedValue, Identity, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="name"),
        CheckConstraint(r"email ~ '^[^@\s]+@[^@\s]+$'", name="email"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str]
    email: Mapped[str]
    password_hash: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # kept current by the set_updated_at trigger
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), server_onupdate=FetchedValue()
    )


# one account per e-mail, regardless of case
Index("users_email_key", func.lower(User.email), unique=True)
