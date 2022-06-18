from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

from gym_manager.core import attr_constraints

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
            optional: True if the String may be empty, False otherwise.
            max_len: maximum amount of characters.

        Raises:
            ValidationError if the validation failed.
        """
        if not kwargs['optional'] and len(value) == 0:
            raise ValidationError(f"A non optional String cannot be empty.")
        if len(value) > kwargs['max_len']:
            raise ValidationError(f"A String cannot exceeds {kwargs['max_len']} characters.")
        return value


class Date(Validatable):

    def validate(self, value: str | date, **kwargs) -> date:
        """Validates the given *value*. If the validation succeeds, return the primitive that the Validatable
        implementation stores.

        Keyword Args:
            format: iterable with date formats.

        Raises:
            ValidationError if the validation failed.
        """
        if isinstance(value, date):
            return value

        for format_ in kwargs['format']:
            try:
                return datetime.strptime(value, format_).date()
            except ValueError:
                pass
        raise ValidationError(f"None of the formats in '{kwargs['format']}' could be used to format the value '{value}'.")

    def __str__(self) -> str:
        return datetime.strftime(self._value, attr_constraints.DATE_FORMATS[0])


class Currency(Validatable):

    def validate(self, value: str, **kwargs) -> Any:
        try:
            value = Decimal(value)
        except InvalidOperation:
            raise ValidationError(f"The value '{value}' is not a valid currency.")
        if kwargs['positive'] and value <= 0:
            raise ValidationError(f"The currency '{value}' is not valid. It should be greater than zero.")
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
class Payment:
    id: int
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
    payment: Optional[Payment] = None

    def first_pay_missing(self) -> bool:
        return self.payment is None

    def pay_day_passed(self, today: date) -> bool:
        if self.payment is None:
            return True  # ToDo add inscription date and compare to it.
        return pay_day_passed(self.payment.when.as_primitive(), today)

    def record_payment(self, payment: Payment):
        """Records the payment of the activity.

        Raises:
            ValueError if *payment.client* is different from *self.client*.
        """
        if self.client != payment.client:
            raise ValueError(f"The client '{payment.client.name}' is paying the activity '{self.activity.name}' for "
                             f"the client '{self.client.name}'.")
        self.payment = payment
