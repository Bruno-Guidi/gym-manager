from datetime import date

from gym_manager.core.base import Date


def test_Date():
    today = date.today()
    print(str(Date(today)))