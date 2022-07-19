import logging
import os
import sys
from datetime import time
from logging import config

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from gym_manager.booking import peewee as booking_peewee
from gym_manager.booking.core import BookingSystem, Duration
from gym_manager.core.base import Currency, String, Activity
from gym_manager.core.security import log_responsible, SimpleSecurityHandler, Responsible
from ui.main import MainUI

stylesheet = """
QCheckBox::indicator { 
    width:32px; height: 32px;
} 
QCheckBox::indicator::checked {
    image: url(ui/resources/checkbox_checked.png);
}
"""


def main():
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

    # Security initialization.
    security_handler = SimpleSecurityHandler(
        peewee.SqliteSecurityRepo(),
        action_tags={"subscribe", "cancel", "register_subscription_charge", "close_balance", "remove_client",
                     "update_client", "remove_activity", "update_activity", "cancel_booking", "charge_booking",
                     "create_booking"},
        needs_responsible={"subscribe", "cancel", "register_subscription_charge", "close_balance", "remove_client",
                           "update_client", "remove_activity", "update_activity", "cancel_booking", "charge_booking",
                           "create_booking"}
    )
    security_handler.add_responsible(Responsible(String("Admin", max_len=10), String("python", max_len=10)))
    log_responsible.config(security_handler)

    # Main window launch.
    window = MainUI(client_repo, activity_repo, subscription_repo, transaction_repo, balance_repo, booking_system,
                    security_handler)
    window.show()
    app.exec()


if __name__ == "__main__":
    os.makedirs(os.path.dirname("logs/gym_manager.log"), exist_ok=True)
    config.fileConfig("logging.conf")

    peewee.create_database("test.db")
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.setLevel(logging.WARNING)

    # noinspection PyBroadException
    try:
        main()
    except Exception as e:
        logging.exception(e)
