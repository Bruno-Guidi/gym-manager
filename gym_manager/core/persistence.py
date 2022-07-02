import abc
from collections import OrderedDict
from datetime import date
from typing import Generator, Type, Any, Iterable, TypeAlias

from gym_manager.core.base import Client, Activity, Currency, String, Number, Subscription, Transaction, Filter


FilterValuePair: TypeAlias = tuple[Filter, str]


class LRUCache:

    def __init__(self, key_types: tuple[Type, ...], value_type: Type, max_len: int) -> None:
        self.key_types = key_types
        self.value_type = value_type

        self.max_len = max_len
        self._cache = OrderedDict()

    def __len__(self) -> int:
        return len(self._cache)

    def __getitem__(self, key: Any) -> Any:
        if not isinstance(key, self.key_types):
            raise TypeError(f"The LRUCache expected a '{self.key_types}' as key, but received a '{type(key)}'.")
        if key not in self._cache.keys():
            raise KeyError(f"The LRUCache does not contains the key '{key}'.")

        self._cache.move_to_end(key, last=False)
        return self._cache[key]

    def __setitem__(self, key: Any, value: Any):
        if not isinstance(key, self.key_types):
            raise TypeError(f"The LRUCache expected a '{self.key_types}' as key, but received a '{type(key)}'.")
        if not isinstance(value, self.value_type):
            raise TypeError(f"The LRUCache expected a '{self.value_type}' as value, but received a '{type(value)}'.")

        self._cache[key] = value
        self._cache.move_to_end(key, last=False)
        if len(self._cache) > self.max_len:  # Removes the LRU key in case the cache len is exceeded.
            self._cache.popitem(last=True)

    def pop(self, key: Any):
        if not isinstance(key, self.key_types):
            raise TypeError(f"The LRUCache expected a '{self.key_types}' as key, but received a '{type(key)}'.")
        if key not in self._cache.keys():
            raise KeyError(f"The LRUCache does not contains the key '{key}'.")
        self._cache.pop(key)

    def __iter__(self):
        yield from iter(self._cache.keys())

    def move_to_front(self, key: Any):
        if not isinstance(key, self.key_types):
            raise TypeError(f"The LRUCache expected a '{self.key_types}' as key, but received a '{type(key)}'.")
        if key not in self._cache.keys():
            raise KeyError(f"The LRUCache does not contains the key '{key}'.")
        self._cache.move_to_end(key, last=False)


class ClientRepo(abc.ABC):
    """Clients repository interface.
    """

    @abc.abstractmethod
    def get(self, dni: int | Number) -> Client:
        """Returns the client with the given *dni*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_active(self, dni: Number) -> bool:
        """Checks if there is an active client with the given *dni*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add(self, client: Client):
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
            self, page: int = 1, page_len: int | None = None, filters: tuple[FilterValuePair, ...] | None = None
    ) -> Generator[Client, None, None]:
        """Retrieve all the clients in the repository.

        Args:
            page: page to retrieve.
            page_len: clients per page. If None, retrieve all clients.
            filters: filters to apply.
        """
        raise NotImplementedError


class ActivityRepo(abc.ABC):
    """Activities repository interface.
    """

    @abc.abstractmethod
    def get(self, name: str | String) -> Activity:
        """Retrieves the activity with the given *id* in the repository, if it exists.

        Raises:
            KeyError if there is no activity with the given *id*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def create(
            self, name: String, price: Currency, charge_once: bool, description: String, locked: bool = False
    ) -> Activity:
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
    def n_subscribers(self, activity: Activity) -> int:
        """Returns the number of clients subscribed in the given *activity*.
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
    def register_charge(self, client: Client, activity: Activity, transaction: Transaction):
        """Registers in the repository that the client was charged for the activity subscription.
        """
        raise NotImplementedError


class TransactionRepo(abc.ABC):
    """Transaction repository interface.
    """

    # noinspection PyShadowingBuiltins
    @abc.abstractmethod
    def from_record(self, id, type, client: Client, when, amount, method, responsible, description):
        """Creates a Transaction with the given data.
        """
        raise NotImplementedError

    # noinspection PyShadowingBuiltins
    @abc.abstractmethod
    def create(
            self, type: String, when: date, amount: Currency, method: String, responsible: String, description: String,
            client: Client | None = None
    ) -> Transaction:
        """Register a new transaction with the given information. This method must return the created transaction.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def all(self, page: int, page_len: int = 20, **filters) -> Generator[Transaction, None, None]:
        """Retrieves the transactions in the repository.

        Keyword Args:
            dict {str: tuple[Filter, str]}. The str key is the filter name, and the str in the tuple is the value to
                filter.
        """
        raise NotImplementedError


class BalanceRepo(abc.ABC):
    def balance_done(self, when: date) -> bool:
        raise NotImplementedError

    def add_all(self, when: date, transactions: Iterable[Transaction]):
        raise NotImplementedError
