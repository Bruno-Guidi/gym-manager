from datetime import date
from typing import Generator

import pytest

from gym_manager.core.base import Activity, String, Transaction, Currency, Client, Number, Subscription
from gym_manager.core.persistence import ActivityRepo, FilterValuePair, TransactionRepo, PersistenceError
from gym_manager.core.security import log_responsible
from gym_manager.peewee import (
    SqliteClientRepo, create_database, ClientTable, SqliteActivityRepo,
    SqliteTransactionRepo, SqliteSubscriptionRepo, TransactionTable, SqliteBalanceRepo)
from test.test_core_api import MockSecurityHandler


class MockActivityRepo(ActivityRepo):

    def add(self, activity: Activity):
        pass

    def exists(self, name: String) -> bool:
        pass

    def get(self, name: String) -> Activity:
        pass

    def remove(self, activity: Activity):
        pass

    def update(self, activity: Activity):
        pass

    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[Activity, None, None]:
        pass

    def n_subscribers(self, activity: Activity) -> int:
        pass

    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        pass


class MockTransactionRepo(TransactionRepo):

    def from_data(
            self, id_: int, type_: str | None = None, when: date | None = None, raw_amount: str | None = None,
            method: str | None = None, raw_responsible: str | None = None, description: str | None = None,
            client: Client | None = None, balance_date: date | None = None
    ) -> Transaction:
        pass

    def create(
            self, type: str, when: date, amount: Currency, method: str, responsible: String, description: str,
            client: Client | None = None
    ) -> Transaction:
        pass

    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None,
            without_balance: bool = True, balance_date: date | None = None
    ) -> Generator[Transaction, None, None]:
        pass

    def bind_to_balance(self, transaction: Transaction, balance_date: date):
        pass


def test_ClientRepo_remove():
    create_database(":memory:")
    log_responsible.config(MockSecurityHandler())
    client_repo = SqliteClientRepo(MockActivityRepo(), MockTransactionRepo())

    client = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(""))

    client_repo.remove(client)
    assert not ClientTable.get_by_id(1).is_active


def test_ClientRepo_remove_withSubs():
    create_database(":memory:")
    log_responsible.config(MockSecurityHandler())
    activity_repo = SqliteActivityRepo()
    client_repo = SqliteClientRepo(activity_repo, SqliteTransactionRepo())
    subscription_repo = SqliteSubscriptionRepo()

    client = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(""))

    activity = Activity(String("Act"), Currency(100), String("Descr"))
    activity_repo.add(activity)

    subscription_repo.add(Subscription(date(2022, 5, 5), client, activity))
    assert activity_repo.n_subscribers(activity) == 1

    client_repo.remove(client)
    assert not ClientTable.get_by_id(1).is_active and activity_repo.n_subscribers(activity) == 0


def test_ClientRepo_create_withNonExistingClient_withNoDni():
    create_database(":memory:")
    client_repo = SqliteClientRepo(MockActivityRepo(), MockTransactionRepo())

    expected = Client(1, String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"))
    result = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(""))

    assert expected == result and ClientTable.get_by_id(1).is_active and result.dni.as_primitive() is None


def test_ClientRepo_create_withNonExistingClient_withDni():
    create_database(":memory:")
    log_responsible.config(MockSecurityHandler())
    client_repo = SqliteClientRepo(MockActivityRepo(), MockTransactionRepo())

    expected = Client(1, String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"), Number(1))
    result = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(1))

    assert expected == result and expected.dni == result.dni and ClientTable.get_by_id(1).is_active


def test_ClientRepo_create_withInactiveClient_withDni():
    create_database(":memory:")
    log_responsible.config(MockSecurityHandler())
    transaction_repo = SqliteTransactionRepo()
    SqliteBalanceRepo(transaction_repo)  # Required to create the BalanceTable.
    SqliteSubscriptionRepo()  # Required to create the SubscriptionTable.
    client_repo = SqliteClientRepo(SqliteActivityRepo(), transaction_repo)

    client = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(1))
    # Creates some transactions, to see if they are preserved after removing and creating again the client.
    transaction_repo.create("type", date(2022, 2, 2), Currency(1), "method", String("Resp"), "descr", client)
    transaction_repo.create("type", date(2022, 2, 2), Currency(1), "method", String("Resp"), "descr", client)

    # Removes the client so it is marked as inactive.
    client_repo.remove(client)
    assert (not client_repo.is_active(Number(1)) and ClientTable.get_or_none(ClientTable.dni == 1) is not None
            and TransactionTable.select().count() == 2)  # Test that the transactions are preserved in the table.

    # Creates again the client. It should be activated.
    client = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(1))
    expected = Client(1, String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"), Number(1))

    assert (expected == client and expected.dni == client.dni and ClientTable.get_by_id(1).is_active
            and TransactionTable.select().where(TransactionTable.client_id == client.id).count() == 2)


def test_ClientRepo_update():
    create_database(":memory:")
    client_repo = SqliteClientRepo(MockActivityRepo(), MockTransactionRepo())

    client = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(1))

    client.name = String("OtherName")
    client.telephone = String("OtherTel")
    client.direction = String("OtherDir")

    client_repo.update(client)

    record = ClientTable.get_by_id(1)
    assert (record.cli_name == client.name.as_primitive() and record.telephone == client.telephone.as_primitive()
            and record.direction == client.direction.as_primitive())


def test_ClientRepo_update_withSubs():
    create_database(":memory:")
    activity_repo = SqliteActivityRepo()
    transaction_repo = SqliteTransactionRepo()
    client_repo = SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = SqliteSubscriptionRepo()

    client = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(1))
    client.name = String("OtherName")
    client.telephone = String("OtherTel")
    client.direction = String("OtherDir")

    activity = Activity(String("Act"), Currency(1), String("Descr"))
    activity_repo.add(activity)
    subscription_repo.add(Subscription(date(2022, 2, 2), client, activity))
    assert activity_repo.n_subscribers(activity) == 1  # Asserts that the subscription was registered.

    client_repo.update(client)

    record = ClientTable.get_by_id(1)
    assert (record.cli_name == client.name.as_primitive() and record.telephone == client.telephone.as_primitive()
            and record.direction == client.direction.as_primitive())  # Asserts that the client was updated.
    assert activity_repo.n_subscribers(activity) == 1  # Asserts that the subscription wasn't deleted.


def test_ClientRepo_all():
    create_database(":memory:")
    log_responsible.config(MockSecurityHandler())
    # Because client querying also queries subscriptions and transactions associated to them, mock repositories can't be
    # used.
    client_repo = SqliteClientRepo(SqliteActivityRepo(), SqliteTransactionRepo())

    cli1 = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                              Number(1))
    cli2 = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                              Number(2))
    cli3 = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                              Number(3))

    # All clients are active.
    assert [cli1, cli2, cli3] == [client for client in client_repo.all()]

    # Only the second client is active.
    client_repo.remove(cli1)
    client_repo.remove(cli3)
    assert [cli2] == [client for client in client_repo.all()]


def test_persistence_removeActivity_lockedActivity_raisesPersistenceError():
    log_responsible.config(MockSecurityHandler())

    create_database(":memory:")

    repo = SqliteActivityRepo()
    activity = Activity(String("dummy_name"), Currency(0.0), String("dummy_descr"), charge_once=True, locked=True)
    repo.add(activity)
    with pytest.raises(PersistenceError) as p_err:
        repo.remove(activity)
    assert str(p_err.value) == "The [activity.name=dummy_name] cannot be removed because its locked."

