from __future__ import annotations

import functools
import math
from datetime import date, datetime, timedelta

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem,
    QSizePolicy, QTableWidget, QTableWidgetItem, QDateEdit, QDialog, QGridLayout, QLabel,
    QComboBox, QCheckBox, QLineEdit, QDesktopWidget, QButtonGroup, QRadioButton)

from gym_manager.booking.core import (
    BookingSystem, ONE_DAY_TD,
    remaining_blocks, Booking, subtract_times, Duration, Block)
from gym_manager.core.base import DateGreater, DateLesser, ClientLike, String, Number, Currency
from gym_manager.core.persistence import FilterValuePair, TransactionRepo, ActivityRepo
from gym_manager.core.security import SecurityHandler, SecurityError
from ui import utils
from ui.utils import MESSAGE
from ui.widget_config import (
    config_layout, config_btn, config_date_edit, fill_cell, config_lbl,
    config_combobox, config_checkbox, config_line, fill_combobox, new_config_table)
from ui.widgets import FilterHeader, PageIndex, Dialog, responsible_field, Field, Separator

DAYS_NAMES = {0: "Lun", 1: "Mar", 2: "Mie", 3: "Jue", 4: "Vie", 5: "Sab", 6: "Dom"}
MONTH_NAMES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
               9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}


def timedelta_to_duration_str(td: timedelta) -> str:
    hours, minutes = td.seconds // 3600, (td.seconds // 60) % 60
    return f"{hours}h{minutes}m"


class MainController:

    def __init__(
            self, main_ui: BookingMainUI, transaction_repo: TransactionRepo, activity_repo: ActivityRepo,
            booking_system: BookingSystem, security_handler: SecurityHandler, allow_passed_time_bookings: bool = False
    ) -> None:
        self.main_ui = main_ui
        self.transaction_repo = transaction_repo
        self.activity_repo = activity_repo
        self.booking_system = booking_system
        self.security_handler = security_handler
        self._courts = {name: number + 1 for number, name in enumerate(booking_system.court_names)}
        self._bookings: dict[int, dict[int, Booking]] | None = None
        self._blocks = {i: block for i, block in enumerate(booking_system.blocks())}

        self.allow_passed_time_bookings = allow_passed_time_bookings

        fill_combobox(self.main_ui.method_combobox, self.transaction_repo.methods, display=lambda method: method)
        self.main_ui.charge_btn.setEnabled(False)
        self.main_ui.cancel_btn.setEnabled(False)

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
        # noinspection PyUnresolvedReferences
        self.main_ui.booking_table.itemSelectionChanged.connect(self.refresh_booking_info)

    def refresh_booking_info(self):
        row, col = self.main_ui.booking_table.currentRow(), self.main_ui.booking_table.currentColumn()
        if col in self._bookings and row in self._bookings[col]:
            self.booking_system.update_prices(self.activity_repo)
            booking = self._bookings[col][row]
            self.main_ui.court_line.setText(booking.court)
            self.main_ui.hour_line.setText(booking.start.strftime("%H:%M"))
            self.main_ui.client_line.setText(booking.client_name.as_primitive())
            self.main_ui.amount_line.setText(Currency.fmt(self.booking_system.amount_to_charge(booking), symbol=""))
            self.main_ui.charge_btn.setEnabled(True)
            self.main_ui.cancel_btn.setEnabled(True)
        else:
            self.main_ui.court_line.clear()
            self.main_ui.hour_line.clear()
            self.main_ui.client_line.clear()
            self.main_ui.amount_line.clear()
            self.main_ui.charge_btn.setEnabled(False)
            self.main_ui.cancel_btn.setEnabled(False)

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
        self.main_ui.booking_table.setRowCount(len(self._blocks))
        for row, block in self._blocks.items():
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
        when, today = self.main_ui.date_edit.date().toPyDate(), date.today()
        block: Block | None = None
        if self.main_ui.booking_table.currentRow() != -1:
            block = self._blocks[self.main_ui.booking_table.currentRow()]

        if not self.allow_passed_time_bookings:
            if when < today:
                Dialog.info("Error", "No se puede reservar un turno para un día previo al actual.")
                return
            if when == today and block is not None and block.start < datetime.now().time():
                Dialog.info("Error", "No se puede reservar un turno para una hora que ya pasó.")
                return

        # noinspection PyAttributeOutsideInit
        self._create_ui = CreateUI(self.booking_system, self.security_handler, when,
                                   self.allow_passed_time_bookings, block)
        self._create_ui.exec_()
        if self._create_ui.controller.booking is not None:
            self._load_booking(self._create_ui.controller.booking)

    def charge_booking(self):
        self.main_ui.responsible_field.setStyleSheet("")
        if not self.main_ui.amount_line.valid_value():
            Dialog.info("Error", f"El monto ingresado no es válido.")
        else:
            b = self._bookings[self.main_ui.booking_table.currentColumn()][self.main_ui.booking_table.currentRow()]
            when = self.main_ui.date_edit.date().toPyDate()

            if when > date.today() or (when == datetime.now().date() and b.start > datetime.now().time()):
                Dialog.info("Error", "No se puede cobrar un turno que todavía no comenzó.")
                return
            if b.was_paid(when):
                Dialog.info("Error", f"El turno ya fue cobrado.")
                return

            try:
                self.security_handler.current_responsible = self.main_ui.responsible_field.value()

                create_transaction_fn = functools.partial(
                    self.transaction_repo.create, "Cobro", date.today(), self.main_ui.amount_line.value(),
                    self.main_ui.method_combobox.currentText(), self.security_handler.current_responsible.name,
                    f"Cobro de turno de Padel a '{b.client_name}'."
                )
                self.booking_system.register_charge(b, when, create_transaction_fn)

                # Updates the ui.
                text = f"{b.client_name}{' (Fijo)' if b.is_fixed else ''}{' (Pago)' if b.was_paid(when) else ''}"
                start, end = self.booking_system.block_range(b.start, b.end)
                for i in range(start, end):
                    self.main_ui.booking_table.item(i, self.main_ui.booking_table.currentColumn()).setText(text)

                Dialog.info("Éxito", f"El cobro a '{b.client_name}' por el turno fue registrado.")

            except SecurityError as sec_err:
                self.main_ui.responsible_field.setStyleSheet("border: 1px solid red")
                Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))

    def cancel_booking(self):
        self.main_ui.responsible_field.setStyleSheet("")
        row, col = self.main_ui.booking_table.currentRow(), self.main_ui.booking_table.currentColumn()
        when = self.main_ui.date_edit.date().toPyDate()

        to_cancel = self._bookings[col][row]
        if when < date.today() or (when == datetime.now().date() and to_cancel.start < datetime.now().time()):
            Dialog.info("Error", "No se puede cancelar un turno que ya comenzo.")
        elif to_cancel.was_paid(when):
            Dialog.info("Error", "No se puede cancelar un turno que ya cobrado.")
        else:
            try:
                self.security_handler.current_responsible = self.main_ui.responsible_field.value()
                definitely_cancelled = True
                if to_cancel.is_fixed:
                    definitely_cancelled = Dialog.confirm("El turno es fijo, ¿Desea cancelarlo definitivamente?",
                                                          ok_btn_text="Si", cancel_btn_text="No")
                # noinspection PyTypeChecker
                self.booking_system.cancel(to_cancel, self.security_handler.current_responsible.name, when,
                                           definitely_cancelled, datetime.now())

                start, end = self.booking_system.block_range(to_cancel.start, to_cancel.end)
                for i in range(start, end):
                    self.main_ui.booking_table.takeItem(i, col)
                    self._bookings[col].pop(i)

                self.refresh_booking_info()

                if to_cancel.is_fixed and definitely_cancelled:
                    Dialog.info("Éxito", "El turno fijo ha sido cancelado correctamente.")
                else:
                    Dialog.info("Éxito", "El turno ha sido cancelado correctamente.")
            except SecurityError as sec_err:
                self.main_ui.responsible_field.setStyleSheet("border: 1px solid red")
                Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))

    def cancelled_bookings(self):
        # noinspection PyAttributeOutsideInit
        self._history_ui = HistoryUI(self.booking_system)
        self._history_ui.setWindowModality(Qt.ApplicationModal)
        self._history_ui.show()


class BookingMainUI(QMainWindow):

    def __init__(
            self, transaction_repo: TransactionRepo, booking_system: BookingSystem, activity_repo: ActivityRepo,
            security_handler: SecurityHandler, allow_passed_time_bookings: bool = False
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, transaction_repo, activity_repo, booking_system, security_handler,
                                         allow_passed_time_bookings)

    def _setup_ui(self):
        self.setWindowTitle("Padel")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        self.top_layout = QHBoxLayout()
        self.layout.addLayout(self.top_layout)

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.top_layout.addLayout(self.buttons_layout)

        self.create_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.create_btn)
        config_btn(self.create_btn, "Reservar turno", font_size=16)

        self.cancel_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.cancel_btn)
        config_btn(self.cancel_btn, "Cancelar turno", font_size=16, icon_path=r"ui/resources/trash_can.png",
                   icon_size=24)

        self.history_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.history_btn)
        config_btn(self.history_btn, "Ver borrados", font_size=16)

        self.top_layout.addWidget(Separator(vertical=True, parent=self.widget))  # Vertical line.

        # Charge form.
        self.charge_form_layout = QGridLayout()
        self.top_layout.addLayout(self.charge_form_layout)

        # Responsible.
        self.responsible_lbl = QLabel(self.widget)
        self.charge_form_layout.addWidget(self.responsible_lbl, 0, 0)
        config_lbl(self.responsible_lbl, "Responsable")

        self.responsible_field = responsible_field(self.widget)
        self.charge_form_layout.addWidget(self.responsible_field, 0, 1)
        config_line(self.responsible_field, fixed_width=100)

        # Court
        self.court_lbl = QLabel(self.widget)
        self.charge_form_layout.addWidget(self.court_lbl, 0, 2)
        config_lbl(self.court_lbl, "Cancha")

        self.court_line = QLineEdit(self.widget)
        self.charge_form_layout.addWidget(self.court_line, 0, 3)
        config_line(self.court_line, fixed_width=40, enabled=False, alignment=Qt.AlignCenter)

        # Hour
        self.hour_lbl = QLabel(self.widget)
        self.charge_form_layout.addWidget(self.hour_lbl, 0, 4)
        config_lbl(self.hour_lbl, "Hora")

        self.hour_line = QLineEdit(self.widget)
        self.charge_form_layout.addWidget(self.hour_line, 0, 5)
        config_line(self.hour_line, fixed_width=60, enabled=False, alignment=Qt.AlignCenter)

        # Client.
        self.client_lbl = QLabel(self.widget)
        self.charge_form_layout.addWidget(self.client_lbl, 1, 0)
        config_lbl(self.client_lbl, "Cliente")

        self.client_line = QLineEdit(self.widget)
        self.charge_form_layout.addWidget(self.client_line, 1, 1, 1, 2)
        config_line(self.client_line, read_only=True)
        self.client_line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Method.
        self.method_combobox = QComboBox(self)
        self.charge_form_layout.addWidget(self.method_combobox, 2, 0)
        config_combobox(self.method_combobox)

        # Amount.
        self.amount_line = Field(Currency, parent=self, positive=True)
        self.charge_form_layout.addWidget(self.amount_line, 2, 1, 1, 2)
        config_line(self.amount_line, place_holder="000000,00", alignment=Qt.AlignRight)

        # Charge button
        self.charge_btn = QPushButton(self.widget)
        self.charge_form_layout.addWidget(self.charge_btn, 1, 3, 2, 3, alignment=Qt.AlignCenter)
        config_btn(self.charge_btn, "Cobrar", icon_path=r"ui/resources/tick.png", icon_size=24)

        self.layout.addWidget(Separator(vertical=False, parent=self.widget))  # Vertical line.

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
            self, create_ui: CreateUI, booking_system: BookingSystem, security_handler: SecurityHandler, when: date,
            allow_passed_time_bookings: bool, selected_block: Block | None = None
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
        # The item in the combobox will be the selected block in BookingMainUI, if one block was selected.
        if selected_block is not None:
            for i in range(len(self.create_ui.block_combobox)):
                if selected_block == self.create_ui.block_combobox.itemData(i, Qt.UserRole):
                    self.create_ui.block_combobox.setCurrentIndex(i)
                    break

        self.create_ui.half_hour_btn.setChecked(True)
        self.enable_other_field()

        # Configs the widgets so they have the same width.
        config_combobox(self.create_ui.block_combobox)
        config_combobox(self.create_ui.court_combobox, fixed_width=self.create_ui.block_combobox.width())

        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_booking)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)
        # noinspection PyUnresolvedReferences
        self.create_ui.charge_filter_group.buttonClicked.connect(self.enable_other_field)

    def enable_other_field(self):
        self.create_ui.other_field.setEnabled(self.create_ui.other_btn.isChecked())

    def _get_duration(self):
        minutes: int
        if self.create_ui.half_hour_btn.isChecked():
            minutes = 30
        elif self.create_ui.one_hour_btn.isChecked():
            minutes = 60
        elif self.create_ui.one_half_hour_btn.isChecked():
            minutes = 90
        elif self.create_ui.two_hour_btn.isChecked():
            minutes = 120
        else:
            minutes = self.create_ui.other_field.value().as_primitive()
            # If the booking duration isn't "n times 30", then add another 30 minutes to it.
            minutes = 30 * math.ceil(minutes / 30)

        return Duration.from_td(timedelta(minutes=minutes))

    def create_booking(self):
        court = self.create_ui.court_combobox.currentData(Qt.UserRole)
        start_block = self.create_ui.block_combobox.currentData(Qt.UserRole)

        if self.create_ui.other_btn.isChecked() and not self.create_ui.other_field.valid_value():
            Dialog.info("Error", "La duración ingresada para el turno no es válida.")
            return
        duration = self._get_duration()

        if not self.create_ui.client_field.valid_value():
            Dialog.info("Error", "El campo Cliente no es válido.")
        elif self.booking_system.out_of_range(start_block.start, duration):
            Dialog.info("Error", f"El turno debe ser entre las '{self.booking_system.start}' y las "
                                 f"'{self.booking_system.end}'.")
        elif not self.booking_system.booking_available(self.when, court, start_block.start, duration,
                                                       self.create_ui.fixed_checkbox.isChecked()):
            Dialog.info("Error", "El horario solicitado se encuentra ocupado.")
        else:
            # noinspection PyTypeChecker
            self.booking = self.booking_system.book(court, self.create_ui.client_field.value(),
                                                    self.create_ui.fixed_checkbox.isChecked(), self.when,
                                                    start_block.start, duration)
            Dialog.info("Éxito", "El turno ha sido reservado correctamente.")
            self.create_ui.client_field.window().close()


class CreateUI(QDialog):

    def __init__(
            self, booking_system: BookingSystem, security_handler: SecurityHandler, when: date,
            allow_passed_time_bookings: bool, selected_block: Block | None = None
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, booking_system, security_handler, when,
                                           allow_passed_time_bookings, selected_block)

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
        self.form_layout.addWidget(self.date_lbl, 0, 2)
        config_lbl(self.date_lbl, "Fecha")

        self.date_edit = QDateEdit(self)  # Configured in CreateController.
        self.form_layout.addWidget(self.date_edit, 0, 3)

        self.court_lbl = QLabel(self)
        self.form_layout.addWidget(self.court_lbl, 1, 0)
        config_lbl(self.court_lbl, "Cancha")

        self.court_combobox = QComboBox(self)  # The configuration is done in _fill_block_combobox.
        self.form_layout.addWidget(self.court_combobox, 1, 1)

        self.hour_lbl = QLabel(self)
        self.form_layout.addWidget(self.hour_lbl, 1, 2)
        config_lbl(self.hour_lbl, "Hora")

        self.block_combobox = QComboBox(self)  # The configuration is done in _fill_block_combobox.
        self.form_layout.addWidget(self.block_combobox, 1, 3)

        # Duration.
        self.duration_lbl = QLabel(self)
        self.form_layout.addWidget(self.duration_lbl, 4, 0)
        config_lbl(self.duration_lbl, "Duración")

        self.duration_layout = QHBoxLayout()
        self.form_layout.addLayout(self.duration_layout, 4, 1, 1, 3)
        self.duration_layout.setAlignment(Qt.AlignCenter)
        self.charge_filter_group = QButtonGroup(self)

        font = QFont("MS Shell Dlg 2", 14)

        self.half_hour_btn = QRadioButton("30m")
        self.charge_filter_group.addButton(self.half_hour_btn)
        self.duration_layout.addWidget(self.half_hour_btn)
        self.half_hour_btn.setFont(font)

        self.one_hour_btn = QRadioButton("1h")
        self.charge_filter_group.addButton(self.one_hour_btn)
        self.duration_layout.addWidget(self.one_hour_btn)
        self.one_hour_btn.setFont(font)

        self.one_half_hour_btn = QRadioButton("1h30")
        self.charge_filter_group.addButton(self.one_half_hour_btn)
        self.duration_layout.addWidget(self.one_half_hour_btn)
        self.one_half_hour_btn.setFont(font)

        self.two_hour_btn = QRadioButton("2h")
        self.charge_filter_group.addButton(self.two_hour_btn)
        self.duration_layout.addWidget(self.two_hour_btn)
        self.two_hour_btn.setFont(font)

        self.other_btn = QRadioButton("Otra")
        self.charge_filter_group.addButton(self.other_btn)
        self.duration_layout.addWidget(self.other_btn)
        self.other_btn.setFont(font)

        self.other_field = Field(Number, parent=self, min_value=1, max_value=601)
        self.duration_layout.addWidget(self.other_field)
        config_line(self.other_field, place_holder="Minutos", fixed_width=75)

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
