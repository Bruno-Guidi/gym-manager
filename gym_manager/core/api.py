from __future__ import annotations

import logging
from datetime import date
from typing import Iterable, TypeAlias, Callable

from gym_manager.core.base import (
    String, Transaction, Client, Activity, Subscription, Currency, OperationalError, Balance, InvalidDate
)
from gym_manager.core.persistence import TransactionRepo, SubscriptionRepo, BalanceRepo
from gym_manager.core.security import log_responsible

logger = logging.getLogger(__name__)

CreateTransactionFn: TypeAlias = Callable[[], Transaction]


def _subscribe_description(subscription: Subscription) -> str:
    return f"Inscripción a actividad {subscription.activity.name} de {subscription.client.name}"


@log_responsible(action_tag="subscribe", to_str=_subscribe_description)
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
        raise OperationalError(f"The subscribed [client.id={client.id}] is not the charged [client.id="
                               f"{transaction.client.id}].")

    subscription = Subscription(when, client, activity, transaction)
    subscription_repo.add(subscription)
    client.add(subscription)

    # noinspection PyUnresolvedReferences
    logger.getChild(__name__).info(
        f"Client [client.id={client.id}] subscribed to activity [activity_name={activity.name}], with [payment="
        f"{'None' if transaction is None else transaction.id}]."
    )

    return subscription


def _cancel_sub_description(subscription: Subscription) -> str:
    return f"Cancelación inscripción de actividad {subscription.activity.name} a {subscription.client.name}"


@log_responsible(action_tag="cancel", to_str=_cancel_sub_description)
def cancel(subscription_repo: SubscriptionRepo, subscription: Subscription) -> Subscription:
    """Cancels the *subscription*.

    Args:
        subscription_repo: repository implementation that registers subscriptions.
        subscription: subscription to cancel.
    """
    subscription.client.unsubscribe(subscription.activity)
    subscription_repo.remove(subscription)

    logger.getChild(__name__).info(
        f"Client [dni={subscription.client.dni}] unsubscribed of activity [activity_name={subscription.activity.name}]."
    )
    return subscription


def _charge_sub_description(subscription: Subscription) -> str:
    return (f"Cobro de {Currency.fmt(subscription.activity.price)} por actividad {subscription.activity.name} a "
            f"{subscription.client.name}")


@log_responsible(action_tag="register_subscription_charge", to_str=_charge_sub_description)
def register_subscription_charge(
        subscription_repo: SubscriptionRepo, subscription: Subscription, year: int, month: int,
        create_transaction_fn: CreateTransactionFn
) -> Subscription:
    """Registers that the *client* was charged for its *activity* subscription.

    Args:
        subscription_repo: repository implementation that registers subscriptions.
        subscription: subscription being charged.
        year: year that was charged.
        month: month of the year that was charged.
        create_transaction_fn: function used to create the associated transaction.
    """
    transaction = create_transaction_fn()

    if subscription.activity.charge_once:
        raise OperationalError(f"The [activity={subscription.activity.name}] is not subscribeable")
    if subscription.client != transaction.client:
        raise OperationalError(f"The [client={transaction.client.name}] is being charged for the [activity="
                               f"{subscription.activity.name}] done by the [client={subscription.client.name}].")

    subscription.add_transaction(year, month, transaction)  # Links the transaction with the subscription.
    subscription_repo.register_transaction(subscription, year, month, transaction)

    logger.getChild(__name__).info(
        f"Responsible [responsible={transaction.responsible}] charged the client [dni={transaction.client.dni}]"
        f" for the activity [activity_name={subscription.activity.name}] with an amount [amount="
        f"{subscription.activity.price}]."
    )

    return subscription


def _extract_description(transaction: Transaction) -> str:
    return f"Extracción de {Currency.fmt(transaction.amount)} para '{transaction.description}'."


@log_responsible(action_tag="extract", to_str=_extract_description)
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

    logger.getChild(__name__).info(f"Extracted [amount={amount}].")

    return transaction


def generate_balance(transactions: Iterable[Transaction]) -> tuple[Balance, list[Transaction]]:
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

    _transactions = []
    for transaction in transactions:
        _transactions.append(transaction)
        if transaction.method not in balance[transaction.type]:
            balance[transaction.type][transaction.method] = Currency(0)
        balance[transaction.type][transaction.method].increase(transaction.amount)
        balance[transaction.type][total].increase(transaction.amount)

    logger.info(f"Generated balance [balance={balance}].")

    return balance, _transactions


@log_responsible(action_tag="close_balance", to_str=lambda when: f"Cierre caja diaria {when}")
def close_balance(
        transaction_repo: TransactionRepo,
        balance_repo: BalanceRepo,
        balance: Balance,
        transactions: list[Transaction],
        balance_date: date,
        responsible: String,
        create_extraction_fn: CreateTransactionFn | None = None
):
    """Closes the *balance*, save it in the repository and bind the transactions to the balance.

    Args:
        transaction_repo: repository implementation that registers transactions.
        balance_repo: repository implementation that registers balances.
        balance: balance to close.
        transactions: transactions included in the balance.
        balance_date: date when the balance was done.
        responsible: responsible for closing the balance.
        create_extraction_fn: function used to create the extraction.

    """
    if balance_repo.balance_done(balance_date):
        raise OperationalError(f"Daily balance for the [balance_date={balance_date}] was already done.")

    if create_extraction_fn is not None:
        # Creates the extraction done at the end of the day.
        extraction = create_extraction_fn()
        transactions.append(extraction)

        # Adds the extraction to the balance.
        if extraction.method not in balance["Extracción"]:
            balance["Extracción"][extraction.method] = Currency(0)
        balance["Extracción"][extraction.method].increase(extraction.amount)
        balance["Extracción"]["Total"].increase(extraction.amount)

    balance_repo.add(balance_date, responsible, balance)

    for transaction in transactions:
        transaction.balance_date = balance_date
        transaction_repo.bind_to_balance(transaction, balance_date)

    logger.getChild(__name__).info(f"Responsible [responsible={responsible}] closed the balance [balance={balance}] of "
                                   f"[balance_date={balance_date}].")
    # This is only used in the log_responsible decorator. If needed, other things can be returned. Remember to update
    # the to_str callable in the decorator.
    return balance_date
