from datetime import date

from gym_manager import peewee
from gym_manager.core import system
from gym_manager.core.base import Client, Number, String, Activity, Currency


def test_subscribe():
    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Data setup.
    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), String("dummy_tel", max_len=20),
                    String("dummy_descr", max_len=20), is_active=True)
    client_repo.add(client)

    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), description=String("dummy_descr", max_len=20),
                        charge_once=False)
    activity_repo.add(activity)

    # Feature being tested.
    system.subscribe(subscription_repo, date(2022, 2, 2), client, activity)
    assert activity_repo.n_subscribers(activity) == 1
