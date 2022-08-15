from __future__ import annotations

import abc
import decimal
import functools
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Callable, TypeAlias, ClassVar

logger = logging.getLogger(__name__)
decimal.getcontext().rounding = decimal.ROUND_HALF_UP

ONE_MONTH_TD = timedelta(days=30)


def discard_subscription(only_overdue: bool, up_to_date: bool) -> bool:
    """Determines if a subscription should be discarded or not.

    Args:
        only_overdue: if True, up-to-date subscription should be discarded.
        up_to_date: if True, the subscription is up-to-date.

    Returns:
        True if a subscription should be discarded, False otherwise.
    """
    return only_overdue and up_to_date


def from_month_to_month(subscription_when: date, year: int, reference_date: date) -> tuple[int, int]:
    from_, to = 1, 1
    if year == subscription_when.year:
        from_ = subscription_when.month  # The client subscribed to the activity in that year.
    # noinspection PyChainedComparisons
    if year < reference_date.year and year > subscription_when.year:
        to = 13  # The year has passed, meaning there should be transactions for all the months.
    elif year == reference_date.year:
        to = reference_date.month + 1  # The year has some remaining months.

    return from_, to


def month_range(from_: date, to: date):
    from_m, from_y = from_.month, from_.year
    while from_ < to:
        yield from_.month, from_.year

        if from_m == 12:
            from_m, from_y = 0, from_y + 1
        from_m += 1

        from_ = date(from_y, from_m, from_.day)


class OperationalError(Exception):
    """Exception raised when there is an error while doing a system operation.
    """

    def __init__(self, cause: str, **involved_things) -> None:
        super().__init__(cause)
        self.involved_things = involved_things


class InvalidDate(Exception):
    """Exception to be raised when a given date fails to pass a given condition.
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ValidationError(Exception):
    """Exception raised when a validation fails in Validatable.validate(args) method.
    """

    def __init__(self, cause: str, *args: object) -> None:
        super().__init__(cause, *args)


class Validatable(abc.ABC):
    """Interface used as a base for classes that wrap primive values that should be validated.
    """

    def __init__(self, value: Any, **validate_args):
        self._value = self.validate(value, **validate_args)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(value={self._value})"

    def as_primitive(self) -> Any:
        """Returns the wrapped primitive.
        """
        return self._value

    @abc.abstractmethod
    def validate(self, value: Any, **kwargs) -> Any:
        """Validates the given *value*. If the validation succeeds, return the primitive that the Validatable
        implementation stores.

        Keyword Args:
            KeyError if a kwarg is missing.
            Any argument required to validate the value.

        Raises:
            ValidationError if the validation failed.
        """
        raise NotImplementedError


@functools.total_ordering
class Number(Validatable):
    """int wrapper.
    """
    OPTIONAL_INT: ClassVar[int] = -1

    def __eq__(self, other: int | Number) -> bool:
        if isinstance(other, type(self._value)):
            logger.getChild(type(self).__name__).warning(f"Comparing '{repr(self)}' with '{repr(other)}'")

            return self._value == other
        if isinstance(other, type(self)):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __lt__(self, other: Number) -> bool:
        return self._value < other.as_primitive()

    def __sub__(self, other: Number) -> Number:
        return Number(self._value - other.as_primitive())

    def __add__(self, other: Number) -> Number:
        return Number(self._value + other.as_primitive())

    def validate(self, value: str | int, **kwargs) -> int:
        """Validates the given *value*. If the validation succeeds, returns the given *value* as int, regardless of its
        type.

        Keyword Args:
            min_value: minimum valid value. If None, min_value will be -inf.
            max_value: maximum valid value. If None, max_value will be inf.
            optional: the object will store a default int that represents an "optional number". If not given, its True.

        Raises:
            ValidationError if the validation failed.
        """
        if not isinstance(value, (str, int)):
            raise ValidationError(
                f"The type of the argument 'value' must be an 'str' or 'int'. [type(value)={type(value)}]"
            )

        optional = kwargs['optional'] if 'optional' in kwargs else True
        if optional and isinstance(value, str) and (len(value) == 0 or value.isspace()):
            return Number.OPTIONAL_INT

        try:
            int_value = int(value)
        except ValueError:
            raise ValidationError(f"The argument 'value' is not a valid number. [value={value}]")

        if int_value == Number.OPTIONAL_INT:
            raise ValidationError(f"The argument 'value' is not a vali because it is a reserved value. [value="
                                  f"{int_value}]")

        min_value = kwargs['min_value'] if 'min_value' in kwargs else float('-inf')
        max_value = kwargs['max_value'] if 'max_value' in kwargs else float('inf')
        if int_value < min_value or int_value >= max_value:
            raise ValidationError(
                f"The argument 'value' must be in the range [{min_value}, {max_value}). [value={value}]"
            )
        return int_value

    def as_primitive(self) -> Any | None:
        int_value = super().as_primitive()
        return int_value if int_value != Number.OPTIONAL_INT else None


class String(Validatable):
    """str wrapper that supports empty str and str with a max length.
    """

    def __eq__(self, other: str | String) -> bool:
        if isinstance(other, type(self._value)):
            logger.getChild(type(self).__name__).warning(f"Comparing '{repr(self)}' with '{repr(other)}'")
            return self._value == other
        if isinstance(other, type(self)):
            return self._value.lower() == other._value.lower()
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def validate(self, value: str, **kwargs) -> str:
        """Validates the given *value*. If the validation succeeds, return the given *value*.

        Keyword Args:
            optional: True if the String may be empty, False otherwise. If not given, it is True.
            max_len: maximum amount of characters.
            invalid_values: values that can't be used.

        Raises:
            KeyError if a kwarg is missing.
            ValidationError if the validation failed.
        """
        optional = True if 'optional' not in kwargs else kwargs['optional']
        max_len = 1024 if 'max_len' not in kwargs else kwargs['max_len']

        if not optional and len(value) == 0:
            raise ValidationError(f"The argument 'value' cannot be empty. [value={value}, optional={optional}]")
        if 'invalid_values' in kwargs:
            for invalid in kwargs['invalid_values']:
                if invalid in value:
                    raise ValidationError(f"The argument 'value' contains an invalid str. "
                                          f"[value{value}, invalid_value={invalid}")
        if len(value) >= max_len:
            raise ValidationError(f"The argument 'value' has more characters than allowed. "
                                  f"[len(value)={len(value)}, max_len={max_len}]")
        return value

    def contains(self, substring: str | String) -> bool:
        if isinstance(substring, String):
            substring = substring.as_primitive()
        return substring.lower() in self._value.lower()


class Currency(Validatable):
    """Decimal wrapper that supports a max currency value.
    """

    # noinspection PyShadowingBuiltins
    @classmethod
    def fmt(
            cls, currency: Currency, places: int = 2, symbol: str = '$', sep: str = '.', dp_sep: str = ','
    ) -> str:
        """Transforms a Currency to str.

        This method was extracted from https://docs.python.org/3/library/decimal.html#recipes.

        Args:
            currency: currency to transform.
            places: numbers after the decimal point.
            symbol: symbol of the currency.
            sep: int part separator.
            dp_sep: separator between the int and the decimal part.

        Returns:
            The Currency as str.
        """
        dp_sep = '' if places == 0 else dp_sep

        q = Decimal(10) ** -places  # 2 places --> '0.01'
        sign, digits, exp = currency.as_primitive().quantize(q).as_tuple()
        digits = list(map(str, digits))

        result = []
        build, next = result.append, digits.pop
        if sign:
            build(')')
        for i in range(places):  # Fills positions after the decimal point.
            build(next() if digits else '0')
        if places:
            build(dp_sep)
        if not digits:
            build('0')
        i = 0
        while len(digits) > 0:
            build(next())
            i += 1
            if i == 3 and len(digits) > 0:
                i = 0
                build(sep)
        build(symbol)
        build('(' if sign else '')
        return ''.join(reversed(result))

    def __eq__(self, other: Currency) -> bool:
        if isinstance(other, type(self)):
            return self._value == other.as_primitive()
        return NotImplemented

    def validate(self, value: str | int, **kwargs) -> Decimal:
        """Validates the given *value*. If the validation succeeds, returns the created Decimal object.

        Keyword Args:
            max_currency: maximum valid currency.
            positive: if True, the currency value must be zero or greater.

        Raises:
            KeyError if a kwarg is missing.
            ValidationError if the validation failed.
        """
        if isinstance(value, str) and "," in value:
            a, b = value.split(",")
            value = f"{a.replace('.', '')}.{b}"
        try:
            value = Decimal(value)
        except InvalidOperation:
            raise ValidationError(f"The argument 'value' is not a valid currency. [value={value}]")

        if 'positive' in kwargs and kwargs['positive'] and value < 0:
            raise ValidationError(f"Negative currencies are not allowed. [value={value}]")
        return value

    def increase(self, other_currency: Currency) -> None:
        self._value += other_currency.as_primitive()

    def __sub__(self, other: Currency) -> Currency:
        return Currency(self._value - other.as_primitive(), positive=False)

    def multiply_by_scalar(self, n: int) -> Currency:
        return Currency(self._value * n)


Balance: TypeAlias = dict[str, dict[str, Currency]]


@dataclass
class Client:
    """Stores information about a client.
    """

    id: int
    name: String = field(compare=False)
    admission: date = field(compare=False)
    birth_day: date = field(compare=False)
    dni: Number | None = field(compare=False, default=None)
    is_active: bool = field(compare=False, default=True)
    _subscriptions: dict[String, Subscription] = field(default_factory=dict, compare=False, init=False)

    def age(self, reference_date: date | None = None) -> int:
        today = date.today() if reference_date is None else reference_date
        cmp = (today.month, today.day) < (self.birth_day.month, self.birth_day.day)
        return today.year - self.birth_day.year - cmp

    def add(self, subscription: Subscription):
        """Registers the *subscription*.
        """
        self._subscriptions[subscription.activity.name] = subscription

    def unsubscribe(self, activity: Activity):
        """Unsubscribes the client from *activity*.
        """
        self._subscriptions.pop(activity.name)

    def is_subscribed(self, activity: Activity) -> bool:
        """Returns True if the client subscribed to *activity*.
        """
        return activity.name in self._subscriptions

    def n_subscriptions(self) -> int:
        """Returns the number of activities subscriptions that the client has.
        """
        return len(self._subscriptions)

    def subscriptions(self) -> Iterable[Subscription]:
        """Returns the activities subscriptions.
        """
        return self._subscriptions.values()

    def mark_as_charged(
            self, activity_name: String, year: int, month: int, transaction: Transaction
    ) -> Subscription:
        self._subscriptions[activity_name].add_transaction(year, month, transaction)
        return self._subscriptions[activity_name]


@dataclass
class Activity:
    """Stores general information about an activity.
    """

    id: int = field(compare=False)
    name: String
    price: Currency = field(compare=False)
    description: String = field(compare=False)
    charge_once: bool = field(compare=False, default=False)
    locked: bool = field(compare=False, default=False)
    removed: bool = field(compare=False, default=False)


defaultdict_list = functools.partial(defaultdict, list)


@dataclass
class Subscription:
    """Stores information about a client's subscription in an activity.
    """

    when: date
    client: Client
    activity: Activity
    _transactions: dict[tuple[int, int], list[Transaction]] = field(default_factory=defaultdict_list, compare=False,
                                                                    init=False)

    def transactions(self):
        for year_month, transaction in self._transactions:
            yield *year_month, transaction

    def transaction(self, year: int, month: int) -> list[Transaction]:
        return self._transactions.get((year, month), None)

    def add_transaction(self, year: int, month: int, transaction: Transaction):
        self._transactions[(year, month)].append(transaction)

    def charged_amount(self, year: int, month: int) -> Currency:
        amount = Currency(0)
        for transaction in self._transactions[(year, month)]:
            amount.increase(transaction.amount)
        return amount

    def last_transaction(self, year: int, month: int) -> Transaction:
        _transactions = sorted(self._transactions[(year, month)], key=lambda transaction: transaction.id)
        return _transactions[-1]

    def is_charged(self, year: int, month: int):
        """Checks if the subscription has a registered charge in the *month* and *year*.
        """
        return (year, month) in self._transactions

    def unpaid_months(self, reference_date: date) -> Iterable[int, int]:
        for year in range(self.when.year, reference_date.year + 1):
            for month in range(*from_month_to_month(self.when, year, reference_date)):
                if not self.is_charged(year, month):
                    yield year, month


@dataclass
class Transaction:
    """Stores information about a transaction.
    """

    id: int
    type: str = field(compare=False)
    when: date = field(compare=False)
    amount: Currency = field(compare=False)
    method: str = field(compare=False)
    responsible: String = field(compare=False)
    description: str = field(compare=False)
    client: Client | None = field(compare=False, default=None)
    balance_date: date | None = field(compare=False, default=None)


class Filter(abc.ABC):
    """Filter base class.
    """

    def __init__(self, name: str, display_name: str, translate_fun: Callable[[Any, Any], bool] | None = None) -> None:
        self.name = name
        self.display_name = display_name
        self.translate_fun = translate_fun

    def __eq__(self, o: Filter) -> bool:
        return self.name == o.name

    def __hash__(self) -> int:
        return hash(self.name)

    @abc.abstractmethod
    def passes(self, to_filter: Any, filter_value: Any) -> bool:
        """Returns True if *to_filter* passes the implemented filter with the given *filter_value*. *to_filter* is an
        in memory object.
        """
        raise NotImplementedError

    def passes_in_repo(self, to_filter: Any, filter_value: Any) -> bool:
        """Returns True if *to_filter* passes the implemented filter with the given *filter_value*. *to_filter* is an
        object that comes from a repository.
        """
        if self.translate_fun is None:
            raise AttributeError(f"The filter '{self.name}' of type '{type(self)}' does not have a 'transalte_fun'.")
        return self.translate_fun(to_filter, filter_value)


class NumberEqual(Filter):

    def __init__(
            self, name: str, display_name: str, attr: str, translate_fun: Callable[[Any, Any], bool] | None = None
    ) -> None:
        super().__init__(name, display_name, translate_fun)
        self.attr = attr

    def passes(self, to_filter: Any, filter_value: Any) -> bool:
        """Returns True if the attr *self.attr* of the object *to_filter* is equal to *filter_value*.
        """
        if not hasattr(to_filter, self.attr):
            raise AttributeError(f"The filter '{self.name}: {type(self)}' expects a 'to_filter' argument that has the "
                                 f"attribute '{self.attr}'.")

        if not isinstance(filter_value, (int, Number)):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the argument 'filter_value' to be an "
                            f"'int' or 'Number', but received a '{type(filter_value)}'.")

        attr_value = getattr(to_filter, self.attr)
        if not isinstance(attr_value, Number):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the attribute '{self.attr}' to be a "
                            f"'Number', not a '{type(attr_value)}'.")

        return attr_value == filter_value


class TextLike(Filter):

    def __init__(
            self, name: str, display_name: str, attr: str, translate_fun: Callable[[Any, Any], bool] | None = None
    ) -> None:
        super().__init__(name, display_name, translate_fun)
        self.attr = attr

    def passes(self, to_filter: Any, filter_value: str | String) -> bool:
        """Returns True if the attr *self.attr* of the object *to_filter* contains the *filter_value*.
        """
        if not hasattr(to_filter, self.attr):
            raise AttributeError(f"The filter '{self.name}: {type(self)}' expects a 'to_filter' argument that has the "
                                 f"attribute '{self.attr}'.")

        if not isinstance(filter_value, (str, String)):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the argument 'filter_value' to be a 'str' "
                            f"or 'String', but received a '{type(filter_value)}'.")

        attr_value = getattr(to_filter, self.attr)
        if not isinstance(attr_value, String):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the attribute '{self.attr}' to be a "
                            f"'String', not a '{type(attr_value)}'.")

        return attr_value.contains(filter_value)


class ClientLike(Filter):

    def passes(self, to_filter: Any, filter_value: str) -> bool:
        """Returns True if the attr *name* of the attr *client* of the object *to_filter* contains the *filter_value*.
        """
        if not hasattr(to_filter, "client"):
            raise TypeError(f"The argument 'to_filter' must be of a type that has the attribute 'client'. Instead, it "
                            f"is of type '{type(to_filter)}'.")
        if not isinstance(to_filter.client, Client):
            raise TypeError(f"The argument 'to_filter' must be a 'Client', not a '{type(to_filter)}'.")
        if not isinstance(filter_value, str):
            raise TypeError(f"The argument 'filter_value' must be a 'str', not a '{type(filter_value)}'.")

        return to_filter.client.name.contains(filter_value)


class TextEqual(Filter):
    def __init__(
            self, name: str, display_name: str, attr: str, translate_fun: Callable[[Any, Any], bool] | None = None
    ) -> None:
        super().__init__(name, display_name, translate_fun)
        self.attr = attr

    def passes(self, to_filter: Any, filter_value: str | String) -> bool:
        """Returns True if the attr *self.attr* of the object *to_filter* is equal to *filter_value*.
        """
        if not hasattr(to_filter, self.attr):
            raise AttributeError(f"The filter '{self.name}: {type(self)}' expects a 'to_filter' argument that has the "
                                 f"attribute '{self.attr}'.")

        if not isinstance(filter_value, (str, String)):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the argument 'filter_value' to be a 'str' "
                            f"or 'String', but received a '{type(filter_value)}'.")

        attr_value = getattr(to_filter, self.attr)
        if not isinstance(attr_value, String):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the attribute '{self.attr}' to be a "
                            f"'String', not a '{type(attr_value)}'.")

        return attr_value == filter_value


class DateGreater(Filter):
    def __init__(
            self, name: str, display_name: str, attr: str, translate_fun: Callable[[Any, Any], bool] | None = None
    ) -> None:
        super().__init__(name, display_name, translate_fun)
        self.attr = attr

    def passes(self, to_filter: Any, filter_value: date) -> bool:
        """Returns True if date stored in the attr *self.attr* of the object *to_filter* is greater or equal than
         *filter_value* date.
        """
        if not hasattr(to_filter, self.attr):
            raise AttributeError(f"The filter '{self.name}: {type(self)}' expects a 'to_filter' argument that has the "
                                 f"attribute '{self.attr}'.")
        if not isinstance(filter_value, date):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the argument 'filter_value' to be a "
                            f"'date', but received a '{type(filter_value)}'.")

        return getattr(to_filter, self.attr) >= filter_value


class DateLesser(Filter):
    def __init__(
            self, name: str, display_name: str, attr: str, translate_fun: Callable[[Any, Any], bool] | None = None
    ) -> None:
        super().__init__(name, display_name, translate_fun)
        self.attr = attr

    def passes(self, to_filter: Any, filter_value: date) -> bool:
        """Returns True if date stored in the attr *self.attr* of the object *to_filter* is lesser or equal than
         *filter_value* date.
        """
        if not hasattr(to_filter, self.attr):
            raise AttributeError(f"The filter '{self.name}: {type(self)}' expects a 'to_filter' argument that has the "
                                 f"attribute '{self.attr}'.")
        if not isinstance(filter_value, date):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the argument 'filter_value' to be a "
                            f"'date', but received a '{type(filter_value)}'.")

        return getattr(to_filter, self.attr) <= filter_value
