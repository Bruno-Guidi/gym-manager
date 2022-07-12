from datetime import date, time, datetime
from typing import Generator

import pytest

from gym_manager import peewee
from gym_manager.booking.core import (
    Duration, BookingRepo, TempBooking, State, Court, FixedBooking, FixedBookingHandler, BookingSystem,
    Booking, time_range, Block)
from gym_manager.booking.peewee import SqliteBookingRepo, serialize_inactive_dates, deserialize_inactive_dates
from gym_manager.core.base import Client, Activity, String, Currency, Transaction, Number, OperationalError
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

    def cancel(self, booking: Booking, definitely_cancelled: bool = True):
        pass

    def log_cancellation(
            self, cancel_datetime: datetime, responsible: String, booking: Booking, definitely_cancelled: bool
    ):
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


def test_timeRange():
    assert [td for td in time_range(time(8, 0), time(8, 0), minute_step=30)] == [time(hour=8, minute=0)]

    expected = [time(hour=8, minute=0), time(hour=8, minute=30)]
    assert [td for td in time_range(time(8, 0), time(8, 30), minute_step=30)] == expected

    expected = [time(hour=8, minute=0), time(hour=8, minute=30),
                time(hour=9, minute=0), time(hour=9, minute=30)]
    assert [td for td in time_range(time(8, 0), time(9, 30), minute_step=30)] == expected


def test_serialization_inactiveDates():
    result = [{"from": "2022-10-10", "to": "2022-10-12"}, {"from": "2022-10-12", "to": "2022-10-14"},
              {"from": "2022-10-14", "to": "2022-10-16"}, {"from": "2022-10-16", "to": "2022-10-18"}]
    to_serialize = [{"from": date(2022, 10, 10), "to": date(2022, 10, 12)},
                    {"from": date(2022, 10, 12), "to": date(2022, 10, 14)},
                    {"from": date(2022, 10, 14), "to": date(2022, 10, 16)},
                    {"from": date(2022, 10, 16), "to": date(2022, 10, 18)}]

    assert result == serialize_inactive_dates(to_serialize)
    assert to_serialize == deserialize_inactive_dates(result)

    assert to_serialize == deserialize_inactive_dates((serialize_inactive_dates(to_serialize)))
    assert result == serialize_inactive_dates(deserialize_inactive_dates(result))


def test_TempBooking_collides():
    # noinspection PyTypeChecker
    b = TempBooking("dummy_court", client=None, start=time(8, 30), end=time(12, 0), when=None)

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
    booking_system = BookingSystem(courts_names=("1", "2"), durations=(), start=time(8, 0), end=time(12, 0),
                                   minute_step=60,
                                   activity=None, repo=MockBookingRepo())

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
    booking_system = BookingSystem(courts_names=("1", "2"), durations=(), start=time(8, 0), end=time(12, 0),
                                   minute_step=60, activity=None, repo=MockBookingRepo())

    # start and end in range.
    assert booking_system.block_range(time(8, 0), time(12, 0)) == (0, 4)
    with pytest.raises(OperationalError):
        # start out of range.
        booking_system.block_range(time(7, 0), time(12, 0))
        # end out of range.
        booking_system.block_range(time(8, 0), time(12, 30))


def test_FixedBooking_isActive():
    # noinspection PyTypeChecker
    booking = FixedBooking("1", client=None, start=time(10, 0), end=time(12, 0), day_of_week=0)

    assert booking.is_active(date(2022, 7, 12))

    # There is only one period of inactivity.
    booking.inactive_dates = [{"from": date(2022, 7, 12), "to": date(2022, 7, 19)}]
    assert (not booking.is_active(date(2022, 7, 12)) and not booking.is_active(date(2022, 7, 18))
            and booking.is_active(date(2022, 7, 19)))

    # There are two consecutive periods of inactivity.
    booking.inactive_dates = [{"from": date(2022, 7, 12), "to": date(2022, 7, 19)},
                              {"from": date(2022, 7, 19), "to": date(2022, 7, 26)}]
    assert (not booking.is_active(date(2022, 7, 12)) and not booking.is_active(date(2022, 7, 19))
            and not booking.is_active(date(2022, 7, 25)) and booking.is_active(date(2022, 7, 26)))

    # There are two non-consecutive periods of inactivity.
    booking.inactive_dates = [{"from": date(2022, 7, 12), "to": date(2022, 7, 19)},
                              {"from": date(2022, 7, 26), "to": date(2022, 8, 2)}]
    assert (not booking.is_active(date(2022, 7, 12)) and booking.is_active(date(2022, 7, 19))
            and not booking.is_active(date(2022, 7, 26)) and not booking.is_active(date(2022, 8, 1))
            and booking.is_active(date(2022, 8, 2)))


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
    MockBookingRepo()
    # noinspection PyTypeChecker
    fixed_handler = FixedBookingHandler(
        courts=("1", "2"), fixed_bookings=[
            FixedBooking("1", client=None, start=time(9, 0), end=time(10, 0), day_of_week=0,
                         inactive_dates=[{"from": date(2022, 7, 18), "to": date(2022, 7, 25)}]),
            FixedBooking("1", client=None, start=time(10, 0), end=time(12, 0), day_of_week=0,
                         inactive_dates=[{"from": date(2022, 7, 25), "to": date(2022, 8, 1)}]),
            FixedBooking("1", client=None, start=time(13, 0), end=time(14, 0), day_of_week=0),
            FixedBooking("1", client=None, start=time(15, 0), end=time(16, 0), day_of_week=0)
        ]
    )

    # In theory collides with the first booking, but because it is inactive it doesn't.
    assert fixed_handler.booking_available(date(2022, 7, 18), "1", time(9, 0), Duration(60, "1h"))
    # Collides with the first booking, because in the given date it is activated again.
    assert not fixed_handler.booking_available(date(2022, 7, 25), "1", time(9, 0), Duration(60, "1h"))
    # In theory collides with the second booking, but because it is inactive it doesn't.
    # But there is another booking that is active, so after all the new booking collides.
    assert not fixed_handler.booking_available(date(2022, 7, 25), "1", time(11, 0), Duration(180, "3h"))
    # In theory collides with the second booking, but because it is inactive it doesn't.
    assert fixed_handler.booking_available(date(2022, 7, 25), "1", time(10, 0), Duration(60, "1h"))
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


def test_BookingSystem_bookings():
    dummy_activity = Activity(String("TestName", max_len=20), Currency(100), String("TestDescr", max_len=20))
    booking_repo = MockBookingRepo()
    # noinspection PyTypeChecker
    booking_system = BookingSystem(dummy_activity, booking_repo, courts_names=("1", "2"), durations=(),
                                   start=time(8, 0), end=time(18, 0), minute_step=60)

    # noinspection PyTypeChecker
    expected = [TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 11),
                            start=time(8, 0), end=time(9, 0)),
                TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 11),
                            start=time(12, 0), end=time(13, 0)),
                TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 11),
                            start=time(16, 0), end=time(17, 0)),
                FixedBooking("1", client=None, start=time(10, 0), end=time(12, 0), day_of_week=0),
                FixedBooking("1", client=None, start=time(13, 0), end=time(14, 0), day_of_week=0),
                FixedBooking("1", client=None, start=time(15, 0), end=time(16, 0), day_of_week=0)]
    result = [b for b, _, _ in booking_system.bookings(date(2022, 7, 11))]
    assert result == expected

    # noinspection PyTypeChecker
    expected = [FixedBooking("1", client=None, start=time(10, 0), end=time(12, 0), day_of_week=0),
                FixedBooking("1", client=None, start=time(13, 0), end=time(14, 0), day_of_week=0),
                FixedBooking("1", client=None, start=time(15, 0), end=time(16, 0), day_of_week=0)]
    result = [b for b, _, _ in booking_system.bookings(date(2022, 7, 18))]
    assert result == expected

    # noinspection PyTypeChecker
    expected = [TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 12),
                            start=time(16, 0), end=time(17, 0)),
                TempBooking("1", client=None, is_fixed=False, when=date(2022, 7, 12),
                            start=time(16, 0), end=time(17, 0)),
                FixedBooking("2", client=None, start=time(15, 0), end=time(16, 0), day_of_week=1)]
    result = [b for b, _, _ in booking_system.bookings(date(2022, 7, 12))]
    assert result == expected

    assert [] == [b for b, _, _ in booking_system.bookings(date(2022, 7, 13))]


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
