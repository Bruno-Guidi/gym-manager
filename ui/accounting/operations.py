from __future__ import annotations

from datetime import date
from typing import TypeAlias, Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, \
    QDateEdit, QComboBox, QTextEdit, QPushButton, QGridLayout, QSpacerItem, QSizePolicy

from gym_manager.core import constants as consts, system
from gym_manager.core.base import String, Client, Currency, Activity, Transaction
from gym_manager.core.persistence import TransactionRepo
from gym_manager.core.system import AccountingSystem
from ui.widget_config import config_layout, config_lbl, config_line, config_date_edit, config_combobox, fill_combobox, \
    config_btn
from ui.widgets import Field, valid_text_value, Dialog

InvalidDateFn: TypeAlias = Callable[[date], bool]


class ChargeController:
    def __init__(
            self, charge_ui: ChargeUI, client: Client, activity: Activity, descr: String,
            accounting_system: AccountingSystem, invalid_date_fn: InvalidDateFn | None = None,
            validation_msg: str | None = None, **invalid_date_kwargs
    ) -> None:
        self.charge_ui = charge_ui

        # Sets ui fields.
        self.charge_ui.client_line.setText(str(client.name))
        self.charge_ui.when_date_edit.setDate(date.today())
        self.charge_ui.amount_field.setText(str(activity.price))
        fill_combobox(self.charge_ui.method_combobox, accounting_system.methods,
                      display=lambda method: method.as_primitive())
        self.charge_ui.descr_text.setText(str(descr))

        self.transaction: Transaction | None = None
        self.client, self.activity = client, activity
        self.accounting_system = accounting_system

        # Function used to do an extra validation to the transaction date, that can't be done with the information
        # available in this context.
        self.invalid_date_fn = invalid_date_fn
        self.validation_msg = validation_msg
        self.invalid_date_kwargs = invalid_date_kwargs

        # Sets callbacks
        # noinspection PyUnresolvedReferences
        self.charge_ui.ok_btn.clicked.connect(self.charge)
        # noinspection PyUnresolvedReferences
        self.charge_ui.cancel_btn.clicked.connect(self.charge_ui.reject)

    # noinspection PyTypeChecker
    # noinspection PyArgumentList
    def charge(self):
        valid_descr, descr = valid_text_value(self.charge_ui.descr_text, optional=False,
                                              max_len=consts.TRANSACTION_DESCR_CHARS)
        valid_fields = all([self.charge_ui.amount_field.valid_value(), self.charge_ui.responsible_field.valid_value(),
                            valid_descr])
        if not valid_fields:
            Dialog.info("Error", "Hay datos que no son válidos.")
        else:
            transaction_date = self.charge_ui.when_date_edit.date().toPyDate()
            if self.invalid_date_fn is not None and self.invalid_date_fn(transaction_date, **self.invalid_date_kwargs):
                Dialog.info("Error", self.validation_msg)
            else:
                self.transaction = self.accounting_system.charge(
                    transaction_date, self.client, self.activity,
                    self.charge_ui.method_combobox.currentData(Qt.UserRole),
                    self.charge_ui.responsible_field.value(),
                    descr
                )
                Dialog.confirm(f"Se ha registrado un cobro con número de identificación '{self.transaction.id}'.")
                self.charge_ui.descr_text.window().close()


class ChargeUI(QDialog):
    def __init__(
            self, accounting_system: AccountingSystem, client: Client, activity: Activity, descr: String,
            invalid_date_fn: InvalidDateFn | None = None, validation_msg: str | None = None, **invalid_date_kwargs
    ) -> None:
        super().__init__()
        self._setup_ui()
        self.controller = ChargeController(self, client, activity, descr, accounting_system, invalid_date_fn, validation_msg, **invalid_date_kwargs)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)

        # Client.
        self.client_lbl = QLabel(self)
        self.form_layout.addWidget(self.client_lbl, 0, 0)
        config_lbl(self.client_lbl, "Cliente")

        self.client_line = QLineEdit(self)
        self.form_layout.addWidget(self.client_line, 0, 1)
        config_line(self.client_line, adjust_to_hint=False, read_only=True)

        # Date.
        self.when_lbl = QLabel(self)
        self.form_layout.addWidget(self.when_lbl, 1, 0)
        config_lbl(self.when_lbl, "Fecha")

        self.when_date_edit = QDateEdit(self)
        self.form_layout.addWidget(self.when_date_edit, 1, 1)
        config_date_edit(self.when_date_edit, date.today(), calendar=True)

        # Method.
        self.method_lbl = QLabel(self)
        self.form_layout.addWidget(self.method_lbl, 2, 0)
        config_lbl(self.method_lbl, "Método")

        self.method_combobox = QComboBox(self)
        self.form_layout.addWidget(self.method_combobox, 2, 1)
        config_combobox(self.method_combobox, fixed_width=self.when_date_edit.width())

        # Amount.
        self.amount_lbl = QLabel(self)
        self.form_layout.addWidget(self.amount_lbl, 3, 0)
        config_lbl(self.amount_lbl, "Monto")

        self.amount_field = Field(Currency, parent=self)
        self.form_layout.addWidget(self.amount_field, 3, 1)
        config_line(self.amount_field, adjust_to_hint=False, enabled=False)

        # Responsible.
        self.responsible_lbl = QLabel(self)
        self.form_layout.addWidget(self.responsible_lbl, 4, 0)
        config_lbl(self.responsible_lbl, "Responsable")

        self.responsible_field = Field(String, parent=self, max_len=consts.CLIENT_DIR_CHARS)
        self.form_layout.addWidget(self.responsible_field, 4, 1)
        config_line(self.responsible_field, adjust_to_hint=False)

        # Description.
        self.descr_lbl = QLabel(self)
        self.form_layout.addWidget(self.descr_lbl, 5, 0)
        config_lbl(self.descr_lbl, "Descripción")

        self.descr_text = QTextEdit(self)
        self.form_layout.addWidget(self.descr_text, 5, 1)
        config_line(self.descr_text, extra_width=30, adjust_to_hint=False, enabled=False)

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)
        config_layout(self.buttons_layout)

        self.ok_btn = QPushButton()
        self.buttons_layout.addWidget(self.ok_btn)
        config_btn(self.ok_btn, "Ok")

        self.cancel_btn = QPushButton()
        self.buttons_layout.addWidget(self.cancel_btn)
        config_btn(self.cancel_btn, "Cancelar")


class ExtractController:
    def __init__(
            self, extract_ui: ExtractUI, transaction_repo: TransactionRepo, transaction_methods: tuple[String, ...]
    ):
        self.extract_ui = extract_ui
        self.transaction_repo = transaction_repo

        self.extraction: Transaction | None = None

        # Loads info into the ui.
        fill_combobox(self.extract_ui.method_combobox, transaction_methods, display=lambda method: str(method))

        # Sets callbacks.
        # noinspection PyUnresolvedReferences
        self.extract_ui.confirm_btn.clicked.connect(self.confirm_extraction)
        # noinspection PyUnresolvedReferences
        self.extract_ui.cancel_btn.clicked.connect(self.extract_ui.reject)

    def confirm_extraction(self):
        valid_descr, description = valid_text_value(self.extract_ui.descr_text, max_len=consts.TRANSACTION_DESCR_CHARS)
        valid_fields = all([
            self.extract_ui.amount_field.valid_value(), self.extract_ui.responsible_field.valid_value(), valid_descr
        ])
        if self.extract_ui.method_combobox.currentIndex() == -1:
            Dialog.info("Error", "Seleccione un método.")
        elif not valid_fields:
            Dialog.info("Error", "Hay campos que no son válidos.")
        else:
            # noinspection PyTypeChecker
            self.extraction = system.register_extraction(self.extract_ui.when_date_edit.date().toPyDate(),
                                                         self.extract_ui.amount_field.value(),
                                                         self.extract_ui.method_combobox.currentData(Qt.UserRole),
                                                         self.extract_ui.responsible_field.value(),
                                                         description,
                                                         self.transaction_repo)
            Dialog.info("Éxito",
                        f"Se ha registrado una extracción con número de identificación '{self.extraction.id}'.")
            self.extract_ui.descr_text.window().close()


class ExtractUI(QDialog):
    def __init__(
            self, transaction_repo: TransactionRepo, transaction_methods: tuple[String, ...]
    ):
        super().__init__()
        self._setup_ui()
        self.controller = ExtractController(self, transaction_repo, transaction_methods)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)

        # Form.
        self.form_layout = QGridLayout()
        self.layout.addLayout(self.form_layout)

        # Date.
        self.when_lbl = QLabel(self)
        self.form_layout.addWidget(self.when_lbl, 0, 0)
        config_lbl(self.when_lbl, "Fecha")

        self.when_date_edit = QDateEdit(self)
        self.form_layout.addWidget(self.when_date_edit, 0, 1)
        config_date_edit(self.when_date_edit, date.today(), calendar=True)

        # Method.
        self.method_lbl = QLabel(self)
        self.form_layout.addWidget(self.method_lbl, 1, 0)
        config_lbl(self.method_lbl, "Método")

        self.method_combobox = QComboBox(self)
        self.form_layout.addWidget(self.method_combobox, 1, 1)
        config_combobox(self.method_combobox, fixed_width=self.when_date_edit.width())

        # Amount.
        self.amount_lbl = QLabel(self)
        self.form_layout.addWidget(self.amount_lbl, 2, 0)
        config_lbl(self.amount_lbl, "Monto*")

        self.amount_field = Field(Currency, parent=self)
        self.form_layout.addWidget(self.amount_field, 2, 1)
        config_line(self.amount_field, place_holder="000000000,00", adjust_to_hint=False)

        # Responsible.
        self.responsible_lbl = QLabel(self)
        self.form_layout.addWidget(self.responsible_lbl, 3, 0)
        config_lbl(self.responsible_lbl, "Responsable*")

        self.responsible_field = Field(String, parent=self, max_len=consts.CLIENT_NAME_CHARS)
        self.form_layout.addWidget(self.responsible_field, 3, 1)
        config_line(self.responsible_field, place_holder="Responsable", adjust_to_hint=False)

        # Description.
        self.descr_lbl = QLabel(self)
        self.form_layout.addWidget(self.descr_lbl, 4, 0, alignment=Qt.AlignTop)
        config_lbl(self.descr_lbl, "Descripción*")

        self.descr_text = QTextEdit(self)
        self.form_layout.addWidget(self.descr_text, 4, 1)
        config_line(self.descr_text, place_holder="Descripción", extra_width=30, adjust_to_hint=False)

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
        self.setFixedSize(self.sizeHint())
