from __future__ import annotations

import logging
from datetime import date
from typing import Iterable

from gym_manager.core import constants
from gym_manager.core.base import String, Transaction, Client, Activity, Subscription, Currency, OperationalError, \
    Balance
from gym_manager.core.persistence import TransactionRepo, SubscriptionRepo, ActivityRepo, BalanceRepo

logger = logging.getLogger(__name__)


class InvalidDate(Exception):
    """Exception to be raised when a given date fails to pass a given condition.
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ActivityManager:
    """Provides an API to do activity related things.
    """

    def __init__(self, activity_repo: ActivityRepo, sub_repo: SubscriptionRepo):
        self.activity_repo = activity_repo
        self.sub_repo = sub_repo

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
            self._transaction_types["Cobro"], when, activity.price, method, responsible, description, client
        )

        # For the activities that are not 'charge once', record that the client was charged for it.
        # A 'charge once' activity is, for example, an activity related to bookings.
        if not activity.charge_once:
            client.register_charge(activity, transaction)
            self.sub_repo.register_charge(client, activity, transaction)

        return transaction


def register_extraction(
        when: date, amount: Currency, method: String, responsible: String, description: String,
        transaction_repo: TransactionRepo
) -> Transaction:
    transaction_type = String("Extracción", max_len=constants.TRANSACTION_TYPE_CHARS)
    transaction = transaction_repo.create(transaction_type, when, amount, method, responsible, description)

    logger.info(f"Registered [extraction={transaction}]")

    return transaction


def generate_balance(
        transactions: Iterable[Transaction],
        transaction_types: Iterable[String],
        transaction_methods: Iterable[String]
):
    """Generates the balance of the day *when*. The transactions are grouped by type and by method, and then summed up.
    """
    total = String("Total", max_len=constants.TRANSACTION_TYPE_CHARS)
    balance = {trans_type: {trans_method: Currency(0) for trans_method in transaction_methods}
               for trans_type in transaction_types}
    for trans_type in transaction_types:
        balance[trans_type][total] = Currency(0)

    for transaction in transactions:
        balance[transaction.type][transaction.method].increase(transaction.amount)
        balance[transaction.type][total].increase(transaction.amount)

    return balance


def close_balance(
        balance: Balance,
        balance_date: date,
        responsible: String,
        transactions: Iterable[Transaction],
        transactions_repo: TransactionRepo,
        balance_repo: BalanceRepo
):
    balance_repo.add(balance_date, responsible, balance)
    for transaction in transactions:
        transaction.balance_date = balance_date
        transactions_repo.bind_to_balance(transaction, balance_date)

