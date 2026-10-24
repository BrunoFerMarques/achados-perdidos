from datetime import datetime

from sqlalchemy import DateTime, MetaData, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # the names Postgres itself would give, e.g. users_pkey, items_user_id_fkey
    metadata = MetaData(
        naming_convention={
            "pk": "%(table_name)s_pkey",
            "fk": "%(table_name)s_%(column_0_name)s_fkey",
            "uq": "%(table_name)s_%(column_0_name)s_key",
            "ck": "%(table_name)s_%(constraint_name)s_check",
            "ix": "%(table_name)s_%(column_0_name)s_idx",
        }
    )

    # Mapped[str] becomes TEXT and Mapped[datetime] becomes TIMESTAMPTZ
    type_annotation_map = {str: Text, datetime: DateTime(timezone=True)}
