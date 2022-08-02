from datetime import date

from gym_manager.contact.core import create_contact, update_contact, all_contacts
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


def test_create_unlinkedContact():
    create_database(":memory:")
    contact_repo = SqliteContactRepo()

    result = create_contact(contact_repo, String("n"), String("tel1"), String("tel2"), String("dir"), String("descr"), )

    assert (result.id == 1 and result.name == String("n") and result.tel1 == String("tel1")
            and result.tel2 == String("tel2") and result.direction == String("dir")
            and result.description == String("descr"))


def test_update_clientContact():
    create_database(":memory:")
    client_repo = SqliteClientRepo(MockActivityRepo(), MockTransactionRepo())
    contact_repo = SqliteContactRepo()

    client = client_repo.create(String("name"), date(2022, 2, 2), date(2000, 2, 2), String("tel"), String("dir"),
                                Number(1))

    contact = create_contact(contact_repo, String(""), String("tel1"), String("tel2"), String("dir"), String("descr"),
                             client)

    update_contact(contact_repo, contact, String(""), String("ntel1"), String("ntel2"), String("ndir"),
                   String("ndescr"))

    contact = [c for c in all_contacts(contact_repo)][0]

    assert (contact.id == 1 and contact.name == client.name and contact.tel1 == String("ntel1")
            and contact.tel2 == String("ntel2") and contact.direction == String("ndir")
            and contact.description == String("ndescr"))


def test_update_unlinkedContact():
    create_database(":memory:")
    contact_repo = SqliteContactRepo()

    contact = create_contact(contact_repo, String("n"), String("tel1"), String("tel2"), String("dir"), String("descr"))

    update_contact(contact_repo, contact, String("nn"), String("ntel1"), String("ntel2"), String("ndir"),
                   String("ndescr"))

    contact = [c for c in all_contacts(contact_repo)][0]

    assert (contact.id == 1 and contact.name == String("nn") and contact.tel1 == String("ntel1")
            and contact.tel2 == String("ntel2") and contact.direction == String("ndir")
            and contact.description == String("ndescr"))
