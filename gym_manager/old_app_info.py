from datetime import date
from typing import Iterable, Generator, TypeAlias

from peewee import Model, IntegerField, CharField, chunked, DateField

from gym_manager.core.base import Currency
from gym_manager.core.persistence import FilterValuePair
from gym_manager.peewee import DATABASE_PROXY


OldCharge: TypeAlias = tuple[int, str, str, int, int, str]
OldExtraction: TypeAlias = tuple[int, date, str, str, str]


class OldChargesModel(Model):
    id = IntegerField(primary_key=True)
    client_name = CharField()
    activity_name = CharField()
    month = IntegerField()
    year = IntegerField()
    amount = CharField()

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
                OldChargesModel.insert_many(batch, fields=[OldChargesModel.client_name, OldChargesModel.activity_name,
                                                           OldChargesModel.month, OldChargesModel.year,
                                                           OldChargesModel.amount]).execute()

    @staticmethod
    def all(
            page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[OldCharge, None, None]:
        query = OldChargesModel.select()

        if filters is not None:  # Apply given filters.
            for filter_, value in filters:
                query = query.where(filter_.passes_in_repo(OldChargesModel, value))

        if page_len is not None:
            query = query.order_by(OldChargesModel.client_name).paginate(page, page_len)

        for record in query:
            yield (record.id, record.client_name, record.activity_name, record.month, record.year,
                   Currency.fmt(Currency(record.amount)))

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

