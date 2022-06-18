from typing import Type, Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLineEdit, QWidget, QTextEdit, QHBoxLayout, QComboBox

from gym_manager.core.base import Validatable, ValidationError, String
from ui.widget_config import fill_combobox, config_combobox, config_line


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
    def __init__(self, filters_names: dict[str, str], parent: QWidget | None = None):
        """
        Args:
            filters_names: dict {k: v}, where k is the filter name and v is the str to display in the combobox.
        """
        super().__init__(parent)

        self._setup_ui()

        self.filters_names = filters_names
        self.filters_values = {f: "" for f in filters_names.keys()}
        fill_combobox(self.filter_combobox, self.filters_names.keys(), display=lambda f: self.filters_names[f])

    def _setup_ui(self):
        self.layout = QHBoxLayout(self)

        self.filter_combobox = QComboBox()
        self.layout.addWidget(self.filter_combobox)
        config_combobox(self.filter_combobox, font_size=16)

        self.search_field = QLineEdit()
        self.layout.addWidget(self.search_field)
        config_line(self.search_field, place_holder="Búsqueda", font_size=16)

    def filters(self) -> dict[str, str]:
        """Returns a dict {k: v}, where k is the filter name and v is the filter value.
        """
        return self.filters_values

    def save_state(self):
        self.filters_values[self.filter_combobox.currentData(Qt.UserRole)] = self.search_field.text()