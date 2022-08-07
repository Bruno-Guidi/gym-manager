from datetime import date

from gym_manager import peewee
from gym_manager.contact.peewee import SqliteContactRepo
from gym_manager.old_app_info import confirm_old_charge, OldChargesRepo
from gym_manager.parsing import parse, minus_n_months


def test_minusNMonths():
    date_ = date(2022, 1, 1)
    assert minus_n_months(date_, 1) == date(2021, 12, 1)

    date_ = date(2022, 8, 4)
    assert minus_n_months(date_, 1) == date(2022, 7, 1)

    date_ = date(2022, 12, 31)
    assert minus_n_months(date_, 1) == date(2022, 11, 1)


def test_parse():
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    balance_repo = peewee.SqliteBalanceRepo(transaction_repo)
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()
    contact_repo = SqliteContactRepo()

    parse(activity_repo, client_repo, subscription_repo, transaction_repo, balance_repo,
          since=date(2022, 1, 1), backup_path=r"E:\downloads\chrome_bruno-leisure\backup_dia_26.sql",
          contact_repo=contact_repo)

    # old_charge = [old_charge for old_charge in OldChargesRepo.all()][0]  # TODO Remove on corresponding PR
    #
    # confirm_old_charge(client_repo, transaction_repo, subscription_repo, old_charge)

