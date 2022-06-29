from __future__ import annotations

from typing import Type, Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit, QWidget, QTextEdit, QHBoxLayout, QComboBox, QDialog, QVBoxLayout, QLabel, \
    QPushButton

from gym_manager.core.base import Validatable, ValidationError, String, Filter
from ui.widget_config import fill_combobox, config_combobox, config_line, config_lbl, config_btn, config_layout


def valid_text_value(text: QTextEdit, optional: bool, max_len: int) -> tuple[bool, Any]:
    valid, value = False, None
    try:
        value = String(text.toPlainText(), optional=optional, max_len=max_len)
        valid = True
    except ValidationError:
        pass
    return valid, value


class Field(QLineEdit):
    def __init__(self, validatable: Type[Validatable], parent: QWidget | None = None, **validate_args) -> None:
        self.validatable = validatable
        self.validate_args = validate_args
        super().__init__(parent)
        self.base_style_sheet = self.styleSheet()

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


class SearchBox(QWidget):
    def __init__(self, filters: list[Filter], parent: QWidget | None = None):
        """
        Args:
            filters: dict {k: v}, where k is the filter name and v is the str to display in the combobox.
        """
        super().__init__(parent)

        self._setup_ui()

        self._filters = filters
        self._filters_index = {f.name: i for i, f in enumerate(self._filters)}
        fill_combobox(self.filter_combobox, self._filters, display=lambda f: f.display_name)

    def _setup_ui(self):
        self.layout = QHBoxLayout(self)

        self.filter_combobox = QComboBox()
        self.layout.addWidget(self.filter_combobox)
        config_combobox(self.filter_combobox, font_size=16)

        self.search_field = QLineEdit()
        self.layout.addWidget(self.search_field)
        config_line(self.search_field, place_holder="Búsqueda", font_size=16)

    def set_filter(self, name: str, value: str):
        self.filter_combobox.setCurrentIndex(self._filters_index[name])
        self.search_field.setText(value)

    def filters(self) -> dict[str: tuple[Filter, str]]:
        """Returns a dict {k: v}, where k is a Filter object and v is its value to filter.
        """
        selected: Filter = self.filter_combobox.currentData(Qt.UserRole)
        return {selected.name: (selected, self.search_field.text())}

    def passes_filters(self, to_filter: Any) -> bool:
        selected: Filter = self.filter_combobox.currentData(Qt.UserRole)
        return selected.passes(to_filter, self.search_field.text())

    def is_empty(self) -> bool:
        return len(self.search_field.text()) == 0 or self.search_field.text().isspace()


class Dialog(QDialog):

    @classmethod
    def confirm(cls, question: str) -> bool:
        dialog = Dialog(title="Confirmar", text=question, show_cancel_btn=True)
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
        self.ok_btn.clicked.connect(self.accept)
        if self.cancel_btn is not None:
            self.cancel_btn.clicked.connect(self.reject)

    def accept(self) -> None:
        self.confirmed = True
        super().accept()

    def reject(self) -> None:
        self.confirmed = False
        super().reject()

    def _setup_ui(self, title: str, text: str, show_cancel_btn: bool):
        self.resize(300, 120)
        self.setWindowTitle(title)

        self.layout = QVBoxLayout(self)

        self.question_lbl = QLabel(self)
        self.layout.addWidget(self.question_lbl, alignment=Qt.AlignCenter)
        config_lbl(self.question_lbl, text=text, width=300, word_wrap=True)

        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)
        config_layout(self.buttons_layout, alignment=Qt.AlignRight, right_margin=5)

        self.ok_btn = QPushButton()
        self.buttons_layout.addWidget(self.ok_btn)
        config_btn(self.ok_btn, "Ok", width=100)

        self.cancel_btn: QPushButton | None = None
        if show_cancel_btn:
            self.cancel_btn = QPushButton()
            self.buttons_layout.addWidget(self.cancel_btn)
            config_btn(self.cancel_btn, "Cancelar", width=100)

