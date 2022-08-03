from typing import Generator

from peewee import Model, IntegerField, CharField

from gym_manager.core.base import String, Number, Currency
from gym_manager.core.persistence import FilterValuePair
from gym_manager.peewee import DATABASE_PROXY
from gym_manager.stock.core import ItemRepo, Item


class ItemModel(Model):
    code = IntegerField(primary_key=True)
    item_name = CharField()
    amount = IntegerField()
    price = CharField()

    class Meta:
        database = DATABASE_PROXY


class SqliteItemRepo(ItemRepo):
    def __init__(self):
        DATABASE_PROXY.create_tables([ItemModel])

    def create(self, name: String, amount: Number, price: Currency, is_fixed: bool = False) -> Item:
        record = ItemModel.create(item_name=name.as_primitive(), amount=amount.as_primitive(),
                                  price=price.as_primitive())
        return Item(record.code, name, amount, price)

    def remove(self, item: Item):
        pass

    def update(self, item: Item):
        pass

    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[Item, None, None]:
        query = ItemModel.select()
        if filters is not None:
            for filter_, value in filters:
                query = query.where(filter_.passes_in_repo(ItemModel, value))

        if page_len is not None:
            query = query.order_by(ItemModel.item_name).paginate(page, page_len)

        for record in query:
            yield Item(record.code, String(record.item_name), Number(record.amount), Currency(record.price))
