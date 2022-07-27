from datetime import date
from typing import Generator

from gym_manager.core.base import Activity, String, Transaction, Currency, Client, Number
from gym_manager.core.persistence import ActivityRepo, FilterValuePair, TransactionRepo
from gym_manager.core.security import log_responsible
from gym_manager.peewee import SqliteClientRepo, create_database, ClientTable
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

    def all(self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None) -> \
    Generator[Activity, None, None]:
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

    client = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"))

    client_repo.remove(client)
    assert not ClientTable.get_by_id(1).is_active


def test_ClientRepo_create_withNonExistingClient_withNoDni():
    create_database(":memory:")
    client_repo = SqliteClientRepo(MockActivityRepo(), MockTransactionRepo())

    expected = Client(1, String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"))
    result = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"))

    assert expected == result and ClientTable.get_by_id(1).is_active


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
    client_repo = SqliteClientRepo(MockActivityRepo(), MockTransactionRepo())

    result = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(1))

    # Removes the client so it is marked as inactive.
    client_repo.remove(result)
    assert not client_repo.is_active(Number(1)) and ClientTable.get_or_none(ClientTable.dni == 1) is not None

    # Creates again the client. It should be activated.
    result = client_repo.create(String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"),
                                Number(1))
    expected = Client(1, String("Name"), date(2022, 5, 5), date(2000, 5, 5), String("Tel"), String("Dir"), Number(1))

    assert expected == result and expected.dni == result.dni and ClientTable.get_by_id(1).is_active


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
