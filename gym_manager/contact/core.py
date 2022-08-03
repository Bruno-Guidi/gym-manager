import abc
from typing import Iterable, Generator

from gym_manager.core.base import String, Client, OperationalError


class Contact:
    def __init__(
            self, id_: int, name: String, tel1: String, tel2: String, direction: String, description: String,
            client: Client | None = None
    ):
        self.id = id_
        self._name = name
        self.tel1 = tel1
        self.tel2 = tel2
        self.direction = direction
        self.description = description
        self.client = client

    @property
    def name(self):
        if self.client is not None:
            return self.client.name
        return self._name

    @name.setter
    def name(self, name: String):
        if self.client is None:
            self._name = name


class ContactRepo(abc.ABC):

    @abc.abstractmethod
    def has_contact_info(self, client: Client) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def create(
            self, name: String, tel1: String, tel2: String, direction: String, description: String,
            client: Client | None = None
    ) -> Contact:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, contact: Contact):
        raise NotImplementedError

    @abc.abstractmethod
    def remove(self, contact: Contact):
        raise NotImplementedError

    @abc.abstractmethod
    def remove_by_client(self, client: Client):
        raise NotImplementedError

    @abc.abstractmethod
    def all(
            self, page: int = 1, page_len: int | None = None, name: String | None = None
    ) -> Generator[Contact, None, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_all(self, raw_contacts: Iterable[tuple]):
        raise NotImplementedError


def create_contact(
        contact_repo: ContactRepo, name: String, tel1: String, tel2: String, direction: String, description: String,
        client: Client | None = None
) -> Contact:
    if client is not None and contact_repo.has_contact_info(client):
        raise OperationalError(f"The [client.id={client.id}] already has contact information.")

    if client is not None and len(name) != 0:
        name = String("")  # Avoids problems when the contact belongs to a client.

    return contact_repo.create(name, tel1, tel2, direction, description, client)


def update_contact(
        contact_repo: ContactRepo, contact: Contact, name: String, tel1: String, tel2: String, direction: String,
        description: String
):
    contact.name = name
    contact.tel1 = tel1
    contact.tel2 = tel2
    contact.direction = direction
    contact.description = description
    contact_repo.update(contact)


def remove_contact(contact_repo: ContactRepo, contact: Contact):
    contact_repo.remove(contact)


def remove_contact_by_client(contact_repo: ContactRepo, client: Client):
    contact_repo.remove_by_client(client)


def all_contacts(
        contact_repo: ContactRepo, page: int = 1, page_len: int | None = None, name: str | None = None
) -> Iterable[Contact]:
    yield from contact_repo.all(page, page_len, name)

