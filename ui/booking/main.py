from __future__ import annotations

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem,
    QSizePolicy, QTableWidget, QMenuBar, QAction, QTableWidgetItem, QDateEdit, QMenu)

from gym_manager.booking.core import BookingSystem, Booking, BOOKING_TO_HAPPEN, BOOKING_PAID, ONE_DAY_TD
from gym_manager.core import constants
from gym_manager.core.base import DateGreater, DateLesser, ClientLike, NumberEqual
from gym_manager.core.persistence import ClientRepo, FilterValuePair
from gym_manager.core.system import AccountingSystem
from ui.booking.operations import BookUI, CancelUI, PreChargeUI
from ui.widget_config import config_layout, config_btn, config_table, config_date_edit, fill_cell
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
        self.main_ui.cancel_btn.clicked.connect(self.cancel_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.see_history_action.triggered.connect(self.history_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.book_btn.clicked.connect(self.book_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.charge_btn.clicked.connect(self.charge_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.prev_btn.clicked.connect(self.prev_page)
        # noinspection PyUnresolvedReferences
        self.main_ui.date_edit.dateChanged.connect(self.load_bookings)
        # noinspection PyUnresolvedReferences
        self.main_ui.next_btn.clicked.connect(self.next_page)

    def _cell_font(self, is_paid: bool) -> QFont:
        default_font = self.main_ui.booking_table.font()
        new_font = QFont(default_font)
        if is_paid:
            new_font.setUnderline(True)
        return new_font

    def _load_booking(
            self, booking: Booking, start: int | None = None, end: int | None = None
    ):
        if start is None or end is None:
            start, end = self.booking_system.block_range(booking.start, booking.end)

        item = QTableWidgetItem(f"{booking.client.name}{' (Fijo)' if booking.is_fixed else ''}")
        item.setTextAlignment(Qt.AlignCenter)
        item.setFont(self._cell_font(is_paid=booking.transaction is not None))
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
                                                                self.main_ui.date_edit.date().toPyDate()):
            self._load_booking(booking, start, end)

    def next_page(self):
        # The load_bookings(args) method is executed as a callback when the date_edit date changes.
        self.main_ui.date_edit.setDate(self.main_ui.date_edit.date().toPyDate() + ONE_DAY_TD)

    def prev_page(self):
        # The load_bookings(args) method is executed as a callback when the date_edit date changes.
        self.main_ui.date_edit.setDate(self.main_ui.date_edit.date().toPyDate() - ONE_DAY_TD)

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
        charged = self._precharge_ui.controller.booking
        if charged is not None:
            start, end = self.booking_system.block_range(charged.start, charged.end)
            self.main_ui.booking_table.item(start, charged.court.id
                                            ).setFont(self._cell_font(is_paid=charged.transaction is not None))

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
        self.setWindowTitle("Turnos")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        # Menu bar.
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        # History menu bar.
        self.history_menu = QMenu("Historial", self)
        self.menu_bar.addMenu(self.history_menu)

        self.see_history_action = QAction("Ver", self)
        self.history_menu.addAction(self.see_history_action)

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)

        self.charge_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.charge_btn)
        config_btn(self.charge_btn, "Cobrar turno", font_size=18)

        self.book_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.book_btn)
        config_btn(self.book_btn, "Reservar turno", font_size=18)

        self.cancel_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.cancel_btn)
        config_btn(self.cancel_btn, "Cancelar turno", font_size=18)

        # Vertical spacer.
        self.spacer_item = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(self.spacer_item)

        # Date index.
        self.date_layout = QHBoxLayout()
        self.layout.addLayout(self.date_layout)
        config_layout(self.date_layout)

        self.prev_btn = QPushButton(self.widget)
        self.date_layout.addWidget(self.prev_btn)
        config_btn(self.prev_btn, icon_path="ui/resources/prev_page.png", icon_size=32)

        self.date_edit = QDateEdit(self.widget)
        self.date_layout.addWidget(self.date_edit)
        config_date_edit(self.date_edit, date.today(), calendar=True)

        self.next_btn = QPushButton(self.widget)
        self.date_layout.addWidget(self.next_btn)
        config_btn(self.next_btn, icon_path="ui/resources/next_page.png", icon_size=32)

        # Booking schedule.
        self.booking_table = QTableWidget(self.widget)
        self.layout.addWidget(self.booking_table)

        config_table(
            target=self.booking_table, min_rows_to_show=10,
            columns={"Hora": (12, bool), "Cancha 1": (16, bool), "Cancha 2": (16, bool),
                     "Cancha 3 (Singles)": (16, bool)}
        )

        # Adjusts size.
        self.setMaximumWidth(self.widget.sizeHint().width())


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
            fill_cell(self.history_ui.booking_table, row, 0, booking.when.strftime(constants.DATE_FORMAT), int)
            fill_cell(self.history_ui.booking_table, row, 1, booking.court.name, str)
            fill_cell(self.history_ui.booking_table, row, 2, booking.start.strftime('%H:%M'), int)
            fill_cell(self.history_ui.booking_table, row, 3, booking.end.strftime('%H:%M'), int)
            fill_cell(self.history_ui.booking_table, row, 4, booking.client.name, str)
            fill_cell(self.history_ui.booking_table, row, 5, booking.state.updated_by, str)
            fill_cell(self.history_ui.booking_table, row, 6, booking.state.name, str)


class HistoryUI(QMainWindow):

    def __init__(self, booking_system: BookingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = HistoryController(self, booking_system)

    def _setup_ui(self):
        self.setWindowTitle("Historial de turnos")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        # Filtering.
        self.filter_header = FilterHeader(date_greater_filtering=True, date_lesser_filtering=True, parent=self.widget)
        self.layout.addWidget(self.filter_header)

        # Bookings.
        self.booking_table = QTableWidget(self.widget)
        self.layout.addWidget(self.booking_table)
        config_table(
            target=self.booking_table, allow_resizing=True, min_rows_to_show=10,
            columns={"Fecha": (10, str), "Cancha": (12, str), "Inicio": (6, int), "Fin": (6, int),
                     "Cliente": (constants.CLIENT_NAME_CHARS // 2, str),
                     "Responsable": (constants.CLIENT_NAME_CHARS // 2, str),
                     "Estado": (10, str)}
        )

        # Index.
        self.page_index = PageIndex(self)
        self.layout.addWidget(self.page_index)

        # Adjusts size.
        self.setMaximumWidth(self.widget.sizeHint().width())
