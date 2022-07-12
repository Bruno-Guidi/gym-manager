from datetime import date, time
from typing import Generator

from gym_manager import peewee
from gym_manager.booking.core import (
    Duration, BookingRepo, TempBooking, State, Court, FixedBooking, FixedBookingHandler, BookingSystem,
    BOOKING_TO_HAPPEN, Booking)
from gym_manager.booking.peewee import SqliteBookingRepo
from gym_manager.core.base import Client, Activity, String, Currency, Transaction, Number
from gym_manager.core.persistence import FilterValuePair


class MockBookingRepo(BookingRepo):

    def add(self, booking: Booking):
        pass

    def charge(self, booking: Booking, transaction: Transaction):
        pass

    def create(
            self, court: Court, client: Client, is_fixed: bool, state: State, when: date, start: time, end: time
    ) -> TempBooking:
        pass

    def update(self, booking: TempBooking, prev_state: State):
        pass

    def cancel(self, booking: TempBooking, cancel_fixed: bool = False, weeks_in_advance: int | None = None):
        pass

    def all_temporal(
            self, when: date | None = None, court: str | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[TempBooking, None, None]:
        # noinspection PyTypeChecker
        to_yield = [
            TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 11),
                        start=time(8, 0), end=time(9, 0)),
            TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 11),
                        start=time(12, 0), end=time(13, 0)),
            TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 11),
                        start=time(16, 0), end=time(17, 0)),
            TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 12),
                        start=time(16, 0), end=time(17, 0)),
            TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 12),
                        start=time(16, 0), end=time(17, 0))
        ]

        for booking in to_yield:
            if booking.when == when:
                yield booking

    def all_fixed(self) -> list[FixedBooking]:
        # noinspection PyTypeChecker
        return [FixedBooking("1", client=None, start=time(10, 0), end=time(12, 0), day_of_week=0),
                FixedBooking("1", client=None, start=time(13, 0), end=time(14, 0), day_of_week=0),
                FixedBooking("1", client=None, start=time(15, 0), end=time(16, 0), day_of_week=0),
                FixedBooking("2", client=None, start=time(15, 0), end=time(16, 0), day_of_week=1)]

    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        pass


def test_FixedBooking_isActive():
    # noinspection PyTypeChecker
    booking = FixedBooking("1", client=None, start=time(10, 0), end=time(12, 0), day_of_week=0)

    assert booking.is_active(date(2022, 7, 12))

    booking.activated_again = date(2022, 7, 19)
    assert (not booking.is_active(date(2022, 7, 12)) and not booking.is_active(date(2022, 7, 18))
            and booking.is_active(date(2022, 7, 19)))


def test_FixedBookingHandler_bookingAvailable():
    # noinspection PyTypeChecker
    fixed_handler = FixedBookingHandler(
        courts=("1", "2"), fixed_bookings=[
            FixedBooking("1", client=None, start=time(9, 0), end=time(10, 0), day_of_week=0),
            FixedBooking("1", client=None, start=time(10, 0), end=time(12, 0), day_of_week=0),
            FixedBooking("1", client=None, start=time(13, 0), end=time(14, 0), day_of_week=0),
            FixedBooking("1", client=None, start=time(15, 0), end=time(16, 0), day_of_week=0)
        ]
    )

    assert fixed_handler.booking_available(date(2022, 7, 11), "1", time(8, 0), Duration(60, "1h"))
    assert not fixed_handler.booking_available(date(2022, 7, 11), "1", time(8, 0), Duration(120, "2h"))
    assert not fixed_handler.booking_available(date(2022, 7, 11), "1", time(13, 0), Duration(120, "2h"))
    assert not fixed_handler.booking_available(date(2022, 7, 11), "1", time(15, 0), Duration(60, "1h"))
    assert fixed_handler.booking_available(date(2022, 7, 11), "1", time(16, 0), Duration(60, "1h"))
    # The booking "collides" with a booking of other court.
    assert fixed_handler.booking_available(date(2022, 7, 11), "2", time(8, 0), Duration(120, "2h"))


def test_FixedBookingHandler_bookingAvailable_withCancelledFixedBooking():
    booking_repo = MockBookingRepo()
    # noinspection PyTypeChecker
    fixed_handler = FixedBookingHandler(
        courts=("1", "2"), fixed_bookings=[
            FixedBooking("1", client=None, start=time(9, 0), end=time(10, 0), day_of_week=0,
                         activated_again=date(2022, 7, 18)),
            FixedBooking("1", client=None, start=time(10, 0), end=time(12, 0), day_of_week=0,
                         activated_again=date(2022, 7, 25)),
            FixedBooking("1", client=None, start=time(13, 0), end=time(14, 0), day_of_week=0),
            FixedBooking("1", client=None, start=time(15, 0), end=time(16, 0), day_of_week=0)
        ]
    )

    # In theory collides with the first booking, but because it is inactive it doesn't.
    assert fixed_handler.booking_available(date(2022, 7, 11), "1", time(9, 0), Duration(60, "1h"))
    # Collides with the first booking, because in the given date it is activated again.
    assert not fixed_handler.booking_available(date(2022, 7, 18), "1", time(9, 0), Duration(60, "1h"))
    # In theory collides with the second booking, but because it is inactive it doesn't.
    # But there is another booking that is active, so after all the new booking collides.
    assert not fixed_handler.booking_available(date(2022, 7, 18), "1", time(11, 0), Duration(180, "3h"))
    # In theory collides with the second booking, but because it is inactive it doesn't.
    assert fixed_handler.booking_available(date(2022, 7, 18), "1", time(10, 0), Duration(60, "1h"))
    # Collides with the second booking, because the date is after the date that its active again.
    assert not fixed_handler.booking_available(date(2022, 8, 1), "1", time(10, 0), Duration(60, "1h"))


def test_BookingSystem_bookingAvailable():
    dummy_activity = Activity(String("TestName", max_len=20), Currency(100), String("TestDescr", max_len=20))
    booking_repo = MockBookingRepo()
    # noinspection PyTypeChecker
    booking_system = BookingSystem(dummy_activity, booking_repo, courts_names=("1", "2"), durations=(),
                                   start=time(8, 0), end=time(18, 0), minute_step=60)

    assert booking_system.booking_available(date(2022, 7, 11), "1", time(9, 0), Duration(60, "1h"))
    assert booking_system.booking_available(date(2022, 7, 11), "1", time(17, 0), Duration(60, "1h"))
    assert not booking_system.booking_available(date(2022, 7, 11), "1", time(9, 0), Duration(120, "2h"))
    assert not booking_system.booking_available(date(2022, 7, 11), "1", time(15, 0), Duration(60, "1h"))


def test_integration_registerCharge_fixedBooking():
    # Set up.
    peewee.create_database(":memory:")

    activity_repo = peewee.SqliteActivityRepo()
    balance_repo = peewee.SqliteBalanceRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    booking_repo = SqliteBookingRepo(tuple(), client_repo, transaction_repo)

    dummy_client = Client(Number(1), String("TestCli", max_len=20), date(2022, 6, 6), date(2000, 1, 1),
                          String("TestTel", max_len=20), String("TestDir", max_len=20))
    client_repo.add(dummy_client)
    dummy_activity = Activity(String("TestName", max_len=20), Currency(100), String("TestDescr", max_len=20))
    # noinspection PyTypeChecker
    booking_system = BookingSystem(dummy_activity, booking_repo, courts_names=("1", "2"), durations=(),
                                   start=time(8, 0), end=time(18, 0), minute_step=60)

    booking_date = date(2022, 7, 11)
    booking = booking_system.book("1", dummy_client, True, booking_date, time(8, 0), Duration(60, "1h"))
    transaction = transaction_repo.create("dummy_type", booking_date, dummy_activity.price, "dummy_method",
                                          String("TestResp", max_len=20), "test_desc", dummy_client)

    booking_system.register_charge(booking, booking_date, transaction)

    # The length of all temporal bookings is checked to ensure that the charge was registered.
    assert booking.transaction == transaction and len([b for b in booking_repo.all_temporal()]) == 1
    assert booking.transaction == [b for b in booking_repo.all_fixed()][0].transaction
