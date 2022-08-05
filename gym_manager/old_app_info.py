from collections import namedtuple
from datetime import date
from typing import Iterable, Generator, TypeAlias

from peewee import Model, IntegerField, CharField, chunked, DateField, ForeignKeyField, prefetch

from gym_manager.core.base import Currency
from gym_manager.core.persistence import FilterValuePair
from gym_manager.peewee import DATABASE_PROXY, ClientTable, ActivityTable, TransactionTable

OldCharge = namedtuple("OldCharge",
                       ["id", "client_id", "client_name", "activity_name", "month", "year", "transaction_id"])
OldExtraction: TypeAlias = tuple[int, date, str, str, str]


class OldChargesModel(Model):
    id = IntegerField(primary_key=True)
    client = ForeignKeyField(ClientTable, backref="old_charges")
    activity = ForeignKeyField(ActivityTable, backref="old_charges")
    month = IntegerField()
    year = IntegerField()
    transaction = ForeignKeyField(TransactionTable, backref="old_charge")

    class Meta:
        database = DATABASE_PROXY


class OldChargesRepo:
    @staticmethod
    def create_model():
        DATABASE_PROXY.create_tables([OldChargesModel])

    @staticmethod
    def add_all(raw_charges: Iterable[tuple]):
        with DATABASE_PROXY.atomic():
            for batch in chunked(raw_charges, 256):
                OldChargesModel.insert_many(batch, fields=[OldChargesModel.client_id, OldChargesModel.activity_id,
                                                           OldChargesModel.month, OldChargesModel.year,
                                                           OldChargesModel.transaction_id]).execute()

    @staticmethod
    def all(
            page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[OldCharge, None, None]:
        old_charges_q = OldChargesModel.select()

        if filters is not None:  # Apply given filters.
            for filter_, value in filters:
                old_charges_q = old_charges_q.where(filter_.passes_in_repo(OldChargesModel, value))

        if page_len is not None:
            old_charges_q = old_charges_q.order_by(OldChargesModel.client_name).paginate(page, page_len)

        clients_q = ClientTable.select(ClientTable.id, ClientTable.cli_name)
        for record in prefetch(old_charges_q, clients_q):
            yield (record.id, record.client_id, record.client.cli_name, record.activity_id, record.month, record.year,
                   record.transaction_id)

    @staticmethod
    def remove(id_: int):
        OldChargesModel.delete_by_id(id_)


class OldExtractionModel(Model):
    id = IntegerField(primary_key=True)
    when = DateField()
    responsible = CharField()
    amount = CharField()
    description = CharField()

    class Meta:
        database = DATABASE_PROXY


class OldExtractionRepo:

    @staticmethod
    def create_model():
        DATABASE_PROXY.create_tables([OldExtractionModel])

    @staticmethod
    def add_all(raw_extractions: Iterable[tuple]):
        with DATABASE_PROXY.atomic():
            for batch in chunked(raw_extractions, 256):
                OldExtractionModel.insert_many(batch, fields=[OldExtractionModel.when, OldExtractionModel.responsible,
                                                              OldExtractionModel.amount, OldExtractionModel.description]
                                               ).execute()

    @staticmethod
    def all(
            page: int = 1, page_len: int | None = None, when: date | None = None
    ) -> Generator[OldExtraction, None, None]:
        query = OldExtractionModel.select().order_by(OldExtractionModel.when)

        if when is not None:
            query = query.where(OldExtractionModel.when == when)

        if page_len is not None:
            query = query.paginate(page, page_len)

        for record in query:
            yield record.id, record.when, record.responsible, Currency.fmt(Currency(record.amount)), record.description

