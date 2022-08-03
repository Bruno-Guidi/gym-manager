from datetime import date

from gym_manager import peewee
from gym_manager.contact.peewee import SqliteContactRepo
from gym_manager.parsing import parse


def test_parse():
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    balance_repo = peewee.SqliteBalanceRepo(transaction_repo)
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()
    contact_repo = SqliteContactRepo()

    parse(activity_repo, client_repo, subscription_repo, transaction_repo,
          since=date(2022, 7, 25), backup_path=r"E:\downloads\chrome_bruno-leisure\backup_dia_26.sql",
          contact_repo=contact_repo)

