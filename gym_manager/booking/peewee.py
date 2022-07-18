import dataclasses
import logging
from datetime import date, datetime, time
from typing import Generator

from peewee import (
    Model, CharField, ForeignKeyField, BooleanField, TimeField, IntegerField, prefetch,
    JOIN, CompositeKey, DateTimeField, DateField)
from playhouse.sqlite_ext import JSONField

from gym_manager import peewee
from gym_manager.booking.core import TempBooking, BookingRepo, Booking, FixedBooking, Cancellation
from gym_manager.core.base import Transaction, String, Number
from gym_manager.core.persistence import (
    ClientRepo, TransactionRepo, FilterValuePair, PersistenceError,
    ClientView, LRUCache)
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
    client = ForeignKeyField(peewee.ClientTable, backref="bookings")
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
    client = ForeignKeyField(peewee.ClientTable, backref="fixed_bookings")
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
    client = ForeignKeyField(peewee.ClientTable, backref="cancelled_bookings")
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

    def __init__(
            self,
            client_repo: ClientRepo,
            transaction_repo: TransactionRepo,
            cache_len: int
    ) -> None:
        peewee.DATABASE_PROXY.create_tables([BookingTable, FixedBookingTable, CancelledLog])

        self.client_repo = client_repo
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
                                     client_id=booking.client.dni.as_primitive(), end=booking.end,
                                     first_when=booking.first_when, last_when=booking.when, inactive_dates=[])
            self.fixed_booking_cache[FixedBookingKey(booking.day_of_week, booking.court, booking.start)] = booking
        elif isinstance(booking, TempBooking):
            booking: TempBooking
            when = datetime.combine(booking.when, booking.start)
            BookingTable.create(when=when, court=booking.court, client_id=booking.client.dni.as_primitive(),
                                end=booking.end, is_fixed=False)

            self.temp_booking_cache[TempBookingKey(when, booking.court)] = booking
        else:
            raise PersistenceError(f"Argument 'booking' of [type={type(booking)}] cannot be persisted in "
                                   f"SqliteBookingRepo.")

    def charge(self, booking: Booking, transaction: Transaction):
        if isinstance(booking, FixedBooking):
            FixedBookingTable.replace(day_of_week=booking.day_of_week, court=booking.court, start=booking.start,
                                      client_id=booking.client.dni.as_primitive(), end=booking.end,
                                      transaction_id=booking.transaction.id, first_when=booking.first_when,
                                      last_when=booking.when, inactive_dates=booking.inactive_dates).execute()
            # Creates a TempBooking based on the FixedBooking, so the charging is registered.
            booking = TempBooking(booking.court, booking.client, booking.start, booking.end, booking.when, transaction,
                                  is_fixed=True)
        elif not isinstance(booking, TempBooking):
            raise PersistenceError(f"Argument 'booking' of [type={type(booking)}] cannot be persisted in "
                                   f"SqliteBookingRepo.")

        BookingTable.replace(when=datetime.combine(booking.when, booking.start), court=booking.court,
                             client_id=booking.client.dni.as_primitive(), end=booking.end, is_fixed=booking.is_fixed,
                             transaction_id=transaction.id).execute()

    def cancel(self, booking: Booking, definitely_cancelled: bool = True):
        if isinstance(booking, FixedBooking):
            if definitely_cancelled:  # The FixedBooking is temporally cancelled.
                pk = FixedBookingKey(booking.day_of_week, booking.court, booking.start)
                FixedBookingTable.delete_by_id(dataclasses.astuple(pk))
                self.fixed_booking_cache.pop(pk)
            else:  # The FixedBooking is definitely cancelled.
                transaction_id = None if booking.transaction is None else booking.transaction.id
                FixedBookingTable.replace(day_of_week=booking.day_of_week, court=booking.court, start=booking.start,
                                          client_id=booking.client.dni.as_primitive(), end=booking.end,
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
                                     client_id=booking.client.dni.as_primitive(), when=booking.when,
                                     court=booking.court, start=booking.start, end=booking.end,
                                     is_fixed=booking.is_fixed, definitely_cancelled=definitely_cancelled)
        self.cancellation_cache[record.id] = Cancellation(record.id, cancel_datetime, responsible, booking.client,
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
            # The left outer join is required because bookings might be filtered by the client name, which isn't
            # an attribute of BookingTable.
            bookings_q = bookings_q.join(peewee.ClientTable, JOIN.LEFT_OUTER)
            for filter_, value in filters:
                bookings_q = bookings_q.where(filter_.passes_in_repo(BookingTable, value))

        for record in prefetch(bookings_q, TransactionTable.select()):
            booking: TempBooking
            pk = TempBookingKey(record.court, record.when)
            if pk in self.temp_booking_cache:
                booking = self.temp_booking_cache[pk]
                logger.getChild(type(self).__name__).info(f"Using cached booking [booking.when={booking.when}, "
                                                          f"booking.court={booking.court}, "
                                                          f"booking.start={booking.start}].")
            else:
                client = ClientView(Number(record.client.dni), String(record.client.cli_name, max_len=30),
                                    created_by="SqliteBookingRepo.all_temporal")

                trans_record, transaction = record.transaction, None
                if trans_record is not None:
                    transaction = self.transaction_repo.from_data(
                        trans_record.id, trans_record.type, trans_record.when, trans_record.amount, trans_record.method,
                        trans_record.responsible, trans_record.description, client, trans_record.balance_id
                    )

                when = record.when.date()
                start = record.when.time()
                booking = TempBooking(record.court, client, start, record.end, when, transaction, record.is_fixed)
                self.temp_booking_cache[pk] = booking
                logger.getChild(type(self).__name__).info(f"Querying booking [booking.when={booking.when}, "
                                                          f"booking.court={booking.court}, "
                                                          f"booking.start={booking.start}].")

            yield booking

    def all_fixed(self) -> Generator[FixedBooking, None, None]:
        for record in prefetch(FixedBookingTable.select(), TransactionTable.select()):
            booking: FixedBooking
            pk = FixedBookingKey(record.day_of_week, record.court, record.start)
            if pk in self.fixed_booking_cache:
                booking = self.fixed_booking_cache[pk]
                logger.getChild(type(self).__name__).info(
                    f"Using cached booking [booking.day_of_week={booking.day_of_week},  booking.court={booking.court}, "
                    f"booking.start={booking.start}]."
                )
            else:
                transaction_record, transaction = record.transaction, None
                client = ClientView(Number(record.client.dni), String(record.client.cli_name, max_len=30),
                                    created_by="SqliteBookingRepo.all_fixed")
                if transaction_record is not None:
                    transaction = self.transaction_repo.from_data(
                        transaction_record.id, transaction_record.type, transaction_record.when,
                        transaction_record.amount, transaction_record.method, transaction_record.responsible,
                        transaction_record.description, client, transaction_record.balance_id
                    )
                booking = FixedBooking(record.court, client, record.start, record.end, record.day_of_week,
                                       record.first_when, record.last_when,
                                       deserialize_inactive_dates(record.inactive_dates), transaction)
                self.fixed_booking_cache[pk] = booking
                logger.getChild(type(self).__name__).info(
                    f"Querying booking [booking.day_of_week={booking.day_of_week},  booking.court={booking.court}, "
                    f"booking.start={booking.start}]."
                )

            yield booking

    def cancelled(
            self, page: int = 1, page_len: int = 10, filters: list[FilterValuePair] | None = None
    ) -> Generator[Cancellation, None, None]:
        cancelled_q = CancelledLog.select()
        # The left outer join is required because the client name is required.
        cancelled_q = cancelled_q.join(peewee.ClientTable, JOIN.LEFT_OUTER)

        if filters is not None:
            for filter_, value in filters:
                cancelled_q = cancelled_q.where(filter_.passes_in_repo(CancelledLog, value))

        for record in cancelled_q.paginate(page, page_len):
            if record.id not in self.cancellation_cache:
                self.cancellation_cache[record.id] = Cancellation(
                    record.id, record.cancel_datetime, record.responsible,
                    ClientView(Number(record.client.dni), String(record.client.cli_name, max_len=30),
                               created_by="SqliteBookingRepo.cancelled"),
                    record.when, record.court, record.start, record.end, record.is_fixed, record.definitely_cancelled
                )
                logger.getChild(type(self).__name__).info(
                    f"Creating Cancellation [cancellation.id={record.id}] from queried data."
                )
            yield self.cancellation_cache[record.id]

    def count_cancelled(self, filters: list[FilterValuePair] | None = None) -> int:
        """Counts the number of bookings in the repository.
        """
        bookings_q = BookingTable.select("1")
        if filters is not None:
            # The left outer join is required because bookings might be filtered by the client name, which isn't
            # an attribute of BookingTable.
            bookings_q = bookings_q.join(peewee.ClientTable, JOIN.LEFT_OUTER)
            for filter_, value in filters:
                bookings_q = bookings_q.where(filter_.passes_in_repo(BookingTable, value))
        return bookings_q.count()
