import typing
from datetime import timedelta, date

from PyQt5 import QtCore
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QCalendarWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, \
    QSizePolicy, QLabel, QTableWidget, QMenuBar, QStatusBar, QAction, QTableWidgetItem, QDateEdit

# class Controller:
#
#     def __init__(
#             self, client_repo: ClientRepo, booking_system: BookingSystem, calendar: QCalendarWidget,
#             date_label: QLabel, bookings_table: QTableWidget, b: QPushButton
#     ) -> None:
#         self.client_repo = client_repo
#         self.booking_system = booking_system
#
#         self._aux_timedelta = timedelta(days=1)
#
#         self.calendar = calendar
#         self.date_label = date_label
#         self.bookings = bookings_table
#         self.b = b
#
#         self.calendar.hide()  # By default the calendar is hided.
#         self.update_current_date()
#
#     def update_calendar_visibility(self):
#         if self.calendar.isVisible():
#             self.calendar.hide()
#         else:
#             self.calendar.show()
#
#     def charge_for_booking(self):
#         self.charge_ui = ChargeUI(self.booking_system)
#         self.charge_ui.exec_()
#
#     def book(self):
#         self.book_gui = BookUI(self.client_repo, self.booking_system, self.calendar.selectedDate().toPyDate())
#         self.book_gui.exec_()
#
#         self._update_bookings()  # After the booking is created, update the booking table.
#
#     def cancel_booking(self):
#         self.cancel_ui = CancelUI(self.booking_system)
#         self.cancel_ui.exec_()
#
#         self._update_bookings()  # After the booking is cancelled, update the booking table.
#
#     def selected_date_to_next(self):
#         self.calendar.setSelectedDate(self.calendar.selectedDate().toPyDate() + self._aux_timedelta)
#         self.update_current_date()
#
#     def selected_date_to_prev(self):
#         self.calendar.setSelectedDate(self.calendar.selectedDate().toPyDate() - self._aux_timedelta)
#         self.update_current_date()
#
#     def _update_bookings(self):
#         self.bookings.setRowCount(0)  # Clears the table.
#
#         # Loads the hour column.
#         booking_units = [booking_unit for booking_unit in self.booking_system.booking_units(include_passed=True)]
#         self.bookings.setRowCount(len(booking_units))
#         for row, booking_unit in enumerate(booking_units):
#             item = QTableWidgetItem(booking_unit.as_range)
#             item.setTextAlignment(Qt.AlignCenter)
#             self.bookings.setItem(row, 0, item)
#
#         # Loads the bookings for the day.
#         for booking in self.booking_system.bookings(self.calendar.selectedDate().toPyDate()):
#             start, end = self.booking_system.booking_unit_range(booking)
#             for number in range(start, end):
#                 item = QTableWidgetItem(f"{booking.client.name}{' (Fijo)' if booking.is_fixed else ''}")
#                 item.setTextAlignment(Qt.AlignCenter)
#                 self.bookings.setItem(number, self.booking_system.court_id(booking.court), item)
#
#     def update_current_date(self):
#         self.date_label.setText(str(self.calendar.selectedDate().toPyDate()))  # Updates current selected date.
#         self.b.setEnabled(self.calendar.selectedDate().toPyDate() >= date.today())  # Blocks the btn if the day passed.
#         self._update_bookings()
#
#     def see_history(self):
#         self.booking_history = BookingHistoryUI(self.booking_system)
#         self.booking_history.setWindowModality(Qt.ApplicationModal)
#         self.booking_history.show()
from ui.widget_config import config_layout, config_btn, config_lbl, config_table, config_date_edit


class BookingMainUI(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        # self.controller = Controller(client_repo, booking_system, self.calendar, self.date_label, self.bookings,
        #                              self.book_button)
        self._setup_callbacks()

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

        self.book_button = QPushButton(self.widget)
        self.buttons_hbox.addWidget(self.book_button)
        config_btn(self.book_button, "Reservar turno", font_size=18, width=200)

        self.cancel_button = QPushButton(self.widget)
        self.buttons_hbox.addWidget(self.cancel_button)
        config_btn(self.cancel_button, "Cancelar turno", font_size=18, width=200)

        self.spacer_item = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.vbox.addItem(self.spacer_item)

        self.date_hbox = QHBoxLayout()
        self.vbox.addLayout(self.date_hbox)
        config_layout(self.date_hbox)

        # self.calendar_button = QPushButton(self.widget)
        # self.date_hbox.addWidget(self.calendar_button)
        # config_btn(self.calendar_button, width=40, height=36, icon_path="gui/resources/calendar-icon.png",
        #               icon_width=40, icon_height=36, style_sheet="border: none;")

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

    def _setup_callbacks(self):
        pass
        # self.see_history_action.triggered.connect(self.controller.see_history)
        # self.calendar_button.clicked.connect(self.controller.update_calendar_visibility)
        # self.charge_button.clicked.connect(self.controller.charge_for_booking)
        # self.book_button.clicked.connect(self.controller.book)
        # self.cancel_button.clicked.connect(self.controller.cancel_booking)
        # self.calendar.clicked.connect(self.controller.update_current_date)
        # self.prev_button.clicked.connect(self.controller.selected_date_to_prev)
        # self.next_button.clicked.connect(self.controller.selected_date_to_next)
