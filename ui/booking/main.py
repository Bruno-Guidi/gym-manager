from __future__ import annotations

from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem,
    QSizePolicy, QTableWidget, QMenuBar, QAction, QTableWidgetItem, QDateEdit, QMenu, QDialog, QGridLayout, QLabel,
    QComboBox, QCheckBox)

from gym_manager.booking.core import (
    BookingSystem, TempBooking, BOOKING_TO_HAPPEN, BOOKING_PAID, ONE_DAY_TD,
    remaining_blocks, Booking)
from gym_manager.core import constants
from gym_manager.core.base import DateGreater, DateLesser, ClientLike, NumberEqual, String, TextLike
from gym_manager.core.persistence import ClientRepo, FilterValuePair
from ui.booking.operations import BookUI, CancelUI, PreChargeUI
from ui.widget_config import (
    config_layout, config_btn, config_table, config_date_edit, fill_cell, config_lbl,
    config_combobox, config_checkbox, config_line, fill_combobox)
from ui.widgets import FilterHeader, PageIndex, Field, Dialog


class MainController:

    def __init__(
            self, main_ui: BookingMainUI, client_repo: ClientRepo, transaction_repo: TransactionRepo,
            booking_system: BookingSystem
    ) -> None:
        self.main_ui = main_ui
        self.client_repo = client_repo
        self.transaction_repo = transaction_repo
        self.booking_system = booking_system
        self._courts = {name: number + 1 for number, name in enumerate(booking_system.court_names)}

        self.load_bookings()

        # noinspection PyUnresolvedReferences
        self.main_ui.date_edit.dateChanged.connect(self.load_bookings)
        # noinspection PyUnresolvedReferences
        self.main_ui.create_btn.clicked.connect(self.create_booking)

    def _load_booking(
            self, booking: Booking, start: int | None = None, end: int | None = None
    ):
        if start is None or end is None:
            start, end = self.booking_system.block_range(booking.start, booking.end)

        item = QTableWidgetItem(f"{booking.client.name}{' (Fijo)' if booking.is_fixed else ''}"
                                f"{' (Pago)' if booking.was_paid() else ''}")
        item.setTextAlignment(Qt.AlignCenter)
        self.main_ui.booking_table.setItem(start, self._courts[booking.court], item)
        self.main_ui.booking_table.setSpan(start, self._courts[booking.court], end - start, 1)

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
        for booking, start, end in self.booking_system.bookings(self.main_ui.date_edit.date().toPyDate()):
            self._load_booking(booking, start, end)

    def next_page(self):
        # The load_bookings(args) method is executed as a callback when the date_edit date changes.
        self.main_ui.date_edit.setDate(self.main_ui.date_edit.date().toPyDate() + ONE_DAY_TD)

    def prev_page(self):
        # The load_bookings(args) method is executed as a callback when the date_edit date changes.
        self.main_ui.date_edit.setDate(self.main_ui.date_edit.date().toPyDate() - ONE_DAY_TD)

    def create_booking(self):
        # noinspection PyAttributeOutsideInit
        self._create_ui = CreateUI(self.client_repo, self.booking_system, self.main_ui.date_edit.date().toPyDate())
        self._create_ui.exec_()
        if self._create_ui.controller.booking is not None:
            self._load_booking(self._create_ui.controller.booking)

    def cancel_ui(self):
        # noinspection PyAttributeOutsideInit
        pass
        # self._cancel_ui = CancelUI(self.booking_system)
        # self._cancel_ui.exec_()
        # removed = self._cancel_ui.controller.booking
        # if removed is not None:
        #     start, end = self.booking_system.block_range(removed.start, removed.end)
        #     self.main_ui.booking_table.takeItem(start, removed.court.id)
        #     for i in range(start, end):  # Undo the spanning.
        #         self.main_ui.booking_table.setSpan(i, removed.court.id, 1, 1)

    def charge_ui(self):
        # noinspection PyAttributeOutsideInit
        pass
        # self._precharge_ui = PreChargeUI(self.booking_system, self.accounting_system)
        # self._precharge_ui.exec_()
        # charged = self._precharge_ui.controller.booking
        # if charged is not None:
        #     start, end = self.booking_system.block_range(charged.start, charged.end)
        #     self.main_ui.booking_table.item(start, charged.court.id
        #                                     ).setFont(self._cell_font(is_paid=charged.transaction is not None))

    def history_ui(self):
        # noinspection PyAttributeOutsideInit
        pass
        # self._history_ui = HistoryUI(self.booking_system)
        # self._history_ui.setWindowModality(Qt.ApplicationModal)
        # self._history_ui.show()


class BookingMainUI(QMainWindow):

    def __init__(
            self, client_repo: ClientRepo, transaction_repo: TransactionRepo, booking_system: BookingSystem
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, client_repo, transaction_repo, booking_system)

    def _setup_ui(self):
        self.setWindowTitle("Padel")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)

        self.charge_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.charge_btn)
        config_btn(self.charge_btn, "Cobrar turno", font_size=16)

        self.create_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.create_btn)
        config_btn(self.create_btn, "Reservar turno", font_size=16)

        self.cancel_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.cancel_btn)
        config_btn(self.cancel_btn, "Cancelar turno", font_size=16)

        self.history_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.history_btn)
        config_btn(self.history_btn, "Ver cancelados", font_size=16)

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


class CreateController:

    def __init__(self, create_ui: CreateUI, client_repo: ClientRepo, booking_system: BookingSystem, when: date) -> None:
        self.create_ui = create_ui
        self.client_repo = client_repo
        self.booking_system = booking_system
        self.when = when
        self.booking: Booking | None = None

        # Fills some widgets that depend on user/system data.
        config_date_edit(self.create_ui.date_edit, when, calendar=False, enabled=False)
        fill_combobox(self.create_ui.court_combobox, self.booking_system.court_names, lambda court: court)
        fill_combobox(self.create_ui.block_combobox, remaining_blocks(self.booking_system.blocks(), when),
                      lambda block: str(block.start))
        fill_combobox(self.create_ui.duration_combobox, self.booking_system.durations, lambda duration: duration.as_str)

        # Configs the widgets so they have the same width.
        config_combobox(self.create_ui.block_combobox)
        config_combobox(self.create_ui.court_combobox, fixed_width=self.create_ui.block_combobox.width())
        config_combobox(self.create_ui.duration_combobox, fixed_width=self.create_ui.block_combobox.width())

        # Configure the filtering widget.
        filters = (TextLike("client_name", display_name="Nombre cliente", attr="name",
                            translate_fun=lambda client, value: client.cli_name.contains(value)),
                   NumberEqual("client_dni", display_name="DNI cliente", attr="dni",
                               translate_fun=lambda client, value: client.dni == value))
        self.create_ui.filter_header.config(filters, self.fill_client_combobox, allow_empty_filter=False)

        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_booking)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    def fill_client_combobox(self, filters: list[FilterValuePair]):
        fill_combobox(self.create_ui.client_combobox,
                      self.client_repo.all(page=1, filters=filters),
                      lambda client: client.name.as_primitive())

    def create_booking(self):
        client = self.create_ui.client_combobox.currentData(Qt.UserRole)
        court = self.create_ui.court_combobox.currentData(Qt.UserRole)
        start_block = self.create_ui.block_combobox.currentData(Qt.UserRole)
        duration = self.create_ui.duration_combobox.currentData(Qt.UserRole)

        if client is None:
            Dialog.info("Error", "Seleccione un cliente.")
        elif not self.create_ui.responsible_field.valid_value():
            Dialog.info("Error", "El campo 'Responsable' no es válido.")
        elif self.booking_system.out_of_range(start_block.start, duration):
            Dialog.info("Error", f"El turno debe ser entre las '{self.booking_system.start}' y las "
                                 f"'{self.booking_system.end}'.")
        elif not self.booking_system.booking_available(self.when, court, start_block.start, duration,
                                                       self.create_ui.fixed_checkbox.isChecked()):
            Dialog.info("Error", "El horario solicitado se encuentra ocupado.")
        else:
            responsible = self.create_ui.responsible_field.value()
            self.booking = self.booking_system.book(court, client, self.create_ui.fixed_checkbox.isChecked(), self.when,
                                                    start_block.start, duration)
            Dialog.info("Éxito", "El turno ha sido reservado correctamente.")
            self.create_ui.client_combobox.window().close()


class CreateUI(QDialog):

    def __init__(self, client_repo: ClientRepo, booking_system: BookingSystem, when: date) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, client_repo, booking_system, when)

    def _setup_ui(self):
        self.setWindowTitle("Reservar turno")
        self.layout = QVBoxLayout(self)

        # Filtering.
        self.filter_header = FilterHeader(show_clear_button=False)
        self.layout.addWidget(self.filter_header)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        self.client_lbl = QLabel(self)
        self.form_layout.addWidget(self.client_lbl, 0, 0)
        config_lbl(self.client_lbl, "Cliente*")

        self.client_combobox = QComboBox(self)
        self.form_layout.addWidget(self.client_combobox, 0, 1)
        config_combobox(self.client_combobox, fixed_width=200)

        self.date_lbl = QLabel(self)
        self.form_layout.addWidget(self.date_lbl, 1, 0)
        config_lbl(self.date_lbl, "Fecha")

        self.date_edit = QDateEdit(self)  # Configured in CreateController.
        self.form_layout.addWidget(self.date_edit, 1, 1)

        self.court_lbl = QLabel(self)
        self.form_layout.addWidget(self.court_lbl, 2, 0)
        config_lbl(self.court_lbl, "Cancha")

        self.court_combobox = QComboBox(self)  # The configuration is done in _fill_block_combobox.
        self.form_layout.addWidget(self.court_combobox, 2, 1)

        self.hour_lbl = QLabel(self)
        self.form_layout.addWidget(self.hour_lbl, 3, 0)
        config_lbl(self.hour_lbl, "Hora")

        self.block_combobox = QComboBox(self)  # The configuration is done in _fill_block_combobox.
        self.form_layout.addWidget(self.block_combobox, 3, 1)

        self.duration_lbl = QLabel(self)
        self.form_layout.addWidget(self.duration_lbl, 4, 0)
        config_lbl(self.duration_lbl, "Duración")

        self.duration_combobox = QComboBox(self)  # The configuration is done in _fill_block_combobox.
        self.form_layout.addWidget(self.duration_combobox, 4, 1)

        # Responsible.
        self.responsible_lbl = QLabel(self)
        self.form_layout.addWidget(self.responsible_lbl, 5, 0)
        config_lbl(self.responsible_lbl, "Responsable*")

        self.responsible_field = Field(String, parent=self, max_len=constants.CLIENT_NAME_CHARS)
        self.form_layout.addWidget(self.responsible_field, 5, 1)
        config_line(self.responsible_field)

        self.fixed_lbl = QLabel(self)
        self.form_layout.addWidget(self.fixed_lbl, 6, 0)
        config_lbl(self.fixed_lbl, "Turno fijo")

        self.fixed_checkbox = QCheckBox(self)
        self.form_layout.addWidget(self.fixed_checkbox, 6, 1)
        config_checkbox(self.fixed_checkbox)

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


# class HistoryController:
#
#     def __init__(self, history_ui: HistoryUI, booking_system: BookingSystem) -> None:
#         self.booking_system = booking_system
#         self.history_ui = history_ui
#         self.current_page, self.page_len = 1, 20
#
#         # Configure the filtering widget.
#         filters = (ClientLike("client_name", display_name="Nombre cliente",
#                               translate_fun=lambda trans, value: trans.client.cli_name.contains(value)),
#                    NumberEqual("client_dni", display_name="DNI cliente", attr="dni",
#                                translate_fun=lambda trans, value: trans.client.dni == value))
#         date_greater_filter = DateGreater("from", display_name="Desde", attr="when",
#                                           translate_fun=lambda trans, when: trans.when >= when)
#         date_lesser_filter = DateLesser("to", display_name="Hasta", attr="when",
#                                         translate_fun=lambda trans, when: trans.when <= when)
#         self.history_ui.filter_header.config(filters, self.fill_booking_table, date_greater_filter, date_lesser_filter)
#
#         # Configures the page index.
#         self.history_ui.page_index.config(refresh_table=self.history_ui.filter_header.on_search_click,
#                                           page_len=10, total_len=self.booking_system.repo.count())
#
#         # Fills the table.
#         self.history_ui.filter_header.on_search_click()
#
#     def fill_booking_table(self, filters: list[FilterValuePair]):
#         self.history_ui.booking_table.setRowCount(0)
#
#         self.history_ui.page_index.total_len = self.booking_system.repo.count(filters)
#         for row, booking in enumerate(self.booking_system.repo.all(filters=filters)):
#             self.history_ui.booking_table.setRowCount(row + 1)
#             fill_cell(self.history_ui.booking_table, row, 0, booking.when.strftime(constants.DATE_FORMAT), int)
#             fill_cell(self.history_ui.booking_table, row, 1, booking.court.name, str)
#             fill_cell(self.history_ui.booking_table, row, 2, booking.start.strftime('%H:%M'), int)
#             fill_cell(self.history_ui.booking_table, row, 3, booking.end.strftime('%H:%M'), int)
#             fill_cell(self.history_ui.booking_table, row, 4, booking.client.name, str)
#             fill_cell(self.history_ui.booking_table, row, 5, booking.state.updated_by, str)
#             fill_cell(self.history_ui.booking_table, row, 6, booking.state.name, str)
#
#
# class HistoryUI(QMainWindow):
#
#     def __init__(self, booking_system: BookingSystem) -> None:
#         super().__init__()
#         self._setup_ui()
#         self.controller = HistoryController(self, booking_system)
#
#     def _setup_ui(self):
#         self.setWindowTitle("Historial de turnos")
#         self.widget = QWidget()
#         self.setCentralWidget(self.widget)
#         self.layout = QVBoxLayout(self.widget)
#
#         # Filtering.
#         self.filter_header = FilterHeader(date_greater_filtering=True, date_lesser_filtering=True, parent=self.widget)
#         self.layout.addWidget(self.filter_header)
#
#         # Bookings.
#         self.booking_table = QTableWidget(self.widget)
#         self.layout.addWidget(self.booking_table)
#         config_table(
#             target=self.booking_table, allow_resizing=True, min_rows_to_show=10,
#             columns={"Fecha": (10, str), "Cancha": (12, str), "Inicio": (6, int), "Fin": (6, int),
#                      "Cliente": (constants.CLIENT_NAME_CHARS // 2, str),
#                      "Responsable": (constants.CLIENT_NAME_CHARS // 2, str),
#                      "Estado": (10, str)}
#         )
#
#         # Index.
#         self.page_index = PageIndex(self)
#         self.layout.addWidget(self.page_index)
#
#         # Adjusts size.
#         self.setMaximumWidth(self.widget.sizeHint().width())
