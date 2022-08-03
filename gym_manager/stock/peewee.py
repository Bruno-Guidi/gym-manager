from gym_manager.core.base import String, Number, Currency
from gym_manager.stock.core import ItemRepo, Item


class SqliteItemRepo(ItemRepo):
    def create(self, name: String, amount: Number, price: Currency, is_fixed: bool = False) -> Item:
        pass

    def remove(self, item: Item):
        pass

    def update(self, item: Item):
        pass