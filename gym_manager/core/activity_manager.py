import logging
from typing import Generator

from gym_manager.core.base import Client, Activity, Payment, Inscription, String, Currency
from gym_manager.core.persistence import ActivityRepo, InscriptionRepo


class ActivityManager:
    def __init__(self, activity_repo: ActivityRepo, inscription_repo: InscriptionRepo):
        self.activity_repo = activity_repo
        self.inscription_repo = inscription_repo

    def create(self, name: String, price: Currency, pay_once: bool, description: String):
        self.activity_repo.create(name, price, pay_once, description)

    def update(self, activity: Activity):
        self.activity_repo.update(activity)

    def remove(self, activity: Activity):
        self.activity_repo.remove(activity, cascade_removing=True)

    def activities(self) -> Generator[Activity, None, None]:
        """Yields all existing activities.
        """
        yield from self.activity_repo.all()

    def inscriptions(self, activity: Activity) -> int:
        return self.activity_repo.inscriptions(activity)

    def load_inscriptions(self, client: Client):
        for inscription in self.inscription_repo.all(client):
            client.sign_on(inscription)

    def sign_on(self, client: Client, activity: Activity, payment: Payment | None = None):
        """Signs on a client in an activity.
        """
        inscription = Inscription(client, activity, payment)
        self.inscription_repo.add(inscription)
        client.sign_on(inscription)
        logging.info(f"'Client' [{client.dni}] signed up in the 'activity' [{activity.name}] with 'payment' "
                     f"{'None' if payment is None else payment.id}")

    def unsubscribe(self, inscription: Inscription):
        inscription.client.cancel(inscription)
        self.inscription_repo.remove(inscription)
        logging.info(f"'Client' [{inscription.client.dni}] unsubscribed from the 'activity' "
                     f"[{inscription.activity.name}].")
