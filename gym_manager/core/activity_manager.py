import logging
from typing import Generator

from gym_manager.core.base import Client, Activity, Payment, Inscription
from gym_manager.core.persistence import ActivityRepo, InscriptionRepo


class ActivityManager:
    def __init__(self, activity_repo: ActivityRepo, inscription_repo: InscriptionRepo):
        self.activity_repo = activity_repo
        self.inscription_repo = inscription_repo

    def activities(self) -> Generator[Activity, None, None]:
        """Yields all existing activities.
        """
        yield from self.activity_repo.all()

    def sign_on(self, client: Client, activity: Activity, payment: Payment | None = None):
        """Signs on a client in an activity.
        """
        inscription = Inscription(client, activity, payment)
        self.inscription_repo.add(inscription)
        client.sign_on(inscription)
        logging.info(f"'Client' [{client.dni}] signed up in the 'activity' [{activity.name}] with 'payment' "
                     f"{'None' if payment is None else payment.id}")
