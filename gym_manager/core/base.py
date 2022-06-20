from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Callable

ONE_MONTH_TD = timedelta(days=30)


def pay_day_passed(last_paid_on: date, today: date) -> bool:
    """The pay day passed if more than 30 days have passed since the payment date (inclusive).
    """
    return today - ONE_MONTH_TD >= last_paid_on


class ValidationError(Exception):

    def __init__(self, cause: str, *args: object) -> None:
        super().__init__(cause, *args)


class Validatable(abc.ABC):

    def __init__(self, value: Any, **validate_args):
        self._value = self.validate(value, **validate_args)

    def __str__(self) -> str:
        return str(self._value)

    def as_primitive(self) -> Any:
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


class Number(Validatable):

    def __eq__(self, o) -> bool:
        if isinstance(o, type(self._value)):
            return self._value == o
        return self._value == o._value

    def __hash__(self) -> int:
        return hash(self._value)

    def validate(self, value: str | int, **kwargs) -> int:
        """Validates the given *value*. If the validation succeeds, returns the given *value* as int, regardless of its
        type.

        Keyword Args:
            min_value: minimum valid value. If None, min_value will be -inf.
            max_value: maximum valid value. If None, max_value will be inf.

        Raises:
            ValidationError if the validation failed.
        """
        if not isinstance(value, (str, int)):
            raise ValidationError(f"The type of the argument 'value' must be an 'str' or 'int'. [type(value)={type(value)}]")
        try:
            int_value = int(value)
        except ValueError:
            raise ValidationError(f"The argument 'value' is not a valid number. [value={value}]")
        min_value = kwargs['min_value'] if 'min_value' in kwargs else float('-inf')
        max_value = kwargs['max_value'] if 'max_value' in kwargs else float('inf')
        if int_value < min_value or int_value >= max_value:
            raise ValidationError(f"The argument 'value' must be in the range [{min_value}, {max_value}). [value={value}]")
        return int_value


class String(Validatable):

    def validate(self, value: str, **kwargs) -> str:
        """Validates the given *value*. If the validation succeeds, return the given *value*.

        Keyword Args:
            optional: True if the String may be empty, False otherwise. If not given, it is False.
            max_len: maximum amount of characters.

        Raises:
            KeyError if a kwarg is missing.
            ValidationError if the validation failed.
        """
        if 'max_len' not in kwargs:
            raise KeyError(f"The method is missing the kwarg 'max_len'. [kwargs={kwargs}]")
        optional = False if 'optional' not in kwargs else kwargs['optional']

        if not optional and len(value) == 0:
            raise ValidationError(f"The argument 'value' cannot be empty. [value={value}, optional={optional}]")
        if len(value) >= kwargs['max_len']:
            raise ValidationError(f"The argument 'value' has more characters than allowed. "
                                  f"[len(value)={len(value)}, max_len={kwargs['max_len']}]")
        return value

    def contains(self, substring: str) -> bool:
        return substring in self._value


class Currency(Validatable):

    def validate(self, value: str, **kwargs) -> Decimal:
        """Validates the given *value*. If the validation succeeds, returns the created Decimal object.

        Keyword Args:
            max_currency: maximum valid currency.

        Raises:
            KeyError if a kwarg is missing.
            ValidationError if the validation failed.
        """
        if 'max_currency' not in kwargs:
            raise KeyError(f"The method is missing the kwarg 'max_currency'. [kwargs={kwargs}]")

        try:
            value = Decimal(value)
        except InvalidOperation:
            raise ValidationError(f"The argument 'value' is not a valid currency. [value={value}]")
        if value >= kwargs['max_currency']:
            raise ValidationError(f"The argument 'value' must be lesser than {kwargs['max_currency']}. [value={value}]")
        return value


class NotSignedUp(KeyError):
    """Exception thrown when the *client* isn't registered in the *activity*.
    """
    def __init__(self, client: Client, activity_id: int, *args: object) -> None:
        msg = f"The client '{client.dni} - {client.name}' is not signed up in the activity '{activity_id}'"
        super().__init__(msg, *args)


@dataclass
class Client:
    dni: Number
    name: String = field(compare=False)
    admission: date = field(compare=False)
    telephone: String = field(compare=False)
    direction: String = field(compare=False)
    is_active: bool = field(compare=False)
    _inscriptions: dict[int, Inscription] = field(default_factory=dict, compare=False, init=False)

    def sign_on(self, inscription: Inscription):
        """Registers the given *inscription*.
        """
        self._inscriptions[inscription.activity.id] = inscription

    def cancel(self, inscription: Inscription):
        self._inscriptions.pop(inscription.activity.id)

    def is_signed_up(self, activity: Activity) -> bool:
        return activity.id in self._inscriptions

    def n_inscriptions(self) -> int:
        return len(self._inscriptions)

    def inscriptions(self) -> Iterable[Inscription]:
        return self._inscriptions.values()

    def register_charge(self, activity: Activity, transaction: Transaction):
        """Registers that the client was charged for the activity.
        """
        self._inscriptions[activity.id].register_charge(transaction)


@dataclass
class Activity:
    """Stores general information about an activity.
    """
    id: int
    name: String
    price: Currency
    pay_once: bool
    description: String


@dataclass
class Inscription:
    """Stores information about a customer's inscription in an activity.
    """
    when: date
    client: Client
    activity: Activity
    transaction: Transaction | None = None

    def charge_day_passed(self, today: date) -> bool:
        if self.transaction is None:
            # More than 30 days passed since the client signed up on the activity, so he should be charged.
            return pay_day_passed(self.when, today)
        return pay_day_passed(self.transaction.when, today)

    def register_charge(self, transaction: Transaction):
        """Updates the inscription with the given *transaction*.
        """
        if self.client != transaction.client:
            raise ValueError(f"The client '{transaction.client.name}' is being charged for the activity "
                             f"'{self.activity.name}' that should be charged to the client '{self.client.name}'.")
        self.transaction = transaction


@dataclass
class Transaction:
    id: int
    type: String
    client: Client
    when: date
    amount: Currency
    method: String
    responsible: String
    description: String


class Filter(abc.ABC):

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
        raise NotImplementedError

    def passes_in_repo(self, to_filter: Any, filter_value: Any) -> bool:
        if self.translate_fun is None:
            raise AttributeError(f"The filter '{self.name}' of type '{type(self)}' does not have a 'transalte_fun'.")
        return self.translate_fun(to_filter, filter_value)


class TextLike(Filter):

    def __init__(
            self, name: str, display_name: str, attr: str, translate_fun: Callable[[Any, Any], bool] | None = None
    ) -> None:
        super().__init__(name, display_name, translate_fun)
        self.attr = attr

    def passes(self, to_filter: Any, filter_value: str) -> bool:
        if not hasattr(to_filter, self.attr):
            raise AttributeError(f"The filter '{self.name}: {type(self)}' expects a 'to_filter' argument that has the "
                                 f"attribute '{self.attr}'.")

        if not isinstance(filter_value, str):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the argument 'filter_value' to be a 'str'"
                            f", but received a '{type(filter_value)}'.")

        attr_value = getattr(to_filter, self.attr)
        if not isinstance(attr_value, String):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the attribute '{self.attr}' to be a "
                            f"'String', not a '{type(attr_value)}'.")

        return attr_value.contains(filter_value)


class ClientLike(Filter):

    def passes(self, to_filter: Any, filter_value: str) -> bool:
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

    def passes(self, to_filter: Any, filter_value: str) -> bool:
        if not hasattr(to_filter, self.attr):
            raise AttributeError(f"The filter '{self.name}: {type(self)}' expects a 'to_filter' argument that has the "
                                 f"attribute '{self.attr}'.")

        if not isinstance(filter_value, str):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the argument 'filter_value' to be a 'str'"
                            f", but received a '{type(filter_value)}'.")

        attr_value = getattr(to_filter, self.attr)
        if not isinstance(attr_value, String):
            raise TypeError(f"The filter '{self.name}: {type(self)}' expects the attribute '{self.attr}' to be a "
                            f"'String', not a '{type(attr_value)}'.")

        return attr_value == filter_value


class DateGreater(Filter):

    def passes(self, to_filter: Any, filter_value: date) -> bool:
        if not isinstance(filter_value, date):
            raise TypeError(f"The filter '{type(self)}' expects a 'filter_value' of type 'date', but received a "
                            f"'{type(filter_value)}'.")
        return to_filter >= filter_value


class DateLesser(Filter):

    def passes(self, to_filter: Any, filter_value: date) -> bool:
        if not isinstance(filter_value, date):
            raise TypeError(f"The filter '{type(self)}' expects a 'filter_value' of type 'date', but received a "
                            f"'{type(filter_value)}'.")
        return to_filter <= filter_value
