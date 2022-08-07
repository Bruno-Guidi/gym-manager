import functools
import json
import logging
import sys
import traceback
from datetime import time
from logging import config
from os import path

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from gym_manager.booking import peewee as booking_peewee
from gym_manager.booking.core import BookingSystem, Duration
from gym_manager.contact.peewee import SqliteContactRepo
from gym_manager.core.base import Currency, String, Activity
from gym_manager.core.persistence import create_backup
from gym_manager.core.security import log_responsible, SimpleSecurityHandler, Responsible
from gym_manager.stock.peewee import SqliteItemRepo
from ui.main import MainUI

stylesheet = """
QCheckBox::indicator { 
    width:32px; height: 32px;
} 
QCheckBox::indicator::unchecked {
    image: url(ui/resources/checkbox_unchecked.png);
}
QCheckBox::indicator::checked {
    image: url(ui/resources/checkbox_checked.png);
}
"""


def main():
    with open(path.join(path.dirname(path.abspath(__file__)), 'config.json')) as config_file:
        config_dict = json.load(config_file)

    # PyQt App.
    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet)

    # Repository initialization
    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo(methods=("Efectivo", "Débito", "Crédito"))
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    subscription_repo = peewee.SqliteSubscriptionRepo()
    balance_repo = peewee.SqliteBalanceRepo(transaction_repo)

    # Booking initialization.
    booking_activity: Activity
    booking_activity_name = String("Padel", max_len=10)
    if activity_repo.exists(booking_activity_name):
        booking_activity = activity_repo.get(booking_activity_name)
    else:
        booking_activity = Activity(booking_activity_name, Currency(100.00), String("d", max_len=10),
                                    charge_once=True, locked=True)
        activity_repo.add(booking_activity)
    booking_repo = booking_peewee.SqliteBookingRepo(client_repo, transaction_repo, cache_len=128)
    booking_system = BookingSystem(
        booking_activity, booking_repo, (Duration(60, "1h"), Duration(90, "1h30m"), Duration(120, "2h")),
        courts_names=("1", "2", "3"), start=time(8, 0), end=time(23, 0), minute_step=30
    )

    # Contact initialization.
    contact_repo = SqliteContactRepo()

    # Stock initialization.
    item_repo = SqliteItemRepo()

    # Security initialization.
    security_handler = SimpleSecurityHandler(
        peewee.SqliteSecurityRepo(),
        action_tags={"subscribe", "cancel", "register_subscription_charge", "close_balance", "cancel_booking",
                     "charge_booking", "create_booking", "update_item_amount", "register_item_charge", "extract",
                     "confirm_subscription_charge"},
        needs_responsible={"cancel", "register_subscription_charge", "close_balance", "cancel_booking",
                           "charge_booking", "create_booking", "update_item_amount", "register_item_charge", "extract",
                           "confirm_subscription_charge"}
    )
    security_handler.add_responsible(Responsible(String("Admin"), String("python")))
    log_responsible.config(security_handler)

    backup_fn = functools.partial(create_backup, "gym_manager.db", config_dict["backups_dir"])

    # Main window launch.
    window = MainUI(client_repo, activity_repo, subscription_repo, transaction_repo, balance_repo, booking_system,
                    contact_repo, item_repo, security_handler, enable_tools=config_dict["enable_utility_functions"],
                    backup_fn=backup_fn)
    window.show()
    app.exec()


def logging_excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.error(tb)
    QApplication.quit()


if __name__ == "__main__":
    sys.excepthook = logging_excepthook

    logging_config_path = path.join(path.dirname(path.abspath(__file__)), 'logging.conf')
    config.fileConfig(logging_config_path)

    peewee.create_database(":memory:")
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.setLevel(logging.WARNING)

    # noinspection PyBroadException
    try:
        main()
    except Exception as e:
        print("exception caught")
        logging.exception(e)
