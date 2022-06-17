from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import QRect, Qt, QSize
from PyQt5.QtWidgets import QMainWindow, QWidget, QListWidget, QHBoxLayout, QLabel, QPushButton, \
    QListWidgetItem, QVBoxLayout, QTableWidget, QComboBox, QLineEdit, QSpacerItem, QSizePolicy, QMessageBox, \
    QTableWidgetItem

from gym_manager.core import attr_constraints
from gym_manager.core.activity_manager import ActivityManager
from gym_manager.core.base import Client, String, Number, Date
from gym_manager.core.persistence import ClientRepo
from ui.client.create import CreateUI
from ui.client.sign_on import SignOn
from ui.widget_config import config_lbl, config_line, config_btn, config_layout, config_combobox, config_table
from ui.widgets import Field


class ClientRow(QWidget):
    def __init__(
            self, client: Client, client_repo: ClientRepo, activity_manager: ActivityManager,
            item: QListWidgetItem, main_ui_controller: Controller, change_selected_item: Callable[[QListWidgetItem], None],
            total_width: int, height: int,
            name_width: int, dni_width: int, admission_width: int, tel_width: int, dir_width: int
    ):
        super().__init__()
        self.client = client
        self.client_repo = client_repo
        self.activity_manager = activity_manager
        self.item = item
        self.main_ui_controller = main_ui_controller
        self.change_selected_item = change_selected_item

        self._setup_ui(total_width, height, name_width, dni_width, admission_width, tel_width, dir_width)

        # Because the widgets are yet to be hided, the hint has the 'extended' height.
        self.current_height, self.previous_height = height, None
        self.item.setSizeHint(QSize(total_width, self.current_height))

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
            config_btn(self.save_btn, text="Guardar", width=100)

            self.remove_client_btn = QPushButton(self.widget)
            self.top_buttons_layout.addWidget(self.remove_client_btn)
            config_btn(self.remove_client_btn, text="Eliminar", width=100)

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

            self.add_activity_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.add_activity_btn)
            config_btn(self.add_activity_btn, text="Nueva\nactividad", width=100)

            self.remove_activity_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.remove_activity_btn)
            config_btn(self.remove_activity_btn, text="Eliminar\nactividad", width=100)

            self.charge_activity_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.charge_activity_btn)
            config_btn(self.charge_activity_btn, text="Cobrar\nactividad", width=100)

            self.payments_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.payments_btn)
            config_btn(self.payments_btn, text="Ver pagos", width=100)

        self._setup_hidden_ui = _setup_hidden_ui
        self.hidden_ui_loaded = False  # Flag used to load the hidden ui only when it is opened for the first time.

        self.detail_btn.clicked.connect(self.hide_detail)
        self.is_hidden = False

    def _setup_ui(
            self, total_width: int, height: int,
            name_width: int, dni_width: int, admission_width: int, tel_width: int, dir_width: int
    ):
        self.widget = QWidget(self)
        self.widget.setGeometry(QRect(0, 0, total_width, height))

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

        self.name_lbl: Optional[QLabel] = None
        self.name_field: Optional[Field] = None

        # DNI layout.
        self.dni_layout = QVBoxLayout()
        self.top_layout.addLayout(self.dni_layout)

        self.dni_summary = QLabel(self.widget)
        self.dni_layout.addWidget(self.dni_summary, alignment=Qt.AlignTop)
        config_lbl(self.dni_summary, str(self.client.dni), width=dni_width, height=30, alignment=Qt.AlignVCenter)

        self.dni_lbl: Optional[QLabel] = None
        self.dni_field: Optional[Field] = None

        # Admission layout.
        self.admission_layout = QVBoxLayout()
        self.top_layout.addLayout(self.admission_layout)

        self.admission_summary = QLabel(self.widget)
        self.admission_layout.addWidget(self.admission_summary, alignment=Qt.AlignTop)
        config_lbl(self.admission_summary, str(self.client.admission), width=admission_width, height=30, alignment=Qt.AlignVCenter)

        self.admission_lbl: Optional[QLabel] = None
        self.admission_field: Optional[Field] = None

        # Telephone layout.
        self.tel_layout = QVBoxLayout()
        self.top_layout.addLayout(self.tel_layout)

        self.tel_summary = QLabel(self.widget)
        self.tel_layout.addWidget(self.tel_summary, alignment=Qt.AlignTop)
        config_lbl(self.tel_summary, str(self.client.telephone), width=tel_width, height=30, alignment=Qt.AlignVCenter)

        self.tel_lbl: Optional[QLabel] = None
        self.tel_field: Optional[Field] = None

        # Direction layout.
        self.dir_layout = QVBoxLayout()
        self.top_layout.addLayout(self.dir_layout)

        self.dir_summary = QLabel(self.widget)
        self.dir_layout.addWidget(self.dir_summary, alignment=Qt.AlignTop)
        config_lbl(self.dir_summary, str(self.client.direction), width=dir_width, height=30, alignment=Qt.AlignVCenter)

        self.dir_lbl: Optional[QLabel] = None
        self.dir_field: Optional[Field] = None

        # Detail button.
        self.top_buttons_layout = QVBoxLayout()
        self.top_layout.addLayout(self.top_buttons_layout)

        self.detail_btn = QPushButton(self.widget)
        self.top_buttons_layout.addWidget(self.detail_btn, alignment=Qt.AlignTop)
        config_btn(self.detail_btn, text="Detalle", width=100)

        self.save_btn: Optional[QPushButton] = None
        self.remove_client_btn: Optional[QPushButton] = None

        # Activities.
        self.activities_lbl: Optional[QLabel] = None

        # Layout that contains activities and buttons to add, remove and charge registrations, and to see payments.
        self.bottom_layout: Optional[QHBoxLayout] = None

        self.inscription_table: Optional[QTableWidget] = None

        # Buttons.
        self.bottom_buttons_layout: Optional[QVBoxLayout] = None
        self.add_activity_btn: Optional[QPushButton] = None
        self.remove_activity_btn: Optional[QPushButton] = None
        self.charge_activity_btn: Optional[QPushButton] = None
        self.payments_btn: Optional[QPushButton] = None

    def _setup_callbacks(self):
        self.save_btn.clicked.connect(self.save_changes)
        self.remove_client_btn.clicked.connect(self.remove)
        self.add_activity_btn.clicked.connect(self.sign_on)

    def set_hidden(self, hidden: bool):
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
        self.remove_client_btn.setHidden(hidden)
        self.add_activity_btn.setHidden(hidden)
        self.remove_activity_btn.setHidden(hidden)
        self.charge_activity_btn.setHidden(hidden)
        self.payments_btn.setHidden(hidden)

        # Updates the height of the widget.
        self.previous_height, self.current_height = self.current_height, self.previous_height

        new_width = self.widget.sizeHint().width() - 3
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

        # Hides previously opened detail.
        if self.main_ui_controller.opened_now is None:
            self.main_ui_controller.opened_now = self
        elif self.main_ui_controller.opened_now.client != self.client:
            self.main_ui_controller.opened_now.set_hidden(True)
            self.main_ui_controller.opened_now = self
        else:
            self.main_ui_controller.opened_now = None

        # Hide or show the widgets.
        self.change_selected_item(self.item)
        self.set_hidden(self.is_hidden)

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
        self.main_ui_controller.opened_now = None
        self.client_repo.remove(self.client)
        self.item.listWidget().takeItem(self.item.listWidget().currentRow())

        QMessageBox.about(self.name_field.window(), "Éxito",
                          f"El cliente '{self.name_field.value()}' fue eliminado correctamente.")

    def sign_on(self):
        self.sign_on_ui = SignOn(self.activity_manager, self.client)
        self.sign_on_ui.exec_()
        self.load_inscriptions()

    def load_inscriptions(self):
        self.inscription_table.setRowCount(self.client.n_inscriptions())

        for row, inscription in enumerate(self.client.inscriptions()):
            self.inscription_table.setItem(row, 0, QTableWidgetItem(str(inscription.activity.name)))
            self.inscription_table.setItem(row, 1, QTableWidgetItem("inscription.payment.when"))
            self.inscription_table.setItem(row, 2, QTableWidgetItem("inscription.payment.id"))


class Controller:
    def __init__(
            self, client_repo: ClientRepo, activity_manager: ActivityManager, client_list: QListWidget
    ):
        self.client_repo = client_repo
        self.activity_manager = activity_manager
        self.current_page = 1
        self.opened_now: Optional[ClientRow] = None

        self.client_list = client_list

        self.load_clients()

    def load_clients(self):
        self.client_list.clear()

        for row, client in enumerate(self.client_repo.all(page_number=self.current_page, items_per_page=15)):
            self.activity_manager.load_inscriptions(client)
            item = QListWidgetItem(self.client_list)
            self.client_list.addItem(item)
            row = ClientRow(
                client, self.client_repo, self.activity_manager,
                item, self, change_selected_item=self.client_list.setCurrentItem,
                total_width=800, height=50, name_width=175, dni_width=90, admission_width=100, tel_width=110, dir_width=140)
            self.client_list.setItemWidget(item, row)

    def add_client(self):
        self.add_ui = CreateUI(self.client_repo)
        self.add_ui.exec_()
        self.load_clients()


class ClientMainUI(QMainWindow):

    def __init__(
            self, client_repo: ClientRepo, activity_manager: ActivityManager
    ) -> None:
        super().__init__(parent=None)
        name_width, dni_width, admission_width, tel_width, dir_width = 175, 90, 100, 110, 140
        self._setup_ui(name_width, dni_width, admission_width, tel_width, dir_width)
        self.controller = Controller(client_repo, activity_manager, self.client_list)
        self._setup_callbacks()

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

    def _setup_callbacks(self):
        self.create_client_btn.clicked.connect(self.controller.add_client)

