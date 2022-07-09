from __future__ import annotations

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QSpacerItem, QSizePolicy, QDialog, QGridLayout, QTableWidget)

from gym_manager.core import constants as constants
from gym_manager.core.base import String, TextLike, Client, Number
from gym_manager.core.persistence import FilterValuePair, ClientRepo
from ui.widget_config import config_lbl, config_line, config_btn, config_table, fill_cell
from ui.widgets import Field, Dialog, FilterHeader, PageIndex, Separator


class MainController:
    def __init__(
            self, main_ui: ClientMainUI, client_repo: ClientRepo
    ):
        self.main_ui = main_ui
        self.client_repo = client_repo
        self._clients: dict[int, Client] = {}  # Dict that maps raw client dni to the associated client.

        # Configure the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name",
                            translate_fun=lambda client, value: client.cli_name.contains(value)), )
        self.main_ui.filter_header.config(filters, on_search_click=self.fill_client_table)

        # Configures the page index.
        self.main_ui.page_index.config(refresh_table=self.main_ui.filter_header.on_search_click,
                                       page_len=20, total_len=self.client_repo.count())

        # Fills the table.
        self.main_ui.filter_header.on_search_click()

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.main_ui.create_btn.clicked.connect(self.create_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.save_btn.clicked.connect(self.save_changes)
        # noinspection PyUnresolvedReferences
        self.main_ui.remove_btn.clicked.connect(self.remove)
        # noinspection PyUnresolvedReferences
        self.main_ui.client_table.itemSelectionChanged.connect(self.refresh_form)

    def _add_client(self, client: Client, check_filters: bool, check_limit: bool = False):
        if check_limit and self.main_ui.client_table.rowCount() == self.main_ui.page_index.page_len:
            return

        if check_filters and not self.main_ui.filter_header.passes_filters(client):
            return

        self._clients[client.dni.as_primitive()] = client
        row = self.main_ui.client_table.rowCount()
        fill_cell(self.main_ui.client_table, row, 0, client.name, data_type=str)
        fill_cell(self.main_ui.client_table, row, 1, client.dni, data_type=int)
        fill_cell(self.main_ui.client_table, row, 2, client.admission, data_type=bool)
        fill_cell(self.main_ui.client_table, row, 3, client.telephone, data_type=str)
        fill_cell(self.main_ui.client_table, row, 4, client.direction, data_type=str)

    def fill_client_table(self, filters: list[FilterValuePair]):
        self.main_ui.client_table.setRowCount(0)

        self.main_ui.page_index.total_len = self.client_repo.count(filters)
        for client in self.client_repo.all(self.main_ui.page_index.page, self.main_ui.page_index.page_len, filters):
            self._clients[client.dni.as_primitive()] = client
            self._add_client(client, check_filters=False)  # Clients are filtered in the repo.

    def refresh_form(self):
        if self.main_ui.client_table.currentRow() != -1:
            client_dni = int(self.main_ui.client_table.item(self.main_ui.client_table.currentRow(), 1).text())
            self.main_ui.name_field.setText(str(self._clients[client_dni].name))
            self.main_ui.dni_field.setText(str(self._clients[client_dni].dni))
            self.main_ui.tel_field.setText(str(self._clients[client_dni].telephone))
            self.main_ui.dir_field.setText(str(self._clients[client_dni].direction))
        else:
            # Clears the form.
            self.main_ui.name_field.clear()
            self.main_ui.dni_field.clear()
            self.main_ui.tel_field.clear()
            self.main_ui.dir_field.clear()

    def create_ui(self):
        # noinspection PyAttributeOutsideInit
        self._create_ui = CreateUI(self.client_repo)
        self._create_ui.exec_()
        if self._create_ui.controller.client is not None:
            self._add_client(self._create_ui.controller.client, check_filters=True, check_limit=True)
            self.main_ui.page_index.total_len += 1

    def save_changes(self):
        if self.main_ui.client_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un cliente.")
            return

        if not all([self.main_ui.name_field.valid_value(), self.main_ui.tel_field.valid_value(),
                    self.main_ui.dir_field.valid_value()]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            # Updates the client.
            client_dni = int(self.main_ui.client_table.item(self.main_ui.client_table.currentRow(), 1).text())
            self._clients[client_dni].name = self.main_ui.name_field.value()
            self._clients[client_dni].telephone = self.main_ui.tel_field.value()
            self._clients[client_dni].direction = self.main_ui.dir_field.value()
            self.client_repo.update(self._clients[client_dni])

            # Updates the ui.
            row = self.main_ui.client_table.currentRow()
            client = self._clients[client_dni]
            fill_cell(self.main_ui.client_table, row, 0, client.name, data_type=str, increase_row_count=False)
            fill_cell(self.main_ui.client_table, row, 1, client.dni, data_type=int, increase_row_count=False)
            fill_cell(self.main_ui.client_table, row, 2, client.admission, data_type=bool, increase_row_count=False)
            fill_cell(self.main_ui.client_table, row, 3, client.telephone, data_type=str, increase_row_count=False)
            fill_cell(self.main_ui.client_table, row, 4, client.direction, data_type=str, increase_row_count=False)

            Dialog.info("Éxito", f"El cliente '{client.name}' fue actualizado correctamente.")

    def remove(self):
        if self.main_ui.client_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un cliente.")
            return

        client_dni = int(self.main_ui.client_table.item(self.main_ui.client_table.currentRow(), 1).text())

        remove = Dialog.confirm(f"¿Desea eliminar el cliente '{self._clients[client_dni].name}'?")

        if remove:
            client = self._clients[client_dni]
            self._clients.pop(client.dni.as_primitive())
            self.client_repo.remove(client)
            self.main_ui.filter_header.on_search_click()  # Refreshes the table.

            # Clears the form.
            self.main_ui.name_field.clear()
            self.main_ui.dni_lbl.clear()
            self.main_ui.tel_field.clear()
            self.main_ui.dir_field.clear()

            Dialog.info("Éxito", f"El cliente '{client.name}' fue eliminado correctamente.")


class ClientMainUI(QMainWindow):

    def __init__(self, client_repo: ClientRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, client_repo)

    def _setup_ui(self):
        self.setWindowTitle("Clientes")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        self.left_layout = QVBoxLayout()
        self.layout.addLayout(self.left_layout)
        self.left_layout.setContentsMargins(10, 0, 10, 0)

        self.layout.addWidget(Separator(vertical=True, parent=self.widget))  # Vertical line.

        self.right_layout = QVBoxLayout()
        self.layout.addLayout(self.right_layout)
        self.right_layout.setContentsMargins(10, 0, 10, 0)

        # Filtering.
        self.filter_header = FilterHeader(parent=self.widget)
        self.left_layout.addWidget(self.filter_header)

        # Clients.
        self.client_table = QTableWidget(self.widget)  # ToDO adjust columns width.
        self.left_layout.addWidget(self.client_table)
        config_table(self.client_table, allow_resizing=True, min_rows_to_show=10,
                     columns={"Nombre": (8, str), "DNI": (8, int), "Ingreso": (8, bool), "Teléfono": (8, str),
                              "Dirección": (8, str)})

        # Index.
        self.page_index = PageIndex(self.widget)
        self.left_layout.addWidget(self.page_index)

        # Buttons.
        # Vertical spacer.
        self.right_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        self.buttons_layout = QHBoxLayout()
        self.right_layout.addLayout(self.buttons_layout)
        self.buttons_layout.setContentsMargins(80, 0, 80, 0)

        self.create_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.create_btn)
        config_btn(self.create_btn, icon_path="ui/resources/add.png", icon_size=48)

        self.save_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.save_btn)
        config_btn(self.save_btn, icon_path="ui/resources/save.png", icon_size=48)

        self.remove_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.remove_btn)
        config_btn(self.remove_btn, icon_path="ui/resources/remove.png", icon_size=48)

        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Client data form.
        self.form_layout = QGridLayout()
        self.right_layout.addLayout(self.form_layout)

        # Name.
        self.name_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, self.widget, max_len=constants.CLIENT_NAME_CHARS)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # DNI.
        self.dni_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.dni_lbl, 1, 0)
        config_lbl(self.dni_lbl, "DNI*")

        self.dni_field = Field(Number, self.widget, min_value=constants.CLIENT_MIN_DNI,
                               max_value=constants.CLIENT_MAX_DNI)
        self.form_layout.addWidget(self.dni_field, 1, 1)
        config_line(self.dni_field, place_holder="XXYYYZZZ", adjust_to_hint=False, enabled=False)

        # Telephone.
        self.tel_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.tel_lbl, 2, 0)
        config_lbl(self.tel_lbl, "Teléfono")

        self.tel_field = Field(String, self.widget, optional=constants.CLIENT_TEL_OPTIONAL,
                                max_len=constants.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel_field, 2, 1)
        config_line(self.tel_field, place_holder="Teléfono", adjust_to_hint=False)

        # Direction.
        self.dir_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.dir_lbl, 3, 0)
        config_lbl(self.dir_lbl, "Dirección")

        self.dir_field = Field(String, self.widget, optional=constants.CLIENT_DIR_OPTIONAL,
                                max_len=constants.CLIENT_DIR_CHARS)
        self.form_layout.addWidget(self.dir_field, 3, 1)
        config_line(self.dir_field, place_holder="Dirección", adjust_to_hint=False)

        # Vertical spacer.
        self.right_layout.addSpacerItem(QSpacerItem(20, 90, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))


class CreateController:

    def __init__(self, create_ui: CreateUI, client_repo: ClientRepo) -> None:
        self.create_ui = create_ui

        self.client: Client | None = None
        self.client_repo = client_repo

        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_client)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    # noinspection PyTypeChecker
    def create_client(self):
        if not all([self.create_ui.name_field.valid_value(), self.create_ui.dni_field.valid_value(),
                    self.create_ui.tel_field.valid_value(), self.create_ui.dir_field.valid_value()]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        elif self.client_repo.is_active(self.create_ui.dni_field.value()):
            Dialog.info("Error", f"Ya existe un cliente con el DNI '{self.create_ui.dni_field.value()}'.")
        else:
            self.client = Client(self.create_ui.dni_field.value(), self.create_ui.name_field.value(),
                                 date.today(), self.create_ui.tel_field.value(), self.create_ui.dir_field.value())
            self.client_repo.add(self.client)
            Dialog.info("Éxito", f"El cliente '{self.create_ui.name_field.value()}' fue creado correctamente.")
            self.create_ui.name_field.window().close()


class CreateUI(QDialog):
    def __init__(self, client_repo: ClientRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, client_repo)

    def _setup_ui(self):
        self.setWindowTitle("Nuevo cliente")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self, max_len=constants.CLIENT_NAME_CHARS)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # DNI.
        self.dni_lbl = QLabel(self)
        self.form_layout.addWidget(self.dni_lbl, 1, 0)
        config_lbl(self.dni_lbl, "DNI*")

        self.dni_field = Field(Number, self, min_value=constants.CLIENT_MIN_DNI, max_value=constants.CLIENT_MAX_DNI)
        self.form_layout.addWidget(self.dni_field, 1, 1)
        config_line(self.dni_field, place_holder="XXYYYZZZ", adjust_to_hint=False)

        # Telephone.
        self.tel_lbl = QLabel(self)
        self.form_layout.addWidget(self.tel_lbl, 2, 0)
        config_lbl(self.tel_lbl, "Teléfono")

        self.tel_field = Field(String, self, optional=constants.CLIENT_TEL_OPTIONAL, max_len=constants.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel_field, 2, 1)
        config_line(self.tel_field, place_holder="Teléfono", adjust_to_hint=False)

        # Direction.
        self.dir_lbl = QLabel(self)
        self.form_layout.addWidget(self.dir_lbl, 3, 0)
        config_lbl(self.dir_lbl, "Dirección")

        self.dir_field = Field(String, self, optional=constants.CLIENT_DIR_OPTIONAL, max_len=constants.CLIENT_DIR_CHARS)
        self.form_layout.addWidget(self.dir_field, 3, 1)
        config_line(self.dir_field, place_holder="Dirección", adjust_to_hint=False)

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
