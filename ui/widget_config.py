from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QLineEdit, QTableWidget, QPushButton, \
    QLayout, QComboBox, QAbstractItemView, QHeaderView, QTableWidgetItem, \
    QTextEdit, QCheckBox


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
        height: int = 0, alignment=Qt.AlignLeft
):
    target.setText(text)
    target.setFont(QFont(font, font_size))
    if width > 0:
        target.setFixedWidth(width)
    if height > 0:
        target.setFixedHeight(height)
    target.setAlignment(alignment)


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
