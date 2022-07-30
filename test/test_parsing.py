from gym_manager import peewee
from gym_manager.parsing import parse


def test_parse():
    peewee.create_database(":memory:")
    activity_repo = peewee.SqliteActivityRepo()
    parse(activity_repo, r"E:\downloads\chrome_bruno-leisure\backup_dia_26.sql")

