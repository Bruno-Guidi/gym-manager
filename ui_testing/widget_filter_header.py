import sys

from PyQt5.QtWidgets import QApplication

from gym_manager.core.base import String
from ui.widgets import FilterHeader

trans_charge, trans_extract = String("Cobro", max_len=30), String("Extracción", max_len=30)
trans_cash, trans_debit, trans_credit = (String("Efectivo", max_len=30), String("Débito", max_len=30),
                                         String("Crédito", max_len=30))


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = FilterHeader(date_greater_filtering=True, date_lesser_filtering=True)
    window.show()

    app.exec()
