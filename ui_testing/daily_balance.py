import sys
from datetime import date
from typing import Iterable

from PyQt5.QtWidgets import QApplication

from gym_manager.core.base import Transaction, String, Currency
from gym_manager.core.persistence import BalanceRepo
from ui.accounting.main import DailyBalanceUI

trans_charge, trans_extract = String("Charge", max_len=10), String("Extract", max_len=10)
trans_cash, trans_debit, trans_credit = String("Cash", max_len=10), String("Debit", max_len=10), String("Credit", max_len=10)


def transactions_fn(page: int, page_len: int | None = None, **filter_values) -> Iterable[Transaction]:
    # noinspection PyTypeChecker
    to_yield = [
        Transaction(1, trans_charge, None, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
        Transaction(2, trans_extract, None, date(2022, 6, 6), Currency("100"), trans_credit, None, None),
        Transaction(3, trans_extract, None, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
        Transaction(4, trans_charge, None, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
        Transaction(5, trans_charge, None, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
        Transaction(6, trans_charge, None, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
        Transaction(7, trans_extract, None, date(2022, 6, 6), Currency("100"), trans_debit, None, None)
    ]
    for t in to_yield:
        yield t


class Mock(BalanceRepo):

    def balance_done(self, when: date) -> bool:
        return False

    def add_all(self, when: date, transactions: list[Transaction]):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = DailyBalanceUI(transactions_fn,
                            transaction_types=(trans_charge, trans_extract),
                            transaction_methods=(trans_cash, trans_debit, trans_credit),
                            balance_repo=Mock())
    window.show()

    app.exec()
