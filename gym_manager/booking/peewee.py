import logging
from datetime import date, time
from typing import Generator

from peewee import Model, CharField, ForeignKeyField, BooleanField, TimeField, IntegerField, prefetch, \
    JOIN, DateField

from gym_manager import peewee
from gym_manager.booking.core import Booking, BookingRepo, Court, State
from gym_manager.core.base import Client
from gym_manager.core.persistence import ClientRepo, TransactionRepo, LRUCache, FilterValuePair
from gym_manager.peewee import TransactionTable

logger = logging.getLogger(__name__)


class BookingTable(Model):
    id = IntegerField(primary_key=True)
    when = DateField()
    court = CharField()
    client = ForeignKeyField(peewee.ClientTable, backref="bookings")
    start = TimeField()
    end = TimeField()
    is_fixed = BooleanField()
    state = CharField()
    updated_by = CharField()
    transaction = ForeignKeyField(peewee.TransactionTable, backref="charged_booking", null=True)

    class Meta:
        database = peewee.DATABASE_PROXY


class SqliteBookingRepo(BookingRepo):

    def __init__(
            self,
            existing_courts: tuple[Court, ...],
            client_repo: ClientRepo,
            transaction_repo: TransactionRepo,
            cache_len: int = 100
    ) -> None:
        BookingTable._meta.database.create_tables([BookingTable])

        self.courts = {court.name: court for court in existing_courts}
        self.client_repo = client_repo
        self.transaction_repo = transaction_repo

        self._do_caching = cache_len > 0
        self.cache = LRUCache((int,), Booking, max_len=cache_len)

    def create(
            self, court: Court, client: Client, is_fixed: bool, state: State, when: date, start: time, end: time
    ) -> Booking:
        record = BookingTable.create(when=when,
                                     court=court.name,
                                     client=peewee.ClientTable.get_by_id(client.dni.as_primitive()),
                                     start=start,
                                     end=end,
                                     is_fixed=is_fixed,
                                     state=state.name,
                                     updated_by=state.updated_by)

        booking = Booking(record.id, court, client, is_fixed, state, when, start, end)
        self.cache[booking.id] = booking
        return booking

    def update(self, booking: Booking, prev_state: State):
        record = BookingTable.get_by_id(booking.id)
        # Updates the booking.
        record.is_fixed = booking.is_fixed
        record.state = booking.state.name
        record.updated_by = booking.state.updated_by
        if booking.transaction is not None:
            record.transaction = TransactionTable.get_by_id(booking.transaction.id)
        record.save()

    def all(
            self,
            states: tuple[str, ...] | None = None,
            when: date | None = None,
            filters: list[FilterValuePair] | None = None
    ) -> Generator[Booking, None, None]:
        bookings_q = BookingTable.select()
        if states is not None:
            bookings_q = bookings_q.where(BookingTable.state.in_(states))
        if when is not None:
            year, month, day = when.year, when.month, when.day
            bookings_q = bookings_q.where(year == BookingTable.when.year, month == BookingTable.when.month,
                                          day == BookingTable.when.day)
        if filters is not None:
            # The left outer join is required because bookings might be filtered by the client name, which isn't
            # an attribute of BookingTable.
            bookings_q = bookings_q.join(peewee.ClientTable, JOIN.LEFT_OUTER)
            for filter_, value in filters:
                bookings_q = bookings_q.where(filter_.passes_in_repo(BookingTable, value))

        for record in prefetch(bookings_q, TransactionTable.select()):
            booking: Booking
            if self._do_caching and record.id in self.cache:
                booking = self.cache[record.id]
            else:
                client = self.client_repo.get(record.client_id)

                trans_record, transaction = record.transaction, None
                if trans_record is not None:
                    transaction = self.transaction_repo.from_record(
                        trans_record.id, trans_record.type, client, trans_record.when, trans_record.amount,
                        trans_record.method, trans_record.responsible, trans_record.description
                    )

                booking = Booking(
                    record.id, self.courts[record.court], client, record.is_fixed,
                    State(record.state, record.updated_by), record.when, record.start, record.end, transaction
                )
                if self._do_caching:
                    self.cache[record.id] = booking
                    logger.getChild(type(self).__name__).info(
                        f"Booking with [id={record.id}] not in cache. The booking will be created from raw data."
                    )
            yield booking

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
