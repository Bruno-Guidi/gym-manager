from __future__ import annotations

from datetime import date
from typing import Iterable, Protocol

from PyQt5 import QtCore
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, \
    QSizePolicy, QLabel, QTableWidget, QDateEdit, QTableWidgetItem, QGridLayout, QMenuBar, QAction, QMenu

from gym_manager.core import system
from gym_manager.core.base import ONE_MONTH_TD, Client, DateGreater, ClientLike, DateLesser, TextEqual, TextLike, \
    NumberEqual, Transaction, String
from gym_manager.core.persistence import BalanceRepo
from gym_manager.core.system import AccountingSystem
from ui.accounting.operations import ExtractUI
from ui.widget_config import config_layout, config_btn, config_lbl, config_table, \
    config_date_edit
from ui.widgets import SearchBox, Dialog


class MainController:

    def __init__(
            self, main_ui: AccountingMainUI, accounting_system: AccountingSystem, client: Client | None = None
    ) -> None:
        self.main_ui = main_ui

        self.accounting_system = accounting_system
        self.current_page, self.page_len = 1, 20

        # If a client is given, set the filter with it.
        if client is not None:
            self.main_ui.search_box.set_filter("client_dni", str(client.dni))
        self.load_transactions()

        # Sets callbacks
        # noinspection PyUnresolvedReferences
        self.main_ui.search_btn.clicked.connect(self.load_transactions)
        # noinspection PyUnresolvedReferences
        self.main_ui.generate_balance_action.triggered.connect(self.daily_balance)
        # noinspection PyUnresolvedReferences
        self.main_ui.register_extraction_action.triggered.connect(self.extraction)

    def load_transactions(self):
        self.main_ui.transaction_table.setRowCount(0)
        self.main_ui.transaction_table.setRowCount(self.page_len)

        from_date_filter = DateGreater("from", display_name="Desde",
                                       translate_fun=lambda trans, when: trans.when >= when)
        to_date_filter = DateLesser("to", display_name="Hasta",
                                    translate_fun=lambda trans, when: trans.when <= when)
        transactions = self.accounting_system.transactions(
            self.current_page, self.page_len,
            from_date=(from_date_filter, self.main_ui.from_date_edit.date().toPyDate()),
            to_date=(to_date_filter, self.main_ui.to_date_edit.date().toPyDate()),
            **self.main_ui.search_box.filters()
        )
        for row, transaction in enumerate(transactions):
            self.main_ui.transaction_table.setItem(row, 0, QTableWidgetItem(str(transaction.id)))
            self.main_ui.transaction_table.setItem(row, 1, QTableWidgetItem(str(transaction.type)))
            self.main_ui.transaction_table.setItem(row, 2, QTableWidgetItem(str(transaction.client.name)))
            self.main_ui.transaction_table.setItem(row, 3, QTableWidgetItem(str(transaction.when)))
            self.main_ui.transaction_table.setItem(row, 4, QTableWidgetItem(str(transaction.amount)))
            self.main_ui.transaction_table.setItem(row, 5, QTableWidgetItem(str(transaction.method)))
            self.main_ui.transaction_table.setItem(row, 6, QTableWidgetItem(str(transaction.responsible)))
            self.main_ui.transaction_table.setItem(row, 7, QTableWidgetItem(str(transaction.description)))

    def daily_balance(self):
        # noinspection PyAttributeOutsideInit
        self.daily_balance_ui = DailyBalanceUI(self.accounting_system.transactions,
                                               self.accounting_system.transactions_types(),
                                               self.accounting_system.methods,
                                               self.accounting_system.balance_repo)
        self.daily_balance_ui.setWindowModality(Qt.ApplicationModal)
        self.daily_balance_ui.show()

    def extraction(self):
        self.extract_ui = ExtractUI(self.accounting_system.methods, self.accounting_system.transaction_repo)
        self.extract_ui.exec_()


class AccountingMainUI(QMainWindow):

    def __init__(
            self, accounting_system: AccountingSystem, client: Client | None = None
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, accounting_system, client)

    def _setup_ui(self):
        self.resize(800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, 800, 600))

        self.main_layout = QVBoxLayout(self.widget)
        config_layout(self.main_layout, left_margin=10, top_margin=10, right_margin=10, bottom_margin=10)

        # Menu bar.
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.menu_bar.setGeometry(QtCore.QRect(0, 0, 800, 20))

        # Balance menu bar.
        self.daily_balance_menu = QMenu("Caja diaria", self)
        self.menu_bar.addMenu(self.daily_balance_menu)

        self.generate_balance_action = QAction("Cerrar caja", self)
        self.daily_balance_menu.addAction(self.generate_balance_action)

        # Extractions menu bar.
        self.extraction_menu = QMenu("Extracción", self)
        self.menu_bar.addMenu(self.extraction_menu)

        self.register_extraction_action = QAction("Registrar", self)
        self.extraction_menu.addAction(self.register_extraction_action)

        # Utilities.
        self.utils_layout = QHBoxLayout()
        self.main_layout.addLayout(self.utils_layout)
        config_layout(self.utils_layout, spacing=0, left_margin=40, top_margin=15, right_margin=40)

        self.search_box = SearchBox(
            filters=[ClientLike("client_name", display_name="Nombre cliente",
                                translate_fun=lambda trans, value: trans.client.cli_name.contains(value)),
                     NumberEqual("client_dni", display_name="DNI cliente", attr="dni",
                                 translate_fun=lambda trans, value: trans.client.dni == value),
                     TextEqual("type", display_name="Tipo", attr="type",
                               translate_fun=lambda trans, value: trans.type == value),
                     TextEqual("method", display_name="Método", attr="method",
                               translate_fun=lambda trans, value: trans.method == value),
                     TextLike("responsible", display_name="Responsable", attr="responsible",
                              translate_fun=lambda trans, value: trans.responsible.contains(value))],
            parent=self.widget
        )
        self.utils_layout.addWidget(self.search_box)

        self.utils_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.from_layout = QVBoxLayout()
        self.utils_layout.addLayout(self.from_layout)

        self.from_lbl = QLabel()
        self.from_layout.addWidget(self.from_lbl)
        config_lbl(self.from_lbl, "Desde", font_size=16, alignment=Qt.AlignCenter)

        self.from_date_edit = QDateEdit()
        self.from_layout.addWidget(self.from_date_edit)
        config_date_edit(self.from_date_edit, date.today() - ONE_MONTH_TD, calendar=True,
                         layout_direction=Qt.LayoutDirection.RightToLeft)

        self.utils_layout.addItem(QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.to_layout = QVBoxLayout()
        self.utils_layout.addLayout(self.to_layout)

        self.to_lbl = QLabel()
        self.to_layout.addWidget(self.to_lbl)
        config_lbl(self.to_lbl, "Hasta", font_size=16, alignment=Qt.AlignCenter)

        self.to_date_edit = QDateEdit()
        self.to_layout.addWidget(self.to_date_edit)
        config_date_edit(self.to_date_edit, date.today(), calendar=True,
                         layout_direction=Qt.LayoutDirection.RightToLeft)

        self.utils_layout.addItem(QSpacerItem(30, 20, QSizePolicy.Minimum, QSizePolicy.Minimum))

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "Busq", font_size=16)

        # Transactions.
        self.transaction_table = QTableWidget(self.widget)
        self.main_layout.addWidget(self.transaction_table)
        config_table(
            target=self.transaction_table, allow_resizing=True,
            columns={"#": 100, "Tipo": 70, "Cliente": 175, "Fecha": 100, "Monto": 100, "Método": 120,
                     "Responsable": 175, "Descripción": 200}
        )

        # Index.
        self.index_layout = QHBoxLayout()
        self.main_layout.addLayout(self.index_layout)
        config_layout(self.index_layout, left_margin=100, right_margin=100)

        self.prev_btn = QPushButton(self.widget)
        self.index_layout.addWidget(self.prev_btn)
        config_btn(self.prev_btn, "<", font_size=18, width=30)

        self.index_lbl = QLabel(self.widget)
        self.index_layout.addWidget(self.index_lbl)
        config_lbl(self.index_lbl, "#", font_size=18)

        self.next_btn = QPushButton(self.widget)
        self.index_layout.addWidget(self.next_btn)
        config_btn(self.next_btn, ">", font_size=18, width=30)


class _TransactionFunction(Protocol):
    def __call__(self, page: int, page_len: int | None = None, **filter_values) -> Iterable[Transaction]:
        pass


class DailyBalanceController:
    def __init__(
            self,
            daily_balance_ui: DailyBalanceUI,
            transactions_fn: _TransactionFunction,
            transaction_types: Iterable[String],
            transaction_methods: Iterable[String],
            balance_repo: BalanceRepo
    ):
        self.daily_balance_ui = daily_balance_ui
        self.transactions_fn = transactions_fn
        self.balance_repo = balance_repo

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.daily_balance_ui.confirm_btn.clicked.connect(self.close_balance)

        # Generates the balance.
        types_dict = {trans_type: i + 1 for i, trans_type in enumerate(transaction_types)}
        methods_dict = {trans_method: i + 2 for i, trans_method in enumerate(transaction_methods)}
        methods_dict["Total"] = len(methods_dict) + 2

        balance = system.generate_balance(self.transactions_fn(page=1), transaction_types, transaction_methods)

        # Shows balance information in the ui.
        for trans_type, type_balance in balance.items():
            for trans_method, method_balance in type_balance.items():
                lbl = QLabel(str(method_balance))
                self.daily_balance_ui.balance_layout.addWidget(lbl, methods_dict[trans_method], types_dict[trans_type])

    def close_balance(self):
        today = date.today()
        overwrite = True
        if self.balance_repo.balance_done(today):
            overwrite = Dialog.confirm(
                f"Ya hay una caja diaria calculada para la fecha {today}. ¿Desea sobreescribirla?", "Si", "No"
            )
        if overwrite:
            self.balance_repo.add_all(today, self.transactions_fn(page=1))
            Dialog.info("Éxito", "Caja diaria calculada correctamente.")
            self.daily_balance_ui.confirm_btn.window().close()


class DailyBalanceUI(QMainWindow):
    def __init__(
            self,
            transactions_fn: _TransactionFunction,
            transaction_types: Iterable[String],
            transaction_methods: Iterable[String],
            balance_repo: BalanceRepo
    ):
        super().__init__()
        self._setup_ui()
        self.controller = DailyBalanceController(self, transactions_fn, transaction_types, transaction_methods,
                                                 balance_repo)

    def _setup_ui(self):
        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        # UI title.
        self.lbl = QLabel(self.widget)
        self.layout.addWidget(self.lbl)
        config_lbl(self.lbl, "Caja diaria")

        # Balance.
        self.balance_layout = QGridLayout()
        self.layout.addLayout(self.balance_layout)

        self.method_lbl = QLabel(self.widget)
        self.method_lbl.setText("Método")
        self.balance_layout.addWidget(self.method_lbl, 1, 0)

        self.income_lbl = QLabel(self.widget)
        self.income_lbl.setText("Ingresos")
        self.balance_layout.addWidget(self.income_lbl, 1, 1)

        self.expenses_lbl = QLabel(self.widget)
        self.expenses_lbl.setText("Egresos")
        self.balance_layout.addWidget(self.expenses_lbl, 1, 2)

        self.cash_lbl = QLabel(self.widget)
        self.cash_lbl.setText("Efectivo")
        self.balance_layout.addWidget(self.cash_lbl, 2, 0)

        self.debit_lbl = QLabel(self.widget)
        self.debit_lbl.setText("Débito")
        self.balance_layout.addWidget(self.debit_lbl, 3, 0)

        self.credit_lbl = QLabel(self.widget)
        self.credit_lbl.setText("Crédito")
        self.balance_layout.addWidget(self.credit_lbl, 4, 0)

        self.total_lbl = QLabel(self.widget)
        self.total_lbl.setText("TOTAL")
        self.balance_layout.addWidget(self.total_lbl, 5, 0)

        # Confirm button.
        self.confirm_btn = QPushButton(self.widget)
        self.confirm_btn.setText("Cerrar caja")
        self.layout.addWidget(self.confirm_btn)
