from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

import pytest

from gym_manager import peewee
from gym_manager.core.base import Client, Number, String, TextLike, Currency, Transaction
from gym_manager.core.system import ActivityManager, AccountingSystem, generate_balance

MAX_CURRENCY = Decimal("9999.99")


def test_allClients():
    peewee.create_database(":memory:")

    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    sub_repo = peewee.SqliteSubscriptionRepo()

    cli_a = Client(Number(1), String("TestCliA", max_len=20), date(2022, 5, 9), String("TelA", max_len=20),
                   String("DirA", max_len=20), is_active=True)
    client_repo.add(cli_a)

    cli_b = Client(Number(2), String("TestCliB", max_len=20), date(2022, 5, 15), String("TelB", max_len=20),
                   String("DirB", max_len=20), is_active=True)
    client_repo.add(cli_b)

    cli_c = Client(Number(3), String("TestCliC", max_len=20), date(2022, 6, 2), String("TelC", max_len=20),
                   String("DirC", max_len=20), is_active=True)
    client_repo.add(cli_c)

    assert [cli for cli in client_repo.all(page=1)] == [cli_a, cli_b, cli_c]


def test_allClients_withFilters():
    peewee.create_database(":memory:")

    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    sub_repo = peewee.SqliteSubscriptionRepo()

    cli_a = Client(Number(1), String("TestCliA", max_len=20), date(2022, 5, 9), String("TelA", max_len=20),
                   String("DirA", max_len=20), is_active=True)
    client_repo.add(cli_a)

    cli_b = Client(Number(2), String("TestCliB", max_len=20), date(2022, 5, 15), String("TelB", max_len=20),
                   String("DirB", max_len=20), is_active=True)
    client_repo.add(cli_b)

    cli_c = Client(Number(3), String("TestCliC", max_len=20), date(2022, 6, 2), String("TelC", max_len=20),
                   String("DirC", max_len=20), is_active=True)
    client_repo.add(cli_c)

    filters = {"filter1": (TextLike("dummy", "dummy", attr="dummy", translate_fun=peewee.client_name_like), "cli")}
    assert [cli_a, cli_b, cli_c] == [cli for cli in client_repo.all(page=1, **filters)]

    filters = {"filter1": (TextLike("dummy", "dummy", attr="dummy", translate_fun=peewee.client_name_like), "clic")}
    assert [cli_c] == [cli for cli in client_repo.all(page=1, **filters)]

    filters = {"filter1": (TextLike("dummy", "dummy", attr="dummy", translate_fun=peewee.client_name_like), "TeC")}
    assert [] == [cli for cli in client_repo.all(page=1, **filters)]


def test_allClients_paginated():
    peewee.create_database(":memory:")

    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    sub_repo = peewee.SqliteSubscriptionRepo()

    cli_a = Client(Number(1), String("TestCliA", max_len=20), date(2022, 5, 9), String("TelA", max_len=20),
                   String("DirA", max_len=20), is_active=True)
    client_repo.add(cli_a)

    cli_b = Client(Number(2), String("TestCliB", max_len=20), date(2022, 5, 15), String("TelB", max_len=20),
                   String("DirB", max_len=20), is_active=True)
    client_repo.add(cli_b)

    cli_c = Client(Number(3), String("TestCliC", max_len=20), date(2022, 6, 2), String("TelC", max_len=20),
                   String("DirC", max_len=20), is_active=True)
    client_repo.add(cli_c)

    # Clients are retrieved ordered by name, so TestCliC is not retrieved.
    assert [cli_a, cli_b] == [cli for cli in client_repo.all(page=1, page_len=2)]


def test_addClient_raisesKeyError_withActiveClient():
    peewee.create_database(":memory:")

    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    sub_repo = peewee.SqliteSubscriptionRepo()

    cli_c = Client(Number(3), String("TestCliC", max_len=20), date(2022, 6, 2), String("TelC", max_len=20),
                   String("DirC", max_len=20), is_active=True)
    client_repo.add(cli_c)

    with pytest.raises(KeyError):
        client_repo.add(cli_c)

    other_cli_c = Client(Number(3), String("TestOtherCliC", max_len=20), date(2022, 6, 2), String("TelC", max_len=20),
                         String("DirC", max_len=20), is_active=True)
    with pytest.raises(KeyError):
        client_repo.add(other_cli_c)


def test_addClient_withInactiveClient():
    peewee.create_database(":memory:")

    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo, cache_len=0)
    sub_repo = peewee.SqliteSubscriptionRepo()

    # This client is inactive. To make things easy, the client is created with is_active=False since the beginning.
    cli_c = Client(Number(3), String("TestCliC", max_len=20), date(2022, 6, 2), String("TelC", max_len=20),
                   String("DirC", max_len=20), is_active=False)
    client_repo.add(cli_c)
    assert not client_repo.is_active(cli_c.dni)

    # This simulates the "reactivation" of the client. We change the name to see if previous data is preserved or not.
    new_name = String("TestOtherCliC", max_len=20)
    other_cli_c = Client(Number(3), new_name, date(2022, 6, 2), String("TelC", max_len=20), String("DirC", max_len=20),
                         is_active=True)
    client_repo.add(other_cli_c)
    # Queries the client again, to see if the client data is updated.
    other_cli_c = client_repo.get(other_cli_c.dni)
    assert client_repo.is_active(other_cli_c.dni) and other_cli_c.name == new_name


def test_removeClient():
    peewee.create_database(":memory:")

    # System objects.
    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo, cache_len=0)
    sub_repo = peewee.SqliteSubscriptionRepo()
    activity_manager = ActivityManager(activity_repo, sub_repo)

    # Set up.
    act1 = activity_manager.create(String("Futbol", max_len=20), Currency("100.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))
    act2 = activity_manager.create(String("Futsal", max_len=20), Currency("200.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))
    act3 = activity_manager.create(String("Act1", max_len=20), Currency("300.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))

    # This client is inactive. To make things easy, the client is created with is_active=False since the beginning.
    cli_c = Client(Number(3), String("TestCliC", max_len=20), date(2022, 5, 2), String("TelC", max_len=20),
                   String("DirC", max_len=20), is_active=True)
    client_repo.add(cli_c)
    activity_manager.subscribe(date(2022, 5, 5), cli_c, act1)
    activity_manager.subscribe(date(2022, 5, 5), cli_c, act2)
    activity_manager.subscribe(date(2022, 5, 5), cli_c, act3)

    # First assert that the clients are correctly subscribed.
    assert (activity_manager.n_subscribers(act1) == 1 and activity_manager.n_subscribers(act2) == 1
            and activity_manager.n_subscribers(act3) == 1)

    # Then remove the client and assert that it is no longer active, and that the subscriptions where cancelled.
    client_repo.remove(cli_c)
    assert (not client_repo.is_active(cli_c.dni) and activity_manager.n_subscribers(act1) == 0
            and activity_manager.n_subscribers(act2) == 0 and activity_manager.n_subscribers(act3) == 0)


def test_allActivities():
    peewee.create_database(":memory:")

    activity_repo, transaction_repo = peewee.SqliteActivityRepo(cache_len=0), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    sub_repo = peewee.SqliteSubscriptionRepo()

    activity_manager = ActivityManager(activity_repo, sub_repo)

    act1 = activity_manager.create(String("Futbol", max_len=20), Currency("100.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))
    act2 = activity_manager.create(String("Futsal", max_len=20), Currency("200.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))
    act3 = activity_manager.create(String("Act1", max_len=20), Currency("300.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))

    assert [act for act in activity_manager.activities()] == [act1, act2, act3]

    filters = {"filter1": (TextLike("dummy", "dummy", attr="name"), "fut")}
    assert [act for act in activity_manager.activities(**filters)] == [act1, act2]


def test_removeActivity():
    peewee.create_database(":memory:")

    # System objects.
    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    sub_repo = peewee.SqliteSubscriptionRepo()

    activity_manager = ActivityManager(activity_repo, sub_repo)

    # Test setup.
    act1 = activity_manager.create(String("Futbol", max_len=20), Currency("100.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))

    cli = Client(Number(3), String("TestCli", max_len=20), date(2022, 6, 2), String("Tel", max_len=20),
                 String("Dir", max_len=20), is_active=True)
    client_repo.add(cli)
    activity_manager.subscribe(date(2022, 7, 9), cli, act1)

    # Feature to test.
    activity_manager.remove(act1)
    with pytest.raises(KeyError):
        activity_repo.get(act1.name)  # The activity is no longer in the repo.
        assert not cli.is_subscribed(act1)  # The client is no longer signed up in the nonexistent activity.


def test_cancelSubscription():
    peewee.create_database(":memory:")

    # System objects.
    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    sub_repo = peewee.SqliteSubscriptionRepo()

    activity_manager = ActivityManager(activity_repo, sub_repo)

    # Test setup.
    act1 = activity_manager.create(String("Futbol", max_len=20), Currency("100.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))

    cli = Client(Number(3), String("TestCli", max_len=20), date(2022, 6, 2), String("Tel", max_len=20),
                 String("Dir", max_len=20), is_active=True)
    client_repo.add(cli)
    sub = activity_manager.subscribe(date(2022, 7, 9), cli, act1)

    # Feature to test.
    activity_manager.cancel(sub)

    assert not cli.is_subscribed(act1) and activity_manager.n_subscribers(act1) == 0


def test_chargeActivity_onSubDate():
    peewee.create_database(":memory:")

    # System objects.
    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    transaction_repo.client_repo = client_repo
    sub_repo = peewee.SqliteSubscriptionRepo()
    balance_repo = None  # This repo is irrelevant to the current test.

    activity_manager = ActivityManager(activity_repo, sub_repo)
    # noinspection PyTypeChecker
    accounting_manager = AccountingSystem(transaction_repo, sub_repo, balance_repo, ("charge",), ("dummy_method",))

    # Test setup.
    act1 = activity_manager.create(String("Futbol", max_len=20), Currency("100.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))

    cli = Client(Number(3), String("TestCli", max_len=20), date(2022, 6, 2), String("Tel", max_len=20),
                 String("Dir", max_len=20), is_active=True)
    client_repo.add(cli)
    sub_date = date(2022, 7, 9)
    sub = activity_manager.subscribe(sub_date, cli, act1)

    # Feature to test.
    accounting_manager.charge(sub_date, cli, act1, String("dummy_method", max_len=20),
                              String("dummy_method", max_len=20), String("dummy_descr", max_len=20))
    assert not sub.charge_day_passed(sub_date) and sub.transaction.when == sub_date


def test_chargeActivity_after30DaysOfSub():
    peewee.create_database(":memory:")

    # System objects.
    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    transaction_repo.client_repo = client_repo
    sub_repo = peewee.SqliteSubscriptionRepo()
    balance_repo = None  # This repo is irrelevant to the current test.

    activity_manager = ActivityManager(activity_repo, sub_repo)
    # noinspection PyTypeChecker
    accounting_manager = AccountingSystem(transaction_repo, sub_repo, balance_repo, ("charge",), ("dummy_method",))

    # Test setup.
    act1 = activity_manager.create(String("Futbol", max_len=20), Currency("100.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))

    cli = Client(Number(3), String("TestCli", max_len=20), date(2022, 6, 2), String("Tel", max_len=20),
                 String("Dir", max_len=20), is_active=True)
    client_repo.add(cli)
    sub_date = date(2022, 7, 9)
    sub = activity_manager.subscribe(sub_date, cli, act1)

    # Feature to test.
    charge_day = sub_date + timedelta(days=30)
    accounting_manager.charge(charge_day, cli, act1, String("dummy_method", max_len=20),
                              String("dummy_method", max_len=20), String("dummy_descr", max_len=20))
    assert not sub.charge_day_passed(sub_date) and sub.transaction.when == charge_day


def test_chargeActivity_after60DaysOfSub():
    peewee.create_database(":memory:")

    # System objects.
    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    transaction_repo.client_repo = client_repo
    sub_repo = peewee.SqliteSubscriptionRepo()
    balance_repo = None  # This repo is irrelevant to the current test.

    activity_manager = ActivityManager(activity_repo, sub_repo)
    # noinspection PyTypeChecker
    accounting_manager = AccountingSystem(transaction_repo, sub_repo, balance_repo, ("charge",), ("dummy_method",))

    # Test setup.
    act1 = activity_manager.create(String("Futbol", max_len=20), Currency("100.00", max_currency=MAX_CURRENCY),
                                   charge_once=False, description=String("Descr", max_len=20))

    cli = Client(Number(3), String("TestCli", max_len=20), date(2022, 6, 2), String("Tel", max_len=20),
                 String("Dir", max_len=20), is_active=True)
    client_repo.add(cli)
    sub_date = date(2022, 7, 9)
    sub = activity_manager.subscribe(sub_date, cli, act1)

    # Feature to test.
    charge_day = sub_date + timedelta(days=60)
    accounting_manager.charge(charge_day, cli, act1, String("dummy_method", max_len=20),
                              String("dummy_method", max_len=20), String("dummy_descr", max_len=20))
    assert not sub.charge_day_passed(sub_date) and sub.transaction.when == charge_day


def test_chargeActivity_chargeOnceActivity():
    peewee.create_database(":memory:")

    # System objects.
    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    transaction_repo.client_repo = client_repo
    sub_repo = peewee.SqliteSubscriptionRepo()
    balance_repo = None  # This repo is irrelevant to the current test.

    activity_manager = ActivityManager(activity_repo, sub_repo)
    # noinspection PyTypeChecker
    accounting_manager = AccountingSystem(transaction_repo, sub_repo, balance_repo, ("charge",), ("dummy_method",))

    # Test setup.
    act1 = activity_manager.create(String("Futbol", max_len=20), Currency("100.00", max_currency=MAX_CURRENCY),
                                   charge_once=True, description=String("Descr", max_len=20))

    cli = Client(Number(3), String("TestCli", max_len=20), date(2022, 6, 2), String("Tel", max_len=20),
                 String("Dir", max_len=20), is_active=True)
    client_repo.add(cli)

    # Feature to test.
    accounting_manager.charge(date(2022, 6, 6), cli, act1, String("dummy_method", max_len=20),
                              String("dummy_method", max_len=20), String("dummy_descr", max_len=20))
    assert not cli.is_subscribed(act1)


def test_generateBalance():
    total = String("Total", max_len=10)
    # Transaction types.
    trans_charge, trans_extract = String("Charge", max_len=10), String("Extract", max_len=10)
    # Transaction methods.
    trans_cash, trans_debit = String("Cash", max_len=10), String("Debit", max_len=10)
    trans_credit = String("Credit", max_len=10)

    # Utility function that creates a generator with some transactions.
    def transactions_gen() -> Iterable[Transaction]:
        # noinspection PyTypeChecker
        to_yield = [
            Transaction(4, trans_charge, None, date(2022, 6, 6), Currency("100.99"), trans_cash, None, None),
            Transaction(5, trans_charge, None, date(2022, 6, 6), Currency("100.0001"), trans_cash, None, None),
            Transaction(1, trans_charge, None, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
            Transaction(6, trans_charge, None, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
            Transaction(3, trans_extract, None, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
            Transaction(7, trans_extract, None, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
            Transaction(2, trans_extract, None, date(2022, 6, 6), Currency("0.0005"), trans_credit, None, None)
        ]
        for t in to_yield:
            yield t

    # Feature to test.
    balance = generate_balance(transactions_gen(), (trans_charge, trans_extract),
                               (trans_cash, trans_debit, trans_credit))
    expected_balance = {
        trans_charge: {trans_cash: Currency("200.9901"), trans_debit: Currency("200"), trans_credit: Currency(0),
                       total: Currency("400.9901")},
        trans_extract: {trans_cash: Currency("100"), trans_debit: Currency("100"), trans_credit: Currency("0.0005"),
                        total: Currency("200.0005")}
    }

    assert expected_balance == balance
