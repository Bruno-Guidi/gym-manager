from __future__ import annotations


import itertools
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable, Generator

from gym_manager.core.base import Client


def time_range(start: time, end: time, minute_step: int, reverse: bool = False) -> Generator[time, None, None]:
    """Generates all the times between *start* and *end*, with steps of *minute_step* minutes.
    """
    step_delta = timedelta(hours=0, minutes=minute_step)
    start_delta = timedelta(hours=start.hour, minutes=start.minute)
    end_delta = timedelta(hours=end.hour, minutes=end.minute)

    if reverse:
        while end_delta >= start_delta:
            yield end_delta.seconds // 3600, (end_delta.seconds // 60) % 60
            end_delta -= step_delta
    else:
        while start_delta <= end_delta:
            yield start_delta.seconds // 3600, (start_delta.seconds // 60) % 60
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


class Court:

    def __init__(self, number: int, name: str) -> None:
        self.number = number
        self.name = name


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


@dataclass
class Booking:
    court: Court
    client: Client
    when: date
    start: time
    end: time


class BookingSystem:

    @classmethod
    def create_blocks(cls, start: time, end: time, minute_step: int) -> Iterable[Block]:
        for i, (block_start, block_end) in enumerate(itertools.pairwise(time_range(start, end, minute_step))):
            yield Block(i, block_start, block_end)

    def __init__(
            self, courts_names: tuple[str], durations: tuple[Duration], start: time, end: time, minute_step: int
    ) -> None:
        self.courts = (Court(i, name) for i, name in enumerate(courts_names))
        self.durations = durations
        self._bookings: dict[date, list[Booking]] = {}
        self._blocks: dict[time, Block] = {block.start: block for block
                                           in self.create_blocks(start, end, minute_step)}
        self.start, self.end = start, end

    def blocks(self, start: time | None = None) -> Iterable[Block]:
        """Yields booking blocks. If *from_* is given, then discard all blocks whose time is lesser than it.
        """
        if start is not None:
            yield from itertools.dropwhile(lambda block_start: block_start < start, self._blocks.values())
        else:
            yield from self._blocks.values()

    def range(self, start: time, end: time) -> tuple[int, int]:
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
        for booking in self._bookings[when]:
            yield booking, *self.range(booking.start, booking.end)

    def book(self, court: Court, client: Client, when: date, start_block: Block, duration: Duration) -> Booking:
        # Because the only needed thing is the time, and the date will be discarded, the ClassVar date.min is used.
        end = combine(date.min, start_block.start, duration).time()
        booking = Booking(court, client, when, start_block.start, end)

        return booking


