from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Generator, Iterable

from peewee import (
    SqliteDatabase, Model, IntegerField, CharField, DateField, BooleanField, TextField, ForeignKeyField,
    CompositeKey, prefetch, Proxy, JOIN, DateTimeField, chunked)
from playhouse.sqlite_ext import JSONField

from gym_manager.core.base import (
    Client, Number, String, Currency, Activity, Transaction, Subscription,
    Balance)
from gym_manager.core.persistence import (
    ClientRepo, ActivityRepo, TransactionRepo, SubscriptionRepo, LRUCache,
    BalanceRepo, FilterValuePair, PersistenceError, ClientView)
from gym_manager.core.security import log_responsible, SecurityRepo, Responsible, Action

logger = logging.getLogger(__name__)

DATABASE_PROXY = Proxy()


def create_database(url: str):
    database = SqliteDatabase(url, pragmas={'foreign_keys': 1})
    DATABASE_PROXY.initialize(database)


def client_name_like(client, filter_value) -> bool:
    return client.cli_name.contains(filter_value)


class ClientTable(Model):
    id = IntegerField(primary_key=True)
    dni = IntegerField(unique=True, null=True)
    cli_name = CharField()
    admission = DateField()
    birth_day = DateField()
    is_active = BooleanField()

    class Meta:
        database = DATABASE_PROXY


class SqliteClientRepo(ClientRepo):
    """Clients repository implementation based on Sqlite and peewee ORM.
    """

    def __init__(self, activity_repo: ActivityRepo, transaction_repo: TransactionRepo, cache_len: int = 50) -> None:
        DATABASE_PROXY.create_tables([ClientTable, ActivityTable, SubscriptionTable, TransactionTable])

        self.activity_repo = activity_repo
        self.transaction_repo = transaction_repo

        self.cache = LRUCache(int, value_type=Client, max_len=cache_len)

        # Links this repo with the ClientView, so they can be refreshed after a client change.
        ClientView.repository = self
        self._views: dict[int, ClientView] = {}

    def is_active(self, dni: Number) -> bool:
        """Checks if there is an active client with the given *dni*.
        """
        if not isinstance(dni, Number):
            raise TypeError(f"The argument 'dni' should be a 'Number', not a '{type(dni)}'")

        if dni.as_primitive() is None:
            # If the client doesn't have a dni, then there won't be any active or inactive client that matches with it.
            return False

        record = ClientTable.get_or_none(ClientTable.dni == dni.as_primitive())
        return record is not None and record.is_active

    def create(self, name: String, admission: date, birthday: date, dni: Number) -> Client:
        if dni.as_primitive() is not None and self.is_active(dni):
            raise PersistenceError(f"There is an existing client with [client.dni={dni}].")

        record = ClientTable.get_or_none(ClientTable.dni == dni.as_primitive()) if dni.as_primitive() is not None else None
        if record is None:
            # record will be None if *dni* is None or if there is no client in the table whose dni matches it.
            logger.getChild(type(self).__name__).info(f"Creating client [client.dni={dni}].")
            record = ClientTable.create(dni=dni.as_primitive(), cli_name=name.as_primitive(), admission=admission,
                                        birth_day=birthday, is_active=True)
        else:
            # There is an inactive client whose dni matches with the received one.
            logger.getChild(type(self).__name__).info(f"Reactivating client [client.dni={dni}].")
            ClientTable.replace(id=record.id, dni=dni.as_primitive(), cli_name=name.as_primitive(), admission=admission,
                                birth_day=birthday, is_active=True).execute()

        client = Client(record.id, name, admission, birthday, dni)
        self.cache[client.id] = client

        if client.dni.as_primitive() is not None:
            for view in self._views.values():
                # If there is a view whose dni matches with the dni of the new (or activated client), update it.
                if view.dni is not None and client.dni == view.dni:
                    view.dni = client.dni
                    view.name = client.name
                    break

        return client

    @log_responsible(action_tag="remove_client", to_str=lambda client: f"Eliminar cliente {client.name}")
    def remove(self, client: Client):
        """Marks the given *client* as inactive, and delete its subscriptions.
        """
        record = ClientTable.get_by_id(client.id)
        record.is_active = False
        record.save()
        self.cache.pop(client.id)
        # The view isn't removed from the view cache, because it still may be used by a Transaction or a Booking.
        SubscriptionTable.delete().where(SubscriptionTable.client_id == client.id).execute()

        return client

    def update(self, client: Client):
        record = ClientTable.get_by_id(client.id)

        if client.dni.as_primitive() is not None and client.id != record.id and self.is_active(client.dni):
            raise PersistenceError(f"There is an existing client with [client.dni={client.dni}].")

        # IMPORTANT. The replace method deletes records that reference the one being updated, even if the pk isn't
        # changed.
        record.dni = client.dni.as_primitive()
        record.cli_name = client.name.as_primitive()
        record.save()

        if client.id in self._views:  # Refreshes the view of the updated client, if there is one.
            self._views[client.id].dni = client.dni
            self._views[client.id].name = client.name

    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[Client, None, None]:
        """Retrieve all the clients in the repository.

        Args:
            page: page to retrieve.
            page_len: clients per page. If None, retrieve all clients.
            filters: filters to apply.
        """
        clients_q = ClientTable.select()
        clients_q = clients_q.where(ClientTable.is_active)  # Retrieve only active clients.

        if filters is not None:  # Apply given filters.
            for filter_, value in filters:
                clients_q = clients_q.where(filter_.passes_in_repo(ClientTable, value))

        if page_len is not None:
            clients_q = clients_q.order_by(ClientTable.cli_name).paginate(page, page_len)

        # Query that contains subs that don't have a charge associated and subs that do.
        predicate = (SubscriptionTable.client_id == SubscriptionCharge.client_id) & (SubscriptionTable.activity_id ==
                                                                                     SubscriptionCharge.activity_id)
        subscriptions_q = SubscriptionTable.select().join(SubscriptionCharge, JOIN.LEFT_OUTER, on=predicate)
        for record in prefetch(clients_q, subscriptions_q, TransactionTable.select()):
            if record.id not in self.cache:
                logger.getChild(type(self).__name__).info(f"Creating Client [client.id={record.id}] from queried data.")
                client = Client(record.id, String(record.cli_name), record.admission, record.birth_day,
                                Number(record.dni if record.dni is not None else ""))
                self.cache[record.id] = client
                subs = {}
                for sub_record in record.subscriptions:
                    subs[sub_record.activity_id] = Subscription(sub_record.when, client,
                                                                self.activity_repo.get(String(sub_record.activity_id)))
                for sub_charge in record.subscriptions_charges:
                    year, month = sub_charge.when.year, sub_charge.when.month
                    trans_record = sub_charge.transaction
                    subs[sub_charge.activity_id].add_transaction(
                        year, month, self.transaction_repo.from_data(
                            trans_record.id, trans_record.type, trans_record.when, trans_record.amount,
                            trans_record.method, trans_record.responsible, trans_record.description, client,
                            trans_record.balance_id
                        )
                    )
                for subscription in subs.values():
                    client.add(subscription)
            yield self.cache[record.id]

    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        """Counts the number of clients in the repository.
        """
        clients_q = ClientTable.select("1").where(ClientTable.is_active)
        if filters is not None:
            for filter_, value in filters:
                clients_q = clients_q.where(filter_.passes_in_repo(ClientTable, value))
        return clients_q.count()

    def register_view(self, view: ClientView):
        self._views[view.id] = view

    def add_all(self, raw_clients: Iterable[tuple]):
        """Adds the clients in the iterable directly into the repository, without creating Client objects.
        """
        with DATABASE_PROXY.atomic():
            for batch in chunked(raw_clients, 256):
                ClientTable.insert_many(batch, fields=[ClientTable.id, ClientTable.cli_name, ClientTable.admission,
                                                       ClientTable.birth_day, ClientTable.is_active]).execute()


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

    def __init__(self, cache_len: int = 50) -> None:
        DATABASE_PROXY.create_tables([ActivityTable, SubscriptionTable, SubscriptionCharge])

        self.cache = LRUCache(String, Activity, max_len=cache_len)

    def add(self, activity: Activity):
        """Adds *activity* to the repository.

        Raises:
            PersistenceError if there is an existing activity with *activity.name*.
        """
        if self.exists(activity.name):
            raise PersistenceError(f"An activity with [activity.name={activity.name}] already exists.")

        ActivityTable.create(act_name=activity.name.as_primitive(), price=str(activity.price),
                             charge_once=activity.charge_once, description=activity.description.as_primitive(),
                             locked=activity.locked)
        self.cache[activity.name] = activity

    def exists(self, name: String) -> bool:
        if name in self.cache:  # First search in the cache.
            return True

        return ActivityTable.get_or_none(act_name=name) is not None  # Then search in the db.

    def get(self, name: String) -> Activity:
        """Retrieves the activity with the given *name* in the repository, if it exists.

        Raises:
            KeyError if there is no activity with the given *name*.
        """
        if name in self.cache:
            return self.cache[name]

        record = ActivityTable.get_or_none(act_name=name)
        if record is None:
            raise KeyError(f"There is no activity with the id '{name}'")

        # The activity description was validated when it was created.
        self.cache[name] = Activity(name, Currency(record.price), String(record.description, optional=True),
                                    record.charge_once, record.locked)
        logger.getChild(type(self).__name__).info(f"Creating Activity [activity.name={name}] from queried data.")
        return self.cache[name]

    @log_responsible(action_tag="remove_activity", to_str=lambda activity: f"Eliminar actividad {activity.name}")
    def remove(self, activity: Activity):
        """Removes the given *activity*.

        Raises:
            PersistenceError: if *activity* is locked.
        """
        if activity.locked:
            raise PersistenceError(f"The [activity.name={activity.name}] cannot be removed because its locked.")

        self.cache.pop(activity.name)
        ActivityTable.delete_by_id(activity.name)

        return activity

    def update(self, activity: Activity):
        record = ActivityTable.get_by_id(activity.name.as_primitive())
        record.price = activity.price.as_primitive()
        record.description = activity.description.as_primitive()
        record.save()

    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[Activity, None, None]:
        activities_q = ActivityTable.select()
        if filters is not None:
            for filter_, value in filters:
                activities_q = activities_q.where(filter_.passes_in_repo(ActivityTable, value))

        if page_len is not None:
            activities_q = activities_q.order_by(ActivityTable.act_name).paginate(page, page_len)

        for record in activities_q:
            activity: Activity
            # The activity name and description were validated when it was created.
            activity_name = String(record.act_name)
            if activity_name not in self.cache:
                logger.getChild(type(self).__name__).info(f"Creating Activity [activity.name={activity_name}] from "
                                                          f"queried data.")
                self.cache[activity_name] = Activity(
                    activity_name, Currency(record.price), String(record.description, optional=True),
                    record.charge_once, record.locked
                )
            yield self.cache[activity_name]

    def n_subscribers(self, activity: Activity) -> int:
        """Returns the number of clients that are signed up in the given *activity*.
        """
        return SubscriptionTable.select().where(SubscriptionTable.activity == activity.name).count()

    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        """Counts the number of activities in the repository.
        """
        activities_q = ActivityTable.select("1")
        if filters is not None:
            for filter_, value in filters:
                activities_q = activities_q.where(filter_.passes_in_repo(ActivityTable, value))
        return activities_q.count()

    def add_all(self, raw_activities: Iterable[tuple]):
        """Adds the activities in the iterable directly into the repository, without creating Activity objects.
        """
        with DATABASE_PROXY.atomic():
            for batch in chunked(raw_activities, 50):
                ActivityTable.insert_many(batch, fields=[ActivityTable.act_name, ActivityTable.price,
                                                         ActivityTable.charge_once, ActivityTable.description,
                                                         ActivityTable.locked]).execute()


class BalanceTable(Model):
    when = DateField(primary_key=True)
    responsible = CharField()
    balance_dict = JSONField()

    class Meta:
        database = DATABASE_PROXY


class SqliteBalanceRepo(BalanceRepo):
    def __init__(self, transaction_repo: TransactionRepo):
        DATABASE_PROXY.create_tables([BalanceTable])

        self.transaction_repo = transaction_repo
        self.client_view_cache = LRUCache(int, ClientView, max_len=64)

    def balance_done(self, when: date) -> bool:
        return BalanceTable.get_or_none(BalanceTable.when == when) is not None

    @staticmethod
    def balance_to_json(balance: Balance):
        _balance = {}
        for type_, type_balance in balance.items():
            _balance[str(type_)] = {}
            for method, method_balance in type_balance.items():
                _balance[str(type_)][str(method)] = str(method_balance)
        return _balance

    @staticmethod
    def json_to_balance(json_balance: dict):
        _balance = {}
        for type_, type_balance in json_balance.items():
            _balance[type_] = {}
            for method, method_balance in type_balance.items():
                _balance[type_][method] = Currency(method_balance)
        return _balance

    def add(self, when: date, responsible: String, balance: Balance):
        BalanceTable.create(when=when, responsible=responsible.as_primitive(),
                            balance_dict=self.balance_to_json(balance))

    def all(
            self, from_date: date, to_date: date
    ) -> Generator[tuple[date, String, Balance, list[Transaction]], None, None]:
        balance_q = BalanceTable.select().where(BalanceTable.when >= from_date, BalanceTable.when <= to_date)
        client_q = ClientTable.select(ClientTable.dni, ClientTable.cli_name)

        for record in prefetch(balance_q.order_by(BalanceTable.when.desc()), TransactionTable.select(), client_q):
            transactions = []
            for transaction_record in record.transactions:
                client_record, client = transaction_record.client, None
                if client_record is not None:
                    if client_record.id in self.client_view_cache:
                        client = self.client_view_cache[client_record.id]
                    else:
                        client = ClientView(client_record.id, String(client_record.cli_name),
                                            created_by="SqliteBalanceRepo.all",
                                            dni=Number(client_record.dni if client_record.dni is not None else ""))

                transactions.append(self.transaction_repo.from_data(
                    transaction_record.id, transaction_record.type, transaction_record.when,
                    transaction_record.amount, transaction_record.method, transaction_record.responsible,
                    transaction_record.description, client, transaction_record.balance_id
                ))
            yield record.when, String(record.responsible), self.json_to_balance(record.balance_dict), transactions


class TransactionTable(Model):
    id = IntegerField(primary_key=True)
    type = CharField()
    client = ForeignKeyField(ClientTable, backref="transactions", null=True)
    when = DateField()
    amount = CharField()
    method = CharField()
    responsible = CharField()
    description = CharField()
    balance = ForeignKeyField(BalanceTable, backref="transactions", null=True, on_delete="SET NULL")

    class Meta:
        database = DATABASE_PROXY


class SqliteTransactionRepo(TransactionRepo):
    """Transaction repository implementation based on Sqlite and peewee ORM.
    """

    # noinspection PyProtectedMember
    def __init__(self, methods: Iterable[str] | None = None, cache_len: int = 50) -> None:
        super().__init__(methods)
        DATABASE_PROXY.create_tables([TransactionTable])

        self.cache = LRUCache(int, Transaction, max_len=cache_len)
        # In the worst case the cache can store as many clients views as transactions, supposing each transaction has
        # a different client.
        self.client_view_cache = LRUCache(int, ClientView, max_len=cache_len)

    # ToDo make arguments mandatory.
    def from_data(
            self, id_: int, type_: str | None = None, when: date | None = None, raw_amount: str | None = None,
            method: str | None = None, raw_responsible: str | None = None, description: str | None = None,
            client: Client | None = None, balance_date: date | None = None
    ) -> Transaction:
        """If there is an existing Transaction with the given *id_*, return it. If not, and all others arguments aren't
        None, create a new Transaction and return it.
        """
        if id_ in self.cache:
            return self.cache[id_]

        self.cache[id_] = Transaction(id_, type_, when, Currency(raw_amount), method, String(raw_responsible),
                                      description, client, balance_date)
        logger.getChild(type(self).__name__).info(f"Creating Transaction [transaction.id={id_}] from queried data.")
        return self.cache[id_]

    # noinspection PyShadowingBuiltins
    def create(
            self, type: str, when: date, amount: Currency, method: str, responsible: String, description: str,
            client: Client | None = None
    ) -> Transaction:
        """Register a new transaction with the given information. This method must return the created transaction.
        """
        # There is no need to check the cache because the Transaction is being created, it didn't exist before.
        record = TransactionTable.create(type=type, client=client.id if client is not None else None, when=when,
                                         amount=amount.as_primitive(), method=method,
                                         responsible=responsible.as_primitive(), description=description)

        self.cache[record.id] = Transaction(record.id, type, when, amount, method, responsible, description, client)
        return self.cache[record.id]

    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None,
            without_balance: bool = True, balance_date: date | None = None
    ) -> Generator[Transaction, None, None]:
        transactions_q = TransactionTable.select(TransactionTable, ClientTable.cli_name, ClientTable.dni)

        if without_balance:  # Retrieve transactions that weren't linked to a balance.
            transactions_q = transactions_q.where(TransactionTable.balance.is_null())
        if balance_date is not None:  # Retrieve transactions linked to the given balance.
            transactions_q = transactions_q.where(TransactionTable.balance == balance_date)

        # The left outer join is needed to include some of ClientTable attributes required by a transaction.
        transactions_q = transactions_q.join(ClientTable, JOIN.LEFT_OUTER)

        if filters is not None:  # Generic filters.
            for filter_, value in filters:
                transactions_q = transactions_q.where(filter_.passes_in_repo(TransactionTable, value))

        if page_len is not None:
            transactions_q = transactions_q.paginate(page, page_len)

        for record in transactions_q:
            client_record, client = record.client, None
            if client_record is not None:
                if client_record.id in self.client_view_cache:
                    client = self.client_view_cache[client_record.id]
                else:
                    client = ClientView(client_record.id, String(client_record.cli_name),
                                        created_by="SqliteTransactionRepo.all",
                                        dni=Number(client_record.dni if client_record.dni is not None else ""))
            yield self.from_data(record.id, record.type, record.when, record.amount, record.method, record.responsible,
                                 record.description, client, record.balance)

    def bind_to_balance(self, transaction: Transaction, balance_date: date):
        record = TransactionTable.get_by_id(transaction.id)
        record.balance_id = balance_date
        record.save()

    def add_raw(self, raw: tuple) -> int:
        """Adds the transaction directly into the repository, without creating Transaction objects. This method should
        be used when the id of the raw transaction to insert is needed.

        Returns:
            Returns the id of the created transaction.
        """
        return TransactionTable.create(type=raw[0], client=raw[1], when=raw[2], amount=raw[3], method=raw[4],
                                       responsible=raw[5], description=raw[6])

    def add_all(self, raw_transactions: Iterable[tuple]):
        """Adds the transactions in the iterable directly into the repository, without creating Transaction objects.
        """
        with DATABASE_PROXY.atomic():
            for batch in chunked(raw_transactions, 1024):
                TransactionTable.insert_many(
                    batch, fields=[TransactionTable.type, TransactionTable.client_id, TransactionTable.when,
                                   TransactionTable.amount, TransactionTable.method, TransactionTable.responsible,
                                   TransactionTable.description]
                ).execute()


class SubscriptionTable(Model):
    when = DateField()
    client = ForeignKeyField(ClientTable, backref="subscriptions", on_delete="CASCADE")
    activity = ForeignKeyField(ActivityTable, backref="subscriptions", on_delete="CASCADE")

    class Meta:
        database = DATABASE_PROXY
        primary_key = CompositeKey("client", "activity")


class SubscriptionCharge(Model):
    when = DateField()
    client = ForeignKeyField(ClientTable, backref="subscriptions_charges", on_delete="CASCADE")
    activity = ForeignKeyField(ActivityTable, backref="subscriptions_charges", on_delete="CASCADE")
    transaction = ForeignKeyField(TransactionTable, backref="subscriptions_transactions")

    class Meta:
        database = DATABASE_PROXY
        primary_key = CompositeKey("when", "client", "activity")


class SqliteSubscriptionRepo(SubscriptionRepo):
    """Subscriptions repository implementation based on Sqlite and peewee ORM.
    """

    # noinspection PyProtectedMember
    def __init__(self) -> None:
        DATABASE_PROXY.create_tables([SubscriptionTable, SubscriptionCharge])

    def add(self, subscription: Subscription):
        SubscriptionTable.create(when=subscription.when, client_id=subscription.client.id,
                                 activity_id=subscription.activity.name.as_primitive())

    def remove(self, subscription: Subscription):
        SubscriptionTable.delete().where((SubscriptionTable.client_id == subscription.client.id)
                                         & (SubscriptionTable.activity_id == subscription.activity.name)).execute()
        SubscriptionCharge.delete().where((SubscriptionCharge.client_id == subscription.client.id)
                                          & (SubscriptionCharge.activity_id == subscription.activity.name)).execute()

    def register_transaction(self, subscription: Subscription, year: int, month: int, transaction: Transaction):
        """Registers the charge for the subscription.
        """
        SubscriptionCharge.create(when=date(year, month, 1), client_id=subscription.client.id,
                                  activity_id=subscription.activity.name.as_primitive(), transaction_id=transaction.id)

    def add_all(self, raw_subscriptions: Iterable[tuple]):
        """Adds the subscriptions in the iterable directly into the repository, without creating Subscription
        objects.
        """
        with DATABASE_PROXY.atomic():
            for batch in chunked(raw_subscriptions, 1024):
                SubscriptionTable.insert_many(batch, fields=[SubscriptionTable.when, SubscriptionTable.client,
                                                             SubscriptionTable.activity_id]).execute()

    def register_raw_charges(self, raw_charges: Iterable[tuple]):
        """Links transactions with pairs (client, activity).
        """
        with DATABASE_PROXY.atomic():
            for batch in chunked(raw_charges, 1024):
                SubscriptionCharge.insert_many(batch, fields=[SubscriptionCharge.when, SubscriptionCharge.client_id,
                                                              SubscriptionCharge.activity_id,
                                                              SubscriptionCharge.transaction_id]).execute()


class ResponsibleTable(Model):
    resp_code = CharField(primary_key=True)
    resp_name = CharField()

    class Meta:
        database = DATABASE_PROXY


class ActionTable(Model):
    id = IntegerField(primary_key=True)
    when = DateTimeField()
    responsible = ForeignKeyField(ResponsibleTable, backref="actions")
    action_tag = CharField()
    action_name = CharField()

    class Meta:
        database = DATABASE_PROXY


class SqliteSecurityRepo(SecurityRepo):

    def __init__(self) -> None:
        DATABASE_PROXY.create_tables([ResponsibleTable, ActionTable])

    def responsible(self) -> Generator[Responsible, None, None]:
        for record in ResponsibleTable.select():
            yield Responsible(String(record.resp_name), String(record.resp_code))

    def add_responsible(self, *responsible):
        for resp in responsible:
            ResponsibleTable.replace(resp_code=resp.code, resp_name=resp.name).execute()

    def log_action(self, when: datetime, responsible: Responsible, action_tag: str, action_name: str):
        ActionTable.create(when=when, responsible_id=responsible.code.as_primitive(), action_tag=action_tag,
                           action_name=action_name)

    def actions(self, page: int = 1, page_len: int = 20) -> Generator[Action, None, None]:
        actions_q = ActionTable.select().order_by(ActionTable.when.desc())
        actions_q = actions_q.paginate(page, page_len)

        for record in prefetch(actions_q, ResponsibleTable.select()):
            resp = Responsible(String(record.responsible.resp_name), String(record.responsible.resp_code))
            yield record.when, resp, record.action_tag, record.action_name
