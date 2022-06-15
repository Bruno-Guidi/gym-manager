from __future__ import annotations

import abc
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Any

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

    def __str__(self) -> str:
        return str(self._value)


class Number(Validatable):

    def validate(self, value: str | int, **kwargs) -> int:
        """Validates the given *value*. If the validation succeeds, return the primitive that the Validatable
        implementation stores.

        Keyword Args:
            min_value: minimum valid value.
            max_value: maximum valid value.

        Raises:
            ValidationError if the validation failed.
        """
        if not isinstance(value, (str, int)):
            raise ValidationError(f"The type '{type(value)}' is not valid for a number.")
        if isinstance(value, str) and not value.isnumeric():
            raise ValidationError(f"The str '{value}' is not numeric.")
        int_value = int(value)
        if int_value < kwargs['min_value'] or int_value >= kwargs['max_value']:
            raise ValidationError(f"The value '{value}' must be in the range [{kwargs['min_value']}, {kwargs['max_value']})")
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

    def validate(self, value: str, **kwargs) -> date:
        """Validates the given *value*. If the validation succeeds, return the primitive that the Validatable
        implementation stores.

        Keyword Args:
            format: iterable with date formats.

        Raises:
            ValidationError if the validation failed.
        """
        for format_ in kwargs['format']:
            try:
                return datetime.strptime(value, format_).date()
            except ValueError:
                pass
        raise ValidationError(f"None of the formats in '{kwargs['format']}' could be used to format the value '{value}'.")


class Currency:  # ToDo extend from Validatable.
    def __init__(self, raw_amount: str) -> None:
        self.amount = Decimal(raw_amount)

    def __str__(self) -> str:
        return str(self.amount)

    def __eq__(self, o: Currency) -> bool:
        return self.amount == o.amount


