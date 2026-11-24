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
    # último desbloqueio feito pelo admin. Falhas antes disso não contam mais, e o bloqueio em
    # si nem é salvo: o domain/blocking.py calcula pelas rejeições
    unblocked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # mantido em dia pelo trigger set_updated_at
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), server_onupdate=FetchedValue()
    )


# um cadastro por e-mail, ignorando maiúsculas
Index("users_email_key", func.lower(User.email), unique=True)
