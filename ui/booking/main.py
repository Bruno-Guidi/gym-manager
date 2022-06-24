from __future__ import annotations

from datetime import date

from PyQt5 import QtCore
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, \
    QSizePolicy, QTableWidget, QMenuBar, QAction, QTableWidgetItem, QDateEdit

from gym_manager.booking.core import BookingSystem, Booking
from gym_manager.core.persistence import ClientRepo
from ui.booking.operations import BookUI, CancelUI
from ui.widget_config import config_layout, config_btn, config_table, config_date_edit


class Controller:

    def __init__(self, client_repo: ClientRepo, booking_system: BookingSystem, main_ui: BookingMainUI) -> None:
        self.client_repo = client_repo
        self.booking_system = booking_system
        self.main_ui = main_ui

        self.load_bookings()

        self.main_ui.cancel_button.clicked.connect(self.cancel_ui)

    def _load_booking(
            self, booking: Booking, start: int | None = None, end: int | None = None
    ):
        if start is None or end is None:
            start, end = self.booking_system.block_range(booking.start, booking.end)

        item = QTableWidgetItem(f"{booking.client.name}{' (Fijo)' if booking.is_fixed else ''}")
        item.setTextAlignment(Qt.AlignCenter)
        self.main_ui.booking_table.setItem(start, booking.court.id, item)
        self.main_ui.booking_table.setSpan(start, booking.court.id, end - start, 1)

    def load_bookings(self):
        self.main_ui.booking_table.setRowCount(0)  # Clears the table.

        # Loads the hour column.
        blocks = [block for block in self.booking_system.blocks()]
        self.main_ui.booking_table.setRowCount(len(blocks))
        for row, block in enumerate(blocks):
            item = QTableWidgetItem(block.str_range)
            item.setTextAlignment(Qt.AlignCenter)
            self.main_ui.booking_table.setItem(row, 0, item)

        # Loads the bookings for the day.
        for booking, start, end in self.booking_system.bookings(self.main_ui.date_field.date().toPyDate()):
            self._load_booking(booking, start, end)

    def book_ui(self):
        self._book_ui = BookUI(self.client_repo, self.booking_system)
        self._book_ui.exec_()
        if self._book_ui.controller.booking is not None:
            self._load_booking(self._book_ui.controller.booking)

    def cancel_ui(self):
        self._cancel_ui = CancelUI(self.booking_system)
        self._cancel_ui.exec_()


class BookingMainUI(QMainWindow):

    def __init__(self, client_repo: ClientRepo, booking_system: BookingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(client_repo, booking_system, self)
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

        self.booking_table = QTableWidget(self.widget)
        self.vbox.addWidget(self.booking_table)

        # height() returns the width of the scrollbar.
        column_len = (width - self.booking_table.verticalScrollBar().height() - 135) // 3
        config_table(
            target=self.booking_table,
            columns={"Hora": 126, "Cancha 1": column_len, "Cancha 2": column_len, "Cancha 3 (Singles)": column_len}
        )
