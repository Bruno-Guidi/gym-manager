from __future__ import annotations

import itertools
from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QLabel, QDateEdit, QPushButton, QComboBox

from gym_manager.core import constants as consts
from gym_manager.core.base import String, Number, Client, Activity
from gym_manager.core.persistence import ClientRepo
from gym_manager.core.system import ActivityManager
from ui.widget_config import config_layout, config_lbl, config_line, config_date_edit, config_btn, fill_combobox, \
    config_combobox
from ui.widgets import Field, Dialog


class CreateController:

    def __init__(
            self, create_ui: CreateUI, client_repo: ClientRepo
    ) -> None:
        self.create_ui = create_ui

        self.client: Client | None = None
        self.client_repo = client_repo

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.create_ui.ok_btn.clicked.connect(self.create_client)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    # noinspection PyTypeChecker
    def create_client(self):
        valid_fields = all([self.create_ui.name_field.valid_value(), self.create_ui.dni_field.valid_value(),
                            self.create_ui.tel_field.valid_value(), self.create_ui.dir_field.valid_value()])
        if not valid_fields:
            Dialog.info("Error", "Hay datos que no son válidos.")
        elif self.client_repo.is_active(self.create_ui.dni_field.value()):
            Dialog.info("Error", f"Ya existe un cliente activo con el dni '{self.create_ui.dni_field.value().as_primitive()}'.")
        else:
            self.client = Client(self.create_ui.dni_field.value(),
                                 self.create_ui.name_field.value(),
                                 self.create_ui.admission_date_field.date().toPyDate(),
                                 self.create_ui.tel_field.value(),
                                 self.create_ui.dir_field.value(),
                                 is_active=True)
            self.client_repo.add(self.client)
            Dialog.info("Éxito", f"El cliente '{self.create_ui.name_field.value()}' fue creado correctamente.")
            self.create_ui.dni_field.window().close()


class CreateUI(QDialog):
    def __init__(self, client_repo: ClientRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, client_repo)

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

        self.name_field = Field(validatable=String, max_len=consts.CLIENT_NAME_CHARS)
        self.name_layout.addWidget(self.name_field)
        config_line(self.name_field, place_holder="Nombre", font_size=16)

        # DNI.
        self.dni_layout = QHBoxLayout()
        self.form_layout.addLayout(self.dni_layout)
        config_layout(self.dni_layout, alignment=Qt.AlignLeft)

        self.dni_lbl = QLabel()
        self.dni_layout.addWidget(self.dni_lbl)
        config_lbl(self.dni_lbl, "DNI", font_size=16, width=120)

        self.dni_field = Field(Number, min_value=consts.CLIENT_MIN_DNI, max_value=consts.CLIENT_MAX_DNI)
        self.dni_layout.addWidget(self.dni_field)
        config_line(self.dni_field, place_holder="DNI", font_size=16)

        # Admission.
        self.admission_layout = QHBoxLayout()
        self.form_layout.addLayout(self.admission_layout)
        config_layout(self.admission_layout, alignment=Qt.AlignLeft)

        self.admission_lbl = QLabel()
        self.admission_layout.addWidget(self.admission_lbl)
        config_lbl(self.admission_lbl, "Ingreso", font_size=16, width=120)

        self.admission_date_field = QDateEdit()
        self.admission_layout.addWidget(self.admission_date_field)
        config_date_edit(self.admission_date_field, date.today(), font_size=16, height=30)

        # Telephone.
        self.tel_layout = QHBoxLayout()
        self.form_layout.addLayout(self.tel_layout)
        config_layout(self.tel_layout, alignment=Qt.AlignLeft)

        self.tel_lbl = QLabel(self)
        self.tel_layout.addWidget(self.tel_lbl)
        config_lbl(self.tel_lbl, "Teléfono", font_size=16, width=120)

        self.tel_field = Field(validatable=String, optional=consts.CLIENT_TEL_OPTIONAL, max_len=consts.CLIENT_TEL_CHARS)
        self.tel_layout.addWidget(self.tel_field)
        config_line(self.tel_field, place_holder="Teléfono", font_size=16)

        # Direction.
        self.dir_layout = QHBoxLayout()
        self.form_layout.addLayout(self.dir_layout)
        config_layout(self.dir_layout, alignment=Qt.AlignLeft)

        self.dir_lbl = QLabel(self)
        self.dir_layout.addWidget(self.dir_lbl)
        config_lbl(self.dir_lbl, "Dirección", font_size=16, width=120)

        self.dir_field = Field(validatable=String, optional=consts.CLIENT_DIR_OPTIONAL, max_len=consts.CLIENT_DIR_CHARS)
        self.dir_layout.addWidget(self.dir_field)
        config_line(self.dir_field, place_holder="Dirección", font_size=16)

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


class SubscribeController:

    def __init__(self, subscribe_ui: SubscribeUI, activity_manager: ActivityManager, client: Client) -> None:
        self.activity_manager = activity_manager
        self.client = client

        self.subscribe_ui = subscribe_ui

        it = itertools.filterfalse(lambda activity: self.client.is_subscribed(activity), activity_manager.activities())
        fill_combobox(self.subscribe_ui.activity_combobox, it, lambda activity: str(activity.name))

    def subscribe(self):
        if self.subscribe_ui.activity_combobox.count() == 0:
            Dialog.info("Error", "No hay actividades disponibles.")
        else:
            activity: Activity = self.subscribe_ui.activity_combobox.currentData(Qt.UserRole)
            self.activity_manager.subscribe(self.subscribe_ui.when_field.date().toPyDate(), self.client, activity)
            Dialog.info("Éxito", f"El cliente '{self.client.name}' fue registrado correctamente en la actividad "
                                 f"'{activity.name}'.")
            self.subscribe_ui.activity_combobox.window().close()


class SubscribeUI(QDialog):
    def __init__(self, activity_manager: ActivityManager, client: Client) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = SubscribeController(self, activity_manager, client)
        self.ok_btn.clicked.connect(self.controller.subscribe)
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

        # When.
        self.when_layout = QHBoxLayout()
        self.layout.addLayout(self.when_layout)

        self.when_lbl = QLabel()
        self.when_layout.addWidget(self.when_lbl)
        config_lbl(self.when_lbl, "Fecha", font_size=16, width=120)

        self.when_field = QDateEdit()
        self.when_layout.addWidget(self.when_field)
        config_date_edit(self.when_field, date.today(), font_size=16)

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
