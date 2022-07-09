from datetime import date

import pytest

from gym_manager import peewee
from gym_manager.core import system
from gym_manager.core.base import (
    Activity, String, Currency, OperationalError, Client, Number, Transaction,
    Subscription)
from gym_manager.core.persistence import PersistenceError
from gym_manager.core.system import InvalidDate


def test_persistence_removeActivity_lockedActivity_raisesPersistenceError():
    peewee.create_database(":memory:")

    repo = peewee.SqliteActivityRepo()
    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), description=String("dummy_descr", max_len=20),
                        charge_once=True, locked=True)
    repo.add(activity)
    with pytest.raises(PersistenceError) as p_err:
        repo.remove(activity)
    assert str(p_err.value) == "The [activity=dummy_name] cannot be removed because its locked."


def test_subscribe_activityChargeOnce_raisesOperationalError():
    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), String("dummy_tel", max_len=20),
                    String("dummy_descr", max_len=20), is_active=True)
    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), description=String("dummy_descr", max_len=20),
                        charge_once=True, locked=True)
    with pytest.raises(OperationalError) as op_error:
        # noinspection PyTypeChecker
        system.subscribe(subscription_repo=None, when=date(2022, 2, 2), client=client, activity=activity)
    assert str(op_error.value) == ("Subscriptions to [activity=dummy_name] are not allowed because it is a "
                                   "'charge_once' activity.")


def test_subscribe_invalidClients_raisesOperationalError():
    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), String("dummy_tel", max_len=20),
                    String("dummy_descr", max_len=20), is_active=True)
    other = Client(Number(2), String("dummy_name", max_len=20), date(2022, 2, 1), String("dummy_tel", max_len=20),
                   String("dummy_descr", max_len=20), is_active=True)
    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), description=String("dummy_descr", max_len=20),
                        charge_once=False, locked=True)
    # noinspection PyTypeChecker
    transaction = Transaction(1, type=None, when=None, amount=None, method=None, responsible=None, description=None,
                              client=client)

    with pytest.raises(OperationalError) as op_error:
        # noinspection PyTypeChecker
        system.subscribe(subscription_repo=None, when=date(2022, 2, 2), client=other, activity=activity,
                         transaction=transaction)
    assert str(op_error.value) == "The subscribed [client=2] is not the charged [client=1]."

    # Swaps client's positions.
    # noinspection PyTypeChecker
    transaction = Transaction(1, type=None, when=None, amount=None, method=None, responsible=None, description=None,
                              client=other)
    with pytest.raises(OperationalError) as op_error:
        # noinspection PyTypeChecker
        system.subscribe(subscription_repo=None, when=date(2022, 2, 2), client=client, activity=activity,
                         transaction=transaction)
    assert str(op_error.value) == "The subscribed [client=1] is not the charged [client=2]."


def test_subscribe_invalidSubscriptionDate_raisesInvalidDate():
    lesser, greater = date(2022, 2, 1), date(2022, 2, 2)

    client = Client(Number(1), String("dummy_name", max_len=20), greater, String("dummy_tel", max_len=20),
                    String("dummy_descr", max_len=20), is_active=True)
    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), description=String("dummy_descr", max_len=20),
                        charge_once=False, locked=True)
    with pytest.raises(InvalidDate):
        # noinspection PyTypeChecker
        system.subscribe(subscription_repo=None, when=lesser, client=client, activity=activity)


# noinspection PyTypeChecker
def test_base_Subscription_payDayPassed():
    subscription = Subscription(date(2022, 8, 8), client=None, activity=None)

    # The client wasn't charged for the activity after he signed up. 06/09/2022 is the 30th day after the subscription
    # date, so the subscription is up-to-date.
    assert subscription.up_to_date(date(2022, 9, 6))

    # The client wasn't charged for the activity after he signed up. 07/09/2022 is the 31st day after the subscription
    # date, so the subscription isn't up-to-date.
    assert not subscription.up_to_date(date(2022, 9, 7))

    # The client is charged for the subscription.
    subscription.transaction = Transaction(1, type=None, client=None, when=date(2022, 9, 7), amount=None, method=None,
                                           responsible=None, description=None)

    assert subscription.up_to_date(date(2022, 9, 7))
    assert subscription.up_to_date(date(2022, 10, 6))  # Only 30 days have passed since the charge.
    assert not subscription.up_to_date(date(2022, 10, 7))  # 31 days have passed since the charge.
