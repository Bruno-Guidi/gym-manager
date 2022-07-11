from __future__ import annotations

import logging
from datetime import date
from typing import Iterable

from gym_manager.core.base import (
    String, Transaction, Client, Activity, Subscription, Currency, OperationalError, Balance, InvalidDate
)
from gym_manager.core.persistence import TransactionRepo, SubscriptionRepo, BalanceRepo

logger = logging.getLogger(__name__)


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

    # noinspection PyUnresolvedReferences
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


def register_subscription_charge(
        subscription_repo: SubscriptionRepo, subscription: Subscription, transaction: Transaction
):
    """Registers that the *client* was charged for its *activity* subscription.

    Args:
        subscription_repo: repository implementation that registers subscriptions.
        subscription: subscription being charged.
        transaction: transaction generated when the client was charged.
    """
    if subscription.activity.charge_once:
        raise OperationalError(f"The [activity={subscription.activity.name}] is not subscribeable")
    if subscription.client != transaction.client:
        raise OperationalError(f"The [client={transaction.client.name}] is being charged for the [activity="
                               f"{subscription.activity.name}] done by the [client={subscription.client.name}].")

    subscription.transaction = transaction  # Links the transaction with the subscription.
    subscription_repo.update(subscription)

    logger.info(f"Responsible [responsible={transaction.responsible}] charged the client [dni={transaction.client.dni}]"
                f" for the activity [activity_name={subscription.activity.name}] with an amount [amount="
                f"{subscription.activity.price}].")


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


def generate_balance(transactions: Iterable[Transaction]) -> Balance:
    """Generates the balance from the given *transactions*. The transactions are grouped by type and by method, and then
    summed up.

    Args:
        transactions: transactions to include in the balance.

    Returns:
        The generated balance.
    """
    balance = {"Cobro": {}, "Extracción": {}}
    total = "Total"
    balance["Cobro"][total], balance["Extracción"][total] = Currency(0), Currency(0)

    for transaction in transactions:
        if transaction.method not in balance[transaction.type]:
            balance[transaction.type][transaction.method] = Currency(0)
        balance[transaction.type][transaction.method].increase(transaction.amount)
        balance[transaction.type][total].increase(transaction.amount)

    logger.info(f"Generated balance [balance={balance}].")

    return balance


def close_balance(
        transaction_repo: TransactionRepo,
        balance_repo: BalanceRepo,
        balance: Balance,
        balance_date: date,
        responsible: String
):
    """Closes the *balance*, save it in the repository and bind the transactions to the balance.

    Args:
        transaction_repo: repository implementation that registers transactions.
        balance_repo: repository implementation that registers balances.
        balance: balance to close.
        balance_date: date when the balance was done.
        responsible: responsible for closing the balance.
    """
    balance_repo.add(balance_date, responsible, balance)

    if balance_repo.balance_done(balance_date):
        transaction_gen = transaction_repo.all(page=1, balance_date=balance_date)
    else:
        transaction_gen = transaction_repo.all(page=1, include_closed=False)

    for transaction in transaction_gen:
        transaction.balance_date = balance_date
        transaction_repo.bind_to_balance(transaction, balance_date)

    logger.info(f"Responsible [responsible={responsible}] closed the balance [balance={balance}] of [balance_date="
                f"{balance_date}].")
