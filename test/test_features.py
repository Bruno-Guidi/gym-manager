from datetime import date
from decimal import Decimal

from gym_manager import peewee
from gym_manager.core.base import Client, Number, String, TextLike

MAX_CURRENCY = Decimal("9999.99")


def test_allClients():
    peewee.create_database(":memory:")

    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    inscription_repo = peewee.SqliteInscriptionRepo()

    cli_a = Client(Number(1), String("TestCliA", max_len=20), date(2022, 5, 9), String("TelA", max_len=20),
                   String("DirA", max_len=20), is_active=True)
    client_repo.add(cli_a)

    cli_b = Client(Number(2), String("TestCliB", max_len=20), date(2022, 5, 15), String("TelB", max_len=20),
                   String("DirB", max_len=20), is_active=True)
    client_repo.add(cli_b)

    cli_c = Client(Number(3), String("TestCliC", max_len=20), date(2022, 6, 2), String("TelC", max_len=20),
                   String("DirC", max_len=20), is_active=True)
    client_repo.add(cli_c)

    assert [cli_a, cli_b, cli_c] == [cli for cli in client_repo.all(page=1)]


def test_allClients_withFilters():
    peewee.create_database(":memory:")

    activity_repo, transaction_repo = peewee.SqliteActivityRepo(), peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    inscription_repo = peewee.SqliteInscriptionRepo()

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
    inscription_repo = peewee.SqliteInscriptionRepo()

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
