import logging
import os
import sys
from datetime import time
from logging import config

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from gym_manager.core import constants as consts
from gym_manager.booking import peewee as booking_peewee
from gym_manager.booking.core import BookingSystem, Duration, Court
from gym_manager.core.base import Currency, String
from gym_manager.core.system import ActivityManager, AccountingSystem
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
    inscription_repo = peewee.SqliteSubscriptionRepo()
    balance_repo = peewee.SqliteBalanceRepo()

    activity_manager = ActivityManager(activity_repo, inscription_repo)
    accounting_system = AccountingSystem(transaction_repo, inscription_repo, balance_repo,
                                         transaction_types=("Cobro", "Extracción"),
                                         methods=("Efectivo", "Débito", "Crédito"))

    activity = activity_manager.create(String("Padel", max_len=consts.ACTIVITY_NAME_CHARS),
                                       Currency("100", max_currency=consts.MAX_CURRENCY),
                                       charge_once=True,
                                       description=String("", optional=True, max_len=consts.ACTIVITY_DESCR_CHARS),
                                       locked=True)
    booking_repo = booking_peewee.SqliteBookingRepo((Court("1", 1), Court("2", 2), Court("3", 3)), client_repo,
                                                    transaction_repo)
    booking_system = BookingSystem(courts_names=("1", "2", "3"),
                                   durations=(Duration(30, "30m"), Duration(60, "1h"), Duration(90, "1h30m")),
                                   start=time(8, 0), end=time(23, 0), minute_step=30,
                                   activity=activity_repo.get("Padel"), repo=booking_repo,
                                   accounting_system=accounting_system,
                                   weeks_in_advance=8)

    window = MainUI(client_repo, activity_manager, accounting_system, booking_system)
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
