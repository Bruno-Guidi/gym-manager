from __future__ import annotations

from datetime import date, datetime, time
from typing import Type, Any, Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLineEdit, QWidget, QTextEdit, QHBoxLayout, QComboBox, QDialog, QVBoxLayout, QLabel,
    QPushButton, QDateEdit, QSpacerItem, QSizePolicy, QFrame)

from gym_manager.core.base import Validatable, ValidationError, String, Filter, ONE_MONTH_TD, DateGreater, DateLesser
from gym_manager.core.persistence import FilterValuePair
from gym_manager.core.security import SecurityHandler, SecurityError
from ui import utils
from ui.utils import MESSAGE
from ui.widget_config import (
    fill_combobox, config_combobox, config_line, config_lbl, config_btn, config_layout,
    config_date_edit)

_text_base_stylesheet = None


def valid_text_value(text: QTextEdit, max_len: int, optional: bool = False) -> tuple[bool, Any]:
    global _text_base_stylesheet
    if _text_base_stylesheet is None:
        _text_base_stylesheet = QTextEdit().styleSheet()
    valid, value = False, None
    try:
        value = String(text.toPlainText(), optional=optional, max_len=max_len)
        valid = True
        text.setStyleSheet(_text_base_stylesheet)
    except ValidationError:
        text.setStyleSheet("border: 1px solid red")
    return valid, value


def responsible_field(parent: QWidget | None = None) -> Field:
    return Field(String, parent, is_password=True, optional=True, max_len=utils.RESP_CHARS)


def Separator(vertical: bool, parent: QWidget | None = None):
    sep = QFrame(parent)
    sep.setFrameShape(QFrame.VLine if vertical else QFrame.HLine)
    sep.setFrameShadow(QFrame.Sunken)
    if vertical:
        sep.setFixedWidth(3)
    else:
        sep.setFixedHeight(3)

    return sep


class Field(QLineEdit):
    def __init__(
            self, validatable: Type[Validatable], parent: QWidget | None = None, is_password: bool = False,
            **validate_args
    ) -> None:
        self.validatable = validatable
        self.validate_args = validate_args
        super().__init__(parent)
        if is_password:
            self.setEchoMode(QLineEdit.Password)
        self.base_style_sheet = self.styleSheet()

    def setText(self, text: str) -> None:
        self.setStyleSheet(self.base_style_sheet)
        super().setText(text)

    def valid_value(self) -> bool:
        try:
            self.validatable(self.text(), **self.validate_args)
            self.setStyleSheet(self.base_style_sheet)
            return True
        except ValidationError:
            self.setStyleSheet("border: 1px solid red")
            return False

    def value(self) -> Validatable:
        return self.validatable(self.text(), **self.validate_args)


class FilterHeader(QWidget):
    def __init__(
            self,
            date_greater_filtering: bool = False,
            date_lesser_filtering: bool = False,
            show_clear_button: bool = True,
            parent: QWidget | None = None
    ):
        super().__init__(parent)
        self._setup_ui(date_greater_filtering, date_lesser_filtering, show_clear_button)

        self._filter_number: dict[str, int] | None = None
        self._date_greater_filter: DateGreater | None = None
        self._date_lesser_filter: DateLesser | None = None

        self._on_search_click: Callable[[list[FilterValuePair]], None] | None = None
        self.allow_empty_filter: bool = True

        # noinspection PyUnresolvedReferences
        self.search_btn.clicked.connect(self.on_search_click)
        # noinspection PyUnresolvedReferences
        self.clear_filter_btn.clicked.connect(self.on_clear_click)
        # noinspection PyUnresolvedReferences
        self.filter_line_edit.returnPressed.connect(self.on_search_click)
        if date_greater_filtering:
            # noinspection PyUnresolvedReferences
            self.from_date_edit.dateChanged.connect(self.on_search_click)
        if date_lesser_filtering:
            # noinspection PyUnresolvedReferences
            self.to_date_edit.dateChanged.connect(self.on_search_click)

    def _setup_ui(self, date_greater_filtering: bool, date_lesser_filtering: bool, show_clear_button: bool):
        self.layout = QHBoxLayout(self)
        config_layout(self.layout, spacing=0)

        # Horizontal spacer.
        self.layout.addSpacerItem(QSpacerItem(30, 10, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum))

        self.filter_combobox = QComboBox(self)
        self.layout.addWidget(self.filter_combobox)

        self.filter_line_edit = QLineEdit(self)
        self.layout.addWidget(self.filter_line_edit)
        config_line(self.filter_line_edit, place_holder="Búsqueda")

        self.clear_filter_btn = QPushButton(self)
        self.layout.addWidget(self.clear_filter_btn)
        config_btn(self.clear_filter_btn, icon_path=r"ui/resources/clear.png", icon_size=30)
        self.clear_filter_btn.setVisible(show_clear_button)

        self.search_btn = QPushButton(self)
        self.layout.addWidget(self.search_btn)
        config_btn(self.search_btn, icon_path=r"ui/resources/search.png", icon_size=30)

        self.from_layout: QVBoxLayout | None = None
        self.from_lbl: QLabel | None = None
        self.from_date_edit: QDateEdit | None = None
        if date_greater_filtering:
            # Horizontal spacer.
            self.layout.addSpacerItem(QSpacerItem(30, 10, QSizePolicy.Minimum, QSizePolicy.Minimum))

            self.from_layout = QVBoxLayout()
            self.layout.addLayout(self.from_layout)

            self.from_lbl = QLabel(self)
            self.from_layout.addWidget(self.from_lbl)
            config_lbl(self.from_lbl, "Desde")

            self.from_date_edit = QDateEdit(self)
            self.from_layout.addWidget(self.from_date_edit)
            config_date_edit(self.from_date_edit, date.today() - ONE_MONTH_TD, calendar=True)

        self.to_layout: QVBoxLayout | None = None
        self.to_lbl: QLabel | None = None
        self.to_date_edit: QDateEdit | None = None
        if date_lesser_filtering:
            # Horizontal spacer.
            self.layout.addSpacerItem(QSpacerItem(15, 10, QSizePolicy.Fixed, QSizePolicy.Fixed))

            self.to_layout = QVBoxLayout()
            self.layout.addLayout(self.to_layout)

            self.to_lbl = QLabel(self)
            self.to_layout.addWidget(self.to_lbl)
            config_lbl(self.to_lbl, "Hasta")

            self.to_date_edit = QDateEdit(self)
            self.to_layout.addWidget(self.to_date_edit)
            config_date_edit(self.to_date_edit, date.today(), calendar=True)

        # Horizontal spacer.
        self.layout.addSpacerItem(QSpacerItem(30, 10, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum))

    def setEnabled(self, enabled: bool) -> None:
        self.filter_combobox.setEnabled(enabled)
        self.filter_line_edit.setEnabled(enabled)
        self.search_btn.setEnabled(enabled)

    def config(
            self,
            filters: tuple[Filter, ...],
            on_search_click: Callable[[list[FilterValuePair]], None],
            date_greater_filter: DateGreater | None = None,
            date_lesser_filter: DateLesser | None = None,
            allow_empty_filter: bool = True
    ):
        # Some checks to ensure that date filters are set in case their corresponding flags were True.
        if self.from_lbl is None and date_greater_filter is not None:
            raise AttributeError("date_greater_filtering flag was False, but a DateGreater filter was configured.")
        if self.from_lbl is not None and date_greater_filter is None:
            raise AttributeError("date_greater_filtering flag was True, but DateGreater filter was not configured.")
        if self.to_lbl is None and date_lesser_filter is not None:
            raise AttributeError("date_lesser_filtering flag was False, but a DateLesser filter was configured.")
        if self.to_lbl is not None and date_lesser_filter is None:
            raise AttributeError("date_lesser_filtering flag was True, but DateLesser filter was not configured.")

        # Configuration.
        fill_combobox(self.filter_combobox, filters, display=lambda filter_: filter_.display_name)
        config_combobox(self.filter_combobox)
        self._filter_number = {filter_.name: i for i, filter_ in enumerate(filters)}
        self._date_greater_filter, self._date_lesser_filter = date_greater_filter, date_lesser_filter
        self.allow_empty_filter = allow_empty_filter

        self._on_search_click = on_search_click

    def set_filter(self, name: str, value: str):
        self.filter_combobox.setCurrentIndex(self._filter_number[name])
        self.filter_line_edit.setText(value)

    def passes_filters(self, obj) -> bool:
        for filter_, value in self._generate_filters():
            try:
                if not filter_.passes(obj, value):
                    return False
            except (AttributeError, TypeError):
                Dialog.info("Error", f"El valor '{value}' no es válido para el filtro '{filter_.display_name}'")
                return False
        return True

    def _generate_filters(self, from_date: date | None = None, to_date: date | None = None) -> list[FilterValuePair]:
        filter_, value = self.filter_combobox.currentData(Qt.UserRole), self.filter_line_edit.text()
        filters = [] if len(value) == 0 or value.isspace() else [(filter_, value)]

        # By default, it doesn't matter that from_date is greater than to_date.
        # The problem appears when the user is actively filtering. In that case the user needs to be notified of the
        # reason that there are no results in the table. For simplicity, this notification has to be done outside this
        # method.
        # This approach is useful when adding one element to the table being filtered. We don't need to notify the user
        # that the dates are invalid, because he wasn't actively filtering. If the dates are invalid, the new element
        # simply won't pass the filtering and won't be displayed.
        from_date = self.from_date_edit.date().toPyDate() if self._date_greater_filter is not None else from_date
        if from_date is not None:
            filters.append((self._date_greater_filter, datetime.combine(from_date, time.min)))
        to_date = self.to_date_edit.date().toPyDate() if self._date_lesser_filter is not None else to_date
        if to_date is not None:
            filters.append((self._date_lesser_filter, datetime.combine(to_date, time.max)))

        return filters

    def on_search_click(self):
        if self._on_search_click is None:
            raise AttributeError("Function 'on_search_click' was not defined.")

        from_date = self.from_date_edit.date().toPyDate() if self._date_greater_filter is not None else None
        to_date = self.to_date_edit.date().toPyDate() if self._date_lesser_filter is not None else None
        if from_date is not None and to_date is not None and from_date > to_date:
            # There is a problem with the date filtering set by the user.
            Dialog.info("Error", "La fecha 'desde' no puede ser posterior a la fecha 'hasta'.")
        else:
            filters = self._generate_filters(from_date, to_date)
            if not self.allow_empty_filter and len(filters) == 0:
                Dialog.info("Error", "La caja de búsqueda no puede estar vacia.")
            else:
                self._on_search_click(self._generate_filters(from_date, to_date))

    def on_clear_click(self):
        if self._on_search_click is None:
            raise AttributeError("Function 'on_search_click' was not defined.")
        self.filter_line_edit.clear()
        if self.from_date_edit is not None:
            self.from_date_edit.setDate(date.today() - ONE_MONTH_TD)
        if self.to_date_edit is not None:
            self.to_date_edit.setDate(date.today())
        self._on_search_click(self._generate_filters())


class Dialog(QDialog):
    @classmethod
    def confirm(cls, question: str, ok_btn_text: str | None = None, cancel_btn_text: str | None = None) -> bool:
        dialog = Dialog(title="Confirmar", text=question, show_cancel_btn=True)
        if ok_btn_text is not None:
            dialog.confirm_btn.setText(ok_btn_text)
        if cancel_btn_text is not None:
            dialog.cancel_btn.setText(cancel_btn_text)
        dialog.exec_()
        return dialog.confirmed

    @classmethod
    def info(cls, title: str, message: str) -> bool:
        dialog = Dialog(title=title, text=message, show_cancel_btn=False)
        dialog.exec_()
        return True

    def __init__(self, title: str, text: str, show_cancel_btn: bool) -> None:
        super().__init__()
        self._setup_ui(title, text, show_cancel_btn)
        self.confirmed = False
        # noinspection PyUnresolvedReferences
        self.confirm_btn.clicked.connect(self.accept)
        if self.cancel_btn is not None:
            # noinspection PyUnresolvedReferences
            self.cancel_btn.clicked.connect(self.reject)

    def _setup_ui(self, title: str, text: str, show_cancel_btn: bool):
        self.setWindowTitle(title)

        self.layout = QVBoxLayout(self)

        self.text_lbl = QLabel(self)
        self.layout.addWidget(self.text_lbl, alignment=Qt.AlignCenter)
        config_lbl(self.text_lbl, text, fixed_width=300, alignment=Qt.AlignLeft)
        # Adjusts the label size according to the text length
        self.text_lbl.setWordWrap(True)
        self.text_lbl.adjustSize()
        self.text_lbl.setMinimumSize(self.text_lbl.sizeHint())

        # Vertical spacer.
        self.layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

        # Buttons.
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)
        self.buttons_layout.setAlignment(Qt.AlignRight)

        self.confirm_btn = QPushButton(self)
        self.buttons_layout.addWidget(self.confirm_btn)
        config_btn(self.confirm_btn, "Confirmar", extra_width=20)

        self.cancel_btn: QPushButton | None = None
        if show_cancel_btn:
            self.cancel_btn = QPushButton(self)
            self.buttons_layout.addWidget(self.cancel_btn)
            config_btn(self.cancel_btn, "Cancelar")

        # Adjusts size.
        self.setMaximumSize(self.minimumWidth(), self.minimumHeight())

    def accept(self) -> None:
        self.confirmed = True
        super().accept()

    def reject(self) -> None:
        self.confirmed = False
        super().reject()


class DialogWithResp(QDialog):
    @classmethod
    def confirm(cls, question: str, security_handler: SecurityHandler, fn: Callable) -> bool:
        dialog = DialogWithResp("Confirmar", question, security_handler, fn)
        dialog.exec_()
        return dialog.confirmed

    def __init__(self, title: str, text: str, security_handler: SecurityHandler, fn: Callable):
        super().__init__()
        self._setup_ui(title, text)

        self.confirmed = False
        self.security_handler = security_handler
        self.fn = fn

        # noinspection PyUnresolvedReferences
        self.confirm_btn.clicked.connect(self.accept)
        # noinspection PyUnresolvedReferences
        self.cancel_btn.clicked.connect(self.reject)

    def _setup_ui(self, title: str, text: str):
        self.setWindowTitle(title)

        self.layout = QVBoxLayout(self)

        self.text_lbl = QLabel(self)
        self.layout.addWidget(self.text_lbl, alignment=Qt.AlignCenter)
        config_lbl(self.text_lbl, text, fixed_width=300, alignment=Qt.AlignLeft)
        # Adjusts the label size according to the text length
        self.text_lbl.setWordWrap(True)
        self.text_lbl.adjustSize()
        self.text_lbl.setMinimumSize(self.text_lbl.sizeHint())

        # Responsible.
        self.responsible_layout = QHBoxLayout()
        self.layout.addLayout(self.responsible_layout)

        self.responsible_lbl = QLabel(self)
        self.responsible_layout.addWidget(self.responsible_lbl)
        config_lbl(self.responsible_lbl, "Responsable*")

        self.responsible_field = responsible_field(self)
        self.responsible_layout.addWidget(self.responsible_field)
        config_line(self.responsible_field, place_holder="Responsable", adjust_to_hint=False)

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
        config_btn(self.cancel_btn, "Cancelar")

        # Adjusts size.
        self.setMaximumSize(self.minimumWidth(), self.minimumHeight())

    def accept(self) -> None:
        if self.responsible_field.valid_value():
            try:
                self.security_handler.current_responsible = self.responsible_field.value()
                self.fn()

                self.confirmed = True
                super().accept()
            except SecurityError as sec_err:
                Dialog.info("Error", MESSAGE.get(sec_err.code, str(sec_err)))

    def reject(self) -> None:
        self.confirmed = False
        super().reject()


class PageIndex(QWidget):
    # noinspection PyPep8
    """
        Setting up a PageIndex:

        + Create the widget and add it to a layout of the QMainWindow.
        + Call (BEFORE FILLING THE TABLE IN DISPLAY) the method config(args). Pass the Callable to run when changing page, the page length, and the total length.
        + Inside the method that fills the table in display, set the PageIndex total_len property with the amount of expected rows (with the active filters applied).
        + If it is possible to add or remove rows manually, after each of these actions update the PageIndex total_len property accordingly.
        """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

        self.page, self.page_len, self._total_len = 1, None, None

        self._refresh_table: Callable[[], None] | None = None

        # noinspection PyUnresolvedReferences
        self.prev_btn.clicked.connect(self.on_prev_clicked)
        # noinspection PyUnresolvedReferences
        self.next_btn.clicked.connect(self.on_next_clicked)

    def _setup_ui(self):
        self.layout = QHBoxLayout(self)
        config_layout(self.layout)

        self.info_lbl = QLabel(self)
        self.layout.addWidget(self.info_lbl, alignment=Qt.AlignRight)
        config_lbl(self.info_lbl, f"xxxxx - yyyyy, de zzzzz", font_size=13, alignment=Qt.AlignCenter)

        self.prev_btn = QPushButton(self)
        self.layout.addWidget(self.prev_btn)
        config_btn(self.prev_btn, icon_path="ui/resources/prev_page.png", icon_size=32)

        # Horizontal spacer.
        self.layout.addSpacerItem(QSpacerItem(10, 1, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.index_lbl = QLabel(self)
        self.layout.addWidget(self.index_lbl)
        config_lbl(self.index_lbl, "xxx", font_size=16, alignment=Qt.AlignCenter)

        # Horizontal spacer.
        self.layout.addSpacerItem(QSpacerItem(10, 1, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.next_btn = QPushButton(self)
        self.layout.addWidget(self.next_btn)
        config_btn(self.next_btn, icon_path="ui/resources/next_page.png", icon_size=32)

        # Horizontal spacer. Adjusts the layout, causing the page_lbl to be in its center.
        self.spacer = QSpacerItem(self.info_lbl.width(), 1, QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.layout.addSpacerItem(self.spacer)

    @property
    def total_len(self):
        return self._total_len

    @total_len.setter
    def total_len(self, total_len: int):
        self._total_len = total_len
        self._update()

    def config(self, refresh_table: Callable[[], None], page_len: int, total_len: int = 0, show_info: bool = True):
        self.page_len, self.total_len = page_len, total_len if total_len != 0 else float("inf")
        self._refresh_table = refresh_table

        if not show_info:
            self.info_lbl.hide()
            self.layout.removeItem(self.spacer)

        self._update()

    def _update(self):
        roof = self.page * self.page_len if self.page * self.page_len < self.total_len else self.total_len
        self.info_lbl.setText(f"{(self.page - 1) * self.page_len + 1} - {roof}, de {self.total_len}")
        self.index_lbl.setText(str(self.page))

        self.prev_btn.setEnabled(self.page != 1)
        self.next_btn.setEnabled(self.page * self.page_len < self.total_len)

    def on_prev_clicked(self):
        if self.page_len is None or self.total_len is None or self._refresh_table is None:
            raise AttributeError("PageIndex widget was not configured.")

        self.page -= 1
        self._update()
        self._refresh_table()

    def on_next_clicked(self):
        if self.page_len is None or self.total_len is None or self._refresh_table is None:
            raise AttributeError("PageIndex widget was not configured.")

        self.page += 1
        self._update()
        self._refresh_table()
