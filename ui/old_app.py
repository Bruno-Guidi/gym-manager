from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QPushButton, QDesktopWidget,
    QLabel)

from gym_manager.core.base import TextLike
from gym_manager.core.persistence import FilterValuePair
from gym_manager.old_app_info import OldChargesRepo, OldCharge
from ui.widget_config import new_config_table, config_btn, config_lbl, fill_combobox, fill_cell
from ui.widgets import FilterHeader, PageIndex


class OldChargesUI(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

        self._charges: dict[int, OldCharge] = {}
        OldChargesRepo.create_model()

        # Configure the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name",
                            translate_fun=lambda old_charge, value: old_charge.client_name.contains(value)),)
        self.filter_header.config(filters, on_search_click=self.fill_charges_table)

        # Configures the page index.
        self.page_index.config(refresh_table=self.filter_header.on_search_click, page_len=20, show_info=False)

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
        fill_cell(self.charges_table, row, 0, charge[0], data_type=str)
        fill_cell(self.charges_table, row, 1, charge[1], data_type=str)
        fill_cell(self.charges_table, row, 2, f"{charge[2]/charge[3]}", data_type=bool)
        fill_cell(self.charges_table, row, 3, charge[4], data_type=int)

    def fill_charges_table(self, filters: list[FilterValuePair]):
        self.charges_table.setRowCount(0)
        self._charges.clear()

        for old_charge in OldChargesRepo.all(self.page_index.page, self.page_index.page_len, filters):
            self._add_charge(old_charge)
