from __future__ import annotations

from datetime import date

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSpacerItem, \
    QSizePolicy, QLabel, QTableWidget, QDateEdit, QTableWidgetItem

from gym_manager.core.system import AccountingSystem
from gym_manager.core.base import ONE_MONTH_TD, Client, DateGreater, ClientLike, DateLesser, TextEqual, TextLike
from ui.widget_config import config_layout, config_btn, config_lbl, config_table, \
    config_date_edit
from ui.widgets import SearchBox


class Controller:

    def __init__(
            self, main_ui: AccountingMainUI, accounting_system: AccountingSystem, client: Client | None = None
    ) -> None:
        self.main_ui = main_ui

        self.accounting_system = accounting_system
        self.current_page, self.page_len = 1, 20

        # If a client is given, set the filter with it.
        if client is not None:
            self.main_ui.search_box.set_filter("client", client.name.as_primitive())
        self.load_transactions()

        # Sets callbacks
        # noinspection PyUnresolvedReferences
        self.main_ui.search_btn.clicked.connect(self.load_transactions)

    def load_transactions(self):
        self.main_ui.transaction_table.setRowCount(0)
        self.main_ui.transaction_table.setRowCount(self.page_len)

        from_date_filter = DateGreater("from", display_name="Desde",
                                       translate_fun=lambda trans, when: trans.when >= when)
        to_date_filter = DateLesser("to", display_name="Hasta",
                                    translate_fun=lambda trans, when: trans.when <= when)
        transactions = self.accounting_system.transactions(
            self.current_page, self.page_len,
            from_date=(from_date_filter, self.main_ui.from_line.date().toPyDate()),
            to_date=(to_date_filter, self.main_ui.to_line.date().toPyDate()),
            **self.main_ui.search_box.filters()
        )
        for row, transaction in enumerate(transactions):
            self.main_ui.transaction_table.setItem(row, 0, QTableWidgetItem(str(transaction.id)))
            self.main_ui.transaction_table.setItem(row, 1, QTableWidgetItem(str(transaction.type)))
            self.main_ui.transaction_table.setItem(row, 2, QTableWidgetItem(str(transaction.client.name)))
            self.main_ui.transaction_table.setItem(row, 3, QTableWidgetItem(str(transaction.when)))
            self.main_ui.transaction_table.setItem(row, 4, QTableWidgetItem(str(transaction.amount)))
            self.main_ui.transaction_table.setItem(row, 5, QTableWidgetItem(str(transaction.method)))
            self.main_ui.transaction_table.setItem(row, 6, QTableWidgetItem(str(transaction.responsible)))
            self.main_ui.transaction_table.setItem(row, 7, QTableWidgetItem(str(transaction.description)))


class AccountingMainUI(QMainWindow):

    def __init__(self, accounting_system: AccountingSystem, client: Client | None = None) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(self, accounting_system, client)

        self.search_btn.clicked.connect(self.controller.load_transactions)

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

        self.search_box = SearchBox(
            filters=[ClientLike("client", display_name="Cliente",
                                translate_fun=lambda trans, value: trans.client.cli_name.contains(value)),
                     TextEqual("type", display_name="Tipo", attr="type",
                               translate_fun=lambda trans, value: trans.type == value),
                     TextEqual("method", display_name="Método", attr="method",
                               translate_fun=lambda trans, value: trans.method == value),
                     TextLike("responsible", display_name="Responsable", attr="responsible",
                              translate_fun=lambda trans, value: trans.responsible.contains(value))],
            parent=self.widget
        )
        self.utils_layout.addWidget(self.search_box)

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

        # Transactions.
        self.transaction_table = QTableWidget(self.widget)
        self.main_layout.addWidget(self.transaction_table)
        config_table(
            target=self.transaction_table, allow_resizing=True,
            columns={"#": 100, "Tipo": 70, "Cliente": 175, "Fecha": 100, "Monto": 100, "Método": 120,
                     "Responsable": 175,
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
