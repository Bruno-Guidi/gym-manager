from __future__ import annotations

import logging
from datetime import date
from typing import Generator, Iterable

from peewee import (SqliteDatabase, Model, IntegerField, CharField, DateField, BooleanField, TextField, ForeignKeyField,
                    CompositeKey, prefetch, Proxy, chunked)

from gym_manager.core import constants
from gym_manager.core.base import Client, Number, String, Currency, Activity, Transaction, Subscription, \
    OperationalError
from gym_manager.core.persistence import ClientRepo, ActivityRepo, TransactionRepo, SubscriptionRepo, LRUCache, \
    BalanceRepo, FilterValuePair

logger = logging.getLogger(__name__)

DATABASE_PROXY = Proxy()


def create_database(url: str):
    database = SqliteDatabase(url, pragmas={'foreign_keys': 1})
    DATABASE_PROXY.initialize(database)


def client_name_like(client, filter_value) -> bool:
    return client.cli_name.contains(filter_value)


class ClientTable(Model):
    dni = IntegerField(primary_key=True)
    cli_name = CharField()
    admission = DateField()
    telephone = CharField()
    direction = CharField()
    is_active = BooleanField()

    class Meta:
        database = DATABASE_PROXY


class SqliteClientRepo(ClientRepo):
    """Clients repository implementation based on Sqlite and peewee ORM.
    """

    # noinspection PyProtectedMember
    def __init__(self, activity_repo: ActivityRepo, transaction_repo: TransactionRepo, cache_len: int = 50) -> None:
        """If cache_len == 0, then there won't be any caching.
        """
        ClientTable._meta.database.create_tables([ClientTable])

        self.activity_repo = activity_repo
        self.transaction_repo = transaction_repo

        self._do_caching = cache_len > 0
        self.cache = LRUCache(key_types=(Number, int), value_type=Client, max_len=cache_len)

    def _from_record(self, raw) -> Client:
        client = Client(Number(raw.dni, min_value=constants.CLIENT_MIN_DNI, max_value=constants.CLIENT_MAX_DNI),
                        String(raw.cli_name, max_len=constants.CLIENT_NAME_CHARS),
                        raw.admission,
                        String(raw.telephone, optional=constants.CLIENT_TEL_OPTIONAL, max_len=constants.CLIENT_TEL_CHARS),
                        String(raw.direction, optional=constants.CLIENT_DIR_OPTIONAL, max_len=constants.CLIENT_DIR_CHARS),
                        raw.is_active)

        for sub_record in raw.subscriptions:
            activity = self.activity_repo.get(sub_record.activity_id)
            trans_record, transaction = sub_record.transaction, None
            if trans_record is not None:
                transaction = self.transaction_repo.from_record(
                    trans_record.id, trans_record.type, client, trans_record.when, trans_record.amount,
                    trans_record.method, trans_record.responsible, trans_record.description
                )
            client.add(Subscription(sub_record.when, client, activity, transaction))

        return client

    def get(self, dni: int | Number) -> Client:
        if not isinstance(dni, (Number, int)):
            raise TypeError(f"The argument 'dni' should be a 'Number' or 'int', not a '{type(dni)}'")
        if isinstance(dni, int):
            dni = Number(dni, min_value=constants.CLIENT_MIN_DNI, max_value=constants.CLIENT_MAX_DNI)
            logger.getChild(type(self).__name__).warning(f"Converting raw dni [dni={dni}] from int to Number.")

        if self._do_caching and dni in self.cache:
            return self.cache[dni]

        # If there is no caching or if the client isn't in the cache, query the db.
        clients_q = ClientTable.select().where(ClientTable.dni == dni.as_primitive())
        subs_q, trans_q = SubscriptionTable.select(), TransactionTable.select()
        # Because the clients are queried according to the pk, the query resulting from the prefetch will have only
        # one record.
        for record in prefetch(clients_q, subs_q, trans_q):
            client = self._from_record(record)
            if self._do_caching:
                self.cache[dni] = client
            return client

        # This is only reached if the previous query doesn't return anything.
        raise KeyError(f"There is no client with [dni={dni}].")

    def is_active(self, dni: Number) -> bool:
        """Checks if there is an active client with the given *dni*.
        """
        if not isinstance(dni, Number):
            raise TypeError(f"The argument 'dni' should be a 'Number', not a '{type(dni)}'")

        record = ClientTable.get_or_none(ClientTable.dni == dni.as_primitive())
        return record is not None and record.is_active

    def add(self, client: Client):
        if self.is_active(client.dni):
            raise KeyError(f"There is an existing client with the 'dni'={client.dni.as_primitive()}")

        if ClientTable.get_or_none(ClientTable.dni == client.dni.as_primitive()) is None:
            # The client doesn't exist in the table.
            logger.getChild(type(self).__name__).info(f"Adding new client [client={repr(client)}].")
        else:
            # The client exists in the table. Because previous check of self.is_active(args) failed, we can assume that
            # the client is inactive.
            logger.getChild(type(self).__name__).info(f"Activating existing client [client={repr(client)}].")

        ClientTable.replace(dni=client.dni.as_primitive(),
                            cli_name=client.name.as_primitive(),
                            admission=client.admission,
                            telephone=client.telephone.as_primitive(),
                            direction=client.direction.as_primitive(),
                            is_active=client.is_active).execute()
        if self._do_caching:
            self.cache[client.dni] = client

    def remove(self, client: Client):
        """Marks the given *client* as inactive, and delete its subscriptions.
        """
        ClientTable.replace(dni=client.dni.as_primitive(),
                            cli_name=client.name.as_primitive(),
                            admission=client.admission,
                            telephone=client.telephone.as_primitive(),
                            direction=client.direction.as_primitive(),
                            is_active=False).execute()
        if self._do_caching:
            self.cache.pop(client.dni)
        SubscriptionTable.delete().where(SubscriptionTable.client_id == client.dni.as_primitive()).execute()

    def update(self, client: Client):
        ClientTable.replace(dni=client.dni.as_primitive(),
                            cli_name=client.name.as_primitive(),
                            admission=client.admission,
                            telephone=client.telephone.as_primitive(),
                            direction=client.direction.as_primitive(),
                            is_active=True).execute()

        if self._do_caching:
            self.cache.move_to_front(client.dni)

    def all(
            self, page: int = 1, page_len: int | None = None, filters: tuple[FilterValuePair, ...] | None = None
    ) -> Generator[Client, None, None]:
        """Retrieve all the clients in the repository.

        Args:
            page: page to retrieve.
            page_len: clients per page. If None, retrieve all clients.
            filters: filters to apply.
        """
        clients_q = ClientTable.select()
        for filter_, value in filters:
            clients_q = clients_q.where(filter_.passes_in_repo(ClientTable, value))
        clients_q = clients_q.where(ClientTable.is_active)
        if page_len is not None:
            clients_q = clients_q.order_by(ClientTable.cli_name).paginate(page, page_len)

        subs_q, trans_q = SubscriptionTable.select(), TransactionTable.select()

        for record in prefetch(clients_q, subs_q, trans_q):
            client: Client
            if self._do_caching and record.dni in self.cache:
                client = self.cache[record.dni]
            else:
                # If there is no caching or if the client isn't in the cache, creates the client from the db record.
                client = self._from_record(record)
                if self._do_caching:
                    self.cache[client.dni] = client
                    logger.getChild(type(self).__name__).info(
                        f"Client with [dni={record.dni}] not in cache. The client will be created from raw data."
                    )
            yield client


class ActivityTable(Model):
    act_name = CharField(primary_key=True)
    price = CharField()
    charge_once = BooleanField()
    description = TextField()
    locked = BooleanField()

    class Meta:
        database = DATABASE_PROXY


class SqliteActivityRepo(ActivityRepo):
    """Activities repository implementation based on Sqlite and peewee ORM.
    """

    # noinspection PyProtectedMember
    def __init__(self, cache_len: int = 50) -> None:
        ActivityTable._meta.database.create_tables([ActivityTable])

        self._do_caching = cache_len > 0
        self.cache = LRUCache(key_types=(str, String), value_type=Activity, max_len=cache_len)

    # noinspection PyShadowingBuiltins
    def get(self, name: str | String) -> Activity:
        """Retrieves the activity with the given *name* in the repository, if it exists.

        Raises:
            KeyError if there is no activity with the given *id*.
        """
        if self._do_caching and name in self.cache:
            return self.cache[name]

        activity: Activity
        for record in ActivityTable.select().where(ActivityTable.act_name == name):
            activity = Activity(String(record.act_name, max_len=constants.ACTIVITY_NAME_CHARS),
                                Currency(record.price, max_currency=constants.MAX_CURRENCY),
                                record.charge_once,
                                String(record.description, optional=True, max_len=constants.ACTIVITY_DESCR_CHARS),
                                record.locked)
            if self._do_caching:
                self.cache[name] = activity
            return activity

        raise KeyError(f"There is no activity with the id '{name}'")

    def create(
            self, name: String, price: Currency, charge_once: bool, description: String, locked: bool = False
    ) -> Activity:
        record = ActivityTable.create(act_name=name.as_primitive(),
                                      price=str(price),
                                      charge_once=charge_once,
                                      description=description.as_primitive(),
                                      locked=locked)
        activity = Activity(name, price, charge_once, description)
        if self._do_caching:
            self.cache[record.act_name] = activity
        return activity

    def remove(self, activity: Activity, cascade_removing: bool = False):
        """Tries to remove the given *activity*.

        If *cascade_removing* is False, and there is at least one client registered in the activity, the removing will
        fail. If *cascade_removing* is True, the *activity* and all registrations for it will be removed.

        Args:
            activity: activity to remove.
            cascade_removing: if True, remove the activity and all registrations for it. If False, remove the activity
                only if it has zero registrations.
        """
        n_subs = self.n_subscribers(activity)
        if not cascade_removing and n_subs > 0:
            raise OperationalError(
                "An activity with active subscriptions cannot be removed, unless 'cascade_removing' is given",
                activity=activity, cascade_removing=cascade_removing, subscriptions=n_subs
            )

        if self._do_caching:
            self.cache.pop(activity.name)
        ActivityTable.delete_by_id(activity.name)

    def update(self, activity: Activity):
        ActivityTable.replace(act_name=activity.name.as_primitive(),
                              price=str(activity.price),
                              charge_once=activity.charge_once,
                              description=activity.description.as_primitive(),
                              locked=activity.locked).execute()

        if self._do_caching:
            self.cache.move_to_front(activity.name)

    def all(self) -> Generator[Activity, None, None]:
        for record in ActivityTable.select():
            activity: Activity
            if self._do_caching and record.act_name in self.cache:
                activity = self.cache[record.act_name]
            else:
                activity = Activity(String(record.act_name, max_len=constants.ACTIVITY_NAME_CHARS),
                                    Currency(record.price, max_currency=constants.MAX_CURRENCY),
                                    record.charge_once,
                                    String(record.description, optional=True, max_len=constants.ACTIVITY_DESCR_CHARS),
                                    record.locked)
                if self._do_caching:
                    self.cache[activity.name] = activity
                    logger.getChild(type(self).__name__).info(f"Activity with [activity.name={record.act_name}] not in "
                                                              f"cache. The activity will be created from raw data.")
            yield activity

    def n_subscribers(self, activity: Activity) -> int:
        """Returns the number of clients that are signed up in the given *activity*.
        """
        return SubscriptionTable.select().where(SubscriptionTable.activity == activity.name).count()


class TransactionTable(Model):
    id = IntegerField(primary_key=True)
    type = CharField()
    client = ForeignKeyField(ClientTable, backref="transactions", null=True)
    when = DateField()
    amount = CharField()
    method = CharField()
    responsible = CharField()
    description = CharField()

    class Meta:
        database = DATABASE_PROXY


class SqliteTransactionRepo(TransactionRepo):
    """Transaction repository implementation based on Sqlite and peewee ORM.
    """

    # noinspection PyProtectedMember
    def __init__(self, cache_len: int = 50) -> None:
        TransactionTable._meta.database.create_tables([TransactionTable])

        self.client_repo: ClientRepo | None = None

        self._do_caching = cache_len > 0
        self.cache = LRUCache(key_types=(int,), value_type=Transaction, max_len=cache_len)

    # noinspection PyShadowingBuiltins
    def from_record(self, id, type, client: Client, when, amount, method, responsible, description):
        """Creates a Transaction with the given data.
        """
        if self._do_caching and id in self.cache:
            return self.cache[id]

        transaction = Transaction(id,
                                  String(type, max_len=constants.TRANSACTION_TYPE_CHARS),
                                  when,
                                  Currency(amount, max_currency=constants.MAX_CURRENCY),
                                  String(method, max_len=constants.TRANSACTION_METHOD_CHARS),
                                  String(responsible, max_len=constants.TRANSACTION_RESP_CHARS),
                                  String(description, max_len=constants.TRANSACTION_DESCR_CHARS),
                                  client)
        if self._do_caching:
            self.cache[id] = transaction
        return transaction

    # noinspection PyShadowingBuiltins
    def create(
            self, type: String, when: date, amount: Currency, method: String, responsible: String, description: String,
            client: Client | None = None
    ) -> Transaction:
        """Register a new transaction with the given information. This method must return the created transaction.

        Raises:
            AttributeError if the client_repo attribute wasn't set before the execution of the method.
        """
        if self.client_repo is None:
            raise AttributeError("The 'client_repo' attribute in 'SqliteTransactionRepo' was not set.")

        record = TransactionTable.create(
            type=type.as_primitive(),
            client=ClientTable.get_by_id(client.dni.as_primitive()) if client is not None else None,
            when=when,
            amount=amount.as_primitive(),
            method=method.as_primitive(),
            responsible=responsible.as_primitive(),
            description=description.as_primitive()
        )

        transaction = Transaction(record.id, type, when, amount, method, responsible, description, client)
        if self._do_caching:
            self.cache[record.id] = transaction

        return transaction

    def all(self, page: int, page_len: int = 20, **filters) -> Generator[Transaction, None, None]:
        """Retrieves the transactions in the repository.

        Keyword Args:
            dict {str: tuple[Filter, str]}. The str key is the filter name, and the str in the tuple is the value to
                filter.

        Raises:
            AttributeError if the client_repo attribute wasn't set before the execution of the method.
        """
        if self.client_repo is None:
            raise AttributeError("The 'client_repo' attribute in 'SqliteTransactionRepo' was not set.")

        transactions_q = TransactionTable.select().join(ClientTable)
        for filter_, value in filters.values():
            transactions_q = transactions_q.where(filter_.passes_in_repo(TransactionTable, value))

        for record in transactions_q.paginate(page, page_len):
            client = None if record.client is None else self.client_repo.get(record.client_id)
            yield self.from_record(record.id, record.type, client, record.when, record.amount, record.method,
                                   record.responsible, record.description)


class SubscriptionTable(Model):
    when = DateField()
    client = ForeignKeyField(ClientTable, backref="subscriptions", on_delete="CASCADE")
    activity = ForeignKeyField(ActivityTable, backref="subscriptions", on_delete="CASCADE")
    transaction = ForeignKeyField(TransactionTable, backref="subscriptions_transactions", null=True)

    class Meta:
        database = DATABASE_PROXY
        primary_key = CompositeKey("client", "activity")


class SqliteSubscriptionRepo(SubscriptionRepo):
    """Subscriptions repository implementation based on Sqlite and peewee ORM.
    """

    # noinspection PyProtectedMember
    def __init__(self) -> None:
        SubscriptionTable._meta.database.create_tables([SubscriptionTable])

    def add(self, subscription: Subscription):
        SubscriptionTable.create(
            when=subscription.when,
            client=ClientTable.get_by_id(subscription.client.dni.as_primitive()),
            activity=ActivityTable.get_by_id(subscription.activity.name),
            transaction=None if subscription.transaction is None else TransactionTable.get_by_id(
                subscription.transaction.id)
        )

    def remove(self, subscription: Subscription):
        SubscriptionTable.delete().where((SubscriptionTable.client_id == subscription.client.dni.as_primitive())
                                         & (SubscriptionTable.activity_id == subscription.activity.name)).execute()

    def register_charge(self, client: Client, activity: Activity, transaction: Transaction):
        """Registers in the repository that the *client* was charged for the *activity*.
        """
        sub_record = SubscriptionTable.get_by_id((client.dni.as_primitive(), activity.name))
        trans_record = TransactionTable.get_by_id(transaction.id)
        sub_record.transaction = trans_record
        sub_record.save()


class BalanceTable(Model):
    when = DateField()
    transaction = ForeignKeyField(TransactionTable, backref="balance_register")

    class Meta:
        database = DATABASE_PROXY
        primary_key = None


class SqliteBalanceRepo(BalanceRepo):
    def __init__(self):
        BalanceTable._meta.database.create_tables([BalanceTable])

    def balance_done(self, when: date) -> bool:
        return BalanceTable.select().where(BalanceTable.when == when).count()

    def add_all(self, when: date, transactions: Iterable[Transaction]):
        with DATABASE_PROXY.atomic():
            BalanceTable.delete().where(BalanceTable.when == when)  # Deletes existing balance, if it exists.

            for batch in chunked(transactions, 30):  # Saves the new balance.
                batch = [(when, transaction.id) for transaction in batch]
                BalanceTable.insert_many(batch, fields=[BalanceTable.when, BalanceTable.transaction_id]).execute()
