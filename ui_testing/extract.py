import sys
from datetime import date
from random import random
from typing import Generator

from PyQt5.QtWidgets import QApplication

from gym_manager.core.base import Transaction, String, Currency, Client
from gym_manager.core.persistence import TransactionRepo
from ui.accounting.operations import ExtractUI


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = ExtractUI((String("Cash", max_len=15), String("Debit", max_len=15)), Mock())
    window.show()

    app.exec()
