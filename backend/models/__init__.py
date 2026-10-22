# every model is imported here, so Alembic autogenerate sees all tables in Base.metadata
from models.base import Base
from models.user import User

__all__ = ["Base", "User"]
