import functools
from datetime import date
from typing import Generator, Iterable

import pytest

from gym_manager import peewee
from gym_manager.core import api
from gym_manager.core.api import close_balance, generate_balance
from gym_manager.core.base import (
    Client, Number, String, Activity, Currency, Subscription, OperationalError,
    Transaction, InvalidDate)
from gym_manager.core.persistence import ClientView
from gym_manager.core.security import (
    SecurityHandler, log_responsible, Responsible, Action)


class MockSecurityHandler(SecurityHandler):

    @property
    def action_tags(self) -> Iterable[str]:
        yield from []

    def add_responsible(self, responsible: Responsible):
        pass

    @property
    def current_responsible(self) -> Responsible:
        return Responsible(String("DefaultResp"), String("DefaultCode"))

    def unregistered_action(self, action_tag: str) -> bool:
        return False

    def cant_perform_action(self, action_tag: str) -> bool:
        return False

    def handle_action(self, action_level: str, action_description: str):
        print(f"Ignoring {action_description}")

    def actions(self, page: int = 1, page_len: int = 20, tag: str | None = None) -> Iterable[Action]:
        pass


def test_subscribe():
    log_responsible.config(MockSecurityHandler())

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, peewee.SqliteTransactionRepo())
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Data setup.
    client = client_repo.create(String("dummy_name"), date(2022, 2, 1), date(2022, 2, 1), Number(""))

    activity = Activity(String("dummy_name"), Currency(0.0), String("dummy_descr"), charge_once=False)
    activity_repo.add(activity)

    # Feature being tested.
    api.subscribe(subscription_repo, date(2022, 2, 2), client, activity)
    assert activity_repo.n_subscribers(activity) == 1


def test_subscribe_activityChargeOnce_raisesOperationalError():
    log_responsible.config(MockSecurityHandler())

    client = Client(1, String("dummy_name"), date(2022, 2, 1), date(2022, 2, 1))
    activity = Activity(String("dummy_name"), Currency(0.0), String("dummy_descr"), charge_once=True, locked=True)
    with pytest.raises(OperationalError) as op_error:
        # noinspection PyTypeChecker
        api.subscribe(None, date(2022, 2, 2), client, activity)
    assert str(op_error.value) == ("Subscriptions to [activity=dummy_name] are not allowed because it is a "
                                   "'charge_once' activity.")


def test_subscribe_invalidClients_raisesOperationalError():
    log_responsible.config(MockSecurityHandler())

    client = Client(1, String("dummy_name"), date(2022, 2, 1), date(2022, 2, 1))
    other = Client(2, String("dummy_name"), date(2022, 2, 1), date(2022, 2, 1))
    activity = Activity(String("dummy_name"), Currency(0.0), String("dummy_descr"), charge_once=False, locked=True)
    # noinspection PyTypeChecker
    transaction = Transaction(1, type=None, when=None, amount=None, method=None, responsible=None, description=None,
                              client=client)

    with pytest.raises(OperationalError) as op_error:
        # noinspection PyTypeChecker
        api.subscribe(None, date(2022, 2, 2), other, activity, transaction)
    assert str(op_error.value) == "The subscribed [client.id=2] is not the charged [client.id=1]."

    # Swaps client's positions.
    # noinspection PyTypeChecker
    transaction = Transaction(1, type=None, when=None, amount=None, method=None, responsible=None, description=None,
                              client=other)
    with pytest.raises(OperationalError) as op_error:
        # noinspection PyTypeChecker
        api.subscribe(None, date(2022, 2, 2), client, activity, transaction)
    assert str(op_error.value) == "The subscribed [client.id=1] is not the charged [client.id=2]."


def test_subscribe_invalidSubscriptionDate_raisesInvalidDate():
    log_responsible.config(MockSecurityHandler())

    lesser, greater = date(2022, 2, 1), date(2022, 2, 2)

    client = Client(1, String("dummy_name"), greater, date(2022, 2, 1))
    activity = Activity(String("dummy_name"), Currency(0.0), String("dummy_descr"), charge_once=False, locked=True)
    with pytest.raises(InvalidDate):
        # noinspection PyTypeChecker
        api.subscribe(None, lesser, client, activity)


def test_cancel():
    log_responsible.config(MockSecurityHandler())

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Data setup.
    client = client_repo.create(String("dummy_name"), date(2022, 2, 1), date(2022, 2, 1), Number(""))

    activity = Activity(String("dummy_name"), Currency(0.0), String("dummy_descr"), charge_once=False)
    activity_repo.add(activity)

    subscription = Subscription(date(2022, 2, 2), client, activity)
    client.add(subscription)
    subscription_repo.add(subscription)

    # Feature being tested.
    api.cancel(subscription_repo, subscription)
    assert activity_repo.n_subscribers(activity) == 0


def test_charge_notChargeOnceActivity():
    log_responsible.config(MockSecurityHandler())

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    balance_repo = peewee.SqliteBalanceRepo(transaction_repo)
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Data setup.
    client = client_repo.create(String("dummy_name"), date(2022, 2, 1), date(2022, 2, 1), Number(""))

    activity = Activity(String("dummy_name"), Currency(0.0), String("dummy_descr"),
                        charge_once=False)
    activity_repo.add(activity)

    subscription = Subscription(date(2022, 2, 2), client, activity)
    client.add(subscription)
    subscription_repo.add(subscription)

    # This ensures that the activity is overdue.
    assert not subscription.is_charged(2022, 4)
    transaction = transaction_repo.create("Cobro", date(2022, 4, 1), Currency(0.0), "dummy_method",
                                          String("dummy_resp"), "dummy_descr", client)

    # Feature being tested.
    api.register_subscription_charge(subscription_repo, subscription, 2022, 4, transaction)
    # Check that the activity is up-to-date, because a charge was registered.
    assert subscription.is_charged(2022, 4)


def test_ClientViewRefreshedAfterClientUpdate():
    log_responsible.config(MockSecurityHandler())

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)

    # Creates a Client.
    client = client_repo.create(String("CliName"), date(2000, 2, 2), date(2022, 1, 1), Number(""))
    first_id = client.id

    # Then creates a Transaction related to the client. The transaction has a ClientView instead of a Client.
    transaction = transaction_repo.from_data(0, "type", date(2022, 2, 2), "100.00", "method", "resp", "descr",
                                             ClientView(1, String("CliName"), "created_by", Number("")))

    # Updates the Client.
    client.name = String("OtherName")
    client_repo.update(client)

    # Assert that the ClientView in the Transaction was updated.
    assert first_id == client.id and transaction.client.name == client.name


def test_ClientViewRefreshedAfterClientCreation():
    log_responsible.config(MockSecurityHandler())

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Creates a Client.
    client = client_repo.create(String("CliName"), date(2000, 2, 2), date(2022, 1, 1), Number(1))
    first_id = client.id

    # Removes a Client. It is marked as inactive.
    client_repo.remove(client)

    # Then creates a Transaction related to the client. The transaction has a ClientView of an inactive Client.
    transaction = transaction_repo.from_data(0, "type", date(2022, 2, 2), "100.00", "method", "resp", "descr",
                                             ClientView(1, String("CliName"), "", Number(1)))

    # Creates the Client again. It has the same dni, but a different name.
    client = client_repo.create(String("OtherName"), date(2000, 2, 2), date(2022, 1, 1), Number(1))

    # Assert that the ClientView in the Transaction was updated.
    assert first_id == client.id and transaction.client.name == client.name


def test_closeBalance():
    log_responsible.config(MockSecurityHandler())

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    balance_repo = peewee.SqliteBalanceRepo(transaction_repo)
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # The following transactions should be included in the daily balance of 04/05/2022.
    transaction_repo.create("Extracción", date(2022, 5, 4), Currency(100), "Efectivo", String("TestResp"),
                            "TestDescr")
    transaction_repo.create("Extracción", date(2022, 5, 4), Currency(100), "Efectivo", String("TestResp"),
                            "TestDescr")

    balance, transactions = generate_balance(transaction_repo.all())
    # First assert that the balance generated is the expected balance.
    assert balance == {"Cobro": {"Total": Currency(0)},
                       "Extracción": {"Efectivo": Currency(200), "Total": Currency(200)}}
    close_balance(transaction_repo, balance_repo, balance, transactions, date(2022, 5, 4), String("TestResp"))
    # Then assert that all transactions included in the balance have their balance_date correctly set.
    assert transactions == [t for t in transaction_repo.all(without_balance=False, balance_date=date(2022, 5, 4))]

    # Now we are generating and closing the balance of 05/05/2022.
    # This transaction was made after the previous daily balance was closed, so it should be included in the balance of
    # 05/05/2022.
    transaction_repo.create("Extracción", date(2022, 5, 4), Currency(100), "Efectivo", String("TestResp"),
                            "TestDescr")
    # The following transactions were made on 05/05/2022.
    transaction_repo.create("Extracción", date(2022, 5, 5), Currency(150), "Efectivo", String("TestResp"),
                            "TestDescr")
    transaction_repo.create("Extracción", date(2022, 5, 5), Currency(350), "Efectivo", String("TestResp"),
                            "TestDescr")
    transaction_repo.create("Extracción", date(2022, 5, 5), Currency(150), "Efectivo", String("TestResp"),
                            "TestDescr")
    transaction_repo.create("Extracción", date(2022, 5, 5), Currency(350), "Efectivo", String("TestResp"),
                            "TestDescr")

    balance, transactions = generate_balance(transaction_repo.all())
    # Assert that the balance generated is the expected balance.
    assert balance == {"Cobro": {"Total": Currency(0)},
                       "Extracción": {"Efectivo": Currency(1100), "Total": Currency(1100)}}
    close_balance(transaction_repo, balance_repo, balance, transactions, date(2022, 5, 5), String("TestResp"))
    # Then assert that all transactions included in the balance have their balance_date correctly set.
    assert transactions == [t for t in transaction_repo.all(without_balance=False, balance_date=date(2022, 5, 5))]


def test_closeBalance_withNoTransactions():
    log_responsible.config(MockSecurityHandler())

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    balance_repo = peewee.SqliteBalanceRepo(transaction_repo)
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    balance, _ = generate_balance(transaction_repo.all())
    # First assert that the balance generated is the expected balance.
    assert balance == {"Cobro": {"Total": Currency(0)}, "Extracción": {"Total": Currency(0)}}
    close_balance(transaction_repo, balance_repo, balance, [], date(2022, 5, 4), String("TestResp"))
    assert balance == [b for _, _, b, _ in balance_repo.all(date(2022, 4, 4), date(2022, 6, 4))][0]


def _create_extraction_fn(transaction_repo: peewee.SqliteTransactionRepo, when: date) -> Transaction:
    return transaction_repo.create("Extracción", when, Currency(100), "Débito", String("TestResp"),
                                   "TestDescr")


def test_closeBalance_withCreateExtractionFn():
    """This test case is the same as the previous one, but a function to create an "end of day" extraction is provided.
    """
    log_responsible.config(MockSecurityHandler())

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    balance_repo = peewee.SqliteBalanceRepo(transaction_repo)
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # The following transactions should be included in the daily balance of 04/05/2022.
    transaction_repo.create("Extracción", date(2022, 5, 4), Currency(100), "Efectivo", String("TestResp"),
                            "TestDescr")
    transaction_repo.create("Extracción", date(2022, 5, 4), Currency(100), "Efectivo", String("TestResp"),
                            "TestDescr")

    balance, transactions = generate_balance(transaction_repo.all())
    close_balance(transaction_repo, balance_repo, balance, transactions, date(2022, 5, 4), String("TestResp"),
                  functools.partial(_create_extraction_fn, transaction_repo, date(2022, 5, 4)))
    # First assert that the balance generated is the expected balance.
    assert balance == {"Cobro": {"Total": Currency(0)},
                       "Extracción": {"Efectivo": Currency(200), "Débito": Currency(100), "Total": Currency(300)}}
    # Then assert that all transactions included in the balance have their balance_date correctly set.
    assert transactions == [t for t in transaction_repo.all(without_balance=False, balance_date=date(2022, 5, 4))]

    # We are generating and closing the balance of 05/05/2022.
    # This transaction was made after the previous daily balance was closed, so it should be included in the balance of
    # 05/05/2022.
    transaction_repo.create("Extracción", date(2022, 5, 4), Currency(100), "Efectivo", String("TestResp"),
                            "TestDescr")
    # The following transactions were made on 05/05/2022.
    transaction_repo.create("Extracción", date(2022, 5, 5), Currency(150), "Efectivo", String("TestResp"),
                            "TestDescr")
    transaction_repo.create("Extracción", date(2022, 5, 5), Currency(350), "Efectivo", String("TestResp"),
                            "TestDescr")
    transaction_repo.create("Extracción", date(2022, 5, 5), Currency(150), "Efectivo", String("TestResp"),
                            "TestDescr")
    transaction_repo.create("Extracción", date(2022, 5, 5), Currency(350), "Efectivo", String("TestResp"),
                            "TestDescr")

    balance, transactions = generate_balance(transaction_repo.all())
    close_balance(transaction_repo, balance_repo, balance, transactions, date(2022, 5, 5), String("TestResp"),
                  functools.partial(_create_extraction_fn, transaction_repo, date(2022, 5, 5)))
    # Assert that the balance generated is the expected balance.
    assert balance == {"Cobro": {"Total": Currency(0)},
                       "Extracción": {"Efectivo": Currency(1100), "Débito": Currency(100), "Total": Currency(1200)}}
    # Then assert that all transactions included in the balance have their balance_date correctly set.
    assert transactions == [t for t in transaction_repo.all(without_balance=False, balance_date=date(2022, 5, 5))]
