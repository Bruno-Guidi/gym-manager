from datetime import date
from typing import Iterable, Callable, Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QLabel, QLineEdit, QTableWidget, QPushButton, \
    QLayout, QComboBox, QAbstractItemView, QHeaderView, QTableWidgetItem, \
    QTextEdit, QCheckBox, QDateEdit, QWidget


def config_widget(
        target: QWidget, font: str = "MS Shell Dlg 2", font_size: int = 14, extra_width: int = 0, extra_height: int = 0,
        enabled: bool = True, layout_dir=Qt.LayoutDirection.LeftToRight
):
    target.setFont(QFont(font, font_size))
    target.setMinimumSize(target.sizeHint().width() + extra_width, target.sizeHint().height() + extra_height)
    target.setMaximumSize(target.sizeHint().width() + extra_width, target.sizeHint().height() + extra_height)
    target.setLayoutDirection(layout_dir)
    target.setEnabled(enabled)


def config_line(
        target: QLineEdit | QTextEdit, text: str = "", place_holder: str = "", font: str = "MS Shell Dlg 2",
        font_size: int = 14, width: int = 0, height: int = 0, read_only: bool = True
):
    target.setText(text)
    target.setPlaceholderText(place_holder)
    target.setReadOnly(read_only)
    config_widget(target, font, font_size, width, height)


def config_lbl(
        target: QLabel, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14, width: int = 0,
        height: int = 0, alignment=None, word_wrap=False
):
    target.setText(text)
    if alignment is not None:
        target.setAlignment(alignment)
    config_widget(target, font, font_size, width, height)


def config_date_edit(
        target: QDateEdit, value: date, font: str = "MS Shell Dlg 2", font_size: int = 14, calendar: bool = True,
        width: int = 0, height: int = 0, layout_direction=Qt.LayoutDirection.LeftToRight
):
    target.setDate(value)
    target.setCalendarPopup(calendar)
    config_widget(target, font, font_size, width, height, layout_dir=layout_direction)


def config_btn(  # ToDo rename width to extra_width
        target: QPushButton, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14, width: int = 0,
        height: int = 0, enabled: bool = True
):
    target.setText(text)  # The value has to be set before the config_widget call.
    config_widget(target, font, font_size, width, height, enabled)


def config_checkbox(
        target: QCheckBox, checked: bool, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14,
        enabled: bool = True, width: int = 0, height: int = 0, direction=Qt.LayoutDirection.RightToLeft
):
    target.setText(text)
    target.setChecked(checked)
    config_widget(target, font, font_size, width, height, enabled, layout_dir=direction)


def config_layout(
        target: QLayout, alignment=Qt.AlignCenter, spacing: int = 6, left_margin: int = 11, top_margin: int = 11,
        right_margin: int = 11, bottom_margin: int = 11
):
    target.setAlignment(alignment)
    target.setSpacing(spacing)
    target.setContentsMargins(left_margin, top_margin, right_margin, bottom_margin)


def config_combobox(
        target: QComboBox, font: str = "MS Shell Dlg 2", font_size: int = 14, width: int = 0, height: int = 0
):
    config_widget(target, font, font_size, width, height)


def fill_combobox(target: QComboBox, items: Iterable, display: Callable[[Any], str]):
    model = QStandardItemModel()
    for item in items:
        std_item = QStandardItem()
        std_item.setData(display(item), Qt.DisplayRole)
        std_item.setData(item, Qt.UserRole)
        model.appendRow(std_item)
    target.setModel(model)


def config_table(
        target: QTableWidget, columns: dict[str, int], n_rows: int = 0, font_size: int = 14,
        allow_resizing: bool = False
):
    """Configures a QTableWidget.

    Args:
        target: QTableWidget to configure.
        columns: dict {k: v} where k is a column name, and v is the max number of chars that the column will display.
        n_rows: numbers of rows that the table will have.
        font_size: font size of the header and cells.
        allow_resizing: if True, columns can be resized during runtime.
    """
    target.setFont(QFont("Inconsolata", font_size))  # This font is monospaced.
    target.verticalHeader().setVisible(False)  # Hides rows number.

    target.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Blocks cell modification.
    if not allow_resizing:
        target.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)  # Blocks column resizing.

    target.setColumnCount(len(columns))
    target.setRowCount(n_rows)

    max_width = 0
    for i, (column_name, column_char_width) in enumerate(columns.items()):
        target.setHorizontalHeaderItem(i, QTableWidgetItem(column_name))
        placeholder = "".zfill(column_char_width)
        target.setColumnWidth(i, len(placeholder) * font_size)
        max_width += target.columnWidth(i)

    target.setMinimumWidth(max_width + target.verticalScrollBar().height() - 7)
    target.setSelectionMode(QAbstractItemView.SingleSelection)
