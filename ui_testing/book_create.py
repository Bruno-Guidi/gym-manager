import sys
from datetime import date, time
from typing import Generator

from PyQt5.QtWidgets import QApplication

from gym_manager.booking.core import BookingRepo, Booking, State, Court, BookingSystem, Duration
from gym_manager.core.base import Client, Number, Activity, String, Currency
from gym_manager.core.persistence import ClientRepo, FilterValuePair
from ui.booking.operations import BookUI


class MockClientRepo(ClientRepo):

    def get(self, dni: int | Number) -> Client:
        pass

    def is_active(self, dni: Number) -> bool:
        pass

    def add(self, client: Client):
        pass

    def remove(self, client: Client):
        pass

    def update(self, client: Client):
        pass

    def all(
            self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None
    ) -> Generator[Client, None, None]:
        pass

    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        pass


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

    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)

    activity = Activity(String("TestAct", max_len=20), Currency("128.99"), True, String("TestDescr", max_len=30),
                        True)
    booking_system = BookingSystem(("1", "2"), (Duration(30, "30m"), Duration(60, "1h")),
                                   time(8, 0), time(23, 0), 30, activity, MockBookingRepo(), None, 8)
    window = BookUI(MockClientRepo(), booking_system)
    window.show()

    app.exec()
