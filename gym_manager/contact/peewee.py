from typing import Generator

from peewee import Model, ForeignKeyField, CharField, IntegerField

from gym_manager.contact.core import ContactRepo, Contact
from gym_manager.core.base import String, Client
from gym_manager.core.persistence import LRUCache
from gym_manager.peewee import ClientTable, DATABASE_PROXY


class ContactModel(Model):
    id = IntegerField(primary_key=True)
    name = CharField(null=True)
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
        pass

    def create(
            self, name: String, tel1: String, tel2: String, direction: String, description: String,
            client: Client | None = None
    ) -> Contact:
        client_id = None if client is None else client.id
        record = ContactModel.create(name=name.as_primitive(), tel1=tel1.as_primitive(), tel2=tel2.as_primitive(),
                                     direction=direction.as_primitive(), description=description.as_primitive(),
                                     client_id=client_id)
        return Contact(record.id, name, tel1, tel2, direction, description, client)

    def update(self, contact: Contact):
        pass

    def remove(self, contact: Contact):
        pass

    def all(
            self, page: int = 1, page_len: int | None = None, name: str | None = None
    ) -> Generator[Contact, None, None]:
        pass
