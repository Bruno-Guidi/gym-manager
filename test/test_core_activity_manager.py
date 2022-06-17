from datetime import date
from decimal import Decimal
from typing import Generator

from gym_manager.core.activity_manager import ActivityManager
from gym_manager.core.base import Activity, String, Currency, Inscription, Client, Number, Date
from gym_manager.core.persistence import ActivityRepo, InscriptionRepo


class MockActivityRepo(ActivityRepo):

    def create(self, name: String, price: Currency, pay_once: bool, description: String) -> int:
        pass

    def remove(self, activity: Activity, cascade_removing: bool = False):
        pass

    def update(self, activity: Activity):
        pass

    def all(self) -> Generator[Activity, None, None]:
        pass

    def registered_clients(self, activity: Activity) -> int:
        pass


class MockInscriptionRepo(InscriptionRepo):

    def add(self, inscription: Inscription):
        pass

    def update_or_create(self, registration: Inscription):
        pass

    def expired(self, when: date, **kwargs) -> Generator[Inscription, None, None]:
        pass


def test_sign_on():
    act_manager = ActivityManager(MockActivityRepo(), MockInscriptionRepo())

    client = Client(Number("1"), String("TestClient", optional=False, max_len=30), Date(date(2022, 5, 5)),
                    String("12345", optional=True, max_len=30), String("abcde", optional=True, max_len=30))
    activity = Activity(1,
                        String("TestActivity", optional=False, max_len=30),
                        Currency("500", positive=True, max_currency=Decimal("1000")),
                        pay_once=False,
                        description=String("TestDescription", optional=True, max_len=30))

    act_manager.sign_on(client, activity)
