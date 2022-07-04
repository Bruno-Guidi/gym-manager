from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from PyQt5 import QtCore
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget, \
    QTableWidgetItem, QGridLayout, QMenuBar, QAction, QMenu, QComboBox, QDateEdit, QCheckBox

from gym_manager.core import system
from gym_manager.core.base import Client, DateGreater, ClientLike, DateLesser, TextEqual, TextLike, \
    NumberEqual, String, Balance
from gym_manager.core.persistence import BalanceRepo, FilterValuePair, TransactionRepo
from gym_manager.core.system import AccountingSystem
from ui.accounting.operations import ExtractUI
from ui.widget_config import config_layout, config_lbl, config_table, config_combobox, config_btn, fill_combobox, \
    config_date_edit, config_checkbox
from ui.widgets import Dialog, FilterHeader, PageIndex


class MainController:

    def __init__(
            self, main_ui: AccountingMainUI, accounting_system: AccountingSystem, client: Client | None = None
    ) -> None:
        self.main_ui = main_ui

        self.accounting_system = accounting_system
        self.current_page, self.page_len = 1, 20

        # Configure the filtering widget.
        filters = (ClientLike("client_name", display_name="Nombre cliente",
                              translate_fun=lambda trans, value: trans.client.cli_name.contains(value)),
                   NumberEqual("client_dni", display_name="DNI cliente", attr="dni",
                               translate_fun=lambda trans, value: trans.client.dni == value),
                   TextEqual("type", display_name="Tipo", attr="type",
                             translate_fun=lambda trans, value: trans.type == value),
                   TextEqual("method", display_name="Método", attr="method",
                             translate_fun=lambda trans, value: trans.method == value),
                   TextLike("responsible", display_name="Responsable", attr="responsible",
                            translate_fun=lambda trans, value: trans.responsible.contains(value)))
        date_greater_filter = DateGreater("from", display_name="Desde", attr="when",
                                          translate_fun=lambda trans, when: trans.when >= when)
        date_lesser_filter = DateLesser("to", display_name="Hasta", attr="when",
                                        translate_fun=lambda trans, when: trans.when <= when)
        self.main_ui.filter_header.config(filters, self.fill_transaction_table, date_greater_filter, date_lesser_filter)

        if client is not None:  # If a client is given, set the filter with it.
            self.main_ui.filter_header.set_filter("client_dni", str(client.dni))

        # Configures the page index.
        self.main_ui.page_index.config(refresh_table=self.main_ui.filter_header.on_search_click,
                                       page_len=30, total_len=self.accounting_system.transaction_repo.count())

        # Fills the table.
        self.main_ui.filter_header.on_search_click()

        # Sets callbacks
        # noinspection PyUnresolvedReferences
        self.main_ui.generate_balance_action.triggered.connect(self.daily_balance)
        # noinspection PyUnresolvedReferences
        self.main_ui.balance_history_action.triggered.connect(self.balance_history_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.register_extraction_action.triggered.connect(self.extraction)

    def fill_transaction_table(self, filters: list[FilterValuePair]):
        self.main_ui.transaction_table.setRowCount(0)

        self.main_ui.page_index.total_len = self.accounting_system.transaction_repo.count(filters)
        transactions = self.accounting_system.transaction_repo.all(self.current_page, self.page_len, filters)
        for row, transaction in enumerate(transactions):
            self.main_ui.transaction_table.setRowCount(row + 1)
            self.main_ui.transaction_table.setItem(row, 0, QTableWidgetItem(str(transaction.id)))
            self.main_ui.transaction_table.setItem(row, 1, QTableWidgetItem(str(transaction.type)))
            client_name = str(transaction.client.name) if transaction.client is not None else "-"
            self.main_ui.transaction_table.setItem(row, 2, QTableWidgetItem(client_name))
            self.main_ui.transaction_table.setItem(row, 3, QTableWidgetItem(str(transaction.when)))
            self.main_ui.transaction_table.setItem(row, 4, QTableWidgetItem(str(transaction.amount)))
            self.main_ui.transaction_table.setItem(row, 5, QTableWidgetItem(str(transaction.method)))
            self.main_ui.transaction_table.setItem(row, 6, QTableWidgetItem(str(transaction.responsible)))
            self.main_ui.transaction_table.setItem(row, 7, QTableWidgetItem(str(transaction.description)))

    def daily_balance(self):
        # noinspection PyAttributeOutsideInit
        self.daily_balance_ui = DailyBalanceUI(self.accounting_system.transaction_repo,
                                               self.accounting_system.transactions_types(),
                                               self.accounting_system.methods,
                                               self.accounting_system.balance_repo)
        self.daily_balance_ui.setWindowModality(Qt.ApplicationModal)
        self.daily_balance_ui.show()

    def balance_history_ui(self):
        # noinspection PyAttributeOutsideInit
        self._balance_history_ui = BalanceHistoryUI(self.accounting_system.balance_repo)
        self._balance_history_ui.setWindowModality(Qt.ApplicationModal)
        self._balance_history_ui.show()

    def extraction(self):
        self.extract_ui = ExtractUI(self.accounting_system.methods, self.accounting_system.transaction_repo)
        self.extract_ui.exec_()

        extraction, row_count = self.extract_ui.controller.extraction, self.main_ui.transaction_table.rowCount()
        if (extraction is not None and row_count < self.page_len
                and self.main_ui.filter_header.passes_filters(extraction)):
            self.main_ui.transaction_table.setRowCount(row_count + 1)
            self.main_ui.transaction_table.setItem(row_count, 0, QTableWidgetItem(str(extraction.id)))
            self.main_ui.transaction_table.setItem(row_count, 1, QTableWidgetItem(str(extraction.type)))
            self.main_ui.transaction_table.setItem(row_count, 2, QTableWidgetItem("-"))
            self.main_ui.transaction_table.setItem(row_count, 3, QTableWidgetItem(str(extraction.when)))
            self.main_ui.transaction_table.setItem(row_count, 4, QTableWidgetItem(str(extraction.amount)))
            self.main_ui.transaction_table.setItem(row_count, 5, QTableWidgetItem(str(extraction.method)))
            self.main_ui.transaction_table.setItem(row_count, 6, QTableWidgetItem(str(extraction.responsible)))
            self.main_ui.transaction_table.setItem(row_count, 7, QTableWidgetItem(str(extraction.description)))


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

        self.balance_history_action = QAction("Historial", self)
        self.daily_balance_menu.addAction(self.balance_history_action)

        # Extractions menu bar.
        self.extraction_menu = QMenu("Extracción", self)
        self.menu_bar.addMenu(self.extraction_menu)

        self.register_extraction_action = QAction("Registrar", self)
        self.extraction_menu.addAction(self.register_extraction_action)

        # Utilities.
        self.utils_layout = QHBoxLayout()
        self.main_layout.addLayout(self.utils_layout)
        config_layout(self.utils_layout, spacing=0, left_margin=40, top_margin=15, right_margin=40)

        # Filtering.
        self.filter_header = FilterHeader(date_greater_filtering=True, date_lesser_filtering=True, parent=self.widget)
        self.utils_layout.addWidget(self.filter_header)

        # Transactions.
        self.transaction_table = QTableWidget(self.widget)
        self.main_layout.addWidget(self.transaction_table)
        config_table(
            target=self.transaction_table, allow_resizing=True,
            columns={"#": 100, "Tipo": 70, "Cliente": 175, "Fecha": 100, "Monto": 100, "Método": 120,
                     "Responsable": 175, "Descripción": 200}
        )

        # Index.
        self.page_index = PageIndex(self)
        self.main_layout.addWidget(self.page_index)


class DailyBalanceController:
    def __init__(
            self,
            daily_balance_ui: DailyBalanceUI,
            transaction_repo: TransactionRepo,
            balance_repo: BalanceRepo,
            transaction_types: Iterable[String],
            transaction_methods: Iterable[String]
    ):
        self.daily_balance_ui = daily_balance_ui
        self.transaction_repo = transaction_repo
        self.balance_repo = balance_repo

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.daily_balance_ui.confirm_btn.clicked.connect(self.close_balance)

        # Generates the balance.
        types_dict = {trans_type: i + 1 for i, trans_type in enumerate(transaction_types)}
        methods_dict = {trans_method: i + 2 for i, trans_method in enumerate(transaction_methods)}
        methods_dict["Total"] = len(methods_dict) + 2

        transaction_gen: Iterable
        today = date.today()
        if self.balance_repo.balance_done(today):
            # If there is a balance closed, pass date.today().
            transaction_gen = self.transaction_repo.all(page=1, balance_date=today)
        else:
            # If there isn't a closed balance, set include_closed=False.
            transaction_gen = self.transaction_repo.all(page=1, include_closed=False)
        self.transactions = [transaction for transaction in transaction_gen]
        self.balance = system.generate_balance(self.transactions, transaction_types, transaction_methods)

        # Shows balance information in the ui.
        for trans_type, type_balance in self.balance.items():
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
            system.close_balance(self.balance, today, self.transactions, self.transaction_repo, self.balance_repo)
            Dialog.info("Éxito", "Caja diaria calculada correctamente.")
            self.daily_balance_ui.confirm_btn.window().close()


class DailyBalanceUI(QMainWindow):
    def __init__(
            self,
            transaction_repo: TransactionRepo,
            transaction_types: Iterable[String],
            transaction_methods: Iterable[String],
            balance_repo: BalanceRepo
    ):
        super().__init__()
        self._setup_ui()
        self.controller = DailyBalanceController(self, transaction_repo, balance_repo, transaction_types,
                                                 transaction_methods)

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


class BalanceHistoryController:
    ONE_WEEK_TD = ("7 días", timedelta(days=7))
    TWO_WEEK_TD = ("14 días", timedelta(days=14))
    ONE_MONTH_TD = ("30 días", timedelta(days=30))

    def __init__(self, history_ui: BalanceHistoryUI, balance_repo: BalanceRepo):
        self.history_ui = history_ui
        self.balance_repo = balance_repo

        self.updated_date_checkbox()

        fill_combobox(self.history_ui.last_n_combobox, (self.ONE_WEEK_TD, self.TWO_WEEK_TD, self.ONE_MONTH_TD),
                      display=lambda pair: pair[0])

        self._balances: dict[date, Balance] = {}
        self.load_last_n_balances()

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.history_ui.last_n_checkbox.stateChanged.connect(self.updated_date_checkbox)
        # noinspection PyUnresolvedReferences
        self.history_ui.date_checkbox.stateChanged.connect(self.update_last_n_checkbox)
        # noinspection PyUnresolvedReferences
        self.history_ui.last_n_combobox.currentIndexChanged.connect(self.load_last_n_balances)
        # noinspection PyUnresolvedReferences
        self.history_ui.date_edit.dateChanged.connect(self.load_date_balance)
        # noinspection PyUnresolvedReferences
        self.history_ui.detail_btn.clicked.connect(self.balance_detail_ui)

    def update_last_n_checkbox(self):
        """Callback called when the state of date_checkbox changes.
        """
        self.history_ui.last_n_checkbox.setChecked(not self.history_ui.date_checkbox.isChecked())
        self.history_ui.last_n_combobox.setEnabled(not self.history_ui.date_checkbox.isChecked())

    def updated_date_checkbox(self):
        """Callback called when the state of last_n_checkbox changes.
        """
        self.history_ui.date_checkbox.setChecked(not self.history_ui.last_n_checkbox.isChecked())
        self.history_ui.date_edit.setEnabled(not self.history_ui.last_n_checkbox.isChecked())

    def _load_balance_table(self, from_date: date, to_date: date):
        self.history_ui.transaction_table.setRowCount(0)

        for when, balance in self.balance_repo.all(from_date, to_date):
            self._balances[when], row_count = balance, self.history_ui.transaction_table.rowCount()
            self.history_ui.transaction_table.setRowCount(row_count + 1)
            self.history_ui.transaction_table.setItem(row_count, 0, QTableWidgetItem(str(when)))
            self.history_ui.transaction_table.setItem(row_count, 1, QTableWidgetItem(str("resp")))
            self.history_ui.transaction_table.setItem(row_count, 2, QTableWidgetItem(str(balance["Cobro"]["Total"])))
            self.history_ui.transaction_table.setItem(row_count, 3,
                                                      QTableWidgetItem(str(balance["Extracción"]["Total"])))

    def load_last_n_balances(self):
        td = self.history_ui.last_n_combobox.currentData(Qt.UserRole)[1]
        self._load_balance_table(from_date=date.today() - td, to_date=date.today())

    def load_date_balance(self):
        when = self.history_ui.date_edit.date().toPyDate()
        self._load_balance_table(from_date=when, to_date=when)

    def balance_detail_ui(self):
        pass


class BalanceHistoryUI(QMainWindow):
    def __init__(self, balance_repo: BalanceRepo, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

        self.controller = BalanceHistoryController(self, balance_repo)

    def _setup_ui(self):
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        # Header layout.
        self.header_layout = QHBoxLayout()
        self.layout.addLayout(self.header_layout)

        # Last n balances.
        self.last_n_layout = QVBoxLayout()
        self.header_layout.addLayout(self.last_n_layout)

        self.last_n_checkbox = QCheckBox(self.widget)
        self.last_n_layout.addWidget(self.last_n_checkbox)
        config_checkbox(self.last_n_checkbox, True, "Últimos", direction=Qt.LayoutDirection.LeftToRight)

        self.last_n_combobox = QComboBox(self.widget)
        self.last_n_layout.addWidget(self.last_n_combobox)
        config_combobox(self.last_n_combobox)

        # Specific date balance.
        self.date_layout = QVBoxLayout()
        self.header_layout.addLayout(self.date_layout)

        self.date_checkbox = QCheckBox(self.widget)
        self.date_layout.addWidget(self.date_checkbox)
        config_checkbox(self.date_checkbox, False, "Fecha", direction=Qt.LayoutDirection.LeftToRight)

        self.date_edit = QDateEdit(self.widget)
        self.date_layout.addWidget(self.date_edit)
        config_date_edit(self.date_edit, date.today())

        # Balance detail button.
        self.detail_btn = QPushButton(self.widget)
        self.header_layout.addWidget(self.detail_btn)
        config_btn(self.detail_btn, "Detalle")

        # Transactions.
        self.transaction_table = QTableWidget(self.widget)
        self.layout.addWidget(self.transaction_table)
        config_table(
            target=self.transaction_table, allow_resizing=True,
            columns={"Fecha": 100, "Responsable": 175, "Cobros": 100, "Extracciones": 100}
        )
