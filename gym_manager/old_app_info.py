import logging
from collections import namedtuple
from datetime import date
from typing import Iterable, Generator, TypeAlias

from peewee import Model, IntegerField, CharField, chunked, DateField, ForeignKeyField

from gym_manager.core.base import Currency, String
from gym_manager.core.persistence import FilterValuePair, ClientRepo, SubscriptionRepo, TransactionRepo
from gym_manager.peewee import DATABASE_PROXY, ClientTable, ActivityTable, TransactionTable

OldCharge = namedtuple("OldCharge",
                       ["id", "client_id", "client_name", "activity_name", "month", "year", "transaction_id",
                        "transaction_amount"])
OldExtraction: TypeAlias = tuple[int, date, str, str, str]


class OldChargesModel(Model):
    id = IntegerField(primary_key=True)
    client = ForeignKeyField(ClientTable, backref="old_charges")
    activity = ForeignKeyField(ActivityTable, backref="old_charges")
    month = IntegerField()
    year = IntegerField()
    transaction = ForeignKeyField(TransactionTable, backref="old_charge")
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
                OldChargesModel.insert_many(batch, fields=[OldChargesModel.client_id, OldChargesModel.activity_id,
                                                           OldChargesModel.month, OldChargesModel.year,
                                                           OldChargesModel.transaction_id, OldChargesModel.amount]
                                            ).execute()

    @staticmethod
    def all(
            page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[OldCharge, None, None]:
        old_charges_q = OldChargesModel.select(OldChargesModel, ClientTable.id, ClientTable.cli_name
                                               ).join(ClientTable).order_by(ClientTable.cli_name)

        if filters is not None:  # Apply given filters.
            for filter_, value in filters:
                old_charges_q = old_charges_q.where(filter_.passes_in_repo(OldChargesModel, value))

        if page_len is not None:
            old_charges_q = old_charges_q.paginate(page, page_len)

        for record in old_charges_q:
            yield OldCharge(record.id, record.client_id, record.client.cli_name, record.activity_id, record.month,
                            record.year, record.transaction_id, Currency.fmt(Currency(record.amount)))

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


def confirm_old_charge(
        client_repo: ClientRepo, transaction_repo: TransactionRepo, subscription_repo: SubscriptionRepo,
        old_charge: OldCharge
):
    client = client_repo.get(old_charge.client_id)
    transaction = transaction_repo.from_data(old_charge.transaction_id, client=client)
    subscription = client.mark_as_charged(String(old_charge.activity_name), old_charge.year, old_charge.month,
                                          transaction)
    subscription_repo.register_transaction(subscription, old_charge.year, old_charge.month, transaction)

    OldChargesRepo.remove(old_charge.id)

    logging.getLogger().getChild(__name__).info(
        f"Confirmed charge of [activity_name={subscription.activity.name}] to [client_name={client.name}] for the "
        f"[month={old_charge.month}] and [year={old_charge.year}]."
    )
    return subscription

