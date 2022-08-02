from typing import Generator

from peewee import Model, ForeignKeyField, CharField, IntegerField, JOIN

from gym_manager.contact.core import ContactRepo, Contact
from gym_manager.core.base import String, Client, Number
from gym_manager.core.persistence import LRUCache, ClientView
from gym_manager.peewee import ClientTable, DATABASE_PROXY


class ContactModel(Model):
    id = IntegerField(primary_key=True)
    c_name = CharField()
    tel1 = CharField()
    tel2 = CharField()
    direction = CharField()
    description = CharField()
    client = ForeignKeyField(ClientTable, backref="info", null=True)

    class Meta:
        database = DATABASE_PROXY


class SqliteContactRepo(ContactRepo):
    def __init__(self, cache_len: int = 64):
        DATABASE_PROXY.create_tables([ClientTable, ContactModel])

        self.cache = LRUCache(int, value_type=Contact, max_len=cache_len)

    def has_contact_info(self, client: Client) -> bool:
        return ContactModel.get_or_none(client_id=client.id) is not None

    def create(
            self, name: String, tel1: String, tel2: String, direction: String, description: String,
            client: Client | None = None
    ) -> Contact:
        client_id = None if client is None else client.id
        record = ContactModel.create(c_name=name.as_primitive(), tel1=tel1.as_primitive(), tel2=tel2.as_primitive(),
                                     direction=direction.as_primitive(), description=description.as_primitive(),
                                     client_id=client_id)
        return Contact(record.id, name, tel1, tel2, direction, description, client)

    def update(self, contact: Contact):
        record = ContactModel.get_by_id(contact.id)
        record.tel1 = contact.tel1
        record.tel2 = contact.tel2
        record.direction = contact.direction
        record.description = contact.description
        if contact.client is None:
            record.c_name = contact.name
        record.save()

    def remove(self, contact: Contact):
        ContactModel.delete_by_id(contact.id)

    def all(
            self, page: int = 1, page_len: int | None = None, name: String | None = None
    ) -> Generator[Contact, None, None]:
        query = ContactModel.select().join(ClientTable, JOIN.LEFT_OUTER).where((ClientTable.is_active) |
                                                                               (ClientTable.is_active.is_null()))

        if name is not None:
            query = query.where((ContactModel.c_name.contains(name.as_primitive()))
                                | (ClientTable.cli_name.contains(name.as_primitive())))

        if page_len is not None:
            query = query.paginate(page, page_len)

        for record in query:
            client, client_record = None, record.client
            if client_record is not None:
                client = ClientView(client_record.id, client_record.cli_name, "SqliteContactRepo.all",
                                    Number(client_record.dni if client_record.dni is not None else ""))
            yield Contact(record.id, String(record.c_name), String(record.tel1), String(record.tel2),
                          String(record.direction), String(record.description), client)
