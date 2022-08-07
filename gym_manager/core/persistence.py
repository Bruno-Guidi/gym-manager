from __future__ import annotations

import abc
import logging
import os
import shutil
from collections import OrderedDict
from datetime import date
from typing import Generator, Type, Any, Iterable, TypeAlias, ClassVar

from gym_manager.core.base import Client, Activity, Currency, String, Number, Subscription, Transaction, Filter, Balance

FilterValuePair: TypeAlias = tuple[Filter, str]


def create_backup(database_path: str, backup_dir: str):
    os.makedirs(backup_dir, exist_ok=True)
    dst = shutil.copy(database_path, os.path.join(backup_dir, f"backup_{date.today().strftime('%Y_%m_%d')}.db"))
    logging.getLogger(__name__).getChild(__name__).info(f"Created backup on {dst}")


class PersistenceError(Exception):

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class LRUCache:

    def __init__(self, key_type: Type, value_type: Type, max_len: int) -> None:
        self.key_type = key_type
        self.value_type = value_type

        self.max_len = max_len
        self._cache = OrderedDict()

    def __len__(self) -> int:
        return len(self._cache)

    def __getitem__(self, key: Any) -> Any:
        if not isinstance(key, self.key_type):
            raise TypeError(f"The LRUCache expected a '{self.key_type}' as key, but received a '{type(key)}'.")
        if key not in self._cache:  # There is one implicit __getitem__ call.
            raise KeyError(f"The LRUCache does not contains the key '{key}'.")

        self._cache.move_to_end(key, last=False)  # There is one implicit __getitem__ call.
        return self._cache[key]

    def __setitem__(self, key: Any, value: Any):
        if not isinstance(key, self.key_type):
            raise TypeError(f"The LRUCache expected a '{self.key_type}' as key, but received a '{type(key)}'.")
        if not isinstance(value, self.value_type):
            raise TypeError(f"The LRUCache expected a '{self.value_type}' as value, but received a '{type(value)}'.")

        self._cache[key] = value
        self._cache.move_to_end(key, last=False)
        if len(self._cache) > self.max_len:  # Removes the LRU key in case the cache len is exceeded.
            self._cache.popitem(last=True)

    def pop(self, key: Any):
        if not isinstance(key, self.key_type):
            raise TypeError(f"The LRUCache expected a '{self.key_type}' as key, but received a '{type(key)}'.")
        if key not in self._cache:
            raise KeyError(f"The LRUCache does not contains the key '{key}'.")
        self._cache.pop(key)

    def __contains__(self, key: Any) -> bool:
        return key in self._cache

    def __iter__(self):
        yield from iter(self._cache)

    def move_to_front(self, key: Any):
        if not isinstance(key, self.key_type):
            raise TypeError(f"The LRUCache expected a '{self.key_type}' as key, but received a '{type(key)}'.")
        if key not in self._cache:
            raise KeyError(f"The LRUCache does not contains the key '{key}'.")
        self._cache.move_to_end(key, last=False)


class ClientView(Client):
    """Stores only the client's dni and number. Could evolve into a proxy if needed later.
    """

    repository: ClassVar[ClientRepo] = None

    def __init__(self, id_: int, name: String, created_by: str, dni: Number):
        self.id = id_
        self.dni = dni
        self.name = name
        self.created_by = created_by

        if self.repository is None:
            raise AttributeError("ClassVar 'repository' wasn't set in ClientView.")
        self.repository.register_view(self)

    def __getattr__(self, attr_name):
        raise NotImplementedError(f"The object '{type(self).__name__}' created by '{self.created_by}' has no "
                                  f"implementation of '{attr_name}'.")

    def __repr__(self) -> str:
        return f"ClientView(id={self.id}, dni={self.dni.as_primitive()}, name={self.name}, created_by=" \
               f"{self.created_by})"

    def __str__(self) -> str:
        return repr(self)


class ClientRepo(abc.ABC):
    """Clients repository interface.
    """

    @abc.abstractmethod
    def get(self, id_: int) -> Client:
        raise NotImplementedError

    @abc.abstractmethod
    def is_active(self, dni: Number) -> bool:
        """Checks if there is an active client with the given *dni*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(self, name: String, admission: date, birthday: date, dni: Number) -> Client:
        """Adds the *client* to the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, client: Client):
        """Marks the given *client* as inactive, and delete its subscriptions.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, client: Client):
        """Updates the client in the repository whose dni is *client.dni*, with the data of *client*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[Client, None, None]:
        """Retrieve all the clients in the repository.

        Args:
            page: page to retrieve.
            page_len: clients per page. If None, retrieve all clients.
            filters: filters to apply.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        """Counts the number of clients in the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def register_view(self, view: ClientView):
        raise NotImplementedError

    @abc.abstractmethod
    def add_all(self, raw_clients: Iterable[tuple]):
        """Adds the clients in the iterable directly into the repository, without creating Client objects.
        """
        raise NotImplementedError


class ActivityRepo(abc.ABC):
    """Activities repository interface.
    """

    @abc.abstractmethod
    def create(self, name: String, price: Currency, description: String) -> Activity:
        """Adds *activity* to the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, name: String) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, name: String) -> Activity:
        """Retrieves the activity with the given *id* in the repository, if it exists.

        Raises:
            KeyError if there is no activity with the given *id*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, activity: Activity):
        """Removes the given *activity*.

        Raises:
            PersistenceError: if *activity* is locked.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, activity: Activity):
        """Updates the activity in the repository whose id is *activity.id*, with the data of *activity*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[Activity, None, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def n_subscribers(self, activity: Activity) -> int:
        """Returns the number of clients subscribed in the given *activity*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        """Counts the number of activities in the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_all(self, raw_activities: Iterable[tuple]):
        """Adds the activities in the iterable directly into the repository, without creating Activity objects.
        """
        raise NotImplementedError


class SubscriptionRepo(abc.ABC):
    """Repository interface for client's activities subscriptions.
    """

    @abc.abstractmethod
    def add(self, subscription: Subscription):
        """Adds the given *subscription* to the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, subscription: Subscription):
        """Removes the given *subscription* from the repository.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def register_transaction(self, subscription: Subscription, year: int, month: int, transaction: Transaction):
        """Registers the charge for the subscription.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_all(self, raw_subscriptions: Iterable[tuple]):
        """Adds the subscriptions in the iterable directly into the repository, without creating Subscription objects.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def register_raw_charges(self, raw_charges: Iterable[tuple]):
        """Links transactions with pairs (client, activity).
        """
        raise NotImplementedError


class TransactionRepo(abc.ABC):
    """Transaction repository interface.
    """

    def __init__(self, methods: Iterable[str] | None = None) -> None:
        self.methods = methods if methods is not None else []

    @abc.abstractmethod
    def from_data(
            self, id_: int, type_: str | None = None, when: date | None = None, raw_amount: str | None = None,
            method: str | None = None, raw_responsible: str | None = None, description: str | None = None,
            client: Client | None = None, balance_date: date | None = None
    ) -> Transaction:
        """If there is an existing Transaction with the given *id_*, return it. If not, and all others arguments aren't
        None, create a new Transaction and return it.
        """
        raise NotImplementedError

    # noinspection PyShadowingBuiltins
    @abc.abstractmethod
    def create(
            self, type: str, when: date, amount: Currency, method: str, responsible: String, description: str,
            client: Client | None = None
    ) -> Transaction:
        """Register a new transaction with the given information. This method must return the created transaction.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None,
            without_balance: bool = True, balance_date: date | None = None
    ) -> Generator[Transaction, None, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_to_balance(self, transaction: Transaction, balance_date: date):
        raise NotImplementedError

    @abc.abstractmethod
    def add_raw(self, raw: tuple) -> int:
        """Adds the transaction directly into the repository, without creating Transaction objects. This method should
        be used when the id of the raw transaction to insert is needed.

        Returns:
            Returns the id of the created transaction.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_all(self, raw_transactions: Iterable[tuple]):
        """Adds the transactions in the iterable directly into the repository, without creating Transaction objects.
        """
        raise NotImplementedError


class BalanceRepo(abc.ABC):
    def balance_done(self, when: date) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def add(self, when: date, responsible: String, balance: Balance):
        raise NotImplementedError

    @abc.abstractmethod
    def all(self, from_date: date, to_date: date) -> Generator[tuple[date, String, Balance], None, None]:
        raise NotImplementedError
