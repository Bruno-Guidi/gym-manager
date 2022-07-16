import logging
from datetime import date, datetime
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
    SimpleClient)
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


class SqliteBookingRepo(BookingRepo):

    def __init__(
            self,
            client_repo: ClientRepo,
            transaction_repo: TransactionRepo,
            cache_len: int = 0
    ) -> None:
        BookingTable._meta.database.create_tables([BookingTable, FixedBookingTable, CancelledLog])

        self.client_repo = client_repo
        self.transaction_repo = transaction_repo

    def add(self, booking: Booking):
        # In both cases, Booking.transaction is ignored, because its supposed that a newly added booking won't have an
        # associated transaction.
        if isinstance(booking, FixedBooking):
            booking: FixedBooking
            FixedBookingTable.create(day_of_week=booking.day_of_week, court=booking.court, start=booking.start,
                                     client_id=booking.client.dni.as_primitive(), end=booking.end,
                                     first_when=booking.first_when, last_when=booking.when, inactive_dates=[])
        elif isinstance(booking, TempBooking):
            booking: TempBooking
            BookingTable.create(when=datetime.combine(booking.when, booking.start), court=booking.court,
                                client_id=booking.client.dni.as_primitive(), end=booking.end, is_fixed=False)

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
                FixedBookingTable.delete_by_id((booking.day_of_week, booking.court, booking.start))
            else:  # The FixedBooking is definitely cancelled.
                transaction_id = None if booking.transaction is None else booking.transaction.id
                FixedBookingTable.replace(day_of_week=booking.day_of_week, court=booking.court, start=booking.start,
                                          client_id=booking.client.dni.as_primitive(), end=booking.end,
                                          transaction_id=transaction_id, first_when=booking.first_when,
                                          last_when=booking.when,
                                          inactive_dates=serialize_inactive_dates(booking.inactive_dates)).execute()
        elif isinstance(booking, TempBooking):  # A TempBooking is always definitely cancelled.
            BookingTable.delete_by_id((datetime.combine(booking.when, booking.start), booking.court))

    def log_cancellation(
            self, cancel_datetime: datetime, responsible: String, booking: Booking, definitely_cancelled: bool
    ):
        CancelledLog.create(cancel_datetime=cancel_datetime, responsible=responsible.as_primitive(),
                            client_id=booking.client.dni.as_primitive(), when=booking.when, court=booking.court,
                            start=booking.start, end=booking.end, is_fixed=booking.is_fixed,
                            definitely_cancelled=definitely_cancelled)

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
            client = SimpleClient(Number(record.client.dni), String(record.client.cli_name, max_len=30),
                                  created_by="SqliteBookingRepo.all_temporal")

            trans_record, transaction = record.transaction, None
            if trans_record is not None:
                transaction = self.transaction_repo.from_data(
                    trans_record.id, trans_record.type, trans_record.when, trans_record.amount, trans_record.method,
                    trans_record.responsible, trans_record.description, client, trans_record.balance_id
                )

            when = record.when.date()
            start = record.when.time()
            yield TempBooking(record.court, client, start, record.end, when, transaction, record.is_fixed)

    def all_fixed(self) -> Generator[FixedBooking, None, None]:
        for record in prefetch(FixedBookingTable.select(), TransactionTable.select()):
            transaction_record, transaction = record.transaction, None
            client = SimpleClient(Number(record.client.dni), String(record.client.cli_name, max_len=30),
                                  created_by="SqliteBookingRepo.all_fixed")
            if transaction_record is not None:
                transaction = self.transaction_repo.from_data(
                    transaction_record.id, transaction_record.type, transaction_record.when, transaction_record.amount,
                    transaction_record.method, transaction_record.responsible, transaction_record.description, client,
                    transaction_record.balance_id
                )
            yield FixedBooking(record.court, client, record.start, record.end, record.day_of_week, record.first_when,
                               record.last_when, deserialize_inactive_dates(record.inactive_dates), transaction)

    def cancelled(
            self, page: int = 1, page_len: int = 10, filters: list[FilterValuePair] | None = None
    ) -> Generator[Cancellation, None, None]:
        cancelled_q = CancelledLog.select(
            CancelledLog.cancel_datetime, CancelledLog.responsible, CancelledLog.client_id, CancelledLog.when,
            CancelledLog.court, CancelledLog.start, CancelledLog.end, CancelledLog.is_fixed,
            CancelledLog.definitely_cancelled
        )
        # The left outer join is required because the client name is required.
        cancelled_q = cancelled_q.join(peewee.ClientTable, JOIN.LEFT_OUTER)

        if filters is not None:
            for filter_, value in filters:
                cancelled_q = cancelled_q.where(filter_.passes_in_repo(CancelledLog, value))

        for record in cancelled_q.paginate(page, page_len):
            yield Cancellation(
                record.cancel_datetime, record.responsible,
                SimpleClient(Number(record.client.dni), String(record.client.cli_name, max_len=30),
                             created_by="SqliteBookingRepo.cancelled"),
                record.when, record.court, record.start, record.end, record.is_fixed, record.definitely_cancelled
            )

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
