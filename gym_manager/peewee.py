from datetime import date
from typing import Type, Generator

from peewee import SqliteDatabase, Model, IntegerField, CharField, DateField, BooleanField, TextField, ForeignKeyField, \
    CompositeKey

from gym_manager.core import attr_constraints as constraints
from gym_manager.core.base import Client, Number, String, Date, Currency, Activity, Payment, Inscription
from gym_manager.core.persistence import ClientRepo, ActivityRepo, PaymentRepo, InscriptionRepo

_DATABASE_NAME = r"test.db"
_DATABASE = SqliteDatabase(_DATABASE_NAME, pragmas={'foreign_keys': 1})


def create_table(table: Type[Model], drop_before: bool = False):
    if drop_before:
        _DATABASE.drop_tables([table])
    _DATABASE.create_tables([table])


class ClientTable(Model):
    dni = IntegerField(primary_key=True)
    name = CharField()
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

        return ClientTable.get_or_none(ClientTable.dni == dni.as_primitive()) is not None

    def get(self, dni: Number) -> Client:
        """Returns the client with the given *dni*.
        """
        raw_client = ClientTable.get_by_id(dni)
        return Client(
            dni,
            String(raw_client.name, optional=False, max_len=constraints.CLIENT_NAME_CHARS),
            Date(date(raw_client.admission.year, raw_client.admission.month, raw_client.admission.day)),
            String(raw_client.telephone, optional=constraints.CLIENT_TEL_OPTIONAL, max_len=constraints.CLIENT_TEL_CHARS),
            String(raw_client.direction, optional=constraints.CLIENT_DIR_OPTIONAL, max_len=constraints.CLIENT_DIR_CHARS)
        )

    def create(self, dni: Number, name: String, admission: Date, telephone: String, direction: String) -> Number:
        """Creates a client with the given data, and return its dni.
        """
        if not isinstance(dni, Number):
            raise TypeError(f"The argument 'dni' should be a 'Number', not a '{type(dni)}'")
        if not isinstance(name, String):
            raise TypeError(f"The argument 'name' should be a 'String', not a '{type(name)}'")
        if not isinstance(admission, Date):
            raise TypeError(f"The argument 'admission' should be a 'Date', not a '{type(admission)}'")
        if not isinstance(telephone, String):
            raise TypeError(f"The argument 'telephone' should be a 'String', not a '{type(telephone)}'")
        if not isinstance(direction, String):
            raise TypeError(f"The argument 'direction' should be a 'String', not a '{type(direction)}'")

        if self.contains(dni):
            raise KeyError(f"There is an existing client with the 'dni'={dni.as_primitive()}")
        raw_client = ClientTable.create(dni=dni.as_primitive(),
                                        name=name.as_primitive(),
                                        admission=admission.as_primitive(),
                                        telephone=telephone.as_primitive(),
                                        direction=direction.as_primitive(),
                                        is_active=True)
        return raw_client.dni

    def remove(self, client: Client):
        """Marks the given *client* as inactive.
        """
        raw_client = ClientTable.get_by_id(client.dni.as_primitive())
        raw_client.is_active = False
        raw_client.save()

        # ToDo. Delete registrations.

    def update(self, client: Client):
        """Updates the client in the repository whose dni is *client.dni*, with the data of *client*.
        """
        raw_client = ClientTable.get_or_none(ClientTable.dni == client.dni.as_primitive())
        raw_client.name = client.name.as_primitive()
        raw_client.admission = client.admission.as_primitive()
        raw_client.telephone = client.telephone.as_primitive()
        raw_client.direction = client.direction.as_primitive()
        raw_client.save()

    def all(self, only_actives: bool = True, **kwargs) -> Generator[Client, None, None]:
        """Returns all the clients in the repository.

        Args:
            only_actives: If True, retrieve only the active clients. An active client is a client that wasn't removed.

        Keyword Args:
            page_number: number of page of the table to return.
            items_per_page: number of items per page.
        """
        page_number, items_per_page = kwargs["page_number"], kwargs["items_per_page"]

        for raw_client in ClientTable.select().where(ClientTable.is_active).paginate(page_number, items_per_page):
            yield Client(
                Number(raw_client.dni, min_value=constraints.CLIENT_MIN_DNI, max_value=constraints.CLIENT_MAX_DNI),
                String(raw_client.name, optional=False, max_len=constraints.CLIENT_NAME_CHARS),
                Date(date(raw_client.admission.year, raw_client.admission.month, raw_client.admission.day)),
                String(raw_client.telephone, optional=constraints.CLIENT_TEL_OPTIONAL, max_len=constraints.CLIENT_TEL_CHARS),
                String(raw_client.direction, optional=constraints.CLIENT_DIR_OPTIONAL, max_len=constraints.CLIENT_DIR_CHARS)
            )


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

    def create(self, name: String, price: Currency, pay_once: bool, description: String) -> int:
        """Creates an activity with the given data, and returns its id in the repository.
        """
        raw_activity = ActivityTable.create(
            name=str(name), price=str(price), pay_once=pay_once, description=str(description)
        )
        return raw_activity.id

    def remove(self, activity: Activity, cascade_removing: bool = False):
        """Tries to remove the given *activity*.

        If *cascade_removing* is False, and there is at least one client registered in the activity, the removing will
        fail. If *cascade_removing* is True, the *activity* and all registrations for it will be removed.

        Args:
            activity: activity to remove.
            cascade_removing: if True, remove the activity and all registrations for it. If False, remove the activity
                only if it has zero registrations.
        """
        registered_clients = self.registered_clients(activity)
        if not cascade_removing and registered_clients > 0:
            raise Exception(f"The activity '{activity.name}' can not be removed because it has {registered_clients} "
                            f"registered clients and 'cascade_removing' was set to False.")
        # ToDo. To remove activity and its registrations, set on_delete=True in RegistrationTable.
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
                           String(raw_activity.name, optional=False, max_len=constraints.ACTIVITY_NAME_CHARS),
                           Currency(raw_activity.price, positive=True, max_currency=constraints.MAX_CURRENCY),
                           raw_activity.pay_once,
                           String(raw_activity.description, optional=True, max_len=constraints.ACTIVITY_DESCR_CHARS))

    def registered_clients(self, activity: Activity) -> int:
        """Returns the number of clients registered in the given *activity*.
        """
        return 0  # ToDo This requires RegistrationTable.


class PaymentTable(Model):
    id = IntegerField(primary_key=True)
    client = ForeignKeyField(ClientTable, backref="payments")
    when = DateField()
    amount = CharField()
    method = CharField()
    responsible = CharField()
    description = CharField()

    class Meta:
        database = _DATABASE


class SqlitePaymentRepo(PaymentRepo):
    """Payments repository implementation based on Sqlite and peewee ORM.
    """

    def __init__(self) -> None:
        create_table(PaymentTable)

    def register(
            self, client: Client, when: Date, amount: Currency, method: String, responsible: String, description: String
    ) -> Payment:
        """Register a new payment with the given information. This method must return the created payment.
        """
        payment = PaymentTable.create(
            client=ClientTable.get_by_id(client.dni),
            when=when,
            amount=amount,
            method=method,
            responsible=responsible,
            description=description
        )

        return Payment(payment.id, client, when, amount, method, responsible, description)

    def all(self, client: Client, **kwargs) -> Generator[Payment, None, None]:
        """Retrieves the payments of the given *client*

        Args:
            client: client whose payments are wanted.

        Keyword Args:
            page_number: number of page of the table to return.
            items_per_page: number of items per page.
        """
        page_number, items_per_page = kwargs["page_number"], kwargs["items_per_page"]
        query = PaymentTable.select().join(ClientTable).where(ClientTable.dni == client.dni)
        query = query.paginate(page_number, items_per_page)

        for row in query:
            yield Payment(row.id, client, row.day, Currency(row.amount), row.method, row.responsible, row.description)


class InscriptionTable(Model):
    client = ForeignKeyField(ClientTable, backref="activities")
    activity = ForeignKeyField(ActivityTable, backref="entries")
    payment = ForeignKeyField(PaymentTable, backref="payments", null=True)

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
            client=ClientTable.get_by_id(inscription.client.dni.as_primitive()),
            activity=ActivityTable.get_by_id(inscription.activity.id),
            payment=None if inscription.payment is None else PaymentTable.get_by_id(inscription.payment.id)
        )

    def update_or_create(self, registration: Inscription):
        """Updates the given *registration* in the repository. If there is no row in the repository, then creates a
        new one.
        """
        raw_client = ClientTable.get_by_id(registration.client.dni.as_primitive())
        raw_activity = ActivityTable.get_by_id(registration.activity.id)
        raw_reg = InscriptionTable.get_or_none(client=raw_client, activity=raw_activity)
        if raw_reg is None:
            InscriptionTable.create(
                client=ClientTable.get_by_id(registration.client.dni.as_primitive()),
                activity=ActivityTable.get_by_id(registration.activity.id),
                payment=None if registration.payment is None else PaymentTable.get_by_id(registration.payment.id)
            )
        # try:
        #     # If the entry already exists, it means the client is registered in the activity. It also means that this
        #     # method is being invoked to register the payment for the activity, so we can assure the *entry* has
        #     # payment information.
        #     raw_entry = RegistrationTable.get_by_id((registration.client, registration.activity))  # Raises DoesNotExist.
        #     raw_entry.payment = PaymentTable.get_by_id(registration.payment.id)
        #     raw_entry.save()
        # except DoesNotExist:
        #     # If the entry doesn't exists, then the client is getting registered in the activity. There might be
        #     # payment information if the client should pay when he is registered in the activity.
        #     RegistrationTable.create(
        #         client=ClientTable.get_by_id(registration.client.dni),
        #         activity=ActivityTable.get_by_id(registration.activity.id),
        #         payment=None if registration.payment is None else PaymentTable.get_by_id(registration.payment.id)
        #     )

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
