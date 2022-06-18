import abc
from datetime import date
from typing import Iterable, Generator

from gym_manager.core.base import Client, Activity, Currency, String, Number, Inscription, Transaction


class ClientRepo(abc.ABC):
    """Clients repository interface.
    """

    @abc.abstractmethod
    def contains(self, dni: Number) -> bool:
        """Returns True if there is a client with the given *dni*, False otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add(self, client: Client):
        """Adds the *client* to the repository.
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
    def all(
            self, cache: dict[int, Activity] | None = None, only_actives: bool = True, name_filter: str = "",
            **kwargs
    ) -> Generator[Client, None, None]:
        """Returns all the clients in the repository.

        Args:
            cache: cached activities.
            only_actives: If True, retrieve only the active clients. An active client is a client that wasn't removed.
            name_filter: If given, filter clients that fulfill the condition 'name_filter like %client.name%'.

        Keyword Args:
            page_number: number of page of the table to return.
            items_per_page: number of items per page.
        """
        raise NotImplementedError


class ActivityRepo(abc.ABC):
    """Activities repository interface.
    """
    @abc.abstractmethod
    def create(self, name: String, price: Currency, pay_once: bool, description: String) -> Activity:
        """Creates an activity with the given data, and returns it.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, activity: Activity, cascade_removing: bool = False):
        """Tries to remove the given *activity*.

        If *cascade_removing* is False, and there is at least one client registered in the activity, the removing will
        fail. If *cascade_removing* is True, the *activity* and all registrations for it will be removed.

        Args:
            activity: activity to remove.
            cascade_removing: if True, remove the activity and all registrations for it. If False, remove the activity
                only if it has zero registrations.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, activity: Activity):
        """Updates the activity in the repository whose id is *activity.id*, with the data of *activity*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(self) -> Generator[Activity, None, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def inscriptions(self, activity: Activity) -> int:
        """Returns the number of clients registered in the given *activity*.
        """
        raise NotImplementedError


class InscriptionRepo(abc.ABC):
    """Repository interface for client's activities inscriptions.
    """
    @abc.abstractmethod
    def add(self, inscription: Inscription):
        """Adds the given *inscription* to the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, inscription: Inscription):
        """Removes the given *inscription* from the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(self, client: Client) -> Generator[Inscription, None, None]:
        """Retrieves all inscriptions of the given *client*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def expired(self, when: date, **kwargs) -> Generator[Inscription, None, None]:
        """Retrieves all entries whose pay day has passed if today date were *when*.
        """
        raise NotImplementedError


class TransactionRepo(abc.ABC):
    """Transaction repository interface.
    """
    @abc.abstractmethod
    def create(
            self, type: String, client: Client, when: date, amount: Currency, method: String, responsible: String,
            description: String
    ) -> Transaction:
        """Register a new transaction with the given information. This method must return the created
        transaction.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(
            self, page: int, page_len: int = 20, cache: dict[Number, Client] | None = None,
            from_date: date | None = None, to_date: date | None = None,
            **kwargs
    ) -> Generator[Transaction, None, None]:
        """Retrieves the transactions in the repository.
        """
        raise NotImplementedError
