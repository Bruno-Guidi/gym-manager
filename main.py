import sys
from datetime import time

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from gym_manager.booking import peewee as booking_peewee
from gym_manager.booking.core import BookingSystem, Duration
from gym_manager.core.system import ActivityManager, AccountingSystem
from ui.main import MainUI

if __name__ == "__main__":
    app = QApplication(sys.argv)

    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    transaction_repo.client_repo = client_repo
    inscription_repo = peewee.SqliteInscriptionRepo()

    activity_manager = ActivityManager(activity_repo, inscription_repo)
    accounting_system = AccountingSystem(transaction_repo, inscription_repo,
                                         transaction_types=["charge", "extract"])

    booking_repo = booking_peewee.SqliteBookingRepo(client_repo)
    booking_system = BookingSystem(courts_names=("1", "2", "3"),
                                   durations=(Duration(30, "30m"), Duration(60, "1h"), Duration(90, "1h30m")),
                                   start=time(8, 0), end=time(23, 0), minute_step=30, repo=booking_repo)

    window = MainUI(client_repo, activity_manager, accounting_system, booking_system)
    window.show()

    app.exec()
