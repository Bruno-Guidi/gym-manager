import sys

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from gym_manager.core.accounting import AccountingSystem
from gym_manager.core.activity_manager import ActivityManager
from ui.main import MainUI

if __name__ == "__main__":
    app = QApplication(sys.argv)

    activity_repo = peewee.SqliteActivityRepo()
    transaction_repo = peewee.SqliteTransactionRepo()
    client_repo = peewee.SqliteClientRepo(activity_repo, transaction_repo)
    inscription_repo = peewee.SqliteInscriptionRepo()

    activity_manager = ActivityManager(activity_repo, inscription_repo)
    accounting_system = AccountingSystem(transaction_repo, inscription_repo,
                                         transaction_types=["charge", "extract"])

    window = MainUI(client_repo, activity_manager, accounting_system)
    window.show()

    app.exec()
