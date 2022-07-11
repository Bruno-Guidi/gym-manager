from __future__ import annotations

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QLabel, QGridLayout, QPushButton, QLineEdit, QDialog,
    QComboBox, QTextEdit, QSpacerItem, QSizePolicy, QCheckBox, QDateEdit)

from gym_manager.core import api, constants
from gym_manager.core.base import DateGreater, DateLesser, Currency, Transaction, String, Client, Balance
from gym_manager.core.persistence import TransactionRepo, BalanceRepo
from ui.widget_config import (
    config_table, config_lbl, config_btn, config_line, fill_cell, config_combobox,
    fill_combobox, config_layout, config_checkbox, config_date_edit)
from ui.widgets import Separator, Field, Dialog


class MainController:
    def __init__(self, acc_main_ui: AccountingMainUI, transaction_repo: TransactionRepo, balance_repo: BalanceRepo):
        self.acc_main_ui = acc_main_ui
        self.transaction_repo = transaction_repo
        self._types_dict: dict[str, int] = {type_: i + 2 for i, type_ in enumerate(("Cobro", "Extracción"))}
        self._methods_dict: dict[str, int] = {method: i + 1 for i, method
                                              in enumerate((*transaction_repo.methods, "Total"))}
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
        self.acc_main_ui.today_charges_line.setText(str(self.balance.get("Cobro", Currency(0))))

        # Shows transactions of the day.
        for i, transaction in enumerate(self._today_transactions):
            fill_cell(self.acc_main_ui.transaction_table, i, 0, transaction.responsible, data_type=str)
            name = transaction.client.name if transaction.client is not None else "-"
            fill_cell(self.acc_main_ui.transaction_table, i, 1, name, data_type=str)
            fill_cell(self.acc_main_ui.transaction_table, i, 2, transaction.amount, data_type=int)
            fill_cell(self.acc_main_ui.transaction_table, i, 3, transaction.description, data_type=str)

        # Fills detailed balance.
        for type_name, row in self._types_dict.items():
            type_balance = self.balance[type_name]
            for method_name, col in self._methods_dict.items():
                lbl = QLabel(self.acc_main_ui.widget)
                config_lbl(lbl, Currency.fmt(type_balance.get(method_name, Currency(0))))
                self.acc_main_ui.detail_layout.addWidget(lbl, row, col, alignment=Qt.AlignRight)

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.acc_main_ui.close_balance_btn.clicked.connect(self.close_balance)
        # noinspection PyUnresolvedReferences
        self.acc_main_ui.history_btn.clicked.connect(self.balance_history)

    def close_balance(self):
        self._daily_balance_ui = DailyBalanceUI(self.balance_repo, self.transaction_repo, self.balance)
        self._daily_balance_ui.exec_()

    def balance_history(self):
        self._history_ui = BalanceHistoryUI()
        self._history_ui.setWindowModality(Qt.ApplicationModal)
        self._history_ui.show()


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
                     columns={"Responsable": (8, str), "Cliente": (8, str), "Monto": (8, int),
                              "Descripción": (12, str)})

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
        self.detail_layout.addWidget(self.cash_lbl, 1, 1, alignment=Qt.AlignCenter)
        config_lbl(self.cash_lbl, "Efectivo")

        self.debit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.debit_lbl, 1, 2, alignment=Qt.AlignCenter)
        config_lbl(self.debit_lbl, "Débito")

        self.credit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.credit_lbl, 1, 3, alignment=Qt.AlignCenter)
        config_lbl(self.credit_lbl, "Crédito")

        self.total_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.total_lbl, 1, 4, alignment=Qt.AlignCenter)
        config_lbl(self.total_lbl, "TOTAL")


class DailyBalanceController:
    def __init__(
            self, daily_balance_ui: DailyBalanceUI, balance_repo: BalanceRepo, transaction_repo: TransactionRepo,
            balance: Balance
    ):
        self.daily_balance_ui = daily_balance_ui
        self.balance_repo = balance_repo
        self.transaction_repo = transaction_repo
        self.balance = balance

        # Fills line edits.
        self.daily_balance_ui.cash_line.setText(Currency.fmt(self.balance["Cobro"].get("Efectivo", Currency(0))))
        self.daily_balance_ui.debit_line.setText(Currency.fmt(self.balance["Cobro"].get("Débito", Currency(0))))
        self.daily_balance_ui.credit_line.setText(Currency.fmt(self.balance["Cobro"].get("Crédito", Currency(0))))

        # Fills method combobox.
        fill_combobox(self.daily_balance_ui.method_combobox, transaction_repo.methods, lambda method: method)

        # Sets callbacks
        # noinspection PyUnresolvedReferences
        self.daily_balance_ui.confirm_btn.clicked.connect(self.close_balance)
        # noinspection PyUnresolvedReferences
        self.daily_balance_ui.cancel_btn.clicked.connect(self.daily_balance_ui.reject)

    def close_balance(self):
        if not (self.daily_balance_ui.responsible_field.valid_value()
                and self.daily_balance_ui.extract_field.valid_value()):
            Dialog.info("Error", "Hay campos que no son válidos.")
        else:
            overwrite, today = True, date.today()
            if self.balance_repo.balance_done(today):
                overwrite = Dialog.confirm(  # ToDo block balance if it was already done for the day.
                    f"Ya hay una caja diaria calculada para la fecha {today}.\n¿Desea sobreescribirla?", "Si", "No"
                )
            if overwrite:
                # noinspection PyTypeChecker
                self.transaction_repo.create("Extracción", today, self.daily_balance_ui.extract_field.value(),
                                             self.daily_balance_ui.method_combobox.currentText(),
                                             self.daily_balance_ui.responsible_field.value(),
                                             description=f"Extracción al cierre de caja diaria del día {today}.")
                # noinspection PyTypeChecker
                api.close_balance(self.transaction_repo, self.balance_repo, self.balance, today,
                                  self.daily_balance_ui.responsible_field.value())
                Dialog.info("Éxito", "Caja diaria calculada correctamente.")
                self.daily_balance_ui.confirm_btn.window().close()


class DailyBalanceUI(QDialog):
    def __init__(self, balance_repo: BalanceRepo, transaction_repo: TransactionRepo, balance: Balance) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = DailyBalanceController(self, balance_repo, transaction_repo, balance)

    def _setup_ui(self):
        self.setWindowTitle("Cerrar caja diaria")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)

        # Responsible.
        self.responsible_lbl = QLabel(self)
        self.form_layout.addWidget(self.responsible_lbl, 0, 0)
        config_lbl(self.responsible_lbl, "Responsable*")

        self.responsible_field = Field(String, parent=self, max_len=constants.CLIENT_NAME_CHARS)
        self.form_layout.addWidget(self.responsible_field, 0, 1)
        config_line(self.responsible_field)

        # Cash amount.
        self.cash_lbl = QLabel(self)
        self.form_layout.addWidget(self.cash_lbl, 1, 0)
        config_lbl(self.cash_lbl, "Caja Efectivo")

        self.cash_line = QLineEdit(parent=self)
        self.form_layout.addWidget(self.cash_line, 1, 1)
        config_line(self.cash_line, enabled=False, alignment=Qt.AlignRight)

        # Debit amount.
        self.debit_lbl = QLabel(self)
        self.form_layout.addWidget(self.debit_lbl, 2, 0)
        config_lbl(self.debit_lbl, "Caja Débito")

        self.debit_line = QLineEdit(parent=self)
        self.form_layout.addWidget(self.debit_line, 2, 1)
        config_line(self.debit_line, enabled=False, alignment=Qt.AlignRight)

        # Credit amount.
        self.credit_lbl = QLabel(self)
        self.form_layout.addWidget(self.credit_lbl, 3, 0)
        config_lbl(self.credit_lbl, "Caja Crédito")

        self.credit_line = QLineEdit(parent=self)
        self.form_layout.addWidget(self.credit_line, 3, 1)
        config_line(self.credit_line, enabled=False, alignment=Qt.AlignRight)

        # Extracted amount.
        self.extract_lbl = QLabel(self)
        self.form_layout.addWidget(self.extract_lbl, 4, 0)
        config_lbl(self.extract_lbl, "Monto extracción*")

        self.extract_field = Field(Currency, self)  # ToDo check that the currency is always positive.
        self.form_layout.addWidget(self.extract_field, 4, 1)
        config_line(self.extract_field, place_holder="00000,00", alignment=Qt.AlignRight)

        # Method.
        self.method_lbl = QLabel(self)
        self.form_layout.addWidget(self.method_lbl, 5, 0)
        config_lbl(self.method_lbl, "Método extracción")

        self.method_combobox = QComboBox(self)
        self.form_layout.addWidget(self.method_combobox, 5, 1)
        config_combobox(self.method_combobox, fixed_width=self.extract_field.width())

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


# class BalanceHistoryController:
#     ONE_WEEK_TD = ("7 días", timedelta(days=7))
#     TWO_WEEK_TD = ("14 días", timedelta(days=14))
#     ONE_MONTH_TD = ("30 días", timedelta(days=30))
#
#     def __init__(self, history_ui: BalanceHistoryUI, balance_repo: BalanceRepo, accounting_system: AccountingSystem):
#         self.history_ui = history_ui
#         self.balance_repo = balance_repo
#         self.accounting_system = accounting_system
#
#         self.updated_date_checkbox()
#
#         fill_combobox(self.history_ui.last_n_combobox, (self.ONE_WEEK_TD, self.TWO_WEEK_TD, self.ONE_MONTH_TD),
#                       display=lambda pair: pair[0])
#
#         self._balances: dict[int, tuple[date, String, Balance]] = {}
#         self.load_last_n_balances()
#
#         # Sets callbacks.
#         # noinspection PyUnresolvedReferences
#         self.history_ui.last_n_checkbox.stateChanged.connect(self.updated_date_checkbox)
#         # noinspection PyUnresolvedReferences
#         self.history_ui.date_checkbox.stateChanged.connect(self.update_last_n_checkbox)
#         # noinspection PyUnresolvedReferences
#         self.history_ui.last_n_combobox.currentIndexChanged.connect(self.load_last_n_balances)
#         # noinspection PyUnresolvedReferences
#         self.history_ui.date_edit.dateChanged.connect(self.load_date_balance)
#         # noinspection PyUnresolvedReferences
#         self.history_ui.detail_btn.clicked.connect(self.balance_detail_ui)
#
#     def update_last_n_checkbox(self):
#         """Callback called when the state of date_checkbox changes.
#         """
#         self.history_ui.last_n_checkbox.setChecked(not self.history_ui.date_checkbox.isChecked())
#         self.history_ui.last_n_combobox.setEnabled(not self.history_ui.date_checkbox.isChecked())
#
#     def updated_date_checkbox(self):
#         """Callback called when the state of last_n_checkbox changes.
#         """
#         self.history_ui.date_checkbox.setChecked(not self.history_ui.last_n_checkbox.isChecked())
#         self.history_ui.date_edit.setEnabled(not self.history_ui.last_n_checkbox.isChecked())
#
#     def _load_balance_table(self, from_date: date, to_date: date):
#         self.history_ui.transaction_table.setRowCount(0)
#
#         for when, responsible, balance in self.balance_repo.all(from_date, to_date):
#             row_count = self.history_ui.transaction_table.rowCount()
#             self._balances[row_count] = when, responsible, balance
#             fill_cell(self.history_ui.transaction_table, row_count, 0, when, data_type=int)
#             fill_cell(self.history_ui.transaction_table, row_count, 1, responsible, data_type=str)
#             fill_cell(self.history_ui.transaction_table, row_count, 2, balance["Cobro"]["Total"], data_type=int)
#             fill_cell(self.history_ui.transaction_table, row_count, 3, balance["Extracción"]["Total"], data_type=int)
#
#     def load_last_n_balances(self):
#         td = self.history_ui.last_n_combobox.currentData(Qt.UserRole)[1]
#         self._load_balance_table(from_date=date.today() - td, to_date=date.today())
#
#     def load_date_balance(self):
#         when = self.history_ui.date_edit.date().toPyDate()
#         self._load_balance_table(from_date=when, to_date=when)
#
#     def balance_detail_ui(self):
#         # noinspection PyAttributeOutsideInit
#         if self.history_ui.transaction_table.currentRow() == -1:
#             Dialog.info("Error", "Seleccione una caja diaria.")
#         else:
#             when, responsible, balance = self._balances[self.history_ui.transaction_table.currentRow()]
#             self.daily_balance_ui = DailyBalanceUI(self.accounting_system.transaction_repo,
#                                                    self.balance_repo,
#                                                    self.accounting_system.transactions_types(),
#                                                    self.accounting_system.methods, when, responsible, balance)
#             self.daily_balance_ui.setWindowModality(Qt.ApplicationModal)
#             self.daily_balance_ui.show()


class BalanceHistoryUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_ui()

        # self.controller = BalanceHistoryController(self, balance_repo)

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

        # Header layout.
        self.header_layout = QHBoxLayout()
        self.left_layout.addLayout(self.header_layout)
        config_layout(self.header_layout, left_margin=100, right_margin=100, alignment=Qt.AlignCenter)

        # Filters.
        self.filters_layout = QGridLayout()
        self.header_layout.addLayout(self.filters_layout)

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

        # Horizontal spacer.
        self.header_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Balance detail button.
        self.detail_btn = QPushButton(self.widget)
        self.header_layout.addWidget(self.detail_btn)
        config_btn(self.detail_btn, "Detalle", extra_width=20)

        # Balances.
        self.balance_table = QTableWidget(self.widget)
        self.left_layout.addWidget(self.balance_table)
        config_table(
            target=self.balance_table, allow_resizing=True, min_rows_to_show=1,
            columns={"Fecha": (10, int), "Responsable": (12, str), "Cobros": (12, int),
                     "Extracciones": (12, int)}
        )

        # Balance detail.
        self.detail_layout = QGridLayout()
        self.right_layout.addLayout(self.detail_layout)
        self.detail_layout.setAlignment(Qt.AlignLeft)

        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

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
        self.detail_layout.addWidget(self.cash_lbl, 1, 1, alignment=Qt.AlignCenter)
        config_lbl(self.cash_lbl, "Efectivo")

        self.debit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.debit_lbl, 1, 2, alignment=Qt.AlignCenter)
        config_lbl(self.debit_lbl, "Débito")

        self.credit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.credit_lbl, 1, 3, alignment=Qt.AlignCenter)
        config_lbl(self.credit_lbl, "Crédito")

        self.total_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.total_lbl, 1, 4, alignment=Qt.AlignCenter)
        config_lbl(self.total_lbl, "TOTAL")

        # Transactions of the balance.
        self.transactions_lbl = QLabel(self.widget)
        self.right_layout.addWidget(self.transactions_lbl)
        config_lbl(self.transactions_lbl, "Transacciones", font_size=16)

        self.transaction_table = QTableWidget(self.widget)
        self.right_layout.addWidget(self.transaction_table)
        config_table(self.transaction_table, allow_resizing=False,
                     columns={"Responsable": (8, str), "Cliente": (8, str), "Monto": (8, int),
                              "Descripción": (12, str)})

        # Adjusts size.
        self.setFixedWidth(self.sizeHint().width())


class ChargeController:
    def __init__(
            self,
            charge_ui: ChargeUI,
            transaction_repo: TransactionRepo,
            client: Client,
            amount: Currency,
            description: String
    ) -> None:
        self.charge_ui = charge_ui
        self.transaction_repo = transaction_repo
        self.client, self.amount = client, amount
        self.transaction: Transaction | None = None

        # Sets ui fields.
        self.charge_ui.client_line.setText(str(client.name))
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
        if not self.charge_ui.responsible_field.valid_value():
            Dialog.info("Error", "El campo 'Responsable' no es válido.")
        else:
            # noinspection PyTypeChecker
            self.transaction = self.transaction_repo.create(
                "Cobro", date.today(), self.amount, self.charge_ui.method_combobox.currentText(),
                self.charge_ui.responsible_field.value(), self.charge_ui.descr_text.toPlainText(), self.client
            )
            Dialog.confirm(f"Se ha registrado un cobro con número de identificación '{self.transaction.id}'.")
            self.charge_ui.descr_text.window().close()


class ChargeUI(QDialog):
    def __init__(
            self,
            transaction_repo: TransactionRepo,
            client: Client,
            amount: Currency,
            description: String
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = ChargeController(self, transaction_repo, client, amount, description)

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
        config_line(self.client_line, read_only=True)

        # Method.
        self.method_lbl = QLabel(self)
        self.form_layout.addWidget(self.method_lbl, 1, 0)
        config_lbl(self.method_lbl, "Método")

        self.method_combobox = QComboBox(self)
        self.form_layout.addWidget(self.method_combobox, 1, 1)
        config_combobox(self.method_combobox, fixed_width=self.client_line.width())

        # Amount.
        self.amount_lbl = QLabel(self)
        self.form_layout.addWidget(self.amount_lbl, 2, 0)
        config_lbl(self.amount_lbl, "Monto")

        self.amount_line = QLineEdit(parent=self)
        self.form_layout.addWidget(self.amount_line, 2, 1)
        config_line(self.amount_line, enabled=False)

        # Responsible.
        self.responsible_lbl = QLabel(self)
        self.form_layout.addWidget(self.responsible_lbl, 3, 0)
        config_lbl(self.responsible_lbl, "Responsable*")

        self.responsible_field = Field(String, parent=self, max_len=constants.CLIENT_NAME_CHARS)
        self.form_layout.addWidget(self.responsible_field, 3, 1)
        config_line(self.responsible_field)

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
