import functools
from datetime import date

import pytest

from gym_manager import peewee
from gym_manager.core import api
from gym_manager.core.base import (
    Client, Number, String, Activity, Currency, Subscription, OperationalError,
    Transaction, InvalidDate)
from gym_manager.core.security import SecurityHandler, log_responsible, SimpleSecurityHandler, SecurityError


class MockSecurityHandler(SecurityHandler):

    @property
    def current_responsible(self) -> String:
        return String("DefaultResp", max_len=30)

    def unregister_action(self, action_tag: str) -> bool:
        return False

    def cant_perform_action(self, action_tag: str) -> bool:
        return False

    def handle_action(self, action_level: str, action_name: str):
        print(f"Ignoring {action_name}")


def test_subscribe():
    log_responsible.config(SimpleSecurityHandler(action_tags={"subscribe"}, needs_responsible={"subscribe"}))

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Data setup.
    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), date(2022, 2, 1),
                    String("dummy_tel", max_len=20), String("dummy_descr", max_len=20), is_active=True)
    client_repo.add(client)

    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), String("dummy_descr", max_len=20),
                        charge_once=False)
    activity_repo.add(activity)

    # Feature being tested.
    log_responsible.handler.current_responsible = String("TestResp", max_len=30)
    api.subscribe(subscription_repo, date(2022, 2, 2), client, activity)
    assert activity_repo.n_subscribers(activity) == 1


def test_subscribe_activityChargeOnce_raisesOperationalError():
    log_responsible.config(MockSecurityHandler())

    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), date(2022, 2, 1),
                    String("dummy_tel", max_len=20), String("dummy_descr", max_len=20), is_active=True)
    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), String("dummy_descr", max_len=20),
                        charge_once=True, locked=True)
    with pytest.raises(OperationalError) as op_error:
        # noinspection PyTypeChecker
        api.subscribe(None, date(2022, 2, 2), client, activity)
    assert str(op_error.value) == ("Subscriptions to [activity=dummy_name] are not allowed because it is a "
                                   "'charge_once' activity.")


def test_subscribe_invalidClients_raisesOperationalError():
    log_responsible.config(MockSecurityHandler())

    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), date(2022, 2, 1),
                    String("dummy_tel", max_len=20), String("dummy_descr", max_len=20), is_active=True)
    other = Client(Number(2), String("dummy_name", max_len=20), date(2022, 2, 1), date(2022, 2, 1),
                   String("dummy_tel", max_len=20), String("dummy_descr", max_len=20), is_active=True)
    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), String("dummy_descr", max_len=20),
                        charge_once=False, locked=True)
    # noinspection PyTypeChecker
    transaction = Transaction(1, type=None, when=None, amount=None, method=None, responsible=None, description=None,
                              client=client)

    with pytest.raises(OperationalError) as op_error:
        # noinspection PyTypeChecker
        api.subscribe(None, date(2022, 2, 2), other, activity, transaction)
    assert str(op_error.value) == "The subscribed [client=2] is not the charged [client=1]."

    # Swaps client's positions.
    # noinspection PyTypeChecker
    transaction = Transaction(1, type=None, when=None, amount=None, method=None, responsible=None, description=None,
                              client=other)
    with pytest.raises(OperationalError) as op_error:
        # noinspection PyTypeChecker
        api.subscribe(None, date(2022, 2, 2), client, activity, transaction)
    assert str(op_error.value) == "The subscribed [client=1] is not the charged [client=2]."


def test_subscribe_invalidSubscriptionDate_raisesInvalidDate():
    log_responsible.config(MockSecurityHandler())

    lesser, greater = date(2022, 2, 1), date(2022, 2, 2)

    client = Client(Number(1), String("dummy_name", max_len=20), greater, date(2022, 2, 1),
                    String("dummy_tel", max_len=20), String("dummy_descr", max_len=20), is_active=True)
    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), String("dummy_descr", max_len=20),
                        charge_once=False, locked=True)
    with pytest.raises(InvalidDate):
        # noinspection PyTypeChecker
        api.subscribe(None, lesser, client, activity)


def test_subscribe_raisesSecurityError_withNoResponsible():
    log_responsible.config(SimpleSecurityHandler(action_tags={"subscribe"}, needs_responsible={"subscribe"}))

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Data setup.
    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), date(2022, 2, 1),
                    String("dummy_tel", max_len=20), String("dummy_descr", max_len=20), is_active=True)
    client_repo.add(client)

    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), String("dummy_descr", max_len=20),
                        charge_once=False)
    activity_repo.add(activity)

    # Feature being tested.
    with pytest.raises(SecurityError) as sec_err:
        api.subscribe(subscription_repo, date(2022, 2, 2), client, activity)
    assert str(sec_err.value) == "Tried to execute action without a defined responsible."


def test_subscribe_raisesSecurityError_withUnregisteredAction():
    log_responsible.config(SimpleSecurityHandler(action_tags={"other_action"}, needs_responsible={"other_action"}))

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Data setup.
    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), date(2022, 2, 1),
                    String("dummy_tel", max_len=20), String("dummy_descr", max_len=20), is_active=True)
    client_repo.add(client)

    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), String("dummy_descr", max_len=20),
                        charge_once=False)
    activity_repo.add(activity)

    # Feature being tested.
    with pytest.raises(SecurityError) as sec_err:
        api.subscribe(subscription_repo, date(2022, 2, 2), client, activity)
    assert str(sec_err.value) == "Tried to execute an unregistered action." and sec_err.value.action_tag == "subscribe"


def test_cancel():
    log_responsible.config(SimpleSecurityHandler(action_tags={"cancel"}, needs_responsible={"cancel"}))

    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Data setup.
    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), date(2022, 2, 1),
                    String("dummy_tel", max_len=20), String("dummy_descr", max_len=20), is_active=True)
    client_repo.add(client)

    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), String("dummy_descr", max_len=20),
                        charge_once=False)
    activity_repo.add(activity)

    subscription = Subscription(date(2022, 2, 2), client, activity)
    client.add(subscription)
    subscription_repo.add(subscription)

    # Feature being tested.
    log_responsible.handler.current_responsible = String("TestResp", max_len=30)
    api.cancel(subscription_repo, subscription)
    assert activity_repo.n_subscribers(activity) == 0


def test_charge_notChargeOnceActivity():
    log_responsible.config(SimpleSecurityHandler(action_tags={"register_subscription_charge"},
                                                 needs_responsible={"register_subscription_charge"}))
    # Repositories setup.
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    balance_repo = peewee.SqliteBalanceRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    transaction_repo.client_repo = client_repo  # ToDo after implementing proxies, remove this line.
    subscription_repo = peewee.SqliteSubscriptionRepo()

    # Data setup.
    client = Client(Number(1), String("dummy_name", max_len=20), date(2022, 2, 1), date(2022, 2, 1),
                    String("dummy_tel", max_len=20), String("dummy_descr", max_len=20), is_active=True)
    client_repo.add(client)

    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), String("dummy_descr", max_len=20),
                        charge_once=False)
    activity_repo.add(activity)

    subscription = Subscription(date(2022, 2, 2), client, activity)
    client.add(subscription)
    subscription_repo.add(subscription)

    # This ensures that the activity is overdue.
    assert not subscription.up_to_date(date(2022, 4, 1))
    create_transaction_fn = functools.partial(
        transaction_repo.create, "Cobro", date(2022, 4, 1), Currency(0.0), "dummy_method",
        String("dummy_resp", max_len=20), "dummy_descr", client
    )

    # Feature being tested.
    log_responsible.handler.current_responsible = String("TestResp", max_len=30)
    api.register_subscription_charge(subscription_repo, subscription, create_transaction_fn)
    # Check that the activity is up-to-date, because a charge was registered.
    assert subscription.up_to_date(date(2022, 4, 1))
