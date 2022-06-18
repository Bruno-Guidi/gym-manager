from __future__ import annotations

from PyQt5.QtCore import QRect, Qt, QSize
from PyQt5.QtWidgets import QMainWindow, QWidget, QListWidget, QHBoxLayout, QLabel, QPushButton, \
    QListWidgetItem, QVBoxLayout, QComboBox, QLineEdit, QSpacerItem, QSizePolicy, QMessageBox, \
    QTextEdit, QCheckBox

from gym_manager.core import attr_constraints
from gym_manager.core.activity_manager import ActivityManager
from gym_manager.core.base import String, Activity, Currency
from ui.activity.create import CreateUI
from ui.widget_config import config_lbl, config_line, config_btn, config_layout, config_combobox, config_checkbox
from ui.widgets import Field, valid_text_value


class ActivityRow(QWidget):
    def __init__(
            self, activity: Activity, activity_manager: ActivityManager, item: QListWidgetItem,
            main_ui_controller: Controller, name_width: int, price_width: int, pay_once_width: int, height: int
    ):
        super().__init__()
        self.activity = activity
        self.activity_manager = activity_manager
        self.item = item
        self.main_ui_controller = main_ui_controller

        self._setup_ui(height, name_width, price_width, pay_once_width)

        self.current_height, self.previous_height = height, None
        self.item.setSizeHint(QSize(self.widget.width(), self.current_height))

        def _setup_hidden_ui():
            # Name.
            self.name_lbl = QLabel(self.widget)
            self.name_layout.addWidget(self.name_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.name_lbl, "Nombre", font_size=12, width=name_width)

            self.name_field = Field(String, self.widget, max_len=attr_constraints.CLIENT_NAME_CHARS)
            self.name_layout.addWidget(self.name_field)
            config_line(self.name_field, str(activity.name), width=name_width)

            # Price.
            self.price_lbl = QLabel(self.widget)
            self.price_layout.addWidget(self.price_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.price_lbl, "Precio", font_size=12, width=price_width)

            self.price_field = Field(Currency, self.widget, positive=True, max_currency=attr_constraints.MAX_CURRENCY)
            self.price_layout.addWidget(self.price_field)
            config_line(self.price_field, str(activity.price), width=price_width)

            # Pay once.
            self.pay_once_lbl = QLabel(self.widget)
            self.pay_once_layout.addWidget(self.pay_once_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.pay_once_lbl, "Pago único", font_size=12, width=pay_once_width)

            self.pay_once_checkbox = QCheckBox()
            self.pay_once_layout.addWidget(self.pay_once_checkbox)
            config_checkbox(self.pay_once_checkbox, checked=activity.pay_once, width=pay_once_width)

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
        pay_once_text = "Si" if self.activity.pay_once else "No"
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
            self.save_btn.clicked.connect(self.save_changes)
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
        valid_descr, descr = valid_text_value(self.description_text, optional=True,
                                              max_len=attr_constraints.ACTIVITY_DESCR_CHARS)
        if not all([self.name_field.valid_value(), self.price_field.valid_value(), valid_descr]):
            QMessageBox.about(self.name_field.window(), "Error", "Hay datos que no son válidos.")
        else:
            # Updates activity object.
            self.activity.name = self.name_field.value()
            self.activity.price = self.price_field.value()
            self.activity.pay_once = self.pay_once_checkbox.isChecked()
            self.activity.description = descr

            self.activity_manager.update(self.activity)

            # Updates ui.
            self.name_summary.setText(str(self.activity.name))
            self.price_summary.setText(str(self.activity.price))
            self.pay_once_summary.setText("Si" if self.activity.pay_once else "No")
            self.description_text.setText(str(self.activity.description))

            QMessageBox.about(self.name_field.window(), "Éxito",
                              f"La actividad '{self.name_field.value()}' fue actualizada correctamente.")

    def remove(self):
        inscriptions, delete = self.activity_manager.inscriptions(self.activity), True
        if inscriptions > 0:
            delete = QMessageBox.question(self.name_field.window(), "Confirmar",
                                          f"La actividad '{self.activity.name}' tiene {inscriptions} clientes "
                                          f"inscriptos. ¿Desea eliminarla igual?")

        if delete:
            self.main_ui_controller.opened_now = None
            self.activity_manager.remove(self.activity)
            self.item.listWidget().takeItem(self.item.listWidget().currentRow())

            QMessageBox.about(self.name_field.window(), "Éxito",
                              f"La actividad '{self.name_field.value()}' fue eliminada correctamente.")


class Controller:
    def __init__(self, activity_manager: ActivityManager, activity_list: QListWidget,
                 name_width: int, price_width: int, pay_once_width: int):
        self.activity_manager = activity_manager
        self.opened_now: ActivityRow | None = None

        self.activity_list = activity_list
        self.name_width = name_width
        self.price_width = price_width
        self.pay_once_width = pay_once_width

        for activity in self.activity_manager.activities():
            self._add_activity(activity)

    def _add_activity(self, activity: Activity):
        item = QListWidgetItem(self.activity_list)
        self.activity_list.addItem(item)
        row = ActivityRow(activity, self.activity_manager, item, self, self.name_width, self.price_width,
                          self.pay_once_width, height=50)
        self.activity_list.setItemWidget(item, row)

    def create_activity(self):
        self.add_ui = CreateUI(self.activity_manager)
        self.add_ui.exec_()
        if self.add_ui.controller.activity is not None:
            self._add_activity(self.add_ui.controller.activity)


class ActivityMainUI(QMainWindow):

    def __init__(self, activity_manager: ActivityManager) -> None:
        super().__init__(parent=None)
        name_width, price_width, pay_once_width = 175, 90, 100
        self._setup_ui(name_width, price_width, pay_once_width)
        self.controller = Controller(activity_manager, self.activity_list, name_width, price_width, pay_once_width)

        self.create_client_btn.clicked.connect(self.controller.create_activity)

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
