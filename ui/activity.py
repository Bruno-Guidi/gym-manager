from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QSpacerItem, QSizePolicy, QTextEdit, QDialog, QGridLayout, QTableWidget, QMenu, QAction)

from gym_manager.core.base import String, Activity, Currency, TextLike
from gym_manager.core.persistence import ActivityRepo, FilterValuePair
from gym_manager.core.security import SecurityHandler
from ui import utils
from ui.widget_config import (
    config_lbl, config_line, config_btn, fill_cell, new_config_table)
from ui.widgets import Field, valid_text_value, Dialog, FilterHeader, PageIndex, Separator


class MainController:
    def __init__(
            self, main_ui: ActivityMainUI, activity_repo: ActivityRepo, security_handler: SecurityHandler
    ):
        self.main_ui = main_ui
        self.activity_repo = activity_repo
        self.security_handler = security_handler
        self._activities: dict[int, Activity] = {}  # Dict that maps row number to the associated activity.

        # Configure the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name",
                            translate_fun=lambda activity, value: activity.act_name.contains(value)),)
        self.main_ui.filter_header.config(filters, on_search_click=self.fill_activity_table)

        # Configures the page index.
        self.main_ui.page_index.config(refresh_table=self.main_ui.filter_header.on_search_click,
                                       page_len=10, total_len=self.activity_repo.count())

        # Fills the table.
        self.main_ui.filter_header.on_search_click()

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.main_ui.create_action.triggered.connect(self.create_activity)
        # noinspection PyUnresolvedReferences
        self.main_ui.edit_action.triggered.connect(self.edit_activity)
        # noinspection PyUnresolvedReferences
        self.main_ui.remove_action.triggered.connect(self.remove_activity)
        # noinspection PyUnresolvedReferences
        self.main_ui.activity_table.itemSelectionChanged.connect(self.update_description)

    def _add_activity(self, activity: Activity, check_filters: bool, check_limit: bool = False):
        if check_limit and self.main_ui.activity_table.rowCount() == self.main_ui.page_index.page_len:
            return

        if check_filters and not self.main_ui.filter_header.passes_filters(activity):
            return

        row = self.main_ui.activity_table.rowCount()
        self._activities[row] = activity
        fill_cell(self.main_ui.activity_table, row, 0, activity.name, data_type=str)
        fill_cell(self.main_ui.activity_table, row, 1, Currency.fmt(activity.price), data_type=int)
        fill_cell(self.main_ui.activity_table, row, 2, self.activity_repo.n_subscribers(activity), data_type=int)

    def fill_activity_table(self, filters: list[FilterValuePair]):
        self.main_ui.activity_table.setRowCount(0)

        self.main_ui.page_index.total_len = self.activity_repo.count(filters)
        for activity in self.activity_repo.all(self.main_ui.page_index.page, self.main_ui.page_index.page_len, filters):
            self._add_activity(activity, check_filters=False)  # Activities are filtered in the repo.

    def create_activity(self):
        # noinspection PyAttributeOutsideInit
        self._create_ui = CreateUI(self.activity_repo)
        self._create_ui.exec_()
        if self._create_ui.controller.activity is not None:
            self._add_activity(self._create_ui.controller.activity, check_filters=True, check_limit=True)
            self.main_ui.page_index.total_len += 1

    def edit_activity(self):
        row = self.main_ui.activity_table.currentRow()
        if row == -1:
            Dialog.info("Error", "Seleccione una actividad en la tabla.")
            return

        activity = self._activities[row]

        # noinspection PyAttributeOutsideInit
        self._edit_ui = EditUI(self.activity_repo, activity)
        self._edit_ui.exec_()

        # Updates the ui.
        fill_cell(self.main_ui.activity_table, row, 0, activity.name, data_type=str, increase_row_count=False)
        fill_cell(self.main_ui.activity_table, row, 1, Currency.fmt(activity.price), data_type=int,
                  increase_row_count=False)
        fill_cell(self.main_ui.activity_table, row, 2, self.activity_repo.n_subscribers(activity),
                  data_type=int, increase_row_count=False)
        self.main_ui.description_text.setText(activity.description.as_primitive())

    def remove_activity(self):
        if self.main_ui.activity_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione una actividad en la tabla.")
            return

        activity = self._activities[self.main_ui.activity_table.currentRow()]
        if activity.locked:
            Dialog.info("Error", f"No esta permitido eliminar la actividad '{activity.name}'.")
            return

        if Dialog.confirm(f"¿Desea eliminar la actividad '{activity.name}'?"):
            self.activity_repo.remove(activity)
            activity.removed = True

            self._activities.pop(self.main_ui.activity_table.currentRow())
            self.main_ui.filter_header.on_search_click()  # Refreshes the table.

            Dialog.info("Éxito", f"La actividad '{activity.name}' fue eliminada correctamente.")

            self.main_ui.description_text.clear()

    def update_description(self):
        row = self.main_ui.activity_table.currentRow()
        if row != -1:
            self.main_ui.description_text.setText(self._activities[row].description.as_primitive())


class ActivityMainUI(QMainWindow):

    def __init__(self, activity_repo: ActivityRepo, security_handler: SecurityHandler) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, activity_repo, security_handler)

    def _setup_ui(self):
        self.setWindowTitle("Actividades")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        # Menu bar.
        menu_bar = self.menuBar()

        activity_menu = QMenu("&Actividades", self)
        menu_bar.addMenu(activity_menu)

        self.create_action = QAction("&Agregar", self)
        activity_menu.addAction(self.create_action)

        self.edit_action = QAction("&Editar", self)
        activity_menu.addAction(self.edit_action)

        self.remove_action = QAction("&Eliminar", self)
        activity_menu.addAction(self.remove_action)

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

        # Activities.
        self.activity_table = QTableWidget(self.widget)
        self.left_layout.addWidget(self.activity_table)
        new_config_table(self.activity_table, width=600, allow_resizing=False,
                         columns={"Nombre": (.55, str), "Precio": (.25, int), "Inscriptos": (.2, int)},
                         min_rows_to_show=10)

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


class CreateController:

    def __init__(self, create_ui: CreateUI, activity_repo: ActivityRepo) -> None:
        self.create_ui = create_ui

        self.activity: Activity | None = None
        self.activity_repo = activity_repo

        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_activity)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    # noinspection PyTypeChecker
    def create_activity(self):
        valid_descr, descr = valid_text_value(self.create_ui.description_text, optional=True,
                                              max_len=utils.ACTIVITY_DESCR_CHARS)
        valid_fields = all([self.create_ui.name_field.valid_value(), self.create_ui.price_field.valid_value(),
                            valid_descr])
        if not valid_fields:
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            self.activity = self.activity_repo.create(
                self.create_ui.name_field.value(), self.create_ui.price_field.value(), descr
            )
            Dialog.info("Éxito", f"La categoría '{self.create_ui.name_field.value()}' fue creada correctamente.")
            self.create_ui.name_field.window().close()


class CreateUI(QDialog):
    def __init__(self, activity_repo: ActivityRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, activity_repo)

    def _setup_ui(self):
        self.setWindowTitle("Nueva actividad")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self, max_len=utils.ACTIVITY_NAME_CHARS, optional=False)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # Price.
        self.price_lbl = QLabel(self)
        self.form_layout.addWidget(self.price_lbl, 1, 0)
        config_lbl(self.price_lbl, "Precio")

        self.price_field = Field(Currency, self)
        self.form_layout.addWidget(self.price_field, 1, 1)
        config_line(self.price_field, "0,00", place_holder="000000,00", adjust_to_hint=False)

        # Description.
        self.description_lbl = QLabel(self)
        self.form_layout.addWidget(self.description_lbl, 2, 0, alignment=Qt.AlignTop)
        config_lbl(self.description_lbl, "Descripción")

        self.description_text = QTextEdit(self)
        self.form_layout.addWidget(self.description_text, 2, 1)
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

    def __init__(self, edit_ui: EditUI, activity_repo: ActivityRepo, activity: Activity) -> None:
        self.edit_ui = edit_ui

        self.activity_repo = activity_repo

        self.activity = activity
        self.edit_ui.name_field.setText(activity.name.as_primitive())
        self.edit_ui.price_field.setText(str(Currency.fmt(activity.price, symbol="")))
        self.edit_ui.description_text.setText(activity.description.as_primitive())

        # noinspection PyUnresolvedReferences
        self.edit_ui.confirm_btn.clicked.connect(self.edit_activity)
        # noinspection PyUnresolvedReferences
        self.edit_ui.cancel_btn.clicked.connect(self.edit_ui.reject)

    # noinspection PyTypeChecker
    def edit_activity(self):
        valid_descr, descr = valid_text_value(self.edit_ui.description_text, optional=True,
                                              max_len=utils.ACTIVITY_DESCR_CHARS)
        valid_fields = all([self.edit_ui.name_field.valid_value(), self.edit_ui.price_field.valid_value(),
                            valid_descr])
        if not valid_fields:
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            self.activity.name = self.edit_ui.name_field.value()
            self.activity.price = self.edit_ui.price_field.value()
            self.activity.description = descr
            self.activity_repo.update(self.activity)
            Dialog.info("Éxito", f"La categoría '{self.edit_ui.name_field.value()}' fue editada correctamente.")
            self.edit_ui.name_field.window().close()


class EditUI(QDialog):
    def __init__(self, activity_repo: ActivityRepo, activity: Activity) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = EditController(self, activity_repo, activity)

    def _setup_ui(self):
        self.setWindowTitle("Editar actividad")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self, max_len=utils.ACTIVITY_NAME_CHARS, optional=False)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # Price.
        self.price_lbl = QLabel(self)
        self.form_layout.addWidget(self.price_lbl, 1, 0)
        config_lbl(self.price_lbl, "Precio")

        self.price_field = Field(Currency, self)
        self.form_layout.addWidget(self.price_field, 1, 1)
        config_line(self.price_field, "0,00", place_holder="000000,00", adjust_to_hint=False)

        # Description.
        self.description_lbl = QLabel(self)
        self.form_layout.addWidget(self.description_lbl, 2, 0, alignment=Qt.AlignTop)
        config_lbl(self.description_lbl, "Descripción")

        self.description_text = QTextEdit(self)
        self.form_layout.addWidget(self.description_text, 2, 1)
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
