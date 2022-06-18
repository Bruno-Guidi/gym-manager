from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

ONE_MONTH_TD = timedelta(days=30)


def pay_day_passed(last_paid_on: date, today: date) -> bool:
    """The pay day passed if more than 30 days have passed since the payment date (inclusive).
    """
    return today - ONE_MONTH_TD >= last_paid_on


class ValidationError(Exception):

    def __init__(self, cause: str, *args: object) -> None:
        super().__init__(*args)
        self.cause = cause


class Validatable(abc.ABC):

    def __init__(self, value: Any, **validate_args):
        self._value = self.validate(value, **validate_args)

    def __str__(self) -> str:
        return str(self._value)

    def __eq__(self, o: Validatable) -> bool:
        return self._value == o._value

    def __hash__(self) -> int:
        return hash(self._value)

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

    def as_primitive(self) -> Any:
        return self._value


class Number(Validatable):

    def validate(self, value: str | int, **kwargs) -> int:
        """Validates the given *value*. If the validation succeeds, return the primitive that the Validatable
        implementation stores.

        Keyword Args:
            min_value: minimum valid value. If None, min_value will be -inf.
            max_value: maximum valid value. If None, max_value will be inf.

        Raises:
            ValidationError if the validation failed.
        """
        if not isinstance(value, (str, int)):
            raise ValidationError(f"The type '{type(value)}' is not valid for a number.")
        if isinstance(value, str) and not value.isnumeric():
            raise ValidationError(f"The str '{value}' is not numeric.")
        int_value = int(value)
        min_value = kwargs['min_value'] if 'min_value' in kwargs else float('-inf')
        max_value = kwargs['max_value'] if 'max_value' in kwargs else float('inf')
        if int_value < min_value or int_value >= max_value:
            raise ValidationError(f"The value '{value}' must be in the range [{min_value}, {max_value})")
        return int_value


class String(Validatable):

    def validate(self, value: str, **kwargs) -> str:
        """Validates the given *value*. If the validation succeeds, return the primitive that the Validatable
        implementation stores.

        Keyword Args:
            optional: True if the String may be empty, False otherwise. False by default.
            max_len: maximum amount of characters.

        Raises:
            KeyError if a kwarg is missing.
            ValidationError if the validation failed.
        """
        if 'max_len' not in kwargs:
            raise KeyError(f"The String.validate(args) method is missing the kwarg 'max_len'.")
        optional = False if 'optional' not in kwargs else kwargs['optional']

        if not optional and len(value) == 0:
            raise ValidationError(f"A non optional String cannot be empty.")
        if len(value) > kwargs['max_len']:
            raise ValidationError(f"A String cannot exceeds {kwargs['max_len']} characters.")
        return value


class Currency(Validatable):

    def validate(self, value: str, **kwargs) -> Any:
        if 'max_currency' not in kwargs:
            raise KeyError(f"The Currency.validate(args) method is missing the kwarg 'max_currency'.")

        try:
            value = Decimal(value)
        except InvalidOperation:
            raise ValidationError(f"The value '{value}' is not a valid currency.")
        if value >= kwargs['max_currency']:
            raise ValidationError(
                f"The currency '{value}' is not valid. It should be less than '{kwargs['max_currency']}'.")
        return value


class NotRegistered(KeyError):
    """Exception thrown when the *client* isn't registered in the *activity*.
    """
    def __init__(self, client: Client, activity_id: int, *args: object) -> None:
        super().__init__(*args)
        self.client = client
        self.activity_id = activity_id

    def __str__(self) -> str:
        return f"The client '{self.client.dni} - {self.client.name}' is not registered in the activity '{self.activity_id}'"


@dataclass
class Activity:
    """Stores general information about an activity.
    """
    id: int
    name: String
    price: Currency
    pay_once: bool
    description: String


class ActivityFilter(abc.ABC):

    def __init__(self, filter_value: Any) -> None:
        self.filter_value = filter_value

    @abc.abstractmethod
    def passes_filter(self, activity: Activity) -> bool:
        raise NotImplementedError


class NameFilter(ActivityFilter):

    def passes_filter(self, activity: Activity) -> bool:
        if not isinstance(self.filter_value, str):
            raise TypeError(f"NameFilter activity filter expects a 'str', but received a '{type(self.filter_value)}'")

        return self.filter_value in activity.name.as_primitive()


@dataclass
class Client:
    dni: Number
    name: String = field(compare=False)
    admission: date = field(compare=False)
    telephone: String = field(compare=False)
    direction: String = field(compare=False)
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


@dataclass
class Inscription:
    """Stores information about an activity inscription of a client.
    """
    client: Client
    activity: Activity
    transaction: Optional[Transaction] = None

    def first_pay_missing(self) -> bool:
        return self.transaction is None

    def pay_day_passed(self, today: date) -> bool:
        if self.transaction is None:
            return True
        return pay_day_passed(self.transaction.when.as_primitive(), today)

    def record_payment(self, payment: Transaction):
        """Records the payment of the activity.

        Raises:
            ValueError if *payment.client* is different from *self.client*.
        """
        if self.client != payment.client:
            raise ValueError(f"The client '{payment.client.name}' is paying the activity '{self.activity.name}' for "
                             f"the client '{self.client.name}'.")
        self.transaction = payment
