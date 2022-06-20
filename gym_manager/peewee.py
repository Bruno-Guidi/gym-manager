from __future__ import annotations

from datetime import date
from typing import Type, Generator

from peewee import SqliteDatabase, Model, IntegerField, CharField, DateField, BooleanField, TextField, ForeignKeyField, \
    CompositeKey, prefetch

from gym_manager.core import constants as consts
from gym_manager.core.base import Client, Number, String, Currency, Activity, Transaction, Inscription
from gym_manager.core.persistence import ClientRepo, ActivityRepo, TransactionRepo, InscriptionRepo

_DATABASE_NAME = r"test.db"
_DATABASE = SqliteDatabase(_DATABASE_NAME, pragmas={'foreign_keys': 1})


def create_table(table: Type[Model], drop_before: bool = False):
    if drop_before:
        _DATABASE.drop_tables([table])
    _DATABASE.create_tables([table])


class ClientTable(Model):
    dni = IntegerField(primary_key=True)
    cli_name = CharField()
    admission = DateField()
    telephone = CharField()
    direction = CharField()
    is_active = BooleanField()

    class Meta:
        database = _DATABASE


class SqliteClientRepo(ClientRepo):
    """Clients repository implementation based on Sqlite and peewee ORM.
    """

    def __init__(self, activity_repo: ActivityRepo, transaction_repo: TransactionRepo) -> None:
        create_table(ClientTable)
        self.activity_repo = activity_repo
        self.transaction_repo = transaction_repo
        self.cache: dict[Number, Client] = {}

    def from_raw(self, raw) -> Client:
        client = Client(Number(raw.dni, min_value=consts.CLIENT_MIN_DNI, max_value=consts.CLIENT_MAX_DNI),
                        String(raw.cli_name, max_len=consts.CLIENT_NAME_CHARS),
                        raw.admission,
                        String(raw.telephone, optional=consts.CLIENT_TEL_OPTIONAL, max_len=consts.CLIENT_TEL_CHARS),
                        String(raw.direction, optional=consts.CLIENT_DIR_OPTIONAL, max_len=consts.CLIENT_DIR_CHARS),
                        raw.is_active)

        for raw_inscription in raw.inscriptions:
            activity = self.activity_repo.get(raw_inscription.activity_id)
            raw_trans, transaction = raw_inscription.transaction, None
            if raw_trans is not None:
                transaction = self.transaction_repo.from_raw_data(
                    raw_trans.id, raw_trans.type, client, raw_trans.when, raw_trans.amount, raw_trans.method,
                    raw_trans.responsible, raw_trans.description
                )
            client.sign_on(Inscription(raw_inscription.when, client, activity, transaction))

        return client

    def get(self, dni: int | Number) -> Client:
        """Returns the client with the given *dni*.
        """
        if not isinstance(dni, (Number, int)):
            raise TypeError(f"The argument 'dni' should be a 'Number' or 'int', not a '{type(dni)}'")
        if isinstance(dni, int):
            dni = Number(dni, min_value=consts.CLIENT_MIN_DNI, max_value=consts.CLIENT_MAX_DNI)

        if dni not in self.cache:
            clients_q = ClientTable.select().where(ClientTable.dni == dni.as_primitive())
            inscriptions_q, trans_q = InscriptionTable.select(), TransactionTable.select()
            for raw in prefetch(clients_q, inscriptions_q, trans_q):
                self.cache[dni] = self.from_raw(raw)
        try:
            return self.cache[dni]
        except KeyError as key_err:
            raise KeyError(f"There is no client with the 'dni'={str(dni)}.") from key_err

    def is_active(self, dni: Number) -> bool:
        """Checks if there is an active client with the given *dni*.
        """
        if not isinstance(dni, Number):
            raise TypeError(f"The argument 'dni' should be a 'Number', not a '{type(dni)}'")

        raw_client = ClientTable.get_or_none(ClientTable.dni == dni.as_primitive())
        return raw_client is not None and raw_client.is_active

    def add(self, client: Client):
        """Adds the *client* to the repository.
        """
        if self.is_active(client.dni):
            raise KeyError(f"There is an existing client with the 'dni'={client.dni.as_primitive()}")

        ClientTable.replace(dni=client.dni.as_primitive(),
                            cli_name=client.name.as_primitive(),
                            admission=client.admission,
                            telephone=client.telephone.as_primitive(),
                            direction=client.direction.as_primitive(),
                            is_active=True).execute()
        self.cache[client.dni] = client

    def remove(self, client: Client):
        """Marks the given *client* as inactive, and delete its inscriptions.
        """
        ClientTable.replace(dni=client.dni.as_primitive(),
                            cli_name=client.name.as_primitive(),
                            admission=client.admission,
                            telephone=client.telephone.as_primitive(),
                            direction=client.direction.as_primitive(),
                            is_active=False).execute()
        self.cache.pop(client.dni)
        InscriptionTable.delete().where(InscriptionTable.client_id == client.dni.as_primitive()).execute()

    def update(self, client: Client):
        """Updates the client in the repository whose dni is *client.dni*, with the data of *client*.
        """
        ClientTable.replace(dni=client.dni.as_primitive(),
                            cli_name=client.name.as_primitive(),
                            admission=client.admission,
                            telephone=client.telephone.as_primitive(),
                            direction=client.direction.as_primitive(),
                            is_active=True).execute()

    def all(self, page: int, page_len: int = 20, **kwargs) -> Generator[Client, None, None]:
        """Returns all the clients in the repository.

        Args:
            page: page to retrieve.
            page_len: clients per page.
        """
        clients_q = ClientTable.select()
        for filter_, value in kwargs.values():
            clients_q = clients_q.where(filter_.passes_in_repo(ClientTable, value))
        clients_q = clients_q.where(ClientTable.is_active == True)
        clients_q.paginate(page, page_len)

        inscription_q, transactions_q = InscriptionTable.select(), TransactionTable.select()

        for raw_client in prefetch(clients_q, inscription_q, transactions_q):
            client = self.from_raw(raw_client)
            self.cache[client.dni] = client
            yield client


class ActivityTable(Model):
    id = IntegerField(primary_key=True)
    act_name = CharField()
    price = CharField()
    pay_once = BooleanField()
    description = TextField()

    class Meta:
        database = _DATABASE


class SqliteActivityRepo(ActivityRepo):
    """Activities repository implementation based on Sqlite and peewee ORM.
    """

    def __init__(self) -> None:
        create_table(ActivityTable)
        self.cache: dict[int, Activity] = {}

    def get(self, id: int) -> Activity:
        """Retrieves the activity with the given *id* in the repository, if it exists.

        Raises:
            KeyError if there is no activity with the given *id*.
        """
        if id not in self.cache:
            raw = ActivityTable.get_or_none(ActivityTable.id == id)
            if raw is None:
                raise KeyError(f"There is no activity with the id '{id}'")
            self.cache[id] = Activity(raw.id,
                                      String(raw.act_name, max_len=consts.ACTIVITY_NAME_CHARS),
                                      Currency(raw.price, max_currency=consts.MAX_CURRENCY),
                                      raw.pay_once,
                                      String(raw.description, optional=True, max_len=consts.ACTIVITY_DESCR_CHARS))
        return self.cache[id]

    def create(self, name: String, price: Currency, pay_once: bool, description: String) -> Activity:
        """Creates an activity with the given data, and returns it.
        """
        raw_activity = ActivityTable.create(
            act_name=name.as_primitive(), price=str(price), pay_once=pay_once, description=description.as_primitive()
        )
        return Activity(raw_activity.id, name, price, pay_once, description)

    def remove(self, activity: Activity, cascade_removing: bool = False):
        """Tries to remove the given *activity*.

        If *cascade_removing* is False, and there is at least one client registered in the activity, the removing will
        fail. If *cascade_removing* is True, the *activity* and all registrations for it will be removed.

        Args:
            activity: activity to remove.
            cascade_removing: if True, remove the activity and all registrations for it. If False, remove the activity
                only if it has zero registrations.
        """
        inscriptions = self.n_inscriptions(activity)
        if not cascade_removing and inscriptions > 0:
            raise Exception(f"The activity '{activity.name}' can not be removed because it has {inscriptions} "
                            f"registered clients and 'cascade_removing' was set to False.")

        ActivityTable.delete_by_id(activity.id)

    def update(self, activity: Activity):
        """Updates the activity in the repository whose id is *activity.id*, with the data of *activity*.
        """
        ActivityTable.replace(id=activity.id,
                              act_name=activity.name.as_primitive(),
                              price=str(activity.price),
                              pay_once=activity.pay_once,
                              description=activity.description.as_primitive()).execute()

    def all(self) -> Generator[Activity, None, None]:
        for raw_activity in ActivityTable.select():
            if raw_activity.id not in self.cache:
                self.cache[raw_activity.id] = Activity(
                    raw_activity.id,
                    String(raw_activity.act_name, max_len=consts.ACTIVITY_NAME_CHARS),
                    Currency(raw_activity.price, max_currency=consts.MAX_CURRENCY),
                    raw_activity.pay_once,
                    String(raw_activity.description, optional=True, max_len=consts.ACTIVITY_DESCR_CHARS)
                )
            yield self.cache[raw_activity.id]

    def n_inscriptions(self, activity: Activity) -> int:
        """Returns the number of clients that are signed up in the given *activity*.
        """
        return InscriptionTable.select().where(InscriptionTable.activity == activity.id).count()


class TransactionTable(Model):
    id = IntegerField(primary_key=True)
    type = CharField()
    client = ForeignKeyField(ClientTable, backref="transactions")
    when = DateField()
    amount = CharField()
    method = CharField()
    responsible = CharField()
    description = CharField()

    class Meta:
        database = _DATABASE


class SqliteTransactionRepo(TransactionRepo):
    """Transaction repository implementation based on Sqlite and peewee ORM.
    """

    def __init__(self) -> None:
        create_table(TransactionTable)
        self.client_repo: ClientRepo | None = None
        self.cache: dict[int, Transaction] = {}

    def from_raw_data(self, id, type, client: Client, when, amount, method, responsible, description):
        """Creates a Transaction with the given data.
        """
        if id not in self.cache:
            transaction = Transaction(id,
                                      String(type, max_len=consts.TRANSACTION_TYPE_CHARS),
                                      client,
                                      when, Currency(amount, max_currency=consts.MAX_CURRENCY),
                                      String(method, max_len=consts.TRANSACTION_METHOD_CHARS),
                                      String(responsible, max_len=consts.TRANSACTION_RESP_CHARS),
                                      String(description, max_len=consts.TRANSACTION_DESCR_CHARS))
            self.cache[id] = transaction
        return self.cache[id]

    def create(
            self, type: String, client: Client, when: date, amount: Currency, method: String, responsible: String,
            description: String
    ) -> Transaction:
        """Register a new transaction with the given information. This method must return the created transaction.

        Raises:
            AttributeError if the client_repo attribute wasn't set before the execution of the method.
        """
        if self.client_repo is None:
            raise AttributeError("The 'client_repo' attribute in 'SqliteTransactionRepo' was not set.")

        transaction = TransactionTable.create(
            type=type.as_primitive(),
            client=ClientTable.get_by_id(client.dni.as_primitive()),
            when=when,
            amount=amount.as_primitive(),
            method=method.as_primitive(),
            responsible=responsible.as_primitive(),
            description=description.as_primitive()
        )

        return Transaction(transaction.id, type, client, when, amount, method, responsible, description)

    def all(self, page: int, page_len: int = 20, **kwargs) -> Generator[Transaction, None, None]:
        """Retrieves the transactions in the repository.

        Keyword Args:
            client: allows filtering by client name.
            type: allows filtering by transaction type.
            from_date: allows filtering transactions whose *when* is after the given date (inclusive).
            to_date: allows filtering transactions whose *when* is before the given date (inclusive).
            method: allows filtering by transaction method.
            responsible: allows filtering by transaction responsible.

        Raises:
            AttributeError if the client_repo attribute wasn't set before the execution of the method.
        """
        if self.client_repo is None:
            raise AttributeError("The 'client_repo' attribute in 'SqliteTransactionRepo' was not set.")

        transactions_q = TransactionTable.select().join(ClientTable)
        for filter_, value in kwargs.values():
            transactions_q = transactions_q.where(filter_.passes_in_repo(TransactionTable, value))

        for raw_transaction in transactions_q.paginate(page, page_len):
            yield Transaction(raw_transaction.id,
                              String(raw_transaction.type, max_len=consts.TRANSACTION_TYPE_CHARS),
                              self.client_repo.get(raw_transaction.client_id),
                              raw_transaction.when,
                              Currency(raw_transaction.amount, max_currency=consts.MAX_CURRENCY),
                              String(raw_transaction.method, max_len=consts.TRANSACTION_METHOD_CHARS),
                              String(raw_transaction.responsible, max_len=consts.TRANSACTION_RESP_CHARS),
                              String(raw_transaction.description, max_len=consts.TRANSACTION_DESCR_CHARS))


class InscriptionTable(Model):
    when = DateField()
    client = ForeignKeyField(ClientTable, backref="inscriptions", on_delete="CASCADE")
    activity = ForeignKeyField(ActivityTable, backref="inscriptions", on_delete="CASCADE")
    transaction = ForeignKeyField(TransactionTable, backref="inscription_transaction", null=True)

    class Meta:
        database = _DATABASE
        primary_key = CompositeKey("client", "activity")


class SqliteInscriptionRepo(InscriptionRepo):
    """Inscriptions repository implementation based on Sqlite and peewee ORM.
    """

    def __init__(self) -> None:
        create_table(InscriptionTable)

    def add(self, inscription: Inscription):
        """Adds the given *inscription* to the repository.
        """
        InscriptionTable.create(
            when=inscription.when,
            client=ClientTable.get_by_id(inscription.client.dni.as_primitive()),
            activity=ActivityTable.get_by_id(inscription.activity.id),
            transaction=None if inscription.transaction is None else TransactionTable.get_by_id(
                inscription.transaction.id)
        )

    def remove(self, inscription: Inscription):
        """Removes the given *inscription* from the repository.
        """
        InscriptionTable.delete().where((InscriptionTable.client_id == inscription.client.dni.as_primitive())
                                        & (InscriptionTable.activity_id == inscription.activity.id)).execute()

    def register_charge(self, client: Client, activity: Activity, transaction: Transaction):
        """Registers in the repository that the client was charged for the activity.
        """
        raw_inscription = InscriptionTable.get_by_id((client.dni.as_primitive(), activity.id))
        raw_transaction = TransactionTable.get_by_id(transaction.id)
        raw_inscription.transaction = raw_transaction
        raw_inscription.save()
