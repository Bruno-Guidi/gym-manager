from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Generator, Iterable

from peewee import (
    SqliteDatabase, Model, IntegerField, CharField, DateField, BooleanField, TextField, ForeignKeyField,
    CompositeKey, prefetch, Proxy, JOIN, DateTimeField)
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
    telephone = CharField()
    direction = CharField()
    is_active = BooleanField()

    class Meta:
        database = DATABASE_PROXY


class SqliteClientRepo(ClientRepo):
    """Clients repository implementation based on Sqlite and peewee ORM.
    """

    def __init__(self, activity_repo: ActivityRepo, transaction_repo: TransactionRepo, cache_len: int = 50) -> None:
        DATABASE_PROXY.create_tables([ClientTable])

        self.activity_repo = activity_repo
        self.transaction_repo = transaction_repo

        self.cache = LRUCache(int, value_type=Client, max_len=cache_len)

        # Links this repo with the ClientView, so they can be refreshed after a client change.
        ClientView.repository = self
        self._views: dict[Number, ClientView] = {}

    def is_active(self, dni: Number | None) -> bool:
        """Checks if there is an active client with the given *dni*.
        """
        if dni is None:
            # If the client doesn't have a dni, then there won't be any active or inactive client that matches with it.
            return False
        if not isinstance(dni, Number):
            raise TypeError(f"The argument 'dni' should be a 'Number', not a '{type(dni)}'")

        record = ClientTable.get_or_none(ClientTable.dni == dni.as_primitive())
        return record is not None and record.is_active

    def create(
            self, name: String, admission: date, birthday: date, telephone: String, direction: String,
            dni: Number | None = None
    ) -> Client:
        if dni is not None and self.is_active(dni):
            raise PersistenceError(f"There is an existing client with [client.dni={dni}].")

        record = ClientTable.get_or_none(ClientTable.dni == dni.as_primitive()) if dni is not None else None
        if record is None:
            # record will be None if *dni* is None or if there is no client in the table whose dni matches it.
            logger.getChild(type(self).__name__).info(f"Creating client [client.dni={dni}].")
            record = ClientTable.create(dni=dni.as_primitive() if dni is not None else None,
                                        cli_name=name.as_primitive(), admission=admission, birth_day=birthday,
                                        telephone=telephone.as_primitive(), direction=direction.as_primitive(),
                                        is_active=True)
        else:
            # There is an inactive client whose dni matches with the received one.
            logger.getChild(type(self).__name__).info(f"Reactivating client [client.dni={dni}].")
            ClientTable.replace(id=record.id, dni=dni.as_primitive() if dni is not None else None,
                                cli_name=name.as_primitive(), admission=admission, birth_day=birthday,
                                telephone=telephone.as_primitive(), direction=direction.as_primitive(),
                                is_active=True).execute()

        client = Client(record.id, name, admission, birthday, telephone, direction, dni)
        self.cache[client.id] = client
        if client.id in self._views:
            self._views[client.id].name = client.name

        return client

    @log_responsible(action_tag="remove_client", to_str=lambda client: f"Eliminar cliente {client.name}")
    def remove(self, client: Client):
        """Marks the given *client* as inactive, and delete its subscriptions.
        """
        ClientTable.replace(id=client.id, dni=client.dni.as_primitive() if client.dni is not None else None,
                            cli_name=client.name.as_primitive(), admission=client.admission, birth_day=client.birth_day,
                            telephone=client.telephone.as_primitive(), direction=client.direction.as_primitive(),
                            is_active=False).execute()
        self.cache.pop(client.id)
        self._views.pop(client.id, None)
        # ToDo invoke corresponding method of SubscriptionRepo.
        # SubscriptionTable.delete().where(SubscriptionTable.client_id == client.id).execute()

        return client

    def update(self, client: Client):
        ClientTable.replace(id=client.id, dni=client.dni.as_primitive() if client.dni is not None else None,
                            cli_name=client.name.as_primitive(), admission=client.admission, birth_day=client.birth_day,
                            telephone=client.telephone.as_primitive(), direction=client.direction.as_primitive(),
                            is_active=True).execute()

        if client.dni in self._views:  # Refreshes the view of the updated client, if there is one.
            self._views[client.dni].name = client.name

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

        for record in prefetch(clients_q, SubscriptionTable.select(), TransactionTable.select()):
            if record.id not in self.cache:
                logger.getChild(type(self).__name__).info(f"Creating Client [client.id={record.id}] from queried data.")
                client = Client(record.id, String(record.cli_name), record.admission, record.birth_day,
                                String(record.telephone), String(record.direction),
                                Number(record.dni) if record.dni is not None else None)
                self.cache[record.id] = client
                for sub_record in record.subscriptions:
                    activity = self.activity_repo.get(String(sub_record.activity_id))
                    trans_record, transaction = sub_record.transaction, None
                    if trans_record is not None:
                        transaction = self.transaction_repo.from_data(
                            trans_record.id, trans_record.type, trans_record.when, trans_record.amount,
                            trans_record.method,
                            trans_record.responsible, trans_record.description, client, trans_record.balance_id
                        )
                    client.add(Subscription(sub_record.when, client, activity, transaction))
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
        self._views[view.dni] = view


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
        DATABASE_PROXY.create_tables([ActivityTable, SubscriptionTable])

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
        ActivityTable.replace(act_name=activity.name.as_primitive(),
                              price=str(activity.price),
                              charge_once=activity.charge_once,
                              description=activity.description.as_primitive(),
                              locked=activity.locked).execute()

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
        self.client_cache = LRUCache(Number, ClientView, max_len=64)

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
                client: ClientView | None = None
                if transaction_record.client is not None:
                    dni = Number(transaction_record.client.dni)
                    if dni not in self.client_cache:
                        self.client_cache[dni] = ClientView(dni, String(transaction_record.client.cli_name),
                                                            created_by="SqliteBalanceRepo.all")
                    client = self.client_cache[dni]

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
        self.client_cache = LRUCache(Number, ClientView, max_len=64)

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

        if not all((type_, when, raw_amount, method, raw_responsible, description)):  # Client and balance_date are opt.
            none_args = {(arg.__name__, arg) for arg in (type_, when, raw_amount, method, raw_responsible, description)
                         if arg is None}
            raise PersistenceError(f"Failed to create a 'Transaction' from data because one of the arguments is None."
                                   f"[none_args={none_args}]")

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
        record = TransactionTable.create(type=type, client=client.dni.as_primitive() if client is not None else None,
                                         when=when, amount=amount.as_primitive(), method=method,
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
            client = None
            if record.client is not None:
                dni = Number(record.client.dni)
                if dni in self.client_cache:
                    client = self.client_cache[dni]
                else:
                    client = ClientView(dni, String(record.client.cli_name), created_by="SqliteTransactionRepo.all")
            yield self.from_data(record.id, record.type, record.when, record.amount, record.method, record.responsible,
                                 record.description, client, record.balance)

    def bind_to_balance(self, transaction: Transaction, balance_date: date):
        record = TransactionTable.get_by_id(transaction.id)
        record.balance_id = balance_date
        record.save()


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
        DATABASE_PROXY.create_tables([SubscriptionTable])

    def add(self, subscription: Subscription):
        SubscriptionTable.create(
            when=subscription.when, client_id=subscription.client.dni.as_primitive(),
            activity_id=subscription.activity.name.as_primitive(),
            transaction_id=None if subscription.transaction is None else subscription.transaction.id
        )

    def remove(self, subscription: Subscription):
        SubscriptionTable.delete().where((SubscriptionTable.client_id == subscription.client.dni.as_primitive())
                                         & (SubscriptionTable.activity_id == subscription.activity.name)).execute()

    def update(self, subscription: Subscription):
        """Registers in the repository that the *client* was charged for the *activity*.
        """
        sub_record = SubscriptionTable.get_by_id((subscription.client.dni.as_primitive(),
                                                  subscription.activity.name.as_primitive()))
        if subscription.transaction is not None:
            sub_record.transaction_id = subscription.transaction.id
        sub_record.save()


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
