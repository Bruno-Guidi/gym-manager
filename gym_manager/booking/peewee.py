import logging
from datetime import date, datetime, time
from typing import Generator

from peewee import (
    Model, CharField, ForeignKeyField, BooleanField, TimeField, IntegerField, prefetch,
    JOIN, DateField, CompositeKey, DateTimeField)

from gym_manager import peewee
from gym_manager.booking.core import (
    TempBooking, BookingRepo, Court, State, ONE_WEEK_TD, BOOKING_TO_HAPPEN, Booking,
    FixedBooking)
from gym_manager.core.base import Transaction
from gym_manager.core.persistence import ClientRepo, TransactionRepo, LRUCache, FilterValuePair, PersistenceError
from gym_manager.peewee import TransactionTable

logger = logging.getLogger(__name__)


class BookingTable(Model):
    when = DateTimeField(primary_key=True)
    court = CharField()
    client = ForeignKeyField(peewee.ClientTable, backref="bookings")
    end = TimeField()
    is_fixed = BooleanField()
    transaction = ForeignKeyField(peewee.TransactionTable, backref="charged_booking", null=True)

    class Meta:
        database = peewee.DATABASE_PROXY


class FixedBookingTable(Model):
    day_of_week = IntegerField()
    court = CharField()
    start = TimeField()
    client = ForeignKeyField(peewee.ClientTable, backref="fixed_bookings")
    end = TimeField()
    transaction = ForeignKeyField(peewee.TransactionTable, backref="charged_fixed_booking", null=True)
    activated_again = DateField(null=True)

    class Meta:
        database = peewee.DATABASE_PROXY
        primary_key = CompositeKey("day_of_week", "court", "start")


class SqliteBookingRepo(BookingRepo):

    def __init__(
            self,
            existing_courts: tuple[Court, ...],
            client_repo: ClientRepo,
            transaction_repo: TransactionRepo,
            cache_len: int = 100
    ) -> None:
        BookingTable._meta.database.create_tables([BookingTable, FixedBookingTable])

        self.courts = {court.name: court for court in existing_courts}
        self.client_repo = client_repo
        self.transaction_repo = transaction_repo

        self._do_caching = cache_len > 0
        self.cache = LRUCache((date,), TempBooking, max_len=cache_len)

    def add(self, booking: Booking):
        # In both cases, Booking.transaction is ignored, because its supposed that a newly added booking won't have an
        # associated transaction.
        if isinstance(booking, FixedBooking):
            booking: FixedBooking
            FixedBookingTable.create(day_of_week=booking.day_of_week,
                                     court=booking.court,
                                     start=booking.start,
                                     client_id=booking.client.dni.as_primitive(),
                                     end=booking.end,
                                     activated_again=booking.activated_again)
        elif isinstance(booking, TempBooking):
            booking: TempBooking
            BookingTable.create(when=datetime.combine(booking.when, booking.start),
                                court=booking.court,
                                client_id=booking.client.dni.as_primitive(),
                                end=booking.end,
                                is_fixed=False)

        else:
            raise PersistenceError(f"Argument 'booking' of [type={type(booking)}] cannot be persisted in "
                                   f"SqliteBookingRepo.")

    def charge(self, booking: Booking, transaction: Transaction):
        if isinstance(booking, FixedBooking):
            FixedBookingTable.replace(day_of_week=booking.day_of_week,
                                      court=booking.court,
                                      start=booking.start,
                                      client_id=booking.client.dni.as_primitive(),
                                      end=booking.end,
                                      transaction_id=booking.transaction.id,
                                      activated_again=booking.activated_again).execute()
            # Creates a TempBooking based on the FixedBooking, so the charging is registered.
            booking = TempBooking(booking.court, booking.client, booking.start, booking.end, booking.when, transaction,
                                  is_fixed=True)
        elif not isinstance(booking, TempBooking):
            raise PersistenceError(f"Argument 'booking' of [type={type(booking)}] cannot be persisted in "
                                   f"SqliteBookingRepo.")

        BookingTable.replace(when=datetime.combine(booking.when, booking.start),
                             court=booking.court,
                             client_id=booking.client.dni.as_primitive(),
                             end=booking.end,
                             is_fixed=booking.is_fixed,
                             transaction_id=transaction.id).execute()

    def update(self, booking: TempBooking, prev_state: State):
        record = BookingTable.get_by_id(booking.id)
        # Updates the booking.
        record.is_fixed = booking.is_fixed
        record.state = booking.state.name
        record.updated_by = booking.state.updated_by
        if booking.transaction is not None:
            record.transaction = TransactionTable.get_by_id(booking.transaction.id)
        record.save()

    def cancel(self, booking: TempBooking, cancel_fixed: bool = False, weeks_in_advance: int | None = None):
        # There is a problem with this approach. If a fixed booking is created, *weeks_in_advance* - 1 bookings will be
        # created in advance, to avoid another booking to step on the fixed one. Now suppose a new fixed booking is
        # created, with the same start and client, but after *weeks_in_advance* weeks of the first fixed booking. If the
        # first fixed booking is cancelled definitely, but after the week number 5, with this approach the remaining 3
        # bookings related to the first one will be deleted, but the first 5 related to the second one will be deleted
        # too. This is because both fixed bookings are virtually the same, even when they don't.

        # Another problem of this approach is that the booking history is bloated with the bookings that were made in
        # advance and cancelled, when they were never actively cancelled.

        # Deletes the booking.
        record = BookingTable.get_by_id(booking.id)
        record.state, record.updated_by = booking.state.name, booking.state.updated_by
        record.save()
        # Deletes the bookings created in advance.
        if cancel_fixed:
            when = booking.when
            for i in range(weeks_in_advance - 1):
                when = when + ONE_WEEK_TD
                # (when, start, client, state) isn't the PK of the table, but even so, there shouldn't be two bookings
                # whose state is BOOKING_TO_HAPPEN. Because of this, the query should always return only one record.
                # If there is any problem regarding booking cancelling, this should be the first place to look at.
                record = BookingTable.get_or_none(when=when,
                                                  start=booking.start,
                                                  client_id=booking.client.dni.as_primitive(),
                                                  state=BOOKING_TO_HAPPEN)
                if record is None:
                    break
                record.state, record.updated_by = booking.state.name, booking.state.updated_by
                record.save()
                self.cache[record.id].update_state(record.state, record.updated_by)

    def all_temporal(
            self, when: date | None = None, court: str | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[TempBooking, None, None]:
        bookings_q = BookingTable.select()
        if when is not None:
            year, month, day = when.year, when.month, when.day
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
            if self._do_caching and record.when in self.cache:
                booking = self.cache[record.when]
            else:
                client = self.client_repo.get(record.client_id)

                trans_record, transaction = record.transaction, None
                if trans_record is not None:
                    transaction = self.transaction_repo.from_record(
                        trans_record.id, trans_record.type, client, trans_record.when, trans_record.amount,
                        trans_record.method, trans_record.responsible, trans_record.description
                    )

                when = record.when.date()
                start = record.when.time()
                booking = TempBooking(record.court, client, start, record.end, when, transaction,
                                      record.is_fixed)
                if self._do_caching:
                    self.cache[record.when] = booking
                    logger.getChild(type(self).__name__).info(
                        f"Booking with [id={record.when}] not in cache. The booking will be created from raw data."
                    )
            yield booking

    def all_fixed(self) -> Generator[FixedBooking, None, None]:
        for record in prefetch(FixedBookingTable.select(), TransactionTable.select()):
            transaction_record: TransactionTable = record.transaction
            transaction = self.transaction_repo.from_record(
                transaction_record.id, transaction_record.type, self.client_repo.get(transaction_record.client_id),
                transaction_record.when, transaction_record.amount, transaction_record.method,
                transaction_record.responsible, transaction_record.description
            )
            yield FixedBooking(record.court, self.client_repo.get(record.client_id), record.start, record.end,
                               record.day_of_week, transaction, record.activated_again)

    def count(self, filters: list[FilterValuePair] | None = None) -> int:
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
