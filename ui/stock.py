from __future__ import annotations

import functools

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QSpacerItem, QSizePolicy, QDialog, QGridLayout, QTableWidget, QComboBox, QCheckBox, QMenu, QAction)

from gym_manager.core.base import String, Currency, TextLike, Number
from gym_manager.core.persistence import FilterValuePair, TransactionRepo
from gym_manager.core.security import SecurityHandler
from gym_manager.stock.core import (
    ItemRepo, Item, create_item, update_item, remove_item, update_item_amount,
    register_item_charge)
from ui import utils
from ui.accounting import ChargeUI
from ui.widget_config import (
    config_lbl, config_line, config_btn, fill_cell, new_config_table, config_combobox, fill_combobox, config_checkbox)
from ui.widgets import Field, Dialog, FilterHeader, PageIndex, Separator, DialogWithResp


class MainController:
    def __init__(
            self, main_ui: StockMainUI, item_repo: ItemRepo, transaction_repo: TransactionRepo,
            security_handler: SecurityHandler
    ):
        self.main_ui = main_ui
        self.item_repo = item_repo
        self.transaction_repo = transaction_repo
        self.security_handler = security_handler
        self.items: dict[int, Item] = {}  # Dict that maps row number to the item that it displays.

        # Configure the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name"),)
        self.main_ui.filter_header.config(filters, on_search_click=self.fill_item_table)

        # Configures the page index.
        self.main_ui.page_index.config(refresh_table=self.main_ui.filter_header.on_search_click, page_len=40,
                                       show_info=False)

        # Fills the table.
        self.main_ui.filter_header.on_search_click()

        decrease_stock = ("Reducir stock", functools.partial(self._update_item_amount, True))
        increase_stock = ("Agregar stock", functools.partial(self._update_item_amount, False))
        charge_item = ("Cobrar item", self._charge_item)
        fill_combobox(self.main_ui.action_combobox, (decrease_stock, increase_stock, charge_item),
                      display=lambda pair: pair[0])

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.main_ui.create_action.triggered.connect(self.create_item)
        # noinspection PyUnresolvedReferences
        self.main_ui.edit_action.triggered.connect(self.edit_item)
        # noinspection PyUnresolvedReferences
        self.main_ui.remove_btn.clicked.connect(self.remove)
        # noinspection PyUnresolvedReferences
        self.main_ui.item_table.itemSelectionChanged.connect(self.refresh_form)
        # noinspection PyUnresolvedReferences
        self.main_ui.confirm_btn.clicked.connect(self.execute_action)

    def _add_item(self, item: Item, check_filters: bool, check_limit: bool = False):
        if check_limit and self.main_ui.item_table.rowCount() == self.main_ui.page_index.page_len:
            return

        if check_filters and not self.main_ui.filter_header.passes_filters(item):
            return

        row = self.main_ui.item_table.rowCount()
        self.items[row] = item
        fill_cell(self.main_ui.item_table, row, 0, item.name, data_type=str)
        fill_cell(self.main_ui.item_table, row, 1, Currency.fmt(item.price), data_type=int)
        fill_cell(self.main_ui.item_table, row, 2, item.amount, data_type=int)

    def fill_item_table(self, filters: list[FilterValuePair]):
        self.main_ui.item_table.setRowCount(0)

        for item in self.item_repo.all(self.main_ui.page_index.page, self.main_ui.page_index.page_len, filters):
            self._add_item(item, check_filters=False)  # Activities are filtered in the repo.

    def refresh_form(self):
        row = self.main_ui.item_table.currentRow()
        if row != -1:
            self.main_ui.name_field.setText(str(self.items[row].name))
            self.main_ui.price_field.setText(Currency.fmt(self.items[row].price, symbol=''))
        else:
            # Clears the form.
            self.main_ui.name_field.clear()
            self.main_ui.price_field.clear()

    def create_item(self):
        # noinspection PyAttributeOutsideInit
        self._create_ui = CreateUI(self.item_repo)
        self._create_ui.exec_()
        if self._create_ui.controller.item is not None:
            self._add_item(self._create_ui.controller.item, check_filters=True, check_limit=True)

    def edit_item(self):
        if self.main_ui.item_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un item en la tabla.")
            return

        item = self.items[self.main_ui.item_table.currentRow()]
        # noinspection PyAttributeOutsideInit
        self._edit_ui = EditUI(self.item_repo, item)
        self._edit_ui.exec_()

        # Updates the ui.
        row = self.main_ui.item_table.currentRow()
        fill_cell(self.main_ui.item_table, row, 0, item.name, data_type=str, increase_row_count=False)
        fill_cell(self.main_ui.item_table, row, 1, Currency.fmt(item.price), data_type=int,
                  increase_row_count=False)

    def remove(self):
        if self.main_ui.item_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un ítem.")
            return

        item = self.items[self.main_ui.item_table.currentRow()]

        if Dialog.confirm(f"¿Desea eliminar el ítem '{item.name}'?"):
            remove_item(self.item_repo, item)

            self.items.pop(item.name.as_primitive())
            self.main_ui.filter_header.on_search_click()  # Refreshes the table.

            # Clears the form.
            self.main_ui.name_field.clear()
            self.main_ui.price_field.clear()

            Dialog.info("Éxito", f"El ítem '{item.name}' fue eliminado correctamente.")

    def _update_item_amount(self, decrease: bool):
        if self.main_ui.item_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un item.")
            return

        item = self.items[self.main_ui.item_table.currentRow()]
        # noinspection PyTypeChecker
        if (not self.main_ui.amount_field.valid_value()
                or (decrease and self.main_ui.amount_field.value() > item.amount)):
            Dialog.info("Error", "La cantidad no es válida.")
            return

        fn = functools.partial(update_item_amount, self.item_repo, item, self.main_ui.amount_field.value(), decrease)
        if DialogWithResp.confirm(f"Ingrese el responsable", self.security_handler, fn):
            fill_cell(self.main_ui.item_table, self.main_ui.item_table.currentRow(), 2, item.amount, data_type=int,
                      increase_row_count=False)
            self.main_ui.amount_field.clear()

    def _charge_item(self):
        if self.main_ui.item_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un item.")
            return

        item = self.items[self.main_ui.item_table.currentRow()]
        # noinspection PyTypeChecker
        if not self.main_ui.amount_field.valid_value() or self.main_ui.amount_field.value() > item.amount:
            Dialog.info("Error", "La cantidad no es válida.")
            return

        register_charge = functools.partial(register_item_charge, self.item_repo, item,
                                            self.main_ui.amount_field.value())
        total = item.total_price(self.main_ui.amount_field.value().as_primitive())
        # noinspection PyAttributeOutsideInit
        self._charge_ui = ChargeUI(
            self.transaction_repo, self.security_handler, total,
            String(f"Cobro de {self.main_ui.amount_field.value()} '{item.name}' por un total de {Currency.fmt(total)}"),
            post_charge_fn=register_charge
        )
        self._charge_ui.exec_()

        if self._charge_ui.controller.success:
            fill_cell(self.main_ui.item_table, self.main_ui.item_table.currentRow(), 2, item.amount, data_type=int)
            self.main_ui.amount_field.clear()

    def execute_action(self):
        self.main_ui.action_combobox.currentData(Qt.UserRole)[1]()


class StockMainUI(QMainWindow):

    def __init__(
            self, item_repo: ItemRepo, transaction_repo: TransactionRepo, security_handler: SecurityHandler
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, item_repo, transaction_repo, security_handler)

    def _setup_ui(self):
        self.setWindowTitle("Stock")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        # Menu bar.
        menu_bar = self.menuBar()

        client_menu = QMenu("&Items", self)
        menu_bar.addMenu(client_menu)

        self.create_action = QAction("&Agregar", self)
        client_menu.addAction(self.create_action)

        self.edit_action = QAction("&Editar", self)
        client_menu.addAction(self.edit_action)

        self.remove_action = QAction("&Eliminar", self)
        client_menu.addAction(self.remove_action)

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

        self.name_field = Field(String, self.widget, max_len=utils.ACTIVITY_NAME_CHARS, optional=False)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre")

        # Price.
        self.price_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.price_lbl, 1, 0)
        config_lbl(self.price_lbl, "Precio*")

        self.price_field = Field(Currency, self.widget, positive=True)
        self.form_layout.addWidget(self.price_field, 1, 1)
        config_line(self.price_field, place_holder="000000,00")

        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Layout with actions to execute related to stock.
        self.action_layout = QGridLayout()
        self.right_layout.addLayout(self.action_layout)

        self.action_lbl = QLabel(self.widget)
        self.action_layout.addWidget(self.action_lbl, 0, 0)
        config_lbl(self.action_lbl, "Acción")

        self.amount_lbl = QLabel(self.widget)
        self.action_layout.addWidget(self.amount_lbl, 1, 0)
        config_lbl(self.amount_lbl, "Cantidad*")

        self.amount_field = Field(Number, parent=self.widget, optional=False, min_value=1)
        self.action_layout.addWidget(self.amount_field, 1, 1)
        config_line(self.amount_field)

        self.action_combobox = QComboBox(self.widget)
        self.action_layout.addWidget(self.action_combobox, 0, 1)
        config_combobox(self.action_combobox, fixed_width=self.amount_field.width())

        self.confirm_btn = QPushButton(self.widget)
        self.right_layout.addWidget(self.confirm_btn, alignment=Qt.AlignCenter)
        config_btn(self.confirm_btn, "Confirmar")

        # Vertical spacer.
        self.right_layout.addSpacerItem(QSpacerItem(20, 90, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        self.setFixedSize(self.minimumSizeHint())


class CreateController:

    def __init__(self, create_ui: CreateUI, item_repo: ItemRepo) -> None:
        self.create_ui = create_ui

        self.item: Item | None = None
        self.item_repo = item_repo

        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_item)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    # noinspection PyTypeChecker
    def create_item(self):
        if not all([self.create_ui.name_field.valid_value(), self.create_ui.price_field.valid_value(),
                    self.create_ui.amount_field.valid_value()]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            self.item = create_item(self.item_repo, self.create_ui.name_field.value(),
                                    self.create_ui.amount_field.value(), self.create_ui.price_field.value(),
                                    is_fixed=self.create_ui.fixed_checkbox.isChecked())
            Dialog.info("Éxito", f"El ítem '{self.create_ui.name_field.value()}' fue creado correctamente.")
            self.create_ui.name_field.window().close()


class CreateUI(QDialog):
    def __init__(self, item_repo: ItemRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, item_repo)

    def _setup_ui(self):
        self.setWindowTitle("Nuevo ítem")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self, max_len=utils.ACTIVITY_NAME_CHARS, optional=False)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # Price.
        self.price_lbl = QLabel(self)
        self.form_layout.addWidget(self.price_lbl, 1, 0)
        config_lbl(self.price_lbl, "Precio*")

        self.price_field = Field(Currency, parent=self, positive=True)
        self.form_layout.addWidget(self.price_field, 1, 1)
        config_line(self.price_field, place_holder="000000,00", adjust_to_hint=False)

        # Price.
        self.amount_lbl = QLabel(self)
        self.form_layout.addWidget(self.amount_lbl, 2, 0)
        config_lbl(self.amount_lbl, "Cantidad*")

        self.amount_field = Field(Number, parent=self, min_value=1, optional=False)
        self.form_layout.addWidget(self.amount_field, 2, 1)
        config_line(self.amount_field, adjust_to_hint=False)

        # Fixed.
        self.fixed_lbl = QLabel(self)
        self.form_layout.addWidget(self.fixed_lbl, 3, 0)
        config_lbl(self.fixed_lbl, "Ítem fijo")

        self.fixed_checkbox = QCheckBox(self)
        self.form_layout.addWidget(self.fixed_checkbox, 3, 1)
        config_checkbox(self.fixed_checkbox, checked=False)

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


class EditController:

    def __init__(self, edit_ui: EditUI, item_repo: ItemRepo, item: Item) -> None:
        self.edit_ui = edit_ui

        self.item = item
        self.item_repo = item_repo

        # noinspection PyUnresolvedReferences
        self.edit_ui.confirm_btn.clicked.connect(self.edit_item)
        # noinspection PyUnresolvedReferences
        self.edit_ui.cancel_btn.clicked.connect(self.edit_ui.reject)

    # noinspection PyTypeChecker
    def edit_item(self):
        if not all([self.edit_ui.name_field.valid_value(), self.edit_ui.price_field.valid_value()]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            update_item(self.item_repo, self.item, self.edit_ui.name_field.value(), self.edit_ui.price_field.value())

            Dialog.info("Éxito", f"El ítem '{self.item.name}' fue actualizado correctamente.")
            self.edit_ui.name_field.window().close()


class EditUI(QDialog):
    def __init__(self, item_repo: ItemRepo, item: Item) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = EditController(self, item_repo, item)

    def _setup_ui(self):
        self.setWindowTitle("Editar ítem")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self, max_len=utils.ACTIVITY_NAME_CHARS, optional=False)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # Price.
        self.price_lbl = QLabel(self)
        self.form_layout.addWidget(self.price_lbl, 1, 0)
        config_lbl(self.price_lbl, "Precio*")

        self.price_field = Field(Currency, parent=self, positive=True)
        self.form_layout.addWidget(self.price_field, 1, 1)
        config_line(self.price_field, place_holder="000000,00", adjust_to_hint=False)

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
