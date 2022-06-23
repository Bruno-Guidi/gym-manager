from __future__ import annotations

import abc
import itertools
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable, Generator

from gym_manager.core.base import Client


BOOKING_TO_HAPPEN, BOOKING_CANCELLED, BOOKING_PAID = "To happen", "Cancelled", "Paid"


def time_range(start: time, end: time, minute_step: int, reverse: bool = False) -> Generator[time, None, None]:
    """Generates all the times between *start* and *end*, with steps of *minute_step* minutes.
    """
    step_delta = timedelta(hours=0, minutes=minute_step)
    start_delta = timedelta(hours=start.hour, minutes=start.minute)
    end_delta = timedelta(hours=end.hour, minutes=end.minute)

    if reverse:
        while end_delta >= start_delta:
            yield time(end_delta.seconds // 3600, (end_delta.seconds // 60) % 60)
            end_delta -= step_delta
    else:
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


@dataclass
class Booking:
    court: str
    client: Client
    is_fixed: bool
    when: date
    start: time
    end: time
    state: State = State(BOOKING_TO_HAPPEN)

    # noinspection PyChainedComparisons
    def collides(self, start: time, end: time) -> bool:
        """Determines if an hypothetical booking with the given start and end time will collide with this booking.

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


class BookingSystem:

    @classmethod
    def create_blocks(cls, start: time, end: time, minute_step: int) -> Iterable[Block]:
        for i, (block_start, block_end) in enumerate(itertools.pairwise(time_range(start, end, minute_step))):
            yield Block(i, block_start, block_end)

    def __init__(
            self, courts_names: tuple[str, ...], durations: tuple[Duration, ...], start: time, end: time,
            minute_step: int, repo: BookingRepo
    ) -> None:
        self._courts = {name: i for i, name in enumerate(courts_names)}
        self.durations = durations

        self.start, self.end = start, end
        self._blocks: dict[time, Block] = {block.start: block for block
                                           in self.create_blocks(start, end, minute_step)}

        self._bookings: dict[date, list[Booking]] = {}
        self.repo = repo

    def blocks(self, start: time | None = None) -> Iterable[Block]:
        """Yields booking blocks. If *from_* is given, then discard all blocks whose time is lesser than it.
        """
        if start is not None:
            yield from itertools.dropwhile(lambda block_start: block_start < start, self._blocks.values())
        else:
            yield from self._blocks.values()

    def block_range(self, start: time, end: time) -> tuple[int, int]:
        """Returns the start and end block number for the given *start* and *end* time.
        """
        if end == self.end:
            # Because there is no Block whose start time is equal to *self.end*, if *self._blocks* is indexed with
            # *end*, a KeyError will be raised. This is the case when a Booking ends in the last valid booking hour.
            # To avoid the KeyError, if *end* == *self.end*, then the end number will be the amount of blocks in the
            # system.
            return self._blocks[start].number, len(self._blocks)
        else:
            return self._blocks[start].number, self._blocks[end].number

    def bookings(self, when: date) -> Iterable[tuple[Booking, int, int]]:
        """Yields bookings and its start and end block number for the given *when*.
        """
        for booking in self.repo.all(when):
            yield booking, *self.block_range(booking.start, booking.end)

    def out_of_range(self, start_block: Block, duration: Duration) -> bool:
        end = combine(date.min, start_block.start, duration).time()
        return start_block.start < self.start or end > self.end

    def booking_available(self, when: date, court: str, start_block: Block, duration: Duration) -> bool:
        end = combine(date.min, start_block.start, duration).time()
        for booking in self.repo.all(when):
            if booking.collides(start_block.start, end):
                return False
        return True

    def book(
            self, court: str, client: Client, when: date, start_block: Block, duration: Duration, is_fixed: bool
    ) -> Booking:
        if self.out_of_range(start_block, duration):
            raise ValueError()
        if not self.booking_available(when, court, start_block, duration):
            raise ValueError()

        # Because the only needed thing is the time, and the date will be discarded, the ClassVar date.min is used.
        end = combine(date.min, start_block.start, duration).time()
        booking = Booking(court, client, is_fixed, when, start_block.start, end)
        self.repo.add(booking)

        return booking


class BookingRepo(abc.ABC):
    @abc.abstractmethod
    def add(self, booking: Booking):
        raise NotImplementedError

    @abc.abstractmethod
    def all(self, when: date) -> Generator[Booking, None, None]:
        raise NotImplementedError