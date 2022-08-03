from __future__ import annotations

import functools

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QSpacerItem, QSizePolicy, QTextEdit, QDialog, QGridLayout, QTableWidget)

from gym_manager.core.base import String, Activity, Currency, TextLike
from gym_manager.core.persistence import ActivityRepo, FilterValuePair
from gym_manager.core.security import SecurityHandler, log_responsible
from gym_manager.stock.core import ItemRepo, Item
from ui import utils
from ui.widget_config import (
    config_lbl, config_line, config_btn, fill_cell, new_config_table)
from ui.widgets import Field, valid_text_value, Dialog, FilterHeader, PageIndex, Separator, DialogWithResp


@log_responsible(action_tag="update_activity", to_str=lambda activity: f"Actualizar actividad {activity.name}")
def update_activity(activity_repo: ActivityRepo, activity: Activity, price: Currency, description: String):
    activity.price = price
    activity.description = description
    activity_repo.update(activity)

    return activity


class MainController:
    def __init__(
            self, main_ui: StockMainUI, item_repo: ItemRepo, security_handler: SecurityHandler
    ):
        self.main_ui = main_ui
        self.item_repo = item_repo
        self.security_handler = security_handler
        self.items: dict[str, Item] = {}  # Dict that maps raw items name to the associated activity.

        # Configure the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name"),)
        self.main_ui.filter_header.config(filters, on_search_click=self.fill_item_table)

        # Configures the page index.
        self.main_ui.page_index.config(refresh_table=self.main_ui.filter_header.on_search_click, page_len=40)

        # Fills the table.
        self.main_ui.filter_header.on_search_click()

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.main_ui.create_btn.clicked.connect(self.create_ui)
        # noinspection PyUnresolvedReferences
        self.main_ui.save_btn.clicked.connect(self.save_changes)
        # noinspection PyUnresolvedReferences
        self.main_ui.remove_btn.clicked.connect(self.remove)
        # noinspection PyUnresolvedReferences
        self.main_ui.item_table.itemSelectionChanged.connect(self.refresh_form)

    def _add_item(self, item: Item, check_filters: bool, check_limit: bool = False):
        if check_limit and self.main_ui.item_table.rowCount() == self.main_ui.page_index.page_len:
            return

        if check_filters and not self.main_ui.filter_header.passes_filters(item):
            return

        self.items[item.name.as_primitive()] = item
        row = self.main_ui.item_table.rowCount()
        fill_cell(self.main_ui.item_table, row, 0, item.name, data_type=str)
        fill_cell(self.main_ui.item_table, row, 1, Currency.fmt(item.price), data_type=int)
        fill_cell(self.main_ui.item_table, row, 2, item.amount, data_type=int)

    def fill_item_table(self, filters: list[FilterValuePair]):
        self.main_ui.item_table.setRowCount(0)

        # for activity in self.item_repo.all(self.main_ui.page_index.page, self.main_ui.page_index.page_len, filters):
        #     self.items[activity.name.as_primitive()] = activity
        #     self._add_item(activity, check_filters=False)  # Activities are filtered in the repo.

    def refresh_form(self):
        if self.main_ui.item_table.currentRow() != -1:
            item_name = self.main_ui.item_table.item(self.main_ui.item_table.currentRow(), 0).text()
            self.main_ui.name_field.setText(str(self.items[item_name].name))
            self.main_ui.price_field.setText(Currency.fmt(self.items[item_name].price, symbol=''))
        else:
            # Clears the form.
            self.main_ui.name_field.clear()
            self.main_ui.price_field.clear()

    def create_ui(self):
        # noinspection PyAttributeOutsideInit
        pass
        # self._create_ui = CreateUI(self.item_repo)
        # self._create_ui.exec_()
        # if self._create_ui.controller.activity is not None:
        #     self._add_item(self._create_ui.controller.activity, check_filters=True, check_limit=True)
        #     self.main_ui.page_index.total_len += 1

    def save_changes(self):
        pass
        # if self.main_ui.item_table.currentRow() == -1:
        #     Dialog.info("Error", "Seleccione un item.")
        #     return
        #
        # if not all([self.main_ui.name_field.valid_value(), self.main_ui.price_field.valid_value()]):
        #     Dialog.info("Error", "Hay datos que no son válidos.")
        # else:
        #     activity_name = self.main_ui.item_table.item(self.main_ui.item_table.currentRow(), 0).text()
        #     activity = self.items[activity_name]
        #     update_fn = functools.partial(update_activity, self.item_repo, self.items[activity_name],
        #                                   self.main_ui.price_field.value(), descr)
        #
        #     if DialogWithResp.confirm(f"Ingrese el responsable.", self.security_handler, update_fn):
        #         # Updates the activity.
        #         activity.price, activity.description = self.main_ui.price_field.value(), descr
        #         self.item_repo.update(activity)
        #
        #         # Updates the ui.
        #         row = self.main_ui.item_table.currentRow()
        #         fill_cell(self.main_ui.item_table, row, 0, activity.name, data_type=str, increase_row_count=False)
        #         # noinspection PyTypeChecker
        #         fill_cell(self.main_ui.item_table, row, 1, Currency.fmt(activity.price), data_type=int,
        #                   increase_row_count=False)
        #         fill_cell(self.main_ui.item_table, row, 2, self.item_repo.n_subscribers(activity),
        #                   data_type=int, increase_row_count=False)
        #
        #         Dialog.info("Éxito", f"La actividad '{activity.name}' fue actualizada correctamente.")

    def remove(self):
        pass
        # if self.main_ui.item_table.currentRow() == -1:
        #     Dialog.info("Error", "Seleccione una actividad.")
        #     return
        #
        # activity_name = self.main_ui.item_table.item(self.main_ui.item_table.currentRow(), 0).text()
        # activity = self.items[activity_name]
        # if activity.locked:
        #     Dialog.info("Error", f"No esta permitido eliminar la actividad '{activity.name}'.")
        #     return
        #
        # remove_fn = functools.partial(self.item_repo.remove, activity)
        # if DialogWithResp.confirm(f"¿Desea eliminar la actividad '{activity.name}'?", self.security_handler, remove_fn):
        #     self.items.pop(activity.name.as_primitive())
        #     self.main_ui.filter_header.on_search_click()  # Refreshes the table.
        #
        #     # Clears the form.
        #     self.main_ui.name_field.clear()
        #     self.main_ui.price_field.clear()
        #     self.main_ui.description_text.clear()
        #
        #     Dialog.info("Éxito", f"La actividad '{activity.name}' fue eliminada correctamente.")


class StockMainUI(QMainWindow):

    def __init__(self, item_repo: ItemRepo, security_handler: SecurityHandler) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, item_repo, security_handler)

    def _setup_ui(self):
        self.setWindowTitle("Stock")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        self.left_layout = QVBoxLayout()
        self.layout.addLayout(self.left_layout)
        self.left_layout.setContentsMargins(10, 0, 10, 0)

        self.layout.addWidget(Separator(vertical=True, parent=self.widget))  # Vertical line.

        self.right_layout = QVBoxLayout()
        self.layout.addLayout(self.right_layout)
        self.right_layout.setContentsMargins(10, 0, 10, 0)

        # Filtering.
        self.filter_header = FilterHeader(parent=self.widget)
        self.left_layout.addWidget(self.filter_header)

        # Items.
        self.item_table = QTableWidget(self.widget)
        self.left_layout.addWidget(self.item_table)
        new_config_table(self.item_table, width=600, allow_resizing=False,
                         columns={"Nombre": (.55, str), "Precio": (.25, int), "Cantidad": (.2, int)},
                         min_rows_to_show=10)

        # Index.
        self.page_index = PageIndex(self.widget)
        self.left_layout.addWidget(self.page_index)

        # Buttons.
        # Vertical spacer.
        self.right_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        self.buttons_layout = QHBoxLayout()
        self.right_layout.addLayout(self.buttons_layout)
        self.buttons_layout.setContentsMargins(80, 0, 80, 0)

        self.create_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.create_btn)
        config_btn(self.create_btn, icon_path="ui/resources/add.png", icon_size=48)

        self.save_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.save_btn)
        config_btn(self.save_btn, icon_path="ui/resources/save.png", icon_size=48)

        self.remove_btn = QPushButton(self.widget)
        self.buttons_layout.addWidget(self.remove_btn)
        config_btn(self.remove_btn, icon_path="ui/resources/remove.png", icon_size=48)

        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Item data form.
        self.form_layout = QGridLayout()
        self.right_layout.addLayout(self.form_layout)

        # Name.
        self.name_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, self.widget, max_len=utils.ACTIVITY_NAME_CHARS)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False, enabled=False)

        # Price.
        self.price_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.price_lbl, 1, 0)
        config_lbl(self.price_lbl, "Precio*")

        self.price_field = Field(Currency, self.widget)
        self.form_layout.addWidget(self.price_field, 1, 1)
        config_line(self.price_field, place_holder="000000,00", adjust_to_hint=False)

        # Vertical spacer.
        self.right_layout.addSpacerItem(QSpacerItem(20, 90, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        self.setFixedSize(self.minimumSizeHint())


class CreateController:

    def __init__(self, create_ui: CreateUI, activity_repo: ActivityRepo) -> None:
        self.create_ui = create_ui

        self.activity: Activity | None = None
        self.activity_repo = activity_repo

        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_activity)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    # noinspection PyTypeChecker
    def create_activity(self):
        valid_descr, descr = valid_text_value(self.create_ui.description_text, optional=True,
                                              max_len=utils.ACTIVITY_DESCR_CHARS)
        valid_fields = all([self.create_ui.name_field.valid_value(), self.create_ui.price_field.valid_value()])
        if not valid_fields:
            Dialog.info("Error", "Hay datos que no son válidos.")
        elif self.activity_repo.exists(self.create_ui.name_field.value()):
            Dialog.info("Error", f"Ya existe una categoría con el nombre '{self.create_ui.name_field.value()}'.")
        else:
            self.activity = Activity(self.create_ui.name_field.value(), self.create_ui.price_field.value(), descr)
            self.activity_repo.add(self.activity)
            Dialog.info("Éxito", f"La categoría '{self.create_ui.name_field.value()}' fue creada correctamente.")
            self.create_ui.name_field.window().close()


class CreateUI(QDialog):
    def __init__(self, activity_repo: ActivityRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, activity_repo)

    def _setup_ui(self):
        self.setWindowTitle("Nueva actividad")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self, max_len=utils.ACTIVITY_NAME_CHARS)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # Price.
        self.price_lbl = QLabel(self)
        self.form_layout.addWidget(self.price_lbl, 1, 0)
        config_lbl(self.price_lbl, "Precio*")

        self.price_field = Field(Currency, self)
        self.form_layout.addWidget(self.price_field, 1, 1)
        config_line(self.price_field, place_holder="000000,00", adjust_to_hint=False)

        # Description.
        self.description_lbl = QLabel(self)
        self.form_layout.addWidget(self.description_lbl, 2, 0, alignment=Qt.AlignTop)
        config_lbl(self.description_lbl, "Descripción")

        self.description_text = QTextEdit(self)
        self.form_layout.addWidget(self.description_text, 2, 1)
        config_line(self.description_text, place_holder="Descripción", adjust_to_hint=False)

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