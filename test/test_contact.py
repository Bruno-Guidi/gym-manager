from datetime import date

from gym_manager.contact.core import create_contact, Contact
from gym_manager.contact.peewee import SqliteContactRepo
from gym_manager.core.base import String, Number
from gym_manager.peewee import SqliteClientRepo, create_database
from test.test_peewee_repos import MockActivityRepo, MockTransactionRepo


def test_create_clientContact():
    create_database(":memory:")
    client_repo = SqliteClientRepo(MockActivityRepo(), MockTransactionRepo())
    contact_repo = SqliteContactRepo()

    client = client_repo.create(String("name"), date(2022, 2, 2), date(2000, 2, 2), String("tel"), String("dir"),
                                Number(1))

    result = create_contact(contact_repo, String(""), String("tel1"), String("tel2"), String("dir"), String("descr"),
                            client)

    assert (result.id == 1 and result.name == client.name and result.tel1 == String("tel1")
            and result.tel2 == String("tel2") and result.direction == String("dir")
            and result.description == String("descr"))
