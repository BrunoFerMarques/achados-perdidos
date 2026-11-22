# every model is imported here, so Alembic autogenerate sees all tables in Base.metadata
from models.base import Base
from models.category import Category
from models.claim import Claim, ClaimAnswer
from models.collection_point import CollectionPoint, CollectionPointAttendant
from models.color import Color
from models.custody import CustodyRecord
from models.item import Item, ItemQuestion
from models.location import Location
from models.lost_report import LostReport
from models.user import User

__all__ = [
    "Base",
    "Category",
    "Claim",
    "ClaimAnswer",
    "CollectionPoint",
    "CollectionPointAttendant",
    "Color",
    "CustodyRecord",
    "Item",
    "ItemQuestion",
    "Location",
    "LostReport",
    "User",
]
