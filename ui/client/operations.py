from __future__ import annotations

import itertools
from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QLabel, QDateEdit, QPushButton, QComboBox, QGridLayout,
    QSpacerItem, QSizePolicy)

from gym_manager.core import constants as consts
from gym_manager.core.base import String, Number, Client, Activity, Subscription
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
        self.create_ui.confirm_btn.clicked.connect(self.create_client)
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
                                 self.create_ui.date_edit.date().toPyDate(),
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
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self, max_len=consts.CLIENT_NAME_CHARS)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre")

        # DNI.
        self.dni_lbl = QLabel(self)
        self.form_layout.addWidget(self.dni_lbl, 1, 0)
        config_lbl(self.dni_lbl, "DNI*")

        self.dni_field = Field(Number, parent=self, min_value=consts.CLIENT_MIN_DNI, max_value=consts.CLIENT_MAX_DNI)
        self.form_layout.addWidget(self.dni_field, 1, 1)
        config_line(self.dni_field, place_holder="XXXXXXXX")

        # Admission.
        self.date_lbl = QLabel(self)
        self.form_layout.addWidget(self.date_lbl, 2, 0)
        config_lbl(self.date_lbl, "Ingreso",)

        self.date_edit = QDateEdit(self)
        self.form_layout.addWidget(self.date_edit, 2, 1)
        config_date_edit(self.date_edit, date.today(), calendar=True)

        # Telephone.
        self.tel_lbl = QLabel(self)
        self.form_layout.addWidget(self.tel_lbl, 3, 0)
        config_lbl(self.tel_lbl, "Teléfono")

        self.tel_field = Field(String, parent=self, optional=consts.CLIENT_TEL_OPTIONAL,
                               max_len=consts.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel_field, 3, 1)
        config_line(self.tel_field, place_holder="Teléfono")

        # Direction.
        self.dir_lbl = QLabel(self)
        self.form_layout.addWidget(self.dir_lbl, 4, 0)
        config_lbl(self.dir_lbl, "Dirección")

        self.dir_field = Field(String, parent=self, optional=consts.CLIENT_DIR_OPTIONAL,
                               max_len=consts.CLIENT_DIR_CHARS)
        self.form_layout.addWidget(self.dir_field, 4, 1)
        config_line(self.dir_field, place_holder="Dirección")

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
        self.setMaximumSize(self.minimumWidth(), self.minimumHeight())


class SubscribeController:

    def __init__(self, subscribe_ui: SubscribeUI, activity_manager: ActivityManager, client: Client) -> None:
        self.activity_manager = activity_manager
        self.client = client
        self.subscription: Subscription | None = None

        self.subscribe_ui = subscribe_ui

        it = itertools.filterfalse(lambda activity: self.client.is_subscribed(activity) or activity.charge_once,
                                   activity_manager.activities())
        fill_combobox(self.subscribe_ui.activity_combobox, it, lambda activity: str(activity.name))

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.subscribe_ui.confirm_btn.clicked.connect(self.subscribe)
        # noinspection PyUnresolvedReferences
        self.subscribe_ui.cancel_btn.clicked.connect(self.subscribe_ui.reject)

    def subscribe(self):
        if self.subscribe_ui.activity_combobox.count() == 0:
            Dialog.info("Error", "No hay actividades disponibles.")
        else:
            sub_date = self.subscribe_ui.when_date_edit.date().toPyDate()
            if self.client.admission > sub_date:
                Dialog.info("Error", "La fecha de inscripción a la actividad no puede ser previa a la fecha de ingreso"
                                     " al sistema del cliente.")
            else:
                activity: Activity = self.subscribe_ui.activity_combobox.currentData(Qt.UserRole)
                self.subscription = self.activity_manager.subscribe(self.subscribe_ui.when_date_edit.date().toPyDate(),
                                                                    self.client, activity)
                Dialog.info("Éxito", f"El cliente '{self.client.name}' fue inscripto correctamente en la actividad "
                                     f"'{activity.name}'.")
                self.subscribe_ui.activity_combobox.window().close()


class SubscribeUI(QDialog):
    def __init__(self, activity_manager: ActivityManager, client: Client) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = SubscribeController(self, activity_manager, client)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)

        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)

        # When.
        self.when_lbl = QLabel(self)
        self.form_layout.addWidget(self.when_lbl, 1, 0)
        config_lbl(self.when_lbl, "Fecha")

        self.when_date_edit = QDateEdit(self)
        self.form_layout.addWidget(self.when_date_edit, 1, 1)
        config_date_edit(self.when_date_edit, date.today(), calendar=False)

        # Activity. The widgets related to the activity are added after the ones related to the date, so the combobox
        # width can be set with the date edit width.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Actividad")

        self.activity_combobox = QComboBox(self)
        self.form_layout.addWidget(self.activity_combobox, 0, 1)
        config_combobox(self.activity_combobox, fixed_width=self.when_date_edit.width())

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
        self.setMaximumSize(self.minimumWidth(), self.minimumHeight())
