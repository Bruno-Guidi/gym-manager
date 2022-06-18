import logging
from typing import Generator, Type

from gym_manager.core.base import Client, Activity, Payment, Inscription, String, Currency, ActivityFilter, NameFilter
from gym_manager.core.persistence import ActivityRepo, InscriptionRepo


class ActivityManager:
    def __init__(self, activity_repo: ActivityRepo, inscription_repo: InscriptionRepo):
        self.activity_repo = activity_repo
        self.inscription_repo = inscription_repo
        self.filters: dict[str, Type[ActivityFilter]] = {"name": NameFilter}

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
        # ToDo cache.
        _active_filters: dict[str, ActivityFilter] = {name: filter_type(active_filters[name])
                                                      for name, filter_type in self.filters.items()}
        for activity in self.activity_repo.all():
            if all([filter_.passes_filter(activity) for filter_ in _active_filters.values()]):
                yield activity

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
