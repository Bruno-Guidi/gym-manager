from __future__ import annotations

import functools
from datetime import date, datetime, timedelta

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem,
    QSizePolicy, QTableWidget, QTableWidgetItem, QDateEdit, QDialog, QGridLayout, QLabel,
    QComboBox, QCheckBox, QLineEdit, QDesktopWidget)

from gym_manager.booking.core import (
    BookingSystem, ONE_DAY_TD,
    remaining_blocks, Booking, subtract_times)
from gym_manager.core.base import DateGreater, DateLesser, ClientLike, String
from gym_manager.core.persistence import FilterValuePair, TransactionRepo
from gym_manager.core.security import SecurityHandler, SecurityError
from ui import utils
from ui.accounting import ChargeUI
from ui.utils import MESSAGE
from ui.widget_config import (
    config_layout, config_btn, config_date_edit, fill_cell, config_lbl,
    config_combobox, config_checkbox, config_line, fill_combobox, new_config_table)
from ui.widgets import FilterHeader, PageIndex, Dialog, responsible_field, Field

DAYS_NAMES = {0: "Lun", 1: "Mar", 2: "Mie", 3: "Jue", 4: "Vie", 5: "Sab", 6: "Dom"}
MONTH_NAMES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
               9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}


def timedelta_to_duration_str(td: timedelta) -> str:
    hours, minutes = td.seconds // 3600, (td.seconds // 60) % 60
    return f"{hours}h{minutes}m"


class MainController:

    def __init__(
            self, main_ui: BookingMainUI, transaction_repo: TransactionRepo,
            booking_system: BookingSystem, security_handler: SecurityHandler, allow_passed_time_bookings: bool = False
    ) -> None:
        self.main_ui = main_ui
        self.transaction_repo = transaction_repo
        self.booking_system = booking_system
        self.security_handler = security_handler
        self._courts = {name: number + 1 for number, name in enumerate(booking_system.court_names)}
        self._bookings: dict[int, dict[int, Booking]] | None = None

        self.allow_passed_time_bookings = allow_passed_time_bookings

        self.load_bookings()

        # noinspection PyUnresolvedReferences
        self.main_ui.date_edit.dateChanged.connect(self.load_bookings)
        # noinspection PyUnresolvedReferences
        self.main_ui.prev_btn.clicked.connect(self.prev_page)
        # noinspection PyUnresolvedReferences
        self.main_ui.next_btn.clicked.connect(self.next_page)
        # noinspection PyUnresolvedReferences
        self.main_ui.create_btn.clicked.connect(self.create_booking)
        # noinspection PyUnresolvedReferences
        self.main_ui.charge_btn.clicked.connect(self.charge_booking)
        # noinspection PyUnresolvedReferences
        self.main_ui.cancel_btn.clicked.connect(self.cancel_booking)
        # noinspection PyUnresolvedReferences
        self.main_ui.history_btn.clicked.connect(self.cancelled_bookings)

    def _load_booking(
            self, booking: Booking, start: int | None = None, end: int | None = None
    ):
        if start is None or end is None:
            start, end = self.booking_system.block_range(booking.start, booking.end)
        for i in range(start, end):
            item = QTableWidgetItem(
                f"{booking.client_name}{' (Fijo)' if booking.is_fixed else ''}"
                f"{' (Pago)' if booking.was_paid(self.main_ui.date_edit.date().toPyDate()) else ''}"
            )
            item.setTextAlignment(Qt.AlignCenter)
            self.main_ui.booking_table.setItem(i, self._courts[booking.court], item)

            self._bookings[self._courts[booking.court]][i] = booking  # Saves the booking to be used later if needed.

    def load_bookings(self):
        date_ = self.main_ui.date_edit.date().toPyDate()
        config_lbl(self.main_ui.date_lbl, f"{DAYS_NAMES[date_.weekday()]} {date_.day} de {MONTH_NAMES[date_.month]}",
                   font_size=16, alignment=Qt.AlignRight, fixed_width=225)

        self.main_ui.booking_table.setRowCount(0)  # Clears the table.
        self._bookings = {court_number: {} for court_number in self._courts.values()}

        # Loads the hour column.
        blocks = [block for block in self.booking_system.blocks()]
        self.main_ui.booking_table.setRowCount(len(blocks))
        for row, block in enumerate(blocks):
            item = QTableWidgetItem(block.str_range)
            item.setTextAlignment(Qt.AlignCenter)
            self.main_ui.booking_table.setItem(row, 0, item)

        # Loads the bookings for the day.
        for booking, start, end in self.booking_system.bookings(date_):
            self._load_booking(booking, start, end)

    def next_page(self):
        # The load_bookings(args) method is executed as a callback when the date_edit date changes.
        self.main_ui.date_edit.setDate(self.main_ui.date_edit.date().toPyDate() + ONE_DAY_TD)

    def prev_page(self):
        # The load_bookings(args) method is executed as a callback when the date_edit date changes.
        self.main_ui.date_edit.setDate(self.main_ui.date_edit.date().toPyDate() - ONE_DAY_TD)

    def create_booking(self):
        # noinspection PyAttributeOutsideInit
        when = self.main_ui.date_edit.date().toPyDate()
        if not self.allow_passed_time_bookings and when < date.today():
            Dialog.info("Error", "No se puede reservar turnos en un día previo al actual.")
        else:
            # noinspection PyAttributeOutsideInit
            self._create_ui = CreateUI(self.booking_system, self.security_handler, when,
                                       self.allow_passed_time_bookings)
            self._create_ui.exec_()
            if self._create_ui.controller.booking is not None:
                self._load_booking(self._create_ui.controller.booking)

    def charge_booking(self):
        row, col = self.main_ui.booking_table.currentRow(), self.main_ui.booking_table.currentColumn()
        when = self.main_ui.date_edit.date().toPyDate()
        if col not in self._bookings or row not in self._bookings[col]:
            Dialog.info("Error", "No existe un turno en el horario seleccionado.")
            return

        booking = self._bookings[col][row]
        if when > date.today() or (when == datetime.now().date() and booking.start > datetime.now().time()):
            Dialog.info("Error", "No se puede cobrar un turno que todavía no comenzó.")
            return
        if booking.was_paid(when):
            Dialog.info("Error", f"El turno ya fue cobrado.")
            return

        register_booking_charge = functools.partial(self.booking_system.register_charge, booking, when)
        # noinspection PyAttributeOutsideInit
        self._charge_ui = ChargeUI(self.transaction_repo, self.security_handler,
                                   self.booking_system.amount_to_charge(booking),
                                   String(f"Cobro de turno de padel en cancha {booking.court}."),
                                   register_booking_charge)
        self._charge_ui.exec_()
        if self._charge_ui.controller.success:
            text = (f"{booking.client_name}{' (Fijo)' if booking.is_fixed else ''}"
                    f"{' (Pago)' if booking.was_paid(when) else ''}")
            start, end = self.booking_system.block_range(booking.start, booking.end)
            for i in range(start, end):
                self.main_ui.booking_table.item(i, col).setText(text)

    def cancel_booking(self):
        row, col = self.main_ui.booking_table.currentRow(), self.main_ui.booking_table.currentColumn()
        when = self.main_ui.date_edit.date().toPyDate()
        if col not in self._bookings or row not in self._bookings[col]:
            Dialog.info("Error", "No existe un turno en el horario seleccionado.")
            return

        to_cancel = self._bookings[col][row]
        if when < date.today() or (when == datetime.now().date() and to_cancel.start < datetime.now().time()):
            Dialog.info("Error", "No se puede cancelar un turno que ya comenzo.")
        elif to_cancel.was_paid(when):
            Dialog.info("Error", "No se puede cancelar un turno que ya cobrado.")
        else:
            # noinspection PyAttributeOutsideInit
            self._cancel_ui = CancelUI(self.booking_system, self.security_handler, to_cancel, when)
            self._cancel_ui.exec_()
            if self._cancel_ui.controller.cancelled:
                start, end = self.booking_system.block_range(to_cancel.start, to_cancel.end)
                for i in range(start, end):
                    self.main_ui.booking_table.takeItem(i, col)
                    self._bookings[col].pop(i)

    def cancelled_bookings(self):
        # noinspection PyAttributeOutsideInit
        self._history_ui = HistoryUI(self.booking_system)
        self._history_ui.setWindowModality(Qt.ApplicationModal)
        self._history_ui.show()


class BookingMainUI(QMainWindow):

    def __init__(
            self, transaction_repo: TransactionRepo, booking_system: BookingSystem,
            security_handler: SecurityHandler, allow_passed_time_bookings: bool = False
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, transaction_repo, booking_system, security_handler,
                                         allow_passed_time_bookings)

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
        config_btn(self.history_btn, "Ver borrados", font_size=16)

        # Date index.
        self.date_layout = QHBoxLayout()
        self.layout.addLayout(self.date_layout)
        config_layout(self.date_layout)
        self.date_layout.setSpacing(0)

        self.date_lbl = QLabel(self.widget)
        self.date_layout.addWidget(self.date_lbl)

        self.date_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Fixed, QSizePolicy.Fixed))

        self.next_btn = QPushButton(self.widget)
        self.date_layout.addWidget(self.next_btn)
        config_btn(self.next_btn, icon_path="ui/resources/up.png", icon_size=20)

        self.prev_btn = QPushButton(self.widget)
        self.date_layout.addWidget(self.prev_btn)
        config_btn(self.prev_btn, icon_path="ui/resources/down.png", icon_size=20)

        self.date_edit = QDateEdit(self.widget)
        self.date_layout.addWidget(self.date_edit)
        config_date_edit(self.date_edit, date.today(), calendar=True, font_size=16)

        # Booking schedule.
        self.booking_table = QTableWidget(self.widget)
        self.layout.addWidget(self.booking_table)

        new_config_table(self.booking_table, width=1000, select_whole_row=False, font_size=12,
                         columns={"Hora": (.19, bool), "Cancha 1": (.27, bool), "Cancha 2": (.27, bool),
                                  "Cancha 3 (Singles)": (.27, bool)}, min_rows_to_show=24)
        self.booking_table.verticalHeader().setDefaultSectionSize(22)

        # Adjusts size.
        self.setMaximumWidth(self.widget.sizeHint().width())

        self.move(int(QDesktopWidget().geometry().center().x() - self.sizeHint().width() / 2),
                  int(QDesktopWidget().geometry().center().y() - self.sizeHint().height() / 2))


class CreateController:

    def __init__(
            self, create_ui: CreateUI, booking_system: BookingSystem,
            security_handler: SecurityHandler, when: date, allow_passed_time_bookings: bool
    ) -> None:
        self.create_ui = create_ui
        self.booking_system = booking_system
        self.security_handler = security_handler
        self.when = when
        self.booking: Booking | None = None

        # Fills some widgets that depend on user/system data.
        config_date_edit(self.create_ui.date_edit, when, calendar=False, enabled=False)
        fill_combobox(self.create_ui.court_combobox, self.booking_system.court_names, lambda court: court)
        blocks = self.booking_system.blocks()
        if not allow_passed_time_bookings:
            blocks = remaining_blocks(blocks, when)
        fill_combobox(self.create_ui.block_combobox, blocks, display=lambda block: str(block.start))
        # fill_combobox(self.create_ui.duration_combobox, self.booking_system.durations, lambda duration: duration.as_str)

        # Configs the widgets so they have the same width.
        config_combobox(self.create_ui.block_combobox)
        config_combobox(self.create_ui.court_combobox, fixed_width=self.create_ui.block_combobox.width())
        config_combobox(self.create_ui.duration_combobox, fixed_width=self.create_ui.block_combobox.width())

        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_booking)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    def create_booking(self):
        court = self.create_ui.court_combobox.currentData(Qt.UserRole)
        start_block = self.create_ui.block_combobox.currentData(Qt.UserRole)
        duration = self.create_ui.duration_combobox.currentData(Qt.UserRole)

        if not self.create_ui.client_field.valid_value():
            Dialog.info("Error", "El campo Cliente no es válido.")
        elif self.booking_system.out_of_range(start_block.start, duration):
            Dialog.info("Error", f"El turno debe ser entre las '{self.booking_system.start}' y las "
                                 f"'{self.booking_system.end}'.")
        elif not self.booking_system.booking_available(self.when, court, start_block.start, duration,
                                                       self.create_ui.fixed_checkbox.isChecked()):
            Dialog.info("Error", "El horario solicitado se encuentra ocupado.")
        else:
            try:
                self.security_handler.current_responsible = self.create_ui.responsible_field.value()
                # noinspection PyTypeChecker
                self.booking = self.booking_system.book(court, self.create_ui.client_field.value(),
                                                        self.create_ui.fixed_checkbox.isChecked(), self.when,
                                                        start_block.start, duration)
                Dialog.info("Éxito", "El turno ha sido reservado correctamente.")
                self.create_ui.client_field.window().close()
            except SecurityError as sec_err:
                Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))


class CreateUI(QDialog):

    def __init__(
            self, booking_system: BookingSystem, security_handler: SecurityHandler, when: date,
            allow_passed_time_bookings: bool
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, booking_system, security_handler, when,
                                           allow_passed_time_bookings)

    def _setup_ui(self):
        self.setWindowTitle("Reservar turno")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        self.client_lbl = QLabel(self)
        self.form_layout.addWidget(self.client_lbl, 0, 0)
        config_lbl(self.client_lbl, "Cliente*")

        self.client_field = Field(String, parent=self, optional=False)
        self.form_layout.addWidget(self.client_field, 0, 1)
        config_line(self.client_field, place_holder="Cliente")

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
        config_lbl(self.responsible_lbl, "Responsable")

        self.responsible_field = responsible_field(self)
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


class CancelController:

    def __init__(
            self, cancel_ui: CancelUI, booking_system: BookingSystem, security_handler: SecurityHandler,
            to_cancel: Booking, when: date
    ) -> None:
        self.cancel_ui = cancel_ui
        self.booking_system = booking_system
        self.security_handler = security_handler
        self.to_cancel = to_cancel
        self.when = when
        self.cancelled = False

        # Loads booking info.
        self.cancel_ui.client_line.setText(str(to_cancel.client_name.as_primitive()))
        self.cancel_ui.court_line.setText(to_cancel.court)
        self.cancel_ui.date_edit.setDate(when)
        self.cancel_ui.start_line.setText(str(to_cancel.start))
        self.cancel_ui.end_line.setText(str(to_cancel.end))
        self.cancel_ui.fixed_line.setText("Si" if to_cancel.is_fixed else "No")

        # noinspection PyUnresolvedReferences
        self.cancel_ui.confirm_btn.clicked.connect(self.cancel)
        # noinspection PyUnresolvedReferences
        self.cancel_ui.cancel_btn.clicked.connect(self.cancel_ui.reject)

    def cancel(self):
        try:
            self.security_handler.current_responsible = self.cancel_ui.responsible_field.value()
            definitely_cancelled = True
            if self.to_cancel.is_fixed:
                definitely_cancelled = Dialog.confirm("El turno es fijo, ¿Desea cancelarlo definitivamente?",
                                                      ok_btn_text="Si", cancel_btn_text="No")
            # noinspection PyTypeChecker
            self.booking_system.cancel(self.to_cancel, self.security_handler.current_responsible.name, self.when,
                                       definitely_cancelled, datetime.now())
            self.cancelled = True

            if self.to_cancel.is_fixed and definitely_cancelled:
                Dialog.info("Éxito", "El turno fijo ha sido cancelado correctamente.")
            else:
                Dialog.info("Éxito", "El turno ha sido cancelado correctamente.")
            self.cancel_ui.client_line.window().close()
        except SecurityError as sec_err:
            Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))


class CancelUI(QDialog):

    def __init__(
            self, booking_system: BookingSystem, security_handler: SecurityHandler, to_cancel: Booking, when: date
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CancelController(self, booking_system, security_handler, to_cancel, when)

    def _setup_ui(self):
        self.setWindowTitle("Cancelar turno")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Client.
        self.client_lbl = QLabel(self)
        self.form_layout.addWidget(self.client_lbl, 1, 0)
        config_lbl(self.client_lbl, "Cliente")

        self.client_line = QLineEdit(self)
        self.form_layout.addWidget(self.client_line, 1, 1)
        config_line(self.client_line, read_only=True)

        # Booked date.
        self.date_lbl = QLabel(self)
        self.form_layout.addWidget(self.date_lbl, 2, 0)
        config_lbl(self.date_lbl, "Fecha")

        self.date_edit = QDateEdit(self)
        self.form_layout.addWidget(self.date_edit, 2, 1)
        config_date_edit(self.date_edit, date.today(), calendar=False, enabled=False)

        # Booked court.
        self.court_lbl = QLabel(self)
        self.form_layout.addWidget(self.court_lbl, 3, 0)
        config_lbl(self.court_lbl, "Cancha")

        self.court_line = QLineEdit(self)
        self.form_layout.addWidget(self.court_line, 3, 1)
        config_line(self.court_line, "n", enabled=False, fixed_width=self.date_edit.width())

        # Booking start.
        self.start_lbl = QLabel(self)
        self.form_layout.addWidget(self.start_lbl, 4, 0)
        config_lbl(self.start_lbl, "Inicio")

        self.start_line = QLineEdit(self)
        self.form_layout.addWidget(self.start_line, 4, 1)
        config_line(self.start_line, "hh:mm", enabled=False, fixed_width=self.date_edit.width())

        # Booking end.
        self.end_lbl = QLabel(self)
        self.form_layout.addWidget(self.end_lbl, 5, 0)
        config_lbl(self.end_lbl, "Fin")

        self.end_line = QLineEdit(self)
        self.form_layout.addWidget(self.end_line, 5, 1)
        config_line(self.end_line, "hh:mm", enabled=False, fixed_width=self.date_edit.width())

        # Fixed booking or not.
        self.fixed_lbl = QLabel(self)
        self.form_layout.addWidget(self.fixed_lbl, 6, 0)
        config_lbl(self.fixed_lbl, "Turno fijo")

        self.fixed_line = QLineEdit(self)
        self.form_layout.addWidget(self.fixed_line, 6, 1)
        config_line(self.fixed_line, "No", enabled=False, fixed_width=self.date_edit.width())

        # Cancellation responsible.
        self.responsible_lbl = QLabel(self)
        self.form_layout.addWidget(self.responsible_lbl, 7, 0)
        config_lbl(self.responsible_lbl, "Responsable")

        self.responsible_field = responsible_field(self)
        self.form_layout.addWidget(self.responsible_field, 7, 1)
        config_line(self.responsible_field, place_holder="Responsable")

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


class HistoryController:

    def __init__(self, history_ui: HistoryUI, booking_system: BookingSystem) -> None:
        self.booking_system = booking_system
        self.history_ui = history_ui

        # Configure the filtering widget.
        filters = (ClientLike("client_name", display_name="Nombre cliente",
                              translate_fun=lambda cancelled, value: cancelled.client_name.contains(value)),)
        date_greater_filter = DateGreater(
            "from", display_name="Desde", attr="when",
            translate_fun=lambda cancelled, datetime_: cancelled.cancel_datetime >= datetime_
        )
        date_lesser_filter = DateLesser(
            "to", display_name="Hasta", attr="when",
            translate_fun=lambda cancelled, datetime_: cancelled.cancel_datetime <= datetime_
        )
        self.history_ui.filter_header.config(filters, self.fill_booking_table, date_greater_filter, date_lesser_filter)

        # Configures the page index.
        self.history_ui.page_index.config(refresh_table=self.history_ui.filter_header.on_search_click,
                                          page_len=20, show_info=False)

        # Fills the table.
        self.history_ui.filter_header.on_search_click()

    def fill_booking_table(self, filters: list[FilterValuePair]):
        self.history_ui.booking_table.setRowCount(0)

        for row, cancelled in enumerate(self.booking_system.repo.cancelled(self.history_ui.page_index.page,
                                                                           self.history_ui.page_index.page_len,
                                                                           filters)):
            fill_cell(self.history_ui.booking_table, row, 0,
                      cancelled.cancel_datetime.strftime(utils.DATE_TIME_FORMAT), bool)
            fill_cell(self.history_ui.booking_table, row, 1, cancelled.when.strftime(utils.DATE_FORMAT), bool)
            fill_cell(self.history_ui.booking_table, row, 2, cancelled.court, bool)
            fill_cell(self.history_ui.booking_table, row, 3, cancelled.start.strftime('%Hh:%Mm'), bool)
            duration = timedelta_to_duration_str(subtract_times(cancelled.start, cancelled.end))
            fill_cell(self.history_ui.booking_table, row, 4, duration, bool)
            fill_cell(self.history_ui.booking_table, row, 5, cancelled.client, str)
            fill_cell(self.history_ui.booking_table, row, 6, cancelled.responsible, str)
            fill_cell(self.history_ui.booking_table, row, 7, DAYS_NAMES[cancelled.when.weekday()], bool)
            fill_cell(self.history_ui.booking_table, row, 8, "Si" if cancelled.is_fixed else "No", bool)


class HistoryUI(QMainWindow):

    def __init__(self, booking_system: BookingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = HistoryController(self, booking_system)

    def _setup_ui(self):
        self.setWindowTitle("Turnos cancelados")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        # Filtering.
        self.filter_header = FilterHeader(date_greater_filtering=True, date_lesser_filtering=True, parent=self.widget)
        self.layout.addWidget(self.filter_header)

        # Bookings.
        self.booking_table = QTableWidget(self.widget)
        self.layout.addWidget(self.booking_table)

        new_config_table(self.booking_table, width=1250,
                         columns={"Fecha borrado": (.19, bool), "Fecha turno": (.12, bool), "Cancha": (.08, bool),
                                  "Hora": (.09, bool), "Duración": (.09, bool), "Cliente": (.19, str),
                                  "Responsable": (.14, str), "Día": (.05, bool), "Fijo": (.05, bool)},
                         min_rows_to_show=10)

        # Index.
        self.page_index = PageIndex(self)
        self.layout.addWidget(self.page_index)

        self.move(int(QDesktopWidget().geometry().center().x() - self.sizeHint().width() / 2),
                  int(QDesktopWidget().geometry().center().y() - self.sizeHint().height() / 2))
