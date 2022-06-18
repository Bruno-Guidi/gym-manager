import sys

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from gym_manager.core.accounting import AccountingSystem
from gym_manager.core.activity_manager import ActivityManager
from ui.main import MainUI

if __name__ == "__main__":
    app = QApplication(sys.argv)

    client_repo = peewee.SqliteClientRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    activity_repo = peewee.SqliteActivityRepo()
    inscription_repo = peewee.SqliteInscriptionRepo()

    activity_manager = ActivityManager(activity_repo, inscription_repo)
    accounting_system = AccountingSystem(transaction_repo, inscription_repo,
                                         transaction_types=["charge", "extract"])

    window = MainUI(client_repo, activity_manager, accounting_system)
    window.show()

    app.exec()
