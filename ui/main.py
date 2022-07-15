from __future__ import annotations

import functools
from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout,
    QSpacerItem, QSizePolicy, QHBoxLayout, QListWidget, QListWidgetItem)

from gym_manager.booking.core import BookingSystem
from gym_manager.core.persistence import ActivityRepo, ClientRepo, SubscriptionRepo, BalanceRepo, TransactionRepo
from gym_manager.core.security import SecurityHandler
from ui.accounting import AccountingMainUI
from ui.activity import ActivityMainUI
from ui.booking import BookingMainUI
from ui.client import ClientMainUI
from ui.widget_config import config_lbl, config_btn


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
            security_handler: SecurityHandler
    ):
        self.main_ui = main_ui
        self.client_repo = client_repo
        self.activity_repo = activity_repo
        self.subscription_repo = subscription_repo
        self.transaction_repo = transaction_repo
        self.balance_repo = balance_repo
        self.booking_system = booking_system
        self.security_handler = security_handler

        # Sets callbacks
        # noinspection PyUnresolvedReferences
        self.main_ui.config_btn.clicked.connect(self.show_config_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.clients_btn.clicked.connect(self.show_client_main_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.activities_btn.clicked.connect(self.show_activity_main_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.bookings_btn.clicked.connect(self.show_booking_main_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.accounting_btn.clicked.connect(self.show_accounting_main_ui)

    def show_config_ui(self):
        add_resp_fn = functools.partial(add_responsible, self.security_handler)

        # noinspection PyAttributeOutsideInit
        self._config_ui = ConfigUI(("Add responsible", add_resp_fn),)
        self._config_ui.setWindowModality(Qt.ApplicationModal)
        self._config_ui.show()

    # noinspection PyAttributeOutsideInit
    def show_client_main_ui(self):
        activities_fn = functools.partial(self.activity_repo.all, 1)
        self.client_main_ui = ClientMainUI(self.client_repo, self.subscription_repo, self.transaction_repo,
                                           self.security_handler, activities_fn)
        self.client_main_ui.setWindowModality(Qt.ApplicationModal)
        self.client_main_ui.show()

    # noinspection PyAttributeOutsideInit
    def show_activity_main_ui(self):
        self.activity_main_ui = ActivityMainUI(self.activity_repo, self.security_handler)
        self.activity_main_ui.setWindowModality(Qt.ApplicationModal)
        self.activity_main_ui.show()

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


class MainUI(QMainWindow):
    def __init__(
            self,
            client_repo: ClientRepo,
            activity_repo: ActivityRepo,
            subscription_repo: SubscriptionRepo,
            transaction_repo: TransactionRepo,
            balance_repo: BalanceRepo,
            booking_system: BookingSystem,
            security_handler: SecurityHandler
    ):
        super().__init__()
        self._setup_ui()
        self.controller = Controller(self, client_repo, activity_repo, subscription_repo, transaction_repo,
                                     balance_repo, booking_system, security_handler)

    def _setup_ui(self):
        self.setWindowTitle("Gestor La Cascada")

        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        self.header_layout = QHBoxLayout()
        self.layout.addLayout(self.header_layout)

        self.name_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.name_lbl)
        config_lbl(self.name_lbl, "La cascada", font_size=28)

        # Horizontal spacer.
        self.layout.addSpacerItem(QSpacerItem(30, 10, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum))

        self.config_btn = QPushButton(self.widget)
        self.header_layout.addWidget(self.config_btn)
        config_btn(self.config_btn, icon_path="", icon_size=32)

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

        # Adjusts size.
        self.setFixedSize(self.sizeHint())


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
