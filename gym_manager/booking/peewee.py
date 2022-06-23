import abc
from datetime import date, time
from typing import Generator

from peewee import Model, DateTimeField, CharField, ForeignKeyField, BooleanField, TimeField

from gym_manager import peewee
from gym_manager.booking.core import Booking, BookingRepo, combine
from gym_manager.core.persistence import ClientRepo


class BookingTable(Model):
    when = DateTimeField(primary_key=True)
    court = CharField()
    client = ForeignKeyField(peewee.ClientTable, backref="bookings")
    end = TimeField()
    is_fixed = BooleanField()
    state = CharField()
    updated_by = CharField()

    class Meta:
        database = peewee._DATABASE


class SqliteBookingRepo(BookingRepo):

    def __init__(self, client_repo: ClientRepo, drop_table: bool = False) -> None:
        if drop_table:
            peewee._DATABASE.drop_tables([BookingTable])
        peewee._DATABASE.create_tables([BookingTable])
        self.client_repo = client_repo

    def add(self, booking: Booking):
        BookingTable.create(when=combine(booking.when, booking.start),
                            court=booking.court,
                            client=peewee.ClientTable.get_by_id(booking.client.dni.as_primitive()),
                            end=booking.end,
                            is_fixed=booking.is_fixed,
                            state=booking.state.name,
                            updated_by=booking.state.updated_by)

    def all(self, when: date) -> Generator[Booking, None, None]:
        year, month, day = when.year, when.month, when.day
        bookings_q = BookingTable.select().where(year == BookingTable.when.year, month == BookingTable.when.month,
                                                 day == BookingTable.when.day)
        for raw in bookings_q:
            start = time(raw.when.hour, raw.when.minute)
            yield Booking(raw.court, self.client_repo.get(raw.client_id), raw.is_fixed, when, start, raw.end)
