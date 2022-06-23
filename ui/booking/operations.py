from __future__ import annotations

from datetime import date

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox, \
    QCheckBox, QPushButton, QDialog, QDateEdit

from gym_manager.booking.core import BookingSystem
from gym_manager.core.base import String
from ui.widget_config import config_layout, config_lbl, config_line, config_combobox, config_btn, config_checkbox, \
    fill_combobox, config_date_edit
from ui.widgets import Field


class Controller:

    def __init__(self, booking_system: BookingSystem, book_ui: BookUI) -> None:
        self.booking_system = booking_system
        self.book_ui = book_ui

        fill_combobox(book_ui.court_combobox, self.booking_system.courts(), lambda court_name: court_name)
        fill_combobox(book_ui.hour_combobox, self.booking_system.blocks(), lambda block: str(block.start))
        fill_combobox(book_ui.duration_combobox, self.booking_system.durations, lambda duration: duration.as_str)


class BookUI(QDialog):

    def __init__(self, booking_system: BookingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(booking_system, self)

    def _setup_ui(self):
        width, height = 600, 400
        self.resize(width, height)

        self.central_widget = QWidget(self)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, width, height))
        self.layout = QVBoxLayout(self.widget)
        config_layout(self.layout, left_margin=30, top_margin=10, right_margin=30, bottom_margin=10, spacing=20)

        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        config_layout(self.form_layout, spacing=10)

        self.client_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.client_lbl, 0, 0, 1, 1)
        config_lbl(self.client_lbl, "Cliente")

        self.client_field = Field(validatable=String, max_len=5)
        self.form_layout.addWidget(self.client_field, 0, 1, 1, 1)
        config_line(self.client_field, height=35)

        self.court_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.court_lbl, 1, 0, 1, 1)
        config_lbl(self.court_lbl, "Cancha")

        self.court_combobox = QComboBox(self.widget)
        self.form_layout.addWidget(self.court_combobox, 1, 1, 1, 1)
        config_combobox(self.court_combobox, height=35)

        self.date_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.date_lbl, 2, 0, 1, 1)
        config_lbl(self.date_lbl, "Fecha")

        self.date_edit = QDateEdit(self.widget)
        self.form_layout.addWidget(self.date_edit, 2, 1, 1, 1)
        config_date_edit(self.date_edit, date.today(), height=35)

        self.hour_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.hour_lbl, 3, 0, 1, 1)
        config_lbl(self.hour_lbl, "Hora")

        self.hour_combobox = QComboBox(self.widget)
        self.form_layout.addWidget(self.hour_combobox, 3, 1, 1, 1)
        config_combobox(self.hour_combobox, height=35)

        self.duration_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.duration_lbl, 4, 0, 1, 1)
        config_lbl(self.duration_lbl, "Duración")

        self.duration_combobox = QComboBox(self.widget)
        self.form_layout.addWidget(self.duration_combobox, 4, 1, 1, 1)
        config_combobox(self.duration_combobox, height=35)

        self.fixed_checkbox = QCheckBox()
        self.layout.addWidget(self.fixed_checkbox, alignment=Qt.AlignCenter)
        config_checkbox(self.fixed_checkbox, checked=False, text="Turno fijo")

        self.confirm_btn = QPushButton(self.widget)
        self.layout.addWidget(self.confirm_btn, alignment=Qt.AlignCenter)
        config_btn(self.confirm_btn, "Confirmar", font_size=18, width=200)
