import itertools

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QVBoxLayout, QLabel, \
    QComboBox, QMessageBox

from gym_manager.core.activity_manager import ActivityManager
from gym_manager.core.base import Client, Activity
from ui.widget_config import config_lbl, config_combobox, fill_combobox


class Controller:

    def __init__(
            self, activity_manager: ActivityManager, client: Client, combobox: QComboBox
    ) -> None:
        self.activity_manager = activity_manager
        self.client = client

        self.combobox = combobox
        it = itertools.filterfalse(lambda activity: self.client.is_signed_up(activity), activity_manager.all())
        fill_combobox(combobox, it, lambda activity: str(activity.name))

    def sign_on(self):
        activity: Activity = self.combobox.currentData(Qt.UserRole)
        self.activity_manager.sign_on(self.client, activity)
        QMessageBox.about(self.combobox.window(), "Éxito",
                          f"El cliente '{self.client.name}' fue registrado correctamente en la actividad '{activity.name}'.")
        self.combobox.window().close()


class SignOn(QDialog):
    def __init__(self, activity_manager: ActivityManager, client: Client) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(activity_manager, client, self.activity_combobox)
        self._setup_callbacks()

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
        self.button_box = QDialogButtonBox(self)
        self.layout.addWidget(self.button_box)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

    def _setup_callbacks(self):
        self.button_box.accepted.connect(self.controller.sign_on)
        self.button_box.rejected.connect(self.reject)
