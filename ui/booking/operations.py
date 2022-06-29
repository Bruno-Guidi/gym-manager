from __future__ import annotations

from datetime import date

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox, \
    QCheckBox, QPushButton, QDialog, QDateEdit, QHBoxLayout, QLineEdit

from gym_manager.booking.core import BookingSystem, Booking, BOOKING_TO_HAPPEN
from gym_manager.core import constants
from gym_manager.core.base import TextLike, ClientLike, String
from gym_manager.core.persistence import ClientRepo
from gym_manager.core.system import AccountingSystem
from ui.accounting.operations import ChargeUI
from ui.widget_config import config_layout, config_lbl, config_combobox, config_btn, config_checkbox, \
    fill_combobox, config_date_edit, config_line
from ui.widgets import SearchBox, Dialog, Field


def booking_summary(booking: Booking):
    return f"{booking.client.name.as_primitive()} - {booking.when} - {booking.court.name} - {booking.state.name}"


class BookController:

    def __init__(self, book_ui: BookUI, client_repo: ClientRepo, booking_system: BookingSystem) -> None:
        self.client_repo = client_repo
        self.booking_system = booking_system
        self.booking: Booking | None = None

        self.book_ui = book_ui

        fill_combobox(book_ui.court_combobox, self.booking_system.courts(), lambda court: court.name)
        fill_combobox(book_ui.block_combobox, self.booking_system.blocks(), lambda block: str(block.start))
        fill_combobox(book_ui.duration_combobox, self.booking_system.durations, lambda duration: duration.as_str)

        # noinspection PyUnresolvedReferences
        self.book_ui.search_btn.clicked.connect(self.search_clients)
        # noinspection PyUnresolvedReferences
        self.book_ui.confirm_btn.clicked.connect(self.book)

    def search_clients(self):
        if self.book_ui.search_box.is_empty():
            Dialog.info("Error", "La caja de búsqueda no puede estar vacia.")
        else:
            clients = self.client_repo.all(page=1, **self.book_ui.search_box.filters())
            fill_combobox(self.book_ui.client_combobox, clients, lambda client: client.name.as_primitive())

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
            self.booking = self.booking_system.book(court, client, is_fixed, when, start_block, duration)
            Dialog.info("Éxito", "El turno ha sido reservado correctamente.")
            self.book_ui.client_combobox.window().close()


class BookUI(QDialog):

    def __init__(self, client_repo: ClientRepo, booking_system: BookingSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = BookController(self, client_repo, booking_system)

    def _setup_ui(self):
        width, height = 600, 400
        self.resize(width, height)

        self.central_widget = QWidget(self)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, width, height))
        self.layout = QVBoxLayout(self.widget)
        config_layout(self.layout, left_margin=30, top_margin=10, right_margin=30, bottom_margin=10, spacing=20)

        # Utilities.
        self.utils_layout = QHBoxLayout()
        self.layout.addLayout(self.utils_layout)

        self.search_box = SearchBox(
            filters=[TextLike("name", display_name="Nombre", attr="name",
                              translate_fun=lambda client, value: client.cli_name.contains(value))],
            parent=self.widget)
        self.utils_layout.addWidget(self.search_box)

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "Busq", font_size=16)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        config_layout(self.form_layout, spacing=10)

        self.client_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.client_lbl, 0, 0, 1, 1)
        config_lbl(self.client_lbl, "Cliente")

        self.client_combobox = QComboBox()
        self.form_layout.addWidget(self.client_combobox, 0, 1, 1, 1)
        config_combobox(self.client_combobox, height=35)

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

        self.block_combobox = QComboBox(self.widget)
        self.form_layout.addWidget(self.block_combobox, 3, 1, 1, 1)
        config_combobox(self.block_combobox, height=35)

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


class CancelController:

    def __init__(self, cancel_ui: CancelUI, booking_system: BookingSystem) -> None:
        self.booking_system = booking_system
        self.booking: Booking | None = None

        self.cancel_ui = cancel_ui

        # noinspection PyUnresolvedReferences
        self.cancel_ui.search_btn.clicked.connect(self.search_bookings)
        # noinspection PyUnresolvedReferences
        self.cancel_ui.booking_combobox.currentIndexChanged.connect(self._update_form)
        # noinspection PyUnresolvedReferences
        self.cancel_ui.confirm_btn.clicked.connect(self.cancel)

    def search_bookings(self):
        if self.cancel_ui.search_box.is_empty():
            Dialog.info("Error", "La caja de búsqueda no puede estar vacia.")
        else:
            bookings = self.booking_system.bookings(states=(BOOKING_TO_HAPPEN,), **self.cancel_ui.search_box.filters())
            fill_combobox(self.cancel_ui.booking_combobox, (booking for booking, _, _ in bookings), booking_summary)

    def _update_form(self):
        booking: Booking = self.cancel_ui.booking_combobox.currentData(Qt.UserRole)
        self.cancel_ui.client_line.setText(str(booking.client.name))
        self.cancel_ui.court_line.setText(booking.court.name)
        self.cancel_ui.date_line.setText(str(booking.when))
        self.cancel_ui.start_line.setText(str(booking.start))
        self.cancel_ui.end_line.setText(str(booking.end))
        self.cancel_ui.fixed_checkbox.setChecked(booking.is_fixed)

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
        width, height = 600, 500
        self.resize(width, height)

        self.central_widget = QWidget(self)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, width, height))
        self.layout = QVBoxLayout(self.widget)
        config_layout(self.layout, left_margin=30, top_margin=10, right_margin=30, bottom_margin=10, spacing=20)

        # Utilities.
        self.utils_layout = QHBoxLayout()
        self.layout.addLayout(self.utils_layout)

        self.search_box = SearchBox(
            filters=[ClientLike("name", display_name="Nombre",
                                translate_fun=lambda booking, value: booking.client.cli_name.contains(value))],
            parent=self.widget)
        self.utils_layout.addWidget(self.search_box)

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "Busq", font_size=16)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        config_layout(self.form_layout, spacing=10)

        self.booking_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.booking_lbl, 0, 0, 1, 1)
        config_lbl(self.booking_lbl, "Reserva")

        self.booking_combobox = QComboBox()
        self.form_layout.addWidget(self.booking_combobox, 0, 1, 1, 1)
        config_combobox(self.booking_combobox, height=35)

        self.client_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.client_lbl, 1, 0, 1, 1)
        config_lbl(self.client_lbl, "Cliente")

        self.client_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.client_line, 1, 1, 1, 1)
        config_line(self.client_line, height=35, enabled=False)

        self.court_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.court_lbl, 2, 0, 1, 1)
        config_lbl(self.court_lbl, "Cancha")

        self.court_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.court_line, 2, 1, 1, 1)
        config_line(self.court_line, height=35, enabled=False)

        self.date_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.date_lbl, 3, 0, 1, 1)
        config_lbl(self.date_lbl, "Fecha")

        self.date_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.date_line, 3, 1, 1, 1)
        config_line(self.date_line, height=35, enabled=False)

        self.block_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.block_lbl, 4, 0, 1, 1)
        config_lbl(self.block_lbl, "Inicio")

        self.start_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.start_line, 4, 1, 1, 1)
        config_line(self.start_line, height=35, enabled=False)

        self.duration_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.duration_lbl, 5, 0, 1, 1)
        config_lbl(self.duration_lbl, "Fin")

        self.end_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.end_line, 5, 1, 1, 1)
        config_line(self.end_line, height=35, enabled=False)

        self.fixed_checkbox = QCheckBox()
        self.layout.addWidget(self.fixed_checkbox, alignment=Qt.AlignCenter)
        config_checkbox(self.fixed_checkbox, checked=False, text="Turno fijo", enabled=False)

        self.responsible_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.responsible_lbl, 6, 0, 1, 1)
        config_lbl(self.responsible_lbl, "Responsable")

        self.responsible_field = Field(String, self.widget, max_len=constants.TRANSACTION_RESP_CHARS)
        self.form_layout.addWidget(self.responsible_field, 6, 1, 1, 1)
        config_line(self.responsible_field, height=35)

        self.confirm_btn = QPushButton(self.widget)
        self.layout.addWidget(self.confirm_btn, alignment=Qt.AlignCenter)
        config_btn(self.confirm_btn, "Eliminar", font_size=18, width=200)


class PreChargeController:

    def __init__(
            self, pre_charge_ui: PreChargeUI, booking_system: BookingSystem, accounting_system: AccountingSystem
    ) -> None:
        self.booking_system = booking_system
        self.accounting_system = accounting_system
        self.booking: Booking | None = None

        self.pre_charge_ui = pre_charge_ui

        # noinspection PyUnresolvedReferences
        self.pre_charge_ui.search_btn.clicked.connect(self.search_bookings)
        # noinspection PyUnresolvedReferences
        self.pre_charge_ui.booking_combobox.currentIndexChanged.connect(self._update_form)
        # noinspection PyUnresolvedReferences
        self.pre_charge_ui.confirm_btn.clicked.connect(self.charge)

    def search_bookings(self):
        if self.pre_charge_ui.search_box.is_empty():
            Dialog.info("Error", "La caja de búsqueda no puede estar vacia.")
        else:
            bookings = self.booking_system.bookings(states=(BOOKING_TO_HAPPEN,),
                                                    **self.pre_charge_ui.search_box.filters())
            fill_combobox(self.pre_charge_ui.booking_combobox, (booking for booking, _, _ in bookings), booking_summary)

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
            self.charge_ui = ChargeUI(self.accounting_system, booking.client, activity, descr, fixed_amount=True,
                                      fixed_descr=True)
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
        width, height = 600, 500
        self.resize(width, height)

        self.central_widget = QWidget(self)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, width, height))
        self.layout = QVBoxLayout(self.widget)
        config_layout(self.layout, left_margin=30, top_margin=10, right_margin=30, bottom_margin=10, spacing=20)

        # Utilities.
        self.utils_layout = QHBoxLayout()
        self.layout.addLayout(self.utils_layout)

        self.search_box = SearchBox(
            filters=[ClientLike("name", display_name="Nombre",
                                translate_fun=lambda booking, value: booking.client.cli_name.contains(value))],
            parent=self.widget)
        self.utils_layout.addWidget(self.search_box)

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "Busq", font_size=16)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        config_layout(self.form_layout, spacing=10)

        self.booking_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.booking_lbl, 0, 0, 1, 1)
        config_lbl(self.booking_lbl, "Reserva")

        self.booking_combobox = QComboBox()
        self.form_layout.addWidget(self.booking_combobox, 0, 1, 1, 1)
        config_combobox(self.booking_combobox, height=35)

        self.client_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.client_lbl, 1, 0, 1, 1)
        config_lbl(self.client_lbl, "Cliente")

        self.client_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.client_line, 1, 1, 1, 1)
        config_line(self.client_line, height=35, enabled=False)

        self.court_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.court_lbl, 2, 0, 1, 1)
        config_lbl(self.court_lbl, "Cancha")

        self.court_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.court_line, 2, 1, 1, 1)
        config_line(self.court_line, height=35, enabled=False)

        self.date_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.date_lbl, 3, 0, 1, 1)
        config_lbl(self.date_lbl, "Fecha")

        self.date_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.date_line, 3, 1, 1, 1)
        config_line(self.date_line, height=35, enabled=False)

        self.block_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.block_lbl, 4, 0, 1, 1)
        config_lbl(self.block_lbl, "Inicio")

        self.start_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.start_line, 4, 1, 1, 1)
        config_line(self.start_line, height=35, enabled=False)

        self.duration_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.duration_lbl, 5, 0, 1, 1)
        config_lbl(self.duration_lbl, "Fin")

        self.end_line = QLineEdit(self.widget)
        self.form_layout.addWidget(self.end_line, 5, 1, 1, 1)
        config_line(self.end_line, height=35, enabled=False)

        self.fixed_checkbox = QCheckBox()
        self.layout.addWidget(self.fixed_checkbox, alignment=Qt.AlignCenter)
        config_checkbox(self.fixed_checkbox, checked=False, text="Turno fijo", enabled=False)

        self.confirm_btn = QPushButton(self.widget)
        self.layout.addWidget(self.confirm_btn, alignment=Qt.AlignCenter)
        config_btn(self.confirm_btn, "Siguiente", font_size=18, width=200)
