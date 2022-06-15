import abc
from datetime import date
from typing import Iterable, Generator

from gym_manager.core.base import Client, Activity, Currency, String, Number, Date, Registration, Payment


class ClientRepo(abc.ABC):
    """Clients repository interface.
    """

    @abc.abstractmethod
    def contains(self, dni: Number) -> bool:
        """Returns True if there is a client with the given *dni*, False otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, dni: Number) -> Client:
        """Returns the client with the given *dni*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, dni: Number, name: String, admission: Date, telephone: String, direction: String) -> Number:
        """Creates a client with the given data, and return its dni.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, client: Client):
        """Marks the given *client* as inactive.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, client: Client):
        """Updates the client in the repository whose dni is *client.dni*, with the data of *client*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(self, only_actives: bool = True, **kwargs) -> Generator[Client, None, None]:
        """Returns all the clients in the repository.

        Args:
            only_actives: If True, retrieve only the active clients. An active client is a client that wasn't removed.
        """
        raise NotImplementedError


class ActivityRepo(abc.ABC):
    """Activities repository interface.
    """
    @abc.abstractmethod
    def add(self, name: String, price: Currency, pay_once: bool, description: String) -> int:
        """Creates an activity with the given data, and returns its id in the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(self, **kwargs) -> Generator[Activity, None, None]:
        raise NotImplementedError


class RegistrationRepo(abc.ABC):
    """Repository interface for client's activities registrations.
    """
    @abc.abstractmethod
    def update_or_create(self, registration: Registration):
        """Updates the given *registration* in the repository. If there is no row in the repository, then creates a
        new one.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def expired(self, today: date, **kwargs) -> Iterable[Registration]:
        """Retrieves all entries whose pay day has passed if today date were *today*.
        """
        raise NotImplementedError


class PaymentRepo(abc.ABC):
    """Payments repository interface.
    """
    @abc.abstractmethod
    def register(
            self, client: Client, when: date, amount: Currency, method: String, responsible: String, description: String
    ) -> Payment:
        """Register a new payment with the given information. This method must return the created payment.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(self, client: Client, **kwargs) -> Iterable[Payment]:
        """Retrieves the payments of the given *client*
        """
        raise NotImplementedError
