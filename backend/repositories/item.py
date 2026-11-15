from models import Item
from repositories.base import Repository


class ItemRepository(Repository[Item]):
    model = Item
