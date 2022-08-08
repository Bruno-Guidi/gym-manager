from __future__ import annotations

import functools
from datetime import date, timedelta
from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QLabel, QGridLayout, QPushButton, QLineEdit, QDialog,
    QComboBox, QTextEdit, QSpacerItem, QSizePolicy, QCheckBox, QDateEdit, QDesktopWidget)

from gym_manager.core import api
from gym_manager.core.api import CreateTransactionFn
from gym_manager.core.base import Currency, Transaction, String, Client, Balance
from gym_manager.core.persistence import TransactionRepo, BalanceRepo
from gym_manager.core.security import SecurityHandler, SecurityError
from ui import utils
from ui.utils import MESSAGE
from ui.widget_config import (
    config_lbl, config_btn, config_line, fill_cell, config_combobox,
    fill_combobox, config_checkbox, config_date_edit, new_config_table)
from ui.widgets import Separator, Field, Dialog, responsible_field, valid_text_value


class MainController:
    def __init__(
            self, acc_main_ui: AccountingMainUI, transaction_repo: TransactionRepo, balance_repo: BalanceRepo,
            security_handler: SecurityHandler
    ):
        self.acc_main_ui = acc_main_ui
        self.transaction_repo = transaction_repo
        self.balance_repo = balance_repo
        self.security_handler = security_handler

        fill_combobox(self.acc_main_ui.method_combobox, self.transaction_repo.methods, display=lambda method: method)
        self._today_transactions: list[Transaction] = [t for t in transaction_repo.all()]

        # Calculates charges of the day.
        self.balance, self._today_transactions = api.generate_balance(self._today_transactions)
        self.acc_main_ui.today_charges_line.setText(Currency.fmt(self.balance["Cobro"].get("Total", Currency(0))))
        self.acc_main_ui.today_extractions_line.setText(
            Currency.fmt(self.balance["Extracción"].get("Total", Currency(0)))
        )

        # Shows transactions of the day.
        for i, transaction in enumerate(self._today_transactions):
            fill_cell(self.acc_main_ui.transaction_table, i, 0, transaction.responsible, data_type=str)
            name = transaction.client.name if transaction.client is not None else "-"
            fill_cell(self.acc_main_ui.transaction_table, i, 1, name, data_type=str)
            fill_cell(self.acc_main_ui.transaction_table, i, 2, Currency.fmt(transaction.amount), data_type=int)
            fill_cell(self.acc_main_ui.transaction_table, i, 3, transaction.description, data_type=str)

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.acc_main_ui.close_balance_btn.clicked.connect(self.close_balance)
        # noinspection PyUnresolvedReferences
        self.acc_main_ui.extract_btn.clicked.connect(self.extract)
        # noinspection PyUnresolvedReferences
        self.acc_main_ui.history_btn.clicked.connect(self.balance_history)

    def close_balance(self):
        self.acc_main_ui.responsible_field.setStyleSheet("")

        if not self.acc_main_ui.amount_line.valid_value():
            Dialog.info("Error", "Hay campos que no son válidos.")
            return

        today = date.today()
        if self.balance_repo.balance_done(today):
            Dialog.info("Error", f"La caja diaria del {today.strftime(utils.DATE_FORMAT)} ya fue cerrada.")
            return

        try:
            ok = Dialog.confirm(f"Esta a punto de cerrar la caja del dia {today.strftime(utils.DATE_FORMAT)}."
                                f"\nEsta accion no se puede deshacer, todas las transacciones no incluidas en esta caja"
                                f" diaria se incluiran en la caja del día de mañana."
                                f"\n¿Desea continuar?")

            if ok:
                self.security_handler.current_responsible = self.acc_main_ui.responsible_field.value()

                # noinspection PyTypeChecker
                create_extraction_fn = functools.partial(
                    self.transaction_repo.create, "Extracción", today, self.acc_main_ui.amount_line.value(),
                    self.acc_main_ui.method_combobox.currentText(), self.security_handler.current_responsible.name,
                    description=f"Extracción al cierre de caja diaria del día {today}."
                )
                # noinspection PyTypeChecker
                api.close_balance(self.transaction_repo, self.balance_repo, self.balance, self._today_transactions,
                                  today, self.security_handler.current_responsible.name, create_extraction_fn)

                self.acc_main_ui.transaction_table.setRowCount(0)
                self.acc_main_ui.today_charges_line.setText(Currency.fmt(Currency(0)))
                self.acc_main_ui.today_extractions_line.setText(Currency.fmt(Currency(0)))

                Dialog.info("Éxito",
                            f"La caja diaria del {today.strftime(utils.DATE_FORMAT)} fue cerrada correctamente")
        except SecurityError as sec_err:
            self.acc_main_ui.responsible_field.setStyleSheet("border: 1px solid red")
            Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))

    def extract(self):
        self.acc_main_ui.responsible_field.setStyleSheet("")

        valid_descr, descr = valid_text_value(self.acc_main_ui.description_text, utils.ACTIVITY_DESCR_CHARS)
        if not all([self.acc_main_ui.amount_line.valid_value(), descr]):
            Dialog.info("Error", "Hay campos con valores inválidos.")
            return

        try:
            self.security_handler.current_responsible = self.acc_main_ui.responsible_field.value()
            # noinspection PyTypeChecker
            extraction = api.extract(self.transaction_repo, date.today(), self.acc_main_ui.amount_line.value(),
                                     self.acc_main_ui.method_combobox.currentData(Qt.UserRole),
                                     self.security_handler.current_responsible.name, descr)

            row = self.acc_main_ui.transaction_table.rowCount()
            fill_cell(self.acc_main_ui.transaction_table, row, 0, extraction.responsible, data_type=str)
            name = extraction.client.name if extraction.client is not None else "-"
            fill_cell(self.acc_main_ui.transaction_table, row, 1, name, data_type=str)
            fill_cell(self.acc_main_ui.transaction_table, row, 2, Currency.fmt(extraction.amount), data_type=int)
            fill_cell(self.acc_main_ui.transaction_table, row, 3, extraction.description, data_type=str)

            Dialog.confirm(f"Extracción registrada correctamente.")
        except SecurityError as sec_err:
            self.acc_main_ui.responsible_field.setStyleSheet("border: 1px solid red")
            Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))

    def balance_history(self):
        # noinspection PyAttributeOutsideInit
        self._history_ui = BalanceHistoryUI(self.balance_repo)
        self._history_ui.setWindowModality(Qt.ApplicationModal)
        self._history_ui.show()


class AccountingMainUI(QMainWindow):
    def __init__(self, transaction_repo: TransactionRepo, balance_repo: BalanceRepo, security_handler: SecurityHandler):
        super().__init__()
        self._setup_ui()

        self.controller = MainController(self, transaction_repo, balance_repo, security_handler)

    def _setup_ui(self):
        self.setWindowTitle("Contabilidad")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        # Header layout.
        self.header_layout = QHBoxLayout()
        self.layout.addLayout(self.header_layout)

        # Today charges layout.
        self.today_charges_layout = QVBoxLayout()
        self.header_layout.addLayout(self.today_charges_layout)
        self.today_charges_layout.setAlignment(Qt.AlignTop)
        self.today_charges_layout.setContentsMargins(0, 20, 0, 0)

        self.today_charges_lbl = QLabel(self.widget)
        self.today_charges_layout.addWidget(self.today_charges_lbl)
        config_lbl(self.today_charges_lbl, "Cobros del día")

        self.today_charges_line = QLineEdit(self.widget)
        self.today_charges_layout.addWidget(self.today_charges_line)
        config_line(self.today_charges_line, place_holder="000000,00", enabled=False, alignment=Qt.AlignRight)

        # Today extractions layout.
        self.today_extractions_layout = QVBoxLayout()
        self.header_layout.addLayout(self.today_extractions_layout)
        self.today_extractions_layout.setAlignment(Qt.AlignTop)
        self.today_extractions_layout.setContentsMargins(0, 20, 0, 0)

        self.today_extractions_lbl = QLabel(self.widget)
        self.today_extractions_layout.addWidget(self.today_extractions_lbl)
        config_lbl(self.today_extractions_lbl, "Extracciones del día")

        self.today_extractions_line = QLineEdit(self.widget)
        self.today_extractions_layout.addWidget(self.today_extractions_line)
        config_line(self.today_extractions_line, place_holder="0,00", enabled=False, alignment=Qt.AlignRight)

        self.header_layout.addWidget(Separator(vertical=True, parent=self.widget))  # Vertical line.

        # Buttons.
        self.buttons_layout = QVBoxLayout()
        self.header_layout.addLayout(self.buttons_layout)

        self.close_balance_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.close_balance_btn, alignment=Qt.AlignCenter)
        config_btn(self.close_balance_btn, "Cerrar caja", font_size=16, extra_width=30)

        self.history_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.history_btn, alignment=Qt.AlignCenter)
        config_btn(self.history_btn, "Historial", font_size=16, extra_width=30)

        # Charge button
        self.extract_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.extract_btn, alignment=Qt.AlignCenter)
        config_btn(self.extract_btn, "Extraer")

        self.header_layout.addWidget(Separator(vertical=True, parent=self.widget))  # Vertical line.

        # Extract form.
        self.extract_form_layout = QGridLayout()
        self.header_layout.addLayout(self.extract_form_layout)

        # Responsible.
        self.responsible_lbl = QLabel(self.widget)
        self.extract_form_layout.addWidget(self.responsible_lbl, 0, 0)
        config_lbl(self.responsible_lbl, "Responsable")

        self.responsible_field = responsible_field(self.widget)
        self.extract_form_layout.addWidget(self.responsible_field, 0, 1)
        config_line(self.responsible_field, fixed_width=100)

        # Method.
        self.method_combobox = QComboBox(self)
        self.extract_form_layout.addWidget(self.method_combobox, 0, 2)
        config_combobox(self.method_combobox)

        # Amount.
        self.amount_line = Field(Currency, parent=self, positive=True)
        self.extract_form_layout.addWidget(self.amount_line, 0, 3)
        config_line(self.amount_line, place_holder="000000,00", alignment=Qt.AlignRight)

        self.description_text = QTextEdit(self.widget)
        self.extract_form_layout.addWidget(self.description_text, 1, 0, 1, 4)
        config_line(self.description_text, place_holder="Descripción", adjust_to_hint=False)
        self.description_text.setFixedHeight(80)

        self.layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Transactions of the day.
        self.transactions_lbl = QLabel(self.widget)
        self.layout.addWidget(self.transactions_lbl)
        config_lbl(self.transactions_lbl, "Transacciones", font_size=16)

        self.transaction_table = QTableWidget(self.widget)
        self.layout.addWidget(self.transaction_table)
        new_config_table(self.transaction_table, width=1200,
                         columns={"Responsable": (.2, str), "Cliente": (.2, str), "Monto": (.12, int),
                                  "Descripción": (.48, str)}, min_rows_to_show=20)

        self.setFixedWidth(self.minimumSizeHint().width())


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

        self._transactions: dict[int, list[Transaction]] = {}
        self._balances: dict[int, Balance] = {}
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
        self.history_ui.balance_table.itemSelectionChanged.connect(self.refresh_balance_info)

    def update_last_n_checkbox(self):
        """Callback called when the state of date_checkbox changes.
        """
        self.history_ui.last_n_checkbox.setChecked(not self.history_ui.date_checkbox.isChecked())
        self.history_ui.last_n_combobox.setEnabled(not self.history_ui.date_checkbox.isChecked())
        if self.history_ui.last_n_checkbox.isChecked():
            self.load_last_n_balances()

    def updated_date_checkbox(self):
        """Callback called when the state of last_n_checkbox changes.
        """
        self.history_ui.date_checkbox.setChecked(not self.history_ui.last_n_checkbox.isChecked())
        self.history_ui.date_edit.setEnabled(not self.history_ui.last_n_checkbox.isChecked())
        if self.history_ui.date_checkbox.isChecked():
            self.load_date_balance()

    def _load_balance_table(self, from_date: date, to_date: date):
        self.history_ui.balance_table.setRowCount(0)

        for when, responsible, balance, transactions in self.balance_repo.all(from_date, to_date):
            row_count = self.history_ui.balance_table.rowCount()
            self._transactions[row_count] = transactions
            self._balances[row_count] = balance
            fill_cell(self.history_ui.balance_table, row_count, 0, when, data_type=int)
            fill_cell(self.history_ui.balance_table, row_count, 1, responsible, data_type=str)
            total = balance["Cobro"].get("Total") - balance["Extracción"].get("Total")
            fill_cell(self.history_ui.balance_table, row_count, 2, Currency.fmt(total), data_type=int)

        if self.history_ui.balance_table.rowCount() != 0:
            self.history_ui.balance_table.selectRow(1)

    def load_last_n_balances(self):
        td = self.history_ui.last_n_combobox.currentData(Qt.UserRole)[1]
        self._load_balance_table(from_date=date.today() - td, to_date=date.today())

    def load_date_balance(self):
        when = self.history_ui.date_edit.date().toPyDate()
        self._load_balance_table(from_date=when, to_date=when)

    def refresh_balance_info(self):
        if self.history_ui.balance_table.currentRow() != -1:
            # Loads transactions of the selected daily balance.
            self.history_ui.transaction_table.setRowCount(0)
            transactions = self._transactions[self.history_ui.balance_table.currentRow()]
            for i, transaction in enumerate(transactions):
                fill_cell(self.history_ui.transaction_table, i, 0, transaction.responsible, data_type=str)
                name = transaction.client.name if transaction.client is not None else "-"
                fill_cell(self.history_ui.transaction_table, i, 1, name, data_type=str)
                fill_cell(self.history_ui.transaction_table, i, 2, Currency.fmt(transaction.amount), data_type=int)
                fill_cell(self.history_ui.transaction_table, i, 3, transaction.description, data_type=str)

            # Loads balance detail.
            balance = self._balances[self.history_ui.balance_table.currentRow()]
            charges, extractions = balance["Cobro"], balance["Extracción"]

            config_lbl(self.history_ui.c_cash_lbl, Currency.fmt(charges.get("Efectivo", Currency(0))),
                       alignment=Qt.AlignRight, fixed_width=110)
            config_lbl(self.history_ui.c_debit_lbl, Currency.fmt(charges.get("Débito", Currency(0))),
                       alignment=Qt.AlignRight, fixed_width=110)
            config_lbl(self.history_ui.c_credit_lbl, Currency.fmt(charges.get("Crédito", Currency(0))),
                       alignment=Qt.AlignRight, fixed_width=110)
            config_lbl(self.history_ui.c_total_lbl, Currency.fmt(charges.get("Total", Currency(0))),
                       alignment=Qt.AlignRight, fixed_width=110)

            config_lbl(self.history_ui.e_cash_lbl, Currency.fmt(extractions.get("Efectivo", Currency(0))),
                       alignment=Qt.AlignRight, fixed_width=110)
            config_lbl(self.history_ui.e_debit_lbl, Currency.fmt(extractions.get("Débito", Currency(0))),
                       alignment=Qt.AlignRight, fixed_width=110)
            config_lbl(self.history_ui.e_credit_lbl, Currency.fmt(extractions.get("Crédito", Currency(0))),
                       alignment=Qt.AlignRight, fixed_width=110)
            config_lbl(self.history_ui.e_total_lbl, Currency.fmt(extractions.get("Total", Currency(0))),
                       alignment=Qt.AlignRight, fixed_width=110)


class BalanceHistoryUI(QMainWindow):
    def __init__(self, balance_repo: BalanceRepo):
        super().__init__()
        self._setup_ui()

        self.controller = BalanceHistoryController(self, balance_repo)

    def _setup_ui(self):
        self.setWindowTitle("Historial de cajas diarias")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        self.left_layout = QVBoxLayout()
        self.layout.addLayout(self.left_layout)

        self.layout.addWidget(Separator(vertical=True, parent=self.widget))  # Vertical line.

        self.right_layout = QVBoxLayout()
        self.layout.addLayout(self.right_layout)

        # Filters.
        self.filters_layout = QGridLayout()
        self.left_layout.addLayout(self.filters_layout)
        self.filters_layout.setAlignment(Qt.AlignCenter)

        self.last_n_checkbox = QCheckBox(self.widget)
        self.filters_layout.addWidget(self.last_n_checkbox, 0, 0)
        config_checkbox(self.last_n_checkbox, "Últimos", checked=True, layout_dir=Qt.LayoutDirection.LeftToRight)

        self.date_checkbox = QCheckBox(self.widget)
        self.filters_layout.addWidget(self.date_checkbox, 1, 0)
        config_checkbox(self.date_checkbox, "Fecha", checked=False, layout_dir=Qt.LayoutDirection.LeftToRight)

        self.date_edit = QDateEdit(self.widget)
        self.filters_layout.addWidget(self.date_edit, 1, 1)
        config_date_edit(self.date_edit, date.today(), calendar=True)

        self.last_n_combobox = QComboBox(self.widget)
        self.filters_layout.addWidget(self.last_n_combobox, 0, 1)
        config_combobox(self.last_n_combobox, extra_width=20, fixed_width=self.date_edit.width())

        # Balances.
        self.balance_table = QTableWidget(self.widget)
        self.left_layout.addWidget(self.balance_table)
        new_config_table(self.balance_table, width=500,
                         columns={"Fecha": (.28, bool), "Responsable": (.42, str), "Total": (.3, int)},
                         min_rows_to_show=20, fix_width=True)

        # Balance detail.
        self.detail_layout = QGridLayout()
        self.right_layout.addLayout(self.detail_layout)
        self.detail_layout.setAlignment(Qt.AlignCenter)

        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Balance date label.
        self.detail_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.detail_lbl, 0, 0, 1, 5)
        config_lbl(self.detail_lbl, "Detalle", font_size=18)

        # Detailed balance layout.
        self.method_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.method_lbl, 1, 0)
        config_lbl(self.method_lbl, "Método")

        self.cash_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.cash_lbl, 1, 1, alignment=Qt.AlignCenter)
        config_lbl(self.cash_lbl, "Efectivo", alignment=Qt.AlignRight, fixed_width=110)

        self.debit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.debit_lbl, 1, 2, alignment=Qt.AlignCenter)
        config_lbl(self.debit_lbl, "Débito", alignment=Qt.AlignRight, fixed_width=110)

        self.credit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.credit_lbl, 1, 3, alignment=Qt.AlignCenter)
        config_lbl(self.credit_lbl, "Crédito", alignment=Qt.AlignRight, fixed_width=110)

        self.total_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.total_lbl, 1, 4, alignment=Qt.AlignCenter)
        config_lbl(self.total_lbl, "TOTAL", alignment=Qt.AlignRight, fixed_width=110)

        self.charges_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.charges_lbl, 2, 0)
        config_lbl(self.charges_lbl, "Cobros")

        self.c_cash_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.c_cash_lbl, 2, 1, alignment=Qt.AlignRight)

        self.c_debit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.c_debit_lbl, 2, 2, alignment=Qt.AlignRight)

        self.c_credit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.c_credit_lbl, 2, 3, alignment=Qt.AlignRight)

        self.c_total_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.c_total_lbl, 2, 4, alignment=Qt.AlignRight)

        self.extractions_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.extractions_lbl, 3, 0)
        config_lbl(self.extractions_lbl, "Extracciones")

        self.e_cash_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.e_cash_lbl, 3, 1, alignment=Qt.AlignRight)

        self.e_debit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.e_debit_lbl, 3, 2, alignment=Qt.AlignRight)

        self.e_credit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.e_credit_lbl, 3, 3, alignment=Qt.AlignRight)

        self.e_total_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.e_total_lbl, 3, 4, alignment=Qt.AlignRight)

        # Transactions of the balance.
        self.transactions_lbl = QLabel(self.widget)
        self.right_layout.addWidget(self.transactions_lbl)
        config_lbl(self.transactions_lbl, "Transacciones", font_size=16)

        self.transaction_table = QTableWidget(self.widget)
        self.right_layout.addWidget(self.transaction_table)

        new_config_table(self.transaction_table, width=1200,
                         columns={"Responsable": (.2, str), "Cliente": (.2, str), "Monto": (.15, int),
                                  "Descripción": (.45, str)}, min_rows_to_show=0)

        self.move(int(QDesktopWidget().geometry().center().x() - self.sizeHint().width() / 2),
                  int(QDesktopWidget().geometry().center().y() - self.sizeHint().height() / 2))


class ChargeController:
    def __init__(
            self,
            charge_ui: ChargeUI,
            transaction_repo: TransactionRepo,
            security_handler: SecurityHandler,
            amount: Currency,
            description: String,
            post_charge_fn: Callable[[CreateTransactionFn], Transaction],
            client: Client | None = None
    ) -> None:
        self.charge_ui = charge_ui
        self.transaction_repo = transaction_repo
        self.security_handler = security_handler
        self.client, self.amount = client, amount
        self.transaction: Transaction | None = None
        self.success = False

        # This is a partial function, where the only argument left is a callable that creates a transaction with the
        # data extracted from the form. In this way, the transaction is created in the same place as the subsequent
        # processing that is done with it.
        self.post_charge_fn = post_charge_fn

        # Sets ui fields.
        self.charge_ui.client_line.setText(str(client.name) if client is not None else "")
        self.charge_ui.client_line.setEnabled(client is not None)
        self.charge_ui.amount_line.setText(Currency.fmt(amount))
        fill_combobox(self.charge_ui.method_combobox, transaction_repo.methods,
                      display=lambda method: method)
        self.charge_ui.descr_text.setText(str(description))

        # Sets callbacks
        # noinspection PyUnresolvedReferences
        self.charge_ui.confirm_btn.clicked.connect(self.charge)
        # noinspection PyUnresolvedReferences
        self.charge_ui.cancel_btn.clicked.connect(self.charge_ui.reject)

    def charge(self):
        try:
            self.security_handler.current_responsible = self.charge_ui.responsible_field.value()

            create_transaction_fn = functools.partial(
                self.transaction_repo.create, "Cobro", date.today(), self.amount,
                self.charge_ui.method_combobox.currentText(), self.security_handler.current_responsible.name,
                self.charge_ui.descr_text.toPlainText(), self.client
            )
            self.success = True
            self.post_charge_fn(create_transaction_fn)
            Dialog.confirm(f"Cobro registrado correctamente.")
            self.charge_ui.descr_text.window().close()
        except SecurityError as sec_err:
            Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))


class ChargeUI(QDialog):
    def __init__(
            self,
            transaction_repo: TransactionRepo,
            security_handler: SecurityHandler,
            amount: Currency,
            description: String,
            post_charge_fn: Callable[[CreateTransactionFn], Transaction],
            client: Client | None = None
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = ChargeController(self, transaction_repo, security_handler, amount, description,
                                           post_charge_fn, client)

    def _setup_ui(self):
        self.setWindowTitle("Registrar cobro")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)

        # Client.
        self.client_lbl = QLabel(self)
        self.form_layout.addWidget(self.client_lbl, 0, 0)
        config_lbl(self.client_lbl, "Cliente")

        self.client_line = QLineEdit(self)
        self.form_layout.addWidget(self.client_line, 0, 1)
        config_line(self.client_line, read_only=True, adjust_to_hint=False)

        # Method.
        self.method_lbl = QLabel(self)
        self.form_layout.addWidget(self.method_lbl, 1, 0)
        config_lbl(self.method_lbl, "Método")

        self.method_combobox = QComboBox(self)
        self.form_layout.addWidget(self.method_combobox, 1, 1)
        config_combobox(self.method_combobox)

        # Amount.
        self.amount_lbl = QLabel(self)
        self.form_layout.addWidget(self.amount_lbl, 2, 0)
        config_lbl(self.amount_lbl, "Monto")

        self.amount_line = QLineEdit(parent=self)
        self.form_layout.addWidget(self.amount_line, 2, 1)
        config_line(self.amount_line, enabled=False, adjust_to_hint=False)

        # Responsible.
        self.responsible_lbl = QLabel(self)
        self.form_layout.addWidget(self.responsible_lbl, 3, 0)
        config_lbl(self.responsible_lbl, "Responsable")

        self.responsible_field = responsible_field(self)
        self.form_layout.addWidget(self.responsible_field, 3, 1)
        config_line(self.responsible_field, adjust_to_hint=False)

        # Description.
        self.descr_lbl = QLabel(self)
        self.form_layout.addWidget(self.descr_lbl, 5, 0, alignment=Qt.AlignTop)
        config_lbl(self.descr_lbl, "Descripción")

        self.descr_text = QTextEdit(self)
        self.form_layout.addWidget(self.descr_text, 5, 1)
        config_line(self.descr_text, enabled=False)

        # Vertical spacer.
        self.layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)
        self.buttons_layout.setAlignment(Qt.AlignRight)

        self.confirm_btn = QPushButton(self)
        self.buttons_layout.addWidget(self.confirm_btn)
        config_btn(self.confirm_btn, "Confirmar", extra_width=20)

        self.cancel_btn = QPushButton(self)
        self.buttons_layout.addWidget(self.cancel_btn)
        config_btn(self.cancel_btn, "Cancelar", extra_width=20)

        # Adjusts size.
        self.setFixedSize(self.sizeHint())
