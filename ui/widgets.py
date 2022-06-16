from typing import Type, Any

from PyQt5.QtWidgets import QLineEdit, QWidget, QTextEdit

from gym_manager.core.base import Validatable, ValidationError, String


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
