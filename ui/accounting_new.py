from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QDateEdit, QComboBox,
    QSpacerItem, QSizePolicy, QTableWidget, QLabel, QGridLayout, QPushButton, QLineEdit)

from ui.widget_config import (
    config_layout, config_checkbox, config_date_edit, config_combobox, config_table,
    config_lbl, config_btn, config_line)
from ui.widgets import Separator


class MainController:
    pass


class AccountingMainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_ui()

        self.controller = MainController()

    def _setup_ui(self):
        self.setWindowTitle("Contabilidad")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        # Left layout.
        self.left_layout = QVBoxLayout()
        self.layout.addLayout(self.left_layout)

        self.layout.addWidget(Separator(vertical=True, parent=self.widget))  # Vertical line.

        # Right layout.
        self.right_layout = QVBoxLayout()
        self.layout.addLayout(self.right_layout)

        # Today info layout.
        self.today_layout = QGridLayout()
        self.left_layout.addLayout(self.today_layout)

        self.today_charges_lbl = QLabel(self.widget)
        self.today_layout.addWidget(self.today_charges_lbl, 0, 0)
        config_lbl(self.today_charges_lbl, "Cobros del día")

        self.today_charges_line = QLineEdit(self.widget)
        self.today_layout.addWidget(self.today_charges_line, 1, 0)
        config_line(self.today_charges_line, place_holder="00000,00", enabled=False)

        self.close_balance_btn = QPushButton(self.widget)
        self.today_layout.addWidget(self.close_balance_btn, 0, 1, 2, 1)
        config_btn(self.close_balance_btn, "Cerrar caja", font_size=16)

        self.left_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Balance detail.
        self.detail_layout = QGridLayout()
        self.left_layout.addLayout(self.detail_layout)

        # Balance date label.
        self.day_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.day_lbl, 0, 0, 1, 5, alignment=Qt.AlignCenter)
        config_lbl(self.day_lbl, "dd/mm/aaaa", font_size=18)

        # Detailed balance layout.
        self.method_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.method_lbl, 1, 0)
        config_lbl(self.method_lbl, "Método")

        self.charges_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.charges_lbl, 2, 0)
        config_lbl(self.charges_lbl, "Cobros")

        self.extractions_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.extractions_lbl, 3, 0)
        config_lbl(self.extractions_lbl, "Extracciones")

        self.cash_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.cash_lbl, 1, 1)
        config_lbl(self.cash_lbl, "Efectivo")

        self.debit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.debit_lbl, 1, 2)
        config_lbl(self.debit_lbl, "Débito")

        self.credit_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.credit_lbl, 1, 3)
        config_lbl(self.credit_lbl, "Crédito")

        self.total_lbl = QLabel(self.widget)
        self.detail_layout.addWidget(self.total_lbl, 1, 4)
        config_lbl(self.total_lbl, "TOTAL")

        # Transactions included in the balance.
        self.transactions_lbl = QLabel(self.widget)
        self.left_layout.addWidget(self.transactions_lbl)
        config_lbl(self.transactions_lbl, "Transacciones", font_size=16)

        self.transaction_table = QTableWidget(self.widget)
        self.left_layout.addWidget(self.transaction_table)
        config_table(self.transaction_table, allow_resizing=False,
                     columns={"Responsable": (8, str), "Monto": (8, int), "Descripción": (12, str)})

        # Filters.
        self.filters_layout = QHBoxLayout()
        self.right_layout.addLayout(self.filters_layout)

        self.last_n_checkbox = QCheckBox(self.widget)
        self.filters_layout.addWidget(self.last_n_checkbox)
        config_checkbox(self.last_n_checkbox, "Últimos", checked=True, layout_dir=Qt.LayoutDirection.LeftToRight)

        self.date_edit = QDateEdit(self.widget)
        self.filters_layout.addWidget(self.date_edit)
        config_date_edit(self.date_edit, date.today(), calendar=True)

        self.date_checkbox = QCheckBox(self.widget)
        self.filters_layout.addWidget(self.date_checkbox)
        config_checkbox(self.date_checkbox, "Fecha", checked=False, layout_dir=Qt.LayoutDirection.LeftToRight)

        self.last_n_combobox = QComboBox(self.widget)
        self.filters_layout.addWidget(self.last_n_combobox)
        config_combobox(self.last_n_combobox, extra_width=20, fixed_width=self.date_edit.width())

        # Horizontal spacer.
        self.right_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Transactions.
        self.balance_table = QTableWidget(self.widget)
        self.right_layout.addWidget(self.balance_table)
        config_table(
            target=self.balance_table, allow_resizing=True, min_rows_to_show=1,
            columns={"Fecha": (10, int), "Responsable": (12, str), "Cobros": (12, int),
                     "Extracciones": (12, int)}
        )


