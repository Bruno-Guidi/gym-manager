import sys
from datetime import date
from random import random
from typing import Generator

from PyQt5.QtWidgets import QApplication

from gym_manager.core.base import Transaction, String, Currency, Client
from gym_manager.core.persistence import TransactionRepo
from ui.accounting.operations import ExtractUI


# noinspection PyShadowingBuiltins
class Mock(TransactionRepo):

    def from_record(self, id, type, client: Client, when, amount, method, responsible, description):
        pass

    def create(self, type: String, when: date, amount: Currency, method: String, responsible: String,
               description: String, client: Client | None = None) -> Transaction:
        return Transaction(int(random()), type, client, when, amount, method, responsible, description)

    def all(self, page: int, page_len: int = 20, **filters) -> Generator[Transaction, None, None]:
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = ExtractUI((String("Cash", max_len=15), String("Debit", max_len=15)), Mock())
    window.show()

    app.exec()
