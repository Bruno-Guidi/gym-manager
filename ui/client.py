from __future__ import annotations

import functools
import itertools
from datetime import date
from typing import Iterable, Callable

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QSpacerItem, QSizePolicy, QDialog, QGridLayout, QTableWidget, QComboBox,
    QDateEdit, QListWidget, QListWidgetItem, QAction, QMenu, QButtonGroup, QRadioButton,
    QSpinBox, QDesktopWidget)

from gym_manager.contact.core import ContactRepo, create_contact, remove_contact_by_client
from gym_manager.core import api
from gym_manager.core.base import (
    String, TextLike, Client, Number, Activity, Subscription, Currency, from_month_to_month, year_month_iterator)
from gym_manager.core.persistence import FilterValuePair, ClientRepo, SubscriptionRepo, TransactionRepo
from gym_manager.core.security import SecurityHandler, SecurityError
from ui import utils
from ui.utils import MESSAGE
from ui.widget_config import (
    config_lbl, config_line, config_btn, fill_cell, config_combobox, fill_combobox, config_date_edit, new_config_table,
    config_widget)
from ui.widgets import Field, Dialog, FilterHeader, PageIndex, Separator, responsible_field


class MainController:
    def __init__(
            self,
            main_ui: ClientMainUI,
            client_repo: ClientRepo,
            subscription_repo: SubscriptionRepo,
            transaction_repo: TransactionRepo,
            security_handler: SecurityHandler,
            activities_fn: Callable[[], Iterable[Activity]],
            contact_repo: ContactRepo | None = None
    ):
        self.main_ui = main_ui
        self.client_repo = client_repo
        self.contact_repo = contact_repo
        self.subscription_repo = subscription_repo
        self.transaction_repo = transaction_repo
        self.security_handler = security_handler
        self.activities_fn = activities_fn
        self._clients: dict[int, Client] = {}  # Dict that maps row numbers to the displayed client.
        self._subscriptions: dict[str, Subscription] = {}  # Maps raw activity name to subs of the selected client.

        # Configure the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name",
                            translate_fun=lambda client, value: client.cli_name.contains(value)),)
        self.main_ui.filter_header.config(filters, on_search_click=self.fill_client_table)

        # Configures the page index.
        self.main_ui.page_index.config(refresh_table=self.main_ui.filter_header.on_search_click,
                                       page_len=20, total_len=self.client_repo.count())

        self.main_ui.all_charges.setChecked(True)  # By default, all months are displayed.

        self._enable_subscribe()

        # Fills the table.
        self.main_ui.filter_header.on_search_click()

        # Fills the combobox with the transaction methods.
        fill_combobox(self.main_ui.method_combobox, ("Efectivo", "Débito", "Crédito"),
                      display=lambda method_name: method_name)

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.main_ui.create_action.triggered.connect(self.create_client)
        # noinspection PyUnresolvedReferences
        self.main_ui.edit_action.triggered.connect(self.edit_client)
        # noinspection PyUnresolvedReferences
        self.main_ui.remove_action.triggered.connect(self.remove_client)
        # noinspection PyUnresolvedReferences
        self.main_ui.client_table.itemSelectionChanged.connect(self.update_client_info)
        # noinspection PyUnresolvedReferences
        self.main_ui.subscribe_btn.clicked.connect(self.create_subscription)
        # noinspection PyUnresolvedReferences
        self.main_ui.subscription_list.currentItemChanged.connect(self.fill_charge_table)
        # noinspection PyUnresolvedReferences
        self.main_ui.subscription_list.itemPressed.connect(self.fill_months_to_charge)
        # noinspection PyUnresolvedReferences
        self.main_ui.year_spinbox.valueChanged.connect(self.fill_charge_table)
        # noinspection PyUnresolvedReferences
        self.main_ui.cancel_btn.clicked.connect(self.cancel_subscription)
        # noinspection PyUnresolvedReferences
        self.main_ui.charge_filter_group.buttonClicked.connect(self.fill_charge_table)
        # noinspection PyUnresolvedReferences
        self.main_ui.charge_table.itemSelectionChanged.connect(self.set_unpaid_month)
        # noinspection PyUnresolvedReferences
        self.main_ui.charge_btn.clicked.connect(self.charge_subscription)

    def _enable_subscribe(self):
        client_selected = self.main_ui.client_table.currentRow() != -1
        self.main_ui.subscribe_combobox.setEnabled(client_selected
                                                   and self.main_ui.subscribe_combobox.currentIndex() != -1)
        self.main_ui.subscribe_btn.setEnabled(client_selected
                                              and self.main_ui.subscribe_combobox.currentIndex() != -1)

        self.main_ui.cancel_btn.setEnabled(len(self.main_ui.subscription_list) > 0)

        sub_selected = self.main_ui.subscription_list.currentRow() != -1
        self.main_ui.year_spinbox.setEnabled(sub_selected)
        self.main_ui.all_charges.setEnabled(sub_selected)
        self.main_ui.only_paid_charges.setEnabled(sub_selected)
        self.main_ui.only_unpaid_charges.setEnabled(sub_selected)

        self.main_ui.method_combobox.setEnabled(client_selected)
        self.main_ui.amount_line.setEnabled(client_selected)
        self.main_ui.month_combobox.setEnabled(client_selected)
        self.main_ui.charge_btn.setEnabled(client_selected)

    def _add_client(self, client: Client, check_filters: bool, check_limit: bool = False):
        if check_limit and self.main_ui.client_table.rowCount() == self.main_ui.page_index.page_len:
            return

        if check_filters and not self.main_ui.filter_header.passes_filters(client):
            return

        row = self.main_ui.client_table.rowCount()
        self._clients[row] = client
        fill_cell(self.main_ui.client_table, row, 0, client.name, data_type=str)
        dni = "" if client.dni.as_primitive() is None else client.dni.as_primitive()
        fill_cell(self.main_ui.client_table, row, 1, dni, data_type=int)
        fill_cell(self.main_ui.client_table, row, 2, client.admission, data_type=bool)
        fill_cell(self.main_ui.client_table, row, 3, client.age(), data_type=int)

    def fill_client_table(self, filters: list[FilterValuePair]):
        self.main_ui.client_table.setRowCount(0)
        self._clients.clear()

        self.main_ui.page_index.total_len = self.client_repo.count(filters)
        for client in self.client_repo.all(self.main_ui.page_index.page, self.main_ui.page_index.page_len, filters):
            self._add_client(client, check_filters=False)  # Clients are filtered in the repo.

    def update_client_info(self):
        row = self.main_ui.client_table.currentRow()
        if row != -1:
            client = self._clients[row]

            subscribeable_activities = itertools.filterfalse(
                lambda activity: activity.charge_once or client.is_subscribed(activity), self.activities_fn()
            )
            fill_combobox(self.main_ui.subscribe_combobox, subscribeable_activities,
                          display=lambda activity: activity.name.as_primitive())
            self.fill_subscription_list()

            self._enable_subscribe()

    def create_client(self):
        # noinspection PyAttributeOutsideInit
        self._create_ui = CreateUI(self.client_repo, self.contact_repo)
        self._create_ui.exec_()
        if self._create_ui.controller.client is not None:
            self._add_client(self._create_ui.controller.client, check_filters=True, check_limit=True)
            self.main_ui.page_index.total_len += 1
            self._enable_subscribe()

    def edit_client(self):
        row = self.main_ui.client_table.currentRow()
        if row == -1:
            Dialog.info("Error", "Seleccione un cliente en la tabla.")
            return

        # noinspection PyAttributeOutsideInit
        self._edit_ui = EditUI(self.client_repo, self._clients[row])
        self._edit_ui.exec_()

        # Updates the ui.
        client = self._edit_ui.controller.client
        fill_cell(self.main_ui.client_table, row, 0, client.name, data_type=str, increase_row_count=False)
        dni = "" if client.dni.as_primitive() is None else str(client.dni.as_primitive())
        fill_cell(self.main_ui.client_table, row, 1, dni, data_type=int, increase_row_count=False)
        fill_cell(self.main_ui.client_table, row, 3, client.age(), data_type=int, increase_row_count=False)

    def remove_client(self):
        self.main_ui.responsible_field.setStyleSheet("")

        row = self.main_ui.client_table.currentRow()
        if row == -1:
            Dialog.info("Error", "Seleccione un cliente en la tabla.")
            return

        client = self._clients[row]

        if Dialog.confirm(f"¿Desea eliminar el cliente '{client.name}'? (Sus pagos NO seran eliminados)"):
            try:
                self.security_handler.current_responsible = self.main_ui.responsible_field.value()

                self.client_repo.remove(client)
                remove_contact_by_client(self.contact_repo, client)

                self._clients.pop(row)
                self.main_ui.filter_header.on_search_click()  # Refreshes the table.

                # Clears the subscriptions table.
                self.main_ui.subscription_list.clear()

                Dialog.info("Éxito", f"El cliente '{client.name}' fue eliminado correctamente.")

                self._enable_subscribe()
            except SecurityError as sec_err:
                self.main_ui.responsible_field.setStyleSheet("border: 1px solid red")
                Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))

    def fill_subscription_list(self):
        row = self.main_ui.client_table.currentRow()
        if row == -1:
            Dialog.info("Error", "Seleccione un cliente en la tabla.")
            return

        self.main_ui.subscription_list.clear()
        self._subscriptions.clear()
        for sub in self._clients[row].subscriptions():
            item = QListWidgetItem(sub.activity.name.as_primitive())
            item.setFont(self.main_ui.font)
            self.main_ui.subscription_list.addItem(item)
            self._subscriptions[sub.activity.name.as_primitive()] = sub

        self._enable_subscribe()

    def create_subscription(self):
        client = self._clients[self.main_ui.client_table.currentRow()]

        subscription = api.subscribe(self.subscription_repo, date.today(), client,
                                     self.main_ui.subscribe_combobox.currentData(Qt.UserRole))

        Dialog.info("Éxito", f"El cliente '{client.name}' fue registrado correctamente en la actividad "
                             f"'{self.main_ui.subscribe_combobox.currentText()}'.")

        # Removes the added activity from the activities that can be subscribed to.
        self.main_ui.subscribe_combobox.removeItem(self.main_ui.subscribe_combobox.currentIndex())

        # Adds the new subscription to the list.
        item = QListWidgetItem(subscription.activity.name.as_primitive(), parent=self.main_ui.subscription_list)
        item.setFont(self.main_ui.font)
        self.main_ui.subscription_list.addItem(item)
        self._subscriptions[subscription.activity.name.as_primitive()] = subscription

        self._enable_subscribe()

    def cancel_subscription(self):
        if self.main_ui.client_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un cliente en la tabla.")
            return

        if self.main_ui.subscription_list.currentRow() == -1:
            Dialog.info("Error", "Seleccione una actividad en la lista.")
            return

        activity_name = self.main_ui.subscription_list.selectedItems()[0].text()
        client_name = self._subscriptions[activity_name].client.name

        if (self.main_ui.responsible_field.valid_value()
                and Dialog.confirm(f"¿Desea eliminar a '{client_name}' de la actividad  '{activity_name}?")):
            try:
                self.security_handler.current_responsible = self.main_ui.responsible_field.value()

                api.cancel(self.subscription_repo, self._subscriptions[activity_name])

                activity = self._subscriptions.pop(activity_name).activity
                self.main_ui.subscription_list.takeItem(self.main_ui.subscription_list.currentRow())
                self.main_ui.subscribe_combobox.addItem(activity.name.as_primitive(), activity)

                self.fill_months_to_charge()

                self.main_ui.responsible_field.setStyleSheet("")
                Dialog.info("Éxito", f"El cliente '{client_name}' fue eliminado de la actividad {activity_name}.")
            except SecurityError as sec_err:
                self.main_ui.responsible_field.setStyleSheet("border: 1px solid red")
                Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))

        self._enable_subscribe()

    def fill_charge_table(self):
        self.main_ui.charge_table.setRowCount(0)

        if self.main_ui.client_table.currentRow() != -1 and self.main_ui.subscription_list.currentItem() is not None:
            year = self.main_ui.year_spinbox.value()
            sub = self._subscriptions[self.main_ui.subscription_list.currentItem().text()]

            self.main_ui.amount_line.setText(Currency.fmt(sub.activity.price, symbol=""))

            # Filters months according to which radio button is checked.
            month_it = (month for month in range(*from_month_to_month(sub.when, year, date.today())))
            if self.main_ui.only_paid_charges.isChecked():
                month_it = itertools.filterfalse(lambda month_: not sub.is_charged(year, month_), month_it)
            if self.main_ui.only_unpaid_charges.isChecked():
                month_it = itertools.filterfalse(lambda month_: sub.is_charged(year, month_), month_it)

            for month in month_it:
                row = self.main_ui.charge_table.rowCount()
                fill_cell(self.main_ui.charge_table, row, 0, f"{month}/{year}", int)
                transaction_when, transaction_amount = "-", "-"
                if sub.is_charged(year, month):
                    transaction_when = sub.last_transaction(year, month).when.strftime(utils.DATE_FORMAT)
                    transaction_amount = Currency.fmt(sub.charged_amount(year, month))
                fill_cell(self.main_ui.charge_table, row, 1, transaction_when, bool, increase_row_count=False)
                fill_cell(self.main_ui.charge_table, row, 2, transaction_amount, int, increase_row_count=False)

        self._enable_subscribe()

    def fill_months_to_charge(self):
        if self.main_ui.client_table.currentRow() != -1 and self.main_ui.subscription_list.currentItem() is not None:
            sub = self._subscriptions[self.main_ui.subscription_list.currentItem().text()]
            fill_combobox(self.main_ui.month_combobox, year_month_iterator(sub.when, date.today()),
                          display=lambda year_month: f"{year_month[1]}/{year_month[0]}")
        if self.main_ui.subscription_list.currentItem() is None:
            self.main_ui.month_combobox.clear()

    def set_unpaid_month(self):
        if self.main_ui.charge_table.currentRow() != -1:
            month_year_str = self.main_ui.charge_table.item(self.main_ui.charge_table.currentRow(), 0).text()
            for i in range(len(self.main_ui.month_combobox)):
                if self.main_ui.month_combobox.itemText(i) == month_year_str:
                    self.main_ui.month_combobox.setCurrentIndex(i)
                    break

    def charge_subscription(self):
        if len(self.main_ui.subscription_list) == 0:
            Dialog.info("Error", "El cliente no esta inscripto en ninguna actividad.")
            return
        if self.main_ui.subscription_list.currentRow() == -1:
            Dialog.info("Error", "Seleccione una actividad en la lista.")
            return
        if self.main_ui.month_combobox.currentIndex() == -1:
            Dialog.info("Error", f"El cliente tiene la actividad "
                                 f"'{self.main_ui.subscription_list.currentItem().text()}' al día.")
            return

        if not self.main_ui.amount_line.valid_value():
            Dialog.info("Error", f"El monto ingresado no es válido.")
        else:
            sub = self._subscriptions[self.main_ui.subscription_list.currentItem().text()]
            year, month = self.main_ui.month_combobox.currentData(Qt.UserRole)
            try:
                self.security_handler.current_responsible = self.main_ui.responsible_field.value()

                create_transaction_fn = functools.partial(
                    self.transaction_repo.create, "Cobro", date.today(), self.main_ui.amount_line.value(),
                    self.main_ui.method_combobox.currentText(), self.security_handler.current_responsible.name,
                    f"Cobro de actividad '{sub.activity.name}' a '{sub.client.name}'.", sub.client
                )
                _, transaction = api.register_subscription_charge(self.subscription_repo, sub, year, month,
                                                                  create_transaction_fn)

                self.main_ui.responsible_field.setStyleSheet("")
                Dialog.info("Éxito", f"El cobro a '{sub.client.name}' por '{sub.activity.name}' fue registrado.")

                # Updates the ui.
                self.fill_charge_table()
                self.fill_months_to_charge()

            except SecurityError as sec_err:
                self.main_ui.responsible_field.setStyleSheet("border: 1px solid red")
                Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))


class ClientMainUI(QMainWindow):

    def __init__(
            self,
            client_repo: ClientRepo,
            subscription_repo: SubscriptionRepo,
            transaction_repo: TransactionRepo,
            security_handler: SecurityHandler,
            activities_fn: Callable[[], Iterable[Activity]],
            contact_repo: ContactRepo | None = None
    ) -> None:
        super().__init__()

        self.font = QFont("MS Shell Dlg 2", 14)

        self._setup_ui()
        self.controller = MainController(self, client_repo, subscription_repo, transaction_repo, security_handler,
                                         activities_fn, contact_repo)

    def _setup_ui(self):
        self.setWindowTitle("Clientes")
        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QHBoxLayout(self.widget)

        # Menu bar.
        menu_bar = self.menuBar()

        client_menu = QMenu("&Clientes", self)
        menu_bar.addMenu(client_menu)

        self.create_action = QAction("&Agregar", self)
        client_menu.addAction(self.create_action)

        self.edit_action = QAction("&Editar", self)
        client_menu.addAction(self.edit_action)

        self.remove_action = QAction("&Eliminar", self)
        client_menu.addAction(self.remove_action)

        # Layout.
        self.left_layout = QVBoxLayout()
        self.layout.addLayout(self.left_layout)
        self.left_layout.setContentsMargins(10, 0, 10, 0)

        self.layout.addWidget(Separator(vertical=True, parent=self.widget))  # Vertical line.

        # Right layout.
        self.right_layout = QVBoxLayout()
        self.layout.addLayout(self.right_layout)
        self.right_layout.setContentsMargins(10, 0, 10, 0)
        self.right_layout.setAlignment(Qt.AlignCenter)

        # Filtering.
        self.filter_header = FilterHeader(parent=self.widget, detect_text_change=True)
        self.left_layout.addWidget(self.filter_header)

        # Clients.
        self.client_table = QTableWidget(self.widget)
        self.left_layout.addWidget(self.client_table)
        new_config_table(self.client_table, width=600, allow_resizing=False, min_rows_to_show=6,
                         columns={"Nombre": (.4, str), "DNI": (.2, int), "Ingreso": (.2, bool), "Edad": (.2, int)})

        # Index.
        self.page_index = PageIndex(self.widget)
        self.left_layout.addWidget(self.page_index)

        # Vertical spacer.
        # self.right_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        # Responsible.
        self.responsible_layout = QHBoxLayout()
        self.right_layout.addLayout(self.responsible_layout)
        self.responsible_layout.setAlignment(Qt.AlignLeft)

        self.responsible_lbl = QLabel(self)
        self.responsible_layout.addWidget(self.responsible_lbl)
        config_lbl(self.responsible_lbl, "Responsable")

        self.responsible_field = responsible_field(self)
        self.responsible_layout.addWidget(self.responsible_field)
        config_line(self.responsible_field, fixed_width=100)

        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Subscriptions data.
        self.subscribe_layout = QHBoxLayout()
        self.right_layout.addLayout(self.subscribe_layout)
        self.subscribe_layout.setAlignment(Qt.AlignLeft)

        self.subscribe_lbl = QLabel(self.widget)
        self.subscribe_layout.addWidget(self.subscribe_lbl)
        config_lbl(self.subscribe_lbl, "Inscribir en ")

        self.subscribe_combobox = QComboBox(self.widget)
        self.subscribe_layout.addWidget(self.subscribe_combobox)
        config_combobox(self.subscribe_combobox)
        self.subscribe_combobox.setFixedWidth(250)

        self.subscribe_btn = QPushButton(self.widget)
        self.subscribe_layout.addWidget(self.subscribe_btn)
        config_btn(self.subscribe_btn, "Confirmar", icon_path=r"ui/resources/tick.png", icon_size=24)

        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        self.subscription_info_lbl = QLabel(self.widget)
        self.right_layout.addWidget(self.subscription_info_lbl)
        config_lbl(self.subscription_info_lbl, "El cliente esta inscripto en las siguientes actividades.")

        self.subscription_list = QListWidget(self.widget)
        self.right_layout.addWidget(self.subscription_list)
        self.subscription_list.setFixedHeight(100)

        self.cancel_btn = QPushButton(self.widget)
        self.right_layout.addWidget(self.cancel_btn)
        config_btn(self.cancel_btn, "Eliminar", icon_path=r"ui/resources/trash_can.png", icon_size=24)

        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Subscription charges info.
        self.charges_info_layout = QHBoxLayout()
        self.right_layout.addLayout(self.charges_info_layout)
        self.charges_info_layout.setAlignment(Qt.AlignLeft)

        self.charges_lbl = QLabel(self.widget)
        self.charges_info_layout.addWidget(self.charges_lbl)
        config_lbl(self.charges_lbl, "Cuotas del ")

        self.year_spinbox = QSpinBox(self.widget)
        self.charges_info_layout.addWidget(self.year_spinbox)
        config_widget(self.year_spinbox, fixed_width=70)
        self.year_spinbox.setMaximum(9999)
        self.year_spinbox.setValue(date.today().year)

        # Charges filtering.
        self.charge_filter_layout = QHBoxLayout()
        self.right_layout.addLayout(self.charge_filter_layout)
        self.charge_filter_layout.setAlignment(Qt.AlignCenter)
        self.charge_filter_group = QButtonGroup(self.widget)

        self.all_charges = QRadioButton("Todas")
        self.charge_filter_group.addButton(self.all_charges)
        self.charge_filter_layout.addWidget(self.all_charges)
        self.all_charges.setFont(self.font)

        self.only_paid_charges = QRadioButton("Pagas")
        self.charge_filter_group.addButton(self.only_paid_charges)
        self.charge_filter_layout.addWidget(self.only_paid_charges)
        self.only_paid_charges.setFont(self.font)

        self.only_unpaid_charges = QRadioButton("Sin pagar")
        self.charge_filter_group.addButton(self.only_unpaid_charges)
        self.charge_filter_layout.addWidget(self.only_unpaid_charges)
        self.only_unpaid_charges.setFont(self.font)

        # Charges table.
        self.charge_table = QTableWidget(self.widget)
        self.right_layout.addWidget(self.charge_table)
        new_config_table(self.charge_table, width=500, min_rows_to_show=4, fix_width=True,
                         columns={"Mes": (.2, int), "Último pago": (.35, bool), "Total cobrado": (.45, int)})

        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Charge form.
        self.charge_form_layout = QGridLayout()
        self.right_layout.addLayout(self.charge_form_layout)
        self.charge_form_layout.setContentsMargins(50, 0, 50, 0)

        # Method.
        self.method_combobox = QComboBox(self)
        self.charge_form_layout.addWidget(self.method_combobox, 0, 0)
        config_combobox(self.method_combobox)

        # Amount.
        self.amount_line = Field(Currency, parent=self, positive=True)
        self.charge_form_layout.addWidget(self.amount_line, 0, 1)
        config_line(self.amount_line, place_holder="000000,00", alignment=Qt.AlignRight)

        # Month.
        self.month_lbl = QLabel(self)
        self.charge_form_layout.addWidget(self.month_lbl, 1, 0)
        config_lbl(self.month_lbl, "Mes")

        self.month_combobox = QComboBox(self)
        self.charge_form_layout.addWidget(self.month_combobox, 1, 1)
        config_combobox(self.month_combobox)

        # Charge button
        self.charge_btn = QPushButton(self.widget)
        self.charge_form_layout.addWidget(self.charge_btn, 0, 2, 2, 1, alignment=Qt.AlignCenter)
        config_btn(self.charge_btn, "Cobrar", icon_path=r"ui/resources/tick.png", icon_size=24)

        self.setFixedSize(self.minimumSizeHint())
        self.move(int(QDesktopWidget().geometry().center().x() - self.sizeHint().width() / 2),
                  int(QDesktopWidget().geometry().center().y() - self.sizeHint().height() / 2))


class CreateController:

    def __init__(self, create_ui: CreateUI, client_repo: ClientRepo, contact_repo: ContactRepo | None = None) -> None:
        self.create_ui = create_ui

        self.client: Client | None = None
        self.client_repo = client_repo
        self.contact_repo = contact_repo

        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_client)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    # noinspection PyTypeChecker
    def create_client(self):
        if self.create_ui.birth_date_edit.date().toPyDate() > date.today():
            Dialog.info("Error", "La fecha de nacimiento no puede ser posterior al día de hoy.")
        elif not all([self.create_ui.name_field.valid_value(), self.create_ui.dni_field.valid_value(),
                      self.create_ui.tel_field.valid_value(), self.create_ui.dir_field.valid_value()]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        elif self.client_repo.is_active(self.create_ui.dni_field.value()):
            Dialog.info("Error", f"Ya existe un cliente con el DNI '{self.create_ui.dni_field.value()}'.")
        else:
            self.client = self.client_repo.create(self.create_ui.name_field.value(), date.today(),
                                                  self.create_ui.birth_date_edit.date().toPyDate(),
                                                  self.create_ui.dni_field.value())
            if self.contact_repo is not None:
                # Creates a contact for the client, with basic info.
                create_contact(self.contact_repo, name=String(""), tel1=self.create_ui.tel_field.value(),
                               tel2=String(""), direction=self.create_ui.dir_field.value(), description=String(""),
                               client=self.client)
            Dialog.info("Éxito", f"El cliente '{self.create_ui.name_field.value()}' fue creado correctamente.")
            self.create_ui.name_field.window().close()


class CreateUI(QDialog):
    def __init__(self, client_repo: ClientRepo, contact_repo: ContactRepo | None = None) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, client_repo, contact_repo)

    def _setup_ui(self):
        self.setWindowTitle("Nuevo cliente")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self, max_len=utils.CLIENT_NAME_CHARS, invalid_values=("Pago", "Fijo"),
                                optional=False)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # DNI.
        self.dni_lbl = QLabel(self)
        self.form_layout.addWidget(self.dni_lbl, 1, 0)
        config_lbl(self.dni_lbl, "DNI")

        self.dni_field = Field(Number, self, optional=True, min_value=utils.CLIENT_MIN_DNI,
                               max_value=utils.CLIENT_MAX_DNI)
        self.form_layout.addWidget(self.dni_field, 1, 1)
        config_line(self.dni_field, place_holder="XXYYYZZZ", adjust_to_hint=False)

        # Birthday.
        self.birth_lbl = QLabel(self)
        self.form_layout.addWidget(self.birth_lbl, 2, 0)
        config_lbl(self.birth_lbl, "Nacimiento")

        self.birth_date_edit = QDateEdit(self)
        self.form_layout.addWidget(self.birth_date_edit, 2, 1)
        config_date_edit(self.birth_date_edit, date.today(), calendar=True)

        # Telephone.
        self.tel_lbl = QLabel(self)
        self.form_layout.addWidget(self.tel_lbl, 3, 0)
        config_lbl(self.tel_lbl, "Teléfono")

        self.tel_field = Field(String, self, optional=True, max_len=utils.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel_field, 3, 1)
        config_line(self.tel_field, place_holder="Teléfono", adjust_to_hint=False)

        # Direction.
        self.dir_lbl = QLabel(self)
        self.form_layout.addWidget(self.dir_lbl, 4, 0)
        config_lbl(self.dir_lbl, "Dirección")

        self.dir_field = Field(String, self, optional=True, max_len=utils.CLIENT_DIR_CHARS)
        self.form_layout.addWidget(self.dir_field, 4, 1)
        config_line(self.dir_field, place_holder="Dirección", adjust_to_hint=False)

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

    def __init__(self, edit_ui: EditUI, client_repo: ClientRepo, client: Client) -> None:
        self.edit_ui = edit_ui

        self.client_repo = client_repo
        self.client = client

        self.edit_ui.name_field.setText(client.name.as_primitive())
        if client.dni.as_primitive() is not None:
            self.edit_ui.dni_field.setText(str(client.dni))
        self.edit_ui.birth_date_edit.setDate(client.birth_day)

        # noinspection PyUnresolvedReferences
        self.edit_ui.confirm_btn.clicked.connect(self.edit_client)
        # noinspection PyUnresolvedReferences
        self.edit_ui.cancel_btn.clicked.connect(self.edit_ui.reject)

    # noinspection PyTypeChecker
    def edit_client(self):
        if self.edit_ui.birth_date_edit.date().toPyDate() > date.today():
            Dialog.info("Error", "La fecha de nacimiento no puede ser posterior al día de hoy.")
        elif not all([self.edit_ui.name_field.valid_value(), self.edit_ui.dni_field.valid_value()]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        elif (self.client.dni != self.edit_ui.dni_field.value()
              and self.client_repo.is_active(self.edit_ui.dni_field.value())):
            Dialog.info("Error", f"Ya existe un cliente con el DNI '{self.edit_ui.dni_field.value()}'.")
        else:
            self.client.name = self.edit_ui.name_field.value()
            self.client.dni = self.edit_ui.dni_field.value()
            self.client.birth_day = self.edit_ui.birth_date_edit.date().toPyDate()
            self.client_repo.update(self.client)
            Dialog.info("Éxito", f"El cliente '{self.edit_ui.name_field.value()}' fue editado correctamente.")
            self.edit_ui.name_field.window().close()


class EditUI(QDialog):
    def __init__(self, client_repo: ClientRepo, client: Client) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = EditController(self, client_repo, client)

    def _setup_ui(self):
        self.setWindowTitle("Editar cliente")
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)
        self.form_layout.setContentsMargins(40, 0, 40, 0)

        # Name.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, parent=self, max_len=utils.CLIENT_NAME_CHARS, invalid_values=("Pago", "Fijo"),
                                optional=False)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # DNI.
        self.dni_lbl = QLabel(self)
        self.form_layout.addWidget(self.dni_lbl, 1, 0)
        config_lbl(self.dni_lbl, "DNI")

        self.dni_field = Field(Number, self, optional=True, min_value=utils.CLIENT_MIN_DNI,
                               max_value=utils.CLIENT_MAX_DNI)
        self.form_layout.addWidget(self.dni_field, 1, 1)
        config_line(self.dni_field, place_holder="XXYYYZZZ", adjust_to_hint=False)

        # Birthday.
        self.birth_lbl = QLabel(self)
        self.form_layout.addWidget(self.birth_lbl, 2, 0)
        config_lbl(self.birth_lbl, "Nacimiento")

        self.birth_date_edit = QDateEdit(self)
        self.form_layout.addWidget(self.birth_date_edit, 2, 1)
        config_date_edit(self.birth_date_edit, date.today(), calendar=True)

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
