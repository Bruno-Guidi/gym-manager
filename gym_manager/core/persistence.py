import abc
from datetime import date
from typing import Iterable, Generator

from gym_manager.core.base import Client, Activity, Currency, String, Number, Date


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
    def add(self, dni: Number, name: String, admission: Date, telephone: String, direction: String) -> Number:
        """Creates a client with the given data, and return its dni.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, client: Client):
        """Removes the given *client* from the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, client: Client):
        """Updates the client in the repository whose dni is *client.dni*, with the data of *client*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(self, **kwargs) -> Generator[Client, None, None]:
        """Returns all the clients in the repository.
        """
        raise NotImplementedError