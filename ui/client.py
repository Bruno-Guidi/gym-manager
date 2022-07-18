from __future__ import annotations

import functools
import itertools
from datetime import date
from typing import Iterable, Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QSpacerItem, QSizePolicy, QDialog, QGridLayout, QTableWidget, QCheckBox, QComboBox,
    QDateEdit)

from gym_manager.core import constants as constants, api
from gym_manager.core.base import String, TextLike, Client, Number, Activity, Subscription, discard_subscription
from gym_manager.core.persistence import FilterValuePair, ClientRepo, SubscriptionRepo, TransactionRepo
from gym_manager.core.security import SecurityHandler, SecurityError, log_responsible
from ui.accounting import ChargeUI
from ui.translated_messages import MESSAGE
from ui.widget_config import (
    config_lbl, config_line, config_btn, config_table, fill_cell, config_checkbox,
    config_combobox, fill_combobox, config_date_edit)
from ui.widgets import Field, Dialog, FilterHeader, PageIndex, Separator, DialogWithResp, responsible_field


@log_responsible(action_tag="update_client", action_name="Actualizar cliente")
def update_client(client_repo: ClientRepo, client: Client, name: String, telephone: String, direction: String):
    client.name = name
    client.telephone = telephone
    client.direction = direction
    client_repo.update(client)


class MainController:
    def __init__(
            self,
            main_ui: ClientMainUI,
            client_repo: ClientRepo,
            subscription_repo: SubscriptionRepo,
            transaction_repo: TransactionRepo,
            security_handler: SecurityHandler,
            activities_fn: Callable[[], Iterable[Activity]]
    ):
        self.main_ui = main_ui
        self.client_repo = client_repo
        self.subscription_repo = subscription_repo
        self.transaction_repo = transaction_repo
        self.security_handler = security_handler
        self.activities_fn = activities_fn
        self._clients: dict[int, Client] = {}  # Dict that maps raw client dni to the associated client.
        self._subscriptions: dict[str, Subscription] = {}  # Maps raw activity name to subs of the selected client.

        # Configure the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name",
                            translate_fun=lambda client, value: client.cli_name.contains(value)),)
        self.main_ui.filter_header.config(filters, on_search_click=self.fill_client_table)

        # Configures the page index.
        self.main_ui.page_index.config(refresh_table=self.main_ui.filter_header.on_search_click,
                                       page_len=20, total_len=self.client_repo.count())

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
        self.main_ui.client_table.itemSelectionChanged.connect(self.update_client_info)
        # noinspection PyUnresolvedReferences
        self.main_ui.overdue_subs_checkbox.stateChanged.connect(self.fill_subscription_table)
        # noinspection PyUnresolvedReferences
        self.main_ui.charge_sub_btn.clicked.connect(self.charge_sub)
        # noinspection PyUnresolvedReferences
        self.main_ui.add_sub_btn.clicked.connect(self.add_sub)
        # noinspection PyUnresolvedReferences
        self.main_ui.cancel_sub_btn.clicked.connect(self.cancel_sub)

    def _add_client(self, client: Client, check_filters: bool, check_limit: bool = False):
        if check_limit and self.main_ui.client_table.rowCount() == self.main_ui.page_index.page_len:
            return

        if check_filters and not self.main_ui.filter_header.passes_filters(client):
            return

        self._clients[client.dni.as_primitive()] = client
        row = self.main_ui.client_table.rowCount()
        fill_cell(self.main_ui.client_table, row, 0, client.name, data_type=str)
        fill_cell(self.main_ui.client_table, row, 1, client.dni, data_type=int)
        fill_cell(self.main_ui.client_table, row, 2, client.admission, data_type=bool)
        fill_cell(self.main_ui.client_table, row, 3, client.age(), data_type=int)
        fill_cell(self.main_ui.client_table, row, 4, client.telephone, data_type=str)
        fill_cell(self.main_ui.client_table, row, 5, client.direction, data_type=str)

    def fill_client_table(self, filters: list[FilterValuePair]):
        self.main_ui.client_table.setRowCount(0)

        self.main_ui.page_index.total_len = self.client_repo.count(filters)
        for client in self.client_repo.all(self.main_ui.page_index.page, self.main_ui.page_index.page_len, filters):
            self._clients[client.dni.as_primitive()] = client
            self._add_client(client, check_filters=False)  # Clients are filtered in the repo.

    def update_client_info(self):
        if self.main_ui.client_table.currentRow() != -1:
            client_dni = int(self.main_ui.client_table.item(self.main_ui.client_table.currentRow(), 1).text())
            # Fills the form.
            self.main_ui.name_field.setText(str(self._clients[client_dni].name))
            self.main_ui.dni_field.setText(str(self._clients[client_dni].dni))
            self.main_ui.tel_field.setText(str(self._clients[client_dni].telephone))
            self.main_ui.dir_field.setText(str(self._clients[client_dni].direction))

            self.fill_subscription_table()

        else:
            # Clears the form.
            self.main_ui.name_field.clear()
            self.main_ui.dni_field.clear()
            self.main_ui.tel_field.clear()
            self.main_ui.dir_field.clear()

    def create_ui(self):
        # noinspection PyAttributeOutsideInit
        self._create_ui = CreateUI(self.client_repo)
        self._create_ui.exec_()
        if self._create_ui.controller.client is not None:
            self._add_client(self._create_ui.controller.client, check_filters=True, check_limit=True)
            self.main_ui.page_index.total_len += 1

    def save_changes(self):
        if self.main_ui.client_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un cliente.")
            return

        if not all([self.main_ui.name_field.valid_value(), self.main_ui.tel_field.valid_value(),
                    self.main_ui.dir_field.valid_value()]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            client_dni = int(self.main_ui.client_table.item(self.main_ui.client_table.currentRow(), 1).text())
            update_fn = functools.partial(update_client, self.client_repo, self._clients[client_dni],
                                          self.main_ui.name_field.value(), self.main_ui.tel_field.value(),
                                          self.main_ui.dir_field.value())

            if DialogWithResp.confirm(f"Ingrese el responsable.", self.security_handler, update_fn):
                # Updates the ui.
                row = self.main_ui.client_table.currentRow()
                client = self._clients[client_dni]
                fill_cell(self.main_ui.client_table, row, 0, client.name, data_type=str, increase_row_count=False)
                fill_cell(self.main_ui.client_table, row, 4, client.telephone, data_type=str, increase_row_count=False)
                fill_cell(self.main_ui.client_table, row, 5, client.direction, data_type=str, increase_row_count=False)

                Dialog.info("Éxito", f"El cliente '{client.name}' fue actualizado correctamente.")

    def remove(self):
        if self.main_ui.client_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un cliente.")
            return

        client_dni = int(self.main_ui.client_table.item(self.main_ui.client_table.currentRow(), 1).text())
        client = self._clients[client_dni]

        remove_fn = functools.partial(self.client_repo.remove, client)
        if DialogWithResp.confirm(f"¿Desea eliminar el cliente '{self._clients[client_dni].name}'?",
                                  self.security_handler, remove_fn):
            self._clients.pop(client.dni.as_primitive())
            self.main_ui.filter_header.on_search_click()  # Refreshes the table.

            # Clears the form.
            self.main_ui.name_field.clear()
            self.main_ui.dni_field.clear()
            self.main_ui.tel_field.clear()
            self.main_ui.dir_field.clear()

            Dialog.info("Éxito", f"El cliente '{client.name}' fue eliminado correctamente.")

    def fill_subscription_table(self):
        if self.main_ui.client_table.currentRow() == -1:
            self.main_ui.overdue_subs_checkbox.setChecked(not self.main_ui.overdue_subs_checkbox.isChecked())
            Dialog.info("Error", "Seleccione un cliente.")
            return

        self._subscriptions = {}  # Clears the dict.
        self.main_ui.subscription_table.setRowCount(0)  # Clears the table.

        client_dni = int(self.main_ui.client_table.item(self.main_ui.client_table.currentRow(), 1).text())

        for i, sub in enumerate(self._clients[client_dni].subscriptions()):
            self._subscriptions[sub.activity.name.as_primitive()] = sub
            if not discard_subscription(self.main_ui.overdue_subs_checkbox.isChecked(), sub.up_to_date(date.today())):
                fill_cell(self.main_ui.subscription_table, i, 0, sub.activity.name, data_type=str)
                last_paid_date = None if sub.transaction is None else sub.transaction.when
                fill_cell(self.main_ui.subscription_table, i, 1, "-" if last_paid_date is None else last_paid_date,
                          data_type=bool)

    def charge_sub(self):
        if self.main_ui.client_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un cliente.")
            return

        if self.main_ui.subscription_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione una actividad.")
            return

        client_dni = int(self.main_ui.client_table.item(self.main_ui.client_table.currentRow(), 1).text())
        activity_name = self.main_ui.subscription_table.item(self.main_ui.subscription_table.currentRow(), 0).text()

        register_sub_charge = functools.partial(api.register_subscription_charge, self.subscription_repo,
                                                self._subscriptions[activity_name])
        # noinspection PyAttributeOutsideInit
        self._charge_ui = ChargeUI(
            self.transaction_repo, self.security_handler, self._clients[client_dni],
            amount=self._subscriptions[activity_name].activity.price,
            description=String(f"Cobro de actividad {activity_name}.", max_len=constants.TRANSACTION_DESCR_CHARS),
            post_charge_fn=register_sub_charge
        )
        self._charge_ui.exec_()
        if self._charge_ui.controller.success:
            # Updates the last charged date of the subscription.
            fill_cell(self.main_ui.subscription_table, self.main_ui.subscription_table.currentRow(), 1,
                      self._subscriptions[self.main_ui.subscription_table.currentRow()], data_type=bool)
            # If 'only overdue' filtering is active, then remove the activity from the table, because it is no longer
            # overdue.
            if self.main_ui.overdue_subs_checkbox.isChecked():
                self.main_ui.subscription_table.removeRow(self.main_ui.subscription_table.currentRow())

    def add_sub(self):
        if self.main_ui.client_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un cliente.")
            return

        client_dni = int(self.main_ui.client_table.item(self.main_ui.client_table.currentRow(), 1).text())
        # noinspection PyAttributeOutsideInit
        self._add_sub_ui = AddSubUI(self.subscription_repo, self.security_handler,
                                    (activity for activity in self.activities_fn()), self._clients[client_dni])
        self._add_sub_ui.exec_()

        subscription = self._add_sub_ui.controller.subscription
        if subscription is not None:
            row = self.main_ui.subscription_table.rowCount()
            self._subscriptions[subscription.activity.name.as_primitive()] = subscription
            fill_cell(self.main_ui.subscription_table, row, 0, subscription.activity.name, data_type=str)
            last_paid_date = None if subscription.transaction is None else subscription.transaction.when
            fill_cell(self.main_ui.subscription_table, row, 1, "-" if last_paid_date is None else last_paid_date,
                      data_type=bool)

    def cancel_sub(self):
        if self.main_ui.client_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione un cliente.")
            return

        if self.main_ui.subscription_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione una actividad.")
            return

        activity_name = self.main_ui.subscription_table.item(self.main_ui.subscription_table.currentRow(), 0).text()
        client_name = self._subscriptions[activity_name].client.name

        cancel_fn = functools.partial(api.cancel, self.subscription_repo, self._subscriptions[activity_name])
        remove = DialogWithResp.confirm(f"¿Desea cancelar la inscripción del cliente '{client_name}' a la actividad "
                                        f"'{activity_name}?", self.security_handler, cancel_fn)

        if remove:
            subscription = self._subscriptions.pop(activity_name)
            self.main_ui.subscription_table.removeRow(self.main_ui.subscription_table.currentRow())
            Dialog.info("Éxito", f"La inscripción del cliente '{subscription.client.name}' a la actividad "
                                 f"'{subscription.activity.name}' fue cancelada.")


class ClientMainUI(QMainWindow):

    def __init__(
            self,
            client_repo: ClientRepo,
            subscription_repo: SubscriptionRepo,
            transaction_repo: TransactionRepo,
            security_handler: SecurityHandler,
            activities_fn: Callable[[], Iterable[Activity]]
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = MainController(self, client_repo, subscription_repo, transaction_repo, security_handler,
                                         activities_fn)

    def _setup_ui(self):
        self.setWindowTitle("Clientes")
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

        # Clients.
        self.client_table = QTableWidget(self.widget)  # ToDO adjust columns width.
        self.left_layout.addWidget(self.client_table)
        config_table(self.client_table, allow_resizing=True, min_rows_to_show=10,
                     columns={"Nombre": (8, str), "DNI": (8, int), "Ingreso": (8, bool), "Edad": (8, int),
                              "Teléfono": (8, str), "Dirección": (8, str)})

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

        # Client data form.
        self.form_layout = QGridLayout()
        self.right_layout.addLayout(self.form_layout)

        # Name.
        self.name_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Nombre*")

        self.name_field = Field(String, self.widget, max_len=constants.CLIENT_NAME_CHARS)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # DNI.
        self.dni_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.dni_lbl, 1, 0)
        config_lbl(self.dni_lbl, "DNI*")

        self.dni_field = Field(Number, self.widget, min_value=constants.CLIENT_MIN_DNI,
                               max_value=constants.CLIENT_MAX_DNI)
        self.form_layout.addWidget(self.dni_field, 1, 1)
        config_line(self.dni_field, place_holder="XXYYYZZZ", adjust_to_hint=False, enabled=False)

        # Telephone.
        self.tel_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.tel_lbl, 2, 0)
        config_lbl(self.tel_lbl, "Teléfono")

        self.tel_field = Field(String, self.widget, optional=constants.CLIENT_TEL_OPTIONAL,
                               max_len=constants.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel_field, 2, 1)
        config_line(self.tel_field, place_holder="Teléfono", adjust_to_hint=False)

        # Direction.
        self.dir_lbl = QLabel(self.widget)
        self.form_layout.addWidget(self.dir_lbl, 3, 0)
        config_lbl(self.dir_lbl, "Dirección")

        self.dir_field = Field(String, self.widget, optional=constants.CLIENT_DIR_OPTIONAL,
                               max_len=constants.CLIENT_DIR_CHARS)
        self.form_layout.addWidget(self.dir_field, 3, 1)
        config_line(self.dir_field, place_holder="Dirección", adjust_to_hint=False)

        # Subscriptions data.
        self.right_layout.addWidget(Separator(vertical=False, parent=self.widget))  # Horizontal line.

        # Subscription layout.
        self.sub_layout = QGridLayout()
        self.right_layout.addLayout(self.sub_layout)

        # Checkbox that enables showing only subscriptions that aren't up-to-date.
        self.overdue_subs_checkbox = QCheckBox(self.widget)
        self.sub_layout.addWidget(self.overdue_subs_checkbox, 0, 1)
        config_checkbox(self.overdue_subs_checkbox, "Solo actividades inpagas", checked=False)

        self.charge_sub_btn = QPushButton(self.widget)
        self.sub_layout.addWidget(self.charge_sub_btn, 1, 0)
        config_btn(self.charge_sub_btn, icon_path="ui/resources/charge.png", icon_size=32)

        self.add_sub_btn = QPushButton(self.widget)
        self.sub_layout.addWidget(self.add_sub_btn, 2, 0)
        config_btn(self.add_sub_btn, icon_path="ui/resources/plus.png", icon_size=32)

        self.cancel_sub_btn = QPushButton(self.widget)
        self.sub_layout.addWidget(self.cancel_sub_btn, 3, 0)
        config_btn(self.cancel_sub_btn, icon_path="ui/resources/minus.png", icon_size=32)

        # Subscription table.
        self.subscription_table = QTableWidget(self.widget)
        self.sub_layout.addWidget(self.subscription_table, 1, 1, 4, 1)
        config_table(self.subscription_table, allow_resizing=False,
                     columns={"Actividad": (10, str), "Último pago": (10, bool)})

        # Vertical spacer.
        self.right_layout.addSpacerItem(QSpacerItem(20, 50, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))


class CreateController:

    def __init__(self, create_ui: CreateUI, client_repo: ClientRepo) -> None:
        self.create_ui = create_ui

        self.client: Client | None = None
        self.client_repo = client_repo

        # noinspection PyUnresolvedReferences
        self.create_ui.confirm_btn.clicked.connect(self.create_client)
        # noinspection PyUnresolvedReferences
        self.create_ui.cancel_btn.clicked.connect(self.create_ui.reject)

    # noinspection PyTypeChecker
    def create_client(self):
        if not all([self.create_ui.name_field.valid_value(), self.create_ui.dni_field.valid_value(),
                    self.create_ui.tel_field.valid_value(), self.create_ui.dir_field.valid_value()]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        elif self.client_repo.is_active(self.create_ui.dni_field.value()):
            Dialog.info("Error", f"Ya existe un cliente con el DNI '{self.create_ui.dni_field.value()}'.")
        else:
            self.client = Client(self.create_ui.dni_field.value(), self.create_ui.name_field.value(), date.today(),
                                 self.create_ui.birth_date_edit.date().toPyDate(), self.create_ui.tel_field.value(),
                                 self.create_ui.dir_field.value())
            self.client_repo.add(self.client)
            Dialog.info("Éxito", f"El cliente '{self.create_ui.name_field.value()}' fue creado correctamente.")
            self.create_ui.name_field.window().close()


class CreateUI(QDialog):
    def __init__(self, client_repo: ClientRepo) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = CreateController(self, client_repo)

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

        self.name_field = Field(String, parent=self, max_len=constants.CLIENT_NAME_CHARS)
        self.form_layout.addWidget(self.name_field, 0, 1)
        config_line(self.name_field, place_holder="Nombre", adjust_to_hint=False)

        # DNI.
        self.dni_lbl = QLabel(self)
        self.form_layout.addWidget(self.dni_lbl, 1, 0)
        config_lbl(self.dni_lbl, "DNI*")

        self.dni_field = Field(Number, self, min_value=constants.CLIENT_MIN_DNI, max_value=constants.CLIENT_MAX_DNI)
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

        self.tel_field = Field(String, self, optional=constants.CLIENT_TEL_OPTIONAL, max_len=constants.CLIENT_TEL_CHARS)
        self.form_layout.addWidget(self.tel_field, 3, 1)
        config_line(self.tel_field, place_holder="Teléfono", adjust_to_hint=False)

        # Direction.
        self.dir_lbl = QLabel(self)
        self.form_layout.addWidget(self.dir_lbl, 4, 0)
        config_lbl(self.dir_lbl, "Dirección")

        self.dir_field = Field(String, self, optional=constants.CLIENT_DIR_OPTIONAL, max_len=constants.CLIENT_DIR_CHARS)
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


class AddSubController:
    def __init__(
            self, add_sub_ui: AddSubUI, subscription_repo: SubscriptionRepo, security_handler: SecurityHandler,
            activities: Iterable[Activity], client: Client
    ):
        self.add_sub_ui = add_sub_ui
        self.subscription_repo = subscription_repo
        self.client = client
        self.security_handler = security_handler
        self.subscription: Subscription | None = None

        activities = itertools.filterfalse(lambda activity: self.client.is_subscribed(activity) or activity.charge_once,
                                           activities)
        fill_combobox(self.add_sub_ui.activity_combobox, activities, display=lambda activity: str(activity.name))

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.add_sub_ui.confirm_btn.clicked.connect(self.add_sub)
        # noinspection PyUnresolvedReferences
        self.add_sub_ui.cancel_btn.clicked.connect(self.add_sub_ui.reject)

    def add_sub(self):
        if self.add_sub_ui.activity_combobox.count() == 0:
            Dialog.info("Error", "No hay actividades disponibles.")
        else:
            activity: Activity = self.add_sub_ui.activity_combobox.currentData(Qt.UserRole)
            try:
                self.security_handler.current_responsible = self.add_sub_ui.responsible_field.value()
                self.subscription = api.subscribe(self.subscription_repo, date.today(), self.client, activity)

                Dialog.info("Éxito", f"El cliente '{self.client.name}' fue inscripto correctamente en la actividad "
                                     f"'{activity.name}'.")
                self.add_sub_ui.activity_combobox.window().close()
            except SecurityError as sec_err:
                Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))


class AddSubUI(QDialog):
    def __init__(
            self, subscription_repo: SubscriptionRepo, security_handler: SecurityHandler,
            activities: Iterable[Activity], client: Client
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = AddSubController(self, subscription_repo, security_handler, activities, client)

    def _setup_ui(self):
        self.setWindowTitle("Inscribir cliente")

        self.layout = QVBoxLayout(self)

        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)

        # Responsible
        self.responsible_lbl = QLabel(self)
        self.form_layout.addWidget(self.responsible_lbl, 1, 0)
        config_lbl(self.responsible_lbl, "Responsable")

        self.responsible_field = responsible_field(self)
        self.form_layout.addWidget(self.responsible_field, 1, 1)
        config_line(self.responsible_field, place_holder="Responsable")

        # Activity.
        self.name_lbl = QLabel(self)
        self.form_layout.addWidget(self.name_lbl, 0, 0)
        config_lbl(self.name_lbl, "Actividad")

        self.activity_combobox = QComboBox(self)
        self.form_layout.addWidget(self.activity_combobox, 0, 1)
        config_combobox(self.activity_combobox, fixed_width=self.responsible_field.width())

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
