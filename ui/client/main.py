from __future__ import annotations

from datetime import date

from PyQt5.QtCore import QRect, Qt, QSize
from PyQt5.QtWidgets import QMainWindow, QWidget, QListWidget, QHBoxLayout, QLabel, QPushButton, \
    QListWidgetItem, QVBoxLayout, QTableWidget, QSpacerItem, QSizePolicy, QTableWidgetItem, QDateEdit

from gym_manager.core import constants as consts
from gym_manager.core.base import Client, String, Number, Subscription, TextLike, invalid_sub_charge_date
from gym_manager.core.persistence import ClientRepo, FilterValuePair
from gym_manager.core.system import ActivityManager, AccountingSystem
from ui.accounting.main import AccountingMainUI
from ui.accounting.operations import ChargeUI
from ui.client.operations import CreateUI
from ui.client.operations import SubscribeUI
from ui.widget_config import config_lbl, config_line, config_btn, config_layout, config_table, \
    config_date_edit
from ui.widgets import Field, Dialog, FilterHeader, PageIndex


def invalid_date(transaction_date: date, **kwargs) -> bool:
    return invalid_sub_charge_date(kwargs['subscription'], transaction_date)


class ClientRow(QWidget):
    def __init__(
            self, item: QListWidgetItem, main_ui_controller: Controller, name_width: int, dni_width: int,
            admission_width: int, tel_width: int, dir_width: int, height: int, client: Client,
            client_repo: ClientRepo, activity_manager: ActivityManager, accounting_system: AccountingSystem
    ):
        super().__init__()
        self.client = client
        self.subscriptions: dict[int, Subscription] = {}
        self.client_repo = client_repo
        self.activity_manager = activity_manager
        self.accounting_system = accounting_system

        self.item = item
        self.main_ui_controller = main_ui_controller

        self._setup_ui(height, name_width, dni_width, admission_width, tel_width, dir_width)

        # Because the widgets are yet to be hided, the hint has the 'extended' height.
        self.current_height, self.previous_height = height, None
        self.item.setSizeHint(QSize(self.widget.width(), self.current_height))

        def _setup_hidden_ui():
            # Name.
            self.name_lbl = QLabel(self.widget)
            self.name_layout.addWidget(self.name_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.name_lbl, "Nombre", font_size=12, width=name_width)

            self.name_field = Field(String, self.widget, max_len=consts.CLIENT_NAME_CHARS)
            self.name_layout.addWidget(self.name_field)
            config_line(self.name_field, str(client.name), width=name_width)

            # DNI.
            self.dni_lbl = QLabel(self.widget)
            self.dni_layout.addWidget(self.dni_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.dni_lbl, "DNI", font_size=12, width=dni_width)

            self.dni_field = Field(Number, self.widget, min_value=consts.CLIENT_MIN_DNI,
                                   max_value=consts.CLIENT_MAX_DNI)
            self.dni_layout.addWidget(self.dni_field)
            config_line(self.dni_field, str(client.dni), width=dni_width, read_only=False)

            # Admission.
            self.admission_lbl = QLabel(self.widget)
            self.admission_layout.addWidget(self.admission_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.admission_lbl, "Ingreso", font_size=12, width=admission_width)

            self.admission_date_edit = QDateEdit()
            self.admission_layout.addWidget(self.admission_date_edit)
            config_date_edit(self.admission_date_edit, self.client.admission, width=admission_width)

            # Telephone.
            self.tel_lbl = QLabel(self.widget)
            self.tel_layout.addWidget(self.tel_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.tel_lbl, "Teléfono", font_size=12, width=tel_width)

            self.tel_field = Field(String, self.widget, optional=consts.CLIENT_TEL_OPTIONAL,
                                   max_len=consts.CLIENT_TEL_CHARS)
            self.tel_layout.addWidget(self.tel_field)
            config_line(self.tel_field, str(client.telephone), width=tel_width)

            # Direction.
            self.dir_lbl = QLabel(self.widget)
            self.dir_layout.addWidget(self.dir_lbl, alignment=Qt.AlignBottom)
            config_lbl(self.dir_lbl, "Dirección", font_size=12, width=dir_width)

            self.dir_field = Field(String, self.widget, optional=consts.CLIENT_DIR_OPTIONAL,
                                   max_len=consts.CLIENT_DIR_CHARS)
            self.dir_layout.addWidget(self.dir_field)
            config_line(self.dir_field, str(client.direction), width=dir_width)

            # Save and delete buttons.
            self.save_btn = QPushButton(self.widget)
            self.top_buttons_layout.addWidget(self.save_btn)
            config_btn(self.save_btn, text="Guardar", width=110)

            self.remove_btn = QPushButton(self.widget)
            self.top_buttons_layout.addWidget(self.remove_btn)
            config_btn(self.remove_btn, text="Eliminar", width=110)

            # Activities.
            self.subscriptions_lbl = QLabel(self.widget)
            self.layout.addWidget(self.subscriptions_lbl)
            config_lbl(self.subscriptions_lbl, "Actividades", font_size=12)

            # Layout that contains hidden buttons.
            self.bottom_layout = QHBoxLayout()
            self.layout.addLayout(self.bottom_layout)
            config_layout(self.bottom_layout, alignment=Qt.AlignCenter)

            self.subscription_table = QTableWidget(self.widget)
            self.bottom_layout.addWidget(self.subscription_table)
            config_table(self.subscription_table,
                         columns={"Nombre": 280, "Último\npago": 100, "Código\npago": 146, "Vencida": 90},
                         allow_resizing=True)  # ToDo. Set min width.

            # Buttons.
            self.bottom_buttons_layout = QVBoxLayout()
            self.bottom_layout.addLayout(self.bottom_buttons_layout)
            config_layout(self.bottom_buttons_layout, alignment=Qt.AlignTop)

            self.subscribe_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.subscribe_btn)
            config_btn(self.subscribe_btn, text="Inscribir en\nactividad", width=110)

            self.unsubscribe_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.unsubscribe_btn)
            config_btn(self.unsubscribe_btn, text="Dar de baja", width=110)

            self.charge_activity_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.charge_activity_btn)
            config_btn(self.charge_activity_btn, text="Cobrar\nactividad", width=110)

            self.transactions_btn = QPushButton(self.widget)
            self.bottom_buttons_layout.addWidget(self.transactions_btn)
            config_btn(self.transactions_btn, text="Ver pagos", width=110)

        self._setup_hidden_ui = _setup_hidden_ui
        self.hidden_ui_loaded = False  # Flag used to load the hidden ui only when it is opened for the first time.

        # noinspection PyUnresolvedReferences
        self.detail_btn.clicked.connect(self.hide_detail)
        self.is_hidden = False

    def _setup_ui(
            self, height: int, name_width: int, dni_width: int, admission_width: int, tel_width: int, dir_width: int
    ):
        self.widget = QWidget(self)

        self.layout = QVBoxLayout(self.widget)

        # Top layout.
        self.top_layout = QHBoxLayout()
        self.layout.addLayout(self.top_layout)
        config_layout(self.top_layout, alignment=Qt.AlignCenter)

        # Name layout.
        self.name_layout = QVBoxLayout()
        self.top_layout.addLayout(self.name_layout)

        self.name_summary = QLabel(self.widget)
        self.name_layout.addWidget(self.name_summary, alignment=Qt.AlignTop)
        config_lbl(self.name_summary, str(self.client.name), width=name_width, height=30, alignment=Qt.AlignVCenter)

        self.name_lbl: QLabel | None = None
        self.name_field: Field | None = None

        # DNI layout.
        self.dni_layout = QVBoxLayout()
        self.top_layout.addLayout(self.dni_layout)

        self.dni_summary = QLabel(self.widget)
        self.dni_layout.addWidget(self.dni_summary, alignment=Qt.AlignTop)
        config_lbl(self.dni_summary, str(self.client.dni), width=dni_width, height=30, alignment=Qt.AlignVCenter)

        self.dni_lbl: QLabel | None = None
        self.dni_field: Field | None = None

        # Admission layout.
        self.admission_layout = QVBoxLayout()
        self.top_layout.addLayout(self.admission_layout)

        self.admission_summary = QLabel(self.widget)
        self.admission_layout.addWidget(self.admission_summary, alignment=Qt.AlignTop)
        config_lbl(self.admission_summary, self.client.admission.strftime(consts.DATE_FORMAT),
                   width=admission_width, height=30, alignment=Qt.AlignVCenter)

        self.admission_lbl: QLabel | None = None
        self.admission_date_edit: QDateEdit | None = None

        # Telephone layout.
        self.tel_layout = QVBoxLayout()
        self.top_layout.addLayout(self.tel_layout)

        self.tel_summary = QLabel(self.widget)
        self.tel_layout.addWidget(self.tel_summary, alignment=Qt.AlignTop)
        config_lbl(self.tel_summary, str(self.client.telephone), width=tel_width, height=30, alignment=Qt.AlignVCenter)

        self.tel_lbl: QLabel | None = None
        self.tel_field: Field | None = None

        # Direction layout.
        self.dir_layout = QVBoxLayout()
        self.top_layout.addLayout(self.dir_layout)

        self.dir_summary = QLabel(self.widget)
        self.dir_layout.addWidget(self.dir_summary, alignment=Qt.AlignTop)
        config_lbl(self.dir_summary, str(self.client.direction), width=dir_width, height=30, alignment=Qt.AlignVCenter)

        self.dir_lbl: QLabel | None = None
        self.dir_field: Field | None = None

        # Some buttons.
        self.top_buttons_layout = QVBoxLayout()
        self.top_layout.addLayout(self.top_buttons_layout)

        self.detail_btn = QPushButton(self.widget)
        self.top_buttons_layout.addWidget(self.detail_btn, alignment=Qt.AlignTop)
        config_btn(self.detail_btn, text="Detalle", width=110)

        self.save_btn: QPushButton | None = None
        self.remove_btn: QPushButton | None = None

        # Bottom layout.
        self.bottom_layout: QHBoxLayout | None = None

        self.subscriptions_lbl: QLabel | None = None
        self.subscription_table: QTableWidget | None = None

        # Other buttons.
        self.bottom_buttons_layout: QVBoxLayout | None = None
        self.subscribe_btn: QPushButton | None = None
        self.unsubscribe_btn: QPushButton | None = None
        self.charge_activity_btn: QPushButton | None = None
        self.transactions_btn: QPushButton | None = None

        self.widget.setGeometry(QRect(0, 0, self.widget.sizeHint().width(), height))

    # noinspection PyUnresolvedReferences
    def _setup_callbacks(self):
        self.save_btn.clicked.connect(self.save_changes)
        self.remove_btn.clicked.connect(self.remove)
        self.subscribe_btn.clicked.connect(self.subscribe)
        self.unsubscribe_btn.clicked.connect(self.unsubscribe)
        self.charge_activity_btn.clicked.connect(self.charge)
        self.transactions_btn.clicked.connect(self.transactions)

    def _set_hidden(self, hidden: bool):
        # Hides widgets.
        self.name_lbl.setHidden(hidden)
        self.name_field.setHidden(hidden)
        self.dni_lbl.setHidden(hidden)
        self.dni_field.setHidden(hidden)
        self.admission_lbl.setHidden(hidden)
        self.admission_date_edit.setHidden(hidden)
        self.tel_lbl.setHidden(hidden)
        self.tel_field.setHidden(hidden)
        self.dir_lbl.setHidden(hidden)
        self.dir_field.setHidden(hidden)

        self.subscriptions_lbl.setHidden(hidden)
        self.subscription_table.setHidden(hidden)

        self.save_btn.setHidden(hidden)
        self.remove_btn.setHidden(hidden)
        self.subscribe_btn.setHidden(hidden)
        self.unsubscribe_btn.setHidden(hidden)
        self.charge_activity_btn.setHidden(hidden)
        self.transactions_btn.setHidden(hidden)

        # Updates the height of the widget.
        self.previous_height, self.current_height = self.current_height, self.previous_height

        new_width = self.widget.width()
        self.item.setSizeHint(QSize(new_width, self.current_height))
        self.resize(new_width, self.current_height)
        self.widget.resize(new_width, self.current_height)

        # Inverts the state of the widget.
        self.is_hidden = not hidden

    def hide_detail(self):
        # Creates the hidden widgets in case it is the first time the detail button is clicked.
        if not self.hidden_ui_loaded:
            self._setup_hidden_ui()
            self._setup_callbacks()
            self.hidden_ui_loaded, self.previous_height = True, 350
            self.load_subscriptions()

        # Hides previously opened detail.
        if self.main_ui_controller.opened_now is None:
            self.main_ui_controller.opened_now = self
        elif self.main_ui_controller.opened_now.client != self.client:
            self.main_ui_controller.opened_now._set_hidden(True)
            self.main_ui_controller.opened_now = self
        else:
            self.main_ui_controller.opened_now = None

        # Hide or show the widgets.
        self.item.listWidget().setCurrentItem(self.item)
        self._set_hidden(self.is_hidden)

    def save_changes(self):
        valid = all([self.name_field.valid_value(), self.dni_field.valid_value(), self.tel_field.valid_value(),
                     self.dir_field.valid_value()])
        if not valid:
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            # Updates client object.
            self.client.name = self.name_field.value()
            self.client.admission = self.admission_date_edit.date().toPyDate()
            self.client.telephone = self.tel_field.value()
            self.client.direction = self.dir_field.value()

            self.client_repo.update(self.client)

            # Updates ui.
            self.name_summary.setText(str(self.client.name))
            self.admission_summary.setText(self.client.admission.strftime(consts.DATE_FORMAT))
            self.tel_summary.setText(self.client.telephone.as_primitive())
            self.dir_summary.setText(self.client.direction.as_primitive())

            Dialog.info("Éxito", f"El cliente '{self.name_field.value()}' fue actualizado correctamente.")

    def remove(self):
        remove = Dialog.confirm(f"¿Desea eliminar el cliente '{self.client.name}'?")

        if remove:
            self.main_ui_controller.opened_now = None
            self.client_repo.remove(self.client)
            self.item.listWidget().takeItem(self.item.listWidget().currentRow())
            self.main_ui_controller.fill_client_table()

            Dialog.info("Éxito", f"El cliente '{self.name_field.value()}' fue eliminado correctamente.")

    # noinspection PyAttributeOutsideInit
    def subscribe(self):
        self.subscribe_ui = SubscribeUI(self.activity_manager, self.client)
        self.subscribe_ui.exec_()

        if self.subscribe_ui.controller.subscription is not None:
            row = self.subscription_table.rowCount()
            self.subscription_table.setRowCount(row + 1)
            self._load_subscription(row, self.subscribe_ui.controller.subscription)

    def unsubscribe(self):
        if self.subscription_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione una actividad")
        else:
            subscription = self.subscriptions[self.subscription_table.currentRow()]
            unsubscribe = Dialog.confirm(f"¿Desea cancelar la subscripcion del cliente {self.client.name} en la "
                                         f"actividad {subscription.activity.name}?")
            if unsubscribe:
                self.activity_manager.cancel(subscription)
                self.subscriptions.pop(self.subscription_table.currentRow())
                self.subscription_table.removeRow(self.subscription_table.currentRow())

    def _load_subscription(self, row: int, subscription: Subscription):
        self.subscriptions[row] = subscription
        self.subscription_table.setItem(row, 0, QTableWidgetItem(str(subscription.activity.name)))

        when = "Sin pagar" if subscription.transaction is None else str(subscription.transaction.when)
        self.subscription_table.setItem(row, 1, QTableWidgetItem(when))

        # noinspection PyUnresolvedReferences
        transaction_id = "-" if subscription.transaction is None else str(subscription.transaction.id)
        self.subscription_table.setItem(row, 2, QTableWidgetItem(transaction_id))

        expired = "Si" if subscription.charge_day_passed(date.today()) else "No"
        self.subscription_table.setItem(row, 3, QTableWidgetItem(expired))

    # noinspection PyAttributeOutsideInit
    def charge(self):
        if self.subscription_table.currentRow() == -1:
            Dialog.info("Error", "Seleccione una actividad")
        else:
            subscription = self.subscriptions[self.subscription_table.currentRow()]
            activity = subscription.activity
            descr = String(f"Cobro por actividad {activity.name}", max_len=consts.TRANSACTION_DESCR_CHARS)
            msg = (f"La fecha de cobro no puede ser previa a la fecha {subscription.when} de inscripción del cliente a"
                   f" la actividad.")
            self.charge_ui = ChargeUI(self.accounting_system, self.client, activity, descr, fixed_amount=True,
                                      fixed_descr=True, invalid_date_fn=invalid_date, validation_msg=msg,
                                      subscription=subscription)
            self.charge_ui.exec_()
            self._load_subscription(self.subscription_table.currentRow(), subscription)

    def load_subscriptions(self):
        self.subscription_table.setRowCount(self.client.n_subscriptions())

        for row, subscription in enumerate(self.client.subscriptions()):
            self._load_subscription(row, subscription)

    # noinspection PyAttributeOutsideInit
    def transactions(self):
        self.accounting_main_ui = AccountingMainUI(self.accounting_system, self.client)
        self.accounting_main_ui.setWindowModality(Qt.ApplicationModal)
        self.accounting_main_ui.show()


class Controller:
    def __init__(
            self, main_ui: ClientMainUI, client_repo: ClientRepo, activity_manager: ActivityManager,
            accounting_system: AccountingSystem, name_width: int, dni_width: int, admission_width: int,
            tel_width: int, dir_width: int
    ):
        self.client_repo = client_repo
        self.activity_manager = activity_manager
        self.accounting_system = accounting_system
        self.current_page, self.page_len = 1, 15
        self.opened_now: ClientRow | None = None

        self.main_ui = main_ui

        self.name_width = name_width
        self.dni_width = dni_width
        self.admission_width = admission_width
        self.tel_width = tel_width
        self.dir_width = dir_width

        # Configures the filtering widget.
        filters = (TextLike("name", display_name="Nombre", attr="name",
                            translate_fun=lambda client, value: client.cli_name.contains(value)), )
        self.main_ui.filter_header.config(filters, on_search_click=self.fill_client_table)

        # Configures the page index.
        self.main_ui.page_index.config(refresh_table=self.main_ui.filter_header.on_search_click,
                                       page_len=20, total_len=self.client_repo.count())

        # Fills the table.
        self.main_ui.filter_header.on_search_click()

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.main_ui.create_client_btn.clicked.connect(self.create_ui)

    def _add_client(
            self, client: Client, check_filters: bool, set_to_current: bool = False, check_limit: bool = False
    ):
        if check_limit and len(self.main_ui.client_list) == self.page_len:
            self.main_ui.client_list.takeItem(len(self.main_ui.client_list) - 1)

        if check_filters and not self.main_ui.filter_header.passes_filters(client):
            return

        item = QListWidgetItem(self.main_ui.client_list)
        self.main_ui.client_list.addItem(item)
        row_height = 50
        client_row = ClientRow(
            item, self, row_height, self.name_width, self.dni_width, self.admission_width, self.tel_width,
            self.dir_width, client, self.client_repo, self.activity_manager, self.accounting_system)
        self.main_ui.client_list.setItemWidget(item, client_row)

        if set_to_current:
            self.main_ui.client_list.setCurrentItem(item)

    def fill_client_table(self, filters: list[FilterValuePair]):
        self.main_ui.client_list.clear()

        self.main_ui.page_index.total_len = self.client_repo.count(filters)
        for client in self.client_repo.all(self.main_ui.page_index.page,
                                           self.main_ui.page_index.page_len, filters):
            self._add_client(client, check_filters=False)  # Clients are filtered in the repo.

    # noinspection PyAttributeOutsideInit
    def create_ui(self):
        self._create_ui = CreateUI(self.client_repo)
        self._create_ui.exec_()
        if self._create_ui.controller.client is not None:
            self._add_client(self._create_ui.controller.client, check_filters=True, set_to_current=True, check_limit=True)
            self.main_ui.page_index.total_len += 1  # ToDo. After removing a client, update the total_len.


class ClientMainUI(QMainWindow):

    def __init__(
            self, client_repo: ClientRepo, activity_manager: ActivityManager, accounting_system: AccountingSystem,
    ) -> None:
        super().__init__(parent=None)
        name_width, dni_width, admission_width, tel_width, dir_width = 175, 90, 100, 110, 140
        self._setup_ui(name_width, dni_width, admission_width, tel_width, dir_width)
        self.controller = Controller(self, client_repo, activity_manager, accounting_system, name_width, dni_width,
                                     admission_width, tel_width, dir_width)

    def _setup_ui(self, name_width: int, dni_width: int, admission_width: int, tel_width: int, dir_width: int):
        self.resize(800, 600)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)

        self.widget = QWidget(self.widget)
        self.widget.setGeometry(QRect(0, 0, 800, 600))

        self.layout = QVBoxLayout(self.widget)

        # Utilities.
        self.utils_layout = QHBoxLayout()
        self.layout.addLayout(self.utils_layout)
        config_layout(self.utils_layout, spacing=0, left_margin=40, top_margin=15, right_margin=80)

        # Filtering.
        self.filter_header = FilterHeader(parent=self.widget)
        self.utils_layout.addWidget(self.filter_header)

        self.utils_layout.addItem(QSpacerItem(80, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.create_client_btn = QPushButton(self.widget)
        self.utils_layout.addWidget(self.create_client_btn)
        config_btn(self.create_client_btn, "Nuevo cliente", font_size=16)

        self.layout.addItem(QSpacerItem(80, 15, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Header.
        self.header_layout = QHBoxLayout()
        self.layout.addLayout(self.header_layout)
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
        self.layout.addWidget(self.client_list)

        # Index.
        self.page_index = PageIndex(self)
        self.layout.addWidget(self.page_index)
