from datetime import date
from typing import Iterable

import pytest

from gym_manager.core import api
from gym_manager.core.base import (
    String, Currency, Client, Number, Transaction,
    Subscription, discard_subscription, ValidationError, month_range)


def test_base_Number():
    number = Number("", optional=True)
    assert number.as_primitive() is None

    with pytest.raises(ValidationError):
        Number("", optional=False)

    with pytest.raises(ValidationError):
        Number("      ", optional=False)

    with pytest.raises(ValidationError):
        Number(str(Number.OPTIONAL_INT))

    with pytest.raises(ValidationError):
        Number(Number.OPTIONAL_INT)


# noinspection PyTypeChecker
def test_base_Subscription_isCharged():
    subscription = Subscription(date(2022, 8, 8), client=None, activity=None)

    assert (not subscription.is_charged(2022, 4) and not subscription.is_charged(2022, 5)
            and not subscription.is_charged(2022, 6))

    subscription.add_transaction(Transaction(1, None, date(2022, 4, 8), None, None, None, None))
    assert (subscription.is_charged(2022, 4) and not subscription.is_charged(2022, 5)
            and not subscription.is_charged(2022, 6))

    subscription.add_transaction(Transaction(1, None, date(2022, 6, 30), None, None, None, None))
    assert (subscription.is_charged(2022, 4) and not subscription.is_charged(2022, 5)
            and subscription.is_charged(2022, 6))


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


def test_base_monthRange():
    expected = [(12, 2021), (1, 2022), (2, 2022), (3, 2022), (4, 2022), (5, 2022), (6, 2022), (7, 2022), (8, 2022),
                (9, 2022), (10, 2022), (11, 2022), ]
    assert expected == [month_year for month_year in month_range(date(2021, 12, 1), date(2022, 12, 1))]

    expected = [(11, 2021), (12, 2021), (1, 2022), (2, 2022), (3, 2022), (4, 2022), (5, 2022), (6, 2022), (7, 2022),
                (8, 2022), (9, 2022), (10, 2022)]
    assert expected == [month_year for month_year in month_range(date(2021, 11, 1), date(2022, 11, 1))]

    assert [] == [month_year for month_year in month_range(date(2021, 11, 1), date(2021, 11, 1))]

