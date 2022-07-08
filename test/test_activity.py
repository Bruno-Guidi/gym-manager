import pytest

from gym_manager import peewee
from gym_manager.core.base import Activity, String, Currency
from gym_manager.core.persistence import PersistenceError


def test_deleteLockedActivity_raisesPersistenceError():
    peewee.create_database(":memory:")

    repo = peewee.SqliteActivityRepo()
    activity = Activity(String("dummy_name", max_len=20), Currency(0.0), description=String("dummy_descr", max_len=20),
                        charge_once=True, locked=True)
    repo.add(activity)
    with pytest.raises(PersistenceError) as p_err:
        repo.remove(activity)
    assert str(p_err.value) == "The [activity=dummy_name] cannot be removed because its locked."


