from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton

# from ui.client.main import ClientMainUI
from gym_manager.core.persistence import ClientRepo
from ui.widget_config import config_layout, config_lbl, config_btn


class Controller:
    def __init__(self, client_repo: ClientRepo):
        self.client_repo = client_repo

    def show_main_client_ui(self):
        pass
        # self.main_client_ui = ClientMainUI(self.client_repo)
        # self.main_client_ui.setWindowModality(Qt.ApplicationModal)
        # self.main_client_ui.show()


class MainUI(QMainWindow):
    def __init__(self, client_repo: ClientRepo):
        super().__init__()
        self._setup_ui()
        self.controller = Controller(client_repo)
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
        self.client_ui_btn.clicked.connect(controller.show_main_client_ui)
