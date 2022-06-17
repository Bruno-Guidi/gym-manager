from datetime import datetime, date

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox

from gym_manager.core import attr_constraints
from gym_manager.core.base import String, Number, Date, Client
from gym_manager.core.persistence import ClientRepo
from ui.widget_config import config_layout, config_lbl, config_line
from ui.widgets import Field


class Controller:

    def __init__(
            self, name_field: Field, dni_field: Field, admission_field: Field, tel_field: Field, dir_field: Field,
            client_repo: ClientRepo
    ) -> None:
        self.name_field = name_field
        self.dni_field = dni_field
        self.admission_field = admission_field
        self.tel_field = tel_field
        self.dir_field = dir_field

        self.client: Client | None = None
        self.client_repo = client_repo

    # noinspection PyTypeChecker
    def create_client(self):
        valid = all([self.name_field.valid_value(), self.dni_field.valid_value(), self.admission_field.valid_value(),
                     self.tel_field.valid_value(), self.dir_field.valid_value()])
        if not valid:
            QMessageBox.about(self.name_field.window(), "Error", "Hay datos que no son válidos.")
        elif self.client_repo.contains(self.dni_field.value()):
            QMessageBox.about(self.name_field.window(), "Error",
                              f"Ya existe un cliente con el dni '{self.dni_field.value().as_primitive()}'.")
        else:
            self.client = Client(self.dni_field.value(), self.name_field.value(), self.admission_field.value(),
                                 self.tel_field.value(), self.dir_field.value())
            self.client_repo.add(self.client)
            QMessageBox.about(self.name_field.window(), "Éxito",
                              f"El cliente '{self.name_field.value()}' fue creado correctamente.")
            self.dni_field.window().close()


class CreateUI(QDialog):
    def __init__(self, client_repo: ClientRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(
            self.name_field, self.dni_field, self.admission_field, self.tel_field, self.dir_field, client_repo
        )

        self.button_box.accepted.connect(self.controller.create_client)
        self.button_box.rejected.connect(self.reject)

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

        self.name_field = Field(validatable=String, optional=False, max_len=attr_constraints.CLIENT_NAME_CHARS)
        self.name_layout.addWidget(self.name_field)
        config_line(self.name_field, place_holder="Nombre", font_size=16)

        # DNI.
        self.dni_layout = QHBoxLayout()
        self.form_layout.addLayout(self.dni_layout)
        config_layout(self.dni_layout, alignment=Qt.AlignLeft)

        self.dni_lbl = QLabel()
        self.dni_layout.addWidget(self.dni_lbl)
        config_lbl(self.dni_lbl, "DNI", font_size=16, width=120)

        self.dni_field = Field(validatable=Number, min_value=attr_constraints.CLIENT_MIN_DNI,
                               max_value=attr_constraints.CLIENT_MAX_DNI)
        self.dni_layout.addWidget(self.dni_field)
        config_line(self.dni_field, place_holder="DNI", font_size=16)

        # Admission.
        self.admission_layout = QHBoxLayout()
        self.form_layout.addLayout(self.admission_layout)
        config_layout(self.admission_layout, alignment=Qt.AlignLeft)

        self.admission_lbl = QLabel()
        self.admission_layout.addWidget(self.admission_lbl)
        config_lbl(self.admission_lbl, "Ingreso", font_size=16, width=120)

        self.admission_field = Field(Date, format=attr_constraints.DATE_FORMATS)
        self.admission_layout.addWidget(self.admission_field)
        config_line(self.admission_field, text=datetime.strftime(date.today(), attr_constraints.DATE_FORMATS[0]),
                    place_holder="DD-MM-AAAA", font_size=16, height=30)

        # Telephone.
        self.tel_layout = QHBoxLayout()
        self.form_layout.addLayout(self.tel_layout)
        config_layout(self.tel_layout, alignment=Qt.AlignLeft)

        self.tel_lbl = QLabel(self)
        self.tel_layout.addWidget(self.tel_lbl)
        config_lbl(self.tel_lbl, "Teléfono", font_size=16, width=120)

        self.tel_field = Field(validatable=String, optional=attr_constraints.CLIENT_TEL_OPTIONAL,
                               max_len=attr_constraints.CLIENT_TEL_CHARS)
        self.tel_layout.addWidget(self.tel_field)
        config_line(self.tel_field, place_holder="Teléfono", font_size=16)

        # Direction.
        self.dir_layout = QHBoxLayout()
        self.form_layout.addLayout(self.dir_layout)
        config_layout(self.dir_layout, alignment=Qt.AlignLeft)

        self.dir_lbl = QLabel(self)
        self.dir_layout.addWidget(self.dir_lbl)
        config_lbl(self.dir_lbl, "Dirección", font_size=16, width=120)

        self.dir_field = Field(validatable=String, optional=attr_constraints.CLIENT_DIR_OPTIONAL,
                               max_len=attr_constraints.CLIENT_DIR_CHARS)
        self.dir_layout.addWidget(self.dir_field)
        config_line(self.dir_field, place_holder="Dirección", font_size=16)

        # Buttons.
        self.button_box = QDialogButtonBox(self)
        self.layout.addWidget(self.button_box)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
