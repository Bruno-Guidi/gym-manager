from datetime import date, time
from typing import Generator

from gym_manager.booking.core import (
    Duration, BookingRepo, Booking, State, Court, FixedBooking, FixedBookingHandler)
from gym_manager.core.base import Client
from gym_manager.core.persistence import FilterValuePair


class MockBookingRepo(BookingRepo):

    def create(
            self, court: Court, client: Client, is_fixed: bool, state: State, when: date, start: time, end: time
            ) -> Booking:
        pass

    def update(self, booking: Booking, prev_state: State):
        pass

    def cancel(self, booking: Booking, cancel_fixed: bool = False, weeks_in_advance: int | None = None):
        pass

    def all(
            self, states: tuple[str, ...] | None = None, when: date | None = None,
            filters: list[FilterValuePair] | None = None
            ) -> Generator[Booking, None, None]:
        pass

    def all_fixed(self) -> list[FixedBooking]:
        # noinspection PyTypeChecker
        return [FixedBooking("1", client=None, start=time(9, 0), end=time(10, 0), day_of_week=0),
                FixedBooking("1", client=None, start=time(10, 0), end=time(12, 0), day_of_week=0),
                FixedBooking("1", client=None, start=time(13, 0), end=time(14, 0), day_of_week=0),
                FixedBooking("1", client=None, start=time(15, 0), end=time(16, 0), day_of_week=0)]

    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        pass


def test_FixedBookingHandler_bookingAvailable():
    booking_repo = MockBookingRepo()
    fixed_handler = FixedBookingHandler(courts=("1", ), fixed_bookings=booking_repo.all_fixed())

    assert fixed_handler.booking_available(0, "1", time(8, 0), Duration(60, "1h"))
    assert not fixed_handler.booking_available(0, "1", time(8, 0), Duration(120, "2h"))
    assert not fixed_handler.booking_available(0, "1", time(13, 0), Duration(120, "2h"))
    assert not fixed_handler.booking_available(0, "1", time(15, 0), Duration(60, "1h"))
    assert fixed_handler.booking_available(0, "1", time(16, 0), Duration(60, "1h"))


def test_bookingAvailable_withNonFixed():
    pass


def test_bookingAvailable_withFixedAndNonFixed():
    pass
