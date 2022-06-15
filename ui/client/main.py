from typing import Callable, Iterable

from PyQt5.QtCore import QRect, Qt, QSize
from PyQt5.QtWidgets import QMainWindow, QWidget, QListWidget, QHBoxLayout, QLabel, QPushButton, \
    QListWidgetItem, QVBoxLayout, QTableWidget, QComboBox, QLineEdit, QSpacerItem, QSizePolicy, QTableWidgetItem, \
    QMessageBox

from gym_manager.core.persistence import ClientRepo
from ui.client.create import CreateUI
from ui.widget_config import config_lbl, config_line, config_btn, config_layout, config_combobox, config_table
from ui.widgets import Field


# class ClientRow(QWidget):
#     def __init__(
#             self, client: Client, client_repo: ClientRepo, item: QListWidgetItem,
#             change_selected_item: Callable[[QListWidgetItem], None],
#             height: int, total_width: int, name_width: int, dni_width: int, admission_width: int, tel_width: int,
#             dir_width: int
#     ):
#         super().__init__()
#         self.client = client
#         self.client_repo = client_repo
#         self.item = item
#         self.change_selected_item = change_selected_item
#
#         self._setup_ui(client, height, total_width, name_width, dni_width, admission_width, tel_width, dir_width)
#
#         # Because the widgets are yet to be hided, the hint has the 'extended' height.
#         self.current_height, self.previous_height = height, self.widget.sizeHint().height()
#
#         self.detail_hidden = True
#         self.detail_btn.clicked.connect(self.hide_detail)
#         self.save_btn.clicked.connect(self.save_changes)
#         self.hide_detail()
#
#         self.load_activities()
#
#     def _setup_ui(
#             self, client: Client, height: int, total_width: int, name_width: int, dni_width: int, admission_width: int,
#             tel_width: int, dir_width: int
#     ):
#         self.widget = QWidget(self)
#         self.widget.setGeometry(QRect(0, 0, total_width, height))
#
#         self.row_layout = QVBoxLayout(self.widget)
#
#         self.top_layout = QHBoxLayout()
#         self.row_layout.addLayout(self.top_layout)
#         config_layout(self.top_layout, alignment=Qt.AlignLeft)
#
#         # Name layout.
#         self.name_layout = QVBoxLayout()
#         self.top_layout.addLayout(self.name_layout)
#
#         self.name_summary = QLabel(self.widget)
#         self.name_layout.addWidget(self.name_summary, alignment=Qt.AlignTop)
#         config_lbl(self.name_summary, text=client.name, width=name_width, height=height - 15)
#
#         self.name_lbl = QLabel(self.widget)
#         self.name_layout.addWidget(self.name_lbl, alignment=Qt.AlignBottom)
#         config_lbl(self.name_lbl, "Nombre", font_size=12, width=name_width)
#
#         self.name_field = Field(String, self.widget, optional=False, max_len=name_max_chars)
#         self.name_layout.addWidget(self.name_field)
#         config_line(self.name_field, text=client.name, width=name_width)
#
#         # DNI layout.
#         self.dni_layout = QVBoxLayout()
#         self.top_layout.addLayout(self.dni_layout)
#
#         self.dni_summary = QLabel(self.widget)
#         self.dni_layout.addWidget(self.dni_summary, alignment=Qt.AlignTop)
#         config_lbl(self.dni_summary, text=str(client.dni), width=dni_width, height=height - 15)
#
#         self.dni_lbl = QLabel(self.widget)
#         self.dni_layout.addWidget(self.dni_lbl, alignment=Qt.AlignBottom)
#         config_lbl(self.dni_lbl, "DNI", font_size=12, width=dni_width)
#
#         self.dni_field = Field(Number, self.widget, min_value=min_dni_value, max_value=max_dni_value)
#         self.dni_layout.addWidget(self.dni_field)
#         config_line(self.dni_field, text=str(client.dni), width=dni_width, enabled=False)
#
#         # Admission layout.
#         self.admission_layout = QVBoxLayout()
#         self.top_layout.addLayout(self.admission_layout)
#
#         self.admission_summary = QLabel(self.widget)
#         self.admission_layout.addWidget(self.admission_summary, alignment=Qt.AlignTop)
#         config_lbl(self.admission_summary, text=str(client.admission), width=admission_width, height=height - 15)
#
#         self.admission_lbl = QLabel(self.widget)
#         self.admission_layout.addWidget(self.admission_lbl, alignment=Qt.AlignBottom)
#         config_lbl(self.admission_lbl, "Ingreso", font_size=12, width=admission_width)
#
#         self.admission_field = Field(Date, self.widget, format=date_formats)
#         self.admission_layout.addWidget(self.admission_field)
#         config_line(self.admission_field, text=str(client.admission), width=admission_width)
#
#         # Telephone layout.
#         self.tel_layout = QVBoxLayout()
#         self.top_layout.addLayout(self.tel_layout)
#
#         self.tel_summary = QLabel(self.widget)
#         self.tel_layout.addWidget(self.tel_summary, alignment=Qt.AlignTop)
#         config_lbl(self.tel_summary, text=str(client.telephone), width=tel_width, height=height - 15)
#
#         self.tel_lbl = QLabel(self.widget)
#         self.tel_layout.addWidget(self.tel_lbl, alignment=Qt.AlignBottom)
#         config_lbl(self.tel_lbl, "Teléfono", font_size=12, width=tel_width)
#
#         self.tel_field = Field(String, self.widget, optional=True, max_len=tel_max_chars)
#         self.tel_layout.addWidget(self.tel_field)
#         config_line(self.tel_field, text=str(client.telephone), width=tel_width)
#
#         # Direction layout.
#         self.dir_layout = QVBoxLayout()
#         self.top_layout.addLayout(self.dir_layout)
#
#         self.dir_summary = QLabel(self.widget)
#         self.dir_layout.addWidget(self.dir_summary, alignment=Qt.AlignTop)
#         config_lbl(self.dir_summary, text=str(client.direction), width=dir_width, height=height - 15)
#
#         self.dir_lbl = QLabel(self.widget)
#         self.dir_layout.addWidget(self.dir_lbl, alignment=Qt.AlignBottom)
#         config_lbl(self.dir_lbl, "Dirección", font_size=12, width=dir_width)
#
#         self.dir_field = Field(String, self.widget, optional=True, max_len=dir_max_chars)
#         self.dir_layout.addWidget(self.dir_field)
#         config_line(self.dir_field, text=str(client.direction), width=dir_width)
#
#         # Some buttons.
#         self.top_buttons_layout = QVBoxLayout()
#         self.top_layout.addLayout(self.top_buttons_layout)
#
#         self.detail_btn = QPushButton(self.widget)
#         self.top_buttons_layout.addWidget(self.detail_btn, alignment=Qt.AlignTop)
#         config_btn(self.detail_btn, text="Detalle", width=100)
#
#         self.save_btn = QPushButton(self.widget)
#         self.top_buttons_layout.addWidget(self.save_btn)
#         config_btn(self.save_btn, text="Guardar", width=100)
#
#         self.remove_client_btn = QPushButton(self.widget)
#         self.top_buttons_layout.addWidget(self.remove_client_btn)
#         config_btn(self.remove_client_btn, text="Eliminar", width=100)
#
#         # Activities.
#         self.activities_lbl = QLabel(self.widget)
#         self.row_layout.addWidget(self.activities_lbl)
#         config_lbl(self.activities_lbl, "Actividades", font_size=12)
#
#         # Layout that contains activities and other buttons.
#         self.bottom_layout = QHBoxLayout()
#         self.row_layout.addLayout(self.bottom_layout)
#         config_layout(self.bottom_layout, alignment=Qt.AlignCenter)
#
#         self.activities_table = QTableWidget(self.widget)
#         self.bottom_layout.addWidget(self.activities_table)
#         config_table(self.activities_table,
#                      columns={"Nombre": 280, "Último\npago": 100, "Código\npago": 146, "Vencida": 90},
#                      allow_resizing=True)  # ToDo. Set min width.
#
#         # Buttons.
#         self.bottom_buttons_layout = QVBoxLayout()
#         self.bottom_layout.addLayout(self.bottom_buttons_layout)
#         config_layout(self.bottom_buttons_layout, alignment=Qt.AlignTop)
#
#         self.add_activity_btn = QPushButton(self.widget)
#         self.bottom_buttons_layout.addWidget(self.add_activity_btn)
#         config_btn(self.add_activity_btn, text="Nueva\nactividad", width=100)
#
#         self.remove_activity_btn = QPushButton(self.widget)
#         self.bottom_buttons_layout.addWidget(self.remove_activity_btn)
#         config_btn(self.remove_activity_btn, text="Eliminar\nactividad", width=100)
#
#         self.charge_activity_btn = QPushButton(self.widget)
#         self.bottom_buttons_layout.addWidget(self.charge_activity_btn)
#         config_btn(self.charge_activity_btn, text="Cobrar\nactividad", width=100)
#
#         self.payments_btn = QPushButton(self.widget)
#         self.bottom_buttons_layout.addWidget(self.payments_btn)
#         config_btn(self.payments_btn, text="Ver pagos", width=100)
#
#     def hide_detail(self):
#         # Hides widgets.
#         self.name_lbl.setHidden(self.detail_hidden)
#         self.name_field.setHidden(self.detail_hidden)
#         self.dni_lbl.setHidden(self.detail_hidden)
#         self.dni_field.setHidden(self.detail_hidden)
#         self.admission_lbl.setHidden(self.detail_hidden)
#         self.admission_field.setHidden(self.detail_hidden)
#         self.tel_lbl.setHidden(self.detail_hidden)
#         self.tel_field.setHidden(self.detail_hidden)
#         self.dir_lbl.setHidden(self.detail_hidden)
#         self.dir_field.setHidden(self.detail_hidden)
#
#         self.activities_lbl.setHidden(self.detail_hidden)
#         self.activities_table.setHidden(self.detail_hidden)
#
#         self.save_btn.setHidden(self.detail_hidden)
#         self.remove_client_btn.setHidden(self.detail_hidden)
#         self.add_activity_btn.setHidden(self.detail_hidden)
#         self.remove_activity_btn.setHidden(self.detail_hidden)
#         self.charge_activity_btn.setHidden(self.detail_hidden)
#         self.payments_btn.setHidden(self.detail_hidden)
#
#         # Updates state.
#         self.change_selected_item(self.item)
#         new_width = self.widget.sizeHint().width() - 3
#         self.item.setSizeHint(QSize(new_width, self.current_height))
#         self.resize(new_width, self.current_height)
#         self.widget.resize(new_width, self.current_height)
#
#         self.previous_height, self.current_height = self.current_height, self.previous_height
#         self.detail_hidden = not self.detail_hidden
#
#     # noinspection PyTypeChecker
#     def save_changes(self):
#         valid = all([self.name_field.valid_value(), self.dni_field.valid_value(), self.admission_field.valid_value(),
#                      self.tel_field.valid_value(), self.dir_field.valid_value()])
#         if not valid:
#             QMessageBox.about(self.name_field.window(), "Error", "Hay datos que no son válidos.")
#         else:
#             self.client_repo.update(self.client)
#             # Updates client object.
#             self.client.name = self.name_field.value().as_primitive()
#             self.client.admission = self.admission_field.value().as_primitive()
#             self.client.telephone = self.tel_field.value().as_primitive()
#             self.client.direction = self.dir_field.value().as_primitive()
#
#             # Updates ui.
#             self.name_lbl.setText(self.client.name)
#             self.admission_lbl.setText(str(self.client.admission))
#             self.tel_lbl.setText(self.client.telephone)
#             self.dir_lbl.setText(self.client.direction)
#
#             QMessageBox.about(self.name_field.window(), "Éxito",
#                               f"El cliente '{self.name_field.value()}' fue actualizado correctamente.")
#
#     def load_activities(self):
#         self.activities_table.setRowCount(self.client.n_activities())
#
#         for row, entry in enumerate(self.client.activities):
#             self.activities_table.setItem(row, 0, QTableWidgetItem(entry.activity.name))
#             self.activities_table.setItem(row, 1, QTableWidgetItem(entry.last_paid_on))
#             self.activities_table.setItem(row, 2, QTableWidgetItem(entry.payment_id))


class Controller:
    def __init__(self, client_repo: ClientRepo, client_list: QListWidget):
        self.client_repo = client_repo
        self.current_page = 1
        self.current_row = None

        self.client_list = client_list

        self.load_clients()

    def load_clients(self):
        self.client_list.clear()  # ToDo Delete when ToDo below is done.

        for client in self.client_repo.all(page_number=self.current_page, items_per_page=15):
            item = QListWidgetItem(self.client_list)
            item.setText(f"{client.name.as_primitive()} {client.dni.as_primitive()} {str(client.admission)}")
            self.client_list.addItem(item)
            # row = ClientRow(client, self.client_repo, item, change_selected_item=self.client_list.setCurrentItem,
            #                 height=50, total_width=800, name_width=175, dni_width=90, admission_width=100, tel_width=110,
            #                 dir_width=140)
            # self.client_list.setItemWidget(item, row)

    def add_client(self):
        self.add_ui = CreateUI(self.client_repo)
        self.add_ui.exec_()
        self.load_clients()  # ToDo Instead of this, put the new client in the top of the page.


class ClientMainUI(QMainWindow):

    def __init__(self, client_repo: ClientRepo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        name_width, dni_width, admission_width, tel_width, dir_width = 175, 90, 100, 110, 140
        self._setup_ui(name_width, dni_width, admission_width, tel_width, dir_width)
        self.controller = Controller(client_repo, self.client_list)
        self._setup_callbacks()

    def _setup_ui(self, name_width: int, dni_width: int, admission_width: int, tel_width: int, dir_width: int):
        self.resize(800, 600)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.widget = QWidget(self.central_widget)
        self.widget.setGeometry(QRect(0, 0, 800, 600))

        self.main_layout = QVBoxLayout(self.widget)

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

        self.create_client_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.create_client_btn)
        config_btn(self.create_client_btn, "Nuevo cliente", font_size=16)

        self.main_layout.addItem(QSpacerItem(80, 15, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Header.
        self.header_layout = QHBoxLayout()
        self.main_layout.addLayout(self.header_layout)
        config_layout(self.header_layout, alignment=Qt.AlignLeft, left_margin=11, spacing=0)

        self.name_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.name_lbl)
        config_lbl(self.name_lbl, "Nombre", width=name_width + 6)  # 6 is the spacing.

        self.dni_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.dni_lbl)
        config_lbl(self.dni_lbl, "DNI", width=dni_width + 6)  # 6 is the spacing.

        self.admission_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.admission_lbl)
        config_lbl(self.admission_lbl, "Ingreso", width=admission_width + 6)  # 6 is the spacing.

        self.tel_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.tel_lbl)
        config_lbl(self.tel_lbl, "Teléfono", width=tel_width + 6)  # 6 is the spacing.

        self.dir_lbl = QLabel(self.widget)
        self.header_layout.addWidget(self.dir_lbl)
        config_lbl(self.dir_lbl, "Dirección", width=dir_width + 6)  # 6 is the spacing.

        # Clients.
        self.client_list = QListWidget(self.widget)
        self.main_layout.addWidget(self.client_list)

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

    def _setup_callbacks(self):
        self.create_client_btn.clicked.connect(self.controller.add_client)

