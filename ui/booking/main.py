from __future__ import annotations

from datetime import timedelta, date

from PyQt5 import QtCore
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QCalendarWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, \
    QSizePolicy, QLabel, QTableWidget, QMenuBar, QStatusBar, QAction, QTableWidgetItem, QDateEdit

from gym_manager.booking.core import BookingSystem
from ui.booking.operations import BookUI
from ui.widget_config import config_layout, config_btn, config_lbl, config_table, config_date_edit


class Controller:

    def __init__(self, booking_system: BookingSystem, main_ui: BookingMainUI) -> None:
        self.booking_system = booking_system
        self.main_ui = main_ui

    def load_bookings(self):
        for booking, start, end in self.booking_system.bookings(self.main_ui.date_field.date().toPyDate()):
            print(booking.when, booking.start, booking.end)

    def book_ui(self):
        self._book_ui = BookUI(self.booking_system)
        self._book_ui.exec_()


class BookingMainUI(QMainWindow):

    def __init__(self, booking_system: BookingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(booking_system, self)
        self.book_btn.clicked.connect(self.controller.book_ui)

    def _setup_ui(self):
        width, height = 800, 600
        self.resize(width, height)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.menu_bar.setGeometry(QtCore.QRect(0, 0, width, 20))
        height -= 20

        self.booking_menu = self.menu_bar.addMenu("Turnos")
        self.see_history_action = QAction("Historial", self)
        self.booking_menu.addAction(self.see_history_action)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, width, height))
        self.vbox = QVBoxLayout(self.widget)
        config_layout(self.vbox, left_margin=10, top_margin=10, right_margin=10, bottom_margin=10, spacing=10)

        self.buttons_hbox = QHBoxLayout()
        self.vbox.addLayout(self.buttons_hbox)
        config_layout(self.buttons_hbox, spacing=50)

        self.charge_button = QPushButton(self.widget)
        self.buttons_hbox.addWidget(self.charge_button)
        config_btn(self.charge_button, "Cobrar turno", font_size=18, width=200)

        self.book_btn = QPushButton(self.widget)
        self.buttons_hbox.addWidget(self.book_btn)
        config_btn(self.book_btn, "Reservar turno", font_size=18, width=200)

        self.cancel_button = QPushButton(self.widget)
        self.buttons_hbox.addWidget(self.cancel_button)
        config_btn(self.cancel_button, "Cancelar turno", font_size=18, width=200)

        self.spacer_item = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.vbox.addItem(self.spacer_item)

        self.date_hbox = QHBoxLayout()
        self.vbox.addLayout(self.date_hbox)
        config_layout(self.date_hbox)

        self.prev_button = QPushButton(self.widget)
        self.date_hbox.addWidget(self.prev_button)
        config_btn(self.prev_button, "<", width=30)

        self.date_field = QDateEdit(self.widget)
        self.date_hbox.addWidget(self.date_field)
        config_date_edit(self.date_field, date.today(), font_size=18, layout_direction=Qt.RightToLeft)

        self.next_button = QPushButton(self.widget)
        self.date_hbox.addWidget(self.next_button)
        config_btn(self.next_button, ">", width=30)

        self.bookings = QTableWidget(self.widget)
        self.vbox.addWidget(self.bookings)

        # height() returns the width of the scrollbar.
        column_len = (width - self.bookings.verticalScrollBar().height() - 135) // 3
        config_table(
            target=self.bookings,
            columns={"Hora": 126, "Cancha 1": column_len, "Cancha 2": column_len, "Cancha 3 (Singles)": column_len}
        )
