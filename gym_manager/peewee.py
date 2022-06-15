from datetime import date
from typing import Type, Generator

from peewee import SqliteDatabase, Model, IntegerField, CharField, DateField

from gym_manager.core import attr_constraints as constraints
from gym_manager.core.base import Client, Number, String, Date
from gym_manager.core.persistence import ClientRepo

_DATABASE_NAME = r"test.db"  # ToDo. See how to set this str at program startup.
_DATABASE = SqliteDatabase(_DATABASE_NAME)


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
        if not isinstance(date, Date):
            raise TypeError(f"The argument 'date' should be a 'String', not a '{type(date)}'")
        if not isinstance(telephone, String):
            raise TypeError(f"The argument 'telephone' should be a 'String', not a '{type(telephone)}'")
        if not isinstance(direction, String):
            raise TypeError(f"The argument 'direction' should be a 'String', not a '{type(direction)}'")

        if self.contains(dni):
            raise KeyError(f"There is an existing client with the 'dni'={dni.as_primitive()}")
        raw_client = ClientTable.create(dni=dni.as_primitive(),
                                        name=name.as_primitive(),
                                        admission=str(admission),
                                        telephone=telephone.as_primitive(),
                                        direction=direction.as_primitive())
        return raw_client.dni

    def remove(self, client: Client):
        """Removes the given *client* from the repository.
        """
        ClientTable.delete_by_id(client.dni.as_primitive())

    def update(self, client: Client):
        """Updates the client in the repository whose dni is *client.dni*, with the data of *client*.
        """
        raw_client = ClientTable.get_or_none(ClientTable.dni == client.dni.as_primitive())
        raw_client.name = client.name.as_primitive()
        raw_client.admission = str(client.admission)
        raw_client.telephone = client.telephone.as_primitive()
        raw_client.direction = client.direction.as_primitive()
        raw_client.save()

    def all(self, **kwargs) -> Generator[Client, None, None]:
        """Returns all the clients in the repository.

        Keyword Args:
            page_number: number of page of the table to return.
            items_per_page: number of items per page.
        """
        page_number, items_per_page = kwargs["page_number"], kwargs["items_per_page"]

        for raw_client in ClientTable.select().paginate(page_number, items_per_page):
            yield Client(
                Number(raw_client.dni, min_value=constraints.CLIENT_MIN_DNI, max_value=constraints.CLIENT_MAX_DNI),
                String(raw_client.name, optional=False, max_len=constraints.CLIENT_NAME_CHARS),
                Date(date(raw_client.admission.year, raw_client.admission.month, raw_client.admission.day)),
                String(raw_client.telephone, optional=constraints.CLIENT_TEL_OPTIONAL, max_len=constraints.CLIENT_TEL_CHARS),
                String(raw_client.direction, optional=constraints.CLIENT_DIR_OPTIONAL, max_len=constraints.CLIENT_DIR_CHARS)
            )
