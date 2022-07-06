from __future__ import annotations

from datetime import date

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QDialog, QDateEdit, QLineEdit, QHBoxLayout, QSpacerItem, QSizePolicy)

from gym_manager.booking.core import BookingSystem, Booking, BOOKING_TO_HAPPEN, current_block_start
from gym_manager.core import constants
from gym_manager.core.base import TextLike, ClientLike, String, NumberEqual
from gym_manager.core.persistence import ClientRepo, FilterValuePair
from gym_manager.core.system import AccountingSystem
from ui.accounting.operations import ChargeUI
from ui.widget_config import config_layout, config_lbl, config_combobox, config_btn, config_checkbox, \
    fill_combobox, config_date_edit, config_line
from ui.widgets import Dialog, Field, FilterHeader


def booking_summary(booking: Booking):
    return f"{booking.client.name.as_primitive()} - {booking.when.strftime(constants.DATE_FORMAT)} - {booking.court.name}"


class BookController:

    def __init__(self, book_ui: BookUI, client_repo: ClientRepo, booking_system: BookingSystem) -> None:
        self.client_repo = client_repo
        self.booking_system = booking_system
        self.booking: Booking | None = None

        self.book_ui = book_ui

        fill_combobox(self.book_ui.court_combobox, self.booking_system.courts(), lambda court: court.name)
        self._fill_block_combobox()
        fill_combobox(self.book_ui.duration_combobox, self.booking_system.durations, lambda duration: duration.as_str)

        # Configure the filtering widget.
        filters = (TextLike("client_name", display_name="Nombre cliente", attr="name",
                            translate_fun=lambda client, value: client.cli_name.contains(value)),
                   NumberEqual("client_dni", display_name="DNI cliente", attr="dni",
                               translate_fun=lambda client, value: client.dni == value))
        self.book_ui.filter_header.config(filters, self.fill_client_combobox, allow_empty_filter=False)

        # noinspection PyUnresolvedReferences
        self.book_ui.confirm_btn.clicked.connect(self.book)
        # noinspection PyUnresolvedReferences
        self.book_ui.cancel_btn.clicked.connect(self.book_ui.reject)
        # noinspection PyUnresolvedReferences
        self.book_ui.date_edit.dateChanged.connect(self._fill_block_combobox)

    def _fill_block_combobox(self):
        blocks = self.booking_system.blocks(current_block_start(self.booking_system.blocks(),
                                                                self.book_ui.date_edit.date().toPyDate()))
        fill_combobox(self.book_ui.block_combobox, blocks, lambda block: str(block.start))
        config_combobox(self.book_ui.block_combobox)
        config_combobox(self.book_ui.court_combobox, fixed_width=self.book_ui.block_combobox.width())
        config_combobox(self.book_ui.duration_combobox, fixed_width=self.book_ui.block_combobox.width())

    def fill_client_combobox(self, filters: list[FilterValuePair]):
        fill_combobox(self.book_ui.client_combobox,
                      self.client_repo.all(page=1, filters=filters),
                      lambda client: client.name.as_primitive())

    def book(self):
        client = self.book_ui.client_combobox.currentData(Qt.UserRole)
        court = self.book_ui.court_combobox.currentData(Qt.UserRole)
        when = self.book_ui.date_edit.date().toPyDate()
        start_block = self.book_ui.block_combobox.currentData(Qt.UserRole)
        duration = self.book_ui.duration_combobox.currentData(Qt.UserRole)

        if client is None:
            Dialog.info("Error", "Seleccione un cliente.")
        elif self.booking_system.out_of_range(start_block, duration):
            Dialog.info("Error", f"El turno debe ser entre las '{self.booking_system.start}' y las "
                                 f"'{self.booking_system.end}'.")
        elif not self.booking_system.booking_available(when, court, start_block, duration):
            Dialog.info("Error", "El horario solicitado se encuentra ocupado.")
        else:
            is_fixed = self.book_ui.fixed_checkbox.isChecked()
            self.booking = self.booking_system.book(court, client, is_fixed, when, start_block, duration)[0]
            Dialog.info("Éxito", "El turno ha sido reservado correctamente.")
            self.book_ui.client_combobox.window().close()


class BookUI(QDialog):

    def __init__(self, client_repo: ClientRepo, booking_system: BookingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = BookController(self, client_repo, booking_system)

    def _setup_ui(self):
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

        self.date_edit = QDateEdit(self)
        self.form_layout.addWidget(self.date_edit, 1, 1)
        config_date_edit(self.date_edit, date.today(), calendar=True)

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

        self.fixed_lbl = QLabel(self)
        self.form_layout.addWidget(self.fixed_lbl, 5, 0)
        config_lbl(self.fixed_lbl, "Turno fijo")

        self.fixed_checkbox = QCheckBox(self)
        self.form_layout.addWidget(self.fixed_checkbox, 5, 1)
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

    def __init__(self, cancel_ui: CancelUI, booking_system: BookingSystem) -> None:
        self.booking_system = booking_system
        self.booking: Booking | None = None

        self.cancel_ui = cancel_ui

        # Configure the filtering widget.
        filters = (ClientLike("client_name", display_name="Nombre cliente",
                              translate_fun=lambda booking, value: booking.client.cli_name.contains(value)),
                   NumberEqual("client_dni", display_name="DNI cliente", attr="dni",
                               translate_fun=lambda booking, value: booking.client.dni == value))
        self.cancel_ui.filter_header.config(filters, self.fill_booking_combobox, allow_empty_filter=False)

        # noinspection PyUnresolvedReferences
        self.cancel_ui.booking_combobox.currentIndexChanged.connect(self._update_form)
        # noinspection PyUnresolvedReferences
        self.cancel_ui.confirm_btn.clicked.connect(self.cancel)
        # noinspection PyUnresolvedReferences
        self.cancel_ui.cancel_btn.clicked.connect(self.cancel_ui.reject)

    def fill_booking_combobox(self, filters: list[FilterValuePair]):
        fill_combobox(self.cancel_ui.booking_combobox,
                      self.booking_system.repo.all(states=(BOOKING_TO_HAPPEN,), filters=filters),
                      booking_summary)

    def _update_form(self):
        booking: Booking = self.cancel_ui.booking_combobox.currentData(Qt.UserRole)
        self.cancel_ui.client_line.setText(str(booking.client.name))
        self.cancel_ui.court_line.setText(booking.court.name)
        self.cancel_ui.date_edit.setDate(booking.when)
        self.cancel_ui.start_line.setText(str(booking.start))
        self.cancel_ui.end_line.setText(str(booking.end))
        self.cancel_ui.fixed_line.setText("Si" if booking.is_fixed else "No")

    def cancel(self):
        self.booking: Booking = self.cancel_ui.booking_combobox.currentData(Qt.UserRole)

        if self.booking is None:
            Dialog.info("Error", "Seleccione una reserva.")
        elif not self.cancel_ui.responsible_field.valid_value():
            Dialog.info("Error", "El campo responsable no es válido.")
        else:
            cancel_fixed = False
            if self.booking.is_fixed:
                cancel_fixed = Dialog.confirm("El turno es fijo, ¿Desea cancelarlo definitivamente?",
                                              ok_btn_text="Si", cancel_btn_text="No")
            self.booking_system.cancel(self.booking, self.cancel_ui.responsible_field.value().as_primitive(),
                                       cancel_fixed)
            msg: str
            if self.booking.is_fixed and cancel_fixed:
                msg = "El turno fijo ha sido cancelado correctamente."
            else:
                msg = "El turno ha sido cancelado correctamente."
            Dialog.info("Éxito", msg)
            self.cancel_ui.booking_combobox.window().close()


class CancelUI(QDialog):

    def __init__(self, booking_system: BookingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CancelController(self, booking_system)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)

        # Filtering.
        self.filter_header = FilterHeader(show_clear_button=False, parent=self)
        self.layout.addWidget(self.filter_header)

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

        # The booking related widgets are declared after the client ones, so the booking combobox width is equal to the
        # client line width.
        self.booking_lbl = QLabel(self)
        self.form_layout.addWidget(self.booking_lbl, 0, 0)
        config_lbl(self.booking_lbl, "Reserva*")

        self.booking_combobox = QComboBox(self)
        self.form_layout.addWidget(self.booking_combobox, 0, 1)
        config_combobox(self.booking_combobox, fixed_width=self.client_line.width())

        # Booked date.
        self.date_lbl = QLabel(self)
        self.form_layout.addWidget(self.date_lbl, 2, 0)
        config_lbl(self.date_lbl, "Fecha",)

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
        config_lbl(self.responsible_lbl, "Responsable*")

        self.responsible_field = Field(String, self, max_len=constants.TRANSACTION_RESP_CHARS)
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


class PreChargeController:

    def __init__(
            self, pre_charge_ui: PreChargeUI, booking_system: BookingSystem, accounting_system: AccountingSystem
    ) -> None:
        self.booking_system = booking_system
        self.accounting_system = accounting_system
        self.booking: Booking | None = None

        self.pre_charge_ui = pre_charge_ui

        # Configure the filtering widget.
        filters = (ClientLike("client_name", display_name="Nombre cliente",
                              translate_fun=lambda booking, value: booking.client.cli_name.contains(value)),
                   NumberEqual("client_dni", display_name="DNI cliente", attr="dni",
                               translate_fun=lambda booking, value: booking.client.dni == value))
        self.pre_charge_ui.filter_header.config(filters, self.fill_booking_combobox, allow_empty_filter=False)

        # noinspection PyUnresolvedReferences
        self.pre_charge_ui.booking_combobox.currentIndexChanged.connect(self._update_form)
        # noinspection PyUnresolvedReferences
        self.pre_charge_ui.confirm_btn.clicked.connect(self.charge)

    def fill_booking_combobox(self, filters: list[FilterValuePair]):
        fill_combobox(self.pre_charge_ui.booking_combobox,
                      self.booking_system.repo.all(states=(BOOKING_TO_HAPPEN,), filters=filters),
                      booking_summary)

    def _update_form(self):
        booking: Booking = self.pre_charge_ui.booking_combobox.currentData(Qt.UserRole)
        self.pre_charge_ui.client_line.setText(str(booking.client.name))
        self.pre_charge_ui.court_line.setText(booking.court.name)
        self.pre_charge_ui.date_line.setText(str(booking.when))
        self.pre_charge_ui.start_line.setText(str(booking.start))
        self.pre_charge_ui.end_line.setText(str(booking.end))
        self.pre_charge_ui.fixed_checkbox.setChecked(booking.is_fixed)

    def charge(self):
        booking: Booking = self.pre_charge_ui.booking_combobox.currentData(Qt.UserRole)

        if booking is None:
            Dialog.info("Error", "Seleccione un turno.")
        else:
            activity = self.booking_system.activity
            descr = String(f"Cobro de turno de {activity.name}", max_len=constants.TRANSACTION_DESCR_CHARS)
            # noinspection PyAttributeOutsideInit
            self.charge_ui = ChargeUI(self.accounting_system, booking.client, activity, descr)
            self.charge_ui.exec_()

            if self.charge_ui.controller.transaction is not None:
                self.booking_system.register_charge(booking, self.charge_ui.controller.transaction)
            self.pre_charge_ui.booking_combobox.window().close()


class PreChargeUI(QDialog):

    def __init__(self, booking_system: BookingSystem, accounting_system: AccountingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = PreChargeController(self, booking_system, accounting_system)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        config_layout(self.layout, left_margin=30, top_margin=10, right_margin=30, bottom_margin=10, spacing=20)

        # Filtering.
        self.filter_header = FilterHeader(show_clear_button=False, parent=self)
        self.layout.addWidget(self.filter_header)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        config_layout(self.form_layout, spacing=10)

        self.booking_lbl = QLabel(self)
        self.form_layout.addWidget(self.booking_lbl, 0, 0)
        config_lbl(self.booking_lbl, "Reserva")

        self.booking_combobox = QComboBox()
        self.form_layout.addWidget(self.booking_combobox, 0, 1)
        config_combobox(self.booking_combobox, extra_height=35)

        self.client_lbl = QLabel(self)
        self.form_layout.addWidget(self.client_lbl, 1, 0)
        config_lbl(self.client_lbl, "Cliente")

        self.client_line = QLineEdit(self)
        self.form_layout.addWidget(self.client_line, 1, 1)
        config_line(self.client_line, extra_height=35, read_only=False)

        self.court_lbl = QLabel(self)
        self.form_layout.addWidget(self.court_lbl, 2, 0)
        config_lbl(self.court_lbl, "Cancha")

        self.court_line = QLineEdit(self)
        self.form_layout.addWidget(self.court_line, 2, 1)
        config_line(self.court_line, extra_height=35, read_only=False)

        self.date_lbl = QLabel(self)
        self.form_layout.addWidget(self.date_lbl, 3, 0)
        config_lbl(self.date_lbl, "Fecha")

        self.date_line = QLineEdit(self)
        self.form_layout.addWidget(self.date_line, 3, 1)
        config_line(self.date_line, extra_height=35, read_only=False)

        self.block_lbl = QLabel(self)
        self.form_layout.addWidget(self.block_lbl, 4, 0)
        config_lbl(self.block_lbl, "Inicio")

        self.start_line = QLineEdit(self)
        self.form_layout.addWidget(self.start_line, 4, 1)
        config_line(self.start_line, extra_height=35, read_only=False)

        self.duration_lbl = QLabel(self)
        self.form_layout.addWidget(self.duration_lbl, 5, 0)
        config_lbl(self.duration_lbl, "Fin")

        self.end_line = QLineEdit(self)
        self.form_layout.addWidget(self.end_line, 5, 1)
        config_line(self.end_line, extra_height=35, read_only=False)

        self.fixed_checkbox = QCheckBox()
        self.layout.addWidget(self.fixed_checkbox, alignment=Qt.AlignCenter)
        config_checkbox(self.fixed_checkbox, checked=False, text="Turno fijo", enabled=False)

        self.confirm_btn = QPushButton(self)
        self.layout.addWidget(self.confirm_btn, alignment=Qt.AlignCenter)
        config_btn(self.confirm_btn, "Siguiente", font_size=18, extra_width=200)
