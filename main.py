import logging
import os
import sys
from datetime import time
from logging import config

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from gym_manager.booking import peewee as booking_peewee
from gym_manager.core.base import Currency, String, Activity
from ui.main import MainUI

log_config = {
    "version": 1,
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG"
    },
    "handlers": {
        "console": {
            "formatter": "std_out",
            "class": "logging.StreamHandler",
            "level": "DEBUG"
        },
        "file": {
            "formatter": "std_out",
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "filename": "logs/gym_manager.log"
        }
    },
    "formatters": {
        "std_out": {
            "format": "%(asctime)s : %(levelname)s : %(name)s : %(funcName)s : %(message)s",
            "datefmt": "%d-%m-%Y %I:%M:%S"
        }
    },
}

stylesheet = """
QCheckBox::indicator { 
    width:32px; height: 32px;
} 
QCheckBox::indicator::checked {
    image: url(ui/resources/checkbox_checked.png);
}
"""


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet)

    peewee.create_database("test.db")

    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    transaction_repo.client_repo = client_repo
    subscription_repo = peewee.SqliteSubscriptionRepo()
    balance_repo = peewee.SqliteBalanceRepo()

    booking_activity: Activity
    if activity_repo.exists("Padel"):
        booking_activity = activity_repo.get("Padel")
    else:
        booking_activity = Activity(String("Padel", max_len=10), Currency(100.00), String("d", max_len=10),
                                    charge_once=True, locked=True)
        activity_repo.add(booking_activity)

    window = MainUI(client_repo, activity_repo, subscription_repo)
    window.show()

    app.exec()


if __name__ == "__main__":
    os.makedirs(os.path.dirname("logs/gym_manager.log"), exist_ok=True)
    config.dictConfig(log_config)
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.setLevel(logging.WARNING)

    # noinspection PyBroadException
    try:
        main()
    except Exception as e:
        logging.exception(e)
