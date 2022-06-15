import sys

from PyQt5.QtWidgets import QApplication

from gym_manager import peewee
from ui.main import MainUI

if __name__ == "__main__":
    app = QApplication(sys.argv)

    client_repo = peewee.SqliteClientRepo()

    window = MainUI(client_repo)
    window.show()

    app.exec()
