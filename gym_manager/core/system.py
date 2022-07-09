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


def subscribe(
        subscription_repo: SubscriptionRepo, when: date, client: Client, activity: Activity,
        transaction: Transaction | None = None
) -> Subscription:
    """Subscribes *client* to *activity* and registers the charging for the subscription, if *transaction* is given.

    Args:
        subscription_repo: repository implementation that registers subscriptions.
        when: date when the subscription is registered.
        client: client to subscribe.
        activity: activity to which the subscription is registered.
        transaction: charging for the subscription. It is optional.

    Returns:
        The created subscription.

    Raises:
        OperationalError if *activity* is a "charge once" activity.
        InvalidDate if *when* < *client.admission*.
    """
    if activity.charge_once:
        raise OperationalError(f"Subscriptions to [activity={activity.name}] are not allowed because it is a "
                               f"'charge_once' activity.")
    if client.admission > when:
        raise InvalidDate(f"[subscription_date={when}] cannot be lesser than [admission_date={client.admission}] of "
                          f"the client")
    if transaction is not None and transaction.client != client:
        raise OperationalError(f"The subscribed [client={client.dni}] is not the charged [client="
                               f"{transaction.client.dni}].")

    subscription = Subscription(when, client, activity, transaction)
    subscription_repo.add(subscription)
    client.add(subscription)

    logger.info(
        f"Client [dni={client.dni}] subscribed to activity [activity_name={activity.name}], with [payment="
        f"{'None' if transaction is None else transaction.id}]."
    )

    return subscription


def cancel(subscription_repo: SubscriptionRepo, subscription: Subscription) -> None:
    """Cancels the *subscription*.

    Args:
        subscription_repo: repository implementation that registers subscriptions.
        subscription: subscription to cancel.
    """
    subscription.client.unsubscribe(subscription.activity)
    subscription_repo.remove(subscription)

    logger.info(
        f"Client [dni={subscription.client.dni}] unsubscribed of activity [activity_name={subscription.activity.name}]."
    )


def charge(
        transaction_repo: TransactionRepo, subscription_repo: SubscriptionRepo, when: date, client: Client,
        activity: Activity, method: str, responsible: String
) -> Transaction:
    """Charges the *client* for its *activity* subscription.

    Args:
        transaction_repo: repository implementation that registers transactions.
        subscription_repo: repository implementation that registers subscriptions.
        when: date when the charging is made.
        client: client being charged.
        activity: activity being charged.
        method: method used in the charging.
        responsible: responsible for doing the charging.

    Returns:
        The created transaction.
    """
    description = f"Cobro por actividad {activity.name}"
    transaction = transaction_repo.create("Cobro", when, activity.price, method, responsible, description, client)

    # For the activities that are not 'charge once', record that the client was charged for it.
    # A 'charge once' activity is, for example, an activity related to bookings.
    if not activity.charge_once:
        client.register_charge(activity, transaction)
        subscription_repo.register_charge(client, activity, transaction)

    logger.info(f"Responsible [responsible={responsible}] charged the client [dni={client.dni}] for the activity "
                f"[activity_name={activity.name}] with an amount [amount={activity.price}].")

    return transaction


def extract(
        transaction_repo: TransactionRepo, when: date, amount: Currency, method: str, responsible: String,
        description: String
) -> Transaction:
    """Registers an extraction.

    Args:
        transaction_repo: repository implementation that registers transactions.
        when: date when the charging is made.
        amount: extracted amount.
        method: method used in the charging.
        responsible: responsible for doing the charging.
        description: description of the extraction.

    Returns:
        The created transaction.
    """
    transaction = transaction_repo.create("Extracción", when, amount, method, responsible, description.as_primitive())

    logger.info(f"Responsible [responsible={responsible}] extracted an amount [amount={amount}].")

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

