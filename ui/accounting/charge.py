from datetime import date

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, \
    QDateEdit, QComboBox, QTextEdit, QPushButton

from gym_manager.core import constants as consts
from gym_manager.core.base import String, Client, Currency, Activity
from gym_manager.core.system import AccountingSystem
from ui.widget_config import config_layout, config_lbl, config_line, config_date_edit, config_combobox, fill_combobox, \
    config_btn
from ui.widgets import Field, valid_text_value, Dialog


class Controller:
    def __init__(
            self, client_field: QLineEdit, when_field: QDateEdit, amount_field: Field, method_field: QComboBox,
            responsible_field: Field, descr_field: QTextEdit,
            client: Client, activity: Activity, descr: String, accounting_system: AccountingSystem,
            fixed_amount: bool = False, fixed_descr: bool = False,

    ) -> None:
        # This fields are the ones that could be edited depending on the context.
        self.when_field = when_field
        self.amount_field = amount_field
        self.method_field = method_field
        self.responsible_field = responsible_field
        self.descr_field = descr_field

        client_field.setText(str(client.name))
        self.when_field.setDate(date.today())
        self.amount_field.setText(str(activity.price))
        if fixed_amount:
            self.amount_field.setEnabled(False)
        fill_combobox(method_field, accounting_system.methods(), display=lambda method: method.as_primitive())
        self.descr_field.setText(str(descr))
        if fixed_descr:
            self.descr_field.setEnabled(False)

        self.client, self.activity = client, activity
        self.accounting_system = accounting_system

    # noinspection PyTypeChecker
    def charge(self):
        valid_descr, descr = valid_text_value(self.descr_field, optional=False, max_len=consts.TRANSACTION_DESCR_CHARS)
        if not all([self.amount_field.valid_value(), self.responsible_field.valid_value(), valid_descr]):
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            transaction_id = self.accounting_system.charge(
                self.when_field.date().toPyDate(), self.client, self.activity,
                self.method_field.currentData(Qt.UserRole), self.responsible_field.value(), descr)
            Dialog.confirm(f"Se ha registrado un cobro con número de identificación '{transaction_id}'.")
            self.descr_field.window().close()


class ChargeUI(QDialog):
    def __init__(
            self, accounting_system: AccountingSystem, client: Client, activity: Activity, descr: String,
            fixed_amount: bool = False, fixed_descr: bool = False
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = Controller(self.client_field, self.when_field, self.amount_field, self.method_field,
                                     self.responsible_field, self.descr_field, client, activity, descr,
                                     accounting_system, fixed_amount, fixed_descr)

        self.ok_btn.clicked.connect(self.controller.charge)
        self.cancel_btn.clicked.connect(self.reject)

    def _setup_ui(self):
        self.resize(400, 300)

        self.layout = QVBoxLayout(self)

        self.form_layout = QVBoxLayout()
        self.layout.addLayout(self.form_layout)

        # Client.
        self.client_layout = QHBoxLayout()
        self.form_layout.addLayout(self.client_layout)
        config_layout(self.client_layout, alignment=Qt.AlignLeft)

        self.client_lbl = QLabel()
        self.client_layout.addWidget(self.client_lbl)
        config_lbl(self.client_lbl, "Cliente", font_size=16, width=120)

        self.client_field = QLineEdit()
        self.client_layout.addWidget(self.client_field)
        config_line(self.client_field, font_size=16, enabled=False)

        # Date.
        self.when_layout = QHBoxLayout()
        self.form_layout.addLayout(self.when_layout)
        config_layout(self.when_layout, alignment=Qt.AlignLeft)

        self.when_lbl = QLabel()
        self.when_layout.addWidget(self.when_lbl)
        config_lbl(self.when_lbl, "Fecha", font_size=16, width=120)

        self.when_field = QDateEdit()
        self.when_layout.addWidget(self.when_field)
        config_date_edit(self.when_field, date.today(), font_size=16, calendar=False)

        # Amount.
        self.amount_layout = QHBoxLayout()
        self.form_layout.addLayout(self.amount_layout)
        config_layout(self.amount_layout, alignment=Qt.AlignLeft)

        self.amount_lbl = QLabel()
        self.amount_layout.addWidget(self.amount_lbl)
        config_lbl(self.amount_lbl, "Monto", font_size=16, width=120)

        self.amount_field = Field(Currency, max_currency=consts.MAX_CURRENCY)
        self.amount_layout.addWidget(self.amount_field)
        config_line(self.amount_field, place_holder="000.00", font_size=16, height=30)

        # Method.
        self.method_layout = QHBoxLayout()
        self.form_layout.addLayout(self.method_layout)
        config_layout(self.method_layout, alignment=Qt.AlignLeft)

        self.method_lbl = QLabel(self)
        self.method_layout.addWidget(self.method_lbl)
        config_lbl(self.method_lbl, "Método", font_size=16, width=120)

        self.method_field = QComboBox()
        self.method_layout.addWidget(self.method_field)
        config_combobox(self.method_field, font_size=16)

        # Responsible.
        self.responsible_layout = QHBoxLayout()
        self.form_layout.addLayout(self.responsible_layout)
        config_layout(self.responsible_layout, alignment=Qt.AlignLeft)

        self.responsible_lbl = QLabel(self)
        self.responsible_layout.addWidget(self.responsible_lbl)
        config_lbl(self.responsible_lbl, "Responsable", font_size=16, width=120)

        self.responsible_field = Field(String, max_len=consts.CLIENT_DIR_CHARS)
        self.responsible_layout.addWidget(self.responsible_field)
        config_line(self.responsible_field, place_holder="Responsable", font_size=16)

        # Description.
        self.descr_layout = QHBoxLayout()
        self.form_layout.addLayout(self.descr_layout)
        config_layout(self.descr_layout, alignment=Qt.AlignLeft)

        self.descr_lbl = QLabel(self)
        self.descr_layout.addWidget(self.descr_lbl)
        config_lbl(self.descr_lbl, "Descripción", font_size=16, width=120)

        self.descr_field = QTextEdit()
        self.descr_layout.addWidget(self.descr_field)
        config_line(self.descr_field, place_holder="Descripción", font_size=16)

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)
        config_layout(self.buttons_layout, alignment=Qt.AlignRight, right_margin=5)

        self.ok_btn = QPushButton()
        self.buttons_layout.addWidget(self.ok_btn)
        config_btn(self.ok_btn, "Ok", width=100)

        self.cancel_btn = QPushButton()
        self.buttons_layout.addWidget(self.cancel_btn)
        config_btn(self.cancel_btn, "Cancelar", width=100)
