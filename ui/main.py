from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton

from gym_manager.booking.core import BookingSystem
from gym_manager.core.system import ActivityManager, AccountingSystem
from ui.accounting.main import AccountingMainUI
from ui.activity.main import ActivityMainUI
from ui.booking.main import BookingMainUI
from ui.client.main import ClientMainUI
from gym_manager.core.persistence import ClientRepo, ActivityRepo, InscriptionRepo
from ui.widget_config import config_layout, config_lbl, config_btn


class Controller:
    def __init__(self, client_repo: ClientRepo, activity_manager: ActivityManager, accounting_system: AccountingSystem,
                 booking_system: BookingSystem):
        self.client_repo = client_repo
        self.activity_manager = activity_manager
        self.accounting_system = accounting_system
        self.booking_system = booking_system

    def show_client_main_ui(self):
        self.client_main_ui = ClientMainUI(self.client_repo, self.activity_manager, self.accounting_system)
        self.client_main_ui.setWindowModality(Qt.ApplicationModal)
        self.client_main_ui.show()

    def show_activity_main_ui(self):
        self.activity_main_ui = ActivityMainUI(self.activity_manager)
        self.activity_main_ui.setWindowModality(Qt.ApplicationModal)
        self.activity_main_ui.show()

    def show_accounting_main_ui(self):
        self.accounting_main_ui = AccountingMainUI(self.accounting_system)
        self.accounting_main_ui.setWindowModality(Qt.ApplicationModal)
        self.accounting_main_ui.show()

    def show_booking_main_ui(self):
        self.booking_main_ui = BookingMainUI(self.booking_system)
        self.booking_main_ui.setWindowModality(Qt.ApplicationModal)
        self.booking_main_ui.show()


class MainUI(QMainWindow):
    def __init__(self, client_repo: ClientRepo, activity_manager: ActivityManager, accounting_system: AccountingSystem,
                 booking_system: BookingSystem):
        super().__init__()
        self._setup_ui()
        self.controller = Controller(client_repo, activity_manager, accounting_system, booking_system)
        self._setup_callbacks(self.controller)

    def _setup_ui(self):
        width, height = 800, 600
        self.resize(width, height)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, width, height))
        self.layout = QVBoxLayout(self.widget)
        config_layout(self.layout, left_margin=10, top_margin=10, right_margin=10, bottom_margin=10, spacing=10)

        self.name_lbl = QLabel()
        self.layout.addWidget(self.name_lbl)
        config_lbl(self.name_lbl, "La cascada", font_size=28)

        self.first_row_layout = QHBoxLayout()
        self.layout.addLayout(self.first_row_layout)

        self.client_ui_btn = QPushButton()
        self.first_row_layout.addWidget(self.client_ui_btn)
        config_btn(self.client_ui_btn, "Cli", width=80, height=80)

        self.activity_ui_btn = QPushButton()
        self.first_row_layout.addWidget(self.activity_ui_btn)
        config_btn(self.activity_ui_btn, "Act", width=80, height=80)

        self.second_row_layout = QHBoxLayout()
        self.layout.addLayout(self.second_row_layout)

        self.booking_ui_btn = QPushButton()
        self.second_row_layout.addWidget(self.booking_ui_btn)
        config_btn(self.booking_ui_btn, "Turn", width=80, height=80)

        self.accounting_ui_btn = QPushButton()
        self.second_row_layout.addWidget(self.accounting_ui_btn)
        config_btn(self.accounting_ui_btn, "Cont", width=80, height=80)

    def _setup_callbacks(self, controller: Controller):
        self.client_ui_btn.clicked.connect(controller.show_client_main_ui)
        self.activity_ui_btn.clicked.connect(controller.show_activity_main_ui)
        self.accounting_ui_btn.clicked.connect(controller.show_accounting_main_ui)
        self.booking_ui_btn.clicked.connect(controller.show_booking_main_ui)
