import logging
from datetime import date
from typing import Iterable, Generator

from gym_manager.core import constants as consts
from gym_manager.core.base import String, Transaction, Client, Activity, Inscription, Currency
from gym_manager.core.persistence import TransactionRepo, InscriptionRepo, ActivityRepo


class ActivityManager:
    def __init__(self, activity_repo: ActivityRepo, inscription_repo: InscriptionRepo):
        self.activity_repo = activity_repo
        self.inscription_repo = inscription_repo

    def create(self, name: String, price: Currency, pay_once: bool, description: String) -> Activity:
        return self.activity_repo.create(name, price, pay_once, description)

    def update(self, activity: Activity):
        self.activity_repo.update(activity)

    def remove(self, activity: Activity):
        self.activity_repo.remove(activity, cascade_removing=True)

    def activities(self, **active_filters) -> Generator[Activity, None, None]:
        """Yields all existing activities.

        Keyword Args:
            name: If given, filter activities that fulfill the condition kwargs['name'] like %activity.name%.
        """
        for activity in self.activity_repo.all():
            if all([filter_.passes(activity, value) for filter_, value in active_filters.values()]):
                yield activity

    def n_inscriptions(self, activity: Activity) -> int:
        return self.activity_repo.n_inscriptions(activity)

    def sign_on(self, when: date, client: Client, activity: Activity, payment: Transaction | None = None):
        """Signs on a client in an activity.
        """
        inscription = Inscription(when, client, activity, payment)
        self.inscription_repo.add(inscription)
        client.sign_on(inscription)
        logging.info(f"'Client' [{client.dni}] signed up in the 'activity' [{activity.name}] with 'payment' "
                     f"{'None' if payment is None else payment.id}")

    def unsubscribe(self, inscription: Inscription):
        inscription.client.cancel(inscription)
        self.inscription_repo.remove(inscription)
        logging.info(f"'Client' [{inscription.client.dni}] unsubscribed from the 'activity' "
                     f"[{inscription.activity.name}].")


class AccountingSystem:

    def __init__(
            self,
            transaction_repo: TransactionRepo,
            inscription_repo: InscriptionRepo,
            transaction_types: list[str]
    ) -> None:
        self.transaction_repo = transaction_repo
        self.inscription_repo = inscription_repo
        self.transaction_types = {name: String(name, max_len=consts.TRANSACTION_TYPE_CHARS)
                                  for name in transaction_types}

    def methods(self) -> Iterable[String]:
        methods = [String("Efectivo", max_len=consts.TRANSACTION_METHOD_CHARS),
                   String("Débito", max_len=consts.TRANSACTION_METHOD_CHARS),
                   String("Crédito", max_len=consts.TRANSACTION_METHOD_CHARS)]
        for m in methods:
            yield m

    def transactions(self, page: int = 1, page_len: int = 15, **filters) -> Iterable[Transaction]:
        """Returns transactions.

        Keyword Args:
            client: allows filtering by client name.
            type: allows filtering by transaction type.
            from_date: allows filtering transactions whose *when* is after the given date (inclusive).
            to_date: allows filtering transactions whose *when* is before the given date (inclusive).
            method: allows filtering by transaction method.
            responsible: allows filtering by transaction responsible.
        """
        yield from self.transaction_repo.all(page, page_len, **filters)

    def charge(
            self, when: date, client: Client, activity: Activity, method: String, responsible: String,
            description: String
    ) -> Transaction:
        """Register a new charge transaction of an *activity* done by the *client*.

        Raises:
            NotRegistered if *client* doesn't do the *activity*.
        """
        # Creates the transaction.
        trans_type = self.transaction_types["charge"]
        transaction = self.transaction_repo.create(trans_type, client, when, activity.price, method, responsible,
                                                   description)

        # For the activities that are not 'charge once', record that the client was charged for it.
        # A 'charge once' activity is, for example, an activity related to bookings.
        if not activity.pay_once:
            client.register_charge(activity, transaction)
            self.inscription_repo.register_charge(client, activity, transaction)

        return transaction