import itertools
from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QLabel, \
    QComboBox, QPushButton

from gym_manager.core.base import Client, Activity
from gym_manager.core.system import ActivityManager
from ui.widget_config import config_lbl, config_combobox, fill_combobox, config_layout, config_btn
from ui.widgets import Dialog


class Controller:

    def __init__(
            self, activity_manager: ActivityManager, client: Client, combobox: QComboBox
    ) -> None:
        self.activity_manager = activity_manager
        self.client = client

        self.combobox = combobox
        it = itertools.filterfalse(lambda activity: self.client.is_signed_up(activity), activity_manager.activities())
        fill_combobox(combobox, it, lambda activity: str(activity.name))

    def sign_on(self):
        if self.combobox.count() == 0:
            Dialog.info("Error", "No hay actividades disponibles.")
        else:
            activity: Activity = self.combobox.currentData(Qt.UserRole)
            self.activity_manager.sign_on(date.today(), self.client, activity)
            Dialog.info("Éxito", f"El cliente '{self.client.name}' fue registrado correctamente en la actividad "
                                 f"'{activity.name}'.")
            self.combobox.window().close()


class SignOn(QDialog):
    def __init__(self, activity_manager: ActivityManager, client: Client) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(activity_manager, client, self.activity_combobox)
        self.ok_btn.clicked.connect(self.controller.sign_on)
        self.cancel_btn.clicked.connect(self.reject)

    def _setup_ui(self):
        self.resize(400, 300)

        self.layout = QVBoxLayout(self)

        # Activity.
        self.activity_layout = QHBoxLayout()
        self.layout.addLayout(self.activity_layout)

        self.name_lbl = QLabel()
        self.activity_layout.addWidget(self.name_lbl)
        config_lbl(self.name_lbl, "Actividad", font_size=16, width=120)

        self.activity_combobox = QComboBox()
        self.activity_layout.addWidget(self.activity_combobox)
        config_combobox(self.activity_combobox, font_size=16)

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)
        config_layout(self.buttons_layout, alignment=Qt.AlignRight, right_margin=5)

        self.ok_btn = QPushButton()
        self.buttons_layout.addWidget(self.ok_btn)
        config_btn(self.ok_btn, "Ok", width=100)

        self.cancel_btn = QPushButton()
        self.buttons_layout.addWidget(self.cancel_btn)
        config_btn(self.cancel_btn, "Cancelar", width=100)
