# every model is imported here, so Alembic autogenerate sees all tables in Base.metadata
from models.base import Base
from models.category import Category
from models.collection_point import CollectionPoint, CollectionPointAttendant
from models.color import Color
from models.location import Location
from models.user import User

__all__ = [
    "Base",
    "Category",
    "CollectionPoint",
    "CollectionPointAttendant",
    "Color",
    "Location",
    "User",
]