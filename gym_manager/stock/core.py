import abc

from gym_manager.core.api import CreateTransactionFn
from gym_manager.core.base import Currency, String, Number, OperationalError


class Item:
    def __init__(self, code: int, name: String, amount: Number, price: Currency, is_fixed: bool = False):
        """Init.

        Args:
            code: code of the item.
            name: name of the item.
            amount: item's amount.
            price: price to charge for the item.
            is_fixed: if True, the amount isn't reduced after charging for the item.
        """
        self.code = code
        self.name = name
        self.amount = amount
        self.price = price
        self.is_fixed = is_fixed

    def total_price(self, units: int) -> Currency:
        return self.price.multiply_by_scalar(units)


class ItemRepo(abc.ABC):
    @abc.abstractmethod
    def create(self, name: String, amount: Number, price: Currency, is_fixed: bool = False) -> Item:
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, item: Item):
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, item: Item):
        raise NotImplementedError


def create_item(item_repo: ItemRepo, name: String, amount: Number, price: Currency, is_fixed: bool = False) -> Item:
    return item_repo.create(name, amount, price, is_fixed)


def remove_item(item_repo: ItemRepo, item: Item):
    item_repo.remove(item)


def update_item(item_repo: ItemRepo, item: Item, name: String, price: Currency):
    item.name = name
    item.price = price
    item_repo.update(item)


def update_item_amount(
        item_repo: ItemRepo, item: Item, amount: Number, update_cause: String) -> tuple[Item, Number, String]:
    if amount > item.amount:
        raise OperationalError(f"The [{item.code=}] does not have [{amount=}] units. It has [{item.amount=}]")

    item.amount += amount
    item_repo.update(item)

    return item, amount, update_cause  # This is returned, so it can be logged by log_responsible decorator.


def register_charge(
        item_repo: ItemRepo, item: Item, amount: Number, create_transaction_fn: CreateTransactionFn
) -> tuple[Item, Number]:
    if amount > item.amount:
        raise OperationalError(f"The [{item.code=}] does not have [{amount=}] units. It has [{item.amount=}]")

    if not item.is_fixed:
        item.amount -= amount

    create_transaction_fn()
    item_repo.update(item)

    return item, amount  # This is returned, so it can be logged by log_responsible decorator.


