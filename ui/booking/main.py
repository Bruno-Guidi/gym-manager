from __future__ import annotations

from datetime import date

from PyQt5 import QtCore
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, \
    QSizePolicy, QTableWidget, QMenuBar, QAction, QTableWidgetItem, QDateEdit

from gym_manager.booking.core import BookingSystem, Booking, BOOKING_TO_HAPPEN, BOOKING_PAID, ONE_DAY_TD
from gym_manager.core import constants
from gym_manager.core.base import DateGreater, DateLesser, ClientLike, NumberEqual
from gym_manager.core.persistence import ClientRepo, FilterValuePair
from gym_manager.core.system import AccountingSystem
from ui.booking.operations import BookUI, CancelUI, PreChargeUI
from ui.widget_config import config_layout, config_btn, config_table, config_date_edit
from ui.widgets import FilterHeader, PageIndex


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
        # noinspection PyUnresolvedReferences
        self.main_ui.prev_button.clicked.connect(self.prev_page)
        # noinspection PyUnresolvedReferences
        self.main_ui.date_field.dateChanged.connect(self.load_bookings)
        # noinspection PyUnresolvedReferences
        self.main_ui.next_button.clicked.connect(self.next_page)

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

    def next_page(self):
        # The load_bookings(args) method is executed as a callback when the date_edit date changes.
        self.main_ui.date_field.setDate(self.main_ui.date_field.date().toPyDate() + ONE_DAY_TD)

    def prev_page(self):
        # The load_bookings(args) method is executed as a callback when the date_edit date changes.
        self.main_ui.date_field.setDate(self.main_ui.date_field.date().toPyDate() - ONE_DAY_TD)

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
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        # Menu bar.
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.see_history_action = QAction("Historial", self)
        self.menu_bar.addAction(self.see_history_action)

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)
        # config_layout(self.buttons_layout, spacing=50)

        self.charge_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.charge_btn)
        config_btn(self.charge_btn, "Cobrar turno", font_size=18)

        self.book_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.book_btn)
        config_btn(self.book_btn, "Reservar turno", font_size=18)

        self.cancel_button = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.cancel_button)
        config_btn(self.cancel_button, "Cancelar turno", font_size=18)

        # Vertical spacer.
        self.spacer_item = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(self.spacer_item)

        # Date index.
        self.date_layout = QHBoxLayout()
        self.layout.addLayout(self.date_layout)
        config_layout(self.date_layout)

        self.prev_button = QPushButton(self.widget)
        self.date_layout.addWidget(self.prev_button)
        config_btn(self.prev_button, "<")

        self.date_field = QDateEdit(self.widget)
        self.date_layout.addWidget(self.date_field)
        config_date_edit(self.date_field, date.today(), calendar=True)

        self.next_button = QPushButton(self.widget)
        self.date_layout.addWidget(self.next_button)
        config_btn(self.next_button, ">")

        # Booking schedule.
        self.booking_table = QTableWidget(self.widget)
        self.layout.addWidget(self.booking_table)

        config_table(
            target=self.booking_table,
            columns={"Hora": (12, int), "Cancha 1": (16, int), "Cancha 2": (16, int), "Cancha 3 (Singles)": (16, int)}
        )


class HistoryController:

    def __init__(self, history_ui: HistoryUI, booking_system: BookingSystem) -> None:
        self.booking_system = booking_system
        self.history_ui = history_ui
        self.current_page, self.page_len = 1, 20

        # Configure the filtering widget.
        filters = (ClientLike("client_name", display_name="Nombre cliente",
                              translate_fun=lambda trans, value: trans.client.cli_name.contains(value)),
                   NumberEqual("client_dni", display_name="DNI cliente", attr="dni",
                               translate_fun=lambda trans, value: trans.client.dni == value))
        date_greater_filter = DateGreater("from", display_name="Desde", attr="when",
                                          translate_fun=lambda trans, when: trans.when >= when)
        date_lesser_filter = DateLesser("to", display_name="Hasta", attr="when",
                                        translate_fun=lambda trans, when: trans.when <= when)
        self.history_ui.filter_header.config(filters, self.fill_booking_table, date_greater_filter, date_lesser_filter)

        # Configures the page index.
        self.history_ui.page_index.config(refresh_table=self.history_ui.filter_header.on_search_click,
                                          page_len=10, total_len=self.booking_system.repo.count())

        # Fills the table.
        self.history_ui.filter_header.on_search_click()

    def fill_booking_table(self, filters: list[FilterValuePair]):
        self.history_ui.booking_table.setRowCount(0)

        self.history_ui.page_index.total_len = self.booking_system.repo.count(filters)
        for row, booking in enumerate(self.booking_system.repo.all(filters=filters)):
            self.history_ui.booking_table.setRowCount(row + 1)
            self.history_ui.booking_table.setItem(row, 0, QTableWidgetItem(str(booking.client.name)))
            self.history_ui.booking_table.setItem(row, 1,
                                                  QTableWidgetItem(str(booking.when.strftime(constants.DATE_FORMAT))))
            self.history_ui.booking_table.setItem(row, 2, QTableWidgetItem(str(booking.court.name)))
            self.history_ui.booking_table.setItem(row, 3, QTableWidgetItem(str(booking.start)))
            self.history_ui.booking_table.setItem(row, 4, QTableWidgetItem(str(booking.end)))
            self.history_ui.booking_table.setItem(row, 5, QTableWidgetItem(str(booking.state.name)))
            self.history_ui.booking_table.setItem(row, 6, QTableWidgetItem(str(booking.state.updated_by)))


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

        # Filtering.
        self.filter_header = FilterHeader(date_greater_filtering=True, date_lesser_filtering=True, parent=self.widget)
        self.layout.addWidget(self.filter_header)

        # Bookings.
        self.booking_table = QTableWidget(self.widget)
        self.layout.addWidget(self.booking_table)
        # config_table(
        #     target=self.booking_table, allow_resizing=True,
        #     columns={"Cliente": 175, "Fecha": 100, "Cancha": 100, "Inicio": 120, "Fin": 120, "Estado": 100,
        #              "Responsable": 175}
        # )

        # Index.
        self.page_index = PageIndex(self)
        self.layout.addWidget(self.page_index)
