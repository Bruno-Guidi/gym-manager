import logging
from datetime import date
from typing import Generator

from gym_manager.core.base import Client, Activity, Transaction, Inscription, String, Currency
from gym_manager.core.persistence import ActivityRepo, InscriptionRepo


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
