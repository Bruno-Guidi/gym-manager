import logging
from datetime import date
from typing import Iterable

from gym_manager.core import constants
from gym_manager.core.base import String, Transaction, Client, Activity, Inscription, Currency
from gym_manager.core.persistence import TransactionRepo, InscriptionRepo, ActivityRepo

logger = logging.getLogger(__name__)


class ActivityManager:
    """Provides an API to do activity related things.
    """

    def __init__(self, activity_repo: ActivityRepo, inscription_repo: InscriptionRepo):
        self.activity_repo = activity_repo
        self.inscription_repo = inscription_repo

    def create(self, name: String, price: Currency, charge_once: bool, description: String) -> Activity:
        return self.activity_repo.create(name, price, charge_once, description)

    def update(self, activity: Activity):
        self.activity_repo.update(activity)

    def remove(self, activity: Activity):
        unsubscribed = [client.dni for client in activity.unsubscribe_clients()]
        self.activity_repo.remove(activity, cascade_removing=True)

        logger.getChild(type(self).__name__).info(
            f"Clients with [dni={unsubscribed}] where unsubscribed after activity [activity_id={activity.id}] was "
            f"removed.")

    def activities(self, **active_filters) -> Iterable[Activity]:
        """Retrieves existing activities.

        Keyword Args:
            dict {str: tuple[Filter, str]}. The str key is the filter name, and the str in the tuple is the value to
                apply to the filter.
        """
        for activity in self.activity_repo.all():
            if all([filter_.passes(activity, value) for filter_, value in active_filters.values()]):
                yield activity

    def n_inscriptions(self, activity: Activity) -> int:
        return self.activity_repo.n_inscriptions(activity)

    def sign_on(
            self, when: date, client: Client, activity: Activity, transaction: Transaction | None = None
    ) -> Inscription:
        """Signs on the *client* in the *activity*. If *transaction* is given, then associate it to the inscription.
        """
        inscription = Inscription(when, client, activity, transaction)
        self.inscription_repo.add(inscription)
        activity.sign_up_client(client)
        client.sign_on(inscription)

        logger.getChild(type(self).__name__).info(
            f"Client with [dni={client.dni}] signed up in the activity with [activity_id={activity.id}], with the "
            f"payment [payment={'None' if transaction is None else transaction.id}].")

        return inscription

    def unsubscribe(self, inscription: Inscription):
        inscription.client.cancel(inscription.activity)
        self.inscription_repo.remove(inscription)
        logging.info(f"'Client' [{inscription.client.dni}] unsubscribed from the 'activity' "
                     f"[{inscription.activity.name}].")


class AccountingSystem:
    """Provides an API to do accounting related things.
    """

    def __init__(
            self,
            transaction_repo: TransactionRepo,
            inscription_repo: InscriptionRepo,
            transaction_types: tuple[str, ...],
            methods: tuple[str, ...]
    ) -> None:
        self.transaction_repo = transaction_repo
        self.inscription_repo = inscription_repo
        self.transaction_types = {name: String(name, max_len=constants.TRANSACTION_TYPE_CHARS)
                                  for name in transaction_types}
        self.methods = tuple(String(name, max_len=constants.TRANSACTION_METHOD_CHARS) for name in methods)

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
        """Charges the *client* for its *activity* inscription.
        """
        transaction = self.transaction_repo.create(
            self.transaction_types["charge"], client, when, activity.price, method, responsible, description
        )

        # For the activities that are not 'charge once', record that the client was charged for it.
        # A 'charge once' activity is, for example, an activity related to bookings.
        if not activity.charge_once:
            client.register_charge(activity, transaction)
            self.inscription_repo.register_charge(client, activity, transaction)

        return transaction
