from datetime import date
from typing import Iterable, Callable, Any, Type

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import (
    QLabel, QLineEdit, QTableWidget, QPushButton,
    QLayout, QComboBox, QAbstractItemView, QHeaderView, QTableWidgetItem,
    QTextEdit, QCheckBox, QDateEdit, QWidget, QStyledItemDelegate)


def config_widget(
        target: QWidget, font: str = "MS Shell Dlg 2", font_size: int = 14, adjust_to_hint: bool = True,
        extra_width: int = 0, extra_height: int = 0, fixed_width: int = 0, enabled: bool = True,
        layout_dir=Qt.LayoutDirection.LeftToRight
):
    target.setFont(QFont(font, font_size))
    target.setMinimumSize(target.sizeHint().width() + extra_width, target.sizeHint().height() + extra_height)
    if adjust_to_hint:
        target.setMaximumSize(target.sizeHint().width() + extra_width, target.sizeHint().height() + extra_height)
    if fixed_width > 0:
        target.setFixedWidth(fixed_width)
    target.setLayoutDirection(layout_dir)
    target.setEnabled(enabled)


def config_line(
        target: QLineEdit | QTextEdit, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14,
        adjust_to_hint: bool = True, extra_width: int = 0, extra_height: int = 0, fixed_width: int = 0,
        enabled: bool = True, layout_dir=Qt.LayoutDirection.LeftToRight, place_holder: str = "",
        read_only: bool = False, alignment=None
):
    target.setText(text)
    target.setPlaceholderText(place_holder)
    target.setReadOnly(read_only)
    if alignment is not None:
        target.setAlignment(alignment)
    config_widget(target, font, font_size, adjust_to_hint, extra_width, extra_height, fixed_width, enabled, layout_dir)


def config_lbl(
        target: QLabel, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14, adjust_to_hint: bool = True,
        extra_width: int = 0, extra_height: int = 0, fixed_width: int = 0, enabled: bool = True,
        layout_dir=Qt.LayoutDirection.LeftToRight, alignment=None, word_wrap: bool = True, adjust_size: bool = True
):
    target.setText(text)
    if alignment is not None:
        target.setAlignment(alignment)
    config_widget(target, font, font_size, adjust_to_hint, extra_width, extra_height, fixed_width, enabled, layout_dir)
    target.setWordWrap(word_wrap)
    if adjust_size:
        target.adjustSize()
        target.setMinimumSize(target.sizeHint())


def config_date_edit(
        target: QDateEdit, value: date, calendar: bool, font: str = "MS Shell Dlg 2", font_size: int = 14,
        enabled: bool = True, layout_dir=Qt.LayoutDirection.LeftToRight
):
    target.setDate(value)
    target.setCalendarPopup(calendar)
    config_widget(target, font, font_size, enabled=enabled, layout_dir=layout_dir)


def config_btn(
        target: QPushButton, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14,
        adjust_to_hint: bool = True, extra_width: int = 0, extra_height: int = 0, fixed_width: int = 0,
        enabled: bool = True, layout_dir=Qt.LayoutDirection.LeftToRight, icon_path: str | None = None,
        icon_size: int | None = None
):
    target.setText(text)  # The value has to be set before the config_widget call.
    if icon_path is not None and icon_size is not None:
        target.setIcon(QIcon(icon_path))
        target.setIconSize(QSize(icon_size, icon_size))
    config_widget(target, font, font_size, adjust_to_hint, extra_width, extra_height, fixed_width, enabled, layout_dir)


def config_checkbox(
        target: QCheckBox, text: str = "", font: str = "MS Shell Dlg 2", font_size: int = 14,
        adjust_to_hint: bool = True, extra_width: int = 0, extra_height: int = 0, fixed_width: int = 0,
        enabled: bool = True, layout_dir=Qt.LayoutDirection.LeftToRight, checked: bool = False
):
    target.setText(text)
    target.setChecked(checked)
    config_widget(target, font, font_size, adjust_to_hint, extra_width, extra_height, fixed_width, enabled, layout_dir)


def config_layout(
        target: QLayout, alignment=Qt.AlignCenter, spacing: int = 6, left_margin: int = 11, top_margin: int = 11,
        right_margin: int = 11, bottom_margin: int = 11
):
    target.setAlignment(alignment)
    target.setSpacing(spacing)
    target.setContentsMargins(left_margin, top_margin, right_margin, bottom_margin)


def config_combobox(
        target: QComboBox, font: str = "MS Shell Dlg 2", font_size: int = 14, adjust_to_hint: bool = True,
        extra_width: int = 0, extra_height: int = 0, fixed_width: int = 0, enabled: bool = True,
        layout_dir=Qt.LayoutDirection.LeftToRight
):
    config_widget(target, font, font_size, adjust_to_hint, extra_width, extra_height, fixed_width, enabled, layout_dir)


def fill_combobox(target: QComboBox, items: Iterable, display: Callable[[Any], str]):
    model = QStandardItemModel()
    for item in items:
        std_item = QStandardItem()
        std_item.setData(display(item), Qt.DisplayRole)
        std_item.setData(item, Qt.UserRole)
        model.appendRow(std_item)
    target.setModel(model)


def config_table(
        target: QTableWidget, columns: dict[str, tuple[int, type]], n_rows: int = 0, font_size: int = 14,
        allow_resizing: bool = False, min_rows_to_show: int = 0
):
    """Configures a QTableWidget.

    Args:
        target: QTableWidget to configure.
        columns: dict {k: (a, b)} where k is a column name, a is the max number of chars that the column will display,
            and b is the type of the data displayed.
        n_rows: numbers of rows that the table will have.
        font_size: font size of the header and cells.
        allow_resizing: if True, columns can be resized during runtime.
        min_rows_to_show: the minimum height of the table will be (*min_rows_to_show* + 1)*horizontalHeader.height()
    """
    target.horizontalHeader().setFont(QFont("Inconsolata", font_size))
    target.setFont(QFont("Inconsolata", font_size))  # This font is monospaced.
    target.verticalHeader().setVisible(False)  # Hides rows number.

    target.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Blocks cell modification.
    if not allow_resizing:
        target.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)  # Blocks column resizing.

    target.setColumnCount(len(columns))
    target.setRowCount(n_rows)

    max_width = 0
    for i, (column_name, (column_char_width, column_type)) in enumerate(columns.items()):
        item = QTableWidgetItem(column_name)
        align = Qt.AlignRight if column_type is int else Qt.AlignLeft
        align = Qt.AlignCenter if column_type is bool else align
        item.setTextAlignment(align)
        target.setHorizontalHeaderItem(i, item)

        placeholder = "".zfill(column_char_width)  # The width of the column is based on the char width received.
        target.setColumnWidth(i, len(placeholder) * font_size)
        max_width += target.columnWidth(i)

    target.setMinimumWidth(max_width + target.verticalScrollBar().height() - 7)
    target.setSelectionMode(QAbstractItemView.SingleSelection)

    if min_rows_to_show > 0:
        # One extra row is added to include header height, and another one is added to include the scrollbar.
        target.setMinimumHeight((min_rows_to_show + 2) * target.horizontalHeader().height())


def new_config_table(
        target: QTableWidget, width: int, columns: dict[str, tuple[float, type]], n_rows: int = 0, font_size: int = 14,
        allow_resizing: bool = True, min_rows_to_show: int = 0
):
    target.horizontalHeader().setFont(QFont("Inconsolata", font_size))
    target.setFont(QFont("Inconsolata", font_size))  # This font is monospaced.
    target.verticalHeader().setVisible(False)  # Hides rows number.

    target.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Blocks cell modification.
    if not allow_resizing:
        target.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)  # Blocks column resizing.

    target.setColumnCount(len(columns))
    target.setRowCount(n_rows)

    target.setMinimumWidth(width)
    width = width - target.verticalScrollBar().height()  # Allocates some spaces to the vertical scrollbar.
    for i, (column_name, (percentage_width, column_type)) in enumerate(columns.items()):
        item = QTableWidgetItem(column_name)
        align = Qt.AlignRight if column_type is int else Qt.AlignLeft
        align = Qt.AlignCenter if column_type is bool else align
        item.setTextAlignment(align)
        target.setHorizontalHeaderItem(i, item)
        target.setColumnWidth(i, int(percentage_width * width))

    target.setSelectionMode(QAbstractItemView.SingleSelection)
    if min_rows_to_show > 0:
        # One extra row is added to include header height, and another one is added to include the scrollbar.
        target.setMinimumHeight((min_rows_to_show + 2) * target.horizontalHeader().height())


def fill_cell(target: QTableWidget, row: int, column: int, data: Any, data_type: Type,
              increase_row_count: bool = True):
    if increase_row_count:
        target.setRowCount(row + 1)
    item = QTableWidgetItem(str(data))
    align = Qt.AlignRight if data_type is int else Qt.AlignLeft
    align = Qt.AlignCenter if data_type is bool else align
    item.setTextAlignment(align | Qt.AlignVCenter)
    target.setItem(row, column, item)
