import functools
from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTableWidget, QPushButton, QDesktopWidget,
    QLabel, QDateEdit, QHBoxLayout)

from gym_manager.core.base import TextLike
from gym_manager.core.persistence import FilterValuePair, ClientRepo, TransactionRepo, SubscriptionRepo
from gym_manager.core.security import SecurityHandler
from gym_manager.old_app_info import OldChargesRepo, OldCharge, OldExtraction, OldExtractionRepo, confirm_old_charge
from ui.widget_config import new_config_table, config_btn, config_lbl, fill_cell, config_date_edit
from ui.widgets import FilterHeader, PageIndex, Dialog, DialogWithResp


class OldChargesUI(QMainWindow):

    def __init__(
            self,
            client_repo: ClientRepo,
            transaction_repo: TransactionRepo,
            subscription_repo: SubscriptionRepo,
            security_handler: SecurityHandler
    ) -> None:
        super().__init__()
        self._setup_ui()

        self.client_repo = client_repo
        self.transaction_repo = transaction_repo
        self.subscription_repo = subscription_repo
        self.security_handler = security_handler

        self._charges: dict[int, OldCharge] = {}
        OldChargesRepo.create_model()

        # Configure the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name",
                            translate_fun=lambda old_charge, value: old_charge.client.cli_name.contains(value)),)
        self.filter_header.config(filters, on_search_click=self.fill_charges_table)

        # Configures the page index.
        self.page_index.config(refresh_table=self.filter_header.on_search_click, page_len=20, show_info=False)

        self.filter_header.on_search_click()

        # noinspection PyUnresolvedReferences
        self.remove_btn.clicked.connect(self.remove_charge)

    def _setup_ui(self):
        self.setWindowTitle("Cobros en aplicación vieja")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        self.info_lbl = QLabel(self.widget)
        self.layout.addWidget(self.info_lbl)
        config_lbl(self.info_lbl, "Aquí se muestran los cobros realizados en los últimos dos meses en la aplicación "
                                  "anterior.")

        # Filtering.
        self.filter_header = FilterHeader(parent=self.widget)
        self.layout.addWidget(self.filter_header)

        self.remove_btn = QPushButton(self.widget)
        self.layout.addWidget(self.remove_btn, alignment=Qt.AlignLeft)
        config_btn(self.remove_btn, "Eliminar cobro")

        # Old charges.
        self.charges_table = QTableWidget(self.widget)
        self.layout.addWidget(self.charges_table)
        new_config_table(self.charges_table, width=600, allow_resizing=False, min_rows_to_show=10,
                         columns={"Cliente": (.4, str), "Actividad": (.4, str), "Cuota": (.2, bool), "Monto": (.2, int)}
                         )

        # Index.
        self.page_index = PageIndex(self.widget)
        self.layout.addWidget(self.page_index)

        self.setFixedSize(self.minimumSizeHint())

        self.move(int(QDesktopWidget().geometry().center().x() - self.sizeHint().width() / 2),
                  int(QDesktopWidget().geometry().center().y() - self.sizeHint().height() / 2))

    def _add_charge(self, charge: OldCharge):
        row = self.charges_table.rowCount()
        self._charges[row] = charge
        fill_cell(self.charges_table, row, 0, charge.client_name, data_type=str)
        fill_cell(self.charges_table, row, 1, charge.activity_name, data_type=str)
        fill_cell(self.charges_table, row, 2, f"{charge.month}/{charge.year}", data_type=bool)
        fill_cell(self.charges_table, row, 3, charge.transaction_amount, data_type=int)

    def fill_charges_table(self, filters: list[FilterValuePair]):
        self.charges_table.setRowCount(0)
        self._charges.clear()

        for old_charge in OldChargesRepo.all(self.page_index.page, self.page_index.page_len, filters):
            self._add_charge(old_charge)

    def remove_charge(self):
        row = self.charges_table.currentRow()
        if row == -1:
            Dialog.info("Error", "Seleccione un cobro.")
            return

        charge = self._charges[row]

        fn = functools.partial(confirm_old_charge, self.client_repo, self.transaction_repo, self.subscription_repo,
                               charge)
        if DialogWithResp.confirm(
                f"¿Desea confirmar el cobro de la cuota '{charge.month}/{charge.year}' por la actividad "
                f"'{charge.activity_name}' a '{charge.client_name}'?", self.security_handler, fn
        ):
            self._charges.pop(row)
            self.filter_header.on_search_click()  # Refreshes the table.

            Dialog.info("Éxito", f"Cobro de '{charge.activity_name}' a '{charge.client_name}', cuota "
                                 f"{charge.month}/{charge.year} confirmado.")


class OldExtractionsUI(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

        OldExtractionRepo.create_model()

        # Configures the page index.
        self.page_index.config(refresh_table=self.fill_extraction_table, page_len=20, show_info=False)

        self.fill_extraction_table()

        # noinspection PyUnresolvedReferences
        self.date_edit.dateChanged.connect(self.fill_extraction_table)

    def _setup_ui(self):
        self.setWindowTitle("Extracciones en aplicación vieja")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)

        self.info_lbl = QLabel(self.widget)
        self.layout.addWidget(self.info_lbl)
        config_lbl(self.info_lbl, "Aquí se muestran las extracciones en los últimos dos meses en la aplicación "
                                  "anterior.")

        # Filtering.
        self.filter_layout = QHBoxLayout()
        self.layout.addLayout(self.filter_layout)
        self.filter_layout.setContentsMargins(250, 0, 250, 0)

        self.date_lbl = QLabel(self.widget)
        self.filter_layout.addWidget(self.date_lbl, alignment=Qt.AlignCenter)
        config_lbl(self.date_lbl, "Fecha")

        self.date_edit = QDateEdit(self.widget)
        self.filter_layout.addWidget(self.date_edit, alignment=Qt.AlignCenter)
        config_date_edit(self.date_edit, date.today(), calendar=True)

        # Old extractions.
        self.extraction_table = QTableWidget(self.widget)
        self.layout.addWidget(self.extraction_table)
        new_config_table(self.extraction_table, width=600, allow_resizing=False, min_rows_to_show=10,
                         columns={"Día": (.2, bool), "Responsable": (.4, str), "Monto": (.2, bool),
                                  "Descripción": (.4, str)})

        # Index.
        self.page_index = PageIndex(self.widget)
        self.layout.addWidget(self.page_index)

        self.setFixedSize(self.minimumSizeHint())

        self.move(int(QDesktopWidget().geometry().center().x() - self.sizeHint().width() / 2),
                  int(QDesktopWidget().geometry().center().y() - self.sizeHint().height() / 2))

    def _add_extraction(self, extraction: OldExtraction):
        row = self.extraction_table.rowCount()
        fill_cell(self.extraction_table, row, 0, extraction[1], data_type=bool)
        fill_cell(self.extraction_table, row, 1, extraction[2], data_type=str)
        fill_cell(self.extraction_table, row, 2, extraction[3], data_type=int)
        fill_cell(self.extraction_table, row, 3, extraction[4], data_type=str)

    def fill_extraction_table(self):
        self.extraction_table.setRowCount(0)

        for old_extraction in OldExtractionRepo.all(self.page_index.page, self.page_index.page_len,
                                                    self.date_edit.date().toPyDate()):
            self._add_extraction(old_extraction)
