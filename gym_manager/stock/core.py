from gym_manager.core.base import Currency, String


class Item:
    def __init__(self, code: int, name: String, amount: int, price: Currency, is_fixed: bool = False):
        self.code = code
        self.name = name
        self.amount = amount
        self.price = price
        self.is_fixed = is_fixed

    def total_price(self, units: int) -> Currency:
        return self.price.multiply_by_scalar(units)



