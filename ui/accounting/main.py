from datetime import date

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, \
    QSizePolicy, QLabel, QTableWidget, QComboBox, QLineEdit, QDateEdit, QTableWidgetItem

from gym_manager.core.accounting import PaymentSystem
from gym_manager.core.base import ONE_MONTH_TD
from ui.widget_config import config_layout, config_btn, config_lbl, config_combobox, config_line, config_table, \
    config_date_edit


class Controller:

    def __init__(
            self, payment_system: PaymentSystem, payment_table: QTableWidget, from_line: QDateEdit, to_line: QDateEdit
    ) -> None:
        self.payment_table = payment_table
        self.from_line = from_line
        self.to_line = to_line

        self.payment_system = payment_system
        self.current_page, self.items_per_page = 1, 20

        self.load_payments()

    def load_payments(self):
        self.payment_table.setRowCount(0)
        self.payment_table.setRowCount(self.items_per_page)

        payments = self.payment_system.payments(from_date=self.from_line.date().toPyDate(),
                                                to_date=self.to_line.date().toPyDate())
        for row, payment in enumerate(payments):
            self.payment_table.setItem(row, 0, QTableWidgetItem(str(payment.id)))
            self.payment_table.setItem(row, 1, QTableWidgetItem(str(payment.client.name)))
            self.payment_table.setItem(row, 2, QTableWidgetItem(str(payment.when)))
            self.payment_table.setItem(row, 3, QTableWidgetItem(str(payment.amount)))
            self.payment_table.setItem(row, 4, QTableWidgetItem(str(payment.method)))
            self.payment_table.setItem(row, 5, QTableWidgetItem(str(payment.responsible)))
            self.payment_table.setItem(row, 6, QTableWidgetItem(str(payment.description)))


class AccountingMainUI(QMainWindow):

    def __init__(self, payment_system: PaymentSystem) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(payment_system, self.payment_table, self.from_line, self.to_line)

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
        config_layout(self.utils_layout, spacing=0, left_margin=40, top_margin=15, right_margin=40)

        self.filter_combobox = QComboBox(self.widget)
        self.utils_layout.addWidget(self.filter_combobox)
        config_combobox(self.filter_combobox, font_size=16)

        self.search_box = QLineEdit(self.widget)
        self.utils_layout.addWidget(self.search_box)
        config_line(self.search_box, place_holder="Filtro", font_size=16)

        self.utils_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.from_layout = QVBoxLayout()
        self.utils_layout.addLayout(self.from_layout)

        self.from_lbl = QLabel()
        self.from_layout.addWidget(self.from_lbl)
        config_lbl(self.from_lbl, "Desde", font_size=16, alignment=Qt.AlignCenter)

        self.from_line = QDateEdit()
        self.from_layout.addWidget(self.from_line)
        config_date_edit(self.from_line, date.today() - ONE_MONTH_TD, calendar=True,
                         layout_direction=Qt.LayoutDirection.RightToLeft)

        self.utils_layout.addItem(QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.to_layout = QVBoxLayout()
        self.utils_layout.addLayout(self.to_layout)

        self.to_lbl = QLabel()
        self.to_layout.addWidget(self.to_lbl)
        config_lbl(self.to_lbl, "Hasta", font_size=16, alignment=Qt.AlignCenter)

        self.to_line = QDateEdit()
        self.to_layout.addWidget(self.to_line)
        config_date_edit(self.to_line, date.today(), calendar=True, layout_direction=Qt.LayoutDirection.RightToLeft)

        self.utils_layout.addItem(QSpacerItem(30, 20, QSizePolicy.Minimum, QSizePolicy.Minimum))

        self.search_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.search_btn)
        config_btn(self.search_btn, "Busq", font_size=16)

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
