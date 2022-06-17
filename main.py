import sys

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from ui.main import MainUI

if __name__ == "__main__":
    app = QApplication(sys.argv)

    client_repo = peewee.SqliteClientRepo()
    activity_repo = peewee.SqliteActivityRepo()
    reg_repo = peewee.SqliteRegistrationRepo()

    window = MainUI(client_repo, activity_repo, reg_repo)
    window.show()

    app.exec()
