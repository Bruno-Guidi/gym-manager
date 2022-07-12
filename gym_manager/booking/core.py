from __future__ import annotations

import abc
import itertools
from collections import namedtuple
from datetime import date, datetime, time, timedelta
from typing import Iterable, Generator, TypeAlias

from gym_manager.core.base import Client, Activity, Transaction, OperationalError, String
from gym_manager.core.persistence import FilterValuePair

BOOKING_TO_HAPPEN, BOOKING_CANCELLED, BOOKING_PAID = "To happen", "Cancelled", "Paid"

ONE_WEEK_TD = timedelta(weeks=1)
ONE_DAY_TD = timedelta(days=1)


def time_range(start: time, end: time, minute_step: int) -> Generator[time, None, None]:
    """Generates all the times between *start* and *end* (inclusive), with steps of *minute_step* minutes.
    """
    step_delta = timedelta(hours=0, minutes=minute_step)
    start_delta = timedelta(hours=start.hour, minutes=start.minute)
    end_delta = timedelta(hours=end.hour, minutes=end.minute)

    while start_delta <= end_delta:
        yield time(start_delta.seconds // 3600, (start_delta.seconds // 60) % 60)
        start_delta += step_delta


def combine(base_date: date, start: time | None = None, duration: Duration | None = None) -> datetime:
    """Creates a new datetime object based on *base_date* and *start*, and then adds to it the given *duration*.
    """
    if base_date is None:
        base_date = datetime.today()
    if start is None:
        start = time()
    dt = datetime.combine(base_date, start)
    if duration is not None:
        dt = dt + duration.as_timedelta
    return dt


def current_block_start(blocks: Iterable[Block], when: date) -> time:
    """Returns the start time of the first block whose start time hasn't passed yet.
    """
    blocks_it = blocks
    if when == date.today():
        blocks_it = itertools.dropwhile(lambda b: b.start < datetime.now().time(), blocks)

    for block in blocks_it:
        return block.start


Court = namedtuple("Court", ["name", "id"])


class Duration:

    def __init__(self, minutes: int, as_str: str) -> None:
        self.minutes = minutes
        self.as_str = as_str
        self.as_timedelta = timedelta(minutes=minutes)


class Block:

    def __init__(self, number: int, start: time, end: time) -> None:
        self.number = number
        self.start = start
        self.end = end
        self.str_range = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"

    def __eq__(self, other: Block) -> bool:
        return self.start == other.start and self.end == other.end


class State:

    def __init__(self, name: str, updated_by: str | None = None) -> None:
        self._name = name
        self._updated_by = updated_by if updated_by is not None else "-"

    @property
    def name(self) -> str:
        return self._name

    @property
    def updated_by(self) -> str:
        return self._updated_by

    def update(self, new_state: str, updated_by: str):
        self._name = new_state
        self._updated_by = updated_by


class Booking(abc.ABC):

    def __init__(self, court: str, client: Client, start: time, end: time, transaction: Transaction | None = None):
        self.court = court
        self.client = client
        self.start = start
        self.end = end
        self.transaction = transaction

    # noinspection PyChainedComparisons
    def collides(self, start: time, end: time) -> bool:
        """Determines if a hypothetical booking with the given start and end time will collide with this booking.

        There are four possible situations where a collision won't happen:
        1. start < end < b.start < b.end.
        2. start < end <= b.start < b.end.
        3. b.start < b.end < start < end.
        4. b.start < b.end <= start < end.
        The remaining possibilities involve a partial or total collision.

        Returns:
            True if there is a collision, False otherwise.
        """
        return not (start < self.start and end <= self.start or start >= self.end and end > self.end)

    @property
    @abc.abstractmethod
    def when(self) -> date:
        raise NotImplementedError

    @when.setter
    @abc.abstractmethod
    def when(self, when: date):
        raise NotImplementedError

    @abc.abstractmethod
    def cancel(self, when: date):
        """Do something after the booking is cancelled. What will be done depends on each implementation.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_state(self, new_state: str, updated_by: str) -> State:
        """Updates the current state of the booking, and return the previous one.
        """
        raise NotImplementedError


class TempBooking(Booking):

    def __init__(
            self, court: str, client: Client, start: time, end: time, when: date,
            transaction: Transaction | None = None, is_fixed: bool = False
    ):
        super().__init__(court, client, start, end, transaction)
        self._when = when
        self.is_fixed = is_fixed

    def __eq__(self, other: TempBooking) -> bool:
        if isinstance(other, type(self)):
            return (self.court == other.court and self.when == other.when and self.start == other.start
                    and self.end == other.end)
        return NotImplemented

    @property
    def when(self) -> date:
        return self._when

    @when.setter
    def when(self, when: date):
        # Checks that the date of the booking remains the same. If it is the same, then pass and do nothing.
        if when != self.when:
            raise OperationalError(f"It is not possible to change the attribute 'when' of a 'TempBooking'.")

    def cancel(self, when: date):
        """Does nothing.
        """
        pass

    def update_state(self, new_state: str, updated_by: str) -> State:
        """Updates the current state of the booking, and return the previous one.
        """
        prev_state = self.state
        self.state.update(new_state, updated_by)
        return prev_state


class FixedBooking(Booking):

    def __init__(
            self, court: str, client: Client, start: time, end: time, day_of_week: int,
            inactive_dates: list[dict[str, date]] | None = None, transaction: Transaction | None = None
    ):
        super().__init__(court, client, start, end, transaction)
        self.day_of_week = day_of_week
        # In theory this attr should be set to None after the date passes, but because of how collides(args) is
        # implemented, there is no need to do it.
        self.inactive_dates = [] if inactive_dates is None else inactive_dates
        self._last_when: date | None = None

    def __eq__(self, other: FixedBooking) -> bool:
        if isinstance(other, type(self)):
            return (self.court == other.court and self.day_of_week == other.day_of_week and self.start == other.start
                    and self.end == other.end)
        return NotImplemented

    def collides(self, start: time, end: time, when: date | None = None) -> bool:
        if self.is_active(when):
            return super().collides(start, end)
        # If *when* is previous to the date when the fixed booking is "active" again, then there is no collision.
        # Note: when < date (when before date) is equivalent to when >= date.
        return False

    @property
    def when(self) -> date:
        if self._last_when is None:
            raise OperationalError(f"The 'FixedBooking' with [day_of_week={self.day_of_week}, start={self.start},"
                                   f"end={self.end}] has not happened at least one time.")
        return self._last_when

    @when.setter
    def when(self, when: date):
        self._last_when = when

    def cancel(self, when: date):
        """Adds a new entry in the inactive dates list.
        """
        self.inactive_dates.append({"from": when, "to": when + ONE_WEEK_TD})

    def is_active(self, reference_date: date) -> bool:
        """Determines if the booking is active. The booking will be active if *reference_date* is not between any of the
        existing date ranges in *self.inactive_dates*.
        """
        for date_range in self.inactive_dates:
            # If the booking is cancelled for one week on '2022/07/12', then the booking on '2022/07/12' is not active,
            # and on '2022/07/19' it is active again.
            # noinspection PyChainedComparisons
            if reference_date >= date_range["from"] and reference_date < date_range["to"]:
                return False
        return True

    def update_state(self, new_state: str, updated_by: str) -> State:
        """Updates the current state of the booking, and return the previous one.
        """
        raise NotImplementedError


DayBookings: TypeAlias = dict[time, FixedBooking]
CourtBookings: TypeAlias = dict[str, DayBookings]


class FixedBookingHandler:
    def __init__(self, courts: Iterable[str], fixed_bookings: Iterable[FixedBooking]):
        self._bookings: list[CourtBookings] = [{court: {} for court in courts} for _ in range(0, 7)]
        for booking in fixed_bookings:
            self._bookings[booking.day_of_week][booking.court][booking.start] = booking

    def booking_available(self, when: date, court: str, start: time, duration: Duration) -> bool:
        day_bookings = self._bookings[when.weekday()][court].values()
        end = combine(date.min, start, duration).time()
        for fixed_booking in day_bookings:
            if fixed_booking.collides(start, end, when):
                return False
        return True

    def all(self, when: date) -> Iterable[FixedBooking]:
        court_bookings: CourtBookings = self._bookings[when.weekday()]
        for day_bookings in court_bookings.values():
            for fixed_booking in day_bookings.values():
                if fixed_booking.is_active(when):
                    yield fixed_booking


class BookingSystem:
    """API to do booking related things.
    """

    @classmethod
    def create_blocks(cls, start: time, end: time, minute_step: int) -> Iterable[Block]:
        """Create blocks from *start* to *end*, with a difference of *minute_step* between each block.
        """
        for i, (block_start, block_end) in enumerate(itertools.pairwise(time_range(start, end, minute_step))):
            yield Block(i, block_start, block_end)

    def __init__(
            self, activity: Activity, repo: BookingRepo, durations: tuple[Duration, ...], courts_names: tuple[str, ...],
            start: time, end: time, minute_step: int
    ) -> None:
        if end < start:
            raise ValueError(f"End time [end={end}] cannot be lesser than start time [start={start}]")

        self._courts = {name: Court(name, i + 1) for i, name in enumerate(courts_names)}
        self.durations = durations

        self.start, self.end = start, end
        self._blocks: dict[time, Block] = {block.start: block for block
                                           in self.create_blocks(start, end, minute_step)}

        self._bookings: dict[date, list[TempBooking]] = {}

        self.activity = activity
        self.repo = repo
        self.fixed_booking_handler = FixedBookingHandler(courts_names, self.repo.all_fixed())

    def courts(self) -> Iterable[Court]:
        return self._courts.values()

    def blocks(self, start: time | None = None) -> Iterable[Block]:
        """Yields booking blocks. If *start* is given, then discard all blocks whose start time is lesser than *start*.
        """
        if start is None or start < self.start:
            yield from self._blocks.values()
        else:
            yield from itertools.dropwhile(lambda block: block.start < start, self._blocks.values())

    def block_range(self, start: time, end: time) -> tuple[int, int]:
        """Returns the start and end block number for the given *start* and *end* time.

        Raises:
            OperationalError if given start or end are not valid.
        """
        if start < self.start or end > self.end:
            raise OperationalError("Invalid start and/or end time", valid_start=self.start, valid_end=self.end,
                                   start=start, end=end)
        if end == self.end:
            # Because there is no Block whose start time is equal to *self.end*, if *self._blocks* is indexed with
            # *end*, a KeyError will be raised. This is the case when a Booking ends in the last valid booking hour.
            # To avoid the KeyError, if *end* == *self.end*, then the end number will be the amount of blocks in the
            # system.
            return self._blocks[start].number, len(self._blocks)
        else:
            return self._blocks[start].number, self._blocks[end].number

    def bookings(self, when: date) -> Iterable[tuple[TempBooking, int, int]]:
        """Retrieves bookings with its start and end block number.
        """
        bookings = itertools.chain.from_iterable((self.repo.all_temporal(when), self.fixed_booking_handler.all(when)))
        for booking in bookings:
            yield booking, *self.block_range(booking.start, booking.end)

    def out_of_range(self, start: time, duration: Duration) -> bool:
        """Returns True if a booking that starts at *start_block* and has the duration *duration* is out of the time
        range that is valid, False otherwise.
        """
        end = combine(date.min, start, duration).time()
        return start < self.start or end > self.end

    def booking_available(self, when: date, court: str, start: time, duration: Duration) -> bool:
        """Returns True if there is enough free time for a booking in *court*, that starts at *start_block* and has the
        duration *duration*. Otherwise, return False.

        Raises:
            OperationalError if the booking time is out of range.
        """
        if self.out_of_range(start, duration):
            raise OperationalError(f"Solicited booking time [start={start}, duration={duration.as_timedelta}] is out "
                                   f"of the range [booking_start={self.start}, booking_end={self.end}].")

        if not self.fixed_booking_handler.booking_available(when, court, start, duration):
            return False

        end = combine(date.min, start, duration).time()
        for booking in self.repo.all_temporal(when, court):
            if booking.collides(start, end):
                return False
        return True

    def book(
            self, court: str, client: Client, is_fixed: bool, when: date, start: time, duration: Duration
    ) -> Booking:
        """Creates a Booking with the given data.

        Raises:
            OperationalError if the booking time is out of range, or if there is no available time for the booking.
        """
        if self.out_of_range(start, duration):
            raise OperationalError(f"Solicited booking time [start={start}, duration={duration.as_timedelta}] is out "
                                   f"of the range [booking_start={self.start}, booking_end={self.end}].")
        if not self.booking_available(when, court, start, duration):
            raise OperationalError(f"Solicited booking time [start={start}, duration={duration.as_timedelta}] collides "
                                   f"with existing booking/s.")

        # Because the only needed thing is the time, and the date will be discarded, the ClassVar date.min is used.
        end = combine(date.min, start, duration).time()
        if is_fixed:
            booking = FixedBooking(court, client, start, end, when.weekday())
        else:
            booking = TempBooking(court, client, start, end, when)

        self.repo.add(booking)
        return booking

    def cancel(
            self, booking: Booking, responsible: String, booking_date: date, definitely_cancelled: bool = True,
            cancel_date: date | None = None
    ):
        if not definitely_cancelled:
            booking.cancel(booking_date)
        cancel_date = date.today() if cancel_date is None else cancel_date
        # ToDo here should go the call to ResponsibleLogger, so the id of the new log is generated, and can be used to as FK in the cancellations log.
        self.repo.cancel(booking, responsible, cancel_date, definitely_cancelled)

    def register_charge(self, booking: Booking, booking_date: date, transaction: Transaction):
        booking.transaction, booking.when = transaction, booking_date
        self.repo.charge(booking, transaction)


class BookingRepo(abc.ABC):

    @abc.abstractmethod
    def add(self, booking: Booking):
        raise NotImplementedError

    @abc.abstractmethod
    def charge(self, booking: Booking, transaction: Transaction):
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, booking: TempBooking, prev_state: State):
        raise NotImplementedError

    @abc.abstractmethod
    def cancel(self, booking: Booking, definitely_cancelled: bool = True):
        raise NotImplementedError

    @abc.abstractmethod
    def all_temporal(
            self, when: date | None = None, court: str | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[TempBooking, None, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def all_fixed(self) -> Generator[FixedBooking, None, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        """Counts the number of bookings in the repository.
        """
        raise NotImplementedError
