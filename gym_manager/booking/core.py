from __future__ import annotations

import abc
import itertools
from collections import namedtuple
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable, Generator

from gym_manager.core.base import Client, Activity, Transaction, OperationalError
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


class IBooking(abc.ABC):

    @property
    @abc.abstractmethod
    def start(self) -> time:
        """Start time of the booking.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def end(self) -> time:
        """End time of the booking.
        """
        raise NotImplementedError

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

    @abc.abstractmethod
    def update_state(self, new_state: str, updated_by: str) -> State:
        """Updates the current state of the booking, and return the previous one.
        """
        raise NotImplementedError


@dataclass
class Booking:
    id: int
    court: Court
    client: Client
    is_fixed: bool
    state: State
    when: date
    start: time
    end: time
    transaction: Transaction | None = None

    # noinspection PyChainedComparisons
    def collides(self, start: time, end: time) -> bool:
        """Determines if a hypothetical booking with the given start and end time will collide with this booking.

        There are four possible situations where a collision wont happen:
        1. start < end < b.start < b.end.
        2. start < end <= b.start < b.end.
        3. b.start < b.end < start < end.
        4. b.start < b.end <= start < end.
        The remaining possibilities involve a partial or total collision.

        Returns:
            True if there is a collision, False otherwise.
        """
        return not (start < self.start and end <= self.start or start >= self.end and end > self.end)

    def update_state(self, new_state: str, updated_by: str) -> State:
        """Updates the current state of the booking, and return the previous one.
        """
        prev_state = self.state
        self.state.update(new_state, updated_by)
        return prev_state


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
            start: time, end: time, minute_step: int, weeks_in_advance: int
    ) -> None:
        if end < start:
            raise ValueError(f"End time [end={end}] cannot be lesser than start time [start={start}]")

        self._courts = {name: Court(name, i + 1) for i, name in enumerate(courts_names)}
        self.durations = durations

        self.start, self.end = start, end
        self._blocks: dict[time, Block] = {block.start: block for block
                                           in self.create_blocks(start, end, minute_step)}

        self._bookings: dict[date, list[Booking]] = {}
        self.weeks_in_advance = weeks_in_advance

        self.activity = activity
        self.repo = repo

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

    def bookings(
            self, states: tuple[str, ...], when: date | None = None, filters: list[FilterValuePair] | None = None
    ) -> Iterable[tuple[Booking, int, int]]:
        """Retrieves bookings with its start and end block number.

        Args:
            states: allows filtering of bookings depending on their states.
            when: if given, filter bookings of that day. This filtering has priority over filtering with kwargs.
            **filters: if given, and *when* is None, filter bookings that pass the Filter implementations received.

        Raises:
            OperationalError if given both when and filters are missing.
        """
        if when is not None:
            for booking in self.repo.all(states, when):
                yield booking, *self.block_range(booking.start, booking.end)
        elif len(filters) > 0:
            for booking in self.repo.all(states, filters):
                yield booking, *self.block_range(booking.start, booking.end)
        else:
            raise OperationalError("Both 'when' and 'filters' arguments cannot be missing when querying bookings",
                                   when=when, filters=filters)

    def out_of_range(self, start_block: Block, duration: Duration) -> bool:
        """Returns True if a booking that starts at *start_block* and has the duration *duration* is out of the time
        range that is valid, False otherwise.
        """
        end = combine(date.min, start_block.start, duration).time()
        return start_block.start < self.start or end > self.end

    def booking_available(self, when: date, court: Court, start_block: Block, duration: Duration) -> bool:
        """Returns True if there is enough free time for a booking in *court*, that starts at *start_block* and has the
        duration *duration*. Otherwise, return False.

        Raises:
            OperationalError if the booking time is out of range.
        """
        if self.out_of_range(start_block, duration):
            raise OperationalError("Solicited booking time is out of range.", start_block=start_block,
                                   duration=duration, start=self.start, end=self.end)
        end = combine(date.min, start_block.start, duration).time()
        for booking in self.repo.all((BOOKING_TO_HAPPEN, BOOKING_PAID), when):
            if booking.court == court and booking.collides(start_block.start, end):
                return False
        return True

    def book(
            self, court: Court, client: Client, is_fixed: bool, when: date, start_block: Block, duration: Duration
    ) -> list[Booking]:
        """Creates a Booking with the given data.

        Raises:
            OperationalError if the booking time is out of range, or if there is no available time for the booking.
        """
        if self.out_of_range(start_block, duration):
            raise OperationalError("Solicited booking time is out of range.", start_block=start_block,
                                   duration=duration, start=self.start, end=self.end)
        if not self.booking_available(when, court, start_block, duration):
            raise OperationalError("There is no available time for the booking.", start=start_block.start,
                                   duration=duration)

        # Because the only needed thing is the time, and the date will be discarded, the ClassVar date.min is used.
        end = combine(date.min, start_block.start, duration).time()
        bookings = [self.repo.create(court, client, is_fixed, State(BOOKING_TO_HAPPEN), when, start_block.start, end)]

        # If the booking is fixed, then create *weeks_in_advance* more bookings in advance.
        if is_fixed:
            for i in range(self.weeks_in_advance - 1):
                when = when + ONE_WEEK_TD
                bookings.append(
                    self.repo.create(court, client, is_fixed, State(BOOKING_TO_HAPPEN), when, start_block.start, end)
                )

        return bookings

    def cancel(self, booking: Booking, responsible: str, cancel_fixed: bool = False):
        booking.update_state(BOOKING_CANCELLED, updated_by=responsible)
        # booking.is_fixed = not cancel_fixed
        self.repo.cancel(booking, cancel_fixed, self.weeks_in_advance)

    def register_charge(self, booking: Booking, transaction: Transaction):
        prev_state = booking.update_state(BOOKING_PAID, transaction.responsible.as_primitive())
        booking.transaction = transaction
        self.repo.update(booking, prev_state)
        if booking.is_fixed:  # ToDo add another booking in weeks_in_advance weeks
            when = booking.when + timedelta(self.weeks_in_advance)
            self.repo.create(booking.court, booking.client, booking.is_fixed, State(BOOKING_TO_HAPPEN),
                             when, booking.start, booking.end)


class BookingRepo(abc.ABC):
    @abc.abstractmethod
    def create(
            self, court: Court, client: Client, is_fixed: bool, state: State, when: date, start: time, end: time
    ) -> Booking:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, booking: Booking, prev_state: State):
        raise NotImplementedError

    @abc.abstractmethod
    def cancel(self, booking: Booking, cancel_fixed: bool = False, weeks_in_advance: int | None = None):
        raise NotImplementedError

    @abc.abstractmethod
    def all(
            self,
            states: tuple[str, ...] | None = None,
            when: date | None = None,
            filters: list[FilterValuePair] | None = None
    ) -> Generator[Booking, None, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        """Counts the number of bookings in the repository.
        """
        raise NotImplementedError
