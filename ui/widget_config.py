from datetime import date
from typing import Iterable, Callable, Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QLabel, QLineEdit, QTableWidget, QPushButton, \
    QLayout, QComboBox, QAbstractItemView, QHeaderView, QTableWidgetItem, \
    QTextEdit, QCheckBox, QDateEdit


def config_line(
        target: QLineEdit | QTextEdit, text: str = "", place_holder: str = "", font: str = "MS Shell Dlg 2",
        font_size: int = 14, width: int = 0, height: int = 0, enabled: bool = True
):
    target.setText(text)
    target.setPlaceholderText(place_holder)
    target.setFont(QFont(font, font_size))
    if width > 0:
        target.setFixedWidth(width)
    if height > 0:
        target.setFixedHeight(height)
    target.setEnabled(enabled)


def config_lbl(
        target: QLabel, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14, width: int = 0,
        height: int = 0, alignment=Qt.AlignLeft, word_wrap: bool = False
):
    target.setWordWrap(word_wrap)
    target.setText(text)
    target.setFont(QFont(font, font_size))
    if width > 0:
        target.setFixedWidth(width)
    if height > 0:
        target.setFixedHeight(height)
    target.setAlignment(alignment)


def config_date_edit(
        target: QDateEdit, value: date, font: str = "MS Shell Dlg 2", font_size: int = 14, calendar: bool = True,
        width: int = 0, height: int = 0, layout_direction=Qt.LayoutDirection.LeftToRight
):
    target.setDate(value)
    target.setFont(QFont(font, font_size))
    target.setCalendarPopup(calendar)
    target.setLayoutDirection(layout_direction)


def config_btn(
        target: QPushButton, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14, width: int = 0,
        height: int = 0
):
    target.setText(text)
    target.setFont(QFont(font, font_size))
    if width > 0:
        target.setFixedWidth(width)
    if height > 0:
        target.setFixedHeight(height)


def config_checkbox(
        target: QCheckBox, checked: bool, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14,
        enabled: bool = True, width: int = 0, direction=Qt.LayoutDirection.RightToLeft
):
    target.setText(text)
    target.setFont(QFont(font, font_size))
    target.setChecked(checked)
    target.setEnabled(enabled)
    if width > 0:
        target.setFixedWidth(width)
    target.setLayoutDirection(direction)


def config_layout(
        target: QLayout, alignment=Qt.AlignCenter, spacing: int = 6, left_margin: int = 0, top_margin: int = 0,
        right_margin: int = 0, bottom_margin: int = 0
):
    target.setAlignment(alignment)
    target.setSpacing(spacing)
    target.setContentsMargins(left_margin, top_margin, right_margin, bottom_margin)


def config_combobox(
        target: QComboBox, font: str = "MS Shell Dlg 2", font_size: int = 14, height: int = 0
):
    target.setFont(QFont(font, font_size))
    if height > 0:
        target.setFixedHeight(height)


def config_table(
        target: QTableWidget, columns: dict[str, int], n_rows: int = 0, font_size: int = 14,
        allow_resizing: bool = False
):
    target.setFont(QFont("Inconsolata", font_size))  # This font is monospaced.
    target.verticalHeader().setVisible(False)

    target.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Blocks cell modification.
    if not allow_resizing:
        target.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)  # Blocks column resizing.

    target.setColumnCount(len(columns))
    target.setRowCount(n_rows)

    for i, (column_name, column_width) in enumerate(columns.items()):
        target.setHorizontalHeaderItem(i, QTableWidgetItem(column_name))
        target.setColumnWidth(i, column_width)


def fill_combobox(target: QComboBox, items: Iterable, display: Callable[[Any], str]):
    model = QStandardItemModel()
    for item in items:
        std_item = QStandardItem()
        std_item.setData(display(item), Qt.DisplayRole)
        std_item.setData(item, Qt.UserRole)
        model.appendRow(std_item)
    target.setModel(model)
