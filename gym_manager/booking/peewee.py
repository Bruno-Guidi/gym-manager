from datetime import date, time
from typing import Generator, Iterable

from peewee import Model, DateTimeField, CharField, ForeignKeyField, BooleanField, TimeField, IntegerField, prefetch

from gym_manager import peewee
from gym_manager.booking.core import Booking, BookingRepo, combine, Court, State
from gym_manager.core.base import Client
from gym_manager.core.persistence import ClientRepo, TransactionRepo
from gym_manager.peewee import TransactionTable


class BookingTable(Model):
    id = IntegerField(primary_key=True)
    when = DateTimeField()
    court = CharField()
    client = ForeignKeyField(peewee.ClientTable, backref="bookings")
    end = TimeField()
    is_fixed = BooleanField()
    state = CharField()
    updated_by = CharField()
    transaction = ForeignKeyField(peewee.TransactionTable, backref="charged_booking", null=True)

    class Meta:
        database = peewee.DATABASE_PROXY


class SqliteBookingRepo(BookingRepo):

    def __init__(self, client_repo: ClientRepo, transaction_repo: TransactionRepo) -> None:
        BookingTable._meta.database.create_tables([BookingTable])

        self.client_repo = client_repo
        self.transaction_repo = transaction_repo

    def create(
            self, court: Court, client: Client, is_fixed: bool, state: State, when: date, start: time, end: time
    ) -> Booking:
        record = BookingTable.create(when=combine(when, start),
                                     court=court.name,
                                     client=peewee.ClientTable.get_by_id(client.dni.as_primitive()),
                                     end=end,
                                     is_fixed=is_fixed,
                                     state=state.name,
                                     updated_by=state.updated_by)
        return Booking(record.id, court, client, is_fixed, state, when, start, end)

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
            self, existing_courts: Iterable[Court], states: tuple[str, ...], when: date | None = None, **filters
    ) -> Generator[Booking, None, None]:
        bookings_q = BookingTable.select()
        if len(states) > 0:
            bookings_q = bookings_q.where(BookingTable.state.in_(states))
        if when is not None:
            year, month, day = when.year, when.month, when.day
            bookings_q = bookings_q.where(year == BookingTable.when.year, month == BookingTable.when.month,
                                          day == BookingTable.when.day)
        for filter_, value in filters.values():
            bookings_q = bookings_q.join(peewee.ClientTable)
            bookings_q = bookings_q.where(filter_.passes_in_repo(BookingTable, value))

        for record in prefetch(bookings_q, TransactionTable.select()):
            start = time(record.when.hour, record.when.minute)
            state = State(record.state, record.updated_by)
            client = self.client_repo.get(record.client_id)

            trans_record, transaction = record.transaction, None
            if trans_record is not None:
                transaction = self.transaction_repo.from_record(
                    trans_record.id, trans_record.type, client, trans_record.when, trans_record.amount,
                    trans_record.method, trans_record.responsible, trans_record.description
                )

            court_dict = {court.name: court for court in existing_courts}
            yield Booking(record.id, court_dict[record.court], client, record.is_fixed, state, record.when, start,
                          record.end, transaction)
