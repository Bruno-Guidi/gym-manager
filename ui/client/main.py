from __future__ import annotations

from datetime import date

from PyQt5.QtCore import QRect, Qt, QSize
from PyQt5.QtWidgets import QMainWindow, QWidget, QListWidget, QHBoxLayout, QLabel, QPushButton, \
    QListWidgetItem, QVBoxLayout, QTableWidget, QComboBox, QLineEdit, QSpacerItem, QSizePolicy, QMessageBox, \
    QTableWidgetItem

from gym_manager.core import attr_constraints
from gym_manager.core.accounting import PaymentSystem
from gym_manager.core.activity_manager import ActivityManager
from gym_manager.core.base import Client, String, Number, Date, Inscription
from gym_manager.core.persistence import ClientRepo
from ui.accounting.charge import ChargeUI
from ui.client.create import CreateUI
from ui.client.sign_on import SignOn
from ui.widget_config import config_lbl, config_line, config_btn, config_layout, config_combobox, config_table
from ui.widgets import Field


class ClientRow(QWidget):
    def __init__(
            self, client: Client, client_repo: ClientRepo, activity_manager: ActivityManager,
            payment_system: PaymentSystem, item: QListWidgetItem, main_ui_controller: Controller,
            name_width: int, dni_width: int, admission_width: int, tel_width: int, dir_width: int, height: int
    ):
        super().__init__()
        self.client = client
        self.inscriptions: dict[int, Inscription] = {}
        self.client_repo = client_repo
        self.activity_manager = activity_manager
        self.payment_system = payment_system
        self.item = item
        self.main_ui_controller = main_ui_controller

        self._setup_ui(height, name_width, dni_width, admission_width, tel_width, dir_width)

        # Because the widgets are yet to be hided, the hint has the 'extended' height.
        self.current_height, self.previous_height = height, None
        self.item.setSizeHint(QSize(self.widget.width(), self.current_height))

        def _setup_hidden_ui():
            # Name.
            self.name_lbl = QLabel(self.widget)
            self.name_layout.addWidget(self.name_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.name_lbl, "Nombre", font_size=12, width=name_width)

            self.name_field = Field(String, self.widget, optional=False, max_len=attr_constraints.CLIENT_NAME_CHARS)
            self.name_layout.addWidget(self.name_field)
            config_line(self.name_field, str(client.name), width=name_width)

            # DNI.
            self.dni_lbl = QLabel(self.widget)
            self.dni_layout.addWidget(self.dni_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.dni_lbl, "DNI", font_size=12, width=dni_width)

            self.dni_field = Field(Number, self.widget, min_value=attr_constraints.CLIENT_MIN_DNI,
                                   max_value=attr_constraints.CLIENT_MAX_DNI)
            self.dni_layout.addWidget(self.dni_field)
            config_line(self.dni_field, str(client.dni), width=dni_width, enabled=False)

            # Admission.
            self.admission_lbl = QLabel(self.widget)
            self.admission_layout.addWidget(self.admission_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.admission_lbl, "Ingreso", font_size=12, width=admission_width)

            self.admission_field = Field(Date, self.widget, format=attr_constraints.DATE_FORMATS)
            self.admission_layout.addWidget(self.admission_field)
            config_line(self.admission_field, str(client.admission), width=admission_width)

            # Telephone.
            self.tel_lbl = QLabel(self.widget)
            self.tel_layout.addWidget(self.tel_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.tel_lbl, "Teléfono", font_size=12, width=tel_width)

            self.tel_field = Field(String, self.widget, optional=attr_constraints.CLIENT_TEL_OPTIONAL,
                                   max_len=attr_constraints.CLIENT_TEL_CHARS)
            self.tel_layout.addWidget(self.tel_field)
            config_line(self.tel_field, str(client.telephone), width=tel_width)

            # Direction.
            self.dir_lbl = QLabel(self.widget)
            self.dir_layout.addWidget(self.dir_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.dir_lbl, "Dirección", font_size=12, width=dir_width)

            self.dir_field = Field(String, self.widget, optional=attr_constraints.CLIENT_DIR_OPTIONAL,
                                   max_len=attr_constraints.CLIENT_DIR_CHARS)
            self.dir_layout.addWidget(self.dir_field)
            config_line(self.dir_field, str(client.direction), width=dir_width)

            # Save and delete buttons.
            self.save_btn = QPushButton(self.widget)
            self.top_buttons_layout.addWidget(self.save_btn)
            config_btn(self.save_btn, text="Guardar", width=110)

            self.remove_btn = QPushButton(self.widget)
            self.top_buttons_layout.addWidget(self.remove_btn)
            config_btn(self.remove_btn, text="Eliminar", width=110)

            # Activities.
            self.activities_lbl = QLabel(self.widget)
            self.row_layout.addWidget(self.activities_lbl)
            config_lbl(self.activities_lbl, "Actividades", font_size=12)

            # Layout that contains activities and buttons to add, remove and charge registrations, and to see payments.
            self.bottom_layout = QHBoxLayout()
            self.row_layout.addLayout(self.bottom_layout)
            config_layout(self.bottom_layout, alignment=Qt.AlignCenter)

            self.inscription_table = QTableWidget(self.widget)
            self.bottom_layout.addWidget(self.inscription_table)
            config_table(self.inscription_table,
                         columns={"Nombre": 280, "Último\npago": 100, "Código\npago": 146, "Vencida": 90},
                         allow_resizing=True)  # ToDo. Set min width.

            # Buttons.
            self.bottom_buttons_layout = QVBoxLayout()
            self.bottom_layout.addLayout(self.bottom_buttons_layout)
            config_layout(self.bottom_buttons_layout, alignment=Qt.AlignTop)

            self.sign_on_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.sign_on_btn)
            config_btn(self.sign_on_btn, text="Inscribir en\nactividad", width=110)

            self.unsubscribe_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.unsubscribe_btn)
            config_btn(self.unsubscribe_btn, text="Dar de baja", width=110)

            self.charge_activity_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.charge_activity_btn)
            config_btn(self.charge_activity_btn, text="Cobrar\nactividad", width=110)

            self.payments_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.payments_btn)
            config_btn(self.payments_btn, text="Ver pagos", width=110)

        self._setup_hidden_ui = _setup_hidden_ui
        self.hidden_ui_loaded = False  # Flag used to load the hidden ui only when it is opened for the first time.

        self.detail_btn.clicked.connect(self.hide_detail)
        self.is_hidden = False

    def _setup_ui(
            self, height: int, name_width: int, dni_width: int, admission_width: int, tel_width: int, dir_width: int
    ):
        self.widget = QWidget(self)

        self.row_layout = QVBoxLayout(self.widget)

        self.top_layout = QHBoxLayout()
        self.row_layout.addLayout(self.top_layout)
        config_layout(self.top_layout, alignment=Qt.AlignCenter)

        # Name layout.
        self.name_layout = QVBoxLayout()
        self.top_layout.addLayout(self.name_layout)

        self.name_summary = QLabel(self.widget)
        self.name_layout.addWidget(self.name_summary, alignment=Qt.AlignTop)
        config_lbl(self.name_summary, str(self.client.name), width=name_width, height=30, alignment=Qt.AlignVCenter)

        self.name_lbl: QLabel | None = None
        self.name_field: Field | None = None

        # DNI layout.
        self.dni_layout = QVBoxLayout()
        self.top_layout.addLayout(self.dni_layout)

        self.dni_summary = QLabel(self.widget)
        self.dni_layout.addWidget(self.dni_summary, alignment=Qt.AlignTop)
        config_lbl(self.dni_summary, str(self.client.dni), width=dni_width, height=30, alignment=Qt.AlignVCenter)

        self.dni_lbl: QLabel | None = None
        self.dni_field: Field | None = None

        # Admission layout.
        self.admission_layout = QVBoxLayout()
        self.top_layout.addLayout(self.admission_layout)

        self.admission_summary = QLabel(self.widget)
        self.admission_layout.addWidget(self.admission_summary, alignment=Qt.AlignTop)
        config_lbl(self.admission_summary, str(self.client.admission), width=admission_width, height=30,
                   alignment=Qt.AlignVCenter)

        self.admission_lbl: QLabel | None = None
        self.admission_field: Field | None = None

        # Telephone layout.
        self.tel_layout = QVBoxLayout()
        self.top_layout.addLayout(self.tel_layout)

        self.tel_summary = QLabel(self.widget)
        self.tel_layout.addWidget(self.tel_summary, alignment=Qt.AlignTop)
        config_lbl(self.tel_summary, str(self.client.telephone), width=tel_width, height=30, alignment=Qt.AlignVCenter)

        self.tel_lbl: QLabel | None = None
        self.tel_field: Field | None = None

        # Direction layout.
        self.dir_layout = QVBoxLayout()
        self.top_layout.addLayout(self.dir_layout)

        self.dir_summary = QLabel(self.widget)
        self.dir_layout.addWidget(self.dir_summary, alignment=Qt.AlignTop)
        config_lbl(self.dir_summary, str(self.client.direction), width=dir_width, height=30, alignment=Qt.AlignVCenter)

        self.dir_lbl: QLabel | None = None
        self.dir_field: Field | None = None

        # Detail button.
        self.top_buttons_layout = QVBoxLayout()
        self.top_layout.addLayout(self.top_buttons_layout)

        self.detail_btn = QPushButton(self.widget)
        self.top_buttons_layout.addWidget(self.detail_btn, alignment=Qt.AlignTop)
        config_btn(self.detail_btn, text="Detalle", width=110)

        self.save_btn: QPushButton | None = None
        self.remove_btn: QPushButton | None = None

        # Activities.
        self.activities_lbl: QLabel | None = None

        # Layout that contains activities and buttons to add, remove and charge registrations, and to see payments.
        self.bottom_layout: QHBoxLayout | None = None

        self.inscription_table: QTableWidget | None = None

        # Buttons.
        self.bottom_buttons_layout: QVBoxLayout | None = None
        self.sign_on_btn: QPushButton | None = None
        self.unsubscribe_btn: QPushButton | None = None
        self.charge_activity_btn: QPushButton | None = None
        self.payments_btn: QPushButton | None = None

        self.widget.setGeometry(QRect(0, 0, self.widget.sizeHint().width(), height))

    def _setup_callbacks(self):
        self.save_btn.clicked.connect(self.save_changes)
        self.remove_btn.clicked.connect(self.remove)
        self.sign_on_btn.clicked.connect(self.sign_on)
        self.unsubscribe_btn.clicked.connect(self.unsubscribe)
        self.charge_activity_btn.clicked.connect(self.charge)

    def _set_hidden(self, hidden: bool):
        # Hides widgets.
        self.name_lbl.setHidden(hidden)
        self.name_field.setHidden(hidden)
        self.dni_lbl.setHidden(hidden)
        self.dni_field.setHidden(hidden)
        self.admission_lbl.setHidden(hidden)
        self.admission_field.setHidden(hidden)
        self.tel_lbl.setHidden(hidden)
        self.tel_field.setHidden(hidden)
        self.dir_lbl.setHidden(hidden)
        self.dir_field.setHidden(hidden)

        self.activities_lbl.setHidden(hidden)
        self.inscription_table.setHidden(hidden)

        self.save_btn.setHidden(hidden)
        self.remove_btn.setHidden(hidden)
        self.sign_on_btn.setHidden(hidden)
        self.unsubscribe_btn.setHidden(hidden)
        self.charge_activity_btn.setHidden(hidden)
        self.payments_btn.setHidden(hidden)

        # Updates the height of the widget.
        self.previous_height, self.current_height = self.current_height, self.previous_height

        new_width = self.widget.width()
        self.item.setSizeHint(QSize(new_width, self.current_height))
        self.resize(new_width, self.current_height)
        self.widget.resize(new_width, self.current_height)

        # Inverts the state of the widget.
        self.is_hidden = not hidden

    def hide_detail(self):
        # Creates the hidden widgets in case it is the first time the detail button is clicked.
        if not self.hidden_ui_loaded:
            self._setup_hidden_ui()
            self._setup_callbacks()
            self.hidden_ui_loaded, self.previous_height = True, 350
            self.load_inscriptions()

        # Hides previously opened detail.
        if self.main_ui_controller.opened_now is None:
            self.main_ui_controller.opened_now = self
        elif self.main_ui_controller.opened_now.client != self.client:
            self.main_ui_controller.opened_now._set_hidden(True)
            self.main_ui_controller.opened_now = self
        else:
            self.main_ui_controller.opened_now = None

        # Hide or show the widgets.
        self.item.listWidget().setCurrentItem(self.item)
        self._set_hidden(self.is_hidden)

    def save_changes(self):
        valid = all([self.name_field.valid_value(), self.dni_field.valid_value(), self.admission_field.valid_value(),
                     self.tel_field.valid_value(), self.dir_field.valid_value()])
        if not valid:
            QMessageBox.about(self.name_field.window(), "Error", "Hay datos que no son válidos.")
        else:
            # Updates client object.
            self.client.name = self.name_field.value()
            self.client.admission = self.admission_field.value()
            self.client.telephone = self.tel_field.value()
            self.client.direction = self.dir_field.value()

            self.client_repo.update(self.client)

            # Updates ui.
            self.name_summary.setText(str(self.client.name))
            self.admission_summary.setText(str(self.client.admission))
            self.tel_summary.setText(self.client.telephone.as_primitive())
            self.dir_summary.setText(self.client.direction.as_primitive())

            QMessageBox.about(self.name_field.window(), "Éxito",
                              f"El cliente '{self.name_field.value()}' fue actualizado correctamente.")

    def remove(self):
        delete = QMessageBox.question(self.name_field.window(), "Confirmar",
                                      f"¿Desea eliminar el cliente {self.client.name}?")

        if delete:
            self.main_ui_controller.opened_now = None
            self.client_repo.remove(self.client)
            self.item.listWidget().takeItem(self.item.listWidget().currentRow())

            # ToDo. Move the cache to ActivityManager.
            clients = [client for client in self.client_repo.all(cache=None, page_number=2, items_per_page=1)]
            if len(clients) > 0:
                self.main_ui_controller._add_client(clients[0])

            QMessageBox.about(self.name_field.window(), "Éxito",
                              f"El cliente '{self.name_field.value()}' fue eliminado correctamente.")

    def sign_on(self):
        self.sign_on_ui = SignOn(self.activity_manager, self.client)
        self.sign_on_ui.exec_()
        self.load_inscriptions()  # ToDo. Load only the new inscription.

    def unsubscribe(self):
        if self.inscription_table.currentRow() == -1:
            QMessageBox.about(self.name_field.window(), "Error", "Seleccione una actividad")
        else:
            inscription = self.inscriptions[self.inscription_table.currentRow()]
            unsubscribe = QMessageBox.question(self.name_field.window(), "Confirmar",
                                               f"¿Desea cancelar la inscripción del cliente {self.client.name} en la "
                                               f"actividad {inscription.activity.name}?")
            if unsubscribe:
                self.activity_manager.unsubscribe(inscription)
                self.inscription_table.removeRow(self.inscription_table.currentRow())

    def charge(self):
        activity = self.inscriptions[self.inscription_table.currentRow()].activity
        descr = String(f"Cobro por actividad {activity.name}", optional=False, max_len=attr_constraints.DESCRIPTION_CHARS)
        self.charge_ui = ChargeUI(self.payment_system, self.client, activity, descr, fixed_amount=True, fixed_descr=True)
        self.charge_ui.exec_()

    # noinspection PyUnresolvedReferences
    def load_inscriptions(self):
        self.inscription_table.setRowCount(self.client.n_inscriptions())

        for row, inscription in enumerate(self.client.inscriptions()):
            self.inscriptions[row] = inscription
            self.inscription_table.setItem(row, 0, QTableWidgetItem(str(inscription.activity.name)))

            when = "Sin pagar" if inscription.payment is None else str(inscription.payment.when)
            self.inscription_table.setItem(row, 1, QTableWidgetItem(when))

            payment_id = "-" if inscription.payment is None else str(inscription.payment.id)
            self.inscription_table.setItem(row, 2, QTableWidgetItem(payment_id))

            expired = "Si" if inscription.pay_day_passed(date.today()) else "No"
            self.inscription_table.setItem(row, 3, QTableWidgetItem(expired))


class Controller:
    def __init__(
            self, client_repo: ClientRepo, activity_manager: ActivityManager, payment_system: PaymentSystem,
            client_list: QListWidget, name_width: int, dni_width: int, admission_width: int, tel_width: int, dir_width: int
    ):
        self.client_repo = client_repo
        self.activity_manager = activity_manager
        self.payment_system = payment_system
        self.current_page, self.items_per_page = 1, 10
        self.opened_now: ClientRow | None = None

        self.client_list = client_list
        self.name_width = name_width
        self.dni_width = dni_width
        self.admission_width = admission_width
        self.tel_width = tel_width
        self.dir_width = dir_width

        self.load_clients()

    def _add_client(self, client: Client, set_to_current: bool = False, check_limit: bool = False):
        if check_limit and len(self.client_list) == self.items_per_page:
            self.client_list.takeItem(len(self.client_list) - 1)

        item = QListWidgetItem(self.client_list)
        self.client_list.addItem(item)
        client_row = ClientRow(
            client, self.client_repo, self.activity_manager, self.payment_system, item, self,
            self.name_width, self.dni_width, self.admission_width, self.tel_width, self.dir_width, height=50)
        self.client_list.setItemWidget(item, client_row)

        if set_to_current:
            self.client_list.setCurrentItem(item)

    def load_clients(self):
        self.client_list.clear()

        activity_cache = {activity.id: activity for activity in self.activity_manager.activities()}
        for client in self.client_repo.all(activity_cache, page_number=self.current_page,
                                           items_per_page=self.items_per_page):
            self._add_client(client)

    def add_client(self):
        self.add_ui = CreateUI(self.client_repo)
        self.add_ui.exec_()
        if self.add_ui.controller.client is not None:
            self._add_client(self.add_ui.controller.client, set_to_current=True, check_limit=True)


class ClientMainUI(QMainWindow):

    def __init__(
            self, client_repo: ClientRepo, activity_manager: ActivityManager, payment_system: PaymentSystem,
    ) -> None:
        super().__init__(parent=None)
        name_width, dni_width, admission_width, tel_width, dir_width = 175, 90, 100, 110, 140
        self._setup_ui(name_width, dni_width, admission_width, tel_width, dir_width)
        self.controller = Controller(client_repo, activity_manager, payment_system, self.client_list,
                                     name_width, dni_width, admission_width, tel_width, dir_width)

        self.create_client_btn.clicked.connect(self.controller.add_client)

    def _setup_ui(self, name_width: int, dni_width: int, admission_width: int, tel_width: int, dir_width: int):
        self.resize(800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, 800, 600))

        self.main_layout = QVBoxLayout(self.widget)

        # Utilities.
        self.utils_layout = QHBoxLayout()
        self.main_layout.addLayout(self.utils_layout)
        config_layout(self.utils_layout, spacing=0, left_margin=40, top_margin=15, right_margin=80)

        self.filter_combobox = QComboBox(self.widget)
        self.utils_layout.addWidget(self.filter_combobox)
        config_combobox(self.filter_combobox, font_size=16)

        self.search_box = QLineEdit(self.widget)
        self.utils_layout.addWidget(self.search_box)
        config_line(self.search_box, place_holder="Búsqueda", font_size=16)

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "Busq", font_size=16)

        self.utils_layout.addItem(QSpacerItem(80, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.create_client_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.create_client_btn)
        config_btn(self.create_client_btn, "Nuevo cliente", font_size=16)

        self.main_layout.addItem(QSpacerItem(80, 15, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Header.
        self.header_layout = QHBoxLayout()
        self.main_layout.addLayout(self.header_layout)
        config_layout(self.header_layout, alignment=Qt.AlignLeft, left_margin=11, spacing=0)

        self.name_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.name_lbl)
        config_lbl(self.name_lbl, "Nombre", width=name_width + 6)  # 6 is the spacing.

        self.dni_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.dni_lbl)
        config_lbl(self.dni_lbl, "DNI", width=dni_width + 6)  # 6 is the spacing.

        self.admission_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.admission_lbl)
        config_lbl(self.admission_lbl, "Ingreso", width=admission_width + 6)  # 6 is the spacing.

        self.tel_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.tel_lbl)
        config_lbl(self.tel_lbl, "Teléfono", width=tel_width + 6)  # 6 is the spacing.

        self.dir_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.dir_lbl)
        config_lbl(self.dir_lbl, "Dirección", width=dir_width + 6)  # 6 is the spacing.

        # Clients.
        self.client_list = QListWidget(self.widget)
        self.main_layout.addWidget(self.client_list)

        # Index.
        self.index_layout = QHBoxLayout()
        self.main_layout.addLayout(self.index_layout)
        config_layout(self.index_layout, left_margin=100, right_margin=100)

        self.prev_btn = QPushButton(self.widget)
        self.index_layout.addWidget(self.prev_btn)
        config_btn(self.prev_btn, "<", font_size=18, width=30)

        self.index_lbl = QLabel(self.widget)
        self.index_layout.addWidget(self.index_lbl)
        config_lbl(self.index_lbl, "#", font_size=18)

        self.next_btn = QPushButton(self.widget)
        self.index_layout.addWidget(self.next_btn)
        config_btn(self.next_btn, ">", font_size=18, width=30)
