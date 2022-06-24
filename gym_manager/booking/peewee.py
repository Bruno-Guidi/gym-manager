from datetime import date, time, datetime
from typing import Generator

from peewee import Model, DateTimeField, CharField, ForeignKeyField, BooleanField, TimeField, IntegerField

from gym_manager import peewee
from gym_manager.booking.core import Booking, BookingRepo, combine, Court, State
from gym_manager.core.base import Client
from gym_manager.core.persistence import ClientRepo


class BookingTable(Model):
    id = IntegerField(primary_key=True)
    when = DateTimeField()
    court = CharField()
    client = ForeignKeyField(peewee.ClientTable, backref="bookings")
    end = TimeField()
    is_fixed = BooleanField()
    state = CharField()
    updated_by = CharField()

    class Meta:
        database = peewee._DATABASE


class StateHistory(Model):
    booking = ForeignKeyField(BookingTable, backref="state_history")
    prev = CharField()
    current = CharField()
    updated_by = CharField()
    when = DateTimeField()

    class Meta:
        database = peewee._DATABASE
        primary_key = False


class SqliteBookingRepo(BookingRepo):

    def __init__(self, client_repo: ClientRepo, drop_table: bool = False) -> None:
        if drop_table:
            peewee._DATABASE.drop_tables([BookingTable, StateHistory])
        peewee._DATABASE.create_tables([BookingTable, StateHistory])
        self.client_repo = client_repo

    def create(
            self, court: Court, client: Client, is_fixed: bool, state: State, when: date, start: time, end: time
    ) -> Booking:
        raw = BookingTable.create(when=combine(when, start),
                                  court=court.name,
                                  client=peewee.ClientTable.get_by_id(client.dni.as_primitive()),
                                  end=end,
                                  is_fixed=is_fixed,
                                  state=state.name,
                                  updated_by=state.updated_by)
        return Booking(raw.id, court, client, is_fixed, state, when, start, end)

    def update(self, booking: Booking, prev_state: State):
        raw = BookingTable.get_by_id(booking.id)
        # Updates the state history.
        StateHistory.create(booking=raw, prev=prev_state.name, current=booking.state.name,
                            updated_by=booking.state.updated_by, when=datetime.now())
        # Updates the booking.
        raw.is_fixed = booking.is_fixed
        raw.state = booking.state.name
        raw.updated_by = booking.state.updated_by
        raw.save()

    def all(
            self, courts: dict[str, Court], states: tuple[State, ...], when: date | None = None, **filters
    ) -> Generator[Booking, None, None]:
        bookings_q = BookingTable.select()
        if len(states) > 0:
            bookings_q = bookings_q.where(BookingTable.state.in_([state.name for state in states]))
        if when is not None:
            year, month, day = when.year, when.month, when.day
            bookings_q = bookings_q.where(year == BookingTable.when.year, month == BookingTable.when.month,
                                          day == BookingTable.when.day)
        for filter_, value in filters.values():
            bookings_q = bookings_q.join(peewee.ClientTable)
            bookings_q = bookings_q.where(filter_.passes_in_repo(BookingTable, value))
        for raw in bookings_q:
            start = time(raw.when.hour, raw.when.minute)
            state = State(raw.state, raw.updated_by)
            yield Booking(raw.id, courts[raw.court], self.client_repo.get(raw.client_id), raw.is_fixed, state, raw.when,
                          start, raw.end)
