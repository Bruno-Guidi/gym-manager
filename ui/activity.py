from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QSpacerItem, QSizePolicy, QTextEdit, QDialog, QGridLayout, QTableWidget)

from gym_manager.core import constants as consts
from gym_manager.core.base import String, Activity, Currency, TextLike
from gym_manager.core.persistence import ActivityRepo, FilterValuePair
from ui.widget_config import (
    config_lbl, config_line, config_btn, config_table,
    fill_cell)
from ui.widgets import Field, valid_text_value, Dialog, FilterHeader, PageIndex


# class ActivityRow(QWidget):
#     def __init__(
#             self, item: QListWidgetItem, name_width: int, price_width: int, charge_once_width: int,
#             n_subscribers_width: int, main_ui_controller: MainController, activity: Activity,
#             activity_manager: ActivityManager
#     ):
#         super().__init__()
#         self.activity = activity
#         self.activity_manager = activity_manager
#
#         self.item = item
#         self.main_ui_controller = main_ui_controller
#
#         self._setup_ui(name_width, price_width, charge_once_width, n_subscribers_width)
#         self.item.setSizeHint(self.sizeHint())
#
#         self.is_hidden = False
#         self.hidden_ui_loaded = False  # Flag used to load the hidden ui only when it is opened for the first time.
#
#         # noinspection PyUnresolvedReferences
#         self.detail_btn.clicked.connect(self.hide_detail)
#         # noinspection PyUnresolvedReferences
#         self.save_btn.clicked.connect(self.save_changes)
#         # noinspection PyUnresolvedReferences
#         self.remove_btn.clicked.connect(self.remove)
#
#     def _setup_ui(self, name_width: int, price_width: int, charge_once_width: int, n_subscribers_width: int):
#         self.layout = QGridLayout(self)
#         self.layout.setAlignment(Qt.AlignLeft)
#
#         # Name.
#         self.name_field = Field(String, self, max_len=consts.ACTIVITY_NAME_CHARS)
#         self.layout.addWidget(self.name_field, 0, 0, alignment=Qt.AlignTop)
#         config_line(self.name_field, str(self.activity.name), font="Inconsolata", fixed_width=name_width)
#
#         # Price.
#         self.price_field = Field(Currency, self)
#         self.layout.addWidget(self.price_field, 0, 1, alignment=Qt.AlignTop)
#         config_line(self.price_field, str(self.activity.price), font="Inconsolata", fixed_width=price_width)
#
#         # Charge once.
#         self.charge_once_checkbox = QCheckBox(self)
#         self.layout.addWidget(self.charge_once_checkbox, 0, 2, alignment=Qt.AlignTop)
#         config_checkbox(self.charge_once_checkbox, checked=self.activity.charge_once, font="Inconsolata",
#                         fixed_width=charge_once_width)
#
#         # Amount of subscribers.
#         self.n_subs_lbl = QLabel(self)
#         self.layout.addWidget(self.n_subs_lbl, 0, 3, alignment=Qt.AlignTop)
#         config_lbl(self.n_subs_lbl, str(self.activity_manager.n_subscribers(self.activity)), font="Inconsolata",
#                    fixed_width=n_subscribers_width)
#
#         # See client detail button.
#         self.detail_btn = QPushButton(self)
#         self.layout.addWidget(self.detail_btn, 0, 4, alignment=Qt.AlignTop)
#         config_btn(self.detail_btn, icon_path="ui/resources/activity_detail.png", icon_size=32)
#
#         # Save client data button
#         self.save_btn = QPushButton(self)
#         self.layout.addWidget(self.save_btn, 0, 5, alignment=Qt.AlignTop)
#         config_btn(self.save_btn, icon_path="ui/resources/save.png", icon_size=32)
#
#         # Remove client button.
#         self.remove_btn = QPushButton(self)
#         self.layout.addWidget(self.remove_btn, 0, 6, alignment=Qt.AlignTop)
#         config_btn(self.remove_btn, icon_path="ui/resources/delete.png", icon_size=32)
#
#         # Adjusts size.
#         self.resize(self.minimumWidth(), self.minimumHeight())
#
#     def _setup_hidden_ui(self):
#         # Description.
#         self.description_lbl = QLabel(self)
#         self.layout.addWidget(self.description_lbl, 1, 0, 1, 5)
#         config_lbl(self.description_lbl, "Descripción", font_size=12)
#
#         self.description_text = QTextEdit(self)
#         self.layout.addWidget(self.description_text, 2, 0, 1, 7)
#         config_line(self.description_text, str(self.activity.description), adjust_to_hint=False)
#
#         # Adjusts size.
#         self.resize(self.minimumWidth(), self.minimumHeight())
#
#     def hide_detail(self):
#         # Creates the hidden widgets in case it is the first time the detail button is clicked.
#         if not self.hidden_ui_loaded:
#             self._setup_hidden_ui()
#             self.hidden_ui_loaded = True
#
#         # Hides widgets.
#         self.description_lbl.setHidden(self.is_hidden)
#         self.description_text.setHidden(self.is_hidden)
#
#         # Inverts the state of the widget.
#         self.is_hidden = not self.is_hidden
#
#         # Adjusts size.
#         self.resize(self.minimumWidth(), self.minimumHeight())
#         self.item.setSizeHint(self.sizeHint())
#
#     def save_changes(self):
#         valid_descr, descr = valid_text_value(self.description_text, optional=True,
#         max_len=consts.ACTIVITY_DESCR_CHARS)
#         if not all([self.name_field.valid_value(), self.price_field.valid_value(), valid_descr]):
#             Dialog.info("Error", "Hay datos que no son válidos.")
#         else:
#             self.activity.price = self.price_field.value()
#             self.activity.description = descr
#             self.activity.charge_once = self.charge_once_checkbox.isChecked()
#             Dialog.info("Éxito", f"La actividad '{self.name_field.value()}' fue actualizada correctamente.")
#
#     def remove(self):
#         if self.activity.locked:
#             Dialog.info("Error", f"No esta permitido eliminar la actividad '{self.name_field.value()}'.")
#             return
#
#         subscribers, delete = self.activity_manager.n_subscribers(self.activity), False
#         if subscribers > 0:
#             delete = Dialog.confirm(f"La actividad '{self.activity.name}' tiene {subscribers} cliente/s inscripto/s. "
#                                     f"\n¿Desea eliminarla igual?")
#
#         # If the previous confirmation failed, or if it didn't show up, then ask one last time.
#         if subscribers == 0 and not delete:
#             delete = Dialog.confirm(f"¿Desea eliminar la actividad '{self.activity.name}'?")
#
#         if delete:
#             activity_list = self.item.listWidget()
#             activity_list.takeItem(activity_list.row(self.item))
#             self.activity_manager.remove(self.activity)
#
#             self.main_ui_controller.refresh_table()
#
#             Dialog.info("Éxito", f"La actividad '{self.name_field.value()}' fue eliminada correctamente.")
#
#
# _dummy_activity = Activity(String("dummy_name", max_len=consts.ACTIVITY_NAME_CHARS),
#                            Currency("111111.11"), charge_once=True,
#                            description=String("dummy_descr", max_len=consts.ACTIVITY_DESCR_CHARS))
#
#
class MainController:
    def __init__(
            self, main_ui: ActivityMainUI, activity_repo: ActivityRepo
    ):
        self.main_ui = main_ui
        self.activity_repo = activity_repo

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
        self.main_ui.create_btn.clicked.connect(self.create_ui)

    def _add_activity(self, activity: Activity, check_filters: bool, check_limit: bool = False):
        if check_limit and self.main_ui.activity_table.rowCount() == self.main_ui.page_index.page_len:
            return

        if check_filters and not self.main_ui.filter_header.passes_filters(activity):
            return

        row = self.main_ui.activity_table.rowCount()
        fill_cell(self.main_ui.activity_table, row, 0, activity.name, data_type=str)
        fill_cell(self.main_ui.activity_table, row, 1, activity.price, data_type=int)
        fill_cell(self.main_ui.activity_table, row, 2, self.activity_repo.n_subscribers(activity), data_type=int)

    def fill_activity_table(self, filters: list[FilterValuePair]):
        self.main_ui.activity_table.setRowCount(0)

        self.main_ui.page_index.total_len = self.activity_repo.count(filters)
        for activity in self.activity_repo.all(self.main_ui.page_index.page,
                                               self.main_ui.page_index.page_len, filters):
            self._add_activity(activity, check_filters=False)  # Activities are filtered in the repo.

    def refresh_table(self):
        self.main_ui.filter_header.on_search_click()

    # noinspection PyAttributeOutsideInit
    def create_ui(self):
        self._create_ui = CreateUI(self.activity_repo)
        self._create_ui.exec_()
        if self._create_ui.controller.activity is not None:
            self._add_activity(self._create_ui.controller.activity, check_filters=True, check_limit=True)
            self.main_ui.page_index.total_len += 1


class ActivityMainUI(QMainWindow):

    def __init__(self, activity_repo: ActivityRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, activity_repo)

    def _setup_ui(self):
        self.setWindowTitle("Actividades")

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        # Left side of the ui.
        self.left_layout = QVBoxLayout()
        self.layout.addLayout(self.left_layout)

        # Filtering.
        self.filter_header = FilterHeader(parent=self.widget)
        self.left_layout.addWidget(self.filter_header)

        # Activities.
        self.activity_table = QTableWidget(self.widget)
        self.left_layout.addWidget(self.activity_table)
        config_table(self.activity_table, allow_resizing=True, min_rows_to_show=10,
                     columns={"Nombre": (8, str), "Precio": (8, int), "Inscriptos": (8, int)})

        # Index.
        self.page_index = PageIndex(self.widget)
        self.left_layout.addWidget(self.page_index)

        # Right side of the ui.
        self.right_layout = QVBoxLayout()
        self.layout.addLayout(self.right_layout)
        self.right_layout.setAlignment(Qt.AlignCenter)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # Vertical spacer.
        self.right_layout.addSpacerItem(QSpacerItem(30, 40, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.right_layout.addLayout(self.buttons_layout)

        self.create_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.create_btn)
        config_btn(self.create_btn, "C")

        self.save_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.save_btn)
        config_btn(self.save_btn, "G")

        self.remove_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.remove_btn)
        config_btn(self.remove_btn, "B")

        # Activity form.
        self.form_layout = QGridLayout()
        self.right_layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(20, 0, 20, 0)

        # Name.
        self.name_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self.widget, max_len=consts.ACTIVITY_NAME_CHARS)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # Price.
        self.price_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.price_lbl, 1, 0)
        config_lbl(self.price_lbl, "Precio*")

        self.price_field = Field(Currency, self.widget)
        self.form_layout.addWidget(self.price_field, 1, 1)
        config_line(self.price_field, place_holder="000000,00", adjust_to_hint=False)

        # Description.
        self.description_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.description_lbl, 2, 0, alignment=Qt.AlignTop)
        config_lbl(self.description_lbl, "Descripción")

        self.description_text = QTextEdit(self.widget)
        self.form_layout.addWidget(self.description_text, 2, 1)
        config_line(self.description_text, place_holder="Descripción", adjust_to_hint=False)

        # Vertical spacer.
        self.right_layout.addSpacerItem(QSpacerItem(30, 40, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        # Adjusts size.
        self.setMaximumSize(self.minimumWidth(), self.minimumHeight())


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
                                              max_len=consts.ACTIVITY_DESCR_CHARS)
        valid_fields = all([self.create_ui.name_field.valid_value(), self.create_ui.price_field.valid_value(),
                            valid_descr])
        if not valid_fields:
            Dialog.info("Error", "Hay datos que no son válidos.")
        elif self.activity_repo.exists(self.create_ui.name_field.value()):
            Dialog.info("Error", f"Ya existe una categoría con el nombre '{self.create_ui.name_field.value()}'.")
        else:
            self.activity = Activity(self.create_ui.name_field.value(), self.create_ui.price_field.value(), descr)
            self.activity_repo.add(self.activity)
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

        self.name_field = Field(String, parent=self, max_len=consts.ACTIVITY_NAME_CHARS)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # Price.
        self.price_lbl = QLabel(self)
        self.form_layout.addWidget(self.price_lbl, 1, 0)
        config_lbl(self.price_lbl, "Precio*")

        self.price_field = Field(Currency, self, max_currency=consts.MAX_CURRENCY)
        self.form_layout.addWidget(self.price_field, 1, 1)
        config_line(self.price_field, place_holder="000000,00", adjust_to_hint=False)

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
