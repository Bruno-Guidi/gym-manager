from __future__ import annotations

import functools
from datetime import date, time, timedelta
from typing import Callable

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout,
    QSpacerItem, QSizePolicy, QHBoxLayout, QListWidget, QListWidgetItem, QTableWidget, QDesktopWidget, QLineEdit,
    QDialog, QDateEdit, QTextEdit, QComboBox, QCheckBox)

from gym_manager import parsing
from gym_manager.booking.core import BookingSystem, ONE_DAY_TD, time_range, Duration
from gym_manager.contact.core import ContactRepo
from gym_manager.core import api
from gym_manager.core.base import String, Activity, Currency, Number
from gym_manager.core.persistence import (
    ActivityRepo, ClientRepo, SubscriptionRepo, BalanceRepo, TransactionRepo)
from gym_manager.core.security import SecurityHandler, Responsible
from gym_manager.stock.core import ItemRepo
from ui import utils
from ui.accounting import AccountingMainUI
from ui.activity import ActivityMainUI
from ui.booking import BookingMainUI
from ui.client import ClientMainUI
from ui.contact import ContactMainUI
from ui.old_app import OldChargesUI, OldExtractionsUI
from ui.stock import StockMainUI
from ui.widget_config import (
    config_lbl, config_btn, fill_cell, new_config_table, config_line, config_date_edit,
    config_combobox, fill_combobox, config_checkbox)
from ui.widgets import PageIndex


class LoadBackupFromOld(QDialog):
    def __init__(self):
        super().__init__()

        self.confirmed = False
        self.path = ""
        self.since = date.today()

        self.layout = QVBoxLayout(self)

        self.line_edit = QLineEdit(self)
        self.layout.addWidget(self.line_edit)
        config_line(self.line_edit, place_holder="Path")

        self.since_layout = QHBoxLayout()
        self.layout.addLayout(self.since_layout)

        self.since_lbl = QLabel(self)
        self.since_layout.addWidget(self.since_lbl)
        config_lbl(self.since_lbl, "Start point")

        self.since_date_edit = QDateEdit(self)
        self.since_layout.addWidget(self.since_date_edit)
        config_date_edit(self.since_date_edit, date.today(), calendar=True)

        self.ok_btn = QPushButton(self)
        self.layout.addWidget(self.ok_btn)
        config_btn(self.ok_btn, "Ok")
        # noinspection PyUnresolvedReferences
        self.ok_btn.clicked.connect(self.ok_clicked)

    def ok_clicked(self):
        self.confirmed = True
        self.path = self.line_edit.text()
        self.since = self.since_date_edit.date().toPyDate()
        self.line_edit.window().close()


class Controller:
    def __init__(
            self,
            main_ui: MainUI,
            client_repo: ClientRepo,
            activity_repo: ActivityRepo,
            subscription_repo: SubscriptionRepo,
            transaction_repo: TransactionRepo,
            balance_repo: BalanceRepo,
            booking_system: BookingSystem,
            contact_repo: ContactRepo,
            item_repo: ItemRepo,
            security_handler: SecurityHandler,
            backup_fn: Callable = None
    ):
        self.main_ui = main_ui
        self.client_repo = client_repo
        self.activity_repo = activity_repo
        self.subscription_repo = subscription_repo
        self.transaction_repo = transaction_repo
        self.balance_repo = balance_repo
        self.booking_system = booking_system
        self.contact_repo = contact_repo
        self.item_repo = item_repo
        self.security_handler = security_handler
        self.backup_fn = backup_fn

        # Sets callbacks
        # noinspection PyUnresolvedReferences
        self.main_ui.config_btn.clicked.connect(self.show_config_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.clients_btn.clicked.connect(self.show_client_main_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.activities_btn.clicked.connect(self.show_activity_main_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.contact_btn.clicked.connect(self.show_contact_main_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.stock_btn.clicked.connect(self.show_stock_main_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.bookings_btn.clicked.connect(self.show_booking_main_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.accounting_btn.clicked.connect(self.show_accounting_main_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.actions_btn.clicked.connect(self.show_action_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.old_charges_btn.clicked.connect(self.show_old_charges_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.old_extractions_btn.clicked.connect(self.show_old_extractions_ui)

    def show_config_ui(self):
        def setup():
            today = date.today()
            self.security_handler.current_responsible = String("Admin")
            activity = Activity(String("TestAct"), Currency("2000"), String("descr"))
            self.activity_repo.add(activity)
            for i in range(0, 50):
                client = self.client_repo.create(String(str(i)), today, today, Number(i))
                sub = api.subscribe(self.subscription_repo, today, client, activity)
                create_t = functools.partial(self.transaction_repo.create, "Cobro", today, activity.price, "Efectivo",
                                             String("Admin"), "descr", client)
                api.register_subscription_charge(self.subscription_repo, sub, create_t)

            client = [c for c in self.client_repo.all(page_len=1)][0]
            for start in time_range(time(8, 0), time(22, 30), 30):
                self.booking_system.book("1", client, False, today + ONE_DAY_TD, start, Duration(30, "30m"))
                self.booking_system.book("2", client, True, today + ONE_DAY_TD, start, Duration(30, "30m"))
                self.booking_system.book("3", client, False, today + ONE_DAY_TD, start, Duration(30, "30m"))

        def generate_balance():
            self.security_handler.current_responsible = String("Admin")

            def _aux(i):
                when = date.today() - timedelta(days=i)
                self.transaction_repo.create("Extracción", when, Currency(100), "Efectivo", String("TestResp"), "TestDescr")
                self.transaction_repo.create("Extracción", when, Currency(150), "Efectivo", String("TestResp"), "TestDescr")
                self.transaction_repo.create("Extracción", when, Currency(350), "Efectivo", String("TestResp"), "TestDescr")
                self.transaction_repo.create("Extracción", when, Currency(150), "Efectivo", String("TestResp"), "TestDescr")
                self.transaction_repo.create("Extracción", when, Currency(350), "Efectivo", String("TestResp"), "TestDescr")

                balance, transactions = api.generate_balance(self.transaction_repo.all())
                api.close_balance(self.transaction_repo, self.balance_repo, balance, transactions, when, String("TestResp"),
                                  functools.partial(self.transaction_repo.create, "Extracción", when, Currency(100),
                                                    "Débito", String("Admin"), "TestDescr"))

            for x in range(32, 0, -1):
                _aux(x)

        def raise_exception():
            raise ValueError("This is a test exception to see if the error is logged.")

        def load_backup_from_old():
            self._backup_ui = LoadBackupFromOld()
            self._backup_ui.setWindowModality(Qt.ApplicationModal)
            self._backup_ui.exec_()
            if self._backup_ui.confirmed:
                parsing.parse(self.activity_repo, self.client_repo, self.subscription_repo, self.transaction_repo,
                              since=self._backup_ui.since, backup_path=self._backup_ui.path,
                              contact_repo=self.contact_repo)

        def add_responsible():
            self._responsible_ui = ResponsibleUI()
            self._responsible_ui.exec_()
            for responsible in self._responsible_ui.responsible_list:
                self.security_handler.add_responsible(responsible)

        # noinspection PyAttributeOutsideInit
        self._config_ui = ConfigUI(("setup", setup), ("balances", generate_balance),
                                   ("raise exception", raise_exception), ("load backup from old", load_backup_from_old),
                                   ("add responsible", add_responsible))
        self._config_ui.setWindowModality(Qt.ApplicationModal)
        self._config_ui.show()

    # noinspection PyAttributeOutsideInit
    def show_client_main_ui(self):
        activities_fn = functools.partial(self.activity_repo.all, 1)
        self.client_main_ui = ClientMainUI(self.client_repo, self.subscription_repo, self.transaction_repo,
                                           self.security_handler, activities_fn, self.contact_repo)
        self.client_main_ui.setWindowModality(Qt.ApplicationModal)
        self.client_main_ui.show()

    # noinspection PyAttributeOutsideInit
    def show_activity_main_ui(self):
        self.activity_main_ui = ActivityMainUI(self.activity_repo, self.security_handler)
        self.activity_main_ui.setWindowModality(Qt.ApplicationModal)
        self.activity_main_ui.show()

    def show_contact_main_ui(self):
        # noinspection PyAttributeOutsideInit
        self.contact_main_ui = ContactMainUI(self.contact_repo, self.client_repo)
        self.contact_main_ui.setWindowModality(Qt.ApplicationModal)
        self.contact_main_ui.show()

    def show_stock_main_ui(self):
        # noinspection PyAttributeOutsideInit
        self.stock_main_ui = StockMainUI(self.item_repo, self.transaction_repo, self.security_handler)
        self.stock_main_ui.setWindowModality(Qt.ApplicationModal)
        self.stock_main_ui.show()

    # noinspection PyAttributeOutsideInit
    def show_accounting_main_ui(self):
        self.accounting_main_ui = AccountingMainUI(self.transaction_repo, self.balance_repo, self.security_handler)
        self.accounting_main_ui.setWindowModality(Qt.ApplicationModal)
        self.accounting_main_ui.show()

    # noinspection PyAttributeOutsideInit
    def show_booking_main_ui(self):
        self.booking_main_ui = BookingMainUI(self.client_repo, self.transaction_repo, self.booking_system,
                                             self.security_handler)
        self.booking_main_ui.setWindowModality(Qt.ApplicationModal)
        self.booking_main_ui.show()

    def show_action_ui(self):
        # noinspection PyAttributeOutsideInit
        self.action_ui = ActionUI(self.security_handler)
        self.action_ui.setWindowModality(Qt.ApplicationModal)
        self.action_ui.show()

    def show_old_charges_ui(self):
        self.old_charges_ui = OldChargesUI()
        self.old_charges_ui.setWindowModality(Qt.ApplicationModal)
        self.old_charges_ui.show()

    def show_old_extractions_ui(self):
        self.old_extractions_ui = OldExtractionsUI()
        self.old_extractions_ui.setWindowModality(Qt.ApplicationModal)
        self.old_extractions_ui.show()

    def close(self):
        if self.backup_fn is not None:
            self.backup_fn()


class MainUI(QMainWindow):
    def __init__(
            self,
            client_repo: ClientRepo,
            activity_repo: ActivityRepo,
            subscription_repo: SubscriptionRepo,
            transaction_repo: TransactionRepo,
            balance_repo: BalanceRepo,
            booking_system: BookingSystem,
            contact_repo: ContactRepo,
            item_repo: ItemRepo,
            security_handler: SecurityHandler,
            enable_tools: bool = False,
            backup_fn: Callable = None
    ):
        super().__init__()
        self._setup_ui(enable_tools)
        self.controller = Controller(self, client_repo, activity_repo, subscription_repo, transaction_repo,
                                     balance_repo, booking_system, contact_repo, item_repo, security_handler, backup_fn)

    def _setup_ui(self, enable_tools: bool):
        self.setWindowTitle("Gestor La Cascada")

        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        self.header_layout = QHBoxLayout()
        self.layout.addLayout(self.header_layout)
        self.header_layout.setContentsMargins(45, 30, 0, 0)

        self.config_btn = QPushButton(self.widget)
        self.header_layout.addWidget(self.config_btn)
        config_btn(self.config_btn, icon_path="ui/resources/config.png", icon_size=32, enabled=enable_tools)

        self.name_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.name_lbl, alignment=Qt.AlignLeft)
        config_lbl(self.name_lbl, "Gestor La Cascada", font_size=28)

        # Vertical spacer.
        self.layout.addSpacerItem(QSpacerItem(30, 40, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        self.top_grid_layout = QGridLayout()
        self.layout.addLayout(self.top_grid_layout)

        self.clients_btn = QPushButton(self.widget)
        self.top_grid_layout.addWidget(self.clients_btn, 0, 0, alignment=Qt.AlignCenter)
        config_btn(self.clients_btn, icon_path="ui/resources/clients.png", icon_size=96)

        self.clients_lbl = QLabel(self.widget)
        self.top_grid_layout.addWidget(self.clients_lbl, 1, 0, alignment=Qt.AlignCenter)
        config_lbl(self.clients_lbl, "Clientes", font_size=18, fixed_width=200, alignment=Qt.AlignCenter)

        self.activities_btn = QPushButton(self.widget)
        self.top_grid_layout.addWidget(self.activities_btn, 0, 1, alignment=Qt.AlignCenter)
        config_btn(self.activities_btn, icon_path="ui/resources/activities.png", icon_size=96)

        self.activities_lbl = QLabel(self.widget)
        self.top_grid_layout.addWidget(self.activities_lbl, 1, 1, alignment=Qt.AlignCenter)
        config_lbl(self.activities_lbl, "Actividades", font_size=18, fixed_width=200, alignment=Qt.AlignCenter)

        self.contact_btn = QPushButton(self.widget)
        self.top_grid_layout.addWidget(self.contact_btn, 0, 2, alignment=Qt.AlignCenter)
        config_btn(self.contact_btn, icon_path="ui/resources/detail.png", icon_size=96)

        self.contact_lbl = QLabel(self.widget)
        self.top_grid_layout.addWidget(self.contact_lbl, 1, 2, alignment=Qt.AlignCenter)
        config_lbl(self.contact_lbl, "Agenda", font_size=18, fixed_width=200, alignment=Qt.AlignCenter)

        self.stock_btn = QPushButton(self.widget)
        self.top_grid_layout.addWidget(self.stock_btn, 0, 3, alignment=Qt.AlignCenter)
        config_btn(self.stock_btn, icon_path="ui/resources/stock.png", icon_size=96)

        self.stock_lbl = QLabel(self.widget)
        self.top_grid_layout.addWidget(self.stock_lbl, 1, 3, alignment=Qt.AlignCenter)
        config_lbl(self.stock_lbl, "Stock", font_size=18, fixed_width=200, alignment=Qt.AlignCenter)

        # Vertical spacer.
        self.layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        self.bottom_grid_layout = QGridLayout()
        self.layout.addLayout(self.bottom_grid_layout)

        self.bookings_btn = QPushButton(self.widget)
        self.bottom_grid_layout.addWidget(self.bookings_btn, 0, 0, alignment=Qt.AlignCenter)
        config_btn(self.bookings_btn, icon_path="ui/resources/bookings.png", icon_size=96)

        self.bookings_lbl = QLabel(self.widget)
        self.bottom_grid_layout.addWidget(self.bookings_lbl, 1, 0, alignment=Qt.AlignCenter)
        config_lbl(self.bookings_lbl, "Turnos", font_size=18, fixed_width=200, alignment=Qt.AlignCenter)

        self.accounting_btn = QPushButton(self.widget)
        self.bottom_grid_layout.addWidget(self.accounting_btn, 0, 1, alignment=Qt.AlignCenter)
        config_btn(self.accounting_btn, icon_path="ui/resources/accounting.png", icon_size=96)

        self.accounting_lbl = QLabel(self.widget)
        self.bottom_grid_layout.addWidget(self.accounting_lbl, 1, 1, alignment=Qt.AlignCenter)
        config_lbl(self.accounting_lbl, "Contabilidad", font_size=18, fixed_width=200, alignment=Qt.AlignCenter)

        self.actions_btn = QPushButton(self.widget)
        self.bottom_grid_layout.addWidget(self.actions_btn, 0, 2, alignment=Qt.AlignCenter)
        config_btn(self.actions_btn, icon_path="ui/resources/actions.png", icon_size=96)

        self.actions_lbl = QLabel(self.widget)
        self.bottom_grid_layout.addWidget(self.actions_lbl, 1, 2, alignment=Qt.AlignCenter)
        config_lbl(self.actions_lbl, "Registro", font_size=18, fixed_width=200, alignment=Qt.AlignCenter)

        self.old_charges_btn = QPushButton(self.widget)
        self.bottom_grid_layout.addWidget(self.old_charges_btn, 0, 3, alignment=Qt.AlignCenter)
        config_btn(self.old_charges_btn, icon_path="ui/resources/charge.png", icon_size=96)

        self.old_charges_lbl = QLabel(self.widget)
        self.bottom_grid_layout.addWidget(self.old_charges_lbl, 1, 3, alignment=Qt.AlignCenter)
        config_lbl(self.old_charges_lbl, "Cobros anteriores", font_size=18, fixed_width=200, alignment=Qt.AlignCenter)

        self.old_extractions_btn = QPushButton(self.widget)
        self.bottom_grid_layout.addWidget(self.old_extractions_btn, 0, 4, alignment=Qt.AlignCenter)
        config_btn(self.old_extractions_btn, icon_path="ui/resources/charge.png", icon_size=96)

        self.old_extractions_lbl = QLabel(self.widget)
        self.bottom_grid_layout.addWidget(self.old_extractions_lbl, 1, 4, alignment=Qt.AlignCenter)
        config_lbl(self.old_extractions_lbl, "Extracciones anteriores", font_size=18, fixed_width=200,
                   alignment=Qt.AlignCenter)

        # Adjusts size.
        self.setFixedSize(self.sizeHint())

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.controller.close()
        super().closeEvent(a0)


class ConfigButtonItem(QWidget):
    def __init__(self, text: str, fn: Callable, item: QListWidgetItem):
        super().__init__()

        self.layout = QHBoxLayout(self)

        self.btn = QPushButton(self)
        self.layout.addWidget(self.btn)
        config_btn(self.btn, text)

        item.setSizeHint(self.sizeHint())

        # noinspection PyUnresolvedReferences
        self.btn.clicked.connect(fn)


class ConfigController:
    def __init__(self, config_ui: ConfigUI, *functions):
        self.config_ui = config_ui

        # Adds functions to config.
        for pair in functions:
            self._create_item(self.config_ui.list, pair[0], pair[1])

    def _create_item(self, dst: QListWidget, text: str, fn: Callable):
        item = QListWidgetItem(self.config_ui.list)
        dst.addItem(item)
        dst.setItemWidget(item, ConfigButtonItem(text, fn, item))


class ConfigUI(QMainWindow):
    def __init__(self, *functions):
        super().__init__()
        self._setup_ui()

        self.controller = ConfigController(self, *functions)

    def _setup_ui(self):
        self.setWindowTitle("Configuración")

        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        self.list = QListWidget(self.widget)
        self.layout.addWidget(self.list)


class ActionController:

    def __init__(self, action_ui: ActionUI, security_handler: SecurityHandler) -> None:
        self.security_handler = security_handler
        self.action_ui = action_ui

        fill_combobox(self.action_ui.action_combobox,
                      ((display, action) for display, action in utils.ACTION_NAMES.items()),
                      display=lambda action_name: action_name[0])
        config_combobox(self.action_ui.action_combobox)

        # Configures the page index.
        self.action_ui.page_index.config(refresh_table=self.fill_action_table, page_len=20, show_info=False)

        self.enable_filtering()

        # Fills the table.
        self.fill_action_table()

        # noinspection PyUnresolvedReferences
        self.action_ui.action_combobox.currentIndexChanged.connect(self.fill_action_table)
        # noinspection PyUnresolvedReferences
        self.action_ui.filter_checkbox.stateChanged.connect(self.enable_filtering)

    def enable_filtering(self):
        self.action_ui.action_combobox.setEnabled(self.action_ui.filter_checkbox.isChecked())
        self.fill_action_table()

    def fill_action_table(self):
        self.action_ui.action_table.setRowCount(0)

        tag = self.action_ui.action_combobox.currentData(Qt.UserRole)[1]
        actions_it = self.security_handler.actions(self.action_ui.page_index.page, self.action_ui.page_index.page_len,
                                                   tag=tag if self.action_ui.filter_checkbox.isChecked() else None)
        for row, (when, resp, _, action_name) in enumerate(actions_it):
            fill_cell(self.action_ui.action_table, row, 0, when.strftime(utils.DATE_TIME_FORMAT), bool)
            fill_cell(self.action_ui.action_table, row, 1, resp.name, str)
            fill_cell(self.action_ui.action_table, row, 2, action_name, str)


class ActionUI(QMainWindow):
    def __init__(self, security_handler: SecurityHandler):
        super().__init__()
        self._setup_ui()
        self.controller = ActionController(self, security_handler)

    def _setup_ui(self):
        self.setWindowTitle("Registro de acciones")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        # Pseudo-filter.
        self.filter_layout = QHBoxLayout()
        self.layout.addLayout(self.filter_layout)
        self.filter_layout.setContentsMargins(240, 0, 240, 0)

        self.filter_checkbox = QCheckBox(self.widget)
        self.filter_layout.addWidget(self.filter_checkbox)
        config_checkbox(self.filter_checkbox, "Acción")

        self.action_combobox = QComboBox(self.widget)  # The configuration is done in the controller.
        self.filter_layout.addWidget(self.action_combobox)

        # Actions.
        self.action_table = QTableWidget(self.widget)
        self.layout.addWidget(self.action_table)
        new_config_table(self.action_table, width=900,
                         columns={"Fecha": (.25, bool), "Responsable": (.25, bool), "Acción": (.5, bool)},
                         min_rows_to_show=10)

        # Index.
        self.page_index = PageIndex(self)
        self.layout.addWidget(self.page_index)

        self.move(int(QDesktopWidget().geometry().center().x() - self.sizeHint().width() / 2),
                  int(QDesktopWidget().geometry().center().y() - self.sizeHint().height() / 2))


class ResponsibleUI(QDialog):
    def __init__(self):
        super().__init__()
        self._setup_ui()

        self.responsible_list: list[Responsible] = []

        # noinspection PyUnresolvedReferences
        self.confirm_btn.clicked.connect(self.parse_responsible)
        # noinspection PyUnresolvedReferences
        self.cancel_btn.clicked.connect(self.reject)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)

        self.responsible_text = QTextEdit(self)
        config_line(self.responsible_text, place_holder="RespName:code\nRespName:code")
        self.layout.addWidget(self.responsible_text)

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
        self.setMaximumSize(self.minimumWidth(), self.minimumHeight())

    def parse_responsible(self):
        for name_code in self.responsible_text.toPlainText().split("\n"):
            name, code = name_code.split(":")
            self.responsible_list.append(Responsible(String(name), String(code)))
        self.confirm_btn.window().close()
