import sys
from datetime import date
from typing import Generator

from PyQt5.QtWidgets import QApplication

from gym_manager.core.base import Transaction, String, Currency, Balance, Client
from gym_manager.core.persistence import BalanceRepo, TransactionRepo, FilterValuePair
from ui.accounting.main import DailyBalanceUI

trans_charge, trans_extract = String("Charge", max_len=10), String("Extract", max_len=10)
trans_cash, trans_debit, trans_credit = String("Cash", max_len=10), String("Debit", max_len=10), String("Credit", max_len=10)


class MockTransactionRepo(TransactionRepo):

    def from_record(self, id, type, client: Client, when, amount, method, responsible, description):
        pass

    def create(self, type: String, when: date, amount: Currency, method: String, responsible: String,
               description: String, client: Client | None = None) -> Transaction:
        pass

    def all(self, page: int = 1, page_len: int | None = None, filters: list[FilterValuePair] | None = None,
            include_closed: bool = True, balance_date: date | None = None) -> Generator[Transaction, None, None]:
        # noinspection PyTypeChecker
        to_yield = [
            Transaction(1, trans_charge, date(2022, 6, 6), Currency("100.33"), trans_debit, None, None),
            Transaction(2, trans_extract, date(2022, 6, 6), Currency("100.56"), trans_credit, None, None),
            Transaction(3, trans_extract, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
            Transaction(4, trans_charge, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
            Transaction(5, trans_charge, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
            Transaction(6, trans_charge, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
            Transaction(7, trans_extract, date(2022, 6, 6), Currency("100.09"), trans_debit, None, None)
        ]
        for t in to_yield:
            yield t

    def count(self, filters: list[FilterValuePair] | None = None) -> int:
        pass

    def bind_to_balance(self, transaction: Transaction, balance_date: date):
        pass


class MockBalanceRepo(BalanceRepo):

    def balance_done(self, when: date) -> bool:
        return False

    def add(self, when: date, responsible: String, balance: Balance):
        pass

    def all(self, from_date: date, to_date: date) -> Generator[tuple[date, String, Balance], None, None]:
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = DailyBalanceUI(MockTransactionRepo(), MockBalanceRepo(),
                            transaction_types=(trans_charge, trans_extract),
                            transaction_methods=(trans_cash, trans_debit, trans_credit))
    window.show()

    app.exec()
