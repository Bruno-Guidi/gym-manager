from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QVBoxLayout, QLabel, \
    QCheckBox, QTextEdit, QPushButton

from gym_manager.core import constants as consts
from gym_manager.core.base import String, Currency, Activity
from gym_manager.core.system import ActivityManager
from ui.widget_config import config_layout, config_lbl, config_line, config_btn
from ui.widgets import Field, valid_text_value, Dialog


class Controller:

    def __init__(
            self, name_field: Field, price_field: Field, pay_once_checkbox: QCheckBox, description_text: QTextEdit,
            activity_manager: ActivityManager
    ) -> None:
        self.name_field = name_field
        self.price_field = price_field
        self.pay_once_checkbox = pay_once_checkbox
        self.description_text = description_text

        self.activity: Activity | None = None
        self.activity_manager = activity_manager

    # noinspection PyTypeChecker
    def create_activity(self):
        valid_descr, descr = valid_text_value(self.description_text, optional=True, max_len=consts.ACTIVITY_DESCR_CHARS)
        if all([self.name_field.valid_value(), self.price_field.valid_value(), valid_descr]):
            self.activity = self.activity_manager.create(self.name_field.value(), self.price_field.value(),
                                                         self.pay_once_checkbox.isChecked(), descr)
            Dialog.info("Éxito", f"La categoría '{self.name_field.value()}' fue creada correctamente.")
            self.name_field.window().close()
        else:
            Dialog.info("Error", "Hay datos que no son válidos.")


class CreateUI(QDialog):
    def __init__(self, activity_manager: ActivityManager) -> None:
        super().__init__(parent=None)
        self._setup_ui()
        self.controller = Controller(self.name_field, self.price_field, self.pay_once_checkbox, self.description_text,
                                     activity_manager)

        self.ok_btn.clicked.connect(self.controller.create_activity)
        self.cancel_btn.clicked.connect(self.reject)

    def _setup_ui(self):
        self.resize(400, 300)

        self.layout = QVBoxLayout(self)

        self.form_layout = QVBoxLayout()
        self.layout.addLayout(self.form_layout)

        # Name.
        self.name_layout = QHBoxLayout()
        self.form_layout.addLayout(self.name_layout)
        config_layout(self.name_layout, alignment=Qt.AlignLeft)

        self.name_lbl = QLabel()
        self.name_layout.addWidget(self.name_lbl)
        config_lbl(self.name_lbl, "Nombre", font_size=16, width=120)

        self.name_field = Field(String, max_len=consts.ACTIVITY_NAME_CHARS)
        self.name_layout.addWidget(self.name_field)
        config_line(self.name_field, place_holder="Nombre", font_size=16)

        # Price.
        self.price_layout = QHBoxLayout()
        self.form_layout.addLayout(self.price_layout)
        config_layout(self.price_layout, alignment=Qt.AlignLeft)

        self.price_lbl = QLabel()
        self.price_layout.addWidget(self.price_lbl)
        config_lbl(self.price_lbl, "Precio", font_size=16, width=120)

        self.price_field = Field(Currency, max_currency=consts.MAX_CURRENCY)
        self.price_layout.addWidget(self.price_field)
        config_line(self.price_field, place_holder="Precio", font_size=16)

        # Pay once.
        self.pay_once_layout = QHBoxLayout()
        self.form_layout.addLayout(self.pay_once_layout)
        config_layout(self.pay_once_layout, alignment=Qt.AlignLeft)

        self.pay_once_lbl = QLabel()
        self.pay_once_layout.addWidget(self.pay_once_lbl)
        config_lbl(self.pay_once_lbl, "Pago único", font_size=16, width=120)

        self.pay_once_checkbox = QCheckBox()
        self.pay_once_layout.addWidget(self.pay_once_checkbox)

        # Description.
        self.description_layout = QHBoxLayout()
        self.form_layout.addLayout(self.description_layout)
        config_layout(self.description_layout, alignment=Qt.AlignLeft)

        self.description_lbl = QLabel(self)
        self.description_layout.addWidget(self.description_lbl)
        config_lbl(self.description_lbl, "Descripción", font_size=16, width=120)

        self.description_text = QTextEdit()
        self.description_layout.addWidget(self.description_text)
        config_line(self.description_text, place_holder="Descripción", font_size=16)

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
