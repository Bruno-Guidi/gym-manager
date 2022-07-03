from __future__ import annotations

from typing import Iterable

from PyQt5.QtCore import QRect, Qt, QSize
from PyQt5.QtWidgets import QMainWindow, QWidget, QListWidget, QHBoxLayout, QLabel, QPushButton, \
    QListWidgetItem, QVBoxLayout, QSpacerItem, QSizePolicy, QTextEdit, QCheckBox, QDialog, QComboBox, QLineEdit

from gym_manager.core import constants as consts
from gym_manager.core.base import String, Activity, Currency, TextLike
from gym_manager.core.system import ActivityManager
from ui.widget_config import config_lbl, config_line, config_btn, config_layout, config_checkbox, config_combobox, \
    fill_combobox
from ui.widgets import Field, valid_text_value, Dialog


class ActivityRow(QWidget):
    def __init__(
            self, item: QListWidgetItem, main_ui_controller: MainController, name_width: int, price_width: int,
            charge_once_width: int, height: int, activity: Activity, activity_manager: ActivityManager
    ):
        super().__init__()

        self.item = item
        self.main_ui_controller = main_ui_controller

        self.activity = activity
        self.activity_manager = activity_manager

        self._setup_ui(height, name_width, price_width, charge_once_width)

        self.current_height, self.previous_height = height, None
        self.item.setSizeHint(QSize(self.widget.width(), self.current_height))

        def _setup_hidden_ui():
            # Name.
            self.name_lbl = QLabel(self.widget)
            self.name_layout.addWidget(self.name_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.name_lbl, "Nombre", font_size=12, width=name_width)

            self.name_field = Field(String, self.widget, max_len=consts.CLIENT_NAME_CHARS)
            self.name_layout.addWidget(self.name_field)
            config_line(self.name_field, str(activity.name), width=name_width, enabled=False)

            # Price.
            self.price_lbl = QLabel(self.widget)
            self.price_layout.addWidget(self.price_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.price_lbl, "Precio", font_size=12, width=price_width)

            self.price_field = Field(Currency, self.widget, max_currency=consts.MAX_CURRENCY)
            self.price_layout.addWidget(self.price_field)
            config_line(self.price_field, str(activity.price), width=price_width)

            # Charge once.
            self.charge_once_lbl = QLabel(self.widget)
            self.charge_once_layout.addWidget(self.charge_once_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.charge_once_lbl, "Cobro único", font_size=12, width=charge_once_width)

            self.charge_once_checkbox = QCheckBox()
            self.charge_once_layout.addWidget(self.charge_once_checkbox)
            config_checkbox(self.charge_once_checkbox, checked=activity.charge_once, width=charge_once_width,
                            enabled=not activity.locked)

            # Save and delete buttons.
            self.save_btn = QPushButton(self.widget)
            self.top_buttons_layout.addWidget(self.save_btn)
            config_btn(self.save_btn, text="Guardar", width=100)

            self.remove_btn = QPushButton(self.widget)
            self.top_buttons_layout.addWidget(self.remove_btn)
            config_btn(self.remove_btn, text="Eliminar", width=100)

            # Description.
            self.description_lbl = QLabel(self.widget)
            self.row_layout.addWidget(self.description_lbl)
            config_lbl(self.description_lbl, "Descripción", font_size=12)

            self.description_text = QTextEdit(self.widget)
            self.row_layout.addWidget(self.description_text)
            config_line(self.description_text, str(activity.description))

        self._setup_hidden_ui = _setup_hidden_ui
        self.hidden_ui_loaded = False  # Flag used to load the hidden ui only when it is opened for the first time.

        # noinspection PyUnresolvedReferences
        self.detail_btn.clicked.connect(self.hide_detail)
        self.is_hidden = False

    def _setup_ui(self, height: int, name_width: int, price_width: int, charge_once_width: int):
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
        config_lbl(self.name_summary, str(self.activity.name), width=name_width, height=30, alignment=Qt.AlignVCenter)

        self.name_lbl: QLabel | None = None
        self.name_field: Field | None = None

        # Price layout.
        self.price_layout = QVBoxLayout()
        self.top_layout.addLayout(self.price_layout)

        self.price_summary = QLabel(self.widget)
        self.price_layout.addWidget(self.price_summary, alignment=Qt.AlignTop)
        config_lbl(self.price_summary, str(self.activity.price), width=price_width, height=30, alignment=Qt.AlignVCenter)

        self.price_lbl: QLabel | None = None
        self.price_field: Field | None = None

        # Admission layout.
        self.charge_once_layout = QVBoxLayout()
        self.top_layout.addLayout(self.charge_once_layout)

        self.charge_once_summary = QLabel(self.widget)
        self.charge_once_layout.addWidget(self.charge_once_summary, alignment=Qt.AlignTop)
        charge_once_text = "Si" if self.activity.charge_once else "No"
        config_lbl(self.charge_once_summary, charge_once_text, width=charge_once_width, height=30, alignment=Qt.AlignVCenter)

        self.charge_once_lbl: QLabel | None = None
        self.charge_once_checkbox: QCheckBox | None = None

        # Detail button.
        self.top_buttons_layout = QVBoxLayout()
        self.top_layout.addLayout(self.top_buttons_layout)

        self.detail_btn = QPushButton(self.widget)
        self.top_buttons_layout.addWidget(self.detail_btn, alignment=Qt.AlignTop)
        config_btn(self.detail_btn, text="Detalle", width=100)

        self.save_btn: QPushButton | None = None
        self.remove_btn: QPushButton | None = None

        # Description.
        self.description_lbl: QLabel | None = None
        self.description_text: QTextEdit | None = None

        self.setGeometry(QRect(0, 0, self.widget.sizeHint().width(), height))

    def _set_hidden(self, hidden: bool):
        # Hides widgets.
        self.name_lbl.setHidden(hidden)
        self.name_field.setHidden(hidden)
        self.price_lbl.setHidden(hidden)
        self.price_field.setHidden(hidden)
        self.charge_once_lbl.setHidden(hidden)
        self.charge_once_checkbox.setHidden(hidden)

        self.description_lbl.setHidden(hidden)
        self.description_text.setHidden(hidden)

        self.save_btn.setHidden(hidden)
        self.remove_btn.setHidden(hidden)

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
            # noinspection PyUnresolvedReferences
            self.save_btn.clicked.connect(self.save_changes)
            # noinspection PyUnresolvedReferences
            self.remove_btn.clicked.connect(self.remove)
            self.hidden_ui_loaded, self.previous_height = True, 350

        # Hides previously opened detail.
        if self.main_ui_controller.opened_now is None:
            self.main_ui_controller.opened_now = self
        elif self.main_ui_controller.opened_now.activity != self.activity:
            self.main_ui_controller.opened_now._set_hidden(True)
            self.main_ui_controller.opened_now = self
        else:
            self.main_ui_controller.opened_now = None

        self.item.listWidget().setCurrentItem(self.item)

        self._set_hidden(self.is_hidden)  # Hide or show the widgets.

    def save_changes(self):
        valid_descr, descr = valid_text_value(self.description_text, optional=True, max_len=consts.ACTIVITY_DESCR_CHARS)
        if not all([self.name_field.valid_value(), self.price_field.valid_value(), valid_descr]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            # Updates activity object.
            self.activity.price = self.price_field.value()
            self.activity.description = descr

            self.activity_manager.update(self.activity)

            # Updates ui.
            self.price_summary.setText(str(self.activity.price))
            self.charge_once_summary.setText("Si" if self.activity.charge_once else "No")
            self.description_text.setText(str(self.activity.description))

            Dialog.info("Éxito", f"La actividad '{self.name_field.value()}' fue actualizada correctamente.")

    def remove(self):
        if self.activity.locked:
            Dialog.info("Error", f"No esta permitido eliminar la actividad '{self.name_field.value()}'.")
            return

        inscriptions, delete = self.activity_manager.n_subscribers(self.activity), False
        if inscriptions > 0:
            delete = Dialog.confirm(f"La actividad '{self.activity.name}' tiene {inscriptions} clientes inscriptos. "
                                    f"¿Desea eliminarla igual?")

        if not delete:  # If the previous confirmation failed, then ask again.
            delete = Dialog.confirm(f"¿Desea eliminar la actividad '{self.activity.name}'?")

        if delete:
            self.main_ui_controller.opened_now = None
            self.activity_manager.remove(self.activity)
            self.item.listWidget().takeItem(self.item.listWidget().currentRow())

            Dialog.info("Éxito", f"La actividad '{self.name_field.value()}' fue eliminada correctamente.")


class MainController:
    def __init__(
            self, activity_manager: ActivityManager, main_ui: ActivityMainUI, name_width: int, price_width: int,
            charge_once_width: int
    ):
        self.main_ui = main_ui

        self.activity_manager = activity_manager
        self.opened_now: ActivityRow | None = None

        self.current_page, self.page_len = 1, 20

        self.name_width, self.price_width, self.charge_once_width = name_width, price_width, charge_once_width

        # Filters.
        filters = (TextLike("name", display_name="Nombre", attr="name",
                            translate_fun=lambda activity, value: activity.act_name.contains(value)),)
        fill_combobox(self.main_ui.filter_combobox, filters, display=lambda filter_: filter_.display_name)

        self.fill_activity_table()

        # noinspection PyUnresolvedReferences
        self.main_ui.create_client_btn.clicked.connect(self.create_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.search_btn.clicked.connect(self.fill_activity_table)
        # noinspection PyUnresolvedReferences
        self.main_ui.clear_filter_btn.clicked.connect(self.clear_and_fill)

    def _add_activity(self, activity: Activity, check_filters: bool, check_limit: bool = False):
        if check_limit and len(self.main_ui.activity_list) == self.page_len:
            self.main_ui.activity_list.takeItem(len(self.main_ui.activity_list) - 1)

        filter_, value = self.main_ui.filter_combobox.currentData(Qt.UserRole), self.main_ui.filter_line_edit.text()
        if check_filters and not filter_.passes(activity, value):
            return

        row_height = 50
        item = QListWidgetItem(self.main_ui.activity_list)
        self.main_ui.activity_list.addItem(item)
        row = ActivityRow(item, self, self.name_width, self.price_width, self.charge_once_width, row_height, activity,
                          self.activity_manager)
        self.main_ui.activity_list.setItemWidget(item, row)

    def fill_activity_table(self):
        self.main_ui.activity_list.clear()

        activities: Iterable
        filter_value = self.main_ui.filter_line_edit.text()
        if len(filter_value) == 0 or filter_value.isspace():
            activities = self.activity_manager.activity_repo.all(self.current_page, self.page_len)
        else:
            filter_ = self.main_ui.filter_combobox.currentData(Qt.UserRole)
            activities = self.activity_manager.activity_repo.all(self.current_page, self.page_len,
                                                                 ((filter_, filter_value), ))

        for activity in activities:
            self._add_activity(activity, check_filters=False)  # Activities are filtered in the repo.

    def clear_and_fill(self):
        self.main_ui.filter_line_edit.clear()
        self.fill_activity_table()

    # noinspection PyAttributeOutsideInit
    def create_ui(self):
        self._create_ui = CreateUI(self.activity_manager)
        self._create_ui.exec_()
        if self._create_ui.controller.activity is not None:
            self._add_activity(self._create_ui.controller.activity, check_filters=True, check_limit=True)


class ActivityMainUI(QMainWindow):

    def __init__(self, activity_manager: ActivityManager) -> None:
        super().__init__()
        name_width, price_width, charge_once_width = 175, 90, 100
        self._setup_ui(name_width, price_width, charge_once_width)
        self.controller = MainController(activity_manager, self, name_width, price_width, charge_once_width)

    def _setup_ui(self, name_width: int, price_width: int, charge_once_width: int):
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

        # Filtering functionalities.
        self.filter_combobox = QComboBox(self.widget)
        self.utils_layout.addWidget(self.filter_combobox)
        config_combobox(self.filter_combobox)

        self.filter_line_edit = QLineEdit(self.widget)
        self.utils_layout.addWidget(self.filter_line_edit)
        config_line(self.filter_line_edit, place_holder="Búsqueda")

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "B")

        self.clear_filter_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.clear_filter_btn)
        config_btn(self.clear_filter_btn, "C")

        self.utils_layout.addItem(QSpacerItem(80, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.create_client_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.create_client_btn)
        config_btn(self.create_client_btn, "Nueva actividad", font_size=16)

        self.main_layout.addItem(QSpacerItem(80, 15, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Header.
        self.header_layout = QHBoxLayout()
        self.main_layout.addLayout(self.header_layout)
        config_layout(self.header_layout, alignment=Qt.AlignLeft, left_margin=11, spacing=0)

        self.name_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.name_lbl)
        config_lbl(self.name_lbl, "Nombre", width=name_width + 6)  # 6 is the spacing.

        self.price_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.price_lbl)
        config_lbl(self.price_lbl, "Precio", width=price_width + 6)  # 6 is the spacing.

        self.charge_once_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.charge_once_lbl)
        config_lbl(self.charge_once_lbl, "Cobro único", width=charge_once_width + 6)  # 6 is the spacing.

        # Activities.
        self.activity_list = QListWidget(self.widget)
        self.main_layout.addWidget(self.activity_list)


class CreateController:

    def __init__(self, create_ui: CreateUI, activity_manager: ActivityManager) -> None:
        self.create_ui = create_ui

        self.activity: Activity | None = None
        self.activity_manager = activity_manager

        # noinspection PyUnresolvedReferences
        self.create_ui.ok_btn.clicked.connect(self.create_activity)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    # noinspection PyTypeChecker
    def create_activity(self):
        valid_descr, descr = valid_text_value(self.create_ui.description_text, optional=True,
                                              max_len=consts.ACTIVITY_DESCR_CHARS)
        if all([self.create_ui.name_field.valid_value(), self.create_ui.price_field.valid_value(), valid_descr]):
            self.activity = self.activity_manager.create(
                self.create_ui.name_field.value(), self.create_ui.price_field.value(),
                self.create_ui.charge_once_checkbox.isChecked(), descr
            )
            Dialog.info("Éxito", f"La categoría '{self.create_ui.name_field.value()}' fue creada correctamente.")
            self.create_ui.name_field.window().close()
        else:
            Dialog.info("Error", "Hay datos que no son válidos.")


class CreateUI(QDialog):
    def __init__(self, activity_manager: ActivityManager) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, activity_manager)

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

        # Charge once.
        self.charge_once_layout = QHBoxLayout()
        self.form_layout.addLayout(self.charge_once_layout)
        config_layout(self.charge_once_layout, alignment=Qt.AlignLeft)

        self.charge_once_lbl = QLabel()
        self.charge_once_layout.addWidget(self.charge_once_lbl)
        config_lbl(self.charge_once_lbl, "Cobro único", font_size=16, width=120)

        self.charge_once_checkbox = QCheckBox()
        self.charge_once_layout.addWidget(self.charge_once_checkbox)
        config_checkbox(self.charge_once_checkbox, checked=False)

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
