from datetime import date
from typing import Iterable

import pytest

from gym_manager.core import api
from gym_manager.core.base import (
    String, Currency, Client, Number, Transaction,
    Subscription, discard_subscription, ValidationError)


def test_base_Number():
    number = Number("", optional=True)
    assert number.as_primitive() is None

    with pytest.raises(ValidationError):
        Number("")

    with pytest.raises(ValidationError):
        Number("      ")

    with pytest.raises(ValidationError):
        Number(str(Number.OPTIONAL_INT))

    with pytest.raises(ValidationError):
        Number(Number.OPTIONAL_INT)


# noinspection PyTypeChecker
def test_base_Subscription_upToDate():
    subscription = Subscription(date(2022, 8, 8), client=None, activity=None)

    # The client wasn't charged for the activity after he signed up. 06/09/2022 is the 30th day after the subscription
    # date, so the subscription is up-to-date.
    assert subscription.up_to_date(date(2022, 9, 6))

    # The client wasn't charged for the activity after he signed up. 07/09/2022 is the 31st day after the subscription
    # date, so the subscription isn't up-to-date.
    assert not subscription.up_to_date(date(2022, 9, 7))

    # The client is charged for the subscription.
    subscription.transaction = Transaction(1, type=None, client=None, when=date(2022, 9, 7), amount=None, method=None,
                                           responsible=None, description=None)

    assert subscription.up_to_date(date(2022, 9, 7))
    assert subscription.up_to_date(date(2022, 10, 6))  # Only 30 days have passed since the charge.
    assert not subscription.up_to_date(date(2022, 10, 7))  # 31 days have passed since the charge.


# noinspection PyTypeChecker
def test_base_Subscription_invalidChargeDate():
    subscription = Subscription(date(2022, 8, 8), client=None, activity=None)
    # The subscription wasn't paid yet.
    assert subscription.invalid_charge_date(date(2022, 8, 7))
    assert not subscription.invalid_charge_date(date(2022, 8, 8))

    # The subscription was already paid.
    subscription.transaction = Transaction(1, None, date(2022, 8, 10), None, None, None, None)
    assert subscription.invalid_charge_date(date(2022, 8, 9))
    assert not subscription.invalid_charge_date(date(2022, 8, 10))


def test_generateBalance():
    total = "Total"
    # Transaction types.
    trans_charge, trans_extract = "Cobro", "Extracción"
    # Transaction methods.
    trans_cash, trans_debit, trans_credit = "Efectivo", "Débito", "Crédito"

    # Utility function that creates a generator with some transactions.
    def transactions_gen() -> Iterable[Transaction]:
        # noinspection PyTypeChecker
        to_yield = [
            Transaction(4, trans_charge, date(2022, 6, 6), Currency("100.99"), trans_cash, None, None),
            Transaction(5, trans_charge, date(2022, 6, 6), Currency("100.0001"), trans_cash, None, None),
            Transaction(1, trans_charge, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
            Transaction(6, trans_charge, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
            Transaction(3, trans_extract, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
            Transaction(7, trans_extract, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
            Transaction(2, trans_extract, date(2022, 6, 6), Currency("0.0005"), trans_credit, None, None)
        ]
        for t in to_yield:
            yield t

    # Feature to test.
    balance, _ = api.generate_balance(transactions_gen())
    expected_balance = {
        trans_charge: {trans_cash: Currency("200.9901"), trans_debit: Currency("200"), total: Currency("400.9901")},
        trans_extract: {trans_cash: Currency("100"), trans_debit: Currency("100"), trans_credit: Currency("0.0005"),
                        total: Currency("200.0005")}
    }

    assert expected_balance == balance


def test_base_filterOverdue():
    assert discard_subscription(only_overdue=True, up_to_date=True)
    assert not discard_subscription(only_overdue=True, up_to_date=False)
    assert not discard_subscription(only_overdue=False, up_to_date=True)
    assert not discard_subscription(only_overdue=False, up_to_date=False)


def test_base_Client_age():
    client = Client(Number(1), String("dummy_name"), date(2022, 2, 2), date(1998, 12, 15),
                    String("dummy_tel"), String("dummy_descr"), is_active=True)

    assert client.age(reference_date=date(2022, 7, 11)) == 23

    client = Client(Number(1), String("dummy_name"), date(2022, 2, 2), date(1998, 7, 12),
                    String("dummy_tel"), String("dummy_descr"), is_active=True)

    assert client.age(reference_date=date(2022, 7, 11)) == 23

    client = Client(Number(1), String("dummy_name"), date(2022, 2, 2), date(1998, 7, 11),
                    String("dummy_tel"), String("dummy_descr"), is_active=True)

    assert client.age(reference_date=date(2022, 7, 11)) == 24

