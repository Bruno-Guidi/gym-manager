from datetime import date

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, \
    QSizePolicy, QLabel, QTableWidget, QComboBox, QLineEdit, QDateEdit

from gym_manager.core.base import ONE_MONTH_TD
from ui.widget_config import config_layout, config_btn, config_lbl, config_combobox, config_line, config_table, \
    config_date_edit


# class Controller:
#
#     def __init__(self, booking_system: BookingSystem, bookings: QTableWidget, page_label: QLabel,
#                  cancelled_checkbox: QCheckBox) -> None:
#         self.booking_system = booking_system
#
#         self.bookings = bookings
#         self.page_label = page_label
#         self.cancelled_checkbox = cancelled_checkbox
#
#         self.current_page = 1
#         self.states = {State.TO_HAPPEN: "Por suceder", State.CANCELLED: "Cancelado", State.PAID: "Pago"}
#         self.update_history()
#
#     def prev_clicked(self):
#         if self.current_page > 0:
#             self.current_page -= 1
#             self.update_history()
#
#     def next_clicked(self):
#         self.current_page += 1
#         self.update_history()
#
#     def update_history(self):
#         self.page_label.setText(str(self.current_page))
#
#         items_per_page = 14
#         states = [State.PAID, State.CANCELLED] if self.cancelled_checkbox.isChecked() else [State.PAID]
#         booking_gen = self.booking_system.history(states, self.current_page, items_per_page)
#
#         self.bookings.setRowCount(0)  # Clears the table.
#         self.bookings.setRowCount(items_per_page)
#         for row, booking in enumerate(booking_gen):
#             add_cell(self.bookings, row, 0, str(booking.when))
#             add_cell(self.bookings, row, 1, booking.start.strftime("%H:%M"))
#             add_cell(self.bookings, row, 2, booking.end.strftime("%H:%M"))
#             add_cell(self.bookings, row, 3, str(booking.court))
#             add_cell(self.bookings, row, 4, str(booking.client.name))
#             add_cell(self.bookings, row, 5, self.states[booking.state.name])
#             add_cell(self.bookings, row, 6, str(booking.state.updated_by))


class AccountingMainUI(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        # self.controller = Controller(booking_system, self.payment_table, self.page_label, self.cancelled_checkbox)

    def _setup_ui(self):
        self.resize(800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, 800, 600))

        self.main_layout = QVBoxLayout(self.widget)
        config_layout(self.main_layout, left_margin=10, top_margin=10, right_margin=10, bottom_margin=10)

        # Utilities.
        self.utils_layout = QHBoxLayout()
        self.main_layout.addLayout(self.utils_layout)
        config_layout(self.utils_layout, spacing=0, left_margin=40, top_margin=15, right_margin=80)

        self.filter_combobox = QComboBox(self.widget)
        self.utils_layout.addWidget(self.filter_combobox)
        config_combobox(self.filter_combobox, font_size=16)

        self.search_box = QLineEdit(self.widget)
        self.utils_layout.addWidget(self.search_box)
        config_line(self.search_box, place_holder="Búsqueda", font_size=16)

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "Busq", font_size=16)

        self.utils_layout.addItem(QSpacerItem(80, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.from_line = QDateEdit()
        self.utils_layout.addWidget(self.from_line)
        config_date_edit(self.from_line, date.today() - ONE_MONTH_TD, calendar=True,
                         layout_direction=Qt.LayoutDirection.RightToLeft)

        self.to_line = QDateEdit()
        self.utils_layout.addWidget(self.to_line)
        config_date_edit(self.to_line, date.today(), calendar=True, layout_direction=Qt.LayoutDirection.RightToLeft)

        self.main_layout.addItem(QSpacerItem(80, 15, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Payments.
        self.payment_table = QTableWidget(self.widget)
        self.main_layout.addWidget(self.payment_table)
        config_table(
            target=self.payment_table, allow_resizing=True,
            columns={"#": 100, "Cliente": 175, "Fecha": 100, "Monto": 100, "Método": 120, "Responsable": 175,
                     "Descripción": 200}
        )

        # Index.
        self.index_layout = QHBoxLayout()
        self.main_layout.addLayout(self.index_layout)
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
