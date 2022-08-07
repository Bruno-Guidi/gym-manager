from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QSpacerItem, QSizePolicy, QDialog, QGridLayout, QTableWidget, QCheckBox, QComboBox,
    QDesktopWidget, QTextEdit, QMenu, QAction)

from gym_manager.contact.core import ContactRepo, Contact, create_contact, update_contact, remove_contact
from gym_manager.core.base import (
    String, TextLike)
from gym_manager.core.persistence import FilterValuePair, ClientRepo
from ui import utils
from ui.widget_config import (
    config_lbl, config_line, config_btn, fill_cell, config_checkbox,
    config_combobox, fill_combobox, new_config_table)
from ui.widgets import (
    Field, Dialog, FilterHeader, PageIndex, Separator, valid_text_value)


class MainController:
    def __init__(
            self,
            main_ui: ContactMainUI,
            contact_repo: ContactRepo,
            client_repo: ClientRepo
    ):
        self.main_ui = main_ui
        self.contact_repo = contact_repo
        self.client_repo = client_repo
        self._contacts: dict[int, Contact] = {}  # Dict that maps row numbers to the displayed contact.

        # Configure the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name"),)
        self.main_ui.filter_header.config(filters, on_search_click=self.fill_contact_table)

        # Configures the page index.
        self.main_ui.page_index.config(refresh_table=self.main_ui.filter_header.on_search_click, page_len=20,
                                       show_info=False)

        # Fills the table.
        self.fill_contact_table([])

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.main_ui.create_action.triggered.connect(self.create_contact)
        # noinspection PyUnresolvedReferences
        self.main_ui.edit_action.triggered.connect(self.save_changes)
        # noinspection PyUnresolvedReferences
        self.main_ui.remove_action.triggered.connect(self.remove_contact)
        # noinspection PyUnresolvedReferences
        self.main_ui.contact_table.itemSelectionChanged.connect(self.update_contact_info)

    def _add_contact(self, contact: Contact, check_filters: bool, check_limit: bool = False):
        if check_limit and self.main_ui.contact_table.rowCount() == self.main_ui.page_index.page_len:
            return

        if check_filters and not contact.name.contains(self.main_ui.filter_header.filter_line_edit.text()):
            return

        row = self.main_ui.contact_table.rowCount()
        self._contacts[row] = contact
        fill_cell(self.main_ui.contact_table, row, 0, contact.name, data_type=str)
        fill_cell(self.main_ui.contact_table, row, 1, contact.tel1, data_type=str)
        fill_cell(self.main_ui.contact_table, row, 2, contact.tel2, data_type=str)
        fill_cell(self.main_ui.contact_table, row, 3, contact.direction, data_type=str)

    def fill_contact_table(self, dummy: list[FilterValuePair]):
        self.main_ui.contact_table.setRowCount(0)
        self._contacts.clear()

        name = String(self.main_ui.filter_header.filter_line_edit.text())
        for contact in self.contact_repo.all(self.main_ui.page_index.page, self.main_ui.page_index.page_len, name=name):
            self._add_contact(contact, check_filters=False)  # Contacts are filtered in the repo.

    def update_contact_info(self):
        row = self.main_ui.contact_table.currentRow()
        if row != -1:
            self.main_ui.description_text.setText(str(self._contacts[row].description))

    def create_contact(self):
        # noinspection PyAttributeOutsideInit
        self._create_ui = CreateUI(self.contact_repo, self.client_repo)
        self._create_ui.exec_()
        if self._create_ui.controller.contact is not None:
            self._add_contact(self._create_ui.controller.contact, check_filters=True, check_limit=True)
            self.main_ui.page_index.total_len += 1

    def save_changes(self):
        row = self.main_ui.contact_table.currentRow()
        if row == -1:
            Dialog.info("Error", "Seleccione un cliente.")
            return

        # noinspection PyAttributeOutsideInit
        self._edit_ui = EditUI(self.contact_repo, self._contacts[row])
        self._edit_ui.exec_()

        # Updates the ui.
        fill_cell(self.main_ui.contact_table, row, 0, self._contacts[row].name, data_type=str, increase_row_count=False)
        fill_cell(self.main_ui.contact_table, row, 1, self._contacts[row].tel1, data_type=str, increase_row_count=False)
        fill_cell(self.main_ui.contact_table, row, 2, self._contacts[row].tel2, data_type=str, increase_row_count=False)
        fill_cell(self.main_ui.contact_table, row, 3, self._contacts[row].direction, data_type=str,
                  increase_row_count=False)

        self.update_contact_info()

    def remove_contact(self):
        row = self.main_ui.contact_table.currentRow()
        if row == -1:
            Dialog.info("Error", "Seleccione un contacto en la tabla.")
            return

        contact = self._contacts[row]

        if Dialog.confirm(f"¿Desea eliminar el contacto '{contact.name}'?"):
            remove_contact(self.contact_repo, contact)
            self._contacts.pop(row)
            self.fill_contact_table([])  # Refreshes the table.

            # Clears the description.
            self.main_ui.description_text.clear()

            Dialog.info("Éxito", f"El contacto '{contact.name}' fue eliminado correctamente.")


class ContactMainUI(QMainWindow):

    def __init__(
            self,
            contact_repo: ContactRepo,
            client_repo: ClientRepo
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, contact_repo, client_repo)

    def _setup_ui(self):
        self.setWindowTitle("Agenda")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        # Menu bar.
        menu_bar = self.menuBar()

        client_menu = QMenu("&Agenda", self)
        menu_bar.addMenu(client_menu)

        self.create_action = QAction("&Agregar contacto", self)
        client_menu.addAction(self.create_action)

        self.edit_action = QAction("&Editar contacto", self)
        client_menu.addAction(self.edit_action)

        self.remove_action = QAction("&Eliminar contacto", self)
        client_menu.addAction(self.remove_action)

        self.left_layout = QVBoxLayout()
        self.layout.addLayout(self.left_layout)
        self.left_layout.setContentsMargins(10, 0, 10, 0)

        self.layout.addWidget(Separator(vertical=True, parent=self.widget))  # Vertical line.

        self.right_layout = QVBoxLayout()
        self.layout.addLayout(self.right_layout)
        self.right_layout.setContentsMargins(0, 80, 0, 0)
        self.right_layout.setAlignment(Qt.AlignTop)

        # Filtering.
        self.filter_header = FilterHeader(parent=self.widget)
        self.left_layout.addWidget(self.filter_header)

        # Contacts.
        self.contact_table = QTableWidget(self.widget)
        self.left_layout.addWidget(self.contact_table)
        new_config_table(self.contact_table, width=860, allow_resizing=False, min_rows_to_show=10,
                         columns={"Nombre": (.25, str), "Teléfono 1": (.25, str), "Teléfono 2": (.25, str),
                                  "Dirección": (.25, str)})

        # Index.
        self.page_index = PageIndex(self.widget)
        self.left_layout.addWidget(self.page_index)

        # Description.
        self.description_lbl = QLabel(self.widget)
        self.right_layout.addWidget(self.description_lbl)
        config_lbl(self.description_lbl, "Descripción")

        self.description_text = QTextEdit(self.widget)
        self.right_layout.addWidget(self.description_text)
        config_line(self.description_text, read_only=True)

        self.setFixedSize(self.minimumSizeHint())

        self.move(int(QDesktopWidget().geometry().center().x() - self.sizeHint().width() / 2),
                  int(QDesktopWidget().geometry().center().y() - self.sizeHint().height() / 2))


class CreateController:

    def __init__(self, create_ui: CreateUI, contact_repo: ContactRepo, client_repo: ClientRepo) -> None:
        self.create_ui = create_ui

        self.contact: Contact | None = None
        self.contact_repo = contact_repo
        self.client_repo = client_repo

        self.enable_client_search()

        # Configure the filtering widget.
        filters = (TextLike("client_name", display_name="Nombre cliente", attr="name",
                            translate_fun=lambda client, value: client.cli_name.contains(value)),)
        self.create_ui.filter_header.config(filters, self.fill_client_combobox, allow_empty_filter=False)

        # noinspection PyUnresolvedReferences
        self.create_ui.client_combobox.currentTextChanged.connect(self.fill_name_field)
        # noinspection PyUnresolvedReferences
        self.create_ui.name_checkbox.stateChanged.connect(self.enable_client_search)
        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_contact)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    def fill_name_field(self):
        if self.create_ui.client_combobox.currentIndex() != -1:
            self.create_ui.name_field.setText(self.create_ui.client_combobox.currentText())

    def enable_client_search(self):
        self.create_ui.filter_header.setEnabled(not self.create_ui.name_checkbox.isChecked())
        self.create_ui.client_combobox.setEnabled(not self.create_ui.name_checkbox.isChecked())
        self.create_ui.name_field.setEnabled(self.create_ui.name_checkbox.isChecked())

    def fill_client_combobox(self, filters: list[FilterValuePair]):
        fill_combobox(self.create_ui.client_combobox,
                      self.client_repo.all(page=1, filters=filters),
                      lambda client: client.name.as_primitive())

    # noinspection PyTypeChecker
    def create_contact(self):
        valid_descr, descr = valid_text_value(self.create_ui.description_text, utils.ACTIVITY_DESCR_CHARS,
                                              optional=True)
        if not all([self.create_ui.name_field.valid_value(), self.create_ui.tel1_field.valid_value(),
                    self.create_ui.tel2_field.valid_value(), self.create_ui.dir_field.valid_value(), valid_descr]):
            Dialog.info("Error", "Hay datos que no son válidos.")
            return
        client = None if self.create_ui.name_checkbox.isChecked() else self.create_ui.client_combobox.currentData(Qt.UserRole)
        if client is not None and self.contact_repo.has_contact_info(client):
            Dialog.info("Error", f"El cliente '{client.name}' ya tiene un contacto asociado.")
        else:
            self.contact = create_contact(
                self.contact_repo, self.create_ui.name_field.value(), self.create_ui.tel1_field.value(),
                self.create_ui.tel2_field.value(), self.create_ui.dir_field.value(), descr, client
            )
            Dialog.info("Éxito", f"El contacto '{self.contact.name}' fue creado correctamente.")
            self.create_ui.name_field.window().close()


class CreateUI(QDialog):
    def __init__(self, contact_repo: ContactRepo, client_repo: ClientRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, contact_repo, client_repo)

    def _setup_ui(self):
        self.setWindowTitle("Nuevo contacto")
        self.layout = QVBoxLayout(self)

        # Filtering.
        self.filter_header = FilterHeader(show_clear_button=False)
        self.layout.addWidget(self.filter_header)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_checkbox = QCheckBox(self)
        self.form_layout.addWidget(self.name_checkbox, 1, 0)
        config_checkbox(self.name_checkbox, "Nombre", checked=True, layout_dir=Qt.LayoutDirection.RightToLeft)

        self.name_field = Field(String, self, max_len=utils.CLIENT_NAME_CHARS, invalid_values=("Pago", "Fijo"),
                                optional=False)
        self.form_layout.addWidget(self.name_field, 1, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # Client
        self.client_lbl = QLabel(self)
        self.form_layout.addWidget(self.client_lbl, 0, 0)
        config_lbl(self.client_lbl, "Cliente")

        self.client_combobox = QComboBox(self)
        self.form_layout.addWidget(self.client_combobox, 0, 1)
        config_combobox(self.client_combobox, fixed_width=self.name_field.width(), adjust_to_hint=False)

        # Telephone 1.
        self.tel1_lbl = QLabel(self)
        self.form_layout.addWidget(self.tel1_lbl, 2, 0)
        config_lbl(self.tel1_lbl, "Teléfono 1")

        self.tel1_field = Field(String, self, optional=True, min_value=utils.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel1_field, 2, 1)
        config_line(self.tel1_field, place_holder="Teléfono 1", adjust_to_hint=False)

        # Telephone 2.
        self.tel2_lbl = QLabel(self)
        self.form_layout.addWidget(self.tel2_lbl, 3, 0)
        config_lbl(self.tel2_lbl, "Teléfono 2")

        self.tel2_field = Field(String, self, optional=True, max_len=utils.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel2_field, 3, 1)
        config_line(self.tel2_field, place_holder="Teléfono 2", adjust_to_hint=False)

        # Direction.
        self.dir_lbl = QLabel(self)
        self.form_layout.addWidget(self.dir_lbl, 4, 0)
        config_lbl(self.dir_lbl, "Dirección")

        self.dir_field = Field(String, self, optional=True, max_len=utils.CLIENT_DIR_CHARS)
        self.form_layout.addWidget(self.dir_field, 4, 1)
        config_line(self.dir_field, place_holder="Dirección", adjust_to_hint=False)

        # Description.
        self.description_lbl = QLabel(self)
        self.form_layout.addWidget(self.description_lbl, 5, 0, alignment=Qt.AlignTop)
        config_lbl(self.description_lbl, "Descripción")

        self.description_text = QTextEdit(self)
        self.form_layout.addWidget(self.description_text, 5, 1)
        config_line(self.description_text, place_holder="Descripción", adjust_to_hint=False)

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


class EditController:

    def __init__(self, edit_ui: EditUI, contact_repo: ContactRepo, contact: Contact) -> None:
        self.edit_ui = edit_ui

        self.contact = contact
        self.contact_repo = contact_repo

        self.edit_ui.name_field.setEnabled(self.contact.client is None)

        self.edit_ui.name_field.setText(contact.name.as_primitive())
        self.edit_ui.tel1_field.setText(contact.tel1.as_primitive())
        self.edit_ui.tel2_field.setText(contact.tel2.as_primitive())
        self.edit_ui.dir_field.setText(contact.direction.as_primitive())
        self.edit_ui.description_text.setText(contact.description.as_primitive())

        # noinspection PyUnresolvedReferences
        self.edit_ui.confirm_btn.clicked.connect(self.edit_contact)
        # noinspection PyUnresolvedReferences
        self.edit_ui.cancel_btn.clicked.connect(self.edit_ui.reject)

    # noinspection PyTypeChecker
    def edit_contact(self):
        valid_descr, descr = valid_text_value(self.edit_ui.description_text, utils.ACTIVITY_DESCR_CHARS,
                                              optional=True)
        if not all([self.edit_ui.name_field.valid_value(), self.edit_ui.tel1_field.valid_value(),
                    self.edit_ui.tel2_field.valid_value(), self.edit_ui.dir_field.valid_value(), valid_descr]):
            Dialog.info("Error", "Hay datos que no son válidos.")
            return
        else:
            update_contact(self.contact_repo, self.contact, self.edit_ui.name_field.value(),
                           self.edit_ui.tel1_field.value(), self.edit_ui.tel2_field.value(),
                           self.edit_ui.dir_field.value(), descr)
            Dialog.info("Éxito", f"El contacto '{self.contact.name}' fue editado correctamente.")
            self.edit_ui.name_field.window().close()


class EditUI(QDialog):
    def __init__(self, contact_repo: ContactRepo, contact: Contact) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = EditController(self, contact_repo, contact)

    def _setup_ui(self):
        self.setWindowTitle("Editar contacto")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre")

        self.name_field = Field(String, self, max_len=utils.CLIENT_NAME_CHARS, invalid_values=("Pago", "Fijo"),
                                optional=False)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # Telephone 1.
        self.tel1_lbl = QLabel(self)
        self.form_layout.addWidget(self.tel1_lbl, 1, 0)
        config_lbl(self.tel1_lbl, "Teléfono 1")

        self.tel1_field = Field(String, self, optional=True, min_value=utils.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel1_field, 1, 1)
        config_line(self.tel1_field, place_holder="Teléfono 1", adjust_to_hint=False)

        # Telephone 2.
        self.tel2_lbl = QLabel(self)
        self.form_layout.addWidget(self.tel2_lbl, 2, 0)
        config_lbl(self.tel2_lbl, "Teléfono 2")

        self.tel2_field = Field(String, self, optional=True, max_len=utils.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel2_field, 2, 1)
        config_line(self.tel2_field, place_holder="Teléfono 2", adjust_to_hint=False)

        # Direction.
        self.dir_lbl = QLabel(self)
        self.form_layout.addWidget(self.dir_lbl, 3, 0)
        config_lbl(self.dir_lbl, "Dirección")

        self.dir_field = Field(String, self, optional=True, max_len=utils.CLIENT_DIR_CHARS)
        self.form_layout.addWidget(self.dir_field, 3, 1)
        config_line(self.dir_field, place_holder="Dirección", adjust_to_hint=False)

        # Description.
        self.description_lbl = QLabel(self)
        self.form_layout.addWidget(self.description_lbl, 4, 0, alignment=Qt.AlignTop)
        config_lbl(self.description_lbl, "Descripción")

        self.description_text = QTextEdit(self)
        self.form_layout.addWidget(self.description_text, 4, 1)
        config_line(self.description_text, place_holder="Descripción", adjust_to_hint=False)

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
