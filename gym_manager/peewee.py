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

    def __init__(self) -> None:
        create_table(ClientTable)

    def contains(self, dni: Number) -> bool:
        """Returns True if there is a client with the given *dni*, False otherwise.
        """
        if not isinstance(dni, Number):
            raise TypeError(f"The argument 'dni' should be a 'Number', not a '{type(dni)}'")

        raw_client = ClientTable.get_or_none(ClientTable.dni == dni.as_primitive())
        return raw_client is not None and raw_client.is_active

    def add(self, client: Client):
        """Adds the *client* to the repository.
        """
        if self.contains(client.dni):
            raise KeyError(f"There is an existing client with the 'dni'={client.dni.as_primitive()}")

        ClientTable.replace(dni=client.dni.as_primitive(),
                            cli_name=client.name.as_primitive(),
                            admission=client.admission,
                            telephone=client.telephone.as_primitive(),
                            direction=client.direction.as_primitive(),
                            is_active=True).execute()

    def remove(self, client: Client):
        """Marks the given *client* as inactive, and delete its inscriptions.
        """
        raw_client = ClientTable.get_by_id(client.dni.as_primitive())
        raw_client.is_active = False
        raw_client.save()

        InscriptionTable.delete().where(client == client.dni.as_primitive())

    def update(self, client: Client):
        """Updates the client in the repository whose dni is *client.dni*, with the data of *client*.
        """
        raw_client = ClientTable.get_or_none(ClientTable.dni == client.dni.as_primitive())
        raw_client.name = client.name.as_primitive()
        raw_client.admission = client.admission
        raw_client.telephone = client.telephone.as_primitive()
        raw_client.direction = client.direction.as_primitive()
        raw_client.save()

    def _get_activity(self, raw_activity, cache: dict[int, Activity]) -> Activity:
        if raw_activity.id in cache:
            return cache[raw_activity.id]
        else:
            new = Activity(raw_activity.id,
                           String(raw_activity.name, max_len=consts.ACTIVITY_NAME_CHARS),
                           Currency(raw_activity.price, max_currency=consts.MAX_CURRENCY),
                           raw_activity.pay_once,
                           String(raw_activity.description, optional=True, max_len=consts.ACTIVITY_DESCR_CHARS))
            cache[raw_activity.id] = new
            return new

    def all(
            self, page: int, page_len: int = 20, activity_cache: dict[Number, Client] | None = None, **kwargs
    ) -> Generator[Client, None, None]:
        """Returns all the clients in the repository.

        Args:
            page: page to retrieve.
            page_len: clients per page.
            activity_cache: cached activities.

        Keyword Args:
            only_actives: allows filtering only active clients.
            name: allows filtering clients by name.
        """
        activity_cache = {} if activity_cache is None else activity_cache

        clients_q = ClientTable.select()
        for filter_, value in kwargs.values():
            clients_q = clients_q.where(filter_.passes_in_repo(ClientTable, value))

        clients_q.paginate(page, page_len)

        inscription_q = InscriptionTable.select()
        transactions_q = TransactionTable.select()

        for raw_client in prefetch(clients_q, inscription_q, transactions_q):
            client = Client(
                Number(raw_client.dni, min_value=consts.CLIENT_MIN_DNI, max_value=consts.CLIENT_MAX_DNI),
                String(raw_client.cli_name, max_len=consts.CLIENT_NAME_CHARS),
                raw_client.admission,
                String(raw_client.telephone, optional=consts.CLIENT_TEL_OPTIONAL, max_len=consts.CLIENT_TEL_CHARS),
                String(raw_client.direction, optional=consts.CLIENT_DIR_OPTIONAL, max_len=consts.CLIENT_DIR_CHARS)
            )

            for raw_inscription in raw_client.inscriptions:
                activity = self._get_activity(raw_inscription.activity, activity_cache)
                raw_transaction = raw_inscription.transaction
                transaction = None
                if raw_transaction is not None:
                    transaction = Transaction(
                        raw_transaction.id,
                        String(raw_transaction.type, max_len=consts.TRANSACTION_TYPE_CHARS),
                        client,
                        raw_transaction.when,
                        Currency(raw_transaction.amount, max_currency=consts.MAX_CURRENCY),
                        String(raw_transaction.method, max_len=consts.TRANSACTION_METHOD_CHARS),
                        String(raw_transaction.responsible, max_len=consts.TRANSACTION_RESP_CHARS),
                        String(raw_transaction.description, max_len=consts.TRANSACTION_DESCR_CHARS)
                    )
                client.sign_on(Inscription(raw_inscription.when, client, activity, transaction))

            yield client


class ActivityTable(Model):
    id = IntegerField(primary_key=True)
    name = CharField()
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

    def create(self, name: String, price: Currency, pay_once: bool, description: String) -> Activity:
        """Creates an activity with the given data, and returns it.
        """
        raw_activity = ActivityTable.create(
            name=str(name), price=str(price), pay_once=pay_once, description=str(description)
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
        inscriptions = self.inscriptions(activity)
        if not cascade_removing and inscriptions > 0:
            raise Exception(f"The activity '{activity.name}' can not be removed because it has {inscriptions} "
                            f"registered clients and 'cascade_removing' was set to False.")

        ActivityTable.delete_by_id(activity.id)

    def update(self, activity: Activity):
        """Updates the activity in the repository whose id is *activity.id*, with the data of *activity*.
        """
        raw_activity = ActivityTable.get_or_none(ActivityTable.id == activity.id)
        raw_activity.name = activity.name.as_primitive()
        raw_activity.price = str(activity.price)
        raw_activity.pay_once = activity.pay_once
        raw_activity.description = activity.description.as_primitive()
        raw_activity.save()

    def all(self) -> Generator[Activity, None, None]:
        for raw_activity in ActivityTable.select():
            yield Activity(raw_activity.id,
                           String(raw_activity.name, max_len=consts.ACTIVITY_NAME_CHARS),
                           Currency(raw_activity.price, max_currency=consts.MAX_CURRENCY),
                           raw_activity.pay_once,
                           String(raw_activity.description, optional=True, max_len=consts.ACTIVITY_DESCR_CHARS))

    def inscriptions(self, activity: Activity) -> int:
        """Returns the number of clients registered in the given *activity*.
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

    def create(
            self, type: String, client: Client, when: date, amount: Currency, method: String, responsible: String,
            description: String
    ) -> Transaction:
        """Register a new transaction with the given information. This method must return the created
        transaction.
        """
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

    def _get_client(self, raw_client, cache: dict[int, Client]) -> Client:
        if raw_client.dni in cache:
            return cache[raw_client.dni]
        else:
            new = Client(
                Number(raw_client.dni, min_value=consts.CLIENT_MIN_DNI, max_value=consts.CLIENT_MAX_DNI),
                String(raw_client.cli_name, max_len=consts.CLIENT_NAME_CHARS),
                raw_client.admission,
                String(raw_client.telephone, optional=consts.CLIENT_TEL_OPTIONAL, max_len=consts.CLIENT_TEL_CHARS),
                String(raw_client.direction, optional=consts.CLIENT_DIR_OPTIONAL, max_len=consts.CLIENT_DIR_CHARS)
            )
            cache[raw_client.dni] = new
            return new

    def all(
            self, page: int, page_len: int = 20, cache: dict[Number, Client] | None = None, **kwargs
    ) -> Generator[Transaction, None, None]:
        """Retrieves the transactions in the repository.

        Keyword Args:
            client: allows filtering by client name.
            type: allows filtering by transaction type.
            from_date: allows filtering transactions whose *when* is after the given date (inclusive).
            to_date: allows filtering transactions whose *when* is before the given date (inclusive).
            method: allows filtering by transaction method.
            responsible: allows filtering by transaction responsible.
        """
        transactions_q = TransactionTable.select().join(ClientTable)

        for filter_, value in kwargs.values():
            transactions_q = transactions_q.where(filter_.passes_in_repo(TransactionTable, value))

        if 'responsible' in kwargs and len(kwargs['responsible']) > 0:
            transactions_q = transactions_q.where(TransactionTable.responsible.contains(kwargs['responsible']))

        cache = {} if cache is None else cache

        for raw_transaction in transactions_q.paginate(page, page_len):
            yield Transaction(raw_transaction.id,
                              String(raw_transaction.type, max_len=consts.TRANSACTION_TYPE_CHARS),
                              self._get_client(raw_transaction.client, cache),
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
        InscriptionTable.delete_by_id((inscription.activity.id, inscription.client.dni.as_primitive()))

    def register_charge(self, client: Client, activity: Activity, transaction: Transaction):
        """Registers in the repository that the client was charged for the activity.
        """
        raw_inscription = InscriptionTable.get_by_id((client.dni.as_primitive(), activity.id))
        raw_transaction = TransactionTable.get_by_id(transaction.id)
        raw_inscription.transaction = raw_transaction
        raw_inscription.save()

    def all(self, client: Client) -> Generator[Inscription, None, None]:
        """Retrieves all inscriptions of the given *client*.
        """
        query = InscriptionTable.select()
        for x in query:
            print(type(x))
            yield x

    def expired(self, when: date, **kwargs) -> Generator[Inscription, None, None]:
        """Retrieves all entries whose pay day has passed if today date were *when*.

        Keyword Args:
            activities: dict[int, Activity] with existing activities.
            page_number: number of page of the table to return.
            items_per_page: number of items per page.
        """
        pass
