import functools
import json
import logging
import sys
import traceback
from datetime import time, datetime
from logging import config
from os import path

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from gym_manager.booking import peewee as booking_peewee
from gym_manager.booking.core import BookingSystem, BookingRepo
from gym_manager.contact.peewee import SqliteContactRepo
from gym_manager.core.base import Currency, String
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


def _save_bookings(booking_repo: BookingRepo):
    with open("booking_backup.json", 'w') as file:
        all_fixed = [
            {"court": fixed_b.court, "client": fixed_b.client_name.as_primitive(),
             "start": fixed_b.start.strftime("%H:%M"), "end": fixed_b.end.strftime("%H:%M"),
             "day_of_week": fixed_b.day_of_week, "first_when": fixed_b.first_when.strftime("%d/%m/%Y")}
            for fixed_b in booking_repo.all_fixed()
        ]
        all_temp = [
            {"court": temp_b.court, "client": temp_b.client_name.as_primitive(),
             "start": temp_b.start.strftime("%H:%M"), "end": temp_b.end.strftime("%H:%M"),
             "when": temp_b.when.strftime("%d/%m/%Y")}
            for temp_b in booking_repo.all_temporal()
        ]
        json.dump({"fixed": all_fixed, "temp": all_temp}, file)


def _load_bookings(booking_system: BookingSystem):
    with open("booking_backup.json", "r") as file:
        json_dict = json.load(file)
        duration_dict = {}
        for fixed_b in json_dict["fixed"]:
            start = datetime.strptime(fixed_b["start"], "%H:%M").time()
            end = datetime.strptime(fixed_b["end"], "%H:%M").time()
            when = datetime.strptime(fixed_b["first_when"], "%d/%m/%Y").date()
            booking_system.book_with_end(fixed_b["court"], String(fixed_b["client"]), True, when, start, end,
                                         duration_dict)

        for temp_b in json_dict["temp"]:
            start = datetime.strptime(temp_b["start"], "%H:%M").time()
            end = datetime.strptime(temp_b["end"], "%H:%M").time()
            when = datetime.strptime(temp_b["when"], "%d/%m/%Y").date()
            booking_system.book_with_end(temp_b["court"], String(temp_b["client"]), False, when, start, end,
                                         duration_dict)


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
    if activity_repo.exists(1):
        booking_single = activity_repo.get(1)
    else:
        booking_single = activity_repo.create(String("Padel Single"), Currency(100.00), String("Precio por media hora"),
                                              charge_once=True, locked=True)
    if activity_repo.exists(2):
        booking_double = activity_repo.get(2)
    else:
        booking_double = activity_repo.create(String("Padel Dobles"), Currency(200.00), String("Precio por media hora"),
                                              charge_once=True, locked=True)
    booking_repo = booking_peewee.SqliteBookingRepo(transaction_repo, cache_len=128)
    booking_system = BookingSystem(
        booking_repo, courts=(("1", booking_double.price), ("2", booking_double.price), ("3", booking_single.price)),
        start=time(8, 0), end=time(23, 0), minute_step=30
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
                    allow_passed_time_bookings=config_dict["allow_passed_time_bookings"], backup_fn=backup_fn)
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

    peewee.create_database("gym_manager.db")
    peewee_logger = logging.getLogger("peewee")
    peewee_logger.setLevel(logging.WARNING)

    # noinspection PyBroadException
    try:
        main()
    except Exception as e:
        print("exception caught")
        logging.exception(e)
