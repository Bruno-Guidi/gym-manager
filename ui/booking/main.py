from __future__ import annotations

from datetime import date

from PyQt5 import QtCore
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, \
    QSizePolicy, QTableWidget, QMenuBar, QAction, QTableWidgetItem, QDateEdit, QLabel

from gym_manager.booking.core import BookingSystem, Booking, BOOKING_TO_HAPPEN, BOOKING_PAID, BOOKING_CANCELLED
from gym_manager.core.base import DateGreater, DateLesser, ClientLike, ONE_MONTH_TD
from gym_manager.core.persistence import ClientRepo
from gym_manager.core.system import AccountingSystem
from ui.booking.operations import BookUI, CancelUI, PreChargeUI
from ui.widget_config import config_layout, config_btn, config_table, config_date_edit, config_lbl
from ui.widgets import SearchBox


class Controller:

    def __init__(
            self, main_ui: BookingMainUI, client_repo: ClientRepo, booking_system: BookingSystem,
            accounting_system: AccountingSystem
    ) -> None:
        self.client_repo = client_repo
        self.booking_system = booking_system
        self.accounting_system = accounting_system
        self.main_ui = main_ui

        self.load_bookings()

        # noinspection PyUnresolvedReferences
        self.main_ui.cancel_button.clicked.connect(self.cancel_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.see_history_action.triggered.connect(self.history_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.book_btn.clicked.connect(self.book_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.charge_btn.clicked.connect(self.charge_ui)

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
        for booking, start, end in self.booking_system.bookings((BOOKING_TO_HAPPEN, BOOKING_PAID),
                                                                self.main_ui.date_field.date().toPyDate()):
            self._load_booking(booking, start, end)

    def book_ui(self):
        # noinspection PyAttributeOutsideInit
        self._book_ui = BookUI(self.client_repo, self.booking_system)
        self._book_ui.exec_()
        if self._book_ui.controller.booking is not None:
            self._load_booking(self._book_ui.controller.booking)

    def cancel_ui(self):
        # noinspection PyAttributeOutsideInit
        self._cancel_ui = CancelUI(self.booking_system)
        self._cancel_ui.exec_()
        removed = self._cancel_ui.controller.booking
        if removed is not None:
            start, end = self.booking_system.block_range(removed.start, removed.end)
            self.main_ui.booking_table.takeItem(start, removed.court.id)
            for i in range(start, end):  # Undo the spanning.
                self.main_ui.booking_table.setSpan(i, removed.court.id, 1, 1)

    def charge_ui(self):
        # noinspection PyAttributeOutsideInit
        self._precharge_ui = PreChargeUI(self.booking_system, self.accounting_system)
        self._precharge_ui.exec_()

    def history_ui(self):
        # noinspection PyAttributeOutsideInit
        self._history_ui = HistoryUI(self.booking_system)
        self._history_ui.setWindowModality(Qt.ApplicationModal)
        self._history_ui.show()


class BookingMainUI(QMainWindow):

    def __init__(
            self, client_repo: ClientRepo, booking_system: BookingSystem, accounting_system: AccountingSystem
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(self, client_repo, booking_system, accounting_system)

    def _setup_ui(self):
        width, height = 800, 600
        self.resize(width, height)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.menu_bar.setGeometry(QtCore.QRect(0, 0, 800, 20))
        self.see_history_action = QAction("Historial", self)
        self.menu_bar.addAction(self.see_history_action)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, width, height))
        self.layout = QVBoxLayout(self.widget)
        config_layout(self.layout, left_margin=10, top_margin=10, right_margin=10, bottom_margin=10, spacing=10)

        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)
        config_layout(self.buttons_layout, spacing=50)

        self.charge_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.charge_btn)
        config_btn(self.charge_btn, "Cobrar turno", font_size=18, width=200)

        self.book_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.book_btn)
        config_btn(self.book_btn, "Reservar turno", font_size=18, width=200)

        self.cancel_button = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.cancel_button)
        config_btn(self.cancel_button, "Cancelar turno", font_size=18, width=200)

        self.spacer_item = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(self.spacer_item)

        self.date_layout = QHBoxLayout()
        self.layout.addLayout(self.date_layout)
        config_layout(self.date_layout)

        self.prev_button = QPushButton(self.widget)
        self.date_layout.addWidget(self.prev_button)
        config_btn(self.prev_button, "<", width=30)

        self.date_field = QDateEdit(self.widget)
        self.date_layout.addWidget(self.date_field)
        config_date_edit(self.date_field, date.today(), font_size=18, layout_direction=Qt.RightToLeft)

        self.next_button = QPushButton(self.widget)
        self.date_layout.addWidget(self.next_button)
        config_btn(self.next_button, ">", width=30)

        self.booking_table = QTableWidget(self.widget)
        self.layout.addWidget(self.booking_table)

        # height() returns the width of the scrollbar.
        column_len = (width - self.booking_table.verticalScrollBar().height() - 135) // 3
        config_table(
            target=self.booking_table,
            columns={"Hora": 126, "Cancha 1": column_len, "Cancha 2": column_len, "Cancha 3 (Singles)": column_len}
        )


class HistoryController:

    def __init__(self, history_ui: HistoryUI, booking_system: BookingSystem) -> None:
        self.booking_system = booking_system
        self.history_ui = history_ui
        self.current_page, self.page_len = 1, 20

        self.load_bookings()

        # noinspection PyUnresolvedReferences
        self.history_ui.search_btn.clicked.connect(self.load_bookings)

    def load_bookings(self):
        self.history_ui.booking_table.setRowCount(0)
        self.history_ui.booking_table.setRowCount(self.page_len)

        from_date_filter = DateGreater("from", display_name="Desde",
                                       translate_fun=lambda trans, when: trans.when >= when)
        to_date_filter = DateLesser("to", display_name="Hasta",
                                    translate_fun=lambda trans, when: trans.when <= when)
        bookings = self.booking_system.bookings(
            (BOOKING_CANCELLED, BOOKING_PAID),
            from_date=(from_date_filter, self.history_ui.from_date_edit.date().toPyDate()),
            to_date=(to_date_filter, self.history_ui.to_date_edit.date().toPyDate()),
            **self.history_ui.search_box.filters()
        )
        for row, (booking, _, _) in enumerate(bookings):
            print(row, booking.client.name)
            # self.transaction_table.setItem(row, 0, QTableWidgetItem(str(transaction.id)))
            # self.transaction_table.setItem(row, 1, QTableWidgetItem(str(transaction.type)))
            # self.transaction_table.setItem(row, 2, QTableWidgetItem(str(transaction.client.name)))
            # self.transaction_table.setItem(row, 3, QTableWidgetItem(str(transaction.when)))
            # self.transaction_table.setItem(row, 4, QTableWidgetItem(str(transaction.amount)))
            # self.transaction_table.setItem(row, 5, QTableWidgetItem(str(transaction.method)))
            # self.transaction_table.setItem(row, 6, QTableWidgetItem(str(transaction.responsible)))
            # self.transaction_table.setItem(row, 7, QTableWidgetItem(str(transaction.description)))


class HistoryUI(QMainWindow):

    def __init__(self, booking_system: BookingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = HistoryController(self, booking_system)

    def _setup_ui(self):
        self.resize(800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, 800, 600))

        self.layout = QVBoxLayout(self.widget)
        config_layout(self.layout, left_margin=10, top_margin=10, right_margin=10, bottom_margin=10)

        # Utilities.
        self.utils_layout = QHBoxLayout()
        self.layout.addLayout(self.utils_layout)
        config_layout(self.utils_layout, spacing=0, left_margin=40, top_margin=15, right_margin=40)

        self.search_box = SearchBox(
            filters=[ClientLike("client", display_name="Cliente",
                                translate_fun=lambda booking, value: booking.client.cli_name.contains(value))],
            parent=self.widget
        )
        self.utils_layout.addWidget(self.search_box)

        self.utils_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.from_layout = QVBoxLayout()
        self.utils_layout.addLayout(self.from_layout)

        self.from_lbl = QLabel()
        self.from_layout.addWidget(self.from_lbl)
        config_lbl(self.from_lbl, "Desde", font_size=16, alignment=Qt.AlignCenter)

        self.from_date_edit = QDateEdit()
        self.from_layout.addWidget(self.from_date_edit)
        config_date_edit(self.from_date_edit, date.today() - ONE_MONTH_TD, calendar=True,
                         layout_direction=Qt.LayoutDirection.RightToLeft)

        self.utils_layout.addItem(QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.to_layout = QVBoxLayout()
        self.utils_layout.addLayout(self.to_layout)

        self.to_lbl = QLabel()
        self.to_layout.addWidget(self.to_lbl)
        config_lbl(self.to_lbl, "Hasta", font_size=16, alignment=Qt.AlignCenter)

        self.to_date_edit = QDateEdit()
        self.to_layout.addWidget(self.to_date_edit)
        config_date_edit(self.to_date_edit, date.today(), calendar=True,
                         layout_direction=Qt.LayoutDirection.RightToLeft)

        self.utils_layout.addItem(QSpacerItem(30, 20, QSizePolicy.Minimum, QSizePolicy.Minimum))

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "Busq", font_size=16)

        # Bookings.
        self.booking_table = QTableWidget(self.widget)
        self.layout.addWidget(self.booking_table)
        config_table(
            target=self.booking_table, allow_resizing=True,
            columns={"#": 100, "Tipo": 70, "Cliente": 175, "Fecha": 100, "Monto": 100, "Método": 120,
                     "Responsable": 175,
                     "Descripción": 200}
        )

        # Index.
        self.index_layout = QHBoxLayout()
        self.layout.addLayout(self.index_layout)
        config_layout(self.index_layout, left_margin=100, right_margin=100)

        self.prev_btn = QPushButton(self.widget)
        self.index_layout.addWidget(self.prev_btn)
        config_btn(self.prev_btn, "<", font_size=18, width=30)

        self.index_lbl = QLabel(self.widget)
        self.index_layout.addWidget(self.index_lbl)
        config_lbl(self.index_lbl, "#", font_size=18)

        self.next_btn = QPushButton(self.widget)
        self.index_layout.addWidget(self.next_btn)
        config_btn(self.next_btn, ">", font_size=18, width=30)
