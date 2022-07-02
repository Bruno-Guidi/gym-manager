from __future__ import annotations

import logging
from datetime import date
from typing import Iterable

from gym_manager.core import constants
from gym_manager.core.base import String, Transaction, Client, Activity, Subscription, Currency, OperationalError
from gym_manager.core.persistence import TransactionRepo, SubscriptionRepo, ActivityRepo, BalanceRepo

logger = logging.getLogger(__name__)


class ActivityManager:
    """Provides an API to do activity related things.
    """

    def __init__(self, activity_repo: ActivityRepo, sub_repo: SubscriptionRepo):
        self.activity_repo = activity_repo
        self.sub_repo = sub_repo

    def create(
            self, name: String, price: Currency, charge_once: bool, description: String, locked: bool = False
    ) -> Activity:
        activity: Activity
        try:
            activity = self.activity_repo.get(name)
        except KeyError:
            activity = self.activity_repo.create(name, price, charge_once, description, locked)
        return activity

    def update(self, activity: Activity):
        self.activity_repo.update(activity)

    def remove(self, activity: Activity):
        self.activity_repo.remove(activity, cascade_removing=True)

    def activities(self, **active_filters) -> Iterable[Activity]:
        """Retrieves existing activities.

        Keyword Args:
            dict {str: tuple[Filter, str]}. The str key is the filter name, and the str in the tuple is the value to
                apply to the filter.
        """
        for activity in self.activity_repo.all():
            if all([filter_.passes(activity, value) for filter_, value in active_filters.values()]):
                yield activity

    def n_subscribers(self, activity: Activity) -> int:
        return self.activity_repo.n_subscribers(activity)

    def subscribe(
            self, when: date, client: Client, activity: Activity, transaction: Transaction | None = None
    ) -> Subscription:
        """Subscribes the *client* in the *activity*. If *transaction* is given, then associate it to the subscription.

        Raises:
            OperationalError if the activity is a charge_once activity, or if the date of the subscription is lesser
             than the admission date of the client.
        """
        if activity.charge_once:
            raise OperationalError("Subscriptions to 'charge_once' activities are not allowed.", activity=activity)
        if client.admission > when:
            raise OperationalError("Subscription date cannot be lesser than client's admission date",
                                   subscription_date=when, client_admission_date=client.admission)

        sub = Subscription(when, client, activity, transaction)
        self.sub_repo.add(sub)
        client.add(sub)

        logger.getChild(type(self).__name__).info(
            f"Client with [dni={client.dni}] subscribed in the activity with [activity_id={activity.name}], with the "
            f"payment [payment={'None' if transaction is None else transaction.id}].")

        return sub

    def cancel(self, subscription: Subscription):
        subscription.client.unsubscribe(subscription.activity)
        self.sub_repo.remove(subscription)
        logging.info(
            f"'Client' [{subscription.client.dni}] unsubscribed from the 'activity' [{subscription.activity.name}].")


class AccountingSystem:
    """Provides an API to do accounting related things.
    """

    def __init__(
            self,
            transaction_repo: TransactionRepo,
            sub_repo: SubscriptionRepo,
            balance_repo: BalanceRepo,
            transaction_types: tuple[str, ...],
            methods: tuple[str, ...]
    ) -> None:
        self.transaction_repo = transaction_repo
        self.sub_repo = sub_repo
        self.balance_repo = balance_repo
        self._transaction_types = {name: String(name, max_len=constants.TRANSACTION_TYPE_CHARS)
                                   for name in transaction_types}
        self.methods = tuple(String(name, max_len=constants.TRANSACTION_METHOD_CHARS) for name in methods)

    def transactions_types(self) -> Iterable[String]:
        return self._transaction_types.values()

    def transactions(self, page: int = 1, page_len: int = 15, **filters) -> Iterable[Transaction]:
        """Retrieves transactions.

        Keyword Args:
            dict {str: tuple[Filter, str]}. The str key is the filter name, and the str in the tuple is the value to
                apply to the filter.
        """
        yield from self.transaction_repo.all(page, page_len, **filters)

    def charge(
            self, when: date, client: Client, activity: Activity, method: String, responsible: String,
            description: String
    ) -> Transaction:
        """Charges the *client* for its *activity* subscription.
        """
        transaction = self.transaction_repo.create(
            self._transaction_types["charge"], client, when, activity.price, method, responsible, description
        )

        # For the activities that are not 'charge once', record that the client was charged for it.
        # A 'charge once' activity is, for example, an activity related to bookings.
        if not activity.charge_once:
            client.register_charge(activity, transaction)
            self.sub_repo.register_charge(client, activity, transaction)

        return transaction


def generate_balance(
        transactions: Iterable[Transaction],
        transaction_types: Iterable[String],
        transaction_methods: Iterable[String]
):
    """Generates the balance of the day *when*. The transactions are grouped by type and by method, and then summed up.
    """
    total = String("Total", max_len=constants.TRANSACTION_TYPE_CHARS)
    balance = {trans_type: {trans_method: Currency("0") for trans_method in transaction_methods}
               for trans_type in transaction_types}
    for trans_type in transaction_types:
        balance[trans_type][total] = Currency("0")

    for transaction in transactions:
        balance[transaction.type][transaction.method].increase(transaction.amount)
        balance[transaction.type][total].increase(transaction.amount)

    return balance
