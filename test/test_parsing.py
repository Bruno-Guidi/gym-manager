from gym_manager import peewee
from gym_manager.parsing import parse


def test_parse():
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    parse(activity_repo, client_repo, subscription_repo, r"E:\downloads\chrome_bruno-leisure\backup_dia_26.sql")

