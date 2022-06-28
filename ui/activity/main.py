from __future__ import annotations

from PyQt5.QtCore import QRect, Qt, QSize
from PyQt5.QtWidgets import QMainWindow, QWidget, QListWidget, QHBoxLayout, QLabel, QPushButton, \
    QListWidgetItem, QVBoxLayout, QSpacerItem, QSizePolicy, QMessageBox, \
    QTextEdit, QCheckBox, QDialog

from gym_manager.core import constants as consts
from gym_manager.core.system import ActivityManager
from gym_manager.core.base import String, Activity, Currency, TextLike
from ui.widget_config import config_lbl, config_line, config_btn, config_layout, config_checkbox
from ui.widgets import Field, valid_text_value, SearchBox, Dialog


class ActivityRow(QWidget):
    def __init__(
            self, item: QListWidgetItem, main_ui_controller: MainController, name_width: int, price_width: int,
            pay_once_width: int, height: int, activity: Activity, activity_manager: ActivityManager
    ):
        super().__init__()

        self.item = item
        self.main_ui_controller = main_ui_controller

        self.activity = activity
        self.activity_manager = activity_manager

        self._setup_ui(height, name_width, price_width, pay_once_width)

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

            # Pay once.
            self.pay_once_lbl = QLabel(self.widget)
            self.pay_once_layout.addWidget(self.pay_once_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.pay_once_lbl, "Pago único", font_size=12, width=pay_once_width)

            self.pay_once_checkbox = QCheckBox()
            self.pay_once_layout.addWidget(self.pay_once_checkbox)
            config_checkbox(self.pay_once_checkbox, checked=activity.charge_once, width=pay_once_width)

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

    def _setup_ui(self, height: int, name_width: int, price_width: int, pay_once_width: int):
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
        self.pay_once_layout = QVBoxLayout()
        self.top_layout.addLayout(self.pay_once_layout)

        self.pay_once_summary = QLabel(self.widget)
        self.pay_once_layout.addWidget(self.pay_once_summary, alignment=Qt.AlignTop)
        pay_once_text = "Si" if self.activity.charge_once else "No"
        config_lbl(self.pay_once_summary, pay_once_text, width=pay_once_width, height=30, alignment=Qt.AlignVCenter)

        self.pay_once_lbl: QLabel | None = None
        self.pay_once_checkbox: QCheckBox | None = None

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
        self.pay_once_lbl.setHidden(hidden)
        self.pay_once_checkbox.setHidden(hidden)

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
            self.activity.charge_once = self.pay_once_checkbox.isChecked()
            self.activity.description = descr

            self.activity_manager.update(self.activity)

            # Updates ui.
            self.price_summary.setText(str(self.activity.price))
            self.pay_once_summary.setText("Si" if self.activity.charge_once else "No")
            self.description_text.setText(str(self.activity.description))

            Dialog.info("Éxito", f"La actividad '{self.name_field.value()}' fue actualizada correctamente.")

    def remove(self):
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
            pay_once_width: int
    ):
        self.main_ui = main_ui

        self.activity_manager = activity_manager
        self.opened_now: ActivityRow | None = None

        self.name_width, self.price_width, self.pay_once_width = name_width, price_width, pay_once_width

        for activity in self.activity_manager.activities(**self.main_ui.search_box.filters()):
            self._add_activity(activity, check_filters=False)  # The activities are filtered in the ActivityManager.

    def _add_activity(self, activity: Activity, check_filters: bool):
        if check_filters and not self.main_ui.search_box.passes_filters(activity):
            return

        row_height = 50
        item = QListWidgetItem(self.main_ui.activity_list)
        self.main_ui.activity_list.addItem(item)
        row = ActivityRow(item, self, self.name_width, self.price_width, self.pay_once_width, row_height, activity,
                          self.activity_manager)
        self.main_ui.activity_list.setItemWidget(item, row)

    def create_activity(self):
        self._create_ui = CreateUI(self.activity_manager)
        self._create_ui.exec_()
        if self._create_ui.controller.activity is not None:
            self._add_activity(self._create_ui.controller.activity, check_filters=True)

    def search(self):
        self.main_ui.activity_list.clear()
        for activity in self.activity_manager.activities(**self.main_ui.search_box.filters()):
            self._add_activity(activity, check_filters=False)  # The activities are filtered in the ActivityManager.


class ActivityMainUI(QMainWindow):

    def __init__(self, activity_manager: ActivityManager) -> None:
        super().__init__(parent=None)
        name_width, price_width, pay_once_width = 175, 90, 100
        self._setup_ui(name_width, price_width, pay_once_width)
        self.controller = MainController(activity_manager, self.activity_list, self.search_box, name_width, price_width,
                                         pay_once_width)

        self.create_client_btn.clicked.connect(self.controller.create_activity)
        self.search_btn.clicked.connect(self.controller.search)

    def _setup_ui(self, name_width: int, price_width: int, pay_once_width: int):
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

        self.search_box = SearchBox([TextLike("name", display_name="Nombre", attr="name")], parent=self.widget)
        self.utils_layout.addWidget(self.search_box)

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "Busq", font_size=16)

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

        self.pay_once_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.pay_once_lbl)
        config_lbl(self.pay_once_lbl, "Pago único", width=pay_once_width + 6)  # 6 is the spacing.

        # Activities.
        self.activity_list = QListWidget(self.widget)
        self.main_layout.addWidget(self.activity_list)


class Controller:

    def __init__(
            self, name_field: Field, price_field: Field, pay_once_checkbox: QCheckBox, description_text: QTextEdit,
            activity_manager: ActivityManager
    ) -> None:
        self.name_field = name_field
        self.price_field = price_field
        self.pay_once_checkbox = pay_once_checkbox
        self.description_text = description_text

        self.activity: Activity | None = None
        self.activity_manager = activity_manager

    # noinspection PyTypeChecker
    def create_activity(self):
        valid_descr, descr = valid_text_value(self.description_text, optional=True, max_len=consts.ACTIVITY_DESCR_CHARS)
        if all([self.name_field.valid_value(), self.price_field.valid_value(), valid_descr]):
            self.activity = self.activity_manager.create(self.name_field.value(), self.price_field.value(),
                                                         self.pay_once_checkbox.isChecked(), descr)
            Dialog.info("Éxito", f"La categoría '{self.name_field.value()}' fue creada correctamente.")
            self.name_field.window().close()
        else:
            Dialog.info("Error", "Hay datos que no son válidos.")


class CreateUI(QDialog):
    def __init__(self, activity_manager: ActivityManager) -> None:
        super().__init__(parent=None)
        self._setup_ui()
        self.controller = Controller(self.name_field, self.price_field, self.pay_once_checkbox, self.description_text,
                                     activity_manager)

        self.ok_btn.clicked.connect(self.controller.create_activity)
        self.cancel_btn.clicked.connect(self.reject)

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

        # Pay once.
        self.pay_once_layout = QHBoxLayout()
        self.form_layout.addLayout(self.pay_once_layout)
        config_layout(self.pay_once_layout, alignment=Qt.AlignLeft)

        self.pay_once_lbl = QLabel()
        self.pay_once_layout.addWidget(self.pay_once_lbl)
        config_lbl(self.pay_once_lbl, "Pago único", font_size=16, width=120)

        self.pay_once_checkbox = QCheckBox()
        self.pay_once_layout.addWidget(self.pay_once_checkbox)

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
