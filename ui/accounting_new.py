from __future__ import annotations

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QLabel, QGridLayout, QPushButton, QLineEdit)

from gym_manager.core import api
from gym_manager.core.base import DateGreater, DateLesser, Currency, Transaction
from gym_manager.core.persistence import TransactionRepo, BalanceRepo
from ui.widget_config import config_table, config_lbl, config_btn, config_line, fill_cell
from ui.widgets import Separator


class MainController:
    def __init__(self, acc_main_ui: AccountingMainUI, transaction_repo: TransactionRepo, balance_repo: BalanceRepo):
        self.acc_main_ui = acc_main_ui
        self.transaction_repo = transaction_repo
        self.balance_repo = balance_repo

        self._date_greater_filter = DateGreater("from", display_name="Desde", attr="when",
                                                translate_fun=lambda trans, when: trans.when >= when)
        self._date_lesser_filter = DateLesser("to", display_name="Hasta", attr="when",
                                              translate_fun=lambda trans, when: trans.when <= when)
        today = str(date.today())
        _filters = [(self._date_greater_filter, today), (self._date_lesser_filter, today)]

        self._today_transactions: list[Transaction] = [t for t in transaction_repo.all(filters=_filters,
                                                                                       include_closed=True)]

        # Calculates charges of the day.
        self.balance = api.generate_balance(self._today_transactions)
        self.acc_main_ui.today_charges_line.setText(str(self.balance.get("Cobros", Currency(0))))

        # Shows transactions of the day.
        for i, transaction in self._today_transactions:
            fill_cell(self.acc_main_ui.transaction_table, i, 0, transaction.responsible, data_type=str)
            fill_cell(self.acc_main_ui.transaction_table, i, 1, transaction.amount, data_type=int)
            fill_cell(self.acc_main_ui.transaction_table, i, 2, transaction.description, data_type=str)


class AccountingMainUI(QMainWindow):
    def __init__(self, transaction_repo: TransactionRepo, balance_repo: BalanceRepo):
        super().__init__()
        self._setup_ui()

        self.controller = MainController(self, transaction_repo, balance_repo)

    def _setup_ui(self):
        self.setWindowTitle("Contabilidad")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        # Left layout.
        self.left_layout = QVBoxLayout()
        self.layout.addLayout(self.left_layout)

        # Header layout.
        self.header_layout = QGridLayout()
        self.left_layout.addLayout(self.header_layout)
        self.header_layout.setAlignment(Qt.AlignLeft)

        self.today_charges_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.today_charges_lbl, 0, 0)
        config_lbl(self.today_charges_lbl, "Cobros del día")

        self.today_charges_line = QLineEdit(self.widget)
        self.header_layout.addWidget(self.today_charges_line, 1, 0)
        config_line(self.today_charges_line, place_holder="00000,00", enabled=False)

        self.close_balance_btn = QPushButton(self.widget)
        self.header_layout.addWidget(self.close_balance_btn, 0, 1, 2, 1)
        config_btn(self.close_balance_btn, "Cerrar caja", font_size=16)

        self.history_btn = QPushButton(self.widget)
        self.header_layout.addWidget(self.history_btn, 0, 2, 2, 1)
        config_btn(self.history_btn, "Historial", font_size=16)

        self.left_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Transactions of the day.
        self.transactions_lbl = QLabel(self.widget)
        self.left_layout.addWidget(self.transactions_lbl)
        config_lbl(self.transactions_lbl, "Transacciones", font_size=16)

        self.transaction_table = QTableWidget(self.widget)
        self.left_layout.addWidget(self.transaction_table)
        config_table(self.transaction_table, allow_resizing=False,
                     columns={"Responsable": (8, str), "Monto": (8, int), "Descripción": (12, str)})

        self.left_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Balance detail.
        self.detail_layout = QGridLayout()
        self.left_layout.addLayout(self.detail_layout)
        self.detail_layout.setAlignment(Qt.AlignLeft)

        # Balance date label.
        self.detail_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.detail_lbl, 0, 0, 1, 5)
        config_lbl(self.detail_lbl, "Detalle", font_size=18)

        # Detailed balance layout.
        self.method_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.method_lbl, 1, 0)
        config_lbl(self.method_lbl, "Método")

        self.charges_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.charges_lbl, 2, 0)
        config_lbl(self.charges_lbl, "Cobros")

        self.extractions_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.extractions_lbl, 3, 0)
        config_lbl(self.extractions_lbl, "Extracciones")

        self.cash_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.cash_lbl, 1, 1)
        config_lbl(self.cash_lbl, "Efectivo")

        self.debit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.debit_lbl, 1, 2)
        config_lbl(self.debit_lbl, "Débito")

        self.credit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.credit_lbl, 1, 3)
        config_lbl(self.credit_lbl, "Crédito")

        self.total_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.total_lbl, 1, 4)
        config_lbl(self.total_lbl, "TOTAL")

        # # Filters.
        # self.filters_layout = QHBoxLayout()
        # self.right_layout.addLayout(self.filters_layout)
        #
        # self.last_n_checkbox = QCheckBox(self.widget)
        # self.filters_layout.addWidget(self.last_n_checkbox)
        # config_checkbox(self.last_n_checkbox, "Últimos", checked=True, layout_dir=Qt.LayoutDirection.LeftToRight)
        #
        # self.date_edit = QDateEdit(self.widget)
        # self.filters_layout.addWidget(self.date_edit)
        # config_date_edit(self.date_edit, date.today(), calendar=True)
        #
        # self.date_checkbox = QCheckBox(self.widget)
        # self.filters_layout.addWidget(self.date_checkbox)
        # config_checkbox(self.date_checkbox, "Fecha", checked=False, layout_dir=Qt.LayoutDirection.LeftToRight)
        #
        # self.last_n_combobox = QComboBox(self.widget)
        # self.filters_layout.addWidget(self.last_n_combobox)
        # config_combobox(self.last_n_combobox, extra_width=20, fixed_width=self.date_edit.width())
        #
        # # Horizontal spacer.
        # self.right_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        #
        # # Balance history.
        # self.balance_table = QTableWidget(self.widget)
        # self.right_layout.addWidget(self.balance_table)
        # config_table(
        #     target=self.balance_table, allow_resizing=True, min_rows_to_show=1,
        #     columns={"Fecha": (10, int), "Responsable": (12, str), "Cobros": (12, int),
        #              "Extracciones": (12, int)}
        # )
