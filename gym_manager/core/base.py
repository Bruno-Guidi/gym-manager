from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Callable


logger = logging.getLogger(__name__)

ONE_MONTH_TD = timedelta(days=30)


def pay_day_passed(last_paid_on: date, today: date) -> bool:
    """The pay day passed if more than 30 days have passed since the payment date (inclusive).
    """
    return today - ONE_MONTH_TD >= last_paid_on


def invalid_sub_charge_date(subscription: Subscription, charge_date: date) -> bool:
    previous_charge = subscription.transaction
    return (charge_date < subscription.when  # The charging is being made after the subscription was made.
            # The charging is being made after the previous charge was made.
            or (previous_charge is not None and charge_date < previous_charge.when))


class OperationalError(Exception):
    """Exception raised when there is an error while doing a system operation.
    """
    def __init__(self, cause: str, **involved_things) -> None:
        super().__init__(cause)
        self.involved_things = involved_things


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


class Number(Validatable):
    """int wrapper that supports min and max optional values.
    """

    def __eq__(self, other: int | Number) -> bool:
        if isinstance(other, type(self._value)):
            logger.getChild(type(self).__name__).warning(f"Comparing '{repr(self)}' with '{repr(other)}'")

            return self._value == other
        if isinstance(other, type(self)):
            return self._value == other._value
        return NotImplemented

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
            raise ValidationError(
                f"The type of the argument 'value' must be an 'str' or 'int'. [type(value)={type(value)}]"
            )
        try:
            int_value = int(value)
        except ValueError:
            raise ValidationError(f"The argument 'value' is not a valid number. [value={value}]")
        min_value = kwargs['min_value'] if 'min_value' in kwargs else float('-inf')
        max_value = kwargs['max_value'] if 'max_value' in kwargs else float('inf')
        if int_value < min_value or int_value >= max_value:
            raise ValidationError(
                f"The argument 'value' must be in the range [{min_value}, {max_value}). [value={value}]"
            )
        return int_value


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

    def contains(self, substring: str | String) -> bool:
        if isinstance(substring, String):
            substring = substring.as_primitive()
        return substring.lower() in self._value.lower()


class Currency(Validatable):
    """Decimal wrapper that supports a max currency value.
    """

    def __eq__(self, other: Currency) -> bool:
        if isinstance(other, type(self)):
            return self._value == other.as_primitive()
        return NotImplemented

    def validate(self, value: str, **kwargs) -> Decimal:
        """Validates the given *value*. If the validation succeeds, returns the created Decimal object.

        Keyword Args:
            max_currency: maximum valid currency.

        Raises:
            KeyError if a kwarg is missing.
            ValidationError if the validation failed.
        """

        try:
            value = Decimal(value)
        except InvalidOperation:
            raise ValidationError(f"The argument 'value' is not a valid currency. [value={value}]")
        return value

    def increase(self, other_currency: Currency) -> None:
        self._value += other_currency.as_primitive()


@dataclass
class Client:
    """Stores information about a client.
    """

    dni: Number
    name: String = field(compare=False)
    admission: date = field(compare=False)
    telephone: String = field(compare=False)
    direction: String = field(compare=False)
    is_active: bool = field(compare=False)
    _subscriptions: dict[String, Subscription] = field(default_factory=dict, compare=False, init=False)

    def add(self, subscription: Subscription):
        """Registers the given *subscription*.
        """
        self._subscriptions[subscription.activity.name] = subscription

    def unsubscribe(self, activity: Activity):
        """Unsubscribes the client from the given *activity*.
        """
        self._subscriptions.pop(activity.name)

    def is_subscribed(self, activity: Activity) -> bool:
        """Returns True if the client subscribed to the *activity*.
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

    def register_charge(self, activity: Activity, transaction: Transaction):
        """Registers that the client was charged for the *activity* subscription.

        Raises:
            OperationalError if the client being charged is not the client that is subscribed.
        """
        if self != transaction.client:
            raise OperationalError("A client is being charged for an activity to which he is not subscribed.",
                                   charged_client=transaction.client, client_to_charge=self, activity=activity)
        self._subscriptions[activity.name].register_charge(transaction)


@dataclass
class Activity:
    """Stores general information about an activity.
    """

    name: String
    price: Currency = field(compare=False)
    charge_once: bool = field(compare=False)
    description: String = field(compare=False)
    locked: bool = False


@dataclass
class Subscription:
    """Stores information about a client's subscription in an activity.
    """

    when: date
    client: Client
    activity: Activity
    transaction: Transaction | None = None

    def charge_day_passed(self, today: date) -> bool:
        """Checks if the charge day for the subscription has passed.

        If *today* is 31 days after *self.transaction.when* (or *self.when*, if the client hasn't been charged for the
        activity after he signed up) then the charge day passed.
        """
        if self.transaction is None:
            # More than 30 days passed since the client signed up on the activity, so he should be charged.
            return pay_day_passed(self.when, today)
        return pay_day_passed(self.transaction.when, today)

    def register_charge(self, transaction: Transaction):
        """Updates the subscription with the given *transaction*.
        """
        self.transaction = transaction


@dataclass
class Transaction:
    """Stores information about a transaction.
    """

    id: int
    type: String
    when: date
    amount: Currency
    method: String
    responsible: String
    description: String
    client: Client | None = None


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

    def passes(self, to_filter: Any, filter_value: date) -> bool:
        """Returns True if the given *to_filter* date is less or equal to *filter_value*.
        """
        if not isinstance(filter_value, date):
            raise TypeError(f"The filter '{type(self)}' expects a 'filter_value' of type 'date', but received a "
                            f"'{type(filter_value)}'.")
        return to_filter <= filter_value
