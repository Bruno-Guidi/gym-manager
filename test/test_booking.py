from datetime import time, date
from typing import Generator

import pytest

from gym_manager.booking.core import time_range, Booking, Court, BookingSystem, Block, BookingRepo, State, Duration
from gym_manager.core.base import OperationalError, Client


class MockBookingRepo(BookingRepo):

    def __init__(self, bookings: list[Booking]):
        self.bookings = bookings

    def create(self, court: Court, client: Client, is_fixed: bool, state: State, when: date, start: time,
               end: time) -> Booking:
        pass

    def update(self, booking: Booking, prev_state: State):
        pass

    def all(
            self, courts: dict[str, Court], states: tuple[str, ...], when: date | None = None, **filters
    ) -> Generator[Booking, None, None]:
        yield from self.bookings


def test_timeRange():
    assert [td for td in time_range(time(8, 0), time(8, 0), minute_step=30)] == [time(hour=8, minute=0)]

    expected = [time(hour=8, minute=0), time(hour=8, minute=30)]
    assert [td for td in time_range(time(8, 0), time(8, 30), minute_step=30)] == expected

    expected = [time(hour=8, minute=0), time(hour=8, minute=30),
                time(hour=9, minute=0), time(hour=9, minute=30)]
    assert [td for td in time_range(time(8, 0), time(9, 30), minute_step=30)] == expected


def test_Booking_collides():
    # noinspection PyTypeChecker
    b = Booking(0, Court("court", 0), client=None, is_fixed=None, state=None, when=None, start=time(8, 30),
                end=time(12, 0))

    # start < b.start < end < b.end.
    assert b.collides(start=time(8, 0), end=time(11, 0))
    # start < b.start < end == b.end.
    assert b.collides(start=time(8, 0), end=time(12, 0))
    # start < b.start < b.end < end.
    assert b.collides(start=time(8, 0), end=time(13, 0))
    # start == b.start < end < b.end.
    assert b.collides(start=time(8, 30), end=time(11, 0))
    # start == b.start < end == b.end.
    assert b.collides(start=time(8, 30), end=time(12, 0))
    # start == b.start < b.end < end.
    assert b.collides(start=time(9, 30), end=time(13, 0))
    # start > b.start < end < b.end.
    assert b.collides(start=time(9, 30), end=time(11, 0))
    # start > b.start < end == b.end.
    assert b.collides(start=time(9, 30), end=time(12, 0))
    # start > b.start < b.end < end.
    assert b.collides(start=time(9, 30), end=time(13, 0))
    # start < end < b.start < b.end.
    assert not b.collides(start=time(7, 0), end=time(8, 0))
    # start < end <= b.start < b.end.
    assert not b.collides(start=time(7, 0), end=time(8, 30))
    # b.start < b.end < start < end.
    assert not b.collides(start=time(13, 0), end=time(14, 0))
    # b.start < b.end <= start < end.
    assert not b.collides(start=time(12, 0), end=time(14, 0))


def test_BookingSystem_blocks():
    # noinspection PyTypeChecker
    booking_system = BookingSystem(courts_names=(), durations=(), start=time(8, 0), end=time(12, 0), minute_step=60,
                                   activity=None, repo=None, accounting_system=None)

    # start is under the booking system start.
    expected = [Block(0, time(8, 0), end=time(9, 0)), Block(1, time(9, 0), end=time(10, 0)),
                Block(2, time(10, 0), end=time(11, 0)), Block(3, time(11, 0), end=time(12, 0))]
    assert expected == [b for b in booking_system.blocks(start=time(7, 0))]

    # start is over the booking system start.
    expected = [Block(0, time(10, 0), end=time(11, 0)), Block(0, time(11, 0), end=time(12, 0))]
    assert expected == [b for b in booking_system.blocks(start=time(9, 30))]

    # start is over the booking system end
    assert [] == [b for b in booking_system.blocks(start=time(12, 30))]


def test_BookingSystem_blockRange():
    # noinspection PyTypeChecker
    booking_system = BookingSystem(courts_names=(), durations=(), start=time(8, 0), end=time(12, 0), minute_step=60,
                                   activity=None, repo=None, accounting_system=None)

    # start and end in range.
    assert booking_system.block_range(time(8, 0), time(12, 0)) == (0, 4)
    with pytest.raises(OperationalError):
        # start out of range.
        booking_system.block_range(time(7, 0), time(12, 0))
        # end out of range.
        booking_system.block_range(time(8, 0), time(12, 30))


def test_BookingSystem_bookings():
    # filter with states
    # filter without states
    # filter with date
    # filter with kwargs
    pass


def test_BookingSystem_outOfRange():
    # booking under booking system start
    # booking over booking system end
    # booking in booking system range
    pass


# noinspection PyTypeChecker
def test_BookingSystem_bookingAvailable():
    duration2h, duration3h, duration4h, duration5h = Duration(120, ""), Duration(180, ""), \
                                                     Duration(240, ""), Duration(300, "")
    repo = MockBookingRepo([Booking(0, Court("1", 0), client=None, is_fixed=None, state=None,
                                    when=None, start=time(9, 0), end=time(10, 0)),
                            Booking(1, Court("1", 0), client=None, is_fixed=None, state=None,
                                    when=None, start=time(11, 00), end=time(12, 0))])
    booking_system = BookingSystem(courts_names=(), durations=(), start=time(8, 0), end=time(13, 0), minute_step=60,
                                   activity=None, repo=repo, accounting_system=None)

    # booking starts before an existing booking and ends after another one.
    assert not booking_system.booking_available(when=None, court=Court("1", 0),
                                                start_block=Block(0, time(8, 0), time(9, 0)),
                                                duration=duration5h)

    # booking starts before an existing booking and ends at the middle another one.
    assert not booking_system.booking_available(when=None, court=Court("1", 0),
                                                start_block=Block(0, time(8, 0), time(9, 0)),
                                                duration=duration3h)
    assert not booking_system.booking_available(when=None, court=Court("1", 0),
                                                start_block=Block(0, time(8, 0), time(9, 0)),
                                                duration=duration4h)

    # booking starts at the middle of an existing booking and ends after another one.
    assert not booking_system.booking_available(when=None, court=Court("1", 0),
                                                start_block=Block(0, time(9, 0), time(10, 0)),
                                                duration=duration4h)

    # booking starts at the middle of an existing booking and ends at the middle another one.
    assert not booking_system.booking_available(when=None, court=Court("1", 0),
                                                start_block=Block(0, time(9, 0), time(10, 0)),
                                                duration=duration2h)


def test_BookingSystem_cancel():
    # cancel of a fixed booking only for the day
    # cancel of a fixed booking forever
    # cancel of a not fixed booking
    pass


def test_BookingSystem_registerCharge():
    # a new booking is created if the booking is fixed.
    # no new booking is created if the booking is not fixed.
    pass
