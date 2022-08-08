import dataclasses
import logging
from datetime import date, datetime, time
from typing import Generator

from peewee import (
    Model, CharField, ForeignKeyField, BooleanField, TimeField, IntegerField, prefetch,
    CompositeKey, DateTimeField, DateField)
from playhouse.sqlite_ext import JSONField

from gym_manager import peewee
from gym_manager.booking.core import TempBooking, BookingRepo, Booking, FixedBooking, Cancellation
from gym_manager.core.base import Transaction, String
from gym_manager.core.persistence import (
    TransactionRepo, FilterValuePair, PersistenceError,
    LRUCache)
from gym_manager.peewee import TransactionTable

logger = logging.getLogger(__name__)


def serialize_inactive_dates(inactive_dates: list[dict[str, date]]):
    return [{key: str(date_) for key, date_ in date_range.items()} for date_range in inactive_dates]


def deserialize_inactive_dates(raw_inactive_dates: list[dict[str, str]]):
    return [{key: datetime.strptime(date_, "%Y-%m-%d").date() for key, date_ in date_range.items()}
            for date_range in raw_inactive_dates]


class BookingTable(Model):
    when = DateTimeField()
    court = CharField()
    client_name = CharField()
    end = TimeField()
    is_fixed = BooleanField()
    transaction = ForeignKeyField(peewee.TransactionTable, backref="charged_booking", null=True)

    class Meta:
        database = peewee.DATABASE_PROXY
        primary_key = CompositeKey("when", "court")


class FixedBookingTable(Model):
    day_of_week = IntegerField()
    court = CharField()
    start = TimeField()
    client_name = CharField()
    end = TimeField()
    transaction = ForeignKeyField(peewee.TransactionTable, backref="charged_fixed_booking", null=True)
    first_when = DateField()
    last_when = DateField()
    inactive_dates = JSONField()

    class Meta:
        database = peewee.DATABASE_PROXY
        primary_key = CompositeKey("day_of_week", "court", "start")


class CancelledLog(Model):
    id = IntegerField(primary_key=True)
    cancel_datetime = DateTimeField()
    responsible = CharField()
    client_name = CharField()
    when = DateField(null=True)
    court = CharField()
    start = TimeField()
    end = TimeField()
    is_fixed = BooleanField()
    definitely_cancelled = BooleanField()

    class Meta:
        database = peewee.DATABASE_PROXY


@dataclasses.dataclass(frozen=True)
class TempBookingKey:
    when: datetime
    court: str


@dataclasses.dataclass(frozen=True)
class FixedBookingKey:
    day_of_week: int
    court: str
    start: time


class SqliteBookingRepo(BookingRepo):

    def __init__(self, transaction_repo: TransactionRepo, cache_len: int) -> None:
        peewee.DATABASE_PROXY.create_tables([BookingTable, FixedBookingTable, CancelledLog])

        self.transaction_repo = transaction_repo

        self.temp_booking_cache = LRUCache(TempBookingKey, TempBooking, max_len=cache_len)
        self.fixed_booking_cache = LRUCache(FixedBookingKey, FixedBooking, max_len=cache_len)
        self.cancellation_cache = LRUCache(int, Cancellation, max_len=int(cache_len / 2))

    def add(self, booking: Booking):
        # In both cases, Booking.transaction is ignored, because its supposed that a newly added booking won't have an
        # associated transaction.
        if isinstance(booking, FixedBooking):
            booking: FixedBooking
            FixedBookingTable.create(day_of_week=booking.day_of_week, court=booking.court, start=booking.start,
                                     client_name=booking.client_name, end=booking.end, first_when=booking.first_when,
                                     last_when=booking.when, inactive_dates=[])
            self.fixed_booking_cache[FixedBookingKey(booking.day_of_week, booking.court, booking.start)] = booking
        elif isinstance(booking, TempBooking):
            booking: TempBooking
            when = datetime.combine(booking.when, booking.start)
            BookingTable.create(when=when, court=booking.court, client_name=booking.client_name, end=booking.end,
                                is_fixed=False)

            self.temp_booking_cache[TempBookingKey(when, booking.court)] = booking
        else:
            raise PersistenceError(f"Argument 'booking' of [type={type(booking)}] cannot be persisted in "
                                   f"SqliteBookingRepo.")

    def charge(self, booking: Booking, transaction: Transaction):
        if isinstance(booking, FixedBooking):
            # There is no problem in using replace method here, because no table has a fk that references this table.
            FixedBookingTable.replace(day_of_week=booking.day_of_week, court=booking.court, start=booking.start,
                                      client_name=booking.client_name, end=booking.end,
                                      transaction_id=booking.transaction.id, first_when=booking.first_when,
                                      last_when=booking.when, inactive_dates=booking.inactive_dates).execute()
            # Creates a TempBooking based on the FixedBooking, so the charging is registered.
            booking = TempBooking(booking.court, booking.client_name, booking.start, booking.end, booking.when,
                                  transaction, is_fixed=True)
        elif not isinstance(booking, TempBooking):
            raise PersistenceError(f"Argument 'booking' of [type={type(booking)}] cannot be persisted in "
                                   f"SqliteBookingRepo.")

        # There is no problem in using replace method here, because no table has a fk that references this table.
        # Replace method is used because there is an existing booking with the given pk, but with no transaction.
        BookingTable.replace(when=datetime.combine(booking.when, booking.start), court=booking.court,
                             client_name=booking.client_name, end=booking.end, is_fixed=booking.is_fixed,
                             transaction_id=transaction.id).execute()

    def cancel(self, booking: Booking, definitely_cancelled: bool = True):
        if isinstance(booking, FixedBooking):  # The FixedBooking is definitely cancelled.
            if definitely_cancelled:
                pk = FixedBookingKey(booking.day_of_week, booking.court, booking.start)
                FixedBookingTable.delete_by_id(dataclasses.astuple(pk))
                self.fixed_booking_cache.pop(pk)
            else:  # The FixedBooking is temporally cancelled.
                transaction_id = None if booking.transaction is None else booking.transaction.id
                FixedBookingTable.replace(day_of_week=booking.day_of_week, court=booking.court, start=booking.start,
                                          client_name=booking.client_name, end=booking.end,
                                          transaction_id=transaction_id, first_when=booking.first_when,
                                          last_when=booking.when,
                                          inactive_dates=serialize_inactive_dates(booking.inactive_dates)).execute()
        elif isinstance(booking, TempBooking):  # A TempBooking is always definitely cancelled.
            when = datetime.combine(booking.when, booking.start)
            pk = TempBookingKey(when, booking.court)
            BookingTable.delete_by_id(dataclasses.astuple(pk))
            self.temp_booking_cache.pop(pk)

    def log_cancellation(
            self, cancel_datetime: datetime, responsible: String, booking: Booking, definitely_cancelled: bool
    ):
        record = CancelledLog.create(cancel_datetime=cancel_datetime, responsible=responsible.as_primitive(),
                                     client_name=booking.client_name, when=booking.when, court=booking.court,
                                     start=booking.start, end=booking.end, is_fixed=booking.is_fixed,
                                     definitely_cancelled=definitely_cancelled)
        self.cancellation_cache[record.id] = Cancellation(record.id, cancel_datetime, responsible, booking.client_name,
                                                          booking.when, booking.court, booking.start, booking.end,
                                                          booking.is_fixed, definitely_cancelled)

    def all_temporal(
            self, when: date | None = None, court: str | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[TempBooking, None, None]:
        bookings_q = BookingTable.select()

        if when is not None:
            year, month, day = when.year, when.month, when.day
            # noinspection PyPropertyAccess
            bookings_q = bookings_q.where(year == BookingTable.when.year, month == BookingTable.when.month,
                                          day == BookingTable.when.day)

        if court is not None:
            bookings_q = bookings_q.where(BookingTable.court == court)
        if filters is not None:
            for filter_, value in filters:
                bookings_q = bookings_q.where(filter_.passes_in_repo(BookingTable, value))

        for record in prefetch(bookings_q, TransactionTable.select()):
            pk = TempBookingKey(record.court, record.when)
            if pk not in self.temp_booking_cache:
                trans_record, transaction = record.transaction, None
                if trans_record is not None:
                    transaction = self.transaction_repo.from_data(
                        trans_record.id, trans_record.type, trans_record.when, trans_record.amount, trans_record.method,
                        trans_record.responsible, trans_record.description, client=None,
                        balance_date=trans_record.balance_id
                    )

                when = record.when.date()
                start = record.when.time()
                self.temp_booking_cache[pk] = TempBooking(record.court, String(record.client_name), start, record.end,
                                                          when, transaction, record.is_fixed)
                logger.getChild(type(self).__name__).info(
                    f"Creating Booking [booking.when={when}, booking.court={record.court}, booking.start={start}] from "
                    f"queried data."
                )

            yield self.temp_booking_cache[pk]

    def all_fixed(self) -> Generator[FixedBooking, None, None]:
        for record in prefetch(FixedBookingTable.select(), TransactionTable.select()):
            pk = FixedBookingKey(record.day_of_week, record.court, record.start)
            if pk not in self.fixed_booking_cache:
                transaction_record, transaction = record.transaction, None
                if transaction_record is not None:
                    transaction = self.transaction_repo.from_data(
                        transaction_record.id, transaction_record.type, transaction_record.when,
                        transaction_record.amount, transaction_record.method, transaction_record.responsible,
                        transaction_record.description, client=None, balance_date=transaction_record.balance_id
                    )
                self.fixed_booking_cache[pk] = FixedBooking(
                    record.court, String(record.client_name), record.start, record.end, record.day_of_week,
                    record.first_when, record.last_when, deserialize_inactive_dates(record.inactive_dates), transaction
                )
                logger.getChild(type(self).__name__).info(
                    f"Creating Booking [booking.day_of_week={record.day_of_week},  booking.court={record.court}, "
                    f"booking.start={record.start}] from queried data."
                )

            yield self.fixed_booking_cache[pk]

    def cancelled(
            self, page: int = 1, page_len: int = 10, filters: list[FilterValuePair] | None = None
    ) -> Generator[Cancellation, None, None]:
        cancelled_q = CancelledLog.select()

        if filters is not None:
            for filter_, value in filters:
                cancelled_q = cancelled_q.where(filter_.passes_in_repo(CancelledLog, value))

        for record in cancelled_q.paginate(page, page_len).order_by(CancelledLog.cancel_datetime.desc()):
            if record.id not in self.cancellation_cache:
                self.cancellation_cache[record.id] = Cancellation(
                    record.id, record.cancel_datetime, record.responsible, String(record.client_name),
                    record.when, record.court, record.start, record.end, record.is_fixed, record.definitely_cancelled
                )
                logger.getChild(type(self).__name__).info(
                    f"Creating Cancellation [cancellation.id={record.id}] from queried data."
                )
            yield self.cancellation_cache[record.id]
