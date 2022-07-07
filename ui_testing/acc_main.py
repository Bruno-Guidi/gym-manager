import sys
from datetime import date
from typing import Generator

from PyQt5.QtWidgets import QApplication

from gym_manager.core import system
from gym_manager.core.base import Transaction, String, Currency, Balance, Client, Activity, Subscription, Number
from gym_manager.core.persistence import BalanceRepo, TransactionRepo, FilterValuePair, SubscriptionRepo
from gym_manager.core.system import AccountingSystem
from ui.accounting.main import AccountingMainUI
from ui.accounting.operations import ChargeUI

trans_charge, trans_extract = String("Cobro", max_len=30), String("Extracción", max_len=30)
trans_cash, trans_debit, trans_credit = (String("Efectivo", max_len=30), String("Débito", max_len=30),
                                         String("Crédito", max_len=30))


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
        return 7

    def bind_to_balance(self, transaction: Transaction, balance_date: date):
        pass


class MockSubscriptionRepo(SubscriptionRepo):

    def add(self, subscription: Subscription):
        pass

    def remove(self, subscription: Subscription):
        pass

    def register_charge(self, client: Client, activity: Activity, transaction: Transaction):
        pass


class MockBalanceRepo(BalanceRepo):

    def balance_done(self, when: date) -> bool:
        return False

    def add(self, when: date, responsible: String, balance: Balance):
        pass

    def all(self, from_date: date, to_date: date) -> Generator[tuple[date, String, Balance], None, None]:
        transactions = [
            Transaction(1, trans_charge, date(2022, 6, 6), Currency("100.33"), trans_debit, None, None),
            Transaction(2, trans_extract, date(2022, 6, 6), Currency("100.56"), trans_credit, None, None),
            Transaction(3, trans_extract, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
            Transaction(4, trans_charge, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
            Transaction(5, trans_charge, date(2022, 6, 6), Currency("100"), trans_cash, None, None),
            Transaction(6, trans_charge, date(2022, 6, 6), Currency("100"), trans_debit, None, None),
            Transaction(7, trans_extract, date(2022, 6, 6), Currency("100.09"), trans_debit, None, None)
        ]
        for i in range(10):
            b = system.generate_balance(transactions,
                                        transaction_types=(trans_charge, trans_extract),
                                        transaction_methods=(trans_cash, trans_debit, trans_credit))
            yield date(2022, 6, 6 + i), "123456789123456789123456789123", b


if __name__ == "__main__":
    app = QApplication(sys.argv)

    balance_repo = MockBalanceRepo()
    acc_system = AccountingSystem(MockTransactionRepo(), MockSubscriptionRepo(), balance_repo,
                                  transaction_types=(trans_charge.as_primitive(), trans_extract.as_primitive()),
                                  methods=(trans_cash.as_primitive(), trans_debit.as_primitive(),
                                           trans_credit.as_primitive()))
    client = Client(Number(41545437), String("TestClient", max_len=20), date(2022, 9, 9), String("TestTel", max_len=20),
                    String("TestDir", max_len=20), is_active=True)
    activity = Activity(String("TestAct", max_len=20), Currency("500.67"), charge_once=False,
                        description=String("TestDescr", max_len=20), locked=False)
    description = String("TestCharge", max_len=20)
    window = AccountingMainUI(acc_system, client=None)
    window.show()

    app.exec()
